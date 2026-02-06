# Fixture Testing with Comprehensive Assertions

Test your AI agents using pre-built fixture test suites with semantic, tool, and performance assertions.

## Overview

Fixture tests demonstrate best practices for comprehensive AI agent validation. Located in `tests/fixtures/generate_scenarios.py`, they include:

- **Semantic Assertions** — AI validates response quality
- **Tool Argument Assertions** — Verify correct parameters passed
- **Tool Count Assertions** — Check single vs. multiple tool calls
- **Performance Assertions** — Validate cost and duration
- **Multi-Agent Comparison** — Compare models and skills
- **Session Testing** — Multi-turn context preservation

## Running Fixture Tests

```bash
# Run all fixture tests
pytest tests/fixtures/generate_scenarios.py -v

# Run single test class
pytest tests/fixtures/generate_scenarios.py::TestSingleAgent -v

# Run single test
pytest tests/fixtures/generate_scenarios.py::TestSingleAgent::test_simple_weather_query -v

# Generate fixture reports
pytest tests/fixtures/generate_scenarios.py --aitest-json=tests/fixtures/reports/01_single_agent.json
```

## Test Suites

### 1. TestSingleAgent (4 tests)

Single agent configuration demonstrating various assertion types.

```python
class TestSingleAgent:
    async def test_simple_weather_query(self, aitest_run, weather_server, llm_assert):
        """Simple query using one tool call."""
        result = await aitest_run(agent, "What's the weather in Berlin?")
        
        # Semantic assertion (AI validation)
        assert llm_assert(result.final_response, "provides current temperature and conditions")
        
        # Tool assertions
        assert result.tool_was_called("get_weather")
        city = result.tool_call_arg("get_weather", "city")
        assert city.lower() == "berlin"
        
        # Cost assertion
        assert result.cost_usd < 0.01
```

**Tests:**
- `test_simple_weather_query` — Single tool call, semantic assertion
- `test_forecast_query` — Multi-day forecast with comparison
- `test_city_comparison` — Multiple tools, tool count verification
- `test_expected_failure` — Intentional failure to test error display

### 2. TestTwoAgents (6 tests)

Compare two different models on same queries.

```python
class TestTwoAgents:
    @pytest.mark.parametrize("model", ["gpt-5-mini", "gpt-4.1-mini"])
    async def test_simple_weather(self, aitest_run, weather_server, model):
        """Same test with different models."""
        agent = Agent(
            provider=Provider(model=f"azure/{model}"),
            mcp_servers=[weather_server],
            # ...
        )
        result = await aitest_run(agent, "What's the weather in London?")
        
        # Semantic assertion for response quality
        assert llm_assert(result.final_response, "mentions London weather conditions")
```

Each test runs on both models — AI analysis auto-generates leaderboard.

### 3. TestMultiAgentSessions (6 tests)

Multi-turn conversation maintaining context across agent calls.

```python
@pytest.mark.session("savings-planning")
class TestMultiAgentSessions:
    async def test_01_establish_context(self, aitest_run, banking_agent):
        """First turn: establish context."""
        result = await aitest_run(
            banking_agent,
            "I want to save more. Check my accounts and suggest monthly transfers."
        )
        
        assert result.success
        assert result.tool_was_called("get_all_balances")
        assert llm_assert(result.final_response, "provides savings suggestion")
    
    async def test_02_reference_previous(self, aitest_run, banking_agent):
        """Second turn: agent remembers context from test_01."""
        result = await aitest_run(banking_agent, "Let's transfer $200 to savings.")
        
        assert result.tool_was_called("transfer")
        
    async def test_03_verify_result(self, aitest_run, banking_agent):
        """Third turn: verify the transfer worked."""
        result = await aitest_run(banking_agent, "Show me my new savings balance.")
        
        assert result.tool_was_called("get_balance")
```

The `@pytest.mark.session` marker ensures tests share agent state.

### 4. TestAgentSelector (6 tests)

Three agents demonstrating agent selector UI in reports.

```python
class TestAgentSelector:
    @pytest.mark.parametrize("model", ["gpt-5-mini", "gpt-4.1-mini", "gpt-5-mini+skill"])
    async def test_weather_query(self, aitest_run, weather_server, model):
        """Run same test with 3 different configurations."""
        agent = Agent(
            provider=Provider(model=...),
            skill=skill if "skill" in model else None,
            # ...
        )
        result = await aitest_run(agent, "What's the weather in Berlin?")
        assert result.success
```

With 3 agents, the report includes an interactive agent selector allowing users to pick any 2 for comparison.

## Assertion Patterns

### Semantic Assertions (LLM-Based)

Validate response quality using AI judgment:

```python
# llm_assert is a pytest fixture — just add it to your test function signature
# Does response mention expected content?
assert llm_assert(result.final_response, "provides temperature in Celsius and Fahrenheit")

# Complex criteria
assert llm_assert(
    result.final_response,
    "recommends specific clothing items based on current temperature"
)
```

### Tool Call Assertions

Verify the agent used the right tools:

```python
# Simple: was tool called at all?
assert result.tool_was_called("get_weather")

# Count: how many times?
assert result.tool_call_count("get_weather") >= 2

# Arguments: what parameters were passed?
city = result.tool_call_arg("get_weather", "city")
assert city.lower() == "berlin"

# Multiple calls: get all invocations
calls = result.tool_calls_for("transfer")
assert len(calls) >= 1
assert calls[0].arguments["amount"] == 100
```

