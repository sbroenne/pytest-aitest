---
description: "Test GitHub Copilot Coding Agent. Wrap the Copilot SDK as a testable tool provider and validate AI-powered code generation."
---

# How to Test GitHub Copilot Coding Agent

Wrap the GitHub Copilot Coding Agent SDK as a testable tool provider to validate AI-powered workflows.

## Overview

GitHub Copilot Coding Agent provides advanced code generation, file editing, and multi-step planning capabilities. pytest-aitest wraps the Copilot SDK to expose these capabilities as testable tools, similar to MCP servers.

!!! note "Prerequisites"
    - GitHub Copilot subscription
    - `github-copilot-sdk` package installed
    - GitHub Copilot CLI authenticated (`gh copilot auth`)

## Installation

Install the optional dependency:

```bash
pip install pytest-aitest[copilot]
# or
pip install github-copilot-sdk
```

Authenticate with GitHub Copilot CLI:

```bash
gh copilot auth
```

## Basic Setup

```python
from pytest_aitest import GitHubCopilotServer

@pytest.fixture(scope="module")
def copilot_server():
    return GitHubCopilotServer(
        name="copilot-assistant",
        model="gpt-4.1",
        instructions="You are a helpful coding assistant. Be concise and accurate.",
    )
```

## How It Works

The Copilot server wraps the GitHub Copilot SDK and exposes it as a tool:

1. **Creates a tool**: `{name}_execute` that accepts a `prompt` parameter
2. **Manages session**: Initializes Copilot client and creates a persistent session
3. **Streams responses**: Handles streaming responses from Copilot (optional)
4. **Returns structured output**: JSON with `response` or `error`

```python
# The LLM calls the tool like this:
copilot_assistant_execute(prompt="Write a Python function to calculate factorial")
```

## Configuration Options

```python
GitHubCopilotServer(
    name="copilot-assistant",         # Server identifier (required)
    model="gpt-4.1",                   # Model to use (default: gpt-4.1)
    instructions=None,                 # Custom instructions (optional)
    skill_directories=[],              # Skill directories (optional)
    streaming=True,                    # Enable streaming (default: True)
    wait=Wait.ready(),                 # Startup wait strategy (optional)
)
```

| Option | Description | Default |
|--------|-------------|---------|
| `name` | Server identifier | Required |
| `model` | LLM model to use | `gpt-4.1` |
| `instructions` | Custom agent instructions | `None` |
| `skill_directories` | Paths to skill markdown files | `[]` |
| `streaming` | Enable response streaming | `True` |
| `wait` | Server startup wait strategy | `Wait.ready()` |

## Available Models

Common models supported by GitHub Copilot SDK:

- `gpt-4.1` (recommended)
- `gpt-4o`
- `gpt-4o-mini`
- `claude-sonnet-4.5`
- `claude-opus-3`

Check your Copilot subscription for available models.

## Custom Instructions

Provide custom instructions to guide Copilot's behavior:

```python
GitHubCopilotServer(
    name="copilot-expert",
    model="gpt-4.1",
    instructions="""
    You are a senior software engineer focused on code quality.
    
    Guidelines:
    - Always include type hints
    - Write comprehensive docstrings
    - Add error handling
    - Follow PEP 8 style guide
    """,
)
```

## Using Skills

Load custom skills to add domain-specific knowledge:

```python
GitHubCopilotServer(
    name="copilot-pr-analyzer",
    model="gpt-4.1",
    skill_directories=[
        "./.copilot_skills/pr-analyzer/SKILL.md",
        "./.copilot_skills/code-review/SKILL.md",
    ],
)
```

