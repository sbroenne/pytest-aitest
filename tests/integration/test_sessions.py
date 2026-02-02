"""Session-based testing with multi-turn conversation continuity.

This module demonstrates how to test agents across multiple conversation turns
where context must be retained between tests. It serves as both a working test
suite and a reference implementation for session-based testing patterns.

Key Concepts Demonstrated
-------------------------
1. **Session Fixture**: Using `scope="class"` to share conversation state
2. **Messages Parameter**: Passing prior conversation to `aitest_run()`
3. **Context Verification**: Testing that the agent remembers information
4. **Session Isolation**: Different test classes get independent sessions
5. **Model Comparison**: Parametrizing models to compare session behavior

The "Paris Trip" Pattern
------------------------
This test proves session support by:
1. User mentions "Paris trip" in test_01
2. User says "that trip" (not Paris) in test_02 - agent must remember
3. User asks "what was I saving for?" in test_03 - ONLY answerable from context

If sessions don't work, test_03 will fail because no tool provides "Paris".

Usage
-----
    pytest tests/integration/test_sessions.py -v --aitest-summary

See Also
--------
    docs/sessions.md : Full documentation on session-based testing
    docs/test-harnesses.md : Documentation on the BankingService test harness
"""

from __future__ import annotations

import sys

import pytest

from pytest_aitest import Agent, MCPServer, Provider, Wait

# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.integration]

# Models to compare for session handling
MODELS = ["gpt-5-mini", "gpt-4o-mini"]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def banking_server():
    """MCP server wrapping the BankingService test harness.

    Scope: module
        The SAME server instance is used for ALL tests in this file.
        This means account balances persist and change across tests.

    The BankingService provides tools:
        - get_balance: Check one account
        - get_all_balances: Check all accounts
        - transfer: Move money between accounts
        - get_transactions: View transaction history

    Initial State:
        - Checking: $1,500.00
        - Savings: $3,000.00
    """
    return MCPServer(
        command=[sys.executable, "-u", "-m", "pytest_aitest.testing.banking_mcp"],
        wait=Wait.for_tools(["get_balance", "transfer", "get_transactions"]),
    )


def make_banking_agent(banking_server, model: str) -> Agent:
    """Create a banking agent with the specified model."""
    return Agent(
        provider=Provider(model=f"azure/{model}"),
        mcp_servers=[banking_server],
        system_prompt=(
            "You are a helpful banking assistant. Help users manage their checking "
            "and savings accounts. Be concise but thorough. When users ask about "
            "balances or transactions, always use the available tools to get "
            "current information - don't guess or use stale data."
        ),
        max_turns=10,
    )


@pytest.fixture(scope="class")
def banking_agent(banking_server):
    """Banking assistant agent configured for helpful, tool-using behavior.

    Scope: class
        Each test class gets its own agent instance, but they share
        the same banking_server (so state changes are visible).

    The system prompt encourages the agent to:
        - Always use tools for current data (not cached/guessed values)
        - Be concise but thorough in responses
        - Help with account management tasks
    """
    return Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[banking_server],
        system_prompt=(
            "You are a helpful banking assistant. Help users manage their checking "
            "and savings accounts. Be concise but thorough. When users ask about "
            "balances or transactions, always use the available tools to get "
            "current information - don't guess or use stale data."
        ),
        max_turns=10,
    )


@pytest.fixture(scope="class")
def session():
    """Shared conversation state for tests within a class.

    Scope: class
        - Tests WITHIN the same class share this session
        - Tests in DIFFERENT classes get separate sessions

    Usage Pattern:
        1. Run agent with prior messages:
           `result = await aitest_run(agent, prompt, messages=session["messages"])`
        2. Save state for next test:
           `session["messages"] = result.messages`

    Important:
        Always save `session["messages"]` BEFORE assertions that might fail.
        Otherwise, if an assertion fails, the session won't be saved and
        subsequent tests will receive an empty conversation.
    """
    return {"messages": []}


# =============================================================================
# TestBankingWorkflow: Multi-turn session proving context retention
# =============================================================================


