"""Fixture generation tests for HTML report testing.

These tests generate JSON fixtures that exercise different report features.
Run them with --aitest-json to save the fixture data.

## Fixtures

| Fixture | Agents | Sessions | Purpose |
|---------|--------|----------|---------|
| 01_single_agent.json | 1 | No | Basic report, no comparison UI |
| 02_multi_agent.json | 2 | No | Leaderboard, comparison (no selector) |
| 03_multi_agent_sessions.json | 2 | Yes | Session grouping + agent comparison |
| 04_agent_selector.json | 3 | No | Agent selector (3+ agents required) |

## Generation Commands

```bash
# Fixture 01: Single agent
pytest tests/fixtures/generate_scenarios.py::TestSingleAgent -v \\
    --aitest-json=tests/fixtures/reports/01_single_agent.json

# Fixture 02: Multi-agent (2 agents)
pytest tests/fixtures/generate_scenarios.py::TestTwoAgents -v \\
    --aitest-json=tests/fixtures/reports/02_multi_agent.json

# Fixture 03: Multi-agent with sessions
pytest tests/fixtures/generate_scenarios.py::TestMultiAgentSessions -v \\
    --aitest-json=tests/fixtures/reports/03_multi_agent_sessions.json

# Fixture 04: Agent selector (3 agents)
pytest tests/fixtures/generate_scenarios.py::TestAgentSelector -v \\
    --aitest-json=tests/fixtures/reports/04_agent_selector.json
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

BANKING_PROMPT = (
    "You are a helpful banking assistant. Use tools to help users manage their accounts."
)


def _make_weather_agent(
    name: str, model: str, *, weather_server, skill=None, max_turns: int = 5
) -> Agent:
    return Agent(
        name=name,
        provider=Provider(model=f"azure/{model}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
        mcp_servers=[weather_server],
        system_prompt=WEATHER_PROMPT,
        skill=skill,
        max_turns=max_turns,
    )


def _make_banking_agent(name: str, model: str, *, banking_server) -> Agent:
    return Agent(
        name=name,
        provider=Provider(model=f"azure/{model}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
        mcp_servers=[banking_server],
        system_prompt=BANKING_PROMPT,
        max_turns=5,
    )


# =============================================================================
# Fixture 01: Single Agent
# =============================================================================


class TestSingleAgent:
    """Single agent tests - basic report without comparison UI.

    Tests pass/fail, assertions, tool calls, mermaid diagrams.
    """

    _agent: Agent | None = None

    @pytest.fixture
    def agent(self, weather_server):
        """Cached agent instance - same UUID across all tests."""
        if TestSingleAgent._agent is None:
            TestSingleAgent._agent = _make_weather_agent(
                "weather-agent",
                DEFAULT_MODEL,
                weather_server=weather_server,
            )
        return TestSingleAgent._agent

    @pytest.mark.asyncio
    async def test_simple_weather_query(self, aitest_run, agent, llm_assert):
        """Basic weather lookup - should pass."""
        result = await aitest_run(agent, "What's the weather in Paris?")
        assert result.success
        assert result.tool_was_called("get_weather")
        assert result.tool_call_arg("get_weather", "city") == "Paris"
        assert llm_assert(
            result.final_response, "mentions the temperature in Celsius or Fahrenheit"
        )
        assert result.cost_usd < 0.05

    @pytest.mark.asyncio
    async def test_forecast_query(self, aitest_run, agent, llm_assert):
        """Multi-day forecast - tests get_forecast tool."""
        result = await aitest_run(agent, "Give me a 3-day forecast for Tokyo")
        assert result.success
        assert result.tool_was_called("get_forecast")
        assert result.tool_call_arg("get_forecast", "city") == "Tokyo"
        assert llm_assert(result.final_response, "provides weather information for multiple days")

    @pytest.mark.asyncio
    async def test_city_comparison(self, aitest_run, agent, llm_assert):
        """Compare two cities - multiple tool calls."""
        agent.max_turns = 8
        result = await aitest_run(agent, "Which is warmer today, Berlin or Sydney?")
        assert result.success
        assert result.tool_call_count("get_weather") >= 2 or result.tool_was_called(
            "compare_weather"
        )
        if result.tool_was_called("compare_weather"):
            assert result.tool_call_arg("compare_weather", "city1") in {"Berlin", "Sydney"}
            assert result.tool_call_arg("compare_weather", "city2") in {"Berlin", "Sydney"}
        else:
            cities = {call.arguments.get("city") for call in result.tool_calls_for("get_weather")}
            assert {"Berlin", "Sydney"}.issubset(cities)
        assert llm_assert(result.final_response, "compares temperatures for both cities")

    @pytest.mark.asyncio
    async def test_expected_failure(self, aitest_run, agent, llm_assert):
        """Test that fails due to turn limit - for report variety."""
        agent.max_turns = 1
        result = await aitest_run(
            agent, "Get weather for Paris, Tokyo, London, Berlin, Sydney, and compare them all"
        )
        # Intentional failure to demonstrate error display in reports
        raise AssertionError(
            "Agent exceeded turn limit - unable to process request for 5 cities (max_turns=1)"
        )


# =============================================================================
# Fixture 02: Two Agents (leaderboard, no selector)
# =============================================================================


class TestTwoAgents:
    """Two agents compared side-by-side.

    Tests leaderboard and comparison view. No agent selector (requires 3+).
    Agents: gpt-5-mini, gpt-4.1-mini
    """

    _agents: dict[str, Agent] = {}

    @pytest.fixture
    def agent(self, weather_server, agent_config):
        """Cached agent - same UUID for same name across parametrized tests."""
        name = agent_config["name"]
        if name not in TestTwoAgents._agents:
            TestTwoAgents._agents[name] = _make_weather_agent(
                name,
                agent_config["model"],
                weather_server=weather_server,
                skill=agent_config["skill"],
            )
        return TestTwoAgents._agents[name]

    @pytest.fixture(
        params=[
            {"name": "gpt-5-mini", "model": DEFAULT_MODEL, "skill": None},
            {"name": "gpt-4.1-mini", "model": SECONDARY_MODEL, "skill": None},
        ],
        ids=["gpt-5-mini", "gpt-4.1-mini"],
    )
    def agent_config(self, request):
        return request.param

    @pytest.mark.asyncio
    async def test_simple_weather(self, aitest_run, agent, llm_assert):
        """Basic weather query - all agents should pass."""
        result = await aitest_run(agent, "What's the weather in London?")
        assert result.success
        assert result.tool_was_called("get_weather")
        assert result.tool_call_arg("get_weather", "city") == "London"
        assert llm_assert(result.final_response, "describes the current weather conditions")

    @pytest.mark.asyncio
    async def test_forecast(self, aitest_run, agent, llm_assert):
        """Forecast query - tests tool selection."""
        result = await aitest_run(agent, "5-day forecast for New York please")
        assert result.success
        assert result.tool_was_called("get_forecast")
        assert result.tool_call_arg("get_forecast", "city") == "New York"
        assert result.tool_call_count("get_forecast") >= 1
        assert llm_assert(result.final_response, "provides a 5-day forecast with daily conditions")
        assert result.duration_ms < 30000

    @pytest.mark.asyncio
    async def test_comparison(self, aitest_run, agent, llm_assert):
        """City comparison - multi-step reasoning."""
        agent.max_turns = 8
        result = await aitest_run(
            agent, "Compare Paris and Tokyo weather - which is better for a picnic?"
        )
        assert result.success
        assert result.tool_call_count("get_weather") >= 2 or result.tool_was_called(
            "compare_weather"
        )
        if result.tool_was_called("compare_weather"):
            assert result.tool_call_arg("compare_weather", "city1") in {"Paris", "Tokyo"}
            assert result.tool_call_arg("compare_weather", "city2") in {"Paris", "Tokyo"}
        else:
            cities = {call.arguments.get("city") for call in result.tool_calls_for("get_weather")}
            assert {"Paris", "Tokyo"}.issubset(cities)
        assert llm_assert(
            result.final_response,
            "recommends which city is better for a picnic based on weather",
        )


# =============================================================================
# Fixture 03: Multi-Agent with Sessions
# =============================================================================


@pytest.mark.session("banking-workflow")
class TestMultiAgentSessions:
    """Multi-turn banking session with 2 agents.

    Tests session grouping and agent comparison together.
    """

    _agents: dict[str, Agent] = {}

    @pytest.fixture
    def agent(self, banking_server, agent_config):
        """Cached agent - same UUID for same name across parametrized tests."""
        name = agent_config["name"]
        if name not in TestMultiAgentSessions._agents:
            TestMultiAgentSessions._agents[name] = _make_banking_agent(
                name,
                agent_config["model"],
                banking_server=banking_server,
            )
        return TestMultiAgentSessions._agents[name]

    @pytest.fixture(
        params=[
            {"name": "gpt-5-mini", "model": DEFAULT_MODEL},
            {"name": "gpt-4.1-mini", "model": SECONDARY_MODEL},
        ],
        ids=["gpt-5-mini", "gpt-4.1-mini"],
    )
    def agent_config(self, request):
        return request.param

    @pytest.mark.asyncio
    async def test_check_balance(self, aitest_run, agent, llm_assert):
        """First turn: check account balance."""
        result = await aitest_run(agent, "What's my checking account balance?")
        assert result.success
        assert result.tool_was_called("get_balance")
        assert result.tool_call_arg("get_balance", "account") == "checking"
        assert llm_assert(result.final_response, "states the checking account balance amount")

    @pytest.mark.asyncio
    async def test_transfer_funds(self, aitest_run, agent, llm_assert):
        """Second turn: transfer money."""
        result = await aitest_run(agent, "Transfer $100 from checking to savings")
        assert result.success
        assert result.tool_was_called("transfer")
        assert result.tool_call_arg("transfer", "from_account") == "checking"
        assert result.tool_call_arg("transfer", "to_account") == "savings"
        assert result.tool_call_arg("transfer", "amount") == 100
        assert result.is_session_continuation
        assert llm_assert(
            result.final_response,
            "confirms the transfer of $100 from checking to savings",
        )

    @pytest.mark.asyncio
    async def test_verify_transfer(self, aitest_run, agent, llm_assert):
        """Third turn: verify the transfer."""
        result = await aitest_run(agent, "Show me all my account balances now")
        assert result.success
        assert result.tool_was_called("get_all_balances") or result.tool_was_called("get_balance")
        assert result.is_session_continuation
        assert llm_assert(result.final_response, "shows balances for multiple accounts")


# =============================================================================
# Fixture 04: Agent Selector (3+ agents)
# =============================================================================


class TestAgentSelector:
    """Three agents for testing the agent selector UI.

    Agent selector only appears when there are 3+ agents.
    Agents: gpt-5-mini, gpt-4.1-mini, gpt-5-mini+skill
    """

    _agents: dict[str, Agent] = {}

    @pytest.fixture
    def agent(self, weather_server, agent_config):
        """Cached agent - same UUID for same name across parametrized tests."""
        name = agent_config["name"]
        if name not in TestAgentSelector._agents:
            TestAgentSelector._agents[name] = _make_weather_agent(
                name,
                agent_config["model"],
                weather_server=weather_server,
                skill=agent_config["skill"],
            )
        return TestAgentSelector._agents[name]

    @pytest.fixture(
        params=[
            {"name": "gpt-5-mini", "model": DEFAULT_MODEL, "skill": None},
            {"name": "gpt-4.1-mini", "model": SECONDARY_MODEL, "skill": None},
            {"name": "gpt-5-mini+skill", "model": DEFAULT_MODEL, "skill": WEATHER_SKILL},
        ],
        ids=["gpt-5-mini", "gpt-4.1-mini", "gpt-5-mini+skill"],
    )
    def agent_config(self, request):
        return request.param

    @pytest.mark.asyncio
    async def test_weather_query(self, aitest_run, agent, llm_assert):
        """Basic weather query - all agents should pass."""
        result = await aitest_run(agent, "What's the weather in Berlin?")
        assert result.success
        assert result.tool_was_called("get_weather")
        assert result.tool_call_arg("get_weather", "city") == "Berlin"
        assert llm_assert(
            result.final_response,
            "provides the current temperature and conditions for Berlin",
        )

    @pytest.mark.asyncio
    async def test_multi_city(self, aitest_run, agent, llm_assert):
        """Multiple cities - tests differentiation between agents."""
        agent.max_turns = 8
        result = await aitest_run(agent, "Compare weather in Rome, Madrid, and Athens")
        assert result.success
        assert result.tool_call_count("get_weather") >= 3
        assert llm_assert(result.final_response, "mentions weather for Rome, Madrid, and Athens")
