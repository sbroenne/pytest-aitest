# Testing Architecture

This document describes the test infrastructure for pytest-aitest.

## Test Categories

```
tests/
├── unit/                      # Fast tests, no LLM calls (~400 tests)
│   ├── test_templates/        # Report template rendering
│   ├── test_config.py         # Configuration parsing
│   ├── test_result.py         # AgentResult assertions
│   ├── test_retry.py          # Rate limit retry logic
│   ├── test_cli.py            # CLI commands
│   ├── test_schema.py         # Pydantic model validation
│   └── ...
└── integration/               # Real LLM calls (~20 tests)
    ├── test_basic_usage.py    # Core agent execution
    ├── test_model_benchmark.py # Model comparison
    ├── test_prompt_arena.py   # Prompt comparison
    ├── test_matrix.py         # Model × Prompt grid
    ├── test_sessions.py       # Multi-turn conversations
    ├── test_skills.py         # Skill injection
    └── ...
```

## Unit Tests

Unit tests run fast (< 30 seconds total) and don't require LLM credentials.

### Core Logic Tests

| File | What It Tests |
|------|---------------|
| `test_config.py` | Configuration parsing, environment variables |
| `test_result.py` | `AgentResult` assertion methods (`.tool_was_called()`, `.response_contains()`) |
| `test_retry.py` | Rate limit retry logic with exponential backoff |
| `test_prompt.py` | YAML prompt loading and variable substitution |
| `test_aggregator.py` | Report dimension detection (model/prompt comparison modes) |
| `test_schema.py` | Pydantic model validation for JSON schema |
| `test_cli.py` | CLI command parsing and execution |
| `test_cli_server_process.py` | CLI server process management |

### Report Template Tests

