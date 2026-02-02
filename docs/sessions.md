# Sessions (Multi-Turn Conversations)

Test agents across multi-turn conversations where context must be retained.

## Why Sessions?

Many agent workflows span multiple turns:

1. **User asks about account balances** → Agent checks balances
2. **User says "transfer $500 to savings"** → Agent makes transfer
3. **User asks "what was I saving for?"** → Agent must remember from context

Without sessions, each test starts fresh—the agent forgets everything.

## Quick Start

```python
import pytest
from pytest_aitest import Agent, Provider

@pytest.fixture(scope="class")
def session():
    """Shared conversation state across tests in this class."""
    return {"messages": []}

@pytest.fixture
def agent():
    return Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[...],
    )

class TestBankingWorkflow:
    """Tests share conversation history within this class."""
    
    async def test_01_check_balances(self, aitest_run, agent, session):
        result = await aitest_run(
            agent,
            "I'm saving for a trip to Paris. What are my balances?"
        )
        
        # Save conversation for next test
        session["messages"] = result.messages
        
        assert result.success
        assert result.tool_was_called("get_balance")
    
    async def test_02_make_transfer(self, aitest_run, agent, session):
        result = await aitest_run(
            agent,
            "Transfer $500 to savings for that trip I mentioned.",
            messages=session["messages"],  # Continue conversation
        )
        
        session["messages"] = result.messages
        
        assert result.success
        assert result.tool_was_called("transfer")
    
    async def test_03_verify_context(self, aitest_run, agent, session):
        # This question is ONLY answerable from conversation history
        result = await aitest_run(
            agent,
            "What was I saving for again?",
            messages=session["messages"],
        )
        
        # Agent must remember "Paris" from first test
        assert "paris" in result.final_response.lower()
```

## Key Concepts

### The `messages` Parameter

Pass prior conversation to `aitest_run()`:

```python
result = await aitest_run(
    agent,
    "Follow-up question...",
    messages=session["messages"],  # Prior conversation
)
```

### The `messages` Property

Get conversation history from a result:

```python
result = await aitest_run(agent, "First message")
conversation = result.messages  # List of message dicts

# Pass to next test
next_result = await aitest_run(agent, "Continue...", messages=conversation)
```

### Session Context Count

Track how many prior messages were passed:

```python
result = await aitest_run(agent, prompt, messages=prior_messages)

if result.is_session_continuation:
    print(f"Received {result.session_context_count} prior messages")
```

## Session Fixture Pattern

Use `scope="class"` for tests that share conversation:

```python
@pytest.fixture(scope="class")
def session():
    """Conversation state shared within test class."""
    return {"messages": []}
```

**Important**: Always save messages **before** assertions that might fail:

```python
async def test_something(self, aitest_run, agent, session):
    result = await aitest_run(agent, prompt, messages=session["messages"])
    
    # Save FIRST, before assertions
    session["messages"] = result.messages
    
    # Then assert (if this fails, session is still saved)
    assert result.success
    assert judge(result.final_response, "...")
```

## Test Design Tips

### 1. Introduce Context in First Test

Start with a prompt containing memorable details:

```python
# GOOD: Mentions "Paris" explicitly
"I'm planning a trip to Paris next summer. What are my account balances?"

# BAD: No memorable context to verify later
"What are my account balances?"
```

### 2. Reference Without Repeating

In follow-up tests, reference context without stating it:

```python
# GOOD: Says "that trip" - agent must remember Paris
"Transfer $500 for that trip I mentioned."

# BAD: Repeats the context - doesn't prove session works
"Transfer $500 for my Paris trip."
```

### 3. Pure Context Questions

Include a test that can ONLY be answered from history:

```python
# This question has no tool to answer it
# Agent MUST use conversation memory
"Remind me - what was I saving for?"
```

## Session Isolation

Different test classes get isolated sessions:

```python
class TestWorkflowA:
    """This class has its own session."""
    
    async def test_01(self, session):
        # session["messages"] is empty at start
        ...

class TestWorkflowB:
    """This class has a DIFFERENT session."""
    
    async def test_01(self, session):
        # session["messages"] is empty - isolated from WorkflowA
        ...
```

## Report Visualization

Session tests appear grouped in the HTML report:

- **🔗 Session container** shows all tests in the workflow
- **Summary stats**: Total duration, tokens, cost, tool calls
- **Flow visualization**: Shows message count between tests
- **Expandable details**: Click any test to see its conversation

## Example: Banking Workflow

See the complete example in [tests/integration/test_sessions.py](../tests/integration/test_sessions.py).

This test proves session support works by:
1. Introducing "Paris trip" context
2. Referencing "that trip" without saying Paris
3. Asking "what was I saving for?" - only answerable from memory

## Best Practices

| Do | Don't |
|----|-------|
| Save `messages` before assertions | Save after assertions (may not run on failure) |
| Use memorable context (names, places) | Use generic prompts |
| Include pure-context questions | Only test tool calls |
| Use `scope="class"` for related tests | Use `scope="function"` for sessions |
| Test session isolation | Assume sessions are isolated |
