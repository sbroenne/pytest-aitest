# Report Structure

The visual structure and components of pytest-aitest HTML reports.

## Design Philosophy

Reports answer one question: **"Which configuration should I deploy?"**

Every visual element supports this goal through:

1. **Progressive disclosure** — Summary first, details on demand
2. **Comparison-first** — Winner highlighting, sorted rankings
3. **Scalability** — Works for 2 agents or 20 agents
4. **Actionable insights** — Not just metrics, but what to fix

## Report Sections

Reports have a minimal, focused structure:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. HEADER (inline in report.html)                               │
│    Suite name, status badge, metrics, context                   │
├─────────────────────────────────────────────────────────────────┤
│ 2. AI ANALYSIS                                                  │
│    LLM-generated markdown (insights.markdown_summary)           │
├─────────────────────────────────────────────────────────────────┤
│ 3. AGENT LEADERBOARD (if multiple agents)                       │
│    Ranked table of configurations                               │
├─────────────────────────────────────────────────────────────────┤
│ 4. DETAILED RESULTS                                             │
│    Test cards with sessions as visual grouping                  │
└─────────────────────────────────────────────────────────────────┘
```

## 1. Header

Inline in `report.html` (not a separate partial). Shows suite identity and key metrics.

### Components

| Component | Content | Example |
|-----------|---------|---------|
| **Suite Title** | Module docstring or "Test Report" | "Weather API Integration Tests" |
| **Status Badge** | Pass/fail with visual styling | ✅ All Passed or ✗ 2 Failed |
| **Metrics Bar** | 6 key numbers | passed, failed, pass rate, tokens, cost, duration |
| **Context Badges** | What was tested | "2 agents compared", "model · prompt", 🤖 $0.03 |

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Weather API Integration Tests                    ✅ All Passed  │
├─────────────────────────────────────────────────────────────────┤
│ 4 passed │ 0 failed │ 100% pass rate │ 3,041 tokens │ $0.004   │
├─────────────────────────────────────────────────────────────────┤
│ Feb 05, 2026 at 14:30  │ 2 agents compared │ model · prompt    │
└─────────────────────────────────────────────────────────────────┘
```

## 2. AI Analysis

LLM-generated markdown rendered directly. The AI writes analysis prose that's displayed as-is.

The `insights.markdown_summary` field contains the complete analysis as markdown:

```jinja2
{{ insights.markdown_summary | markdown | safe }}
```

For details on what the AI analyzes and how insights are generated, see [AI-Powered Reports](ai-reports.md).

## 3. Agent Leaderboard

**Only shown when multiple agents are tested** (`flags.show_agent_leaderboard`).

Answers: "Which configuration should I deploy?"

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ 🏆 Agent Leaderboard                                            │
├─────────────────────────────────────────────────────────────────┤
│ Rank │ Agent                          │ Pass │ Tokens │ Cost   │
├──────┼────────────────────────────────┼──────┼────────┼────────┤
│  🥇  │ gpt-4.1-mini / concise         │ 100% │  561 ★ │ $0.001 │
│  🥈  │ gpt-5-mini / concise           │ 100% │  743   │ $0.001 │
│  🥉  │ gpt-4.1-mini / detailed        │ 100% │  764   │ $0.001 │
│   4  │ gpt-5-mini / detailed          │ 100% │  973   │ $0.002 │
└──────┴────────────────────────────────┴──────┴────────┴────────┘
  ★ = Best in column    Sorted by: Pass Rate → Cost (tiebreaker)
```

### Features

- **Medals** (🥇🥈🥉) for top 3
- **Pass rate bar** (visual progress)
- **Star (★)** on best-in-column values
- **Full agent identity**: Model + Prompt name + Skill name

## 4. Detailed Results

All test results with full agent interaction details. Sessions are shown as visual groupings within this section.

### Test Card (Collapsed)

```
┌─────────────────────────────────────────────────────────────────┐
│ ▶ Get weather in Paris                    ✅ passed │ 4.6s     │
└─────────────────────────────────────────────────────────────────┘
```

### Test Card (Expanded)

Tests are **expanded by default** so users see results immediately.

```
┌─────────────────────────────────────────────────────────────────┐
│ ▼ Get weather in Paris                    ✅ passed │ 4.6s     │
├─────────────────────────────────────────────────────────────────┤
│ Agent: gpt-4.1-mini / concise                                   │
│ Tokens: 561 │ Cost: $0.001 │ Tools: get_weather                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     Mermaid Diagram                       │  │
│  │   (full width, readable sequence diagram)                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  💬 Final Response                                              │
│  Paris: 18°C (64°F), partly cloudy, humidity 65%, SW wind       │
│  12 km/h.                                                       │
│                                                                 │
│  ✓ Assertions                                                   │
│  · result.success == True                                       │
│  · result.tool_was_called("get_weather") == True                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Session Grouping

