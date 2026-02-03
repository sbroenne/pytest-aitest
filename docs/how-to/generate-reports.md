# How to Generate Reports

Generate HTML, JSON, and Markdown reports with AI-powered insights.

## Quick Start

```bash
# Run tests with AI-powered HTML report
pytest tests/ \
    --aitest-summary-model=azure/gpt-5.1-chat \
    --aitest-html=report.html

# Multiple formats
pytest tests/ \
    --aitest-summary-model=azure/gpt-5.1-chat \
    --aitest-html=report.html \
    --aitest-md=report.md
```

!!! important
    AI insights are **mandatory** for report generation. You must specify `--aitest-summary-model`.

## CLI Options

| Option | Description |
|--------|-------------|
| `--aitest-html=PATH` | Generate HTML report |
| `--aitest-json=PATH` | Custom JSON path (default: `aitest-reports/results.json`) |
| `--aitest-md=PATH` | Generate Markdown report |
| `--aitest-summary-model=MODEL` | Model for AI insights (**required**) |

## pyproject.toml Configuration

Set defaults once:

```toml
[tool.pytest.ini_options]
addopts = """
--aitest-summary-model=azure/gpt-5.1-chat
--aitest-html=aitest-reports/report.html
"""
```

## Report Regeneration

Regenerate reports from saved JSON without re-running tests:

```bash
# Regenerate HTML from saved JSON
pytest-aitest-report aitest-reports/results.json \
    --html report.html \
    --summary-model azure/gpt-5.1-chat

# Use a different model for fresh analysis
pytest-aitest-report results.json \
    --html report.html \
    --summary-model azure/gpt-4.1
```

This is useful for:

- Iterating on report styling without re-running expensive LLM tests
- Generating different formats from one test run
- Experimenting with different AI summary models

## Adaptive Reports

Reports auto-detect test dimensions and adapt:

| Test Pattern | Report Shows |
|--------------|--------------|
| No parametrize | Test list |
| `@parametrize("model", ...)` | Model comparison table |
| `@parametrize("prompt", ...)` | Prompt comparison table |
| Both | 2D matrix grid |

### Mode Detection

```
Single Model + Single Prompt     → Basic Mode (test list only)
Multiple Models + Single Prompt  → Model Comparison Mode
Single Model + Multiple Prompts  → Prompt Comparison Mode  
Multiple Models + Multiple Prompts → Matrix Mode
```

### Leaderboard Ranking

When comparing models or prompts, rankings are based on:

1. **Pass rate** (primary) — higher is better
2. **Efficiency** (secondary) — passes per 1K tokens
3. **Total cost** (tiebreaker) — lower is better

## AI Insights

The AI analysis includes:

- **🎯 Recommendation** — Which configuration to deploy and why
- **❌ Failure Analysis** — Root cause + suggested fix for each failure
- **🔧 MCP Tool Feedback** — How to improve tool descriptions
- **📝 System Prompt Feedback** — Prompt improvements
- **📚 Agent Skill Feedback** — Skill restructuring suggestions
- **⚡ Optimizations** — Reduce turns/tokens

### Recommended Models

Use a capable model for quality analysis:

| Provider | Recommended Models |
|----------|-------------------|
| Azure OpenAI | `azure/gpt-5.1-chat`, `azure/gpt-4.1` |
| OpenAI | `openai/gpt-4o`, `openai/gpt-4.1` |
| Anthropic | `anthropic/claude-sonnet-4` |

!!! warning
    Smaller models (gpt-4o-mini, gpt-5-mini) produce generic, low-quality insights.

## HTML Report Contents

### Summary Dashboard

- Total/passed/failed counts
- Success rate
- Total tokens and cost

### Session Grouping

Tests using sessions are visually grouped:

- Session container with collapsible test list
- Summary stats: Duration, tokens, cost, tool calls
- Flow visualization showing message count between tests

### Model/Prompt Comparison

- Side-by-side metrics
- Success rates per configuration
- Token usage comparison

### Detailed Test Results

- Each test with pass/fail status
- Tool calls made
- Token usage and execution time

## JSON Report Structure

```json
{
  "summary": {
    "total": 10,
    "passed": 8,
    "failed": 2,
    "success_rate": 0.8
  },
  "dimensions": {
    "models": ["gpt-5-mini", "gpt-4.1"],
    "prompts": ["concise", "detailed"]
  },
  "tests": [
    {
      "name": "test_weather",
      "parameters": {
        "model": "gpt-5-mini",
        "prompt": "concise"
      },
      "passed": true,
      "duration_ms": 2500,
      "tokens": 450,
      "tool_calls": ["get_weather"]
    }
  ]
}
```

## CI/CD Integration

```yaml
# .github/workflows/test.yml
- name: Run agent tests
  run: |
    pytest tests/ \
      --aitest-html=reports/report.html \
      --aitest-json=reports/report.json \
      --aitest-md=reports/report.md \
      --aitest-summary-model=azure/gpt-5.1-chat

- name: Upload reports
  uses: actions/upload-artifact@v4
  with:
    name: test-reports
    path: reports/
```
