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

pytest-aitest requires an AI model to generate reports:

```bash
pytest tests/ --aitest-html=report.html --aitest-summary-model=azure/gpt-5-mini
```

This is intentional. Without AI analysis, you get a list of failures. With it, you get **actionable insights**.

## The Six Insight Sections

Every report includes these AI-generated sections:

### 🎯 Recommendation

High-level deployment guidance:

> **Recommend: gpt-5-mini**
> 
> Best balance of cost ($0.002/test) and reliability (94% pass rate).
> gpt-4.1 scored 97% but costs 8x more with marginal improvement.

### ❌ Failure Analysis

For each failed test, root cause + suggested fix:

> **test_complex_query** failed because the LLM couldn't parse the 
> multi-step instruction. The tool `search_products` was called with 
> an empty query.
>
> **Fix:** Split into separate prompts or add examples to the system 
> prompt showing multi-step queries.

### 🔧 MCP Tool Feedback

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

### 📝 Prompt Feedback

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

### ⚡ Optimizations

Reduce turns and tokens:

> Tests average 4.2 turns. Adding tool output examples to the system
> prompt could reduce this to ~2 turns, cutting costs by 50%.

## Comparison Modes

The AI adapts its analysis based on your test structure:

### Single Configuration

Basic pass/fail analysis with improvement suggestions.

### Benchmark Mode (Model Comparison)

When you parametrize by model:

```python
@pytest.mark.parametrize("model", ["gpt-5-mini", "gpt-4.1"])
```

The report shows:
- Side-by-side pass rates
- Cost comparison
- Which model to deploy and why

### Arena Mode (Prompt Comparison)

When you parametrize by prompt:

```python
@pytest.mark.parametrize("prompt", PROMPTS)
```

The report shows:
- Which prompt performed best
- Why certain prompts failed
- Suggested prompt improvements

### Matrix Mode

When you parametrize by both:

```python
@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("prompt", PROMPTS)
```

The report shows:
- 2D grid of results
- Best model × prompt combination
- Interaction effects (prompt X works with model A but not B)

## Example Report

Here's what a real report looks like:

![Report Screenshot](../images/report-example.png)

The AI summary appears at the top, followed by detailed test results, tool information, and raw data for debugging.

## Cost Considerations

The summary model analyzes your test results, which are relatively small. Typical costs:

| Tests | Input Tokens | Cost (gpt-5-mini) |
|-------|--------------|-------------------|
| 10    | ~2,000       | $0.001            |
| 50    | ~8,000       | $0.004            |
| 200   | ~30,000      | $0.015            |

The insights are worth far more than the cost.
