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
import os
import sys
from pathlib import Path
from typing import Any

from pytest_aitest.reporting.collector import SuiteReport, TestReport
from pytest_aitest.reporting.generator import ReportGenerator
from pytest_aitest.result import AgentResult, ToolCall, Turn


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


def load_suite_report(json_path: Path) -> tuple[SuiteReport, str | None]:
    """Load SuiteReport from JSON file.

    Returns:
        Tuple of (SuiteReport, ai_summary or None)
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))

    # Extract AI summary if present
    ai_summary = data.get("ai_summary")

    # Deserialize tests
    tests = [_deserialize_test(t) for t in data.get("tests", [])]

    # Create SuiteReport
    report = SuiteReport(
        name=data.get("name", "pytest-aitest"),
        timestamp=data.get("timestamp", ""),
        duration_ms=data.get("duration_ms", 0.0),
        tests=tests,
        passed=data.get("summary", {}).get("passed", 0),
        failed=data.get("summary", {}).get("failed", 0),
        skipped=data.get("summary", {}).get("skipped", 0),
    )

    return report, ai_summary


def _deserialize_test(data: dict[str, Any]) -> TestReport:
    """Deserialize test from JSON dict."""
    agent_result = None
    if "agent_result" in data:
        agent_result = _deserialize_agent_result(data["agent_result"])

    return TestReport(
        name=data.get("name", ""),
        outcome=data.get("outcome", "unknown"),
        duration_ms=data.get("duration_ms", 0.0),
        agent_result=agent_result,
        error=data.get("error"),
        assertions=data.get("assertions", []),
        metadata=data.get("metadata", {}),
        docstring=data.get("docstring"),
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
    )


def generate_ai_summary(report: SuiteReport, model: str) -> str:
    """Generate AI summary for the report.

    Args:
        report: The suite report to summarize
        model: LiteLLM model string (e.g., azure/gpt-4.1)

    Returns:
        Generated summary text
    """
    import litellm

    from pytest_aitest.prompts import get_ai_summary_prompt

    # Load the system prompt
    system_prompt = get_ai_summary_prompt()

    # Detect evaluation context
    detected_models = report.models_used
    is_multi_model = len(detected_models) > 1
    context_hint = (
        "**Context: Multi-Model Comparison** - Compare the MODELS and recommend which to use."
        if is_multi_model
        else "**Context: Single-Model Evaluation** - Assess the model's fitness for this task."
    )

    # Build test results summary
    test_lines = []
    for t in report.tests:
        line = f"- {t.display_name}: {t.outcome}"
        if t.model:
            line = f"- [{t.model}] {t.display_name}: {t.outcome}"
        if t.error:
            line += f" ({t.error[:100]})"
        test_lines.append(line)
    test_summary = "\n".join(test_lines)

    # Create user message
    user_message = f"""
{context_hint}

## Test Suite Results
- **Total Tests**: {report.total}
- **Passed**: {report.passed}
- **Failed**: {report.failed}
- **Pass Rate**: {report.pass_rate:.1f}%
{f"- **Models Tested**: {', '.join(detected_models)}" if detected_models else ""}

## Individual Test Results
{test_summary}

Please provide a concise analysis following the template in your instructions.
"""

    # Call LLM
    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content or ""  # type: ignore[union-attr]


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
        "--md",
        metavar="PATH",
        type=Path,
        help="Generate Markdown report to given path",
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

    if not args.html and not args.md:
        print("Error: At least one output format required (--html or --md)", file=sys.stderr)
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
        report, existing_summary = load_suite_report(args.json_file)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error: Failed to parse JSON file: {e}", file=sys.stderr)
        return 1

    # Generate AI summary if requested
    ai_summary = existing_summary
    if args.summary:
        print(f"Generating AI summary with {summary_model}...")
        try:
            ai_summary = generate_ai_summary(report, summary_model)
            print("AI summary generated successfully.")
        except Exception as e:
            print(f"Warning: Failed to generate AI summary: {e}", file=sys.stderr)
            ai_summary = existing_summary

    # Generate reports
    generator = ReportGenerator()

    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        generator.generate_html(report, args.html, ai_summary=ai_summary)
        print(f"HTML report: {args.html}")

    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        generator.generate_markdown(report, args.md, ai_summary=ai_summary)
        print(f"Markdown report: {args.md}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
