---
description: "Test-driven development for AI interfaces. Write tests first, then iterate on tool descriptions, schemas, and prompts until LLMs can use them."
---

# Test-Driven Development for AI Interfaces

pytest-aitest enables TDD for the parts of your system that no compiler can check: tool descriptions, schemas, system prompts, and skills.

## The Problem TDD Solves

Traditional code has a fast feedback loop. Write a function, the compiler catches type errors, a linter catches style issues, unit tests catch logic bugs. You iterate quickly.

AI interfaces have **no feedback loop**. You write a tool description, deploy it, and discover it's broken when users complain that the LLM picks the wrong tool. There's no compiler for "this description is confusing to an LLM." There's no linter for "this parameter name is ambiguous."

pytest-aitest creates that missing feedback loop.

## The TDD Cycle

The classic Red/Green/Refactor cycle maps directly to AI interface development:

### Red: Write a Failing Test

Start with what a user would say. Don't think about implementation — think about intent:

```python
async def test_weather_query(aitest_run):
    agent = Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[weather_server],
    )
    result = await aitest_run(agent, "What's the weather in Paris?")

    assert result.success
    assert result.tool_was_called("get_weather")
```

Run it. The LLM reads your tool descriptions, tries to use them, and fails. Maybe it called `get_forecast` instead of `get_weather`. Maybe it passed `{"city": "Paris"}` when the parameter is `location`. The test tells you exactly what went wrong.

### Green: Fix the Interface

Now improve the thing the LLM actually sees — your tool descriptions, schemas, or system prompt:

```python
# Before: LLM confused get_weather with get_forecast
@mcp.tool()
def get_weather(city: str) -> str:
    """Get weather."""  # Too vague

# After: clear name, clear description, clear parameter
@mcp.tool()
def get_weather(location: str) -> str:
    """Get the current weather conditions for a city.
    Use this for current conditions, not forecasts."""
```

Run the test again. It passes. The LLM now picks the right tool with the right parameters.

### Refactor: Let AI Analysis Guide You

Generate a report. The AI analysis reads your full test results and tells you what else to improve:

```
🔧 MCP Tool Feedback
- compare_weather: Consider strengthening description to encourage
  single-call usage instead of multiple get_weather calls.
  Estimated impact: ~15–25% cost reduction on comparison queries.

💡 Suggested description:
  "Compare current weather between two cities and return per-city
  conditions plus computed differences (temperature, humidity deltas).
  Use instead of calling get_weather twice."
```

You didn't know this was a problem. The AI found it by analyzing actual LLM behavior across your test suite.

## What You're Designing

In traditional TDD, you design functions and classes. In pytest-aitest, you design **what the LLM sees**:

| Traditional TDD | AI Interface TDD |
|-----------------|-----------------|
| Function signatures | Tool descriptions |
| Type definitions | Parameter schemas |
| API documentation | System prompts |
| — | Agent skills |

These are your "code." They have no type system, no compiler, no static analysis. The only way to validate them is to let an LLM try to use them — which is exactly what pytest-aitest does.

## Why Not Just Manual Testing?

You could test manually: open a chat, type a prompt, see if the LLM uses the right tool. But:

- **No regression detection** — You changed a description and broke three other tools. Manual testing won't catch that.
- **No comparison** — Is `gpt-5-mini` better than `gpt-4.1` for your tools? Manual testing can't tell you.
- **No CI/CD** — You can't gate deployments on "I chatted with it and it seemed fine."
- **No analysis** — You see what failed, but not *why* or *how to fix it*.

pytest-aitest gives you automated, repeatable, analyzable tests for your AI interfaces — the same guarantees TDD gives you for code.

## The Feedback Loop

The key insight: **AI analysis closes the loop that traditional testing leaves open.**

```
Write test → Run → Fail → Fix interface → Pass → AI analysis → Improve further → ...
```

Traditional test frameworks stop at pass/fail. pytest-aitest continues: the AI reads your results and produces specific, actionable suggestions for tool descriptions, system prompts, and cost optimization. This is the refactoring step that makes TDD powerful — applied to AI interfaces.

## Getting Started

Write your first test: [Getting Started](../getting-started/index.md)

See AI analysis in action: [Sample Reports](ai-analysis.md#sample-reports)
