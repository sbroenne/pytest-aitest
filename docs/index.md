# pytest-aitest

**Test your AI interfaces. Get actionable insights.**

A pytest plugin for validating whether language models can understand and operate your MCP servers, tools, prompts, and skills. Generates AI-powered reports that tell you *what to fix*, not just *what failed*.

## What Makes This Different

### AI-Powered Reports

Reports don't just show pass/fail — they tell you **what to do**. Here's actual output analyzing 2 LLM models:

> ## 🎯 Recommendation
>
> **Deploy: gpt-4.1-mini** (default prompt)
>
> Achieves **100% pass rate at ~55–70% lower cost** than gpt-5-mini, with equal tool correctness and acceptable response quality.
>
> - **Simple weather:** $0.000297 (vs $0.000342 — 13% cheaper)
> - **Forecast:** $0.000575 (vs $0.001508 — 62% cheaper)  
> - **Comparison:** $0.000501 (vs $0.001785 — 72% cheaper)
>
> ## 🔧 MCP Tool Feedback
>
> | Tool | Status | Calls | Issue |
> |------|--------|-------|-------|
> | `get_weather` | ✅ | 6 | Working well |
> | `get_forecast` | ✅ | 2 | Working well |
> | `compare_weather` | ✅ | 1 | Consider strengthening description |
> | `list_cities` | ⚠️ | 0 | Not exercised |
>
> **Suggested improvement for `compare_weather`:**
> > Compare current weather between two cities and return per-city conditions plus computed differences (temperature, humidity deltas). Use instead of calling `get_weather` twice.
>
> ## 💡 Optimizations
>
> **Cost reduction opportunity:** Strengthen `compare_weather` description to encourage single-call logic instead of multiple `get_weather` calls. **Estimated impact: ~15–25% cost reduction** on comparison queries.

*Generates [interactive HTML reports](reports/02_multi_agent.html) with agent leaderboards, comparison tables, and sequence diagrams.*

## Why?

Your MCP server passes all unit tests. Then an LLM tries to use it and:

- Picks the wrong tool
- Passes garbage parameters
- Can't recover from errors
- Ignores your system prompt instructions

**Why?** Because you tested the code, not the AI interface.

For LLMs, your API isn't functions and types — it's **tool descriptions, system prompts, skills, and schemas**. These are what the LLM actually sees. Traditional tests can't validate them.

**The key insight: your test is a prompt.** You write what a user would say, and the LLM figures out how to use your tools. If it can't, your AI interface needs work.

## The Agent Concept

An **Agent** is what executes your test. It bundles:

- **Provider** — The LLM (model name, rate limits)
- **MCP/CLI Servers** — The tools being tested
- **System Prompt** — Optional behavior instructions
- **Skill** — Optional domain knowledge

The Agent is the *test harness*, not the thing being tested. Your tests validate whether the LLM can use your tools correctly.

When you test multiple agents (different models, prompts, or servers), pytest-aitest automatically generates a **leaderboard** comparing them.

## Quick Start

```python
from pytest_aitest import Agent, Provider, MCPServer

weather_server = MCPServer(command=["python", "weather_mcp.py"])

@pytest.mark.asyncio
async def test_weather_query(aitest_run):
    agent = Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[weather_server],
    )
    
    result = await aitest_run(agent, "What's the weather in Paris?")
    
    assert result.success
    assert result.tool_was_called("get_weather")
```

> 📁 See [test_basic_usage.py](https://github.com/sbroenne/pytest-aitest/blob/main/tests/integration/test_basic_usage.py) for complete examples.

## Features

- **Test MCP Servers** — Verify LLMs can discover and use your tools
- **A/B Test Servers** — Compare MCP server versions or implementations
- **Test CLI Tools** — Wrap command-line interfaces as testable servers
- **Compare Models** — Benchmark different LLMs against your tools
- **Compare System Prompts** — Find the system prompt that works best
- **Multi-Turn Sessions** — Test conversations that build on context
- **Agent Skills** — Add domain knowledge following [agentskills.io](https://agentskills.io)
- **AI-Powered Reports** — Get insights on what to fix, not just what failed

## Installation

```bash
uv add pytest-aitest
```

## Documentation

- [Getting Started](getting-started/index.md) — Write your first test
- [How-To Guides](how-to/index.md) — Solve specific problems
- [Reference](reference/index.md) — API and configuration details
- [Explanation](explanation/index.md) — Understand the design

## License

MIT
