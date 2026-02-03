# Configuration

## Quick Start

pytest-aitest uses [LiteLLM](https://docs.litellm.ai/) for LLM access. Configure your provider once with standard environment variables.

### Azure OpenAI (Recommended)

```bash
export AZURE_API_BASE=https://your-resource.openai.azure.com/
az login
```

### OpenAI

```bash
export OPENAI_API_KEY=sk-xxx
```

### Other Providers

See [LiteLLM provider docs](https://docs.litellm.ai/docs/providers) for Anthropic, Google, etc.

## pyproject.toml

Set defaults once:

```toml
[tool.pytest.ini_options]
addopts = """
--aitest-summary-model=azure/gpt-5.1-chat
--aitest-html=aitest-reports/report.html
"""
```

## CLI Options

| Option | Description |
|--------|-------------|
| `--aitest-summary-model=MODEL` | Model for AI insights (required for reports) |
| `--aitest-html=PATH` | Generate HTML report |
| `--aitest-json=PATH` | Custom path for JSON report (default: `aitest-reports/results.json`) |
| `--aitest-md=PATH` | Generate Markdown report |

> **Note:** JSON is always generated to `aitest-reports/results.json` by default. Use `--aitest-json` only to specify a custom path.

## Report Regeneration CLI

Regenerate reports from existing JSON without re-running tests:

```bash
# Basic regeneration
pytest-aitest-report results.json --html report.html

# Generate multiple formats
pytest-aitest-report results.json --html report.html --md report.md

# Regenerate with fresh AI summary
pytest-aitest-report results.json --html report.html --summary --summary-model azure/gpt-5.1-chat
```

| Option | Description |
|--------|-------------|
| `--html PATH` | Generate HTML report |
| `--md PATH` | Generate Markdown report |
| `--summary` | Generate AI-powered summary (requires `--summary-model`) |
| `--summary-model MODEL` | LiteLLM model for AI summary |

### CLI Configuration

The CLI reads configuration with this precedence (highest to lowest):

1. **CLI arguments**: `--summary-model azure/gpt-5.1-chat`
2. **Environment variables**: `AITEST_SUMMARY_MODEL=azure/gpt-5.1-chat`
3. **pyproject.toml**:

```toml
[tool.pytest-aitest-report]
summary-model = "azure/gpt-5.1-chat"
```

## Provider

Each Agent uses one Provider. To compare different LLM providers or models, create multiple agents.

```python
from pytest_aitest import Provider

# Just the model - LiteLLM handles auth via env vars
provider = Provider(model="azure/gpt-5-mini")

# With generation parameters
provider = Provider(
    model="openai/gpt-4o-mini",
    temperature=0.7,
    max_tokens=1000,
)

# With rate limits (model-specific)
provider = Provider(
    model="azure/gpt-5-mini",
    rpm=10,    # Requests per minute
    tpm=10000, # Tokens per minute
)
```

## Agent

```python
from pytest_aitest import Agent, Provider

agent = Agent(
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[server],           # MCP servers
    cli_servers=[cli],              # CLI servers
    system_prompt="You are...",     # System Prompt (optional)
    skill=my_skill,                 # Agent Skill (optional)
    max_turns=10,                   # Max tool-call rounds
)
```

## Servers

### MCP Server

```python
from pytest_aitest import MCPServer, Wait

server = MCPServer(
    command=["python", "-m", "my_server"],
    wait=Wait.for_tools(["tool1", "tool2"]),
)
```

See **[MCP Server documentation](mcp-server.md)** for complete options.

### CLI Server

```python
from pytest_aitest import CLIServer

cli = CLIServer(
    name="git-cli",
    command="git",
    tool_prefix="git",  # Creates "git_execute" tool
)
```

See **[CLI Server documentation](cli-server.md)** for complete options.

## Fixtures

### Using aitest_run

```python
@pytest.mark.asyncio
async def test_weather(aitest_run):
    agent = Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[weather_server],
    )
    
    result = await aitest_run(agent, "What's the weather?")
    assert result.success
```

See **[Assertions documentation](assertions.md)** for complete API.

## Environment Variables

| Provider | Variable |
|----------|----------|
| Azure OpenAI | `AZURE_API_BASE` + `az login` |
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Google | `GEMINI_API_KEY` |

See [LiteLLM docs](https://docs.litellm.ai/docs/providers) for complete list.

## More Documentation

- **[MCP Server](mcp-server.md)** — MCP server configuration
- **[CLI Server](cli-server.md)** — CLI tool wrapper configuration  
- **[Assertions](assertions.md)** — AgentResult API and assertions
- **[Reporting](reporting.md)** — HTML/JSON reports
- **[API Reference](api-reference.md)** — Complete type reference
