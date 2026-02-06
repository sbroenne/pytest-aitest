# CLI Options

## Recommended: pyproject.toml

Configure once, run simply:

```toml
[tool.pytest.ini_options]
addopts = """
--aitest-summary-model=azure/gpt-5.2-chat
--aitest-html=aitest-reports/report.html
"""
```

Then just `pytest tests/` — reports are generated automatically.

## pytest Options

| Option | Description | Required |
|--------|-------------|----------|
| `--aitest-summary-model=MODEL` | Model for AI insights | Yes (for reports) |
| `--aitest-html=PATH` | Generate HTML report | No |
| `--aitest-json=PATH` | Custom JSON path | No (default: `aitest-reports/results.json`) |
| `--aitest-min-pass-rate=N` | Disqualify agents below N% pass rate | No (default: 0) |

### CLI Examples

```bash
# Run tests with HTML report
pytest tests/ \
    --aitest-summary-model=azure/gpt-5.2-chat \
    --aitest-html=report.html

# With threshold: only consider agents with ≥95% pass rate
pytest tests/ \
    --aitest-summary-model=azure/gpt-5.2-chat \
    --aitest-html=report.html \
    --aitest-min-pass-rate=95

# With JSON output
pytest tests/ \
    --aitest-summary-model=azure/gpt-5.2-chat \
    --aitest-html=report.html \
    --aitest-json=results.json
```

## pytest-aitest-report CLI

Regenerate reports from saved JSON without re-running tests.

```bash
pytest-aitest-report <json-file> [options]
```

| Option | Description | Required |
|--------|-------------|----------|
| `--html PATH` | Generate HTML report | No |
| `--summary-model MODEL` | Model for AI insights | Yes* |
| `--regenerate` | Force regeneration of AI insights | No |

\* Required if JSON has placeholder insights. Can also be set via `AITEST_SUMMARY_MODEL` env var or `pyproject.toml`.

### Examples

```bash
# Regenerate HTML (if JSON already has real insights)
pytest-aitest-report results.json --html report.html

# Generate with AI analysis (required if JSON has placeholder insights)
pytest-aitest-report results.json \
    --html report.html \
    --summary-model azure/gpt-5.2-chat

# Multiple formats
pytest-aitest-report results.json \
    --html report.html \
    --md report.md \
    --summary-model azure/gpt-5.2-chat

# Force fresh AI analysis with different model
pytest-aitest-report results.json \
    --html report.html \
    --summary-model azure/gpt-4.1 \
    --regenerate
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
