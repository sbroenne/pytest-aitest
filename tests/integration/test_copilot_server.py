"""GitHub Copilot Coding Agent server tests.

These tests demonstrate how to use GitHub Copilot Coding Agent as a system under test,
similar to MCP servers. Includes A/B testing of custom instructions and model comparison.

NOTE: These tests require github-copilot-sdk to be installed and the GitHub Copilot CLI
to be authenticated. Install with:
    uv add pytest-aitest[copilot]
    gh copilot auth

Run with:
    # Run all tests (will skip if SDK not available)
    pytest tests/integration/test_copilot_server.py -v
    
    # Generate comparison report
    pytest tests/integration/test_copilot_server.py -v --aitest-html=copilot_report.html

Cost: ~$0.05 for full suite (uses outer agent only, Copilot calls are free with subscription)
"""

from __future__ import annotations

import pytest

from pytest_aitest import Agent, GitHubCopilotServer, Provider

from .conftest import DEFAULT_MAX_TURNS, DEFAULT_MODEL, DEFAULT_RPM, DEFAULT_TPM

pytestmark = [pytest.mark.integration, pytest.mark.copilot]


# =============================================================================
# Helper to check if Copilot SDK is available
# =============================================================================


def _copilot_sdk_available() -> bool:
    """Check if github-copilot-sdk is installed."""
    try:
        import copilot  # noqa: F401

        return True
    except ImportError:
        return False


# =============================================================================
# Custom Instructions for A/B Testing
# =============================================================================

# Instruction Set A: Code Quality Focus
QUALITY_FOCUSED_INSTRUCTIONS = """You are a senior software engineer focused on code quality.

Guidelines:
- Always include type hints for function parameters and return values
- Write comprehensive docstrings in Google style
- Add error handling and input validation
- Follow PEP 8 style conventions
- Include usage examples in docstrings when helpful
- Prefer clarity over cleverness"""

# Instruction Set B: Performance Focus
PERFORMANCE_FOCUSED_INSTRUCTIONS = """You are a performance-oriented software engineer.

Guidelines:
- Optimize for speed and memory efficiency
- Use appropriate data structures for the task
- Include time/space complexity in comments
- Consider algorithmic efficiency
- Add benchmarking comments where relevant
- Prefer built-in functions and standard library"""

# Instruction Set C: Beginner-Friendly
BEGINNER_FRIENDLY_INSTRUCTIONS = """You are a patient coding mentor writing code for beginners.

Guidelines:
- Write simple, easy-to-understand code
- Add explanatory comments for non-obvious logic
- Use descriptive variable names
- Break complex operations into smaller steps
- Avoid advanced Python features
- Include examples showing how to use the code"""

# Instructions for comparison
INSTRUCTION_SETS = {
    "quality": QUALITY_FOCUSED_INSTRUCTIONS,
    "performance": PERFORMANCE_FOCUSED_INSTRUCTIONS,
    "beginner": BEGINNER_FRIENDLY_INSTRUCTIONS,
}

# Models for comparison
COPILOT_MODELS = ["gpt-4.1", "gpt-4o-mini"]


# =============================================================================
# A/B Testing: Custom Instructions Comparison
# =============================================================================


@pytest.mark.skipif(
    not _copilot_sdk_available(),
    reason="github-copilot-sdk not available",
)
class TestCopilotInstructionComparison:
    """A/B test different custom instructions with Copilot.

    This demonstrates comparing different instruction sets to see which
    produces better results for a given task. The report will show
    side-by-side comparison of the three instruction variants.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "instruction_name,instructions",
        INSTRUCTION_SETS.items(),
        ids=INSTRUCTION_SETS.keys(),
    )
    async def test_binary_search_tree_with_different_instructions(
        self, aitest_run, instruction_name: str, instructions: str
    ):
        """Generate a binary search tree class with different instruction sets.

        This test runs 3 times (once per instruction set) to compare:
        - quality-focused: Should produce well-documented, type-hinted code
        - performance-focused: Should emphasize efficiency and complexity
        - beginner-friendly: Should produce simple, well-commented code

        The AI analysis will compare which instruction set produces the best results.
        """
        copilot_server = GitHubCopilotServer(
            name=f"copilot-{instruction_name}",
            model="gpt-4.1",
            instructions=instructions,
        )

        agent = Agent(
            name=f"copilot-{instruction_name}",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            copilot_servers=[copilot_server],
            system_prompt=f"""You have access to a GitHub Copilot coding assistant 
specialized in {instruction_name} code generation. Use it for this task.""",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "Use the Copilot assistant to create a Python class for a binary search tree "
            "with insert, search, and delete methods.",
        )

        # Basic success criteria
        assert result.success
        assert result.tool_was_called(f"copilot_{instruction_name}_execute")

        # Check that response contains expected elements
        response_lower = result.final_response.lower()
        assert "class" in response_lower or "def" in response_lower


# =============================================================================
# A/B Testing: Model Comparison
# =============================================================================


@pytest.mark.skipif(
    not _copilot_sdk_available(),
    reason="github-copilot-sdk not available",
)
class TestCopilotModelComparison:
    """Compare different Copilot models for the same task.

    This demonstrates comparing different underlying LLMs to see which
    produces better code. The report will show side-by-side comparison.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("model", COPILOT_MODELS, ids=COPILOT_MODELS)
    async def test_sorting_algorithm_across_models(self, aitest_run, model: str):
        """Generate a sorting algorithm implementation across different models.

        This tests whether different models (gpt-4.1 vs gpt-4o-mini) produce
        different quality code for the same task.
        """
        copilot_server = GitHubCopilotServer(
            name=f"copilot-{model.replace('.', '-').replace('-', '')}",
            model=model,
            instructions="Write clean, efficient Python code with good documentation.",
        )

        agent = Agent(
            name=f"copilot-{model}",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            copilot_servers=[copilot_server],
            system_prompt=f"You have access to a Copilot assistant using {model}. Use it for code generation.",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "Use Copilot to implement the quicksort algorithm in Python with type hints.",
        )

        assert result.success
        # Tool name varies by model
        tool_called = any(
            "copilot" in call.name and "execute" in call.name for call in result.all_tool_calls
        )
        assert tool_called


