# Reporting

Generate HTML, JSON, and Markdown reports with auto-detected comparison views.

## Quick Start

```bash
# Run tests - JSON is always generated to aitest-reports/results.json
pytest tests/

# Generate HTML report
pytest tests/ --aitest-html=report.html

# Generate Markdown report
pytest tests/ --aitest-md=report.md

# Multiple formats
pytest tests/ --aitest-html=report.html --aitest-md=report.md

# With AI-powered summary
pytest tests/ --aitest-html=report.html --aitest-summary --aitest-summary-model=azure/gpt-4.1
```

## Report Regeneration

Regenerate reports from existing JSON without re-running tests. This is useful for:
- Iterating on report styling without expensive LLM calls
- Generating different formats from one test run
- Experimenting with AI summary models

```bash
# Regenerate HTML from saved JSON
pytest-aitest-report aitest-reports/results.json --html report.html

# Generate multiple formats
pytest-aitest-report results.json --html report.html --md report.md

# Regenerate with fresh AI summary (uses different model)
pytest-aitest-report results.json --html report.html --summary --summary-model azure/gpt-4.1
```

## CLI Options

### pytest options

| Option | Description |
|--------|-------------|
| `--aitest-html=PATH` | Generate HTML report |
| `--aitest-json=PATH` | Custom JSON path (default: `aitest-reports/results.json`) |
| `--aitest-md=PATH` | Generate Markdown report |
| `--aitest-summary` | Include AI-powered analysis |
| `--aitest-summary-model=MODEL` | Model for AI summary (required with `--aitest-summary`). Use a capable model like `gpt-4.1`. |

### pytest-aitest-report options

| Option | Description |
|--------|-------------|
| `--html PATH` | Generate HTML report |
| `--md PATH` | Generate Markdown report |
| `--summary` | Generate AI-powered summary |
| `--summary-model MODEL` | Model for AI summary (required with `--summary`) |

## pyproject.toml Configuration

Set defaults once:

```toml
[tool.pytest.ini_options]
addopts = """
--aitest-model=azure/gpt-5-mini
--aitest-summary-model=azure/gpt-4.1
--aitest-html=reports/report.html
"""
```

## Adaptive Reports

Reports auto-detect test dimensions from `@pytest.mark.parametrize` and adapt:

| Test Pattern | Report Shows |
|--------------|--------------|
| No parametrize | Test list |
| `@parametrize("model", ...)` | Model comparison table |
| `@parametrize("prompt", ...)` | Prompt comparison table |
| Both | 2D matrix grid |

### Adaptive Display Rules

The HTML report automatically shows or hides sections based on test results. This ensures reports are clean and focused—showing only relevant information.

| Section | Display Condition |
|---------|-------------------|
| **Model Leaderboard** | 2+ models tested |
| **Prompt Comparison** | 2+ prompts tested AND NOT matrix mode |
| **Matrix Grid** | 2+ models AND 2+ prompts (shows prompts as rows, models as columns) |
| **Tool Comparison** | Comparison mode (models or prompts) AND tests used tools |
| **Side-by-Side Details** | Matrix mode only (deep-dive per prompt×model) |
| **Session Groups** | Any test uses session continuity |
| **AI Summary** | `--aitest-summary` flag enabled |
| **Detailed Results** | Always shown (collapsible per test) |

### Mode Detection

The report generator detects the test mode automatically:

```
Single Model + Single Prompt  → Basic Mode (test list only)
Multiple Models + Single Prompt → Model Comparison Mode
Single Model + Multiple Prompts → Prompt Comparison Mode  
Multiple Models + Multiple Prompts → Matrix Mode
```

### Leaderboard Ranking

When comparing models or prompts, the leaderboard ranks by:

1. **Pass rate** (primary) - higher is better
2. **Efficiency** (secondary) - passes per 1K tokens, higher is better
3. **Total cost** (tiebreaker) - lower is better

Rankings display medals: 🥇 Gold, 🥈 Silver, 🥉 Bronze

### Simple Test List

With no parametrize, you get a clean test list:

```python
@pytest.mark.asyncio
async def test_weather(aitest_run, agent):
    result = await aitest_run(agent, "What's the weather?")
    assert result.success
```

### Model Comparison

Parametrize on model to get a comparison table:

```python
@pytest.mark.parametrize("model", ["gpt-5-mini", "gpt-4.1"])
@pytest.mark.asyncio
async def test_weather(aitest_run, model):
    agent = Agent(provider=Provider(model=f"azure/{model}"), ...)
    result = await aitest_run(agent, "What's the weather?")
    assert result.success
```

Report shows:
- Pass rate per model
- Token usage per model
- Cost comparison

