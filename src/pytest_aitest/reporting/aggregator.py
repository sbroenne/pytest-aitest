"""Smart dimension detection and aggregation for test results.

Automatically detects multi-model and multi-prompt test patterns from
pytest.mark.parametrize and groups results accordingly.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from pytest_aitest.reporting.collector import SuiteReport, TestReport


@dataclass(slots=True)
class TestDimensions:
    """Detected test dimensions (models and prompts used in the test suite)."""
    
    models: list[str]
    prompts: list[str]


class ReportMode(Enum):
    """Detected report mode based on test dimensions."""

    SIMPLE = auto()  # Single tests, no parametrization
    MODEL_COMPARISON = auto()  # Same tests across multiple models
    PROMPT_COMPARISON = auto()  # Same model, multiple prompts
    MATRIX = auto()  # Multiple models AND prompts (2D grid)


@dataclass
class AdaptiveFlags:
    """Flags controlling which sections to render in the report.

    Mirrors agent-benchmark: detect dimensions → set flags → template renders.
    """

    # Core visibility flags
    show_model_leaderboard: bool = False
    show_prompt_comparison: bool = False
    show_matrix: bool = False
    show_test_overview: bool = True
    show_tool_comparison: bool = False
    show_side_by_side: bool = False

    # Counts for display
    model_count: int = 0
    prompt_count: int = 0
    test_count: int = 0

    # Single model/prompt mode (no comparison needed)
    single_model_mode: bool = True
    single_model_name: str | None = None
    single_prompt_mode: bool = True
    single_prompt_name: str | None = None

    @classmethod
    def from_dimensions(cls, dimensions: TestDimensions, test_count: int) -> AdaptiveFlags:
        """Create flags from detected dimensions."""
        model_count = len(dimensions.models)
        prompt_count = len(dimensions.prompts)

        return cls(
            show_model_leaderboard=model_count > 1,
            show_prompt_comparison=prompt_count > 1,
            show_matrix=model_count > 1 and prompt_count > 1,
            show_test_overview=test_count > 1,
            show_tool_comparison=False,  # Set later by get_adaptive_flags
            show_side_by_side=False,  # Set later by get_adaptive_flags
            model_count=model_count,
            prompt_count=prompt_count,
            test_count=test_count,
            single_model_mode=model_count <= 1,
            single_model_name=dimensions.models[0] if model_count == 1 else None,
            single_prompt_mode=prompt_count <= 1,
            single_prompt_name=dimensions.prompts[0] if prompt_count == 1 else None,
        )





@dataclass
class GroupedResult:
    """Results grouped by a dimension (model or prompt)."""

    dimension_value: str
    tests: list[TestReport]
    passed: int = 0
    failed: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_duration_ms: float = 0.0
    rank: int = 0  # 1 = best, 2 = second, etc.

    def __post_init__(self) -> None:
        self.passed = sum(1 for t in self.tests if t.outcome == "passed")
        self.failed = sum(1 for t in self.tests if t.outcome == "failed")
        self.total_tokens = sum(
            (
                t.agent_result.token_usage.get("prompt", 0)
                + t.agent_result.token_usage.get("completion", 0)
            )
            for t in self.tests
            if t.agent_result is not None
        )
        self.total_cost = sum(
            t.agent_result.cost_usd for t in self.tests if t.agent_result is not None
        )
        durations = [t.duration_ms for t in self.tests]
        self.avg_duration_ms = sum(durations) / len(durations) if durations else 0.0

    @property
    def pass_rate(self) -> float:
        total = self.passed + self.failed
        return (self.passed / total * 100) if total > 0 else 0.0

    @property
    def efficiency(self) -> float:
        """Tokens per passed test (lower is better). Returns inf if no passed tests."""
        if self.passed == 0:
            return float("inf")
        return self.total_tokens / self.passed

    @property
    def medal(self) -> str:
        """Return medal emoji based on rank."""
        if self.rank == 1:
            return "🥇"
        elif self.rank == 2:
            return "🥈"
        elif self.rank == 3:
            return "🥉"
        return ""


@dataclass
class MatrixCell:
    """A single cell in a model x prompt matrix."""

    model: str
    prompt: str
    test: TestReport | None = None

    @property
    def outcome(self) -> str:
        return self.test.outcome if self.test else "missing"

    @property
    def passed(self) -> bool:
        return self.test is not None and self.test.outcome == "passed"


@dataclass
class SessionGroup:
    """A group of tests that share conversation history (session).

    Detected from test class names - tests in the same class with
    is_session_continuation form a session workflow.
    """

    name: str  # Class name or "Standalone" for non-session tests
    tests: list[TestReport]
    is_session: bool = False  # True if tests share conversation context

    @property
    def total_messages(self) -> int:
        """Total messages in the session (from last test)."""
        if not self.tests:
            return 0
        last = self.tests[-1]
        if last.agent_result:
            return len(last.agent_result.messages)
        return 0

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.outcome == "passed")

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if t.outcome == "failed")

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.passed > 0

    @property
    def total_duration_ms(self) -> float:
        """Total duration of all tests in session."""
        return sum(t.duration_ms for t in self.tests)

    @property
    def total_tokens(self) -> int:
        """Total tokens used across all tests in session."""
        return sum(
            (
                t.agent_result.token_usage.get("prompt", 0)
                + t.agent_result.token_usage.get("completion", 0)
            )
            for t in self.tests
            if t.agent_result
        )

    @property
    def total_cost(self) -> float:
        """Total cost across all tests in session."""
        return sum(t.agent_result.cost_usd for t in self.tests if t.agent_result)

    @property
    def total_tool_calls(self) -> int:
        """Total tool calls across all tests in session."""
        return sum(len(t.agent_result.all_tool_calls) for t in self.tests if t.agent_result)


class DimensionAggregator:
    """Analyzes test results and groups by detected dimensions.

    Uses pytest node ID parsing to detect parametrization patterns:
    - test_foo[gpt-4o] -> model dimension
    - test_foo[PROMPT_V1] -> prompt dimension
    - test_foo[gpt-4o-PROMPT_V1] -> matrix (both dimensions)

    Example:
        aggregator = DimensionAggregator()
        dimensions = aggregator.detect_dimensions(suite_report)

        if dimensions.mode == ReportMode.MODEL_COMPARISON:
            groups = aggregator.group_by_model(suite_report)
        elif dimensions.mode == ReportMode.MATRIX:
            matrix = aggregator.build_matrix(suite_report, dimensions)
    """

    # Common model patterns (litellm format) - non-greedy to avoid matching prompt names
    MODEL_PATTERNS: ClassVar[Sequence[str]] = (
        r"openai/gpt-\d[\w.-]*",  # openai/gpt-4o, openai/gpt-4o-mini
        r"anthropic/claude-\d[\w.-]*",  # anthropic/claude-3-opus
        r"azure/[\w.-]+",
        r"gpt-\d[\w.]*(?:-mini|-turbo)?",  # gpt-4o, gpt-4.1, gpt-5-mini
        r"gpt-3\.5-turbo",  # gpt-3.5-turbo
        r"claude-\d(?:\.\d)?(?:-\w+)?",  # claude-3, claude-3.5-sonnet
        r"gemini-\d[\w.-]*",  # gemini-1.5-pro
        r"mistral-[\w-]+",
        r"llama\d[\w.-]*",  # llama3, llama3-8b
        r"o\d(?:-mini|-preview)?",  # o1, o1-mini
    )

    # Pattern for prompt names (typically SCREAMING_CASE or PascalCase)
    PROMPT_PATTERNS: ClassVar[Sequence[str]] = (
        r"PROMPT_\w+",
        r"[A-Z][a-z]+Prompt",
        r"prompt_v\d+",
    )



    def _parse_node_id(self, node_id: str) -> tuple[str, list[str]]:
        """Parse pytest node ID into base name and parameters.

        Example:
            "test_weather[gpt-4o-PROMPT_V1]" -> ("test_weather", ["gpt-4o-PROMPT_V1"])

        Note: Returns the full parameter string as a single item. Model/prompt
        extraction is done by matching patterns against this string.
        """
        match = re.match(r"([^\[]+)(?:\[([^\]]+)\])?", node_id)
        if not match:
            return node_id, []

        base_name = match.group(1)
        params_str = match.group(2)

        if not params_str:
            return base_name, []

        # Return the full param string - pattern matching handles extraction
        return base_name, [params_str]

    def _extract_model_from_params(self, params_str: str) -> str | None:
        """Extract model name from parameter string using pattern matching."""
        model_pattern = re.compile("|".join(f"({p})" for p in self.MODEL_PATTERNS), re.IGNORECASE)
        match = model_pattern.search(params_str)
        if match:
            return match.group(0)
        return None

    def _extract_prompt_from_params(self, params_str: str) -> str | None:
        """Extract prompt name from parameter string using pattern matching."""
        prompt_pattern = re.compile("|".join(f"({p})" for p in self.PROMPT_PATTERNS))
        match = prompt_pattern.search(params_str)
        if match:
            return match.group(0)
        return None

    def detect_dimensions(self, report: SuiteReport) -> TestDimensions:
        """Detect unique models and prompts used in the test suite.
        
        Extracts from test metadata and node IDs to build a complete
        picture of what dimensions are being compared.
        
        Returns:
            TestDimensions with unique models and prompts.
        """
        models: set[str] = set()
        prompts: set[str] = set()
        
        for test in report.tests:
            # Extract model
            model = test.metadata.get("model")
            if not model:
                _, params = self._parse_node_id(test.name)
                if params:
                    model = self._extract_model_from_params(params[0])
            if model:
                models.add(model)
            
            # Extract prompt
            prompt = test.metadata.get("prompt")
            if not prompt:
                _, params = self._parse_node_id(test.name)
                if params:
                    prompt = self._extract_prompt_from_params(params[0])
            if prompt:
                prompts.add(prompt)
        
        return TestDimensions(
            models=sorted(models),
            prompts=sorted(prompts),
        )

    def group_by_model(self, report: SuiteReport) -> list[GroupedResult]:
        """Group test results by model.

        Returns results sorted by pass rate (descending) with ranks assigned.
        """
        groups: dict[str, list[TestReport]] = {}

        for test in report.tests:
            model = test.metadata.get("model")
            if not model:
                # Try to extract from node ID
                _, params = self._parse_node_id(test.name)
                if params:
                    model = self._extract_model_from_params(params[0])

            if model:
                groups.setdefault(model, []).append(test)

        results = [
            GroupedResult(dimension_value=model, tests=tests) for model, tests in groups.items()
        ]
        results = sorted(results, key=lambda g: (-g.pass_rate, g.dimension_value))

        # Assign ranks
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def group_by_prompt(self, report: SuiteReport) -> list[GroupedResult]:
        """Group test results by prompt.

        Returns results sorted by pass rate (descending) with ranks assigned.
        """
        groups: dict[str, list[TestReport]] = {}

        for test in report.tests:
            prompt = test.metadata.get("prompt")
            if not prompt:
                # Try to extract from node ID
                _, params = self._parse_node_id(test.name)
                if params:
                    prompt = self._extract_prompt_from_params(params[0])

            if prompt:
                groups.setdefault(prompt, []).append(test)

        results = [
            GroupedResult(dimension_value=prompt, tests=tests) for prompt, tests in groups.items()
        ]
        results = sorted(results, key=lambda g: (-g.pass_rate, g.dimension_value))

        # Assign ranks
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def build_matrix(
        self, report: SuiteReport, dimensions: TestDimensions
    ) -> list[list[MatrixCell]]:
        """Build 2D matrix of model x prompt results.

        Returns a list of rows (prompts), each containing cells (models).
        """
        # Create lookup: (model, prompt) -> test
        lookup: dict[tuple[str, str], TestReport] = {}
        for test in report.tests:
            model = test.metadata.get("model", "")
            prompt = test.metadata.get("prompt", "")

            # Try to extract from node ID if not in metadata
            if not model or not prompt:
                _, params = self._parse_node_id(test.name)
                if params:
                    params_str = params[0]
                    if not model:
                        model = self._extract_model_from_params(params_str) or ""
                    if not prompt:
                        prompt = self._extract_prompt_from_params(params_str) or ""

            if model and prompt:
                lookup[(model, prompt)] = test

        # Build matrix
        matrix = []
        for prompt in dimensions.prompts:
            row = []
            for model in dimensions.models:
                test = lookup.get((model, prompt))
                row.append(MatrixCell(model=model, prompt=prompt, test=test))
            matrix.append(row)

        return matrix

    def group_by_session(self, report: SuiteReport) -> list[SessionGroup]:
        """Group tests by session (tests sharing conversation history).

        Detects sessions by:
        1. Extracting class name from test node ID (e.g., TestBankingWorkflow)
        2. Checking if tests have is_session_continuation set
        3. Grouping tests with same class that form a session workflow

        Returns ordered list of SessionGroups preserving test order.
        """
        # Group by class name
        class_groups: dict[str, list[TestReport]] = {}
        standalone: list[TestReport] = []

        for test in report.tests:
            # Extract class name from node ID
            # Format: path/file.py::ClassName::test_name or path/file.py::test_name
            class_name = self._extract_class_name(test.name)

            if class_name:
                if class_name not in class_groups:
                    class_groups[class_name] = []
                class_groups[class_name].append(test)
            else:
                standalone.append(test)

        # Build session groups
        groups: list[SessionGroup] = []

        for class_name, tests in class_groups.items():
            # Check if this is a session (any test has session continuation)
            has_session = any(
                t.agent_result and t.agent_result.is_session_continuation for t in tests
            )

            groups.append(
                SessionGroup(
                    name=class_name,
                    tests=tests,
                    is_session=has_session,
                )
            )

        # Add standalone tests (no class)
        if standalone:
            groups.append(
                SessionGroup(
                    name="Standalone Tests",
                    tests=standalone,
                    is_session=False,
                )
            )

        return groups

    def _extract_class_name(self, node_id: str) -> str | None:
        """Extract test class name from pytest node ID.

        Examples:
            "tests/test_foo.py::TestClass::test_method" -> "TestClass"
            "tests/test_foo.py::test_function" -> None
        """
        # Split by :: and look for class pattern
        parts = node_id.split("::")
        if len(parts) >= 2:
            # Check if second-to-last part is a class (starts with uppercase)
            for part in parts[1:-1]:  # Skip file path and test name
                if part and part[0].isupper():
                    return part
        return None

    def get_model_rankings(self, report: SuiteReport) -> list[tuple[str, float, int, float]]:
        """Get models ranked by pass rate.

        Returns list of (model, pass_rate, total_tests, avg_cost).
        """
        groups = self.group_by_model(report)
        return [
            (
                g.dimension_value,
                g.pass_rate,
                len(g.tests),
                g.total_cost / len(g.tests) if g.tests else 0,
            )
            for g in groups
        ]

    def get_prompt_rankings(self, report: SuiteReport) -> list[tuple[str, float, int]]:
        """Get prompts ranked by pass rate.

        Returns list of (prompt, pass_rate, total_tests).
        """
        groups = self.group_by_prompt(report)
        return [(g.dimension_value, g.pass_rate, len(g.tests)) for g in groups]

    def get_adaptive_flags(self, report: SuiteReport) -> AdaptiveFlags:
        """Create adaptive flags for template rendering."""
        dimensions = self.detect_dimensions(report)
        flags = AdaptiveFlags.from_dimensions(dimensions, len(report.tests))
        
        # Add new comparison flags
        flags.show_tool_comparison = (
            flags.model_count > 1 or flags.prompt_count > 1
        ) and self._has_tool_calls(report)
        flags.show_side_by_side = flags.model_count > 1 or flags.prompt_count > 1
        
        return flags

    def _has_tool_calls(self, report: SuiteReport) -> bool:
        """Check if any test has tool calls."""
        return any(
            t.agent_result and t.agent_result.all_tool_calls
            for t in report.tests
        )

    def _get_model_for_test(self, test: TestReport) -> str | None:
        """Extract model name from test metadata or node ID."""
        model = test.metadata.get("model")
        if not model:
            _, params = self._parse_node_id(test.name)
            if params:
                model = self._extract_model_from_params(params[0])
        return model

    def _get_prompt_for_test(self, test: TestReport) -> str | None:
        """Extract prompt name from test metadata or node ID."""
        prompt = test.metadata.get("prompt")
        if not prompt:
            _, params = self._parse_node_id(test.name)
            if params:
                prompt = self._extract_prompt_from_params(params[0])
        return prompt

    def build_tool_comparison(self, report: SuiteReport) -> dict | None:
        """Build tool usage comparison across models or prompts.
        
        Returns a dict with:
        - columns: list of column names (models or prompts)
        - tools: list of {name, counts, total} for each tool
        - column_totals: list of total calls per column
        - grand_total: total calls across all
        """
        dimensions = self.detect_dimensions(report)
        
        # Determine columns (prefer models if available, otherwise prompts)
        if len(dimensions.models) > 1:
            columns = dimensions.models
            get_column = self._get_model_for_test
        elif len(dimensions.prompts) > 1:
            columns = dimensions.prompts
            get_column = self._get_prompt_for_test
        else:
            return None  # No comparison possible
        
        # Collect tool calls per column
        tool_counts: dict[str, dict[str, int]] = {}  # tool_name -> column -> count
        
        for test in report.tests:
            if not test.agent_result:
                continue
            column = get_column(test)
            if not column:
                continue
            
            for tc in test.agent_result.all_tool_calls:
                if tc.name not in tool_counts:
                    tool_counts[tc.name] = {c: 0 for c in columns}
                if column in tool_counts[tc.name]:
                    tool_counts[tc.name][column] += 1
        
        if not tool_counts:
            return None
        
        # Build result structure
        tools = []
        for tool_name in sorted(tool_counts.keys()):
            counts = [tool_counts[tool_name].get(c, 0) for c in columns]
            tools.append({
                "name": tool_name,
                "counts": counts,
                "total": sum(counts),
            })
        
        column_totals = [
            sum(tool_counts[t].get(c, 0) for t in tool_counts)
            for c in columns
        ]
        
        return {
            "columns": columns,
            "tools": tools,
            "column_totals": column_totals,
            "grand_total": sum(column_totals),
        }

    def build_side_by_side(self, report: SuiteReport) -> list[dict] | None:
        """Build side-by-side comparison data for tests across variants.
        
        Returns list of test groups, each with:
        - test_name: base test name
        - variants: list of {name, passed, duration_ms, total_tokens, tool_calls, agent_result}
        - has_tool_calls: bool
        """
        dimensions = self.detect_dimensions(report)
        
        # Need multiple models or prompts for comparison
        if len(dimensions.models) <= 1 and len(dimensions.prompts) <= 1:
            return None
        
        # Group by base test name
        test_groups: dict[str, list[TestReport]] = {}
        
        for test in report.tests:
            base_name, _ = self._parse_node_id(test.name)
            if base_name not in test_groups:
                test_groups[base_name] = []
            test_groups[base_name].append(test)
        
        # Only include tests with multiple variants
        result = []
        for base_name, tests in test_groups.items():
            if len(tests) <= 1:
                continue
            
            # Build variant info
            variants = []
            has_tool_calls = False
            
            for test in tests:
                # Determine variant name (model or prompt or both)
                parts = []
                model = self._get_model_for_test(test)
                prompt = self._get_prompt_for_test(test)
                if model:
                    parts.append(model)
                if prompt:
                    parts.append(prompt)
                variant_name = " / ".join(parts) if parts else test.name
                
                # Calculate metrics
                total_tokens = 0
                tool_calls = 0
                if test.agent_result is not None:
                    total_tokens = (
                        test.agent_result.token_usage.get("prompt", 0)
                        + test.agent_result.token_usage.get("completion", 0)
                    )
                    tool_calls = len(test.agent_result.all_tool_calls)
                    if tool_calls > 0:
                        has_tool_calls = True
                
                variants.append({
                    "name": variant_name,
                    "passed": test.outcome == "passed",
                    "duration_ms": test.duration_ms,
                    "total_tokens": total_tokens,
                    "tool_calls": tool_calls,
                    "agent_result": test.agent_result,
                })
            
            result.append({
                "test_name": base_name,
                "variants": variants,
                "has_tool_calls": has_tool_calls,
            })
        
        return result if result else None
