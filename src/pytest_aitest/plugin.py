"""pytest plugin for aitest."""

from __future__ import annotations

from datetime import datetime
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


class _RecordingLLMAssert:
    """Wrapper that records LLM assertions for report rendering."""

    def __init__(self, inner: Any, store: list[dict[str, Any]]) -> None:
        self._inner = inner
        self._store = store

    def __call__(self, content: str, criterion: str) -> Any:
        result = self._inner(content, criterion)
        self._store.append(
            {
                "type": "llm",
                "passed": bool(result),
                "message": result.criterion,
                "details": result.reasoning,
            }
        )
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem: Item) -> Any:
    """Wrap llm_assert fixture values before test function execution."""
    llm_assert = getattr(pyfuncitem, "funcargs", {}).get("llm_assert")
    if llm_assert is not None and not isinstance(llm_assert, _RecordingLLMAssert):
        store = getattr(pyfuncitem, "_aitest_assertions", None)
        if store is None:
            store = []
            pyfuncitem._aitest_assertions = store  # type: ignore[attr-defined]

        pyfuncitem.funcargs["llm_assert"] = _RecordingLLMAssert(llm_assert, store)

    yield


def _get_timestamped_path(base_name: str, test_name: str = None, default_dir: Path = None) -> Path:
    """Generate timestamped filename for unique report names.
    
    Args:
        base_name: Base filename with extension (e.g., 'results.json', 'report.html')
        test_name: Name of the test/suite to include in filename
        default_dir: Directory to store the file (default: 'aitest-reports')
    
    Returns:
        Path with format: {dir}/{prefix}_{test_name}_{ISO8601-timestamp}.{ext}
    """
    if default_dir is None:
        default_dir = Path("aitest-reports")
    
    # Use ISO8601 timestamp: YYYY-MM-DDTHH-MM-SS (seconds precision, : replaced with -)
    timestamp = datetime.now().isoformat(timespec="seconds").replace(":", "-")
    
    # Sanitize test name (remove paths, lowercase, replace spaces/special chars)
    if test_name:
        # Remove file extensions and paths
        safe_name = test_name.split("/")[-1].split(".")[0].lower().replace(" ", "-").replace("_", "-")
    else:
        safe_name = None
    
    # Split filename and extension
    if "." in base_name:
        name_part, ext = base_name.rsplit(".", 1)
        if safe_name:
            filename = f"{name_part}_{safe_name}_{timestamp}.{ext}"
        else:
            filename = f"{name_part}_{timestamp}.{ext}"
    else:
        if safe_name:
            filename = f"{base_name}_{safe_name}_{timestamp}"
        else:
            filename = f"{base_name}_{timestamp}"
    
    return default_dir / filename


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

    # Build metadata from agent_result (source of truth) with fallback to parsing
    metadata = _extract_metadata_from_nodeid(item.nodeid)
    
    # Override with actual values from agent_result if available
    if agent_result:
        if agent_result.agent_name:
            metadata["agent_name"] = agent_result.agent_name
        if agent_result.model:
            metadata["model"] = agent_result.model
        if agent_result.skill_info:
            metadata["skill"] = agent_result.skill_info.name

    # Extract assertions recorded by the llm_assert fixture
    assertions = getattr(item, "_aitest_assertions", [])

    # Capture error message - extract just the assertion error, not the whole traceback
    error_msg = None
    if report.failed:
        error_text = str(report.longrepr)
        
        # Try to extract just the AssertionError line (starts with "E       ")
        error_lines = error_text.split("\n")
        assertion_lines = [line for line in error_lines if line.strip().startswith("E ")]
        
        if assertion_lines:
            # Found assertion lines - use those (without the "E       " prefix)
            error_msg = "\n".join(line.strip()[2:] for line in assertion_lines)
        else:
            # Fallback: truncate full traceback
            if len(error_text) > 300:
                error_msg = error_text[:300] + "\n... (see full traceback in test output)"
            else:
                error_msg = error_text

    # Create test report
    test_report = TestReport(
        name=item.nodeid,
        outcome=report.outcome,
        duration_ms=report.duration * 1000,
        agent_result=agent_result,
        error=error_msg,
        assertions=assertions,
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

    # Extract suite docstring from first test's parent class/module
    suite_docstring = None
    if session.items:
        first_item = session.items[0]
        # Try to get docstring from test class first
        if hasattr(first_item, 'parent') and first_item.parent:
            parent = first_item.parent
            # Check if parent is a class
            if hasattr(parent, 'obj') and parent.obj and hasattr(parent.obj, '__doc__'):
                suite_docstring = parent.obj.__doc__
                if suite_docstring:
                    # Get first line only
                    suite_docstring = suite_docstring.strip().split('\n')[0].strip()

    # Build suite report first (to get the test name for default filenames)
    default_dir = Path("aitest-reports")
    suite_report = collector.build_suite_report(
        name=session.name or "pytest-aitest",
        suite_docstring=suite_docstring,
    )

    # Generate default paths with test name included
    default_json_path = _get_timestamped_path("results.json", test_name=suite_report.name, default_dir=default_dir)
    default_html_path = _get_timestamped_path("report.html", test_name=suite_report.name, default_dir=default_dir)

    generator = ReportGenerator()

    # Generate AI insights if HTML report requested OR summary model specified
    summary_model = config.getoption("--aitest-summary-model")
    insights = None
    if html_path or summary_model:
        insights = _generate_structured_insights(config, suite_report, required=bool(html_path))

    # Always generate JSON report (to default or custom path)
    json_output_path = Path(json_path) if json_path else default_json_path
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    generator.generate_json(suite_report, json_output_path, insights=insights)
    _log_report_path(config, "JSON", json_output_path)

    # Generate HTML report (use default timestamped name if not specified)
    html_output_path = Path(html_path) if html_path else default_html_path
    html_output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate AI insights if HTML requested (even if using default path)
    if insights is None:
        insights = _generate_structured_insights(config, suite_report, required=True)
    
    generator.generate_html(suite_report, html_output_path, insights=insights)
    _log_report_path(config, "HTML", html_output_path)


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
        markdown_summary, metadata = asyncio.run(_run())

        # Log generation stats
        terminalreporter: TerminalReporter | None = config.pluginmanager.get_plugin(
            "terminalreporter"
        )
        if terminalreporter:
            tokens_used = metadata.get("tokens_used") if isinstance(metadata, dict) else metadata.tokens_used
            cost_usd = metadata.get("cost_usd") if isinstance(metadata, dict) else metadata.cost_usd
            cached = metadata.get("cached") if isinstance(metadata, dict) else metadata.cached
            
            tokens_str = f"{tokens_used:,}" if tokens_used else "N/A"
            cost_str = f"${cost_usd:.4f}" if cost_usd else "N/A"
            cached_str = " (cached)" if cached else ""
            terminalreporter.write_line(
                f"\nAI Insights generated{cached_str}: {tokens_str} tokens, {cost_str}"
            )

        # Return dict with both summary and metadata
        return {
            "markdown_summary": markdown_summary,
            "cost_usd": metadata.get("cost_usd") if isinstance(metadata, dict) else getattr(metadata, "cost_usd", None),
            "tokens_used": metadata.get("tokens_used") if isinstance(metadata, dict) else getattr(metadata, "tokens_used", None),
            "cached": metadata.get("cached") if isinstance(metadata, dict) else getattr(metadata, "cached", False),
        }

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


# Register fixtures from fixtures module
pytest_plugins = ["pytest_aitest.fixtures"]
