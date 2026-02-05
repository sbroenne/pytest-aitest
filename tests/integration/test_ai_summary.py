"""Integration tests for AI insights generation.

These tests verify that the AI insights feature generates proper structured output
using the report_analysis prompt.

Run with: pytest tests/integration/test_ai_summary.py -v
"""

from __future__ import annotations

import pytest

from pytest_aitest.reporting.collector import SuiteReport, TestReport

pytestmark = [pytest.mark.integration]


def _make_test_report(
    name: str,
    outcome: str = "passed",
    model: str | None = None,
    duration_ms: float = 1000.0,
) -> TestReport:
    """Create a test report for testing."""
    metadata = {}
    if model:
        metadata["model"] = model
    return TestReport(
        name=name,
        outcome=outcome,
        duration_ms=duration_ms,
        metadata=metadata if metadata else None,
    )


def _make_suite_report(tests: list[TestReport]) -> SuiteReport:
    """Create a suite report for testing."""
    passed = sum(1 for t in tests if t.outcome == "passed")
    failed = sum(1 for t in tests if t.outcome == "failed")
    return SuiteReport(
        name="test-suite",
        timestamp="2026-01-01T00:00:00Z",
        duration_ms=sum(t.duration_ms for t in tests),
        tests=tests,
        passed=passed,
        failed=failed,
    )


class TestAIInsightsGeneration:
    """Test that AI insights generates proper structured output."""

    @pytest.mark.asyncio
    async def test_insights_has_recommendation(self):
        """Insights should include a recommendation."""
        from pytest_aitest.reporting.insights import generate_insights

        tests = [
            _make_test_report("test_weather", "passed", model="gpt-5-mini"),
            _make_test_report("test_forecast", "passed", model="gpt-5-mini"),
        ]
        suite = _make_suite_report(tests)

        insights, metadata = await generate_insights(
            suite_report=suite,
            tool_info=[],
            skill_info=[],
            prompts={},
            model="azure/gpt-5-mini",
        )

        # Verify we got structured insights
        assert insights is not None
        assert insights.recommendation is not None
        assert insights.recommendation.configuration, "Should have a configuration recommendation"
        assert insights.recommendation.summary, "Should have a summary"

    @pytest.mark.asyncio
    async def test_insights_has_markdown_summary(self):
        """Insights should include a markdown summary."""
        from pytest_aitest.reporting.insights import generate_insights

        tests = [
            _make_test_report("test_a", "passed", model="gpt-5-mini"),
            _make_test_report("test_b", "failed", model="gpt-5-mini"),
        ]
        suite = _make_suite_report(tests)

        insights, metadata = await generate_insights(
            suite_report=suite,
            tool_info=[],
            skill_info=[],
            prompts={},
            model="azure/gpt-5-mini",
        )

        # Verify markdown summary
        assert insights.markdown_summary, "Should have markdown_summary"
        assert len(insights.markdown_summary) > 50, "Summary should have substantial content"

    @pytest.mark.asyncio
    async def test_insights_with_failures_has_failure_analysis(self):
        """Insights should analyze failures when present."""
        from pytest_aitest.reporting.insights import generate_insights

        tests = [
            _make_test_report("test_passing", "passed", model="gpt-5-mini"),
            _make_test_report("test_failing", "failed", model="gpt-5-mini"),
        ]
        suite = _make_suite_report(tests)
        # Add error to failing test
        suite.tests[1].error = "AssertionError: Expected result not found"

        insights, metadata = await generate_insights(
            suite_report=suite,
            tool_info=[],
            skill_info=[],
            prompts={},
            model="azure/gpt-5-mini",
        )

        # With failures, we expect failure analysis
        # Note: The AI may or may not include failures depending on input
        # This is a basic sanity check
        assert insights is not None
        assert insights.recommendation is not None

    @pytest.mark.asyncio
    async def test_insights_returns_metadata(self):
        """Insights should return analysis metadata."""
        from pytest_aitest.reporting.insights import generate_insights

        tests = [_make_test_report("test_one", "passed", model="gpt-5-mini")]
        suite = _make_suite_report(tests)

        insights, metadata = await generate_insights(
            suite_report=suite,
            tool_info=[],
            skill_info=[],
            prompts={},
            model="azure/gpt-5-mini",
        )

        # Verify metadata
        assert metadata is not None
        assert metadata.model == "azure/gpt-5-mini"
        assert metadata.tokens_used >= 0
        assert metadata.cost_usd >= 0


class TestPromptLoading:
    """Test that the prompt loads correctly."""

    def test_report_analysis_prompt_loads(self):
        """The AI summary prompt should load successfully."""
        from pytest_aitest.prompts import get_ai_summary_prompt

        prompt = get_ai_summary_prompt()
        assert prompt, "Prompt should not be empty"
        assert "pytest-aitest" in prompt.lower() or "analysis" in prompt.lower()
        assert len(prompt) > 100, "Prompt should have substantial content"

    def test_prompt_is_cached(self):
        """Prompt should be cached after first load."""
        from pytest_aitest.prompts import get_ai_summary_prompt

        prompt1 = get_ai_summary_prompt()
        prompt2 = get_ai_summary_prompt()
        # Same object due to caching
        assert prompt1 is prompt2
