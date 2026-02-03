# Comparison Modes

When to use benchmark, arena, or matrix testing.

## Overview

pytest-aitest auto-detects your comparison mode based on how you parametrize tests:

| Mode | Parametrize By | Question Answered |
|------|----------------|-------------------|
| **Benchmark** | Model | Which LLM should I use? |
| **Arena** | Prompt | Which system prompt works best? |
| **Matrix** | Model × Prompt | What's the best combination? |

## Benchmark Mode: Compare Models

Use when you want to pick the best LLM for your tools.

### When to Use

- Evaluating cost vs. performance tradeoffs
- Checking if a cheaper model is "good enough"
- Validating tools work across different providers

### Setup

```python
MODELS = ["azure/gpt-5-mini", "azure/gpt-4.1", "openai/gpt-4o"]

@pytest.mark.parametrize("model", MODELS)
@pytest.mark.asyncio
async def test_tool_usage(aitest_run, model):
    agent = Agent(
        provider=Provider(model=model),
        mcp_servers=[my_server],
    )
    result = await aitest_run(agent, "Do the thing")
    assert result.success
```

### What You Learn

The report shows:

- **Pass rate per model**: gpt-4.1 (97%), gpt-5-mini (91%), gpt-4o (89%)
- **Cost comparison**: gpt-5-mini is 8x cheaper
- **Failure patterns**: gpt-4o struggles with multi-step instructions
- **Recommendation**: "Use gpt-5-mini unless you need complex reasoning"

## Arena Mode: Compare Prompts

Use when you want to optimize your system prompt.

### When to Use

- A/B testing prompt variations
- Finding the right level of detail
- Testing different instruction styles

### Setup

```yaml
# prompts/concise.yaml
name: CONCISE
system_prompt: |
  You are a helpful assistant. Be brief.

# prompts/detailed.yaml  
name: DETAILED
system_prompt: |
  You are a helpful assistant. Explain your reasoning
  step by step before taking action.
```

```python
from pytest_aitest import load_prompts

PROMPTS = load_prompts(Path("prompts/"))

@pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
@pytest.mark.asyncio
async def test_with_prompt(aitest_run, prompt):
    agent = Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[my_server],
        system_prompt=prompt.system_prompt,
    )
    result = await aitest_run(agent, "Do the thing")
    assert result.success
```

### What You Learn

The report shows:

- **Pass rate per prompt**: DETAILED (95%), CONCISE (82%)
- **Turn count**: CONCISE averages 2 turns, DETAILED averages 4
- **Failure analysis**: CONCISE fails on complex queries
- **Recommendation**: "Use DETAILED for complex tasks, CONCISE for simple ones"

## Matrix Mode: Full Comparison

Use when you want to find the optimal model + prompt combination.

### When to Use

- Full optimization across both dimensions
- Finding interaction effects
- Production deployment decisions

### Setup

```python
MODELS = ["azure/gpt-5-mini", "azure/gpt-4.1"]
PROMPTS = load_prompts(Path("prompts/"))

@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
@pytest.mark.asyncio
async def test_matrix(aitest_run, model, prompt):
    agent = Agent(
        provider=Provider(model=model),
        mcp_servers=[my_server],
        system_prompt=prompt.system_prompt,
    )
    result = await aitest_run(agent, "Do the thing")
    assert result.success
```

### What You Learn

The report shows a 2D grid:

|              | CONCISE | DETAILED |
|--------------|---------|----------|
| gpt-5-mini   | 82%     | 91%      |
| gpt-4.1      | 94%     | 97%      |

Plus analysis:

- **Best combination**: gpt-4.1 + DETAILED (97%)
- **Best value**: gpt-5-mini + DETAILED (91% at 1/8 cost)
- **Interaction**: gpt-5-mini needs DETAILED prompt to perform well
- **Recommendation**: "gpt-5-mini + DETAILED for most use cases"

## A/B Testing Servers

A special case: comparing different versions of your MCP server.

### When to Use

- Testing a new version before deployment
- Comparing implementation approaches
- Validating refactored tool descriptions

### Setup

```python
server_v1 = MCPServer(command=["python", "server_v1.py"])
server_v2 = MCPServer(command=["python", "server_v2.py"])

@pytest.mark.parametrize("server", [server_v1, server_v2], ids=["v1", "v2"])
@pytest.mark.asyncio
async def test_server_version(aitest_run, server):
    agent = Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[server],
    )
    result = await aitest_run(agent, "Do the thing")
    assert result.success
```

See [A/B Testing Servers](../getting-started/ab-testing-servers.md) for details.

## Choosing the Right Mode

```
Do you know which model to use?
├─ No → Benchmark Mode (compare models)
└─ Yes → Do you know which prompt to use?
         ├─ No → Arena Mode (compare prompts)
         └─ Yes → Do you want to optimize both?
                  ├─ Yes → Matrix Mode
                  └─ No → You're done! Just run tests.
```

## Cost Considerations

Matrix mode multiplies your test runs:

| Models | Prompts | Tests | Multiplier |
|--------|---------|-------|------------|
| 1      | 1       | 10    | 10 runs    |
| 3      | 1       | 10    | 30 runs    |
| 1      | 4       | 10    | 40 runs    |
| 3      | 4       | 10    | 120 runs   |

Start with benchmark or arena to narrow down, then use matrix for final optimization.
