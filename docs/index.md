# pytest-aitest

**Test AI agents the way they actually fail.**

pytest-aitest is a pytest plugin for testing MCP servers and CLI tools through the lens of an LLM. You write tests as natural language prompts, and an LLM executes them against your tools.

## Why?

MCP servers and CLIs have two problems nobody talks about:

1. **Design** — Your tool descriptions, parameter names, and error messages are the entire API for LLMs. Getting them right is hard.
2. **Testing** — Traditional tests can't verify if an LLM can actually understand and use your tools.

- Bad tool description? The LLM picks the wrong tool.
- Confusing parameter name? The LLM passes garbage.
- Unhelpful error message? The LLM can't recover.

**The key insight: your test is a prompt.** You write what a user would say, and the LLM figures out how to use your tools. If it can't, your tool descriptions need work.

## Quick Start

```python
from pytest_aitest import Agent, Provider, MCPServer

weather_server = MCPServer(command="python", args=["weather_mcp.py"])

agent = Agent(
    name="weather-test",
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[weather_server],
)

@pytest.mark.asyncio
async def test_weather_query(aitest_run):
    result = await aitest_run(agent, "What's the weather in Paris?")
    
    assert result.success
    assert result.tool_was_called("get_weather")
```

## Features

- **Test MCP Servers** — Verify LLMs can discover and use your tools
- **A/B Test Servers** — Compare MCP server versions or implementations
- **Test CLI Tools** — Wrap command-line interfaces as testable servers
- **Compare Models** — Benchmark different LLMs against your tools
- **Compare Prompts** — Find the system prompt that works best
- **Multi-Turn Sessions** — Test conversations that build on context
- **Agent Skills** — Add domain knowledge following [agentskills.io](https://agentskills.io)
- **AI-Powered Reports** — Get insights on what to fix, not just what failed

## Installation

```bash
pip install pytest-aitest
```

## Documentation

- [Getting Started](getting-started/index.md) — Write your first test
- [How-To Guides](how-to/index.md) — Solve specific problems
- [Reference](reference/index.md) — API and configuration details
- [Explanation](explanation/index.md) — Understand the design

## License

MIT
