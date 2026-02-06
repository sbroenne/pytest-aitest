"""Report collector and data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pytest_aitest.core.result import AgentResult


@dataclass
class TestReport:
    """Report data for a single test.

    Attributes:
        name: Full test node ID (e.g., "test_weather[gpt-4o-PROMPT_V1]")
        outcome: Test outcome - "passed", "failed", or "skipped"
        duration_ms: Test duration in milliseconds
        agent_result: Optional AgentResult from aitest_run
        error: Error message if test failed
        assertions: List of assertion results
        metadata: Additional test metadata (model, prompt, etc.)
        docstring: Test function's docstring (first line) for human-readable description
    """

    name: str
    outcome: str  # "passed", "failed", "skipped"
    duration_ms: float
    agent_result: AgentResult | None = None
    error: str | None = None
    assertions: list[dict[str, Any]] = field(default_factory=list)
    docstring: str | None = None

    # Agent identity (populated by plugin from Agent object, or from JSON)
    agent_id: str = ""
    agent_name: str = ""
    model: str = ""
    system_prompt_name: str | None = None
    skill_name: str | None = None

    @property
    def is_passed(self) -> bool:
        return self.outcome == "passed"

    @property
    def is_failed(self) -> bool:
        return self.outcome == "failed"

    @property
    def short_name(self) -> str:
        """Extract just the test function name from the full node ID.

        'tests/test_foo.py::TestClass::test_bar[param]' -> 'test_bar[param]'
        """
        return self.name.split("::")[-1]

    @property
    def display_name(self) -> str:
        """Human-readable test name: docstring if available, else short test name."""
        if self.docstring:
            # Return first line of docstring, stripped
            return self.docstring.split("\n")[0].strip()
        return self.short_name

    @property
    def tokens_used(self) -> int:
        """Get total tokens used from agent_result if present."""
        if self.agent_result:
            return self.agent_result.token_usage.get(
                "prompt", 0
            ) + self.agent_result.token_usage.get("completion", 0)
        return 0

    @property
    def tool_calls(self) -> list[str]:
        """Get tool call names from agent_result if present."""
        if self.agent_result:
            return [tc.name for tc in self.agent_result.all_tool_calls]
        return []


@dataclass
class SuiteReport:
    """Report data for a test suite.

    Automatically computes statistics from test results.
    """

    name: str
    timestamp: str
    duration_ms: float
    tests: list[TestReport] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    suite_docstring: str | None = None

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total * 100

    @property
    def total_tokens(self) -> int:
        """Sum of all tokens used."""
        total = 0
        for t in self.tests:
            if t.agent_result:
                total += t.agent_result.token_usage.get("prompt", 0)
                total += t.agent_result.token_usage.get("completion", 0)
        return total

    @property
    def total_cost_usd(self) -> float:
        """Sum of all costs in USD."""
        return sum(t.agent_result.cost_usd for t in self.tests if t.agent_result)

    @property
    def token_stats(self) -> dict[str, int]:
        """Get min/max/avg token usage."""
        tokens = [
            t.agent_result.token_usage.get("prompt", 0)
            + t.agent_result.token_usage.get("completion", 0)
            for t in self.tests
            if t.agent_result
        ]
        if not tokens:
            return {"min": 0, "max": 0, "avg": 0}
        return {
            "min": min(tokens),
            "max": max(tokens),
            "avg": sum(tokens) // len(tokens),
        }

    @property
    def cost_stats(self) -> dict[str, float]:
        """Get min/max/avg cost in USD."""
        costs = [
            t.agent_result.cost_usd
            for t in self.tests
            if t.agent_result and t.agent_result.cost_usd > 0
        ]
        if not costs:
            return {"min": 0.0, "max": 0.0, "avg": 0.0}
        return {
            "min": min(costs),
            "max": max(costs),
            "avg": sum(costs) / len(costs),
        }

    @property
    def duration_stats(self) -> dict[str, float]:
        """Get min/max/avg duration in ms."""
        durations = [t.duration_ms for t in self.tests if t.duration_ms > 0]
        if not durations:
            return {"min": 0.0, "max": 0.0, "avg": 0.0}
        return {
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations),
        }

    @property
    def tool_call_count(self) -> int:
        """Total number of tool calls across all tests."""
        return sum(len(t.agent_result.all_tool_calls) for t in self.tests if t.agent_result)

    @property
    def test_files(self) -> list[str]:
        """Unique test file paths."""
        files = set()
        for t in self.tests:
            # Extract file path from node ID (e.g., "tests/test_basic.py::TestClass::test")
            if "::" in t.name:
                files.add(t.name.split("::")[0])
            else:
                files.add(t.name)
        return sorted(files)

    @property
    def models_used(self) -> list[str]:
        """Unique models used across tests."""
        models = set()
        for t in self.tests:
            if t.model:
                models.add(t.model)
        return sorted(models)

    @property
    def prompts_used(self) -> list[str]:
        """Unique system prompt names used across tests."""
        prompts = set()
        for t in self.tests:
            if t.system_prompt_name:
                prompts.add(t.system_prompt_name)
        return sorted(prompts)


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


class ReportCollector:
    """Collects test results during pytest run.

    Example:
        collector = ReportCollector()
        collector.add_test(TestReport(name="test_foo", outcome="passed", ...))
        report = collector.build_suite_report("my_tests")
    """

    def __init__(self) -> None:
        self.tests: list[TestReport] = []
        self._start_time: float | None = None

    def add_test(self, test: TestReport) -> None:
        """Add a test result."""
        self.tests.append(test)

    def build_suite_report(self, name: str, suite_docstring: str | None = None) -> SuiteReport:
        """Build final suite report from collected tests."""
        passed = sum(1 for t in self.tests if t.outcome == "passed")
        failed = sum(1 for t in self.tests if t.outcome == "failed")
        skipped = sum(1 for t in self.tests if t.outcome == "skipped")
        total_duration = sum(t.duration_ms for t in self.tests)

        return SuiteReport(
            name=name,
            timestamp=datetime.now().isoformat(),
            duration_ms=total_duration,
            tests=self.tests,
            passed=passed,
            failed=failed,
            skipped=skipped,
            suite_docstring=suite_docstring,
        )
