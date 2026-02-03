"""Integration tests for generating report fixtures.

These tests are designed to produce specific JSON report scenarios
that exercise different parts of the HTML reporting system.

Run individual scenarios to generate fixtures:

    # Fixture 06: With AI summary
    pytest tests/integration/test_fixture_scenarios.py::TestWithAISummary -v \
        --aitest-json=tests/fixtures/reports/06_with_ai_summary.json \
        --aitest-summary --aitest-summary-model=azure/gpt-5-mini

    # Fixture 07: With skipped tests
    pytest tests/integration/test_fixture_scenarios.py::TestWithSkipped -v \
        --aitest-json=tests/fixtures/reports/07_with_skipped.json

    # Fixture 08: Matrix with all features
    pytest tests/integration/test_fixture_scenarios.py::TestMatrixFull -v \
        --aitest-json=tests/fixtures/reports/08_matrix_full.json \
        --aitest-summary --aitest-summary-model=azure/gpt-5-mini
"""

from __future__ import annotations

import pytest

from pytest_aitest import Prompt, load_prompts
from pathlib import Path

pytestmark = [pytest.mark.integration]


# =============================================================================
# Fixture 06: With AI Summary
# =============================================================================


class TestWithAISummary:
    """Simple tests that produce a report WITH AI summary when --aitest-summary is used.
    
    This is a simple single-model scenario to test AI summary rendering.
    """

    @pytest.mark.asyncio
    async def test_weather_lookup(self, aitest_run, weather_agent_factory):
        """Basic weather query."""
        agent = weather_agent_factory("gpt-5-mini")
        result = await aitest_run(agent, "What's the weather in Paris?")
        assert result.success
        assert result.tool_was_called("get_weather")

    @pytest.mark.asyncio
    async def test_forecast_query(self, aitest_run, weather_agent_factory):
        """Multi-day forecast."""
        agent = weather_agent_factory("gpt-5-mini")
        result = await aitest_run(agent, "Give me a 3-day forecast for Tokyo")
        assert result.success
        assert result.tool_was_called("get_forecast")

    @pytest.mark.asyncio
    async def test_city_comparison(self, aitest_run, weather_agent_factory):
        """Compare two cities."""
        agent = weather_agent_factory("gpt-5-mini")
        result = await aitest_run(agent, "Which is warmer, Berlin or Sydney?")
        assert result.success

    @pytest.mark.asyncio
    async def test_expected_failure(self, aitest_run, weather_agent_factory):
        """Test that intentionally fails for report variety."""
        agent = weather_agent_factory("gpt-5-mini", max_turns=1)  # Limit turns to force failure
        result = await aitest_run(
            agent, 
            "Get weather for Paris, then Tokyo, then compare them, then give me a 5-day forecast for the colder one"
        )
        # This will likely fail due to max_turns=1
        assert result.success, "Expected to fail due to turn limit"


# =============================================================================
# Fixture 07: With Skipped Tests
# =============================================================================


class TestWithSkipped:
    """Tests including skipped ones to verify skip badge rendering."""

    @pytest.mark.asyncio
    async def test_weather_passes(self, aitest_run, weather_agent_factory):
        """Normal passing test."""
        agent = weather_agent_factory("gpt-5-mini")
        result = await aitest_run(agent, "What's the weather in London?")
        assert result.success

    @pytest.mark.asyncio
    async def test_forecast_passes(self, aitest_run, weather_agent_factory):
        """Another passing test."""
        agent = weather_agent_factory("gpt-5-mini")
        result = await aitest_run(agent, "5-day forecast for New York")
        assert result.success

    @pytest.mark.skip(reason="Feature not yet implemented")
    @pytest.mark.asyncio
    async def test_skipped_feature(self, aitest_run, weather_agent_factory):
        """Skipped test - feature pending."""
        agent = weather_agent_factory("gpt-5-mini")
        result = await aitest_run(agent, "Historical weather data")
        assert result.success

    @pytest.mark.skip(reason="Requires premium API access")
    @pytest.mark.asyncio  
    async def test_skipped_premium(self, aitest_run, weather_agent_factory):
        """Skipped test - premium only."""
        agent = weather_agent_factory("gpt-5-mini")
        result = await aitest_run(agent, "Satellite imagery")
        assert result.success

    @pytest.mark.asyncio
    async def test_compare_passes(self, aitest_run, weather_agent_factory):
        """Comparison test that passes."""
        agent = weather_agent_factory("gpt-5-mini")
        result = await aitest_run(agent, "Compare Tokyo and Paris weather")
        assert result.success

    @pytest.mark.skip(reason="Flaky on CI - investigating")
    @pytest.mark.asyncio
    async def test_skipped_flaky(self, aitest_run, weather_agent_factory):
        """Skipped test - flaky."""
        agent = weather_agent_factory("gpt-5-mini")
        result = await aitest_run(agent, "Complex multi-step operation")
        assert result.success


# =============================================================================
# Fixture 08: Matrix Full (Model × Prompt with all features)
# =============================================================================


# Load prompts for matrix
PROMPTS_DIR = Path(__file__).parent / "prompts"
PROMPTS = load_prompts(PROMPTS_DIR) if PROMPTS_DIR.exists() else []

MODELS = ["gpt-5-mini", "gpt-4.1"]


class TestMatrixFull:
    """Full matrix: 2 models × 3 prompts = 6 combinations per test.
    
    Tests include pass, fail, and skip to exercise all report features.
    Run with --aitest-summary to include AI summary.
    """

    @pytest.mark.parametrize("model", MODELS)
    @pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
    @pytest.mark.asyncio
    async def test_weather_query(self, aitest_run, weather_agent_factory, model, prompt):
        """Basic weather - should pass for all combinations."""
        agent = weather_agent_factory(model, system_prompt=prompt.system_prompt)
        result = await aitest_run(agent, "What's the weather in Paris?")
        assert result.success
        assert result.tool_was_called("get_weather")

    @pytest.mark.parametrize("model", MODELS)
    @pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
    @pytest.mark.asyncio
    async def test_forecast_interpretation(self, aitest_run, weather_agent_factory, model, prompt):
        """Forecast with interpretation - tests reasoning."""
        agent = weather_agent_factory(model, system_prompt=prompt.system_prompt)
        result = await aitest_run(
            agent, 
            "Should I bring an umbrella to London this week?"
        )
        assert result.success

    @pytest.mark.parametrize("model", MODELS)
    @pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
    @pytest.mark.asyncio
    async def test_multi_city_comparison(self, aitest_run, weather_agent_factory, model, prompt):
        """Compare cities - tests tool chaining."""
        agent = weather_agent_factory(model, system_prompt=prompt.system_prompt)
        result = await aitest_run(
            agent,
            "Compare the weather in Tokyo and Berlin, which is better for outdoor activities?"
        )
        assert result.success