Skills are markdown files that provide context and capabilities to the Copilot agent. See [GitHub's skills documentation](https://github.com/microsoft/skills) for examples.

## Complete Example

```python
import pytest
from pytest_aitest import Agent, GitHubCopilotServer, Provider

@pytest.fixture(scope="module")
def copilot_server():
    return GitHubCopilotServer(
        name="copilot-assistant",
        model="gpt-4.1",
        instructions="Focus on clean, maintainable code with proper documentation.",
    )

@pytest.fixture
def agent_with_copilot(copilot_server):
    return Agent(
        name="code-generator",
        provider=Provider(model="azure/gpt-5-mini"),
        copilot_servers=[copilot_server],
        system_prompt="""
        You have access to a GitHub Copilot coding assistant.
        Use it to generate high-quality code that meets the user's requirements.
        """,
        max_turns=10,
    )

@pytest.mark.asyncio
async def test_code_generation(aitest_run, agent_with_copilot):
    """Test Copilot's code generation capabilities."""
    result = await aitest_run(
        agent_with_copilot,
        "Use Copilot to create a Python class for a binary search tree "
        "with insert, search, and delete methods.",
    )
    
    assert result.success
    assert result.tool_was_called("copilot_assistant_execute")
    assert "class" in result.final_response.lower()
    assert "binary" in result.final_response.lower() or "bst" in result.final_response.lower()

@pytest.mark.asyncio
async def test_multi_step_workflow(aitest_run, agent_with_copilot):
    """Test multi-step workflow with Copilot."""
    result = await aitest_run(
        agent_with_copilot,
        "First, use Copilot to create a simple calculator class. "
        "Then, use Copilot again to generate unit tests for it.",
    )
    
    assert result.success
    # Should call Copilot at least twice
    copilot_calls = [
        call for call in result.all_tool_calls 
        if call.name == "copilot_assistant_execute"
    ]
    assert len(copilot_calls) >= 2
```

## Combining with Other Server Types

Use Copilot alongside MCP and CLI servers:

```python
from pytest_aitest import Agent, CLIServer, GitHubCopilotServer, MCPServer, Provider

@pytest.fixture
def hybrid_agent(filesystem_server, git_server, copilot_server):
    return Agent(
        name="full-stack-agent",
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[filesystem_server],      # File operations
        cli_servers=[git_server],              # Git commands
        copilot_servers=[copilot_server],      # Code generation
        system_prompt="""
        You are a full-stack development assistant with access to:
        - Filesystem tools for reading/writing files
        - Git CLI for version control
        - GitHub Copilot for code generation
        
        Use these tools together to complete development tasks.
        """,
        max_turns=15,
    )

@pytest.mark.asyncio
async def test_end_to_end_development(aitest_run, hybrid_agent):
    """Test complete development workflow."""
    result = await aitest_run(
        hybrid_agent,
        "Create a new Python module with a TodoList class, "
        "generate tests for it using Copilot, "
        "and commit the changes to git.",
    )
    
    assert result.success
    # Should use all three server types
    assert result.tool_was_called("write_file")           # MCP
    assert result.tool_was_called("git_execute")          # CLI
    assert result.tool_was_called("copilot_assistant_execute")  # Copilot
```

## Tool Output Format

Copilot tool results are JSON with structured output:

### Success

```json
{
  "response": "Here's a Python class for a binary search tree:\n\nclass BinarySearchTree:\n    ..."
}
```

### Error

```json
{
  "error": "Session not initialized: Copilot client failed to start"
}
```

## Testing Copilot Configuration

Test different Copilot configurations using pytest parametrize:

```python
import pytest

@pytest.mark.parametrize("model", ["gpt-4.1", "gpt-4o", "claude-sonnet-4.5"])
@pytest.mark.asyncio
async def test_model_comparison(aitest_run, model):
    """Compare different Copilot models."""
    copilot_server = GitHubCopilotServer(
        name=f"copilot-{model}",
        model=model,
    )
    
    agent = Agent(
        name=f"agent-{model}",
        provider=Provider(model="azure/gpt-5-mini"),
        copilot_servers=[copilot_server],
        system_prompt="Use Copilot to generate code.",
    )
    
    result = await aitest_run(agent, "Generate a factorial function")
    assert result.success
```

## A/B Testing Custom Instructions

Compare different instruction sets to find the optimal configuration for your use case. The report will show side-by-side comparison.

### Instruction Comparison Pattern

```python
import pytest

# Define instruction sets
QUALITY_INSTRUCTIONS = """You are a senior software engineer focused on code quality.

Guidelines:
- Always include type hints for parameters and return values
- Write comprehensive docstrings in Google style
- Add error handling and input validation
- Follow PEP 8 style conventions"""

PERFORMANCE_INSTRUCTIONS = """You are a performance-oriented software engineer.

Guidelines:
- Optimize for speed and memory efficiency
- Use appropriate data structures for the task
- Include time/space complexity in comments
- Consider algorithmic efficiency"""

INSTRUCTION_SETS = {
    "quality": QUALITY_INSTRUCTIONS,
    "performance": PERFORMANCE_INSTRUCTIONS,
}

@pytest.mark.parametrize(
    "instruction_name,instructions",
    INSTRUCTION_SETS.items(),
    ids=INSTRUCTION_SETS.keys(),
)
@pytest.mark.asyncio
async def test_compare_instructions(aitest_run, instruction_name, instructions):
    """Compare different instruction sets for the same task.
    
    This test runs twice (once per instruction set):
    - quality: Should produce well-documented, type-hinted code
    - performance: Should emphasize efficiency and complexity
    
    The AI analysis will compare which instruction set works best.
    """
    copilot_server = GitHubCopilotServer(
        name=f"copilot-{instruction_name}",
        model="gpt-4.1",
        instructions=instructions,
    )
    
    agent = Agent(
        name=f"copilot-{instruction_name}",
        provider=Provider(model="azure/gpt-5-mini"),
        copilot_servers=[copilot_server],
        system_prompt=f"Use Copilot specialized in {instruction_name} code generation.",
        max_turns=5,
    )
    
    result = await aitest_run(
        agent,
        "Use Copilot to create a Python binary search tree class "
        "with insert, search, and delete methods.",
    )
    
    assert result.success
    assert result.tool_was_called(f"copilot_{instruction_name}_execute")
```

### Multi-Dimension Testing

Test all combinations of models and instructions:

```python
# Test 2×2 matrix: 2 models × 2 instruction sets
@pytest.mark.parametrize("model", ["gpt-4.1", "gpt-4o-mini"])
@pytest.mark.parametrize(
    "instruction_name,instructions",
    INSTRUCTION_SETS.items(),
    ids=INSTRUCTION_SETS.keys(),
)
@pytest.mark.asyncio
async def test_all_combinations(aitest_run, model, instruction_name, instructions):
    """Test all model × instruction combinations.
    
    Creates:
    - gpt-4.1 × quality
    - gpt-4.1 × performance
    - gpt-4o-mini × quality
    - gpt-4o-mini × performance
    
    The AI analysis identifies the optimal combination.
    """
    copilot_server = GitHubCopilotServer(
        name=f"copilot-{model.replace('.', '-')}-{instruction_name}",
        model=model,
        instructions=instructions,
    )
    
    agent = Agent(
        name=f"{model}-{instruction_name}",
        provider=Provider(model="azure/gpt-5-mini"),
        copilot_servers=[copilot_server],
        system_prompt=f"Use Copilot ({model}, {instruction_name}) for code generation.",
        max_turns=5,
    )
    
    result = await aitest_run(
        agent,
        "Use Copilot to write a factorial function in Python.",
    )
    
    assert result.success
```

### Viewing Results

Generate a comparison report:

```bash
# Run A/B tests and generate report
pytest tests/ --aitest-html=copilot_comparison.html

# View the report (opens in browser)
open copilot_comparison.html
```

The report will show:

- **Agent Leaderboard** — Ranked by pass rate and cost
- **Test Comparison** — Side-by-side results for each agent
- **AI Analysis** — Recommendations on which configuration to deploy

## Troubleshooting

### SDK Not Installed

If you get an import error:

```python
ServerStartError: github-copilot-sdk not installed. 
Install with: pip install github-copilot-sdk
```

Install the SDK:

```bash
pip install github-copilot-sdk
# or
pip install pytest-aitest[copilot]
```

### Authentication Failed

If Copilot fails to authenticate:

```bash
# Authenticate with GitHub Copilot CLI
gh copilot auth

# Verify authentication
gh copilot status
```

### Model Not Available

Check your Copilot subscription for available models:

```python
# Use gpt-4.1 (widely available)
GitHubCopilotServer(
    name="copilot",
    model="gpt-4.1",  # Safe default
)
```

### Session Timeout

For long-running workflows, increase the agent's `max_turns`:

```python
Agent(
    provider=Provider(model="azure/gpt-5-mini"),
    copilot_servers=[copilot_server],
    max_turns=20,  # Allow more turns for complex tasks
)
```

## Best Practices

### 1. Clear Instructions

Provide clear instructions to guide the outer agent on when to use Copilot:

```python
system_prompt="""
You have access to a GitHub Copilot coding assistant.

When to use Copilot:
- Generating new code from scratch
- Creating boilerplate code
- Writing unit tests
- Refactoring existing code

Always provide context about what you need in your prompt.
"""
```

### 2. Validate Generated Code

Use assertions to validate Copilot's output:

```python
async def test_code_quality(aitest_run, agent_with_copilot):
    result = await aitest_run(
        agent_with_copilot,
        "Generate a well-documented class with type hints",
    )
    
    assert result.success
    # Check for quality markers
    assert "def " in result.final_response or "class " in result.final_response
    assert '"""' in result.final_response  # Docstring present
```

### 3. Skip Tests When SDK Unavailable

Make tests optional when the SDK isn't installed:

```python
import pytest

pytestmark = pytest.mark.skipif(
    not _copilot_available(),
    reason="github-copilot-sdk not installed",
)

def _copilot_available():
    try:
        import copilot
        return True
    except ImportError:
        return False
```

## What Gets Tested?

When you test with GitHub Copilot server, you're validating:

1. **Tool Usage**: Can the outer agent properly invoke Copilot?
2. **Prompt Quality**: Are the prompts sent to Copilot clear and effective?
3. **Response Handling**: Does the agent correctly process Copilot's responses?
4. **Workflow Integration**: Can Copilot work alongside other tools?

!!! tip "Testing Philosophy"
    You're testing the **interface** to Copilot, not Copilot itself. Focus on validating that your agent can effectively use Copilot as a tool.

> 📁 **Real Example:** [test_copilot_server.py](https://github.com/sbroenne/pytest-aitest/blob/main/tests/integration/test_copilot_server.py) — Complete examples with A/B testing of instructions, model comparison, and multi-dimension testing
