# Example Reports

Live HTML reports showcasing pytest-aitest's adaptive reporting. Each report is generated from real test runs.

## Report Gallery

| Report | Mode | Description |
|--------|------|-------------|
| [**08_matrix_full.html**](08_matrix_full.html) | Matrix | 🌟 **Hero report** — All features: 2 models × 3 prompts with AI summary |
| [01_basic_usage.html](01_basic_usage.html) | Simple | Basic test list with pass/fail and tool usage |
| [02_model_comparison.html](02_model_comparison.html) | Model Comparison | Compare 2 models (gpt-5-mini vs gpt-4.1) |
| [03_prompt_comparison.html](03_prompt_comparison.html) | Prompt Comparison | Compare 3 system prompts |
| [04_matrix.html](04_matrix.html) | Matrix | 2 models × 3 prompts comparison grid |
| [05_sessions.html](05_sessions.html) | Sessions | Multi-turn conversation continuity |
| [06_with_ai_summary.html](06_with_ai_summary.html) | Simple + AI | Basic tests with AI-generated summary |
| [07_with_skipped.html](07_with_skipped.html) | Simple | Includes skipped tests |

## What Each Report Demonstrates

### 🌟 [08_matrix_full.html](08_matrix_full.html) — The Complete Picture

The **hero report** showcases every feature:

- **Summary Cards** — Pass rate, duration, token usage at a glance
- **Model Leaderboard** — Ranked comparison with medals (🥇🥈🥉)
- **Prompt Comparison** — Which system prompt performs best
- **Comparison Matrix** — Full prompt × model grid
- **Tool Usage Analysis** — Which tools were called, by which model
- **AI Summary** — LLM-generated analysis of the results
- **Detailed Results** — Expandable cards with conversation flow diagrams
- **Mermaid Diagrams** — Visual tool call sequences

### [01_basic_usage.html](01_basic_usage.html) — Simple Test List

What you get with no parametrization:
- Clean test list showing pass/fail status
- Individual test details with tool usage
- Conversation flow for each test

### [02_model_comparison.html](02_model_comparison.html) — Model Benchmark

Compare models side-by-side:
- **Model Leaderboard** — Ranked by pass rate, efficiency, cost
- **Test Results by Model** — See each test's outcome per model
- **Tool Comparison** — How models differ in tool selection

### [03_prompt_comparison.html](03_prompt_comparison.html) — Prompt Arena

Battle-test your system prompts:
- **Prompt Comparison Table** — Performance per prompt
- **Test Results by Prompt** — Which prompts handle which tasks
- Identify brittle prompts before production

### [04_matrix.html](04_matrix.html) — Full Grid Testing

When you need the full picture:
- **2D Matrix Grid** — Every model × prompt combination
- **Quick identification** of problematic pairings
- Surface interactions between model and prompt choices

### [05_sessions.html](05_sessions.html) — Multi-turn Conversations

Test stateful interactions:
- **Session continuity** — Context preserved across turns
- **Conversation flows** — See how context builds up
- Validate memory and state management

### [06_with_ai_summary.html](06_with_ai_summary.html) — AI-Powered Insights

Get LLM-generated analysis:
- **AI Summary Section** — High-level analysis of test results
- **Key findings** — What the AI noticed
- **Recommendations** — Suggested improvements

### [07_with_skipped.html](07_with_skipped.html) — Handling Skipped Tests

How skipped tests appear:
- **Skip badges** — Clear visual indicator
- **Skip reasons** — Why tests were skipped
- Proper handling in statistics

## Generating Your Own Reports

```bash
# Basic HTML report
pytest tests/ --aitest-html=report.html

# With AI summary
pytest tests/ --aitest-html=report.html \
    --aitest-summary \
    --aitest-summary-model=azure/gpt-4.1

# Regenerate from existing JSON
pytest-aitest-report results.json --html report.html
```

## Adaptive Sections

Reports **auto-compose** based on detected test dimensions:

| Pattern | Sections Shown |
|---------|---------------|
| No `@parametrize` | Summary → Test List |
| `@parametrize("model", ...)` | Summary → Model Leaderboard → Test Results by Model → Tool Comparison → Test List |
| `@parametrize("prompt", ...)` | Summary → Prompt Comparison → Test Results by Prompt → Test List |
| Both | Summary → Leaderboard → Comparison Matrix → Tool Comparison → Side-by-Side → Test List |

See [Reporting Documentation](../reporting.md) for full details.