### Prompt Comparison

Parametrize on prompt to compare prompts:

```python
PROMPTS = [
    Prompt(name="concise", system_prompt="Be brief."),
    Prompt(name="detailed", system_prompt="Be thorough."),
]

@pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
@pytest.mark.asyncio
async def test_weather(aitest_run, prompt):
    agent = Agent(system_prompt=prompt.system_prompt, ...)
    result = await aitest_run(agent, "What's the weather?")
    assert result.success
```

### Matrix Comparison

Combine both for full grid:

```python
@pytest.mark.parametrize("model", ["gpt-5-mini", "gpt-4.1"])
@pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
@pytest.mark.asyncio
async def test_matrix(aitest_run, model, prompt):
    ...
```

Report shows a 2D matrix: models vs prompts.

## AI Summary

Enable AI-powered analysis of test results:

```bash
pytest tests/ --aitest-html=report.html --aitest-summary --aitest-summary-model=azure/gpt-4.1
```

**`--aitest-summary-model` is required** when using `--aitest-summary`. Use a capable model for quality analysis:

| Provider | Recommended Models |
|----------|-------------------|
| Azure OpenAI | `azure/gpt-4.1`, `azure/gpt-4o` |
| OpenAI | `openai/gpt-4o`, `openai/gpt-4.1` |
| Anthropic | `anthropic/claude-sonnet-4`, `anthropic/claude-3-5-sonnet` |

**Note:** Smaller models (gpt-4o-mini, gpt-5-mini) produce generic, low-quality summaries. Use a capable model.

### Multi-Model Comparison

When tests are parametrized by model, the AI summary provides:
- **Verdict**: Which model to recommend and why
- **Per-model breakdown**: Pass rate, tokens, cost
- **Key differences**: Capability gaps, cost tradeoffs
- **Actionable recommendation**: Which model for production

### Single-Model Evaluation

For non-parametrized tests, the summary assesses:
- Model fitness for the task
- Failure patterns
- Recommendations

## HTML Report Contents

The HTML report includes:

### Summary Dashboard
- Total/passed/failed counts
- Success rate
- Total tokens and cost

### Session Grouping
Tests using [sessions](sessions.md) (multi-turn conversations) are visually grouped:

- **🔗 Session container** with collapsible test list
- **Summary stats**: Duration, tokens, cost, tool calls for entire session
- **Flow visualization**: Shows message count passed between tests
- **Grouped by test class**: Tests in the same class with session continuity

### Model/Prompt Comparison (if parametrized)
- Side-by-side metrics
- Success rates
- Token usage

### Detailed Test Results
- Each test with pass/fail status
- Tool calls made
- Token usage
- Execution time

### AI Summary (if enabled)
- LLM-generated analysis
- Recommendations

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

## Markdown Report

The markdown format is useful for documentation and GitHub wikis. It includes:

- **Summary table** with pass rate, tokens, and duration
- **Model/prompt comparison tables** (GitHub-flavored markdown)
- **Test results** with status indicators (✅/❌)
- **Collapsible sections** for error details and agent responses (using `<details>` tags)

Example output:

```markdown
# pytest-aitest

**Generated:** 2026-02-02T10:30:00
**Duration:** 15.50s

## Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 10 |
| **Passed** | 8 ✅ |
| **Failed** | 2 ❌ |
| **Pass Rate** | 80.0% |
| **Total Tokens** | 4,500 |

## Model Comparison

| Model | Pass Rate | Passed | Failed | Tokens | Cost |
|-------|-----------|--------|--------|--------|------|
| gpt-4.1 | 100% | 5 | 0 | 2,100 | $0.0042 |
| gpt-5-mini | 60% | 3 | 2 | 2,400 | $0.0024 |

## Test Results

### ✅ Weather lookup returns valid data
- **Status:** passed
- **Duration:** 1.25s
- **Model:** gpt-4.1
- **Tokens:** 450
- **Tools:** `get_weather`
```

## Report Examples

### Basic Usage

```bash
# Run tests and generate report
pytest tests/integration/ --aitest-html=report.html

# Open report
open report.html
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
- name: Run agent tests
  run: |
    pytest tests/ \
      --aitest-html=reports/report.html \
      --aitest-json=reports/report.json \
      --aitest-md=reports/report.md

- name: Upload reports
  uses: actions/upload-artifact@v4
  with:
    name: test-reports
    path: reports/
```

### Compare Models in CI

```yaml
- name: Benchmark models
  run: |
    pytest tests/integration/test_benchmark.py \
      --aitest-html=benchmark-report.html \
      --aitest-summary --aitest-summary-model=azure/gpt-4.1
```