class TestBankingWorkflow:
    """Multi-turn banking workflow demonstrating session continuity.

    This test class PROVES that sessions work correctly by establishing
    context in early tests and verifying it's retained in later tests.

    Test Flow
    ---------
    test_01: User introduces "Paris trip" context, checks balances
    test_02: User says "that trip" (not Paris) and transfers money
    test_03: User asks "what was I saving for?" - ONLY answerable from context
    test_04: User asks about trip costs - requires context AND tool calls
    test_05: User asks for conversation summary - tests full history retention

    Key Insight
    -----------
    test_03 is the critical test. The question "what was I saving for?" cannot
    be answered by any tool - the agent MUST remember "Paris" from test_01.
    If sessions don't work, test_03 will fail.
    """

    async def test_01_introduce_context(self, aitest_run, judge, banking_agent, session):
        """Establish memorable context (Paris trip) and check balances.

        This test introduces "Paris" as a memorable detail that will be
        verified in later tests. The agent should check account balances
        and acknowledge the trip planning context.

        Session State After:
            - Contains user's Paris trip mention
            - Contains agent's balance response
            - Approximately 5 messages
        """
        result = await aitest_run(
            banking_agent,
            "Hi! I'm planning a trip to Paris next summer and want to start "
            "saving for it. Can you check my account balances first?",
        )

        # CRITICAL: Save session FIRST, before any assertions that might fail.
        # If we assert first and it fails, session["messages"] never gets set,
        # causing all subsequent tests to fail with empty context.
        session["messages"] = result.messages

        assert result.success, f"Agent failed: {result.error}"

        # Verify the agent used tools to get real balance data
        balance_calls = result.tool_call_count("get_balance") + result.tool_call_count(
            "get_all_balances"
        )
        assert balance_calls >= 1, "Agent should use tools to check balances"

        # Verify response quality - agent should show actual balances
        assert judge(
            result.final_response,
            "Response shows account balances (checking and/or savings amounts)",
        )

    async def test_02_reference_prior_context(self, aitest_run, judge, banking_agent, session):
        """Reference prior context without repeating it.

        Key Test Design:
            The prompt says "that trip I mentioned" NOT "Paris trip".
            The agent must remember that "that trip" refers to Paris.

        This tests implicit context retention - the agent should understand
        the reference without us restating it explicitly.

        Session State After:
            - Contains transfer request and confirmation
            - Account state changed: Checking -$500, Savings +$500
            - Approximately 9 messages total
        """
        result = await aitest_run(
            banking_agent,
            # IMPORTANT: We say "that trip" NOT "Paris trip"
            # The agent must remember what trip we're talking about
            "Great! Let's start saving. Move $500 from checking to savings "
            "for that trip I mentioned.",
            messages=session["messages"],  # Continue from test_01
        )

        # Save session before assertions
        session["messages"] = result.messages

        assert result.success, f"Agent failed: {result.error}"
        assert result.tool_was_called("transfer"), "Agent should make a transfer"

        # Verify the transfer was completed
        assert judge(
            result.final_response,
            "Response confirms the transfer of $500 to savings was completed",
        )

    async def test_03_pure_context_question(self, aitest_run, judge, banking_agent, session):
        """Ask a question that can ONLY be answered from conversation history.

        THIS IS THE CRITICAL TEST.

        The question "what was I saving for?" cannot be answered by any tool.
        The BankingService has no concept of goals or purposes - it only knows
        about accounts and transactions.

        The agent MUST retrieve "Paris" from the conversation history established
        in test_01. If sessions don't work, this test fails.

        Why This Works:
            - No tool provides trip/goal information
            - "Paris" was only mentioned in test_01's user message
            - The agent must use the `messages` parameter to access history
        """
        result = await aitest_run(
            banking_agent,
            # This cannot be answered by tools - requires memory
            "Wait, remind me - what was I saving for again?",
            messages=session["messages"],
        )

        # Save session before assertions
        session["messages"] = result.messages

        assert result.success, f"Agent failed: {result.error}"

        # THE DEFINITIVE ASSERTION: Agent must say "Paris"
        response_lower = result.final_response.lower()
        assert "paris" in response_lower, (
            f"Agent must remember 'Paris' from conversation history.\n"
            f"This proves sessions work - no tool provides this information.\n"
            f"Got: {result.final_response}"
        )

    async def test_04_multi_turn_reasoning(self, aitest_run, judge, banking_agent, session):
        """Complex question requiring both context retention AND tool usage.

        This test combines:
            1. Context: "where I'm going" refers to Paris (from history)
            2. Tool call: Check current savings balance
            3. Reasoning: Calculate months to afford $800 flight

        Tests that the agent can use tools WHILE retaining conversation context.
        """
        result = await aitest_run(
            banking_agent,
            # Requires: context (Paris), tool call (balance), math (calculation)
            "If I keep saving $500 per month for my trip, and flights to "
            "where I'm going cost about $800, how many months until I can "
            "afford the flight? Check my current savings balance first.",
            messages=session["messages"],
        )

        # Save session before assertions
        session["messages"] = result.messages

        assert result.success, f"Agent failed: {result.error}"

        # Agent should check the balance using tools
        assert result.tool_was_called("get_balance"), "Agent should check savings balance"

        # Agent should provide a reasonable answer with calculation
        assert judge(
            result.final_response,
            "Response shows current savings balance and calculates how long "
            "until they can afford an $800 flight (likely already can with ~$3,500)",
        )

    async def test_05_context_summary(self, aitest_run, judge, banking_agent, session):
        """Request a summary to verify full conversation history retention.

        This tests that the agent remembers the ENTIRE conversation:
            - The original Paris trip goal
            - The $500 transfer
            - The flight cost calculation

        A good summary proves the agent has access to complete history.
        """
        result = await aitest_run(
            banking_agent,
            "Give me a quick summary of what we've discussed and done today.",
            messages=session["messages"],
        )

        # Save session before assertions
        session["messages"] = result.messages

        assert result.success, f"Agent failed: {result.error}"

        # Summary should mention key points from the entire conversation
        assert judge(
            result.final_response,
            "Summary mentions the Paris trip goal and the $500 transfer "
            "to savings. This proves the agent retained conversation history.",
        )


