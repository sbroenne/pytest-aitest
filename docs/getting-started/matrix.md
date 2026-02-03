# Full Matrix Testing

Compare MCP servers, models, and prompts in a single test run.

## Comparing MCP Servers

A/B test different versions of your MCP server:

```python
weather_v1 = MCPServer(command=["python", "weather_v1.py"])
weather_v2 = MCPServer(command=["python", "weather_v2.py"])

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

## What Server Comparison Reveals

| Metric | What it tells you |
|--------|-------------------|
| Pass rate | Does the new server break anything? |
| Tool calls | Is the new server more efficient? |
| Duration | Is response time better? |
| Token usage | Does better tool output reduce LLM tokens? |

## Full Matrix: Models × Prompts × Servers

Include servers in your agent permutations:

```python
MODELS = ["gpt-5-mini", "gpt-4.1"]
PROMPTS = {"brief": "Be concise.", "detailed": "Explain your reasoning."}
SERVERS = [weather_v1, weather_v2]

AGENTS = [
    Agent(
        name=f"{model}-{prompt_name}-{server.name}",
        provider=Provider(model=f"azure/{model}"),
        mcp_servers=[server],
        system_prompt=prompt,
    )
    for model in MODELS
    for prompt_name, prompt in PROMPTS.items()
    for server in SERVERS
]

# 2 models × 2 prompts × 2 servers = 8 configurations
@pytest.mark.parametrize("agent", AGENTS, ids=lambda a: a.name)
@pytest.mark.asyncio
async def test_weather_query(aitest_run, agent):
    result = await aitest_run(agent, "What's the weather in Paris?")
    assert result.success
```

## Summary

**What you're testing:**

| Target | Question |
|--------|----------|
| MCP Server | Can the LLM understand and use my tools? |
| System Prompt | Do these instructions produce the behavior I want? |
| Agent Skill | Does this knowledge improve performance? |
| Model | Which LLM works best with my tools? |

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

## Next Steps

- [Test MCP Servers](../how-to/test-mcp-servers.md) — Detailed MCP configuration
- [Test CLI Tools](../how-to/test-cli-tools.md) — Wrap CLIs as testable interfaces
- [Generate Reports](../how-to/generate-reports.md) — Understand report output
