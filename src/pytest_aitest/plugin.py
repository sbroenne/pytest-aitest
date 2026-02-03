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
# Key for storing session messages for @pytest.mark.session
SESSION_MESSAGES_KEY = pytest.StashKey[dict[str, list[dict[str, Any]]]]()
# Export for use in fixtures
__all__ = ["COLLECTOR_KEY", "SESSION_MESSAGES_KEY"]


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

    # Model selection for AI summary (use the most capable model you can afford)
    group.addoption(
        "--aitest-summary-model",
        default=None,
        help=(
            "LiteLLM model for AI analysis. Required when generating reports. "
            "Use the most capable model you can afford (e.g., gpt-5.1-chat, claude-opus-4)."
        ),
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
    config.addinivalue_line(
        "markers",
        "session(name): Mark tests as part of a named session for multi-turn conversations. "
        "Tests with the same session name share conversation history automatically.",
    )

    # Always initialize report collector - JSON is always generated
    config.stash[COLLECTOR_KEY] = ReportCollector()
    # Initialize session message storage
    config.stash[SESSION_MESSAGES_KEY] = {}


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
        aitest_fixtures = {"aitest_run", "agent_factory"}
        if (aitest_fixtures & set(fixturenames)) and not any(
            m.name == "aitest" for m in item.iter_markers()
        ):
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

    # Only collect tests that actually used aitest (have an agent result)
    # This prevents unit tests from triggering AI analysis for reports
    if agent_result is None:
        return

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

    # Default paths - JSON is always generated
    default_dir = Path("aitest-reports")
    default_json_path = default_dir / "results.json"

    # Build suite report
    suite_report = collector.build_suite_report(
        name=session.name or "pytest-aitest",
    )

    generator = ReportGenerator()

    # Generate AI insights (mandatory for HTML and MD reports)
    insights = None
    if html_path or md_path:
        insights = _generate_structured_insights(config, suite_report, required=True)

    # Always generate JSON report (to default or custom path)
    json_output_path = Path(json_path) if json_path else default_json_path
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    generator.generate_json(suite_report, json_output_path, insights=insights)
    _log_report_path(config, "JSON", json_output_path)

    # Generate HTML report if requested
    if html_path:
        path = Path(html_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        generator.generate_html(suite_report, path, insights=insights)
        _log_report_path(config, "HTML", path)

    # Generate Markdown report
    if md_path:
        path = Path(md_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        generator.generate_markdown(suite_report, path, insights=insights)
        _log_report_path(config, "Markdown", path)


def _log_report_path(config: Config, format_name: str, path: Path) -> None:
    """Log report path to terminal."""
    terminalreporter: TerminalReporter | None = config.pluginmanager.get_plugin("terminalreporter")
    if terminalreporter:
        terminalreporter.write_line(f"aitest {format_name} report: {path}")


def _generate_structured_insights(
    config: Config, report: SuiteReport, *, required: bool = False
) -> Any:
    """Generate structured AI insights from test results.

    Uses the new insights generation system with structured output.
    
    Args:
        config: pytest config
        report: Suite report with test results
        required: If True, raise error when model not configured (for report generation)
    
    Returns:
        AIInsights object or None if generation fails/skipped.
        
    Raises:
        pytest.UsageError: If required=True and model not configured.
    """
    import asyncio

    try:
        from pytest_aitest.reporting.insights import generate_insights

        # Require dedicated summary model - no fallback
        model = config.getoption("--aitest-summary-model")
        if not model:
            if required:
                raise pytest.UsageError(
                    "AI analysis is required for report generation.\n"
                    "Please specify --aitest-summary-model with a capable model.\n"
                    "Example: --aitest-summary-model=azure/gpt-4.1\n"
                    "         --aitest-summary-model=openai/gpt-4o"
                )
            return None

        # Collect tool info and skill info from test results
        tool_info: list[Any] = []
        skill_info: list[Any] = []
        prompts: dict[str, str] = {}

        for test in report.tests:
            if test.agent_result:
                # Collect tools (deduplicate by name)
                seen_tools = {t.name for t in tool_info}
                for t in getattr(test.agent_result, "available_tools", []) or []:
                    if t.name not in seen_tools:
                        tool_info.append(t)
                        seen_tools.add(t.name)
                
                # Collect skills (deduplicate by name)
                skill = getattr(test.agent_result, "skill_info", None)
                if skill and skill.name not in {s.name for s in skill_info}:
                    skill_info.append(skill)
                
                # Collect effective system prompts as prompt variants
                effective_prompt = getattr(test.agent_result, "effective_system_prompt", "")
                if effective_prompt and test.metadata:
                    prompt_name = test.metadata.get("prompt", "default")
                    if prompt_name not in prompts:
                        prompts[prompt_name] = effective_prompt

        # Generate insights using async function
        async def _run() -> tuple[Any, Any]:
            return await generate_insights(
                suite_report=report,
                tool_info=tool_info,
                skill_info=skill_info,
                prompts=prompts,
                model=model,
            )

        # Use asyncio.run() instead of deprecated get_event_loop().run_until_complete()
        insights, metadata = asyncio.run(_run())

        # Log generation stats
        terminalreporter: TerminalReporter | None = config.pluginmanager.get_plugin(
            "terminalreporter"
        )
        if terminalreporter:
            tokens_str = f"{metadata.tokens_used:,}" if metadata.tokens_used else "N/A"
            cost_str = f"${metadata.cost_usd:.4f}" if metadata.cost_usd else "N/A"
            cached_str = " (cached)" if metadata.cached else ""
            terminalreporter.write_line(
                f"\nAI Insights generated{cached_str}: {tokens_str} tokens, {cost_str}"
            )

        return insights

    except pytest.UsageError:
        # Re-raise configuration errors
        raise
    except Exception as e:
        if required:
            raise pytest.UsageError(
                f"AI analysis failed (required for report generation): {e}\n"
                "Check your model configuration and credentials."
            ) from e
        terminalreporter: TerminalReporter | None = config.pluginmanager.get_plugin(
            "terminalreporter"
        )
        if terminalreporter:
            terminalreporter.write_line(f"Warning: AI insights generation failed: {e}")
        return None


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

        # Set up Azure Entra ID auth if needed
        from pytest_aitest.core.auth import get_azure_auth_kwargs

        kwargs = get_azure_auth_kwargs(model)

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