See [Report Template Testing](#report-template-testing) below for the four-layer architecture.

## Integration Tests

Integration tests make real LLM API calls and validate end-to-end behavior.

**Requirements:**
```bash
# Azure OpenAI (uses Entra ID)
export AZURE_API_BASE=https://your-resource.cognitiveservices.azure.com
az login
```

### Test Scenarios

| File | What It Tests |
|------|---------------|
| `test_basic_usage.py` | Agent executes tools correctly |
| `test_model_benchmark.py` | Compare multiple models on same tests |
| `test_prompt_arena.py` | Compare multiple prompts with same model |
| `test_matrix.py` | Full model × prompt comparison grid |
| `test_sessions.py` | Multi-turn conversations with context |
| `test_skills.py` | Skill file injection |
| `test_skill_improvement.py` | Compare agent with/without skills |
| `test_cli_server.py` | CLI tools as agent servers |
| `test_ai_summary.py` | AI-generated report insights |
| `test_fixture_scenarios.py` | Generate test fixtures for unit tests |

### Test Harnesses

Integration tests use built-in MCP servers for predictable tool behavior:

```python
from pytest_aitest.testing import WeatherMCPServer, TodoMCPServer

# Weather server - deterministic responses
server = WeatherMCPServer()  # get_weather, get_forecast, compare_weather

# Todo server - CRUD operations
server = TodoMCPServer()  # add_todo, list_todos, complete_todo, delete_todo
```

See [Test Harnesses](test-harnesses.md) for details.

---

## Report Template Testing

When testing HTML report generation, traditional tests miss critical bugs. We use a four-layer defense:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 4: DATA FLOW TESTS                         │
│    test_context_flow.py - Source values → final HTML                │
│    "Does my model name actually appear in the leaderboard?"         │
└─────────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────────┐
│                  LAYER 3: COMPOSITION TESTS                         │
│    test_report_composition.py - Flags → sections appear/hide        │
│    "When show_ai_summary=True, does the section exist?"             │
└─────────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────────┐
│                  LAYER 2: ADAPTIVE FLAGS TESTS                      │
│    test_adaptive_flags.py - Dimensions → correct flags              │
│    "With 2 models, is show_model_leaderboard=True?"                 │
└─────────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────────┐
│                  LAYER 1: COMPONENT TESTS                           │
│    test_*.py partials - Each partial renders correctly              │
│    "Does ai_summary.html render markdown correctly?"                │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer 1: Component Tests

Test each Jinja2 partial template in isolation.

| File | Tests | Partial |
|------|-------|---------|
| `test_ai_summary.py` | 14 | AI-generated analysis section |
| `test_comparison_matrix.py` | 14 | Side-by-side test comparison grid |
| `test_model_leaderboard.py` | 12 | Model ranking table with medals |
| `test_prompt_comparison.py` | 7 | Prompt performance table |
| `test_summary_cards.py` | 8 | Pass/fail/skip statistics |
| `test_tool_comparison.py` | 6 | Tool usage heatmap |
| `test_header.py` | 8 | Report header with badges |

**What these catch:** Broken Jinja2 syntax, incorrect conditionals, missing CSS classes.

### Layer 2: Adaptive Flags Tests

Test the `_build_adaptive_flags()` logic that determines which sections to show.

```python
# test_adaptive_flags.py
def test_model_comparison_flags():
    flags = extract_flags("02_model_comparison")
    assert flags["show_model_leaderboard"] is True
    assert flags["show_comparison_grid"] is True
```

**What these catch:** Wrong show/hide logic, incorrect mode detection.

### Layer 3: Composition Tests

Test that flags correctly include/exclude HTML sections.

```python
# test_report_composition.py
def test_ai_summary_rendered_when_present():
    html, data = generate_html("06_with_ai_summary")
    assert "AI Analysis" in html
```

**What these catch:** Missing sections, broken flag → template integration.

### Layer 4: Data Flow Tests

Test that specific data values from source fixtures appear in final HTML.

```python
# test_context_flow.py
def test_model_names_in_leaderboard():
    html, data = generate_html("02_model_comparison")
    for model in data["dimensions"]["models"]:
        assert model in html
```

**What these catch:** Context dict missing variables (the AI summary bug), data transformation errors.

## The Bug That Drove This Architecture

The AI summary bug revealed a gap in our testing:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Pydantic Model │ --> │  Context Dict   │ --> │  Jinja Template │
│  (report.json)  │     │  (generator.py) │     │   (partials)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ✓                      ❌                       ✓
   (validated)            THE BUG WAS HERE        (rendered fine)
```

- **Layer 1 passed**: The `ai_summary.html` partial rendered markdown correctly
- **Layer 2 passed**: The flag `show_ai_summary` was computed correctly  
- **Layer 3 passed**: The section appeared when the flag was True
- **Layer 4 failed**: The actual AI summary text wasn't in the HTML

The fix was one line: `"ai_summary": pydantic_report.ai_summary` in the context dict.

## Test Fixtures

Real integration test results are stored in `tests/fixtures/reports/`:

| Fixture | Mode | Features |
|---------|------|----------|
| `01_basic_usage.json` | simple | Single model, basic tests |
| `02_model_comparison.json` | model_comparison | 2 models, leaderboard |
| `03_prompt_comparison.json` | prompt_comparison | 3 prompts |
| `04_matrix.json` | matrix | 2 models × 3 prompts |
| `05_sessions.json` | simple | Session context tracking |
| `06_with_ai_summary.json` | model_comparison | LLM-generated summary |
| `07_with_skipped.json` | simple | Skipped tests |
| `08_matrix_full.json` | matrix | Full features + AI summary |

These are real outputs from integration tests, not hand-crafted mocks.

## Running Tests

```bash
# All unit tests (fast, no LLM calls)
pytest tests/unit/ -v

# Just template tests
pytest tests/unit/test_templates/ -v

# Integration tests (requires LLM credentials)
pytest tests/integration/ -v

# Full test suite
pytest -v
```

## Test Helpers

The `tests/unit/test_templates/conftest.py` provides helpers for template testing:

```python
# Load real fixture data
report = load_pydantic_report("02_model_comparison")

# Extract specific data for partial testing
model_groups = extract_model_groups("02_model_comparison")
flags = extract_flags("02_model_comparison")

# Render a partial in isolation
html = render_partial("ai_summary.html", ai_summary="**Bold text**")

# Generate full HTML from fixture
html, data = generate_html("08_matrix_full")
```

## Adding New Template Tests

When adding a new partial or modifying existing templates:

1. **Add component test** (Layer 1): Test the partial renders correctly with various inputs
2. **Update flag tests** (Layer 2): If new flags are needed
3. **Add composition test** (Layer 3): Verify the section appears/hides based on flags
4. **Add data flow test** (Layer 4): Verify specific values reach the final HTML

Example for a new "cost breakdown" partial:

```python
# Layer 1: tests/unit/test_templates/test_cost_breakdown.py
class TestCostBreakdownRendering:
    def test_renders_with_costs(self, render_partial):
        html = render_partial("cost_breakdown.html", 
            costs=[{"model": "gpt-4", "usd": 0.05}])
        assert "gpt-4" in html
        assert "$0.05" in html

# Layer 4: tests/unit/test_templates/test_context_flow.py
def test_costs_appear_in_html():
    html, data = generate_html("02_model_comparison")
    total_cost = data["summary"]["total_cost_usd"]
    assert f"${total_cost:.2f}" in html or str(total_cost) in html
```

---

## Writing Integration Tests

Integration tests validate that agents actually work with real LLMs.

### Basic Pattern

```python
# tests/integration/test_my_feature.py
import pytest
from pytest_aitest import Agent, Provider, MCPServer

@pytest.fixture
def my_agent():
    return Agent(
        provider=Provider(model="azure/gpt-4o-mini"),
        mcp_servers=[WeatherMCPServer()],
        system_prompt="You help users check weather.",
    )

async def test_agent_uses_tool(my_agent, aitest_run):
    result = await aitest_run(my_agent, "What's the weather in Paris?")
    
    assert result.success
    assert result.tool_was_called("get_weather")
    assert "Paris" in result.final_response
```

### Parametrized Tests (Benchmarking)

```python
# Compare multiple models
@pytest.mark.parametrize("model", ["azure/gpt-4o-mini", "azure/gpt-4o"])
async def test_model_comparison(model, aitest_run):
    agent = Agent(provider=Provider(model=model), ...)
    result = await aitest_run(agent, "What's the weather?")
    assert result.success

# Compare multiple prompts
PROMPTS = load_prompts(Path("prompts/"))

@pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
async def test_prompt_comparison(prompt, aitest_run):
    agent = Agent(system_prompt=prompt.system_prompt, ...)
    result = await aitest_run(agent, "What's the weather?")
    assert result.success
```

### Test Execution Time

Integration tests are slow (5-30+ seconds per test) because they make real API calls. This is expected and necessary — fast tests that mock LLM responses don't validate real behavior.

---

## Test Philosophy

### What We Test

| Category | Tests | Purpose |
|----------|-------|---------|
| **Core Logic** | Unit tests with mocks | Fast validation of algorithms |
| **Agent Behavior** | Integration tests with real LLMs | Validate tools are used correctly |
| **Report Rendering** | Four-layer template tests | Guarantee HTML output correctness |
| **Schema Validation** | Pydantic model tests | Ensure JSON schema compliance |

### What We Don't Mock

- **LLM responses in integration tests**: The whole point is testing real agent behavior
- **Report fixtures**: We use real integration test outputs, not hand-crafted JSON

### Test Coverage Goals

- **Unit tests**: Run on every commit, fast CI feedback
- **Integration tests**: Run on PR merge, validate real-world behavior
- **Template tests**: Catch rendering bugs before they reach users
