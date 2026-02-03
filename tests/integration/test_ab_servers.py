"""A/B Server Comparison Tests.

Demonstrate comparing different MCP server implementations for the same task.
This pattern is useful for:
- Testing tool description improvements
- Comparing different API designs
- Evaluating server refactoring

The report will show side-by-side comparison of the two server versions.

Run with: pytest tests/integration/test_ab_servers.py -v --aitest-html=report.html
"""

from __future__ import annotations

import sys

import pytest

from pytest_aitest import Agent, MCPServer, Provider, Wait

from .conftest import (
    DEFAULT_MAX_TURNS,
    DEFAULT_MODEL,
    DEFAULT_RPM,
    DEFAULT_TPM,
    WEATHER_PROMPT,
)

pytestmark = [pytest.mark.integration, pytest.mark.abtest]


# =============================================================================
# Server Fixtures - Two versions of the same service
# =============================================================================


@pytest.fixture(scope="module")
def weather_server_v1():
    """Weather server version 1 - original implementation."""
    return MCPServer(
        command=[
            sys.executable,
            "-u",
            "-m",
            "pytest_aitest.testing.weather_mcp",
        ],
        wait=Wait.for_tools(["get_weather", "get_forecast", "list_cities"]),
    )


@pytest.fixture(scope="module")
def todo_server_v1():
    """Todo server version 1 - original implementation."""
    return MCPServer(
        command=[
            sys.executable,
            "-u",
            "-m",
            "pytest_aitest.testing.todo_mcp",
        ],
        wait=Wait.for_tools(["add_task", "list_tasks", "complete_task"]),
    )


# In a real scenario, you'd have a v2 server with improved tool descriptions
# For this demo, we use the same server but with different system prompts


# =============================================================================
# A/B Comparison Tests
# =============================================================================


class TestServerABComparison:
    """Compare different server configurations for the same tasks.

    This demonstrates how to A/B test:
    - Different tool description styles (verbose vs terse)
    - Different system prompt guidance
    - Different server implementations

    The report will group these by server version for easy comparison.
    """

    @pytest.mark.parametrize("server_version", ["v1-verbose", "v1-terse"])
    @pytest.mark.asyncio
    async def test_weather_simple_query(self, aitest_run, weather_server_v1, server_version):
        """Simple weather query across different prompt styles."""
        # Simulate A/B by varying system prompt (in real scenario, use different servers)
        if server_version == "v1-verbose":
            system_prompt = WEATHER_PROMPT
        else:
            system_prompt = "You help with weather. Use tools to get data."

        agent = Agent(
            name=f"weather-{server_version}",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server_v1],
            system_prompt=system_prompt,
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(agent, "What's the weather in Paris?")

        assert result.success
        assert result.tool_was_called("get_weather")

    @pytest.mark.parametrize("server_version", ["v1-verbose", "v1-terse"])
    @pytest.mark.asyncio
    async def test_weather_comparison_query(self, aitest_run, weather_server_v1, server_version):
        """City comparison across different prompt styles.

        This tests whether the prompt style affects the agent's ability
        to handle more complex queries.
        """
        if server_version == "v1-verbose":
            system_prompt = WEATHER_PROMPT
        else:
            system_prompt = "You help with weather. Use tools to get data."

        agent = Agent(
            name=f"weather-compare-{server_version}",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server_v1],
            system_prompt=system_prompt,
            max_turns=8,
        )

        result = await aitest_run(
            agent,
            "Which city is warmer right now: Tokyo or Berlin?",
        )

        assert result.success
        # Should gather weather data for comparison
        assert result.tool_was_called("get_weather") or result.tool_was_called("compare_weather")


class TestToolDescriptionImpact:
    """Test how tool description quality impacts agent performance.

    This demonstrates measuring the impact of tool description improvements.
    Better descriptions should lead to:
    - Fewer incorrect tool calls
    - Better parameter usage
    - More efficient task completion
    """

    @pytest.mark.parametrize("description_quality", ["good", "minimal"])
    @pytest.mark.asyncio
    async def test_ambiguous_query_handling(
        self, aitest_run, weather_server_v1, description_quality
    ):
        """Test how description quality affects ambiguous query handling.

        With good descriptions, the agent should:
        - Know which cities are available
        - Handle unknown cities gracefully
        - Suggest alternatives when needed

        With minimal descriptions, the agent may fail to use tools properly.
        This test captures the quality difference for the report.
        """
        if description_quality == "good":
            system_prompt = (
                "You are a weather assistant. The weather system has data for specific "
                "cities only. Use list_cities to discover available locations. "
                "If a city isn't available, suggest alternatives from the list."
            )
        else:
            system_prompt = "You get weather data."

        agent = Agent(
            name=f"ambiguous-{description_quality}",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server_v1],
            system_prompt=system_prompt,
            max_turns=8,
        )

        result = await aitest_run(
            agent,
            "What's the weather in a European city?",
        )

        assert result.success

        # Count tool usage
        tool_calls = result.tool_call_count("get_weather") + result.tool_call_count("list_cities")

        if description_quality == "good":
            # Good descriptions should lead to tool usage
            assert tool_calls >= 1, "Good descriptions should enable tool usage"
        else:
            # Minimal descriptions may or may not work - we're measuring the difference
            # This test captures the behavior for comparison in the report
            # We don't assert failure because sometimes minimal still works
            pass


class TestServerMigration:
    """Test to validate server migration/refactoring.

    When refactoring an MCP server, use this pattern to ensure
    the new implementation produces equivalent or better results.
    """

    @pytest.mark.asyncio
    async def test_todo_workflow_consistency(self, aitest_run, todo_server_v1):
        """Ensure todo workflow works consistently.

        This test could be run against v1 and v2 servers to ensure
        a migration doesn't regress functionality.
        """
        agent = Agent(
            name="todo-migration-test",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[todo_server_v1],
            system_prompt="You manage tasks. Add, complete, and list tasks as requested.",
            max_turns=10,
        )

        result = await aitest_run(
            agent,
            "Add 'buy groceries' to my shopping list, then show me all my tasks.",
        )

        assert result.success
        assert result.tool_was_called("add_task"), "Should add task"
        assert result.tool_was_called("list_tasks"), "Should list tasks"
        assert "groceries" in result.final_response.lower()
