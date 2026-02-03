# Copilot Instructions for pytest-aitest

## CRITICAL: What We Test

**We do NOT test agents. We USE agents to test:**
- **MCP Servers** — Can an LLM understand and use these tools?
- **CLI Tools** — Can an LLM operate this command-line interface?
- **System Prompts** — Do these instructions produce the desired behavior?
- **Agent Skills** — Does this domain knowledge improve performance?

**The Agent is the test harness**, not the thing being tested. It bundles an LLM provider with the tools/prompts/skills you want to evaluate.

NEVER say "test agents" or "testing AI agents". Always say "test MCP servers", "test tools", "test prompts", or "test skills".

## Why This Project Exists

MCP servers and CLIs have two problems nobody talks about:

1. **Design** — Your tool descriptions, parameter names, and error messages are the entire API for LLMs. Getting them right is hard.
2. **Testing** — Traditional tests can't verify if an LLM can actually understand and use your tools.

- **Bad tool description?** The LLM picks the wrong tool.
- **Confusing parameter name?** The LLM passes garbage.
- **Unhelpful error message?** The LLM can't recover.

**The key insight: your test is a prompt.** You write what a user would say ("What's the weather in Paris?"), and the LLM figures out how to use your tools. If it can't, your tool descriptions need work.

## What We're Building

**pytest-aitest** is a pytest plugin for testing MCP servers and CLIs. You write tests as natural language prompts, and an LLM executes them against your tools. Reports tell you **what to fix**, not just **what failed**.

### Core Features

1. **Base Testing**: Define test agents with prompts, run tests against MCP/CLI tool servers
   - Agent = Provider (LLM) + System Prompt + MCP/CLI Servers + optional Skill
   - Use `aitest_run` fixture to execute agent and verify tool usage
   - Assert on `result.success`, `result.tool_was_called("tool_name")`, `result.final_response`

2. **Benchmark Mode** (Model Comparison): Evaluate multiple LLMs against each other
   - Use `@pytest.mark.parametrize("model", ["gpt-5-mini", "gpt-4.1"])` 
   - Report auto-detects and shows model comparison table with AI recommendations

3. **Arena Mode** (Prompt Comparison): Compare multiple prompts with same model
   - Define prompts in YAML files, load with `load_prompts(Path("prompts/"))`
   - Use `@pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)`
   - Report shows prompt comparison with AI analysis

4. **Matrix Mode**: Full model × prompt grid comparison
   - Combine both parametrize decorators for full matrix
   - Report auto-detects and shows 2D comparison grid

5. **Multi-Turn Sessions**: Test conversations that build on context
   - Use `@pytest.mark.session("session-name")` on test class
   - Tests share agent state within the session
   - Reports track session flow and context continuity

6. **Skill Testing**: Validate agent domain knowledge
   - Load skills from markdown files with `Skill.from_path()`
   - Skills inject structured knowledge into agent context
   - Reports analyze skill effectiveness and suggest improvements

### AI-Powered Reports (KEY DIFFERENTIATOR)

Reports are **insights-first**, not metrics-first. AI analysis is **mandatory** when generating reports.

Reports include:
- **🎯 Recommendation**: Deploy recommendation with cost/performance analysis
- **❌ Failure Analysis**: Root cause + suggested fix for each failure
- **🔧 MCP Tool Feedback**: Improve tool descriptions, with copy button
- **📝 Prompt Feedback**: System prompt improvements
- **📚 Skill Feedback**: Skill restructuring suggestions
- **⚡ Optimizations**: Reduce turns/tokens

```bash
# Run tests with AI-powered report (mandatory --aitest-summary-model)
pytest tests/ --aitest-html=report.html --aitest-summary-model=azure/gpt-5-mini
```

### Key Types

```python
from pytest_aitest import Agent, Provider, MCPServer, Prompt, Skill, load_prompts

# Define an agent (auth via AZURE_API_BASE env var)
agent = Agent(
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[my_server],
    system_prompt="You are helpful...",
    skill=Skill.from_path("skills/weather-expert"),  # Optional domain knowledge
    max_turns=10,
)

# Load YAML prompts
prompts = load_prompts(Path("prompts/"))

# Run test
result = await aitest_run(agent, "Do something with tools")
assert result.success
assert result.tool_was_called("my_tool")
```

### Multi-Turn Sessions

