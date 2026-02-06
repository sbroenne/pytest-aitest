"""CLI for regenerating reports from JSON data.

Usage:
    pytest-aitest-report results.json --html report.html
    pytest-aitest-report results.json --md report.md
    pytest-aitest-report results.json --html report.html --summary --summary-model azure/gpt-4.1

Configuration (in order of precedence):
    1. CLI arguments (highest)
    2. Environment variables: AITEST_SUMMARY_MODEL
    3. pyproject.toml [tool.pytest-aitest-report] section (lowest)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from pytest_aitest.core.result import AgentResult, ToolCall, Turn
from pytest_aitest.reporting.collector import SuiteReport as LegacySuiteReport
from pytest_aitest.reporting.collector import TestReport as LegacyTestReport
from pytest_aitest.reporting.generator import ReportGenerator

_logger = logging.getLogger(__name__)


def load_config_from_pyproject() -> dict[str, Any]:
    """Load configuration from pyproject.toml [tool.pytest-aitest-report] section.

    Searches for pyproject.toml in current directory and parents.
    Returns empty dict if not found or section doesn't exist.
    """
    try:
        import tomllib
    except ImportError:
        # Python < 3.11 fallback
        try:
            import tomli as tomllib  # type: ignore[import-not-found]
        except ImportError:
            return {}

    # Search for pyproject.toml
    current = Path.cwd()
    for parent in [current, *current.parents]:
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            try:
                data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
                return data.get("tool", {}).get("pytest-aitest-report", {})
            except Exception:
                _logger.warning("Failed to parse pyproject.toml", exc_info=True)
                return {}
    return {}


def get_config_value(key: str, cli_value: Any, env_var: str) -> Any:
    """Get config value with precedence: CLI > env var > pyproject.toml."""
    # CLI takes highest precedence
    if cli_value is not None:
        return cli_value

    # Then environment variable
    env_value = os.environ.get(env_var)
    if env_value:
        return env_value

    # Finally pyproject.toml
    config = load_config_from_pyproject()
    return config.get(key)


def load_suite_report(
    json_path: Path,
) -> tuple[LegacySuiteReport, str | None, dict[str, Any] | str | None]:
    """Load SuiteReport from JSON file.

    Supports both v2.0 Pydantic schema and legacy formats.

    Returns:
        Tuple of (SuiteReport, ai_summary string, insights dict or markdown string)
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))

    # Check for v2.0+ schema (current is 3.0)
    schema_version = data.get("schema_version")
    if schema_version and schema_version >= "2.0":
        return _load_v2_report(data)

    # Fall back to legacy format
    return _load_legacy_report(data)


def _load_v2_report(
    data: dict[str, Any],
) -> tuple[LegacySuiteReport, str | None, dict[str, Any] | str | None]:
    """Load report from v2.0 schema format (current format with dataclasses).

    Returns:
        Tuple of (LegacySuiteReport, ai_summary string, insights dict or string)
    """
    # Load the SuiteReport from our current dataclass format
    from pytest_aitest.core.serialization import deserialize_suite_report

    # Deserialize the report from dict format
    suite_report = deserialize_suite_report(data)

    # Get insights - can be dict (new format) or string (legacy)
    insights = data.get("insights")
    ai_summary = None
    if insights:
        if isinstance(insights, str):
            # Legacy format - insights is just markdown string
            ai_summary = insights
        elif isinstance(insights, dict) and insights.get("markdown_summary"):
            # New format - insights is dict with markdown_summary and cost_usd
            ai_summary = insights.get("markdown_summary")
            # Keep insights as dict (don't extract just the string)

    # deserialize_suite_report returns fully reconstructed SuiteReport with typed fields
    return suite_report, ai_summary, insights


def _load_legacy_report(
    data: dict[str, Any],
) -> tuple[LegacySuiteReport, str | None, dict[str, Any] | str | None]:
    """Load report from legacy format (pre-v2.0).

    Returns:
        Tuple of (LegacySuiteReport, ai_summary string, insights markdown string)
    """
    # Extract AI summary if present
    ai_summary = data.get("ai_summary")

    # Check for insights - a plain markdown string
    insights = data.get("insights")
    if insights and isinstance(insights, str):
        ai_summary = ai_summary or insights

    # Deserialize tests
    tests = [_deserialize_test(t) for t in data.get("tests", [])]

    # Create SuiteReport
    report = LegacySuiteReport(
        name=data.get("name", "pytest-aitest"),
        timestamp=data.get("timestamp", ""),
        duration_ms=data.get("duration_ms", 0.0),
        tests=tests,
        passed=data.get("summary", {}).get("passed", data.get("passed", 0)),
        failed=data.get("summary", {}).get("failed", data.get("failed", 0)),
        skipped=data.get("summary", {}).get("skipped", data.get("skipped", 0)),
    )

    return report, ai_summary, insights


