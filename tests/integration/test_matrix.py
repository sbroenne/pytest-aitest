"""Matrix tests - model × prompt comparison.

The most comprehensive comparison: every model with every prompt.
The report auto-detects both dimensions and shows a 2D grid.

Run with: pytest tests/integration/test_matrix.py -v --aitest-html=report.html
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pytest_aitest import Agent, Provider, load_prompts

from .conftest import BENCHMARK_MODELS, DEFAULT_RPM, DEFAULT_TPM

pytestmark = [pytest.mark.integration, pytest.mark.matrix]

# Load prompts from YAML files
PROMPTS_DIR = Path(__file__).parent / "prompts"
PROMPTS = load_prompts(PROMPTS_DIR)


class TestMatrixComparison:
    """Full model × prompt matrix.

    The report will show a 2D grid:
    - Rows = models
    - Columns = prompts
    - Cells = pass/fail + metrics
    """

    @pytest.mark.parametrize("model", BENCHMARK_MODELS)
    @pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
    @pytest.mark.asyncio
    async def test_weather_matrix(self, aitest_run, weather_server, model, prompt):
        """Weather query across all model/prompt combinations."""
        agent = Agent(
            name=f"matrix-{model}-{prompt.name}",
            provider=Provider(model=f"azure/{model}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            system_prompt=prompt.system_prompt,
            max_turns=5,
        )

        result = await aitest_run(agent, "What's the weather in Paris?")

        assert result.success
        assert result.tool_was_called("get_weather")

    @pytest.mark.parametrize("model", BENCHMARK_MODELS)
    @pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
    @pytest.mark.asyncio
    async def test_comparison_matrix(self, aitest_run, weather_server, model, prompt):
        """City comparison across all model/prompt combinations."""
        agent = Agent(
            name=f"matrix-compare-{model}-{prompt.name}",
            provider=Provider(model=f"azure/{model}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            system_prompt=prompt.system_prompt,
            max_turns=5,
        )

        result = await aitest_run(agent, "Is it warmer in Sydney or Berlin right now?")

        assert result.success
        # Response should answer the question
        assert "sydney" in result.final_response.lower()
