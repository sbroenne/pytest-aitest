"""Unit tests for Agent configuration."""

from __future__ import annotations

from pytest_aitest.core.agent import Agent, MCPServer, Provider, Wait


class TestAgent:
    """Tests for Agent dataclass."""

    def test_minimal_agent(self) -> None:
        """Agent requires only provider."""
        agent = Agent(provider=Provider(model="azure/gpt-5-mini"))
        assert agent.provider.model == "azure/gpt-5-mini"
        assert agent.name is None
        assert agent.mcp_servers == []
        assert agent.cli_servers == []
        assert agent.system_prompt is None
        assert agent.max_turns == 10
        assert agent.skill is None
        assert agent.allowed_tools is None

    def test_agent_with_allowed_tools(self) -> None:
        """Agent can specify allowed_tools to filter available tools."""
        agent = Agent(
            provider=Provider(model="azure/gpt-5-mini"),
            allowed_tools=["read_cell", "write_cell"],
        )
        assert agent.allowed_tools == ["read_cell", "write_cell"]

    def test_agent_with_empty_allowed_tools(self) -> None:
        """Empty allowed_tools list means no tools available."""
        agent = Agent(
            provider=Provider(model="azure/gpt-5-mini"),
            allowed_tools=[],
        )
        assert agent.allowed_tools == []

    def test_agent_with_all_options(self) -> None:
        """Agent with all configuration options."""
        server = MCPServer(
            command=["python", "-m", "weather_server"],
            wait=Wait.for_tools(["get_weather"]),
        )
        agent = Agent(
            name="test-agent",
            provider=Provider(model="azure/gpt-5-mini", temperature=0.7),
            mcp_servers=[server],
            system_prompt="Be helpful.",
            max_turns=5,
            allowed_tools=["get_weather"],
        )
        assert agent.name == "test-agent"
        assert agent.provider.temperature == 0.7
        assert len(agent.mcp_servers) == 1
        assert agent.system_prompt == "Be helpful."
        assert agent.max_turns == 5
        assert agent.allowed_tools == ["get_weather"]


class TestProvider:
    """Tests for Provider dataclass."""

    def test_minimal_provider(self) -> None:
        """Provider requires only model."""
        provider = Provider(model="openai/gpt-4o")
        assert provider.model == "openai/gpt-4o"
        assert provider.temperature is None
        assert provider.max_tokens is None
        assert provider.rpm is None
        assert provider.tpm is None

    def test_provider_with_rate_limits(self) -> None:
        """Provider with rate limiting."""
        provider = Provider(model="azure/gpt-5-mini", rpm=10, tpm=10000)
        assert provider.rpm == 10
        assert provider.tpm == 10000


class TestMCPServer:
    """Tests for MCPServer dataclass."""

    def test_minimal_server(self) -> None:
        """MCPServer requires only command."""
        server = MCPServer(command=["python", "-m", "my_server"])
        assert server.command == ["python", "-m", "my_server"]
        assert server.args == []
        assert server.env == {}
        assert server.wait.strategy.value == "ready"
        assert server.cwd is None

    def test_server_with_wait_for_tools(self) -> None:
        """MCPServer with Wait.for_tools()."""
        server = MCPServer(
            command=["python", "-m", "weather"],
            wait=Wait.for_tools(["get_weather", "get_forecast"]),
        )
        assert server.wait.strategy.value == "tools"
        assert server.wait.tools == ("get_weather", "get_forecast")
