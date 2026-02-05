"""Fixture generation tests for HTML report testing.

These tests generate JSON fixtures that exercise different report features.
Run them with --aitest-json to save the fixture data.

## Fixtures

| Fixture | Agents | Sessions | Purpose |
|---------|--------|----------|---------|
| 01_single_agent.json | 1 | No | Basic report, no comparison UI |
| 02_multi_agent.json | 3 | No | Agent selector, leaderboard, comparison |
| 03_multi_agent_sessions.json | 2 | Yes | Session grouping + agent comparison |

## Generation Commands

```bash
# Fixture 01: Single agent
pytest tests/fixtures/generate_scenarios.py::TestSingleAgent -v \\
    --aitest-json=tests/fixtures/reports/01_single_agent.json

# Fixture 02: Multi-agent (3 agents)
pytest tests/fixtures/generate_scenarios.py::TestMultiAgent -v \\
    --aitest-json=tests/fixtures/reports/02_multi_agent.json

# Fixture 03: Multi-agent with sessions
pytest tests/fixtures/generate_scenarios.py::TestMultiAgentSessions -v \\
    --aitest-json=tests/fixtures/reports/03_multi_agent_sessions.json
```
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pytest_aitest import Agent, Provider, Skill

pytestmark = [pytest.mark.integration]

# Constants
DEFAULT_MODEL = "gpt-5-mini"
SECONDARY_MODEL = "gpt-4.1-mini"
DEFAULT_RPM = 10
DEFAULT_TPM = 10000

WEATHER_PROMPT = """You are a helpful weather assistant.
Use the available tools to answer questions about weather.
Always use tools - never make up weather data."""

# Load skill for agent variation
SKILLS_DIR = Path(__file__).parent.parent / "integration" / "skills"
WEATHER_SKILL = None
if (SKILLS_DIR / "weather-expert").exists():
    WEATHER_SKILL = Skill.from_path(SKILLS_DIR / "weather-expert")


# =============================================================================
# Fixture 01: Single Agent
# =============================================================================


class TestSingleAgent:
    """Single agent tests - basic report without comparison UI.
    
    Tests pass/fail, assertions, tool calls, mermaid diagrams.
    """

    @pytest.mark.asyncio
    async def test_simple_weather_query(self, aitest_run, weather_server):
        """Basic weather lookup - should pass."""
        agent = Agent(
            name="weather-agent",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            system_prompt=WEATHER_PROMPT,
            max_turns=5,
        )
        result = await aitest_run(agent, "What's the weather in Paris?")
        assert result.success
        assert result.tool_was_called("get_weather")

    @pytest.mark.asyncio
    async def test_forecast_query(self, aitest_run, weather_server):
        """Multi-day forecast - tests get_forecast tool."""
        agent = Agent(
            name="weather-agent",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            system_prompt=WEATHER_PROMPT,
            max_turns=5,
        )
        result = await aitest_run(agent, "Give me a 3-day forecast for Tokyo")
        assert result.success
        assert result.tool_was_called("get_forecast")

    @pytest.mark.asyncio
    async def test_city_comparison(self, aitest_run, weather_server):
        """Compare two cities - multiple tool calls."""
        agent = Agent(
            name="weather-agent",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            system_prompt=WEATHER_PROMPT,
            max_turns=8,
        )
        result = await aitest_run(agent, "Which is warmer today, Berlin or Sydney?")
        assert result.success
        # Should call get_weather at least twice or use compare_weather
        assert result.tool_call_count("get_weather") >= 2 or result.tool_was_called("compare_weather")

    @pytest.mark.asyncio
    async def test_expected_failure(self, aitest_run, weather_server):
        """Test that fails due to turn limit - for report variety."""
        agent = Agent(
            name="weather-agent",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            system_prompt=WEATHER_PROMPT,
            max_turns=1,  # Force failure
        )
        result = await aitest_run(
            agent,
            "Get weather for Paris, Tokyo, London, Berlin, Sydney, and compare them all"
        )
        # This should fail due to max_turns=1
        assert result.success, "Expected to fail due to turn limit"


# =============================================================================
# Fixture 02: Multi-Agent (3 agents for selector testing)
# =============================================================================


class TestMultiAgent:
    """Three agents compared side-by-side.
    
    Tests agent selector, leaderboard, and comparison view.
    Agents: gpt-5-mini, gpt-4.1-mini, gpt-5-mini+skill
    """

    @pytest.mark.parametrize("agent_config", [
        {"name": "gpt-5-mini", "model": DEFAULT_MODEL, "skill": None},
        {"name": "gpt-4.1-mini", "model": SECONDARY_MODEL, "skill": None},
        {"name": "gpt-5-mini+skill", "model": DEFAULT_MODEL, "skill": WEATHER_SKILL},
    ], ids=["gpt-5-mini", "gpt-4.1-mini", "gpt-5-mini+skill"])
    @pytest.mark.asyncio
    async def test_simple_weather(self, aitest_run, weather_server, agent_config):
        """Basic weather query - all agents should pass."""
        agent = Agent(
            name=agent_config["name"],
            provider=Provider(model=f"azure/{agent_config['model']}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            system_prompt=WEATHER_PROMPT,
            skill=agent_config["skill"],
            max_turns=5,
        )
        result = await aitest_run(agent, "What's the weather in London?")
        assert result.success
        assert result.tool_was_called("get_weather")

    @pytest.mark.parametrize("agent_config", [
        {"name": "gpt-5-mini", "model": DEFAULT_MODEL, "skill": None},
        {"name": "gpt-4.1-mini", "model": SECONDARY_MODEL, "skill": None},
        {"name": "gpt-5-mini+skill", "model": DEFAULT_MODEL, "skill": WEATHER_SKILL},
    ], ids=["gpt-5-mini", "gpt-4.1-mini", "gpt-5-mini+skill"])
    @pytest.mark.asyncio
    async def test_forecast(self, aitest_run, weather_server, agent_config):
        """Forecast query - tests tool selection."""
        agent = Agent(
            name=agent_config["name"],
            provider=Provider(model=f"azure/{agent_config['model']}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            system_prompt=WEATHER_PROMPT,
            skill=agent_config["skill"],
            max_turns=5,
        )
        result = await aitest_run(agent, "5-day forecast for New York please")
        assert result.success
        assert result.tool_was_called("get_forecast")

    @pytest.mark.parametrize("agent_config", [
        {"name": "gpt-5-mini", "model": DEFAULT_MODEL, "skill": None},
        {"name": "gpt-4.1-mini", "model": SECONDARY_MODEL, "skill": None},
        {"name": "gpt-5-mini+skill", "model": DEFAULT_MODEL, "skill": WEATHER_SKILL},
    ], ids=["gpt-5-mini", "gpt-4.1-mini", "gpt-5-mini+skill"])
    @pytest.mark.asyncio
    async def test_comparison(self, aitest_run, weather_server, agent_config):
        """City comparison - multi-step reasoning."""
        agent = Agent(
            name=agent_config["name"],
            provider=Provider(model=f"azure/{agent_config['model']}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            system_prompt=WEATHER_PROMPT,
            skill=agent_config["skill"],
            max_turns=8,
        )
        result = await aitest_run(agent, "Compare Paris and Tokyo weather - which is better for a picnic?")
        assert result.success


# =============================================================================
# Fixture 03: Multi-Agent with Sessions
# =============================================================================


@pytest.mark.session("banking-workflow")
class TestMultiAgentSessions:
    """Multi-turn banking session with 2 agents.
    
    Tests session grouping and agent comparison together.
    """

    @pytest.mark.parametrize("agent_config", [
        {"name": "gpt-5-mini", "model": DEFAULT_MODEL},
        {"name": "gpt-4.1-mini", "model": SECONDARY_MODEL},
    ], ids=["gpt-5-mini", "gpt-4.1-mini"])
    @pytest.mark.asyncio
    async def test_check_balance(self, aitest_run, banking_server, agent_config):
        """First turn: check account balance."""
        agent = Agent(
            name=agent_config["name"],
            provider=Provider(model=f"azure/{agent_config['model']}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt="You are a helpful banking assistant. Use tools to help users manage their accounts.",
            max_turns=5,
        )
        result = await aitest_run(agent, "What's my checking account balance?")
        assert result.success
        assert result.tool_was_called("get_balance")

    @pytest.mark.parametrize("agent_config", [
        {"name": "gpt-5-mini", "model": DEFAULT_MODEL},
        {"name": "gpt-4.1-mini", "model": SECONDARY_MODEL},
    ], ids=["gpt-5-mini", "gpt-4.1-mini"])
    @pytest.mark.asyncio
    async def test_transfer_funds(self, aitest_run, banking_server, agent_config):
        """Second turn: transfer money."""
        agent = Agent(
            name=agent_config["name"],
            provider=Provider(model=f"azure/{agent_config['model']}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt="You are a helpful banking assistant. Use tools to help users manage their accounts.",
            max_turns=5,
        )
        result = await aitest_run(agent, "Transfer $100 from checking to savings")
        assert result.success
        assert result.tool_was_called("transfer")

    @pytest.mark.parametrize("agent_config", [
        {"name": "gpt-5-mini", "model": DEFAULT_MODEL},
        {"name": "gpt-4.1-mini", "model": SECONDARY_MODEL},
    ], ids=["gpt-5-mini", "gpt-4.1-mini"])
    @pytest.mark.asyncio
    async def test_verify_transfer(self, aitest_run, banking_server, agent_config):
        """Third turn: verify the transfer."""
        agent = Agent(
            name=agent_config["name"],
            provider=Provider(model=f"azure/{agent_config['model']}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt="You are a helpful banking assistant. Use tools to help users manage their accounts.",
            max_turns=5,
        )
        result = await aitest_run(agent, "Show me all my account balances now")
        assert result.success
        assert result.tool_was_called("get_all_balances") or result.tool_was_called("get_balance")
