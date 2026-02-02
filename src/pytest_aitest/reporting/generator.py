"""Report generation with composable renderers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from pytest_aitest.reporting.aggregator import (
    DimensionAggregator,
    ReportMode,
    SessionGroup,
)

if TYPE_CHECKING:
    from pytest_aitest.core.result import AgentResult
    from pytest_aitest.reporting.collector import SuiteReport, TestReport


def _render_markdown(text: str) -> Markup:
    """Convert markdown to HTML, sanitized for safe output."""
    try:
        import markdown

        html = markdown.markdown(text, extensions=["extra"])
        return Markup(html)
    except ImportError:
        # Fallback: basic line break handling if markdown not installed
        import html

        escaped = html.escape(text)
        return Markup(escaped.replace("\n", "<br>"))


def get_provider(model_name: str) -> str:
    """Extract provider name from model string for badge styling."""
    model_lower = model_name.lower()
    if "azure" in model_lower:
        return "azure"
    elif "openai" in model_lower or model_lower.startswith("gpt"):
        return "openai"
    elif "anthropic" in model_lower or "claude" in model_lower:
        return "anthropic"
    elif "vertex" in model_lower or "gemini" in model_lower:
        return "vertex"
    return "default"


def _sanitize_mermaid_text(text: str, limit: int) -> str:
    cleaned = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    cleaned = cleaned.replace('"', "'")
    cleaned = " ".join(cleaned.split())
    return cleaned[:limit]


def _to_file_url(path: str) -> str:
    return Path(path).resolve().as_uri()


def generate_mermaid_sequence_pydantic(result: Any) -> str:
    """Generate Mermaid sequence diagram from Pydantic AgentResult.
    
    Works with pytest_aitest.models.AgentResult (Pydantic model).
    """
    if result is None:
        return ""
    
    lines = [
        "sequenceDiagram",
        "    participant User",
        "    participant Agent",
        "    participant Tools",
        "",
    ]

    for turn in result.turns:
        role = turn.role.value if hasattr(turn.role, 'value') else str(turn.role)
        
        if role == "user":
            content = _sanitize_mermaid_text(turn.content, 80)
            lines.append(f'    User->>Agent: "{content}"')

        elif role == "assistant":
            if turn.tool_calls:
                for tc in turn.tool_calls:
                    args_preview = _sanitize_mermaid_text(str(tc.arguments), 60)
                    lines.append(f'    Agent->>Tools: "{tc.name}({args_preview})"')
                    if tc.error:
                        err_preview = _sanitize_mermaid_text(str(tc.error), 60)
                        lines.append(f'    Tools--xAgent: "Error: {err_preview}"')
                    elif tc.result:
                        result_preview = _sanitize_mermaid_text(tc.result, 60)
                        lines.append(f'    Tools-->>Agent: "{result_preview}"')
            else:
                content = _sanitize_mermaid_text(turn.content, 80)
                lines.append(f'    Agent->>User: "{content}"')

    return "\n".join(lines)


class ReportGenerator:
    """Generates HTML and JSON reports with smart layout selection.

    Automatically chooses the best report layout based on detected test dimensions:
    - Simple: Standard test list
    - Model comparison: Side-by-side model comparison table
    - Prompt comparison: Prompt variant comparison
    - Matrix: 2D grid of models x prompts

    Example:
        generator = ReportGenerator()
        generator.generate_html(suite_report, "report.html")
        generator.generate_json(suite_report, "report.json")
    """

    def __init__(self) -> None:
        # Use importlib.resources to find templates directory reliably
        import importlib.resources as resources

        templates_dir = resources.files("pytest_aitest").joinpath("templates")
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True,
        )
        self._env.filters["markdown"] = _render_markdown
        self._aggregator = DimensionAggregator()

    def generate_html(
        self,
        report: SuiteReport,
        output_path: str | Path,
        *,
        ai_summary: str | None = None,
    ) -> None:
        """Generate HTML report with adaptive layout.

        Args:
            report: Test suite report data (legacy dataclass)
            output_path: Path to write HTML file
            ai_summary: Optional LLM-generated summary to include
        """
        from pytest_aitest.models.converter import convert_suite_report
        
        # Convert legacy dataclass to Pydantic model for template
        pydantic_report = convert_suite_report(report, ai_summary=ai_summary)
        
        # Get mode from dimensions
        mode = pydantic_report.mode.value if pydantic_report.mode else "simple"
        
        # Build adaptive flags
        flags = self._build_adaptive_flags(pydantic_report)
        
        # Prepare context - Pydantic models only!
        context: dict[str, Any] = {
            "report": pydantic_report,
            "flags": flags,
            "mode": mode,
            "format_cost": self._format_cost,
            "generate_mermaid": generate_mermaid_sequence_pydantic,
            "get_provider": get_provider,
            "to_file_url": _to_file_url,
        }

        # Add grouped data based on mode
        if mode in ("model_comparison", "matrix"):
            context["model_groups"] = self._build_model_rankings(pydantic_report)
        if mode in ("prompt_comparison", "matrix"):
            context["prompt_groups"] = self._build_prompt_rankings(pydantic_report)
        if mode == "matrix":
            context["matrix"] = self._build_matrix(pydantic_report)

        # Add comparison views (available in any comparison mode)
        if flags["show_tool_comparison"]:
            context["tool_comparison"] = self._build_tool_comparison(pydantic_report)
        if flags["show_side_by_side"]:
            context["side_by_side_tests"] = self._build_side_by_side(pydantic_report)
        if flags["show_sessions"]:
            context["session_groups"] = self._build_session_groups(pydantic_report)

        template = self._env.get_template("report_v2.html")
        html = template.render(**context)
        Path(output_path).write_text(html, encoding="utf-8")
    
    def _build_adaptive_flags(self, report: Any) -> dict[str, Any]:
        """Build adaptive display flags from Pydantic report."""
        dims = report.dimensions
        models = dims.models if dims else []
        prompts = dims.prompts if dims else []
        
        has_tool_calls = any(
            test.agent_result and test.agent_result.tools_called
            for test in report.tests
        )
        has_sessions = any(
            test.agent_result and (test.agent_result.session_context_count or 0) > 0
            for test in report.tests
        )
        
        return {
            # Display flags
            "show_model_leaderboard": len(models) >= 2,
            "show_prompt_comparison": len(prompts) >= 2,
            "show_matrix": len(models) >= 2 and len(prompts) >= 2,
            "show_tool_comparison": (len(models) >= 2 or len(prompts) >= 2) and has_tool_calls,
            "show_side_by_side": len(models) >= 2 and len(prompts) >= 2,
            "show_sessions": has_sessions,
            "show_ai_summary": report.ai_summary is not None,
            "has_failures": report.summary.failed > 0,
            "has_skipped": report.summary.skipped > 0,
            # Counts for header badges
            "model_count": len(models),
            "prompt_count": len(prompts),
            "single_model_name": models[0] if len(models) == 1 else None,
            "single_prompt_name": prompts[0] if len(prompts) == 1 else None,
        }
    
    def _build_model_rankings(self, report: Any) -> list[dict[str, Any]]:
        """Build model rankings for leaderboard.
        
        Returns list of dicts with structure matching template expectations:
        - dimension_value: model name
        - medal: 🥇, 🥈, 🥉 or None
        - rank: numeric rank (1, 2, 3...)
        - passed, failed, total: counts
        - pass_rate: percentage (0-100)
        - total_tokens: sum of all tokens
        - efficiency: tokens per successful test (or inf)
        - total_cost: USD cost
        - avg_duration_ms: average duration in ms
        """
        from collections import defaultdict
        
        models = report.dimensions.models if report.dimensions else []
        if len(models) < 2:
            return []
        
        stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "passed": 0, "failed": 0, "total": 0, "tokens": 0, "cost": 0.0, "duration": 0.0
        })
        
        for test in report.tests:
            model = test.metadata.model if test.metadata else None
            if not model:
                continue
            s = stats[model]
            s["total"] += 1
            if test.outcome.value == "passed":
                s["passed"] += 1
            elif test.outcome.value == "failed":
                s["failed"] += 1
            if test.agent_result:
                s["tokens"] += test.agent_result.total_tokens
                s["cost"] += test.agent_result.cost_usd
            s["duration"] += test.duration_ms
        
        rankings = []
        for model, s in stats.items():
            pass_rate = (s["passed"] / s["total"] * 100) if s["total"] > 0 else 0
            efficiency = s["tokens"] / s["passed"] if s["passed"] > 0 else float("inf")
            rankings.append({
                "dimension_value": model,  # Template expects this name
                "passed": s["passed"],
                "failed": s["failed"],
                "total": s["total"],
                "pass_rate": pass_rate,
                "total_tokens": s["tokens"],  # Template expects total_tokens
                "total_cost": s["cost"],  # Template expects total_cost
                "efficiency": efficiency,
                "avg_duration_ms": s["duration"] / s["total"] if s["total"] > 0 else 0,
            })
        
        # Sort by pass rate desc, then by name
        rankings.sort(key=lambda x: (-x["pass_rate"], x["dimension_value"]))
        
        # Add rank and medal
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, r in enumerate(rankings, 1):
            r["rank"] = i
            r["medal"] = medals.get(i)
        
        return rankings
    
    def _build_prompt_rankings(self, report: Any) -> list[dict[str, Any]]:
        """Build prompt rankings for comparison.
        
        Returns list of dicts with structure matching template expectations:
        - dimension_value: prompt name
        - medal: 🥇, 🥈, 🥉 or None
        - rank: numeric rank
        - passed, failed, total: counts
        - pass_rate: percentage (0-100)
        - total_tokens: sum of all tokens
        - avg_duration_ms: average duration in ms
        """
        from collections import defaultdict
        
        prompts = report.dimensions.prompts if report.dimensions else []
        if len(prompts) < 2:
            return []
        
        stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "passed": 0, "failed": 0, "total": 0, "tokens": 0, "cost": 0.0, "duration": 0.0
        })
        
        for test in report.tests:
            prompt = test.metadata.prompt if test.metadata else None
            if not prompt:
                continue
            s = stats[prompt]
            s["total"] += 1
            if test.outcome.value == "passed":
                s["passed"] += 1
            elif test.outcome.value == "failed":
                s["failed"] += 1
            if test.agent_result:
                s["tokens"] += test.agent_result.total_tokens
                s["cost"] += test.agent_result.cost_usd
            s["duration"] += test.duration_ms
        
        rankings = []
        for prompt, s in stats.items():
            pass_rate = (s["passed"] / s["total"] * 100) if s["total"] > 0 else 0
            rankings.append({
                "dimension_value": prompt,  # Template expects this
                "passed": s["passed"],
                "failed": s["failed"],
                "total": s["total"],
                "pass_rate": pass_rate,
                "total_tokens": s["tokens"],  # Template expects total_tokens
                "avg_duration_ms": s["duration"] / s["total"] if s["total"] > 0 else 0,
            })
        
        rankings.sort(key=lambda x: (-x["pass_rate"], x["dimension_value"]))
        
        # Add rank and medal
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, r in enumerate(rankings, 1):
            r["rank"] = i
            r["medal"] = medals.get(i)
        
        return rankings
    
    def _build_matrix(self, report: Any) -> dict[str, Any]:
        """Build model × prompt matrix."""
        dims = report.dimensions
        models = dims.models if dims else []
        prompts = dims.prompts if dims else []
        
        # Build lookup: (model, prompt) -> test
        cells: dict[tuple[str, str], Any] = {}
        for test in report.tests:
            model = test.metadata.model if test.metadata else None
            prompt = test.metadata.prompt if test.metadata else None
            if model and prompt:
                cells[(model, prompt)] = test
        
        return {
            "models": models,
            "prompts": prompts,
            "cells": cells,
        }
    
    def _build_tool_comparison(self, report: Any) -> dict[str, Any]:
        """Build tool usage comparison grid.
        
        Returns dict with structure matching template expectations:
        - columns: list of column headers (model names or prompt names)
        - tools: list of {name, counts, total} dicts
        - column_totals: list of totals per column
        - grand_total: overall total
        """
        dims = report.dimensions
        models = dims.models if dims else []
        prompts = dims.prompts if dims else []
        
        # Determine comparison dimension
        if len(models) >= 2:
            columns = models
            dimension = "model"
        elif len(prompts) >= 2:
            columns = prompts
            dimension = "prompt"
        else:
            return {"columns": [], "tools": [], "column_totals": [], "grand_total": 0}
        
        # Collect all unique tools and build usage matrix
        usage: dict[str, dict[str, int]] = {col: {} for col in columns}
        all_tools: set[str] = set()
        
        for test in report.tests:
            if dimension == "model":
                key = test.metadata.model if test.metadata else None
            else:
                key = test.metadata.prompt if test.metadata else None
            
            if key and test.agent_result and test.agent_result.tools_called:
                for tool in test.agent_result.tools_called:
                    all_tools.add(tool)
                    usage[key][tool] = usage[key].get(tool, 0) + 1
        
        # Build tools list with counts per column
        tools = []
        for tool_name in sorted(all_tools):
            counts = [usage[col].get(tool_name, 0) for col in columns]
            tools.append({
                "name": tool_name,
                "counts": counts,
                "total": sum(counts),
            })
        
        # Calculate column totals
        column_totals = [
            sum(usage[col].get(tool, 0) for tool in all_tools)
            for col in columns
        ]
        
        return {
            "columns": columns,
            "tools": tools,
            "column_totals": column_totals,
            "grand_total": sum(column_totals),
        }
    
    def _build_side_by_side(self, report: Any) -> list[dict[str, Any]]:
        """Build side-by-side comparison data for tests."""
        from collections import defaultdict
        
        # Group tests by base name (without model/prompt params)
        groups: dict[str, list[Any]] = defaultdict(list)
        for test in report.tests:
            # Extract base name: test_foo[model-prompt] -> test_foo
            base_name = test.name.split("[")[0].split("::")[-1]
            groups[base_name].append(test)
        
        # Only include groups with multiple variants
        result = []
        for base_name, tests in groups.items():
            if len(tests) >= 2:
                variants = []
                for test in tests:
                    model = test.metadata.model if test.metadata else "unknown"
                    prompt = test.metadata.prompt if test.metadata else None
                    label = f"{model}"
                    if prompt:
                        label += f" / {prompt}"
                    
                    total_tokens = 0
                    tool_count = 0
                    if test.agent_result is not None:
                        total_tokens = test.agent_result.total_tokens
                        tool_count = len(test.agent_result.tools_called or [])
                    
                    variants.append({
                        "label": label,
                        "test": test,
                        "outcome": test.outcome.value,
                        "duration_ms": test.duration_ms,
                        "tokens": total_tokens,
                        "tool_count": tool_count,
                    })
                result.append({"base_name": base_name, "variants": variants})
        
        return result
    
    def _build_session_groups(self, report: Any) -> list[dict[str, Any]]:
        """Build session groups for session flow visualization."""
        from collections import defaultdict
        
        # Group tests by session (class name)
        sessions: dict[str, list[Any]] = defaultdict(list)
        for test in report.tests:
            # Extract class name from test name
            parts = test.name.split("::")
            if len(parts) >= 2:
                session = parts[-2]  # Class name
            else:
                session = "default"
            sessions[session].append(test)
        
        # Only include sessions with context continuation
        result = []
        for session_name, tests in sessions.items():
            has_continuation = any(
                t.agent_result and (t.agent_result.session_context_count or 0) > 0
                for t in tests
            )
            if has_continuation:
                result.append({
                    "name": session_name,
                    "tests": tests,
                })
        
        return result

    def generate_json(
        self,
        report: SuiteReport,
        output_path: str | Path,
        *,
        ai_summary: str | None = None,
    ) -> None:
        """Generate JSON report using Pydantic schema.

        Args:
            report: Test suite report data
            output_path: Path to write JSON file
            ai_summary: Optional AI-generated summary to include
        """
        from pytest_aitest.models.converter import convert_suite_report
        
        pydantic_report = convert_suite_report(report, ai_summary=ai_summary)
        json_str = pydantic_report.model_dump_json(indent=2, exclude_none=True)
        Path(output_path).write_text(json_str, encoding="utf-8")

    def generate_markdown(
        self,
        report: SuiteReport,
        output_path: str | Path,
        *,
        ai_summary: str | None = None,
    ) -> None:
        """Generate Markdown report.

        Produces GitHub-flavored markdown with:
        - Summary section with pass rate, tokens, duration
        - Model/prompt comparison tables
        - Test results list with status indicators
        - Collapsible sections for test details (using <details> tags)
        """
        dimensions = self._aggregator.detect_dimensions(report)
        lines: list[str] = []

        # Header
        lines.append(f"# {report.name}")
        lines.append("")
        lines.append(f"**Generated:** {report.timestamp}")
        lines.append(f"**Duration:** {report.duration_ms / 1000:.2f}s")
        lines.append("")

        # Summary section
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| **Total Tests** | {report.total} |")
        lines.append(f"| **Passed** | {report.passed} ✅ |")
        lines.append(f"| **Failed** | {report.failed} ❌ |")
        if report.skipped > 0:
            lines.append(f"| **Skipped** | {report.skipped} ⏭️ |")
        lines.append(f"| **Pass Rate** | {report.pass_rate:.1f}% |")
        if report.total_tokens > 0:
            lines.append(f"| **Total Tokens** | {report.total_tokens:,} |")
        if report.total_cost_usd > 0:
            lines.append(f"| **Est. Cost** | {self._format_cost(report.total_cost_usd)} |")
        lines.append("")

        # AI Summary (if provided)
        if ai_summary:
            lines.append("## AI Analysis")
            lines.append("")
            lines.append(ai_summary)
            lines.append("")

        # Model comparison (if multi-model)
        if dimensions.mode == ReportMode.MODEL_COMPARISON or dimensions.mode == ReportMode.MATRIX:
            model_groups = self._aggregator.group_by_model(report)
            if model_groups:
                lines.append("## Model Comparison")
                lines.append("")
                lines.append("| Model | Pass Rate | Passed | Failed | Tokens | Cost |")
                lines.append("|-------|-----------|--------|--------|--------|------|")
                for group in sorted(model_groups, key=lambda g: -g.pass_rate):
                    cost_str = self._format_cost(group.total_cost)
                    lines.append(
                        f"| {group.dimension_value} | {group.pass_rate:.0f}% | "
                        f"{group.passed} | {group.failed} | {group.total_tokens:,} | {cost_str} |"
                    )
                lines.append("")

        # Prompt comparison (if multi-prompt)
        if dimensions.mode == ReportMode.PROMPT_COMPARISON or dimensions.mode == ReportMode.MATRIX:
            prompt_groups = self._aggregator.group_by_prompt(report)
            if prompt_groups:
                lines.append("## Prompt Comparison")
                lines.append("")
                lines.append("| Prompt | Pass Rate | Passed | Failed | Tokens |")
                lines.append("|--------|-----------|--------|--------|--------|")
                for group in sorted(prompt_groups, key=lambda g: -g.pass_rate):
                    lines.append(
                        f"| {group.dimension_value} | {group.pass_rate:.0f}% | "
                        f"{group.passed} | {group.failed} | {group.total_tokens:,} |"
                    )
                lines.append("")

        # Test Results
        lines.append("## Test Results")
        lines.append("")

        for test in report.tests:
            status = "✅" if test.is_passed else "❌" if test.is_failed else "⏭️"
            lines.append(f"### {status} {test.display_name}")
            lines.append("")

            # Test metadata
            lines.append(f"- **Status:** {test.outcome}")
            lines.append(f"- **Duration:** {test.duration_ms / 1000:.2f}s")
            if test.model:
                lines.append(f"- **Model:** {test.model}")

            if test.agent_result:
                result = test.agent_result
                tokens = result.token_usage.get("prompt", 0) + result.token_usage.get(
                    "completion", 0
                )
                if tokens > 0:
                    lines.append(f"- **Tokens:** {tokens:,}")
                if result.cost_usd > 0:
                    lines.append(f"- **Cost:** {self._format_cost(result.cost_usd)}")
                if result.all_tool_calls:
                    tool_names = ", ".join(f"`{tc.name}`" for tc in result.all_tool_calls)
                    lines.append(f"- **Tools:** {tool_names}")

            lines.append("")

            # Error details (if failed)
            if test.error:
                lines.append("<details>")
                lines.append("<summary>Error Details</summary>")
                lines.append("")
                lines.append("```")
                lines.append(test.error[:500])  # Truncate long errors
                lines.append("```")
                lines.append("</details>")
                lines.append("")

            # Final response (collapsible)
            if test.agent_result and test.agent_result.final_response:
                lines.append("<details>")
                lines.append("<summary>Agent Response</summary>")
                lines.append("")
                lines.append(test.agent_result.final_response)
                lines.append("")
                lines.append("</details>")
                lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Generated by [pytest-aitest](https://github.com/sbroenne/pytest-aitest)*")

        # Write to file
        Path(output_path).write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _format_cost(cost: float) -> str:
        """Format cost in USD."""
        if cost == 0:
            return "N/A"
        if cost < 0.01:
            return f"${cost:.6f}"
        return f"${cost:.4f}"

    def _serialize_report(self, report: SuiteReport) -> dict[str, Any]:
        """Serialize report to dict for JSON."""
        dimensions = self._aggregator.detect_dimensions(report)

        data: dict[str, Any] = {
            "name": report.name,
            "timestamp": report.timestamp,
            "duration_ms": report.duration_ms,
            "mode": dimensions.mode.name.lower(),
            "dimensions": {
                "models": dimensions.models,
                "prompts": dimensions.prompts,
                "base_tests": dimensions.base_tests,
            },
            "summary": {
                "total": report.total,
                "passed": report.passed,
                "failed": report.failed,
                "skipped": report.skipped,
                "pass_rate": report.pass_rate,
                "total_tokens": report.total_tokens,
                "total_cost_usd": report.total_cost_usd,
                "token_stats": report.token_stats,
                "cost_stats": report.cost_stats,
            },
            "tests": [self._serialize_test(t) for t in report.tests],
        }

        # Add comparison data if applicable
        if dimensions.mode == ReportMode.MODEL_COMPARISON:
            data["model_comparison"] = [
                {
                    "model": g.dimension_value,
                    "pass_rate": g.pass_rate,
                    "passed": g.passed,
                    "failed": g.failed,
                    "total_tokens": g.total_tokens,
                    "total_cost": g.total_cost,
                }
                for g in self._aggregator.group_by_model(report)
            ]
        elif dimensions.mode == ReportMode.PROMPT_COMPARISON:
            data["prompt_comparison"] = [
                {
                    "prompt": g.dimension_value,
                    "pass_rate": g.pass_rate,
                    "passed": g.passed,
                    "failed": g.failed,
                }
                for g in self._aggregator.group_by_prompt(report)
            ]
        elif dimensions.mode == ReportMode.MATRIX:
            matrix = self._aggregator.build_matrix(report, dimensions)
            data["matrix"] = [
                [
                    {
                        "model": cell.model,
                        "prompt": cell.prompt,
                        "outcome": cell.outcome,
                        "passed": cell.passed,
                    }
                    for cell in row
                ]
                for row in matrix
            ]

        return data

    def _serialize_test(self, test: TestReport) -> dict[str, Any]:
        """Serialize test report to dict."""
        data: dict[str, Any] = {
            "name": test.name,
            "outcome": test.outcome,
            "duration_ms": test.duration_ms,
            "metadata": test.metadata,
        }

        if test.docstring:
            data["docstring"] = test.docstring

        if test.error:
            data["error"] = test.error

        if test.agent_result:
            data["agent_result"] = self._serialize_agent_result(test.agent_result)

        if test.assertions:
            data["assertions"] = test.assertions

        return data

    def _serialize_agent_result(self, result: AgentResult) -> dict[str, Any]:
        """Serialize AgentResult to dict."""
        return {
            "success": result.success,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "token_usage": result.token_usage,
            "cost_usd": result.cost_usd,
            "turns": [
                {
                    "role": t.role,
                    "content": t.content,
                    "tool_calls": [
                        {
                            "name": tc.name,
                            "arguments": tc.arguments,
                            "result": tc.result,
                            "error": tc.error,
                        }
                        for tc in t.tool_calls
                    ],
                }
                for t in result.turns
            ],
            "final_response": result.final_response,
            "tools_called": list(result.tool_names_called),
        }


def generate_mermaid_sequence(result: AgentResult) -> str:
    """Generate Mermaid sequence diagram from agent result.

    Example output:
        sequenceDiagram
            participant User
            participant Agent
            participant Tools

            User->>Agent: Hello!
            Agent->>Tools: read_file(path="/tmp/test.txt")
            Tools-->>Agent: File contents...
            Agent->>User: Here is the file...
    """
    lines = [
        "sequenceDiagram",
        "    participant User",
        "    participant Agent",
        "    participant Tools",
        "",
    ]

    for turn in result.turns:
        if turn.role == "user":
            content = _sanitize_mermaid_text(turn.content, 80)
            lines.append(f'    User->>Agent: "{content}"')

        elif turn.role == "assistant":
            if turn.tool_calls:
                for tc in turn.tool_calls:
                    args_preview = _sanitize_mermaid_text(str(tc.arguments), 60)
                    lines.append(f'    Agent->>Tools: "{tc.name}({args_preview})"')
                    if tc.error:
                        err_preview = _sanitize_mermaid_text(str(tc.error), 60)
                        lines.append(f'    Tools--xAgent: "Error: {err_preview}"')
                    elif tc.result:
                        result_preview = _sanitize_mermaid_text(tc.result, 60)
                        lines.append(f'    Tools-->>Agent: "{result_preview}"')
            else:
                content = _sanitize_mermaid_text(turn.content, 80)
                lines.append(f'    Agent->>User: "{content}"')

    return "\n".join(lines)


def generate_session_mermaid(session: SessionGroup) -> str:
    """Generate Mermaid sequence diagram showing session workflow.

    Shows how tests in a session build on each other's conversation context.

    Example output:
        sequenceDiagram
            participant Test1 as test_step1
            participant Test2 as test_step2
            participant Agent

            Test1->>Agent: Initial prompt
            Agent-->>Test1: Response (3 tool calls)
            Note over Test1,Test2: Context: 4 messages
            Test2->>Agent: Follow-up prompt
            Agent-->>Test2: Response (2 tool calls)
    """
    if not session.tests:
        return ""

    lines = ["sequenceDiagram"]

    # Add participants for each test
    for i, test in enumerate(session.tests):
        test_name = test.name.split("::")[-1]
        lines.append(f"    participant T{i} as {test_name}")
    lines.append("    participant Agent")
    lines.append("")

    # Show flow between tests
    for i, test in enumerate(session.tests):
        result = test.agent_result
        if not result:
            continue

        # Get prompt (first user message in this test's turns)
        prompt = "..."
        for turn in result.turns:
            if turn.role == "user":
                prompt = _sanitize_mermaid_text(turn.content, 50)
                break

        # Test sends prompt to agent
        lines.append(f'    T{i}->>Agent: "{prompt}"')

        # Agent responds
        tool_count = len(result.all_tool_calls)
        if tool_count > 0:
            lines.append(f"    Agent-->>T{i}: Response ({tool_count} tool calls)")
        else:
            lines.append(f"    Agent-->>T{i}: Response")

        # Show context carried to next test
        if i < len(session.tests) - 1:
            ctx_count = result.session_context_count if result else 0
            msg_count = len(result.messages) if result else 0
            delta = msg_count - ctx_count
            lines.append(f"    Note over T{i},T{i + 1}: +{delta} msgs → {msg_count} total")

    return "\n".join(lines)
