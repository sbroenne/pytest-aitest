# CLI Options

## pytest Options

| Option | Description | Required |
|--------|-------------|----------|
| `--aitest-summary-model=MODEL` | Model for AI insights | Yes (for reports) |
| `--aitest-html=PATH` | Generate HTML report | No |
| `--aitest-json=PATH` | Custom JSON path | No (default: `aitest-reports/results.json`) |
| `--aitest-md=PATH` | Generate Markdown report | No |

### Examples

```bash
# Run tests with HTML report
pytest tests/ \
    --aitest-summary-model=azure/gpt-5.1-chat \
    --aitest-html=report.html

# All formats
pytest tests/ \
    --aitest-summary-model=azure/gpt-5.1-chat \
    --aitest-html=report.html \
    --aitest-json=results.json \
    --aitest-md=report.md
```

## pytest-aitest-report CLI

Regenerate reports from saved JSON without re-running tests.

```bash
pytest-aitest-report <json-file> [options]
```

| Option | Description | Required |
|--------|-------------|----------|
| `--html PATH` | Generate HTML report | No |
| `--md PATH` | Generate Markdown report | No |
| `--summary-model MODEL` | Model for AI insights | Yes |

### Examples

```bash
# Regenerate HTML
pytest-aitest-report results.json \
    --html report.html \
    --summary-model azure/gpt-5.1-chat

# Multiple formats
pytest-aitest-report results.json \
    --html report.html \
    --md report.md \
    --summary-model azure/gpt-5.1-chat

# Different model for fresh analysis
pytest-aitest-report results.json \
    --html report.html \
    --summary-model azure/gpt-4.1
```

## pyproject.toml Configuration

Set defaults once:

```toml
[tool.pytest.ini_options]
addopts = """
--aitest-summary-model=azure/gpt-5.1-chat
--aitest-html=aitest-reports/report.html
"""
```

## Environment Variables

LLM authentication is handled by [LiteLLM](https://docs.litellm.ai/docs/providers):

| Provider | Variable |
|----------|----------|
| Azure OpenAI | `AZURE_API_BASE` + `az login` |
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Google | `GEMINI_API_KEY` |

### Azure OpenAI Setup

```bash
# Set endpoint
export AZURE_API_BASE=https://your-resource.openai.azure.com/

# Authenticate (no API key needed!)
az login
```

### OpenAI Setup

```bash
export OPENAI_API_KEY=sk-xxx
```