def _deserialize_test(data: dict[str, Any]) -> LegacyTestReport:
    """Deserialize test from JSON dict."""
    agent_result = None
    if "agent_result" in data:
        agent_result = _deserialize_agent_result(data["agent_result"])

    # Read identity from typed fields
    agent_id = data.get("agent_id", "")
    agent_name = data.get("agent_name", "")
    model = data.get("model", "")
    system_prompt_name = data.get("system_prompt_name")
    skill_name = data.get("skill_name")

    return LegacyTestReport(
        name=data.get("name", ""),
        outcome=data.get("outcome", "unknown"),
        duration_ms=data.get("duration_ms", 0.0),
        agent_result=agent_result,
        error=data.get("error"),
        assertions=data.get("assertions", []),
        docstring=data.get("docstring"),
        agent_id=agent_id,
        agent_name=agent_name,
        model=model,
        system_prompt_name=system_prompt_name,
        skill_name=skill_name,
    )


def _deserialize_agent_result(data: dict[str, Any]) -> AgentResult:
    """Deserialize AgentResult from JSON dict."""
    turns = [_deserialize_turn(t) for t in data.get("turns", [])]

    return AgentResult(
        turns=turns,
        success=data.get("success", False),
        error=data.get("error"),
        duration_ms=data.get("duration_ms", 0.0),
        token_usage=data.get("token_usage", {}),
        cost_usd=data.get("cost_usd", 0.0),
    )


def _deserialize_turn(data: dict[str, Any]) -> Turn:
    """Deserialize Turn from JSON dict."""
    tool_calls = [_deserialize_tool_call(tc) for tc in data.get("tool_calls", [])]

    return Turn(
        role=data.get("role", "user"),
        content=data.get("content", ""),
        tool_calls=tool_calls,
    )


def _deserialize_tool_call(data: dict[str, Any]) -> ToolCall:
    """Deserialize ToolCall from JSON dict."""
    return ToolCall(
        name=data.get("name", ""),
        arguments=data.get("arguments", {}),
        result=data.get("result"),
        error=data.get("error"),
        duration_ms=data.get("duration_ms"),
    )


def generate_ai_summary(report: LegacySuiteReport, model: str) -> str:
    """Generate AI summary for the report.

    NOTE: This is a legacy wrapper. The new approach uses structured AIInsights.
    This function generates a markdown summary for backward compatibility with
    CLI regeneration.

    Args:
        report: The suite report to summarize
        model: LiteLLM model string (e.g., azure/gpt-4.1)

    Returns:
        Generated summary text (markdown)
    """
    import asyncio

    from pytest_aitest.reporting.insights import generate_insights

    # Convert legacy report to minimal format for insights
    # Note: We don't have full tool/skill info in CLI context
    async def _run():
        insights, _metadata = await generate_insights(
            suite_report=report,
            tool_info=[],
            skill_info=[],
            prompts={},
            model=model,
        )
        return insights

    insights = asyncio.run(_run())

    # Return the markdown summary (insights is already a string)
    return insights if insights else ""


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pytest-aitest-report",
        description="Regenerate reports from pytest-aitest JSON data",
    )

    parser.add_argument(
        "json_file",
        type=Path,
        help="Path to JSON results file (e.g., aitest-reports/results.json)",
    )

    parser.add_argument(
        "--html",
        metavar="PATH",
        type=Path,
        help="Generate HTML report to given path",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate AI-powered summary (requires --summary-model)",
    )

    parser.add_argument(
        "--summary-model",
        metavar="MODEL",
        help="LiteLLM model for AI summary (e.g., azure/gpt-4.1, openai/gpt-4o). "
        "Can also be set via AITEST_SUMMARY_MODEL env var or pyproject.toml.",
    )

    args = parser.parse_args(argv)

    # Resolve summary-model with config precedence
    summary_model = get_config_value("summary-model", args.summary_model, "AITEST_SUMMARY_MODEL")

    # Validate arguments
    if not args.json_file.exists():
        print(f"Error: JSON file not found: {args.json_file}", file=sys.stderr)
        return 1

    if not args.html:
        print("Error: --html is required to generate HTML report", file=sys.stderr)
        return 1

    if args.summary and not summary_model:
        print("Error: --summary requires --summary-model to be specified", file=sys.stderr)
        print("Options:", file=sys.stderr)
        print("  --summary-model azure/gpt-4.1", file=sys.stderr)
        print("  AITEST_SUMMARY_MODEL=azure/gpt-4.1", file=sys.stderr)
        print(
            "  pyproject.toml: [tool.pytest-aitest-report] summary-model = 'azure/gpt-4.1'",
            file=sys.stderr,
        )
        return 1

    # Load report from JSON
    try:
        report, existing_summary, existing_insights = load_suite_report(args.json_file)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error: Failed to parse JSON file: {e}", file=sys.stderr)
        return 1

    # Generate AI summary if requested
    ai_summary = existing_summary
    insights = existing_insights
    if args.summary:
        print(f"Generating AI summary with {summary_model}...")
        try:
            ai_summary = generate_ai_summary(report, summary_model)
            # For new reports generated via CLI, create insights from summary
            # Create insights dict if we have ai_summary
            insights = {"markdown_summary": ai_summary} if ai_summary else None
            print("AI summary generated successfully.")
        except Exception as e:
            print(f"Warning: Failed to generate AI summary: {e}", file=sys.stderr)
            ai_summary = existing_summary

    # Generate reports
    generator = ReportGenerator()

    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        generator.generate_html(report, args.html, insights=insights)
        print(f"HTML report: {args.html}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
