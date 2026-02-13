
# pytest-aitest

> **4** tests | **3** passed | **1** failed | **75%** pass rate  
> Duration: 72.1s | Cost: 🧪 $-0.010143 · 🤖 $0.0204 · 💰 $0.0102 | Tokens: 1,286–2,169  
> February 07, 2026 at 07:39 PM

*Skill improvement — baseline vs skilled agent.*


## Agent Leaderboard


|#|Agent|Tests|Pass Rate|Tokens|Cost|Duration|
| :---: | :--- | :---: | :---: | ---: | ---: | ---: |
|🥇|baseline 🏆|2/2|100%|3,455|$0.004625|37.7s|
|🥈|with-financial-skill|1/2|50%|3,975|$0.005622|34.4s|



## AI Analysis

<div class="winner-card">
<div class="winner-title">Recommended for Deploy</div>
<div class="winner-name">baseline</div>
<div class="winner-summary">Delivers a 100% pass rate at the lowest total cost, with decisive tool usage and no permission-seeking delays. Consistently answers immediately when account data is required.</div>
<div class="winner-stats">
<div class="winner-stat"><span class="winner-stat-value green">100%</span><span class="winner-stat-label">Pass Rate</span></div>
<div class="winner-stat"><span class="winner-stat-value blue">$0.004625</span><span class="winner-stat-label">Total Cost</span></div>
<div class="winner-stat"><span class="winner-stat-value amber">3,455</span><span class="winner-stat-label">Tokens</span></div>
</div>
</div>

<div class="metric-grid">
<div class="metric-card green">
<div class="metric-value green">4</div>
<div class="metric-label">Total Tests</div>
</div>
<div class="metric-card red">
<div class="metric-value red">1</div>
<div class="metric-label">Failures</div>
</div>
<div class="metric-card blue">
<div class="metric-value blue">2</div>
<div class="metric-label">Agents</div>
</div>
<div class="metric-card amber">
<div class="metric-value amber">2.2</div>
<div class="metric-label">Avg Turns</div>
</div>
</div>

## Comparative Analysis

**Why the winner wins:**  
Baseline achieves the same functional outcomes with a perfect pass rate while costing less overall. The decisive factor is behavior: baseline immediately calls `get_all_balances` when allocation advice requires concrete data, whereas the skilled variant hesitates and asks for permission. That single hesitation accounts for the only failure and makes baseline the safer deploy choice.

**Notable patterns:**  
- Injecting the financial skill increased verbosity and caution, leading to permission-seeking language before acting.  
- The cheaper configuration (baseline) outperformed the augmented one on tool usage reliability, despite having less domain context.  
- When no tool call is required (general savings advice), both agents perform well and mention emergency funds correctly.

**Alternatives:**  
- **with-financial-skill**: Provides richer narrative guidance but is unreliable for tasks that require immediate tool invocation. Trade-off is higher cost with lower pass rate due to prompt-induced hesitation. No agents were disqualified.

## ❌ Failure Analysis

### Failure Summary

**with-financial-skill** (1 failure)

| Test | Root Cause | Fix |
|------|------------|-----|
| Ask for allocation advice — skilled agent should apply 50/30/20 rule. | Permission-seeking prevented required tool call | Add explicit instruction to call balance tools without asking |

### Ask for allocation advice — skilled agent should apply 50/30/20 rule. (with-financial-skill)
- **Problem:** The agent asked whether it should look up balances instead of doing so, causing the test to fail because no balance tool was called.
- **Root Cause:** The system prompt + skill content primes caution and user consent before action, even when the task implicitly authorizes data lookup.
- **Behavioral Mechanism:** Phrases like “to give specific transfers I’ll need a little info” and “do you want me to look up your current balances” trigger a deliberative, permission-seeking mode. This delays action and suppresses automatic tool calls.
- **Fix:** Add an explicit override to the system prompt:  
  > “When a user asks for allocation or transfer advice, automatically call balance tools as needed without asking for permission or clarification.”

## 🔧 MCP Tool Feedback

### banking-server
Overall, tool discoverability is good and the baseline agent uses it correctly when required.

| Tool | Status | Calls | Issues |
|------|--------|-------|--------|
| get_all_balances | ✅ | 1 | Working well |

## 📝 System Prompt Feedback

### with-financial-skill prompt (mixed)
- **Token count:** Not provided
- **Behavioral impact:** Emphasizes thoroughness and user consent, which increases verbosity and primes permission-seeking before acting.
- **Problem:** Lacks an instruction that authorizes immediate tool usage for implicit data requests.
- **Suggested change:** Add the following line verbatim:  
  > “Do not ask the user for permission to call tools when the request clearly requires account data; proceed directly.”

## 📚 Skill Feedback

### financial-skill (mixed)
- **Usage rate:** High in narrative advice; low in procedural/tool-driven steps
- **Token cost:** Not provided
- **Problem:** Encourages explanatory depth at the expense of action, interfering with tests that assert tool usage.
- **Suggested change:** Split the skill into two sections:  
  - “Principles” (kept concise)  
  - “Execution rules” with a first rule: *“If balances are needed, call tools immediately.”*

## 💡 Optimizations

| # | Optimization | Priority | Estimated Savings |
|---|-------------|----------|-------------------|
| 1 | Enforce automatic balance lookup | recommended | Prevents retries and failures |
| 2 | Reduce narrative preambles in skill | suggestion | ~10% token reduction |