### Performance Assertions

Validate efficiency:

```python
# Cost (in USD)
assert result.cost_usd < 0.01  # Under 1 cent

# Duration (in milliseconds)
assert result.duration_ms < 30000  # Under 30 seconds

# Token usage
total_tokens = (result.token_usage.get("prompt", 0) + 
                result.token_usage.get("completion", 0))
assert total_tokens < 5000
```

## Generated Reports

Running fixture tests generates JSON and HTML reports:

```bash
pytest tests/fixtures/generate_scenarios.py::TestSingleAgent -v \
    --aitest-json=tests/fixtures/reports/01_single_agent.json \
    --aitest-html=docs/reports/01_single_agent.html

# Output:
# aitest JSON report: tests\fixtures\reports\01_single_agent.json
# aitest HTML report: docs\reports\01_single_agent.html
```

Reports include:

- **AI Analysis** — LLM-generated insights on performance
- **Test Results** — All assertions with pass/fail details
- **Tool Feedback** — Suggestions for improving tool descriptions
- **Tool Call Flows** — Mermaid diagrams showing sequence
- **Leaderboard** — Compare agents if multiple models tested

## Running Comprehensive Test Suite

Generate reports for all 4 fixture suites:

```bash
# Run and generate all fixture reports
pytest tests/fixtures/generate_scenarios.py -v \
    --aitest-summary-model=azure/gpt-5.2-chat \
    --aitest-html=docs/reports/fixtures-report.html

# Or individually
pytest tests/fixtures/generate_scenarios.py::TestSingleAgent --aitest-json=reports/01.json
pytest tests/fixtures/generate_scenarios.py::TestTwoAgents --aitest-json=reports/02.json
pytest tests/fixtures/generate_scenarios.py::TestMultiAgentSessions --aitest-json=reports/03.json
pytest tests/fixtures/generate_scenarios.py::TestAgentSelector --aitest-json=reports/04.json
```

Then regenerate HTML from all JSONs:

```bash
python scripts/generate_fixture_html.py
```

This updates HTML reports in `docs/reports/` without re-running tests (faster).

## Assertion Workflow

When writing fixture tests, follow this pattern:

1. **Create agent** — Configure provider, servers, system prompt, skill
2. **Run prompt** — Use `aitest_run(agent, "user message")`
3. **Validate success** — `assert result.success`
4. **Assert tool usage** — `assert result.tool_was_called(...)`
5. **Check arguments** — `assert result.tool_call_arg(...) == expected`
6. **Semantic validation** — `assert llm_assert(response, "criterion")`
7. **Performance validation** — `assert result.cost_usd < threshold`

Example:

```python
async def test_trip_planning(self, aitest_run, weather_server, llm_assert):
    agent = Agent(...)
    
    result = await aitest_run(
        agent,
        "Plan a trip to Paris. Check weather for the next 3 days."
    )
    
    # Validate execution
    assert result.success, f"Agent failed: {result.error}"
    
    # Validate tools used
    assert result.tool_was_called("get_forecast")
    days = result.tool_call_arg("get_forecast", "days")
    assert days == 3, f"Expected 3 days, got {days}"
    
    # Validate response quality
    assert llm_assert(result.final_response, "provides weather prediction for 3 days")
    
    # Validate efficiency
    assert result.cost_usd < 0.05, f"Cost too high: ${result.cost_usd}"
    assert result.duration_ms < 30000, f"Took too long: {result.duration_ms}ms"
```

## Debugging Failed Tests

If a fixture test fails:

1. **Check the error message** — AI assertion detail explains why
2. **Run the test locally** — `pytest tests/fixtures/... -vv`
3. **Check JSON report** — `tests/fixtures/reports/01_*.json` has full details
4. **Verify agent config** — Is the right server/model/prompt used?
5. **Check tool availability** — Does `result.available_tools` include what you need?

### Common Issues

**"Tool not found"**
```python
# Check available tools
print(f"Available: {[t.name for t in result.available_tools]}")

# Ensure MCP server is running
assert len(result.available_tools) > 0
```

**"Wrong parameter passed"**
```python
# Get all calls to debug
calls = result.tool_calls_for("get_weather")
for i, call in enumerate(calls):
    print(f"Call {i}: {call.arguments}")
```

**"Response doesn't match criterion"**
```python
# Print what the LLM actually said
print(f"Response:\n{result.final_response}")

# Check if criterion is too strict
assert llm_assert(result.final_response, "mentions weather")  # Too vague
assert llm_assert(result.final_response, "exact phrase")      # Too narrow
```

## Best Practices

### Do ✅
- Use semantic assertions for subjective quality checks
- Use tool assertions for behavioral verification
- Use performance assertions for efficiency checks
- Combine assertion types for comprehensive validation
- Document what each assertion validates with comments

### Don't ❌
- Don't rely only on `result.success` (it's too broad)
- Don't hardcode exact prices for cost assertions (use thresholds)
- Don't expect specific tool call counts without testing multiple times
- Don't use semantic assertions for tool-related checks (use `tool_was_called`)
- Don't assume tool arguments — always verify with `tool_call_arg`
