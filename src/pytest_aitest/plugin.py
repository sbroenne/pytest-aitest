"""pytest plugin for aitest."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from pytest_aitest.reporting import ReportCollector, ReportGenerator, TestReport

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser
    from _pytest.nodes import Item
    from _pytest.reports import TestReport as PytestTestReport
    from _pytest.terminal import TerminalReporter

    from pytest_aitest.reporting import SuiteReport


# Key for storing report collector in config
COLLECTOR_KEY = pytest.StashKey[ReportCollector]()


def pytest_addoption(parser: Parser) -> None:
    """Add pytest CLI options for aitest.

    Note: LLM authentication is handled by LiteLLM's standard environment variables:
    - Azure: AZURE_API_BASE + `az login` (Entra ID)
    - OpenAI: OPENAI_API_KEY
    - Anthropic: ANTHROPIC_API_KEY
    - etc.

    See https://docs.litellm.ai/docs/providers for full list.
    """
    group = parser.getgroup("aitest", "AI agent testing")

    # Model selection for agents
    group.addoption(
        "--aitest-model",
        default="openai/gpt-4o-mini",
        help="Default LiteLLM model for agents (default: openai/gpt-4o-mini)",
    )

    # Model selection for AI summary (use a more capable model)
    group.addoption(
        "--aitest-summary-model",
        default=None,
        help="LiteLLM model for AI summary generation. Required when using --aitest-summary. "
        "Use a capable model like gpt-4.1 or claude-sonnet-4 for quality analysis.",
    )

    # Report options
    group.addoption(
        "--aitest-html",
        metavar="PATH",
        default=None,
        help="Generate HTML report to given path (e.g., report.html)",
    )
    group.addoption(
        "--aitest-json",
        metavar="PATH",
        default=None,
        help="Generate JSON report to given path (e.g., results.json)",
    )
    group.addoption(
        "--aitest-md",
        metavar="PATH",
        default=None,
        help="Generate Markdown report to given path (e.g., report.md)",
    )
    group.addoption(
        "--aitest-summary",
        action="store_true",
        default=False,
        help="Include AI-powered analysis in HTML report",
    )

    # Rate limit options
    group.addoption(
        "--aitest-rpm",
        type=int,
        default=None,
        metavar="N",
        help="Default requests per minute limit for LLM calls (enables LiteLLM rate limiting)",
    )
    group.addoption(
        "--aitest-tpm",
        type=int,
        default=None,
        metavar="N",
        help="Default tokens per minute limit for LLM calls (enables LiteLLM rate limiting)",
    )


def pytest_configure(config: Config) -> None:
    """Configure the aitest plugin."""
    # Register markers
    config.addinivalue_line(
        "markers",
        "aitest: Mark test as an AI agent test (optional, enables filtering with -m aitest)",
    )
    config.addinivalue_line(
        "markers",
        "aitest_skip_report: Exclude this test from AI test reports",
    )

    # Initialize report collector if any reporting is enabled
    html_path = config.getoption("--aitest-html")
    json_path = config.getoption("--aitest-json")
    if html_path or json_path:
        config.stash[COLLECTOR_KEY] = ReportCollector()


def _extract_metadata_from_nodeid(nodeid: str) -> dict[str, Any]:
    """Extract model and prompt from parametrized test node ID.

    Parses test names like 'test_foo[gpt-5-mini-PROMPT_V1]' to extract:
    - model: gpt-5-mini
    - prompt: PROMPT_V1
    """
    import re

    metadata: dict[str, Any] = {}

    # Extract parameters from node ID: test_foo[param1-param2] -> "param1-param2"
    match = re.search(r"\[([^\]]+)\]", nodeid)
    if not match:
        return metadata

    params_str = match.group(1)

    # Model patterns - use negative lookahead to stop before PROMPT_
    # Note: Order matters - more specific patterns first (gpt-4o before gpt-4)
    model_patterns = [
        r"gpt-\d+(?:\.\d+)?o(?:-(?!PROMPT)\w+)*",  # gpt-4o, gpt-4o-mini
        r"gpt-\d+(?:\.\d+)?(?:-(?!PROMPT)\w+)*",  # gpt-4, gpt-4-turbo, gpt-5-mini
        r"o\d+-(?!PROMPT)\w+",  # o1-mini, o1-preview, o3-mini
        r"claude-\d+(?:\.\d+)?(?:-(?!PROMPT)\w+)*",  # claude-3-opus, claude-3.5-sonnet
        r"gemini-\d+(?:\.\d+)?(?:-(?!PROMPT)\w+)*",  # gemini-1.5-pro
        r"mistral-(?!PROMPT)\w+",  # mistral-large
        r"llama-?\d*(?:\.\d+)?(?:-(?!PROMPT)\w+)*",  # llama-3.1-70b
        r"deepseek-(?!PROMPT)\w+",  # deepseek-chat
        r"qwen-?\d*(?:\.\d+)?(?:-(?!PROMPT)\w+)*",  # qwen-2.5-72b
        r"command-r(?:-(?!PROMPT)\w+)?",  # command-r-plus
    ]
    model_pattern = re.compile("|".join(f"({p})" for p in model_patterns), re.IGNORECASE)
    model_match = model_pattern.search(params_str)
    if model_match:
        metadata["model"] = model_match.group(0)

    # Prompt patterns (from DimensionAggregator)
    prompt_patterns = [
        r"PROMPT_\w+",  # PROMPT_V1, PROMPT_CONCISE
        r"prompt_\w+",  # prompt_v1, prompt_concise
    ]
    prompt_pattern = re.compile("|".join(f"({p})" for p in prompt_patterns))
    prompt_match = prompt_pattern.search(params_str)
    if prompt_match:
        metadata["prompt"] = prompt_match.group(0)

    return metadata


def pytest_collection_modifyitems(
    session: pytest.Session,
    config: Config,
    items: list[pytest.Item],
) -> None:
    """Auto-mark tests that use aitest fixtures."""
    for item in items:
        # Check if test uses any aitest fixtures
        fixturenames = getattr(item, "fixturenames", [])
        aitest_fixtures = {"aitest_run", "judge", "agent_factory"}
        if aitest_fixtures & set(fixturenames):
            # Add aitest marker if not already present
            if not any(m.name == "aitest" for m in item.iter_markers()):
                item.add_marker(pytest.mark.aitest)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item, call: Any) -> Any:
    """Capture test results for reporting."""
    outcome = yield
    report: PytestTestReport = outcome.get_result()

    # Only process call phase (not setup/teardown)
    if report.when != "call":
        return

    # Check if reporting is enabled
    collector = item.config.stash.get(COLLECTOR_KEY, None)
    if collector is None:
        return

    # Skip if marked to exclude from report
    if any(m.name == "aitest_skip_report" for m in item.iter_markers()):
        return

    # Get agent result if available
    agent_result = getattr(item, "_aitest_result", None)

    # Get test function docstring if available
    docstring = None
    func = getattr(item, "function", None)
    if func is not None and func.__doc__:
        docstring = func.__doc__

    # Extract model and prompt from parametrized test node ID
    metadata = _extract_metadata_from_nodeid(item.nodeid)

    # Create test report
    test_report = TestReport(
        name=item.nodeid,
        outcome=report.outcome,
        duration_ms=report.duration * 1000,
        agent_result=agent_result,
        error=str(report.longrepr) if report.failed else None,
        docstring=docstring,
        metadata=metadata,
    )

    collector.add_test(test_report)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Generate reports at end of test session."""
    config = session.config
    collector = config.stash.get(COLLECTOR_KEY, None)

    if collector is None or not collector.tests:
        return

    html_path = config.getoption("--aitest-html")
    json_path = config.getoption("--aitest-json")
    md_path = config.getoption("--aitest-md")

    if not html_path and not json_path and not md_path:
        return

    # Build suite report
    suite_report = collector.build_suite_report(
        name=session.name or "pytest-aitest",
    )

    generator = ReportGenerator()

    # Generate AI summary if requested (for HTML and MD reports)
    ai_summary = None
    if (html_path or md_path) and config.getoption("--aitest-summary"):
        ai_summary = _generate_ai_summary(config, suite_report)

    # Generate HTML report
    if html_path:
        path = Path(html_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        generator.generate_html(suite_report, path, ai_summary=ai_summary)
        _log_report_path(config, "HTML", path)

    # Generate JSON report
    if json_path:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        generator.generate_json(suite_report, path)
        _log_report_path(config, "JSON", path)

    # Generate Markdown report
    if md_path:
        path = Path(md_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        generator.generate_markdown(suite_report, path, ai_summary=ai_summary)
        _log_report_path(config, "Markdown", path)


def _log_report_path(config: Config, format_name: str, path: Path) -> None:
    """Log report path to terminal."""
    terminalreporter: TerminalReporter | None = config.pluginmanager.get_plugin("terminalreporter")
    if terminalreporter:
        terminalreporter.write_line(f"aitest {format_name} report: {path}")


def _generate_ai_summary(config: Config, report: SuiteReport) -> str | None:
    """Generate AI-powered summary of test results.

    Uses the structured AI summary prompt from prompts/ai_summary.md.
    Auto-detects single-model vs multi-model evaluation context.

    Authentication is handled by LiteLLM via standard environment variables:
    - Azure: AZURE_API_BASE + `az login` (Entra ID)
    - OpenAI: OPENAI_API_KEY
    - Anthropic: ANTHROPIC_API_KEY

    Returns the summary text or None if generation fails.
    """
    import os

    try:
        import litellm

        from pytest_aitest.prompts import get_ai_summary_prompt

        # Require dedicated summary model - no fallback
        model = config.getoption("--aitest-summary-model")
        if not model:
            terminalreporter: TerminalReporter | None = config.pluginmanager.get_plugin(
                "terminalreporter"
            )
            if terminalreporter:
                terminalreporter.write_line(
                    "\nAI Summary: Skipped - --aitest-summary-model not specified."
                    "\nUse a capable model like azure/gpt-4.1 or openai/gpt-4o.",
                    yellow=True,
                )
            return None

        # Load the system prompt
        system_prompt = get_ai_summary_prompt()

        # Detect evaluation context using populated metadata
        detected_models = report.models_used
        is_multi_model = len(detected_models) > 1
        context_hint = (
            "**Context: Multi-Model Comparison** - Compare the MODELS and recommend which to use."
            if is_multi_model
            else "**Context: Single-Model Evaluation** - Assess the model's fitness for this task."
        )

        # Build test results summary using human-readable names (docstrings)
        # Include model info from metadata
        test_lines = []
        for t in report.tests:
            line = f"- {t.display_name}: {t.outcome}"
            if t.model:
                line = f"- [{t.model}] {t.display_name}: {t.outcome}"
            if t.error:
                line += f" ({t.error[:100]})"
            test_lines.append(line)
        test_summary = "\n".join(test_lines)

        # Build per-model breakdown for multi-model scenarios
        model_breakdown = ""
        if is_multi_model and report.tests:
            from collections import defaultdict

            model_stats: dict[str, dict[str, int | float]] = defaultdict(
                lambda: {"passed": 0, "failed": 0, "tokens": 0, "cost": 0.0}
            )
            for t in report.tests:
                if t.model:
                    model_stats[t.model]["passed" if t.outcome == "passed" else "failed"] += 1
                    model_stats[t.model]["tokens"] += t.tokens_used or 0
                    if t.agent_result:
                        model_stats[t.model]["cost"] += t.agent_result.cost_usd

            lines = ["**Per-Model Breakdown:**"]
            for m, stats in sorted(model_stats.items()):
                total = stats["passed"] + stats["failed"]
                rate = (stats["passed"] / total * 100) if total > 0 else 0
                cost_str = f"${stats['cost']:.4f}" if stats["cost"] > 0 else "N/A"
                lines.append(
                    f"- **{m}**: {rate:.0f}% pass ({stats['passed']}/{total}), "
                    f"{stats['tokens']:,} tokens, {cost_str}"
                )
            model_breakdown = "\n".join(lines)

        models_info = f"Models tested: {', '.join(detected_models)}" if detected_models else ""
        prompts_info = (
            f"Prompts tested: {', '.join(report.prompts_used)}" if report.prompts_used else ""
        )
        files_info = f"Test files: {', '.join(report.test_files)}" if report.test_files else ""

        user_content = f"""{context_hint}

**Test Suite:** {report.name}
**Pass Rate:** {report.pass_rate:.1f}% ({report.passed}/{report.total} tests passed)
**Duration:** {report.duration_ms / 1000:.1f}s total
**Tokens Used:** {report.total_tokens:,} tokens
**Tool Calls:** {report.tool_call_count} total
{models_info}
{prompts_info}
{files_info}
{model_breakdown}

**Test Results:**
{test_summary}
"""

        # Build proper system/user messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        # Set up Azure Entra ID auth if needed (no API key in env)
        kwargs: dict = {}
        if model.startswith("azure/") and not os.environ.get("AZURE_API_KEY"):
            try:
                from litellm.secret_managers.get_azure_ad_token_provider import (
                    get_azure_ad_token_provider,
                )

                kwargs["azure_ad_token_provider"] = get_azure_ad_token_provider()
            except (ImportError, Exception):
                pass  # Fall through to let litellm handle auth

        response = litellm.completion(
            model=model,
            messages=messages,
            **kwargs,
        )

        return response.choices[0].message.content or ""  # type: ignore[union-attr]
    except Exception as e:
        terminalreporter: TerminalReporter | None = config.pluginmanager.get_plugin(
            "terminalreporter"
        )
        if terminalreporter:
            terminalreporter.write_line(f"Warning: AI summary generation failed: {e}")
        return None


# Register fixtures from fixtures module
pytest_plugins = ["pytest_aitest.fixtures"]