#### 1. Enforce automatic balance lookup (recommended)
- Current: Skilled agent asks clarifying questions before acting.
- Change: Explicitly authorize immediate tool calls for allocation tasks.
- Impact: Eliminates failure risk and avoids wasted turns, improving reliability more than cost.

#### 2. Reduce narrative preambles in skill (suggestion)
- Current: Skill front-loads high-level guidance before execution.
- Change: Move high-level principles after any required tool calls.
- Impact: ~10% cost reduction from fewer tokens per response.


## Test Results


### tests/fixtures/scenario_07_skill_improvement.py


#### ❌ Ask for allocation advice — skilled agent should apply 50/30… ⚡

<details>
<summary>✅ baseline — 23.9s · 2,169 tokens · 3 turns · $0.002759</summary>

**Assertions:**

- ✅ `llm`: provides financial advice about fund allocation

**Tool Calls:**


|Tool|Status|Args|
| :--- | :---: | :--- |
|`get_all_balances`|✅||


**Response:**

> Right now you have $4,500 total: $1,500 in checking and $3,000 in savings. How you should split it depends on your goals and monthly cash flow. A few quick questions that will let me give a specific plan:
> - How much are your typical monthly living expenses (rent/mortgage, bills, food, transport)?
> - Any upcoming large expenses in the next 6–12 months (car repair, vacation, tuition, down payment)?
> - Do you have high‑interest debt (credit cards) you’re paying down?
> - Do you feel comfortable with th

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant Tools

    User->>Agent: "How should I allocate the money across my accounts?"
    Agent->>Tools: "get_all_balances({})"
    Tools-->>Agent: "{'accounts': {'checking': {'balance': 1500.0, 'formatted': '"
    Agent->>User: "Right now you have $4,500 total: $1,500 in checking and $3,000 in savings. How y"
```

</details>

<details>
<summary>❌ with-financial-skill — 17.7s · 1,983 tokens · 2 turns · $0.002804</summary>

**Error:** `      AssertionError: assert (False or False)
       +  where False = tool_was_called('get_all_balances')
       +    where tool_was_called = AgentResult(SUCCESS)\n  Turns: 2\n  Tools called: none\n  Duration: 11112ms\n  Tokens: 1983 | Cost: $0.002804\n  Final: 'I can help — to give specific transfers I’ll need a little info. Quick question first: do you want g'....tool_was_called
       +  and   False = tool_was_called('get_balance')
       +    where tool_was_called = AgentResult(SUCCESS)\n  Turns: 2\n  Tools called: none\n  Duration: 11112ms\n  Tokens: 1983 | Cost: $0.002804\n  Final: 'I can help — to give specific transfers I’ll need a little info. Quick question first: do you want g'....tool_was_called`

**Response:**

> I can help — to give specific transfers I’ll need a little info. Quick question first: do you want general guidance, or do you want me to look up your current balances and suggest exact transfers now?
> 
> Below is a short, practical plan you can use right away plus what I’ll do if you want me to check your accounts.
> 
> High-level rules (my priorities)
> - Emergency fund first: build 3–6 months of essential expenses in savings before other big goals.
> - Follow 50/30/20 as a baseline: 50% needs, 30% wants

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant Tools

    User->>Agent: "How should I allocate the money across my accounts?"
    Agent->>User: "I can help — to give specific transfers I’ll need a little info. Quick question "
```

</details>


#### ✅ Ask about savings — skilled agent should mention emergency f…

<details>
<summary>✅ baseline — 13.8s · 1,286 tokens · 2 turns · $0.001865</summary>

**Assertions:**

- ✅ `llm`: provides savings recommendations

**Response:**

> Great — here are practical, high-impact ways to save more, plus a couple quick options I can help with right away.
> 
> High-level principles
> - Automate it: set up automatic transfers to savings right after payday so you “pay yourself first.”
> - Make goals specific: name the goal, amount, and date (e.g., $3,600 in 12 months = $300/month).
> - Reduce friction: simplify accounts and automate categorization so saving feels effortless.
> 
> Concrete steps you can start today
> 1. Set a clear goal
>    - Emergency 

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant Tools

    User->>Agent: "I want to save more money. What do you recommend?"
    Agent->>User: "Great — here are practical, high-impact ways to save more, plus a couple quick o"
```

</details>

<details>
<summary>✅ with-financial-skill — 16.7s · 1,992 tokens · 2 turns · $0.002818</summary>

**Assertions:**

- ✅ `llm`: provides savings recommendations

**Response:**

> Great — want practical, doable steps. Here’s a short, actionable plan you can start today plus specific tactics to speed up saving.
> 
> Top priorities (in order)
> 1. Build an emergency fund equal to 3–6 months of your essential monthly expenses. This comes first.
> 2. After your emergency fund, pay down any high‑interest debt (credit cards, payday, some personal loans).
> 3. Make sure you’re getting any employer retirement match (this is “free money”).
> 4. Then save for other goals (house, vacation) and 

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant Tools

    User->>Agent: "I want to save more money. What do you recommend?"
    Agent->>User: "Great — want practical, doable steps. Here’s a short, actionable plan you can st"
```

</details>

*Generated by [pytest-aitest](https://github.com/sbroenne/pytest-aitest) on February 07, 2026 at 07:39 PM*