# =============================================================================
# TestSessionIsolation: Verify sessions don't leak between test classes
# =============================================================================


class TestSessionIsolation:
    """Verify that different test classes get isolated sessions.

    This test class runs AFTER TestBankingWorkflow. It verifies that:
        1. This class's session starts empty (no Paris context)
        2. Server state IS shared (balances changed by prior class)

    Key Distinction:
        - Session (conversation): Isolated per class
        - Server state (balances): Shared across all tests
    """

    async def test_fresh_session_starts_clean(self, aitest_run, banking_agent, session):
        """This class should NOT see TestBankingWorkflow's conversation.

        The conversation history should be empty, even though the server
        state (account balances) reflects changes from the prior test class.

        Expected:
            - session["messages"] starts empty (no Paris context here)
            - Banking balance ~$1,000 (after $500 transfer in prior class)
        """
        result = await aitest_run(
            banking_agent,
            "What's my current checking balance?",
            # Note: session["messages"] is empty - fresh session
        )

        assert result.success
        assert result.tool_was_called("get_balance")

        # The balance will be ~$1,000 (reflecting prior class's transfer)
        # but this class has no knowledge of WHY the transfer happened
        # because conversation history is isolated

        session["messages"] = result.messages


# =============================================================================
# TestModelComparison: Compare session handling across models
# =============================================================================


class TestModelSessionComparison:
    """Compare how different models handle session context retention.

    This tests the same multi-turn workflow across multiple models to see
    if there are differences in:
    - Context retention quality
    - Token usage
    - Response quality

    Each model runs the full 3-step session workflow independently.
    """

    @pytest.mark.parametrize("model", MODELS)
    @pytest.mark.asyncio
    async def test_session_context_retention(self, aitest_run, banking_server, model):
        """Full session workflow: introduce context → reference it → verify memory.

        This runs a complete session in a single test to compare models fairly.
        Each model gets the same prompts and must demonstrate context retention.
        """
        agent = make_banking_agent(banking_server, model)
        messages: list = []

        # Step 1: Introduce Paris trip context
        result1 = await aitest_run(
            agent,
            "Hi! I'm planning a trip to Paris next summer. Can you check my savings balance?",
        )
        assert result1.success, f"{model} failed step 1: {result1.error}"
        assert result1.tool_was_called("get_balance"), f"{model} didn't check balance"
        messages = result1.messages

        # Step 2: Reference prior context without repeating it
        result2 = await aitest_run(
            agent,
            "Great! Move $200 to savings for that trip I mentioned.",
            messages=messages,
        )
        assert result2.success, f"{model} failed step 2: {result2.error}"
        assert result2.tool_was_called("transfer"), f"{model} didn't transfer"
        messages = result2.messages

        # Step 3: Pure context question - THE CRITICAL TEST
        result3 = await aitest_run(
            agent,
            "Remind me - what was I saving for?",
            messages=messages,
        )
        assert result3.success, f"{model} failed step 3: {result3.error}"

        # Model MUST remember "Paris" from step 1
        response_lower = result3.final_response.lower()
        assert "paris" in response_lower, (
            f"{model} failed to remember 'Paris' from conversation.\n"
            f"Response: {result3.final_response}"
        )