# =============================================================================
# Multi-Dimension: Instructions × Models
# =============================================================================


@pytest.mark.skipif(
    not _copilot_sdk_available(),
    reason="github-copilot-sdk not available",
)
class TestCopilotMultiDimension:
    """Test all combinations of instructions and models (2×3 matrix).

    This demonstrates the full power of pytest-aitest's dimension detection.
    The report will show which combination works best.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("model", COPILOT_MODELS, ids=COPILOT_MODELS)
    @pytest.mark.parametrize(
        "instruction_name,instructions",
        list(INSTRUCTION_SETS.items())[:2],  # Use only 2 instruction sets to reduce cost
        ids=list(INSTRUCTION_SETS.keys())[:2],
    )
    async def test_factorial_function_all_combinations(
        self,
        aitest_run,
        model: str,
        instruction_name: str,
        instructions: str,
    ):
        """Generate factorial function with all model × instruction combinations.

        This creates a 2×2 matrix:
        - gpt-4.1 × quality
        - gpt-4.1 × performance  
        - gpt-4o-mini × quality
        - gpt-4o-mini × performance

        The AI analysis will identify which combination is optimal.
        """
        copilot_server = GitHubCopilotServer(
            name=f"copilot-{model.replace('.', '-').replace('-', '')}-{instruction_name}",
            model=model,
            instructions=instructions,
        )

        agent = Agent(
            name=f"{model}-{instruction_name}",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            copilot_servers=[copilot_server],
            system_prompt=f"Use Copilot ({model}, {instruction_name}) for code generation.",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "Use Copilot to write a factorial function in Python.",
        )

        assert result.success


# =============================================================================
# Basic Usage Tests
# =============================================================================


@pytest.mark.skipif(
    not _copilot_sdk_available(),
    reason="github-copilot-sdk not available",
)
class TestCopilotBasicUsage:
    """Basic tests demonstrating Copilot integration."""

    @pytest.mark.asyncio
    async def test_simple_function_generation(self, aitest_run):
        """Test basic code generation with Copilot."""
        copilot_server = GitHubCopilotServer(
            name="copilot-basic",
            model="gpt-4.1",
            instructions="Write clean, simple Python code.",
        )

        agent = Agent(
            name="copilot-basic",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            copilot_servers=[copilot_server],
            system_prompt="You have access to a Copilot coding assistant. Use it for code tasks.",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "Use Copilot to create a function that checks if a number is prime.",
        )

        assert result.success
        assert result.tool_was_called("copilot_basic_execute")

    @pytest.mark.asyncio
    async def test_multi_step_code_generation(self, aitest_run):
        """Test multiple Copilot calls in sequence."""
        copilot_server = GitHubCopilotServer(
            name="copilot-multi",
            model="gpt-4.1",
            instructions="Write clean Python code with tests.",
        )

        agent = Agent(
            name="copilot-multi-step",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            copilot_servers=[copilot_server],
            system_prompt="Use Copilot for multi-step coding tasks.",
            max_turns=10,
        )

        result = await aitest_run(
            agent,
            "First, use Copilot to create a simple Calculator class. "
            "Then, use Copilot to generate unit tests for it.",
        )

        assert result.success
        # Should call Copilot at least twice
        copilot_calls = [
            call for call in result.all_tool_calls if "copilot" in call.name
        ]
        assert len(copilot_calls) >= 2


# =============================================================================
# Documentation Tests (No SDK Required)
# =============================================================================


class TestCopilotServerDocumentation:
    """Documentation-only tests showing Copilot server usage patterns.

    These tests demonstrate the API without requiring actual execution.
    No SDK needed - just validates the configuration API.
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

    def test_instruction_comparison_pattern(self):
        """Document the pattern for A/B testing instructions."""
        # Create two agents with different instructions
        agent_a = Agent(
            name="copilot-quality",
            provider=Provider(model="azure/gpt-5-mini"),
            copilot_servers=[
                GitHubCopilotServer(
                    name="copilot-quality",
                    model="gpt-4.1",
                    instructions="Focus on code quality, type hints, and documentation.",
                )
            ],
        )

        agent_b = Agent(
            name="copilot-speed",
            provider=Provider(model="azure/gpt-5-mini"),
            copilot_servers=[
                GitHubCopilotServer(
                    name="copilot-speed",
                    model="gpt-4.1",
                    instructions="Focus on performance and algorithmic efficiency.",
                )
            ],
        )

        # Use pytest.mark.parametrize with both agents to compare
        assert agent_a.copilot_servers[0].instructions != agent_b.copilot_servers[0].instructions
