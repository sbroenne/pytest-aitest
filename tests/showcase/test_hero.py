"""Hero test suite for README showcase.

A SINGLE cohesive banking scenario demonstrating ALL pytest-aitest capabilities:

1. Basic Tool Usage - Check account balances, view transactions
2. Multi-Tool Workflows - Transfer and verify, analyze transactions
3. Session Continuity - Multi-turn financial planning conversation
4. Model Comparison - Compare models on complex financial tasks
5. Prompt Comparison - Compare advisory styles (concise vs detailed vs friendly)
6. Skill Integration - Financial advisor skill enhancement
7. Error Handling - Graceful recovery from invalid operations

Output: docs/demo/hero-report.html
Command: pytest tests/showcase/ -v --aitest-html=docs/demo/hero-report.html
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pytest_aitest import Agent, MCPServer, Provider, Skill, Wait, load_system_prompts

# Mark all tests as showcase
pytestmark = [pytest.mark.showcase]

# =============================================================================
# Constants
# =============================================================================

DEFAULT_MODEL = "gpt-5-mini"
BENCHMARK_MODELS = ["gpt-5-mini", "gpt-4.1-mini"]
DEFAULT_RPM = 10
DEFAULT_TPM = 10000
DEFAULT_MAX_TURNS = 8

# Load prompts for system prompt comparison
PROMPTS_DIR = Path(__file__).parent / "prompts"

# Banking system prompt
BANKING_PROMPT_BASE = (
    "You are a personal finance assistant helping users manage their bank accounts. "
    "You have access to tools for checking balances, making transfers, deposits, "
    "withdrawals, and viewing transaction history."
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def banking_server():
    """Banking MCP server - the ONLY server for all hero tests.
    
    Provides a realistic banking scenario with:
    - 2 accounts: checking ($1,500), savings ($3,000)
    - Tools: get_balance, get_all_balances, transfer, deposit, withdraw, get_transactions
    """
    return MCPServer(
        command=[sys.executable, "-u", "-m", "pytest_aitest.testing.banking_mcp"],
        wait=Wait.for_tools([
            "get_balance", "get_all_balances", "transfer",
            "deposit", "withdraw", "get_transactions",
        ]),
    )


@pytest.fixture
def financial_advisor_skill():
    """Financial advisor skill with budgeting knowledge."""
    skill_path = Path(__file__).parent / "skills" / "financial-advisor"
    if skill_path.exists():
        return Skill.from_path(skill_path)
    return None


# =============================================================================
# 1. Basic Tool Usage - Single tool operations
# =============================================================================


class TestBasicOperations:
    """Basic single-tool operations demonstrating core functionality."""

    @pytest.mark.asyncio
    async def test_check_single_balance(self, aitest_run, banking_server):
        """Check balance of one account - simplest possible test."""
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt=BANKING_PROMPT_BASE,
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(agent, "What's my checking account balance?")

        assert result.success
        assert result.tool_was_called("get_balance")

    @pytest.mark.asyncio
    async def test_view_all_balances(self, aitest_run, banking_server):
        """View all account balances - demonstrates multi-account overview."""
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt=BANKING_PROMPT_BASE,
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(agent, "Show me all my account balances.")

        assert result.success
        assert result.tool_was_called("get_all_balances")


# =============================================================================
# 2. Multi-Tool Workflows - Complex operations requiring multiple tools
# =============================================================================


class TestMultiToolWorkflows:
    """Complex workflows requiring coordination of multiple tools."""

    @pytest.mark.asyncio
    async def test_transfer_and_verify(self, aitest_run, llm_assert, banking_server):
        """Transfer money and verify the result with balance check."""
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt=BANKING_PROMPT_BASE,
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "Transfer $100 from checking to savings, then show me my new balances.",
        )

        assert result.success
        assert result.tool_was_called("transfer")
        assert result.tool_was_called("get_all_balances") or result.tool_was_called("get_balance")
        assert llm_assert(result.final_response, "shows updated balances after transfer")

    @pytest.mark.asyncio
    async def test_transaction_analysis(self, aitest_run, llm_assert, banking_server):
        """Get transaction history and provide analysis."""
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt=BANKING_PROMPT_BASE,
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "Show me my recent transactions and summarize my spending patterns.",
        )

        assert result.success
        assert result.tool_was_called("get_transactions")


# =============================================================================
# 3. Session Continuity - Multi-turn conversation with context retention
# =============================================================================


@pytest.mark.session("savings-planning")
class TestSavingsPlanningSession:
    """Multi-turn session: Planning savings transfers.
    
    Tests that the agent remembers context across turns:
    - Turn 1: Check balances and discuss savings
    - Turn 2: Reference "my savings" (must remember context)
    - Turn 3: Follow up on the plan
    """

    @pytest.mark.asyncio
    async def test_01_establish_context(self, aitest_run, llm_assert, banking_server):
        """First turn: check balances and discuss savings goals."""
        agent = Agent(
            name="savings-01",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt=BANKING_PROMPT_BASE,
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "I want to save more money. Can you check my accounts and suggest "
            "how much I could transfer to savings each month?",
        )

        assert result.success
        assert result.tool_was_called("get_all_balances") or result.tool_was_called("get_balance")
        assert llm_assert(result.final_response, "provides savings suggestion based on balances")

    @pytest.mark.asyncio
    async def test_02_reference_previous(self, aitest_run, llm_assert, banking_server):
        """Second turn: reference previous context."""
        agent = Agent(
            name="savings-02",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt=BANKING_PROMPT_BASE,
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "That sounds good. Let's start by moving $200 to savings right now.",
        )

        assert result.success
        assert result.tool_was_called("transfer")

    @pytest.mark.asyncio
    async def test_03_verify_result(self, aitest_run, llm_assert, banking_server):
        """Third turn: verify the transfer worked."""
        agent = Agent(
            name="savings-03",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt=BANKING_PROMPT_BASE,
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "Great! Can you show me my new savings balance?",
        )

        assert result.success
        assert result.tool_was_called("get_balance") or result.tool_was_called("get_all_balances")


# =============================================================================
# 4. Model Comparison - Compare different LLMs on same task
# =============================================================================


class TestModelComparison:
    """Compare how different models handle financial tasks."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("model", BENCHMARK_MODELS)
    async def test_financial_advice_quality(self, aitest_run, llm_assert, banking_server, model: str):
        """Compare models on providing financial advice."""
        agent = Agent(
            provider=Provider(model=f"azure/{model}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt=BANKING_PROMPT_BASE,
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "I have some money in checking. Should I move some to savings? "
            "Check my balances and give me a recommendation.",
        )

        assert result.success
        assert len(result.all_tool_calls) >= 1, f"Model {model} should use tools"
        assert llm_assert(
            result.final_response,
            "provides recommendation based on account balances",
        )


# =============================================================================
# 5. Prompt Comparison - Compare different system prompts
# =============================================================================


def _load_advisor_prompts():
    """Load financial advisor prompts."""
    if PROMPTS_DIR.exists():
        return load_system_prompts(PROMPTS_DIR)
    return {}


ADVISOR_PROMPTS = _load_advisor_prompts()


@pytest.mark.skipif(len(ADVISOR_PROMPTS) == 0, reason="No prompts found")
class TestPromptComparison:
    """Compare how different prompt styles affect responses."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("prompt_name,system_prompt", ADVISOR_PROMPTS.items())
    async def test_advice_style_comparison(self, aitest_run, llm_assert, banking_server, prompt_name, system_prompt):
        """Compare concise vs detailed vs friendly advisory styles."""
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt=system_prompt,
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "I'm worried about my spending. Can you check my accounts "
            "and give me advice on managing my money better?",
        )

        assert result.success
        assert result.tool_was_called("get_all_balances") or result.tool_was_called("get_balance")


# =============================================================================
# 6. Skill Integration - Test with domain knowledge
# =============================================================================


class TestSkillEnhancement:
    """Test how skills improve advice quality."""

    @pytest.mark.asyncio
    async def test_with_financial_skill(
        self, aitest_run, llm_assert, banking_server, financial_advisor_skill
    ):
        """Agent with financial advisor skill should give better advice."""
        if financial_advisor_skill is None:
            pytest.skip("Financial advisor skill not found")

        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt=BANKING_PROMPT_BASE,
            skill=financial_advisor_skill,
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "I have $1500 in checking. Should I keep it there or move some to savings? "
            "What's a good emergency fund target?",
        )

        assert result.success
        assert llm_assert(
            result.final_response,
            "provides financial advice about savings or emergency funds",
        )


# =============================================================================
# 7. Error Handling - Graceful recovery from invalid operations
# =============================================================================


class TestErrorHandling:
    """Test graceful handling of edge cases and errors."""

    @pytest.mark.asyncio
    async def test_insufficient_funds_recovery(self, aitest_run, llm_assert, banking_server):
        """Agent should handle insufficient funds gracefully."""
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt=BANKING_PROMPT_BASE + " If an operation fails, explain why and suggest alternatives.",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "Transfer $50,000 from my checking to savings.",
        )

        assert result.success
        assert result.tool_was_called("transfer") or result.tool_was_called("get_balance")
        assert llm_assert(
            result.final_response,
            "explains insufficient funds or suggests an alternative",
        )

    @pytest.mark.asyncio
    async def test_ambiguous_request_clarification(self, aitest_run, llm_assert, banking_server):
        """Agent should ask for clarification on ambiguous requests."""
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[banking_server],
            system_prompt=BANKING_PROMPT_BASE + " Ask for clarification when requests are ambiguous.",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "Move some money around.",
        )

        assert result.success
        assert llm_assert(
            result.final_response,
            "asks for clarification OR explains what information is needed",
        )
