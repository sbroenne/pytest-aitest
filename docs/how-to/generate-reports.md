# How to Generate Reports

Generate HTML, JSON, and Markdown reports with AI-powered insights.

## Quick Start (Recommended)

Configure once in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = """
--aitest-summary-model=azure/gpt-5.2-chat
--aitest-html=aitest-reports/report.html
"""
```

Then just run:

```bash
pytest tests/
```

Reports are generated automatically with AI insights. This approach is recommended because:

- **Version controlled** — Team shares the same configuration
- **Less typing** — No need to remember CLI flags
- **Consistent** — Every run produces reports the same way

!!! important
    AI insights are **mandatory** for report generation. You must specify `--aitest-summary-model`.

## CLI Options (Alternative)

You can also use CLI flags directly:

```bash
# Run tests with AI-powered HTML report
pytest tests/ \
    --aitest-summary-model=azure/gpt-5.2-chat \
    --aitest-html=report.html

```

| Option | Description |
|--------|-------------|
| `--aitest-html=PATH` | Generate HTML report |
| `--aitest-json=PATH` | Custom JSON path (default: `aitest-reports/results.json`) |
| `--aitest-summary-model=MODEL` | Model for AI insights (**required**) |

## Report Regeneration

Regenerate reports from saved JSON without re-running tests:

```bash
# Regenerate HTML from saved JSON
pytest-aitest-report aitest-reports/results.json \
    --html report.html \
    --summary-model azure/gpt-5.2-chat

# Force regeneration with a different model
pytest-aitest-report results.json \
    --html report.html \
    --summary-model azure/gpt-4.1 \
    --regenerate
```

This is useful for:

- Iterating on report styling without re-running expensive LLM tests
- Generating different formats from one test run
- Experimenting with different AI summary models

## Agent Leaderboard

When you test multiple agents, the report shows an **Agent Leaderboard** ranking all configurations:

| Agent | Pass Rate | Cost |
|-------|-----------|------|
| ✓ gpt-4.1 (detailed) | 100% | $0.15 |
| ✓ gpt-5-mini (detailed) | 97% | $0.03 |
| ✗ gpt-5-mini (concise) | 82% | $0.02 |

**Winning Agent = Highest pass rate → Lowest cost (tiebreaker)**

Use `--aitest-min-pass-rate=N` to disqualify agents below N%:

```bash
pytest tests/ --aitest-min-pass-rate=95
```

### Dimension Detection

The AI detects *what varies* between agents to focus its analysis:

| What Varies | AI Analysis Focuses On |
|-------------|------------------------|
| Model | Which model works best |
| System Prompt | Which instructions work best |
| Skill | Whether domain knowledge helps |
| Server | Which implementation is more reliable |

**Winning = Highest pass rate → Lowest cost (tiebreaker)**

### Threshold Filtering

Disqualify agents below a minimum pass rate:

```bash
pytest tests/ --aitest-min-pass-rate=95
```

Agents below threshold are grayed out but still shown for reference.

### Leaderboard Ranking

When comparing Agents, rankings are based on:

1. **Pass rate** (primary) — higher is better
2. **Efficiency** (secondary) — passes per 1K tokens
3. **Total cost** (tiebreaker) — lower is better

## AI Insights

Reports include AI-powered analysis with actionable recommendations. For a detailed explanation of each insight section, see [AI-Powered Reports](../explanation/ai-reports.md).

### Recommended Models

Use the **most capable model you can afford** for quality analysis:

| Provider | Recommended Models |
|----------|-------------------|
| Azure OpenAI | `azure/gpt-5.2-chat` (best), `azure/gpt-4.1` |
| OpenAI | `openai/gpt-4.1`, `openai/gpt-4o` |
| Anthropic | `anthropic/claude-opus-4`, `anthropic/claude-sonnet-4` |

!!! warning "Don't Use Cheap Models for Analysis"
    Smaller models (gpt-4o-mini, gpt-5-mini) produce generic, low-quality insights.
    The summary model analyzes your test results and generates actionable feedback.
    Use your most capable model here—this is a one-time cost per test run.

## Report Structure

For details on the HTML report layout including header, leaderboard, and test details, see [Report Structure](../explanation/report-structure.md).

## JSON Report Structure

```json
{
  "schema_version": "3.0",
  "mode": "model_comparison",
  "summary": {
    "total": 10,
    "passed": 8,
    "failed": 2,
    "pass_rate": 80.0
  },
  "dimensions": {
    "models": ["gpt-5-mini", "gpt-4.1"],
    "prompts": ["concise", "detailed"]
  },
  "insights": {
    "markdown_summary": "## 🎯 Recommendation\n\n...",
    "recommendation": {...},
    "failures": [...],
    "mcp_feedback": [...]
  },
  "tests": [...]
}
```

## CI/CD Integration

### JUnit XML for CI Pipelines

pytest includes built-in JUnit XML output that works with all CI systems. Use it alongside aitest reports:

```bash
pytest tests/ \
    --junitxml=results.xml \
    --aitest-html=report.html \
    --aitest-summary-model=azure/gpt-5.2-chat
```

| Format | Purpose | Consumers |
|--------|---------|----------|
| `--junitxml` | Pass/fail tracking, test history | GitHub Actions, Azure Pipelines, Jenkins |
| `--aitest-html` | AI insights, tool analysis | Human review |
| `--aitest-json` | Raw data for custom tooling | Scripts, dashboards |

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
- name: Run agent tests
  run: |
    pytest tests/ \
      --junitxml=reports/results.xml \
      --aitest-html=reports/report.html \
      --aitest-json=reports/report.json \
      --aitest-summary-model=azure/gpt-5.2-chat

- name: Upload test results
  uses: actions/upload-artifact@v4
  if: always()
  with:
    name: test-reports
    path: reports/

- name: Publish JUnit results
  uses: dorny/test-reporter@v1
  if: always()
  with:
    name: Test Results
    path: reports/results.xml
    reporter: java-junit
```

### Azure Pipelines Example

```yaml
- task: PublishTestResults@2
  inputs:
    testResultsFormat: 'JUnit'
    testResultsFiles: 'reports/results.xml'
  condition: always()
```
