# Core Concepts

pytest-aitest is a pytest plugin for testing AI interfaces - hence its name. You write tests as natural language prompts, and an LLM executes them against your tools.

## Quick Overview

**What you're testing:**
- **MCP Servers/CLIs** - Can an LLM understand and use your tools correctly?
- **System Prompts** - Do your instructions produce the behavior you want?
- **Agent Skills** - Does domain knowledge help the agent perform? ([agentskills.io](https://agentskills.io))

**An Agent is the test harness** that combines these:

```python
Agent(
    name="weather-test",
    provider=Provider(model="azure/gpt-5-mini"),   # LLM provider (required)
    mcp_servers=[weather_server],                  # MCP servers with tools
    system_prompt="Be concise.",                   # Agent behavior (optional)
    skill=weather_skill,                           # Agent Skill (optional)
)
```

**Testing workflow:**

1. **Define what you're testing** - MCP server, prompt, skill, or combination
2. **Run tests** - `aitest_run(agent, prompt)` executes and captures results
3. **Compare variations** - Use pytest parametrize to compare configurations

---

*The rest of this guide builds from the simplest case to advanced scenarios.*

---

## The Simplest Case: Testing an MCP Server

The most common use case: verify an LLM can use your MCP server correctly.

```python
from pytest_aitest import Agent, Provider, MCPServer

# The MCP server you're testing
weather_server = MCPServer(command="python", args=["weather_mcp.py"])

agent = Agent(
    name="basic",
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[weather_server],
)

@pytest.mark.asyncio
async def test_weather_query(aitest_run):
    """Verify the LLM can use get_weather correctly."""
    result = await aitest_run(agent, "What's the weather in Paris?")
    
    assert result.success
    assert result.tool_was_called("get_weather")
```

**What this tests:**
- Tool discovery - Did the LLM find `get_weather`?
- Parameter inference - Did it pass `location="Paris"` correctly?
- Response handling - Did it interpret the tool output?

If this fails, your MCP server's tool descriptions or schemas need work.

---

## Testing System Prompts

System prompts define agent behavior. Test different prompts to find what works:

```python
agent = Agent(
    name="concise-assistant",
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[weather_server],
    system_prompt="You are a weather assistant. Be concise and direct.",
)
```

Different system prompts produce different behaviors:

| System Prompt | Behavior |
|---------------|----------|
| "Be concise." | Short, direct answers |
| "Explain your reasoning." | Verbose, step-by-step responses |
| "Use bullet points." | Structured output format |
| "If unsure, ask clarifying questions." | More cautious, interactive |

The system prompt affects both the *quality* of responses and the *cost* (longer prompts → more tokens).

---

## Testing Agent Skills

An **Agent Skill** is a domain knowledge module following the [agentskills.io](https://agentskills.io/specification) specification. Agent Skills provide:

- **Instructions** - prepended to the system prompt
- **References** - on-demand documents the agent can look up

Test whether a skill improves agent performance:

```python
from pytest_aitest import Skill

skill = Skill.from_path("skills/weather-expert")

agent = Agent(
    name="with-skill",
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[weather_server],
    skill=skill,
)
```

A skill is a directory with a `SKILL.md` file:

```
weather-expert/
├── SKILL.md           # Instructions (required)
└── references/        # On-demand lookup docs (optional)
    └── clothing-guide.md
```

```markdown
# SKILL.md
---
name: weather-expert
description: Guidelines for interpreting weather data and making recommendations
---

# Weather Expert Guidelines

## Temperature Interpretation
- Below 0°C: Freezing, warn about ice
- 0-10°C: Cold, recommend warm clothing  
- 10-20°C: Mild, light jacket sufficient
- Above 20°C: Warm, no jacket needed

For clothing recommendations, use the reference document.
```

**System prompt vs Skill:**

| Aspect | System Prompt | Skill |
|--------|---------------|-------|
| Purpose | Define behavior | Provide domain knowledge |
| Content | Instructions | Reference material |
| Example | "Be concise" | "Temperature chart..." |
| Where | `system_prompt=` | `skill=` |

You can use both together. The skill content is prepended to the system prompt.

See [Agent Skills](skills.md) for the complete guide on creating and testing Agent Skills.

---

## Comparing Configurations

The power of pytest-aitest is comparing different configurations to find what works best. There are two patterns.

### Pattern 1: Explicit Configurations

Define agents with meaningful names when testing distinct approaches:

```python
from pytest_aitest import Agent, Provider, MCPServer, Skill

weather_server = MCPServer(command="python", args=["weather_mcp.py"])

# Test different prompts with the same MCP server
agent_brief = Agent(
    name="brief-prompt",
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[weather_server],
    system_prompt="Be concise. One sentence max.",
)

agent_detailed = Agent(
    name="detailed-prompt",
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[weather_server],
    system_prompt="Be thorough. Explain your reasoning.",
)

agent_with_skill = Agent(
    name="with-skill",
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[weather_server],
    skill=Skill.from_path("skills/weather-expert"),
)

AGENTS = [agent_brief, agent_detailed, agent_with_skill]

@pytest.mark.parametrize("agent", AGENTS, ids=lambda a: a.name)
@pytest.mark.asyncio
async def test_weather_query(aitest_run, agent):
    """Which configuration handles weather queries best?"""
    result = await aitest_run(agent, "What's the weather in Paris?")
    assert result.success
```

This runs 3 tests:
- `test_weather_query[brief-prompt]`
- `test_weather_query[detailed-prompt]`
- `test_weather_query[with-skill]`

**Use explicit configurations when:**
- Testing conceptually different approaches
- Names have meaning ("with-skill", "without-skill")
- You want full control over each configuration

### Pattern 2: Generated Configurations (Permutations)

Generate configurations from all permutations for systematic testing:

```python
MODELS = ["gpt-5-mini", "gpt-4.1"]
PROMPTS = {
    "brief": "Be concise.",
    "detailed": "Explain your reasoning step by step.",
}

weather_server = MCPServer(command="python", args=["weather_mcp.py"])

# Generate all combinations to test your MCP server
AGENTS = [
    Agent(
        name=f"{model}-{prompt_name}",
        provider=Provider(model=f"azure/{model}"),
        mcp_servers=[weather_server],
        system_prompt=prompt,
    )
    for model in MODELS
    for prompt_name, prompt in PROMPTS.items()
]

# 2 models × 2 prompts = 4 configurations
@pytest.mark.parametrize("agent", AGENTS, ids=lambda a: a.name)
@pytest.mark.asyncio
async def test_weather_query(aitest_run, agent):
    """Test MCP server with different model/prompt combinations."""
    result = await aitest_run(agent, "What's the weather in Paris?")
    assert result.success
```

This runs 4 tests:
- `test_weather_query[gpt-5-mini-brief]`
- `test_weather_query[gpt-5-mini-detailed]`
- `test_weather_query[gpt-4.1-brief]`
- `test_weather_query[gpt-4.1-detailed]`

**Use generated configurations when:**
- You want to test all combinations systematically
- Looking for interactions (e.g., "this MCP server works with gpt-4.1 but fails with gpt-5-mini")
- Running a full matrix evaluation

### What the Report Shows

The report shows a **Configuration Leaderboard**:

| Configuration | Pass Rate | Tokens | Cost |
|---------------|-----------|--------|------|
| gpt-5-mini-brief | 100% | 747 | $0.002 |
| gpt-4.1-brief | 100% | 560 | $0.008 |
| gpt-5-mini-detailed | 100% | 1,203 | $0.004 |
| gpt-4.1-detailed | 100% | 892 | $0.012 |

This helps you answer:
- "Which configuration works best for my MCP server?"
- "Can I use a cheaper model with my tools?"
- "Does this prompt improve tool usage?"

---

## Sessions: Multi-Turn Conversations

So far, each test is independent—the agent has no memory between tests. **Sessions** let multiple tests share conversation history, simulating real multi-turn interactions.

### Why Sessions?

Real agents don't answer single questions. Users have conversations:

1. "What's the weather in Paris?"
2. "What about tomorrow?"  ← Requires remembering "Paris"
3. "Should I bring an umbrella?"  ← Requires remembering the forecast

Without sessions, test 2 would fail—the agent doesn't know what "tomorrow" refers to.

### Defining a Session

Use the `@pytest.mark.session` marker:

```python
@pytest.mark.session("weather-chat")
class TestWeatherConversation:
    """Tests run in order, sharing conversation history."""
    
    @pytest.mark.asyncio
    async def test_initial_query(self, aitest_run, weather_agent):
        """First message - establishes context."""
        result = await aitest_run(weather_agent, "What's the weather in Paris?")
        assert result.success
        assert "Paris" in result.final_response
    
    @pytest.mark.asyncio
    async def test_followup(self, aitest_run, weather_agent):
        """Second message - uses context from first."""
        result = await aitest_run(weather_agent, "What about tomorrow?")
        assert result.success
        # Agent remembers we were talking about Paris
        assert result.tool_was_called("get_forecast")
    
    @pytest.mark.asyncio
    async def test_recommendation(self, aitest_run, weather_agent):
        """Third message - builds on full conversation."""
        result = await aitest_run(weather_agent, "Should I bring an umbrella?")
        assert result.success
```

**Key points:**
- Tests in a session run **in order** (top to bottom)
- Each test sees the **full conversation history** from previous tests
- The session name (`"weather-chat"`) groups related tests

### Session Context Flow

```
test_initial_query
    User: "What's the weather in Paris?"
    Agent: "Paris is 18°C, partly cloudy..."
    ↓ context passed to next test

test_followup  
    [Previous messages included]
    User: "What about tomorrow?"
    Agent: "Tomorrow in Paris will be..."
    ↓ context passed to next test

test_recommendation
    [All previous messages included]
    User: "Should I bring an umbrella?"
    Agent: "Based on tomorrow's forecast..."
```

### When to Use Sessions

| Scenario | Use Session? |
|----------|--------------|
| Single Q&A tests | No |
| Multi-turn conversation | Yes |
| Workflow with multiple steps | Yes |
| Independent feature tests | No |
| Testing context retention | Yes |

### Sessions with Parametrize

You can combine sessions with model/prompt comparison:

```python
@pytest.mark.session("shopping-flow")
@pytest.mark.parametrize("model", ["gpt-5-mini", "gpt-4.1"])
class TestShoppingWorkflow:
    """Test the same conversation flow with different models."""
    
    async def test_browse(self, aitest_run, model, shopping_server):
        agent = Agent(provider=Provider(model=f"azure/{model}"), ...)
        result = await aitest_run(agent, "Show me running shoes")
        assert result.success
    
    async def test_select(self, aitest_run, model, shopping_server):
        agent = Agent(provider=Provider(model=f"azure/{model}"), ...)
        result = await aitest_run(agent, "I'll take the Nike ones")
        assert result.success
```

This creates two separate session flows:
- `shopping-flow[gpt-5-mini]`: browse → select (with gpt-5-mini)
- `shopping-flow[gpt-4.1]`: browse → select (with gpt-4.1)

The report shows each session as a complete flow with all turns visualized.

---

## Comparing MCP Servers

You can A/B test MCP servers by including them in agent configurations:

```python
weather_v1 = MCPServer(name="v1", command="python", args=["weather_v1.py"])
weather_v2 = MCPServer(name="v2", command="python", args=["weather_v2.py"])

AGENTS = [
    Agent(
        name="agent-v1",
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[weather_v1],
    ),
    Agent(
        name="agent-v2",
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[weather_v2],
    ),
]

@pytest.mark.parametrize("agent", AGENTS, ids=lambda a: a.name)
@pytest.mark.asyncio
async def test_weather_query(aitest_run, agent):
    result = await aitest_run(agent, "What's the weather in Paris?")
    assert result.success
```

**Use cases:**
- Iterating on your own server (v1 vs v2)
- Comparing implementations (your server vs open-source)
- Testing different backends (SQLite vs PostgreSQL)

### What Server Comparison Reveals

| Metric | What it tells you |
|--------|-------------------|
| Pass rate | Does the new server break anything? |
| Tool calls | Is the new server more efficient? |
| Duration | Is response time better? |
| Token usage | Does better tool output reduce LLM tokens? |

### Full Matrix with Servers

Include servers in your agent permutations:

```python
MODELS = ["gpt-5-mini", "gpt-4.1"]
SERVERS = [weather_v1, weather_v2]

AGENTS = [
    Agent(
        name=f"{model}-{server.name}",
        provider=Provider(model=f"azure/{model}"),
        mcp_servers=[server],
    )
    for model in MODELS
    for server in SERVERS
]
# 4 agents: gpt-5-mini-v1, gpt-5-mini-v2, gpt-4.1-v1, gpt-4.1-v2
```

---

## Summary

**What you're testing:**

| Target | Question |
|--------|----------|
| MCP Server | Can the LLM understand and use my tools? |
| System Prompt | Do these instructions produce the behavior I want? |
| Skill | Does this knowledge improve performance? |

**The Agent is the test harness** that bundles configuration:

```
┌─────────────────────────────────────────────────────────┐
│                   Agent (test harness)                  │
├─────────────────────────────────────────────────────────┤
│  name             → Identity for reports               │
│  provider         → Which LLM runs the test            │
│  mcp_servers      → MCP servers to test                │
│  system_prompt    → Instructions to test               │
│  skill            → Knowledge to test                  │
└─────────────────────────────────────────────────────────┘
```

**Two comparison patterns:**

| Pattern | When to use |
|---------|-------------|
| Explicit configurations | Testing distinct approaches ("with-skill", "without-skill") |
| Generated configurations | Systematic testing (model × prompt × server) |

**Progression:**

1. **Start simple**: Test one MCP server
2. **Add instructions**: Test system prompts
3. **Add knowledge**: Test Agent Skills
4. **Compare configurations**: Find what works best
5. **Full matrix**: Generate all permutations
6. **Multi-turn flows**: Use sessions for conversations

Each step is optional. Match complexity to your needs.

---

## Next Steps

- [Configuration](configuration.md) - Provider settings, authentication
- [MCP Servers](mcp-server.md) - Defining and testing tool servers
- [Skills](skills.md) - Creating and using skill reference documents
- [Reporting](reporting.md) - Understanding the HTML report
