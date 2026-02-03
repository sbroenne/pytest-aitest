# Testing Philosophy

Why AI tools need different testing approaches.

## The Problem

MCP servers and CLIs have two problems nobody talks about:

1. **Design** — Your tool descriptions, parameter names, and error messages are the entire API for LLMs. Getting them right is hard.

2. **Testing** — Traditional tests can't verify if an LLM can actually understand and use your tools.

- Bad tool description? The LLM picks the wrong tool.
- Confusing parameter name? The LLM passes garbage.
- Unhelpful error message? The LLM can't recover.

## The Key Insight

**Your test is a prompt.**

You write what a user would say ("What's the weather in Paris?"), and the LLM figures out how to use your tools. If it can't, your tool descriptions need work.

This is fundamentally different from traditional testing:

| Traditional Testing | AI Tool Testing |
|---------------------|-----------------|
| Call function with exact args | Give natural language prompt |
| Assert on return value | Assert LLM chose right tool |
| Deterministic | Probabilistic |
| Tests your code | Tests your *interface* |

## Why Unit Tests Don't Work

Consider this MCP server tool:

```python
@server.tool()
def get_weather(loc: str) -> dict:
    """Gets weather."""
    return {"temp": 20, "conditions": "sunny"}
```

Traditional unit tests pass:

```python
def test_get_weather():
    result = get_weather("Paris")
    assert result["temp"] == 20  # ✅ passes
```

But an LLM might fail to use it because:

- `loc` is ambiguous — is it a location name, coordinates, or an airport code?
- "Gets weather" doesn't explain what the return value means
- No examples of expected input format

**The tool works, but the interface is broken.**

## What pytest-aitest Tests

pytest-aitest tests the *LLM's ability to use your tools*:

```python
@pytest.mark.asyncio
async def test_weather_query(aitest_run, agent):
    result = await aitest_run(agent, "What's the weather in Paris?")
    
    assert result.success
    assert result.tool_was_called("get_weather")
    assert result.tool_call_arg("get_weather", "loc") == "Paris"
```

This test fails if:

1. The LLM doesn't discover the tool
2. The LLM picks a different tool
3. The LLM passes wrong arguments
4. The LLM can't interpret the response

Each failure points to a specific interface problem to fix.

## The Fix: Better Tool Descriptions

```python
@server.tool()
def get_weather(city: str) -> dict:
    """Get current weather conditions for a city.
    
    Args:
        city: City name (e.g., "Paris", "Tokyo", "New York")
    
    Returns:
        dict with temperature_celsius (int) and conditions (str)
    
    Example:
        get_weather("Paris") → {"temperature_celsius": 20, "conditions": "sunny"}
    """
    return {"temperature_celsius": 20, "conditions": "sunny"}
```

Now the test passes because:

- `city` is unambiguous
- Examples show expected format
- Return value is documented

## Integration Tests Are Essential

For pytest-aitest itself, unit tests with mocked LLM responses are worthless. The only way to verify the framework works is to:

1. Run **real integration tests** against **real LLM providers**
2. Use **actual MCP/CLI servers** that perform real operations
3. Verify the **full pipeline end-to-end**

This is why:

- Integration tests take 5-30+ seconds (real LLM calls)
- Tests require Azure OpenAI credentials
- Mocking the LLM defeats the purpose

## Test Architecture

```
tests/
├── unit/                      # Fast tests, no LLM calls (~400 tests)
│   ├── test_config.py         # Configuration parsing
│   ├── test_result.py         # AgentResult assertions
│   └── ...
└── integration/               # Real LLM calls (~20 tests)
    ├── test_basic_usage.py    # Core agent execution
    ├── test_model_benchmark.py # Model comparison
    └── ...
```

**Unit tests** validate internal logic:
- Configuration parsing
- Result object methods
- Report generation
- Retry logic

**Integration tests** validate the full pipeline:
- LLM can discover and use tools
- Multi-turn conversations work
- Reports capture the right data

## Summary

1. **Traditional tests can't catch interface problems** — a working function can still be unusable by an LLM

2. **Your test is a prompt** — write what a user would say, let the LLM figure out the tools

3. **Integration tests are essential** — mocking the LLM defeats the purpose of testing AI tool interfaces

4. **Failures point to fixes** — each test failure indicates a specific interface problem (description, parameter name, error message)