Multi-turn sessions appear as grouped test cards with visual connectors showing context flow:

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔗 Session: banking-flow                    3 tests │ all ✅   │
├─────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ ▼ Check account balance                   ✅ │ 2.1s       │   │
│ │ [test details...]                                         │   │
│ └───────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                     +3 msgs (context carried)                   │
│                          │                                      │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ ▼ Transfer to savings                     ✅ │ 3.4s       │   │
│ │ [test details...]                                         │   │
│ └───────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                     +5 msgs (context carried)                   │
│                          │                                      │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ ▼ Confirm transaction                     ✅ │ 1.8s       │   │
│ │ [test details...]                                         │   │
│ └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Adaptive Behavior

The report layout adapts based on what was tested:

| Scenario | Agent Leaderboard | Detailed Results |
|----------|-------------------|------------------|
| 1 agent, 1 test | ❌ | ✅ Expanded |
| 1 agent, N tests | ❌ | ✅ Expanded |
| N agents, same tests | ✅ | ✅ Grouped by test |
| Session tests | ❌ (unless multi-agent) | ✅ Session grouping |

### Detection Logic

```python
if len(unique_agents) == 1:
    # Simple mode: no comparison views
    show_agent_leaderboard = False
elif len(unique_agents) > 1:
    # Comparison mode
    show_agent_leaderboard = True
```

## Scalability Requirements

The design MUST work at these scales:

| Scale | Behavior |
|-------|----------|
| 2 agents | Leaderboard shows 2 rows |
| 8 agents | Leaderboard with 8 rows, vertical scroll |
| 20 agents | Leaderboard with pagination |
| 50+ tests | Tests expanded by default, browser scroll |

### Anti-Patterns (What NOT to Do)

❌ **Don't** show side-by-side cards that shrink with more items  
❌ **Don't** truncate agent names — wrap or tooltip instead  
❌ **Don't** show tiny unreadable diagrams  
❌ **Don't** require horizontal scrolling for core content  
❌ **Don't** duplicate information across multiple views

## Visual Design Tokens

Consistent styling from Material Design (indigo theme):

| Token | Value | Usage |
|-------|-------|-------|
| `--c-primary` | `#3f51b5` | Primary actions, highlights |
| `--c-pass` | `#4caf50` | Success states |
| `--c-fail` | `#f44336` | Error states |
| `--c-warn` | `#ff9800` | Warnings, tool names |
| `--c-card` | `#1e1e1e` (dark) | Card backgrounds |
| `--radius` | `8px` | Border radius |
| `--font-mono` | `Roboto Mono` | Code, metrics |

## Implementation Files

The template structure is minimal and focused:

| File | Purpose |
|------|---------|
| `templates/report.html` | Main report template (includes inline header) |
| `templates/partials/agent_leaderboard.html` | Agent ranking table |
| `templates/partials/detailed_results.html` | Test cards with session grouping |
| `templates/partials/test_details.html` | Expanded test view (metrics, diagram, response) |
| `templates/partials/overlay.html` | Fullscreen diagram viewer |
| `templates/partials/styles.css` | All CSS |
| `templates/partials/scripts.js` | Interactions (expand/collapse, diagram zoom) |

### Removed Partials (Dead Code)

These partials were removed as they duplicated functionality or were never used:

| Removed File | Reason |
|--------------|--------|
| `header.html` | Header is inline in report.html |
| `summary_cards.html` | Never included in any template |
| `ai_summary.html` | Replaced by markdown_summary rendering |
| `prompt_comparison.html` | Redundant with Agent Leaderboard |
| `comparison_matrix.html` | Limited to 2D, breaks with 3+ dimensions |
| `side_by_side.html` | Broken layout, doesn't scale |
| `tool_comparison.html` | Covered by AI Analysis |
| `session_container.html` | Merged into detailed_results.html |

## Key Principles

1. **One source of truth** — Agent Leaderboard is THE comparison view
2. **AI explains, templates display** — AI writes insights in markdown
3. **Sessions are grouping, not special** — Same test cards, visual connectors
4. **Progressive disclosure** — Click to expand details
5. **No redundancy** — Each piece of information appears once
