# Testing Architecture

This document describes the test infrastructure for pytest-aitest.

## Test Philosophy

**Unit tests with mocks are valuable but insufficient for template rendering.**

When testing HTML report generation, traditional "mock the data, check the output" tests miss critical bugs. The AI summary bug taught us this: the partial template worked perfectly in isolation, but the context dict never passed the variable to it.

## Four-Layer Testing Architecture

We use a four-layer defense system to guarantee correct HTML rendering:

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
