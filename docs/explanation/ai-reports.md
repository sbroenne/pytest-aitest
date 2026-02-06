# AI-Powered Reports

Why AI analysis is mandatory and what makes these reports different.

## The Problem with Metrics

Traditional test reports show you metrics:

```
Tests: 47 passed, 3 failed
Duration: 2m 34s
Coverage: 87%
```

This tells you *what* failed, not *why* or *what to fix*.

For AI tool testing, this is even worse because failures are often about **interface quality**, not bugs. A test might fail because:

- Your tool description is ambiguous
- Your parameter name is confusing
- Your error message doesn't help the LLM recover
- Your system prompt contradicts itself

Metrics can't diagnose these problems. AI can.

## Mandatory AI Analysis

pytest-aitest **requires** an AI model to generate reports:

```bash
pytest tests/ --aitest-html=report.html --aitest-summary-model=azure/gpt-5.2-chat
```

This is intentional. Without AI analysis, reports would just show pass/fail metrics. With it, you get **actionable insights**.

> **Note:** If you request `--aitest-html` without `--aitest-summary-model`, pytest will error.

## The Six Insight Sections

Every report includes these AI-generated sections:

### 🎯 Recommendation

Which Agent to deploy and why:

> **Winner: gpt-5-mini / DETAILED / weather-expert**
> 
> 100% pass rate at $0.03/test. Outperformed 5 other configurations.
> 
> **Why it won:** The DETAILED prompt + weather-expert skill combination
> gave the agent enough context to use tools correctly on first try.

### 🏆 Agent Leaderboard

When comparing multiple Agents, a ranked table:

> | Rank | Agent | Pass Rate | Cost |
> |------|-------|-----------|------|
> | 1 | gpt-5-mini / DETAILED / weather-expert | 100% | $0.03 |
> | 2 | gpt-4.1 / DETAILED / weather-expert | 100% | $0.15 |
> | 3 | gpt-5-mini / CONCISE / none | 82% | $0.02 |
>
> **Dimension Impact:**
> - Adding weather-expert skill: +15% pass rate
> - DETAILED vs CONCISE prompt: +8% pass rate
> - gpt-4.1 vs gpt-5-mini: No accuracy gain, 5x cost increase

### ❌ Failure Analysis

For each failed test, root cause + suggested fix:

> **test_complex_query** failed because the LLM couldn't parse the 
> multi-step instruction. The tool `search_products` was called with 
> an empty query.
>
> **Fix:** Split into separate prompts or add examples to the system 
> prompt showing multi-step queries.

### 🔧 MCP Server Feedback

Specific improvements to tool descriptions:

> **get_weather** — The `loc` parameter is ambiguous. LLMs tried 
> coordinates, airport codes, and city names.
>
> **Suggested description:**
> ```python
> def get_weather(city: str) -> dict:
>     """Get weather for a city by name.
>     
>     Args:
>         city: City name like "Paris" or "New York"
>     """
> ```

### 📝 System Prompt Feedback

System prompt improvements:

> Your prompt says "be concise" but also "explain your reasoning."
> The LLM oscillates between styles.
>
> **Suggestion:** Remove "be concise" or add "explain briefly."

### 📚 Skill Feedback

For agents with skills, improvement suggestions:

> The weather-expert skill lists clothing recommendations but doesn't
> explain temperature thresholds. The LLM guessed wrong on edge cases.
>
> **Add to skill:** "Below 10°C: warm jacket. 10-20°C: light jacket."

### 🔄 Server A/B Results

When comparing server implementations:

> **Winner: weather_server_v2**
> 
> v2 achieved 100% pass rate vs v1's 85%. The improved error messages
> in v2 helped the LLM recover from invalid city names.

### ⚡ Optimizations

Reduce turns and tokens:

> Tests average 4.2 turns. Adding tool output examples to the system
> prompt could reduce this to ~2 turns, cutting costs by 50%.

## Agent Leaderboard

When you test multiple agents, the report shows an **Agent Leaderboard** ranking all configurations.

| Agent | Pass Rate | Cost |
|-------|-----------|------|
| gpt-5-mini (concise) | 100% | $0.002 |
| gpt-4.1 (concise) | 100% | $0.008 |
| gpt-5-mini (detailed) | 100% | $0.004 |

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
| Skill | Whether knowledge helps |
| Server | Which implementation wins |

This helps the AI provide targeted recommendations.

## Example Report

Here's what a real report looks like:

![Report Screenshot](../images/report-example.png)

The AI summary appears at the top with the Agent Leaderboard, followed by detailed test results, tool information, and raw data for debugging.

## The Analysis Prompt

The AI analysis is generated using a structured prompt located at:

```
src/pytest_aitest/prompts/ai_summary.md
```

### What the AI Analyzes

The prompt analyzes test results and produces structured insights:

| Output | Description |
|--------|-------------|
| **Recommendation** | Which configuration to deploy and why |
| **Failure Analysis** | Root cause + fix for each failing test |
| **MCP Server Feedback** | Tool description improvements |
| **System Prompt Feedback** | Instruction improvements |
| **Skill Feedback** | Domain knowledge improvements |
| **Optimizations** | Token/turn reduction opportunities |

### Strict Rules

The prompt enforces these rules for consistent output:

1. **No speculation** — Only analyze what's in the test results
2. **No generic advice** — Every suggestion must reference specific test data
3. **Exact rewrites required** — Don't say "make it clearer", provide the exact new text
4. **Use test IDs** — Reference specific tests when discussing failures
5. **Be concise** — Quality over quantity; 3 good insights > 10 vague ones

### Customizing the Prompt

Currently, the prompt is embedded in the package. To customize:

1. Fork the repository
2. Edit `src/pytest_aitest/prompts/ai_summary.md`
3. Install your fork: `pip install -e /path/to/fork`

!!! note "Future: Custom Prompt Support"
    A future release will add `--aitest-analysis-prompt` to specify a custom prompt file.

## Cost Considerations

The summary model analyzes your test results, which are relatively small. Typical costs:

| Tests | Input Tokens | Cost (gpt-5.2-chat) |
|-------|--------------|---------------------|
| 10    | ~2,000       | $0.01               |
| 50    | ~8,000       | $0.04               |
| 200   | ~30,000      | $0.15               |

The insights are worth far more than the cost.