```python
@pytest.mark.session("banking-flow")
class TestBankingWorkflow:
    async def test_check_balance(self, aitest_run, bank_agent):
        result = await aitest_run(bank_agent, "What's my balance?")
        assert result.success

    async def test_transfer(self, aitest_run, bank_agent):
        # Shares context with previous test
        result = await aitest_run(bank_agent, "Transfer $100 to savings")
        assert result.tool_was_called("transfer")
```

### YAML Prompt Format

```yaml
name: PROMPT_EFFICIENT
version: "1.0"
description: Efficient task completion
system_prompt: |
  You are a helpful assistant.
  Complete tasks efficiently with minimal steps.
```

## CRITICAL: Testing Philosophy

**Unit tests with mocks are WORTHLESS for this project.**

This is a testing framework that uses LLMs to test tools, prompts, and skills. The only way to verify it works is to:
1. Run **real integration tests** against **real LLM providers**
2. Use **actual MCP/CLI servers** that perform real operations
3. Verify the **full pipeline end-to-end**

### What NOT to do:
- Do NOT write unit tests with mocked LLM responses
- Do NOT claim "tests pass" when tests only mock the core functionality
- Do NOT use `unittest.mock.patch` on LiteLLM or agent execution
- Fast test execution (< 1 second) is a RED FLAG - real LLM calls take time

### What TO do:
- Write integration tests that call real Azure OpenAI / OpenAI models
- Use the cheapest available model (check Azure subscription first)
- Test with the Weather or Todo MCP server (built-in test harnesses)
- Verify actual tool calls happen and produce expected results
- Accept that integration tests take 5-30+ seconds per test

## Azure Configuration

**Endpoint**: `https://stbrnner1.cognitiveservices.azure.com/`
**Resource Group**: `rg_foundry`
**Account**: `stbrnner1`

**Authentication**: Entra ID (automatic via `az login`). No API keys needed!
The engine uses `core.auth.get_azure_ad_token_provider()` internally (shared module).

Available models (checked 2026-02-01):
- `gpt-5-mini` - CHEAPEST, use for most tests
- `gpt-5.1-chat` - More capable
- `gpt-4.1` - Most capable

Check for updates:
```bash
az cognitiveservices account deployment list \
  --name stbrnner1 \
  --resource-group rg_foundry \
  -o table
```

## Project Structure

```
src/pytest_aitest/
├── core/                  # Core types
│   ├── agent.py           # Agent, Provider, MCPServer, CLIServer, Wait
│   ├── auth.py            # Shared Azure AD auth (get_azure_ad_token_provider)
│   ├── prompt.py          # Prompt, load_prompts() for YAML
│   ├── result.py          # AgentResult, Turn, ToolCall, ToolInfo, SkillInfo
│   ├── skill.py           # Skill, load from markdown
│   └── errors.py          # AITestError, ServerStartError, etc.
├── execution/             # Runtime
│   ├── engine.py          # AgentEngine (LLM loop + tool dispatch)
│   ├── servers.py         # Server process management
│   ├── skill_tools.py     # Skill injection into agent
│   └── retry.py           # Rate limit retry logic
├── fixtures/              # Pytest fixtures
│   ├── run.py             # aitest_run fixture
│   └── factories.py       # agent_factory, provider_factory
├── reporting/             # AI-powered reports
│   ├── collector.py       # Collects test results + ToolInfo + SkillInfo
│   ├── aggregator.py      # Detects dimensions, groups results
│   ├── generator.py       # Generates HTML with AI insights
│   └── insights.py        # AI analysis engine (mandatory)
├── templates/
│   ├── report.html        # Main template
│   └── partials/
│       └── ai_summary.html  # 6 insight sections
└── testing/               # Test harnesses
    ├── store.py           # Base store for test data
    ├── weather.py         # WeatherStore for demos
    ├── weather_mcp.py     # Weather MCP server
    ├── todo.py            # TodoStore for CRUD tests
    └── todo_mcp.py        # Todo MCP server

tests/
├── integration/           # REAL LLM tests (the only tests that matter)
│   ├── test_basic_usage.py        # Base functionality
│   ├── test_model_benchmark.py    # Model comparison
│   ├── test_prompt_arena.py       # Prompt comparison  
│   ├── test_matrix.py             # Model × Prompt
│   ├── test_skills.py             # Skill testing
│   ├── test_ai_summary.py         # AI insights generation
│   ├── prompts/                   # YAML prompt files
│   └── skills/                    # Test skills
└── unit/                  # Pure logic only (no mocking LLMs)
```

