"""GitHub Copilot Coding Agent server tests.

These tests demonstrate how to use GitHub Copilot Coding Agent as a system under test,
similar to MCP servers. The tests verify that the Copilot agent can be wrapped and
tested as a tool provider.

NOTE: These tests require github-copilot-sdk to be installed and the GitHub Copilot CLI
to be authenticated. Install with:
    pip install github-copilot-sdk
    gh copilot auth

Run with: pytest tests/integration/test_copilot_server.py -v
"""

from __future__ import annotations

import pytest

from pytest_aitest import Agent, GitHubCopilotServer, Provider

from .conftest import DEFAULT_MAX_TURNS, DEFAULT_MODEL, DEFAULT_RPM, DEFAULT_TPM

pytestmark = [pytest.mark.integration, pytest.mark.copilot]


@pytest.fixture
def copilot_server():
    """GitHub Copilot server fixture."""
    return GitHubCopilotServer(
        name="copilot-assistant",
        model="gpt-4.1",
        instructions="You are a helpful coding assistant. Be concise and accurate.",
    )


@pytest.mark.skipif(
    True,  # Skip by default since github-copilot-sdk may not be installed
    reason="github-copilot-sdk not available or gh copilot not authenticated",
)
class TestGitHubCopilotServer:
    """Tests for GitHub Copilot Coding Agent as a system under test."""

    @pytest.mark.asyncio
    async def test_basic_code_generation(self, aitest_run, copilot_server):
        """Test basic code generation using Copilot agent.

        This tests:
        - Copilot server initialization
        - Basic tool call to copilot_assistant_execute
        - Response handling
        """
        agent = Agent(
            name="copilot-test",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            copilot_servers=[copilot_server],
            system_prompt="You have access to a GitHub Copilot coding assistant. "
            "Use it to help with coding tasks.",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "Use the Copilot assistant to write a Python function that calculates "
            "the factorial of a number.",
        )

        assert result.success
        assert result.tool_was_called("copilot_assistant_execute")
        assert "def" in result.final_response.lower() or "factorial" in result.final_response.lower()

    @pytest.mark.asyncio
    async def test_copilot_with_custom_instructions(self, aitest_run):
        """Test Copilot with custom instructions."""
        copilot_server = GitHubCopilotServer(
            name="copilot-expert",
            model="gpt-4.1",
            instructions="Focus on code quality, add type hints, and include docstrings.",
        )

        agent = Agent(
            name="copilot-expert-test",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            copilot_servers=[copilot_server],
            system_prompt="You have access to a code quality expert Copilot. "
            "Use it for high-quality code generation.",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "Use the Copilot expert to create a well-documented class for a binary search tree.",
        )

        assert result.success
        assert result.tool_was_called("copilot_expert_execute")

    @pytest.mark.asyncio
    async def test_multiple_copilot_calls(self, aitest_run, copilot_server):
        """Test multiple sequential calls to Copilot.

        This tests:
        - Multiple tool calls to the same Copilot server
        - Context preservation across calls
        """
        agent = Agent(
            name="multi-copilot",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            copilot_servers=[copilot_server],
            system_prompt="Use Copilot to help with multi-step coding tasks.",
            max_turns=10,
        )

        result = await aitest_run(
            agent,
            "First, use Copilot to create a simple class. "
            "Then, use Copilot again to add unit tests for that class.",
        )

        assert result.success
        # Should call Copilot at least twice
        copilot_calls = [
            call for call in result.all_tool_calls if call.name == "copilot_assistant_execute"
        ]
        assert len(copilot_calls) >= 2


class TestCopilotServerDocumentation:
    """Documentation-only tests showing Copilot server usage patterns.

    These tests demonstrate the API without requiring actual execution.
    """

    def test_copilot_server_configuration(self):
        """Document various ways to configure a Copilot server."""
        # Basic configuration
        basic = GitHubCopilotServer(
            name="copilot-basic",
            model="gpt-4.1",
        )
        assert basic.name == "copilot-basic"
        assert basic.model == "gpt-4.1"

        # With custom instructions
        with_instructions = GitHubCopilotServer(
            name="copilot-expert",
            model="claude-sonnet-4.5",
            instructions="Focus on code quality and best practices.",
        )
        assert with_instructions.instructions is not None

        # With skills
        with_skills = GitHubCopilotServer(
            name="copilot-pr-analyzer",
            model="gpt-4.1",
            skill_directories=["./.copilot_skills/pr-analyzer"],
        )
        assert len(with_skills.skill_directories) == 1

    def test_agent_with_multiple_server_types(self):
        """Document using Copilot alongside MCP and CLI servers."""
        from pytest_aitest import CLIServer, MCPServer

        # Agent can use all three server types together
        agent = Agent(
            name="hybrid-agent",
            provider=Provider(model="azure/gpt-5-mini"),
            mcp_servers=[
                MCPServer(command=["npx", "-y", "@modelcontextprotocol/server-filesystem"])
            ],
            cli_servers=[CLIServer(name="git", command="git")],
            copilot_servers=[GitHubCopilotServer(name="copilot", model="gpt-4.1")],
            system_prompt="You have access to filesystem tools, git, and a Copilot assistant.",
        )

        assert len(agent.mcp_servers) == 1
        assert len(agent.cli_servers) == 1
        assert len(agent.copilot_servers) == 1
