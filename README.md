# pytest-aitest

[![PyPI version](https://img.shields.io/pypi/v/pytest-aitest)](https://pypi.org/project/pytest-aitest/)
[![Python versions](https://img.shields.io/pypi/pyversions/pytest-aitest)](https://pypi.org/project/pytest-aitest/)
[![CI](https://github.com/sbroenne/pytest-aitest/actions/workflows/ci.yml/badge.svg)](https://github.com/sbroenne/pytest-aitest/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# Test your AI interfaces. Get actionable AI-powered insights.

A pytest plugin for validating whether language models can understand and operate your MCP servers, tools, prompts, and skills. Generates AI-powered insights & reports that tell you *what to fix*, not just *what failed*.

## The Problem

Your MCP server passes all unit tests. Then an LLM tries to use it and:

- Picks the wrong tool
- Passes garbage parameters
- Can't recover from errors
- Ignores your system prompt instructions

**Why?** Because you tested the code, not the AI interface.

For LLMs, your API isn't functions and types — it's **tool descriptions, system prompts, skills, and schemas**. These are what the LLM actually sees. Traditional tests can't validate them.

## The Solution

Write tests as natural language prompts. An **Agent** is your test harness — it combines an LLM provider, MCP servers, and optional configuration:

```python
@pytest.mark.asyncio
async def test_weather_comparison(aitest_run, weather_server):
    agent = Agent(
        provider=Provider(model="azure/gpt-5-mini"),   # LLM provider
        mcp_servers=[weather_server],                  # MCP servers with tools
        system_prompt="Be concise.",                   # System Prompt (optional)
        skill=weather_skill,                           # Agent Skill (optional)
    )

    result = await aitest_run(
        agent,
        "Compare weather in Paris and Tokyo. Which is better for a picnic?",
    )

    assert result.success
    assert result.tool_was_called("get_weather")
```

The agent runs your prompt, calls tools, and returns results. You assert on what happened. If the test fails, your tool descriptions need work — not your code.

**What you're testing:**

| Component | Question It Answers |
|-----------|---------------------|
| MCP Server | Can an LLM understand and use my tools? |
| System Prompt | Does this behavior definition produce the results I want? |
| Agent Skill | Does this domain knowledge help the agent perform? |

See [Getting Started](docs/getting-started/index.md) for details on each component.

## What Makes This Different

### AI-Powered Reports

Reports don't just show pass/fail — they tell you **what to do**. Here's actual output from a test run:

> # pytest-aitest
>
> ✅ **2 passed** · ⏱️ 16.8s · 💰 $0.001
>
> ## 🎯 Recommendation
>
> **Deploy `gpt-5-mini / default`**
>
> Deploy the existing configuration as-is; it achieves a 100% pass rate on the tested scenarios with correct tool usage.
>
> ## 🔧 Tool Improvements
>
> | Tool | Status | Issue |
> |------|--------|-------|
> | `get_balance` | ✅ working | None |
> | `get_budgets` | ✅ working | None |
> | `get_all_balances` | ➖ unused | Not exercised by any test cases |
>
> <details>
> <summary>💡 Suggested description for <code>get_all_balances</code></summary>
>
> `Get balances for all accounts at once. Use when the user asks for an overview of all accounts or total balance.`
> </details>

*Generates both Markdown (for GitHub PRs) and [interactive HTML reports](https://sbroenne.github.io/pytest-aitest/demo/hero-report.html) with sequence diagrams.*

### Compare Configurations

Use pytest parametrize to find what works best:

```python
@pytest.mark.parametrize("model", ["gpt-5-mini", "gpt-4.1"])
@pytest.mark.asyncio
async def test_tool_usage(aitest_run, weather_server, model):
    agent = Agent(provider=Provider(model=f"azure/{model}"), ...)
    result = await aitest_run(agent, "What's the weather in Paris?")
    assert result.success
```

Reports show which model/prompt/Agent Skill combination performs best.

### Multi-Turn Sessions

Test conversations that build on context:

```python
@pytest.mark.session("banking-flow")
class TestBankingWorkflow:
    async def test_check_balance(self, aitest_run, bank_agent):
        result = await aitest_run(bank_agent, "What's my balance?")
        assert result.success

    async def test_transfer(self, aitest_run, bank_agent):
        # Remembers context from previous test
        result = await aitest_run(bank_agent, "Transfer $100 to savings")
        assert result.tool_was_called("transfer")
```

## Quick Start

### Install

```bash
uv add pytest-aitest
# or
pip install pytest-aitest

# For Azure OpenAI with Entra ID authentication
pip install pytest-aitest[azure]
```

### Configure

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = """
--aitest-summary-model=azure/gpt-5.2-chat
--aitest-html=aitest-reports/report.html
"""
```

Set your LLM provider credentials:

```bash
# Azure (recommended)
export AZURE_API_BASE=https://your-resource.openai.azure.com/
az login

# Or OpenAI
export OPENAI_API_KEY=sk-xxx
```

See [LiteLLM docs](https://docs.litellm.ai/docs/providers) for 100+ supported providers.

### Write Tests

```python
# test_my_mcp_server.py
import pytest
from pytest_aitest import Agent, Provider, MCPServer

@pytest.fixture
def my_server():
    return MCPServer(command=["python", "-m", "my_mcp_server"])

@pytest.mark.asyncio
async def test_basic_query(aitest_run, my_server):
    agent = Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[my_server],
    )
    result = await aitest_run(agent, "Do something useful")
    assert result.success
```

### Run

```bash
pytest tests/
```

Reports with AI insights are generated automatically based on your `pyproject.toml` config.

## Features at a Glance

| Feature | Description |
|---------|-------------|
| **MCP Server Testing** | Real models against real tool interfaces |
| **CLI Server Testing** | Test CLIs as if they were MCP servers |
| **Agent Comparison** | Compare any combination of Model, Prompt, Skill, Server |
| **Agent Leaderboard** | Ranked by pass rate → cost |
| **Threshold Filtering** | Disqualify agents below minimum pass rate |
| **Multi-Turn Sessions** | `@pytest.mark.session` for conversations |
| **AI Judge** | Semantic assertions via [pytest-llm-assert](https://github.com/sbroenne/pytest-llm-assert) |
| **AI-Powered Reports** | Actionable insights, not just metrics |

## How Comparison Works

An **Agent** is a configuration: Model + System Prompt + Skill + Server(s).

pytest-aitest auto-detects what varies between agents:

| What Varies | Report Shows |
|-------------|--------------|
| Only Model | Model Comparison + Leaderboard |
| Only Prompt | Prompt Comparison + Leaderboard |
| Only Skill | Skill Comparison + Leaderboard |
| Only Server | Server A/B Comparison |
| Model + Prompt | Model × Prompt Matrix |
| Multiple | Agent Leaderboard (all dimensions) |

**Winning Agent:** Highest pass rate → Lowest cost (tiebreaker)

Use `--aitest-min-pass-rate=95` to disqualify agents below 95%.

**[→ See the complete example guide](docs/how-to/complete-example.md)**

## Documentation

📚 **[Full Documentation](https://sbroenne.github.io/pytest-aitest/)** (coming soon)

- **[Getting Started](docs/getting-started/index.md)** — Write your first test
- **[How-To Guides](docs/how-to/index.md)** — Solve specific problems
- **[Reference](docs/reference/index.md)** — API and configuration
- **[Explanation](docs/explanation/index.md)** — Design philosophy

## Why pytest?

This is a **pytest plugin**, not a standalone tool.

- Use existing fixtures, markers, parametrize
- Works with CI/CD pipelines  
- Combine with other pytest plugins
- No new syntax to learn

## Who This Is For

- **MCP server authors** — Validate tool descriptions work
- **Agent builders** — Compare models and prompts
- **Teams shipping AI systems** — Catch LLM-facing regressions
- **Anyone with tools LLMs operate** — Test the actual interface

## Requirements

- Python 3.11+
- pytest 9.0+
- An LLM provider (Azure, OpenAI, Anthropic, etc.)

## Related

- **[pytest-llm-assert](https://github.com/sbroenne/pytest-llm-assert)** — Semantic assertions
- **[Contributing](CONTRIBUTING.md)** — Development setup

## License

MIT
