# Agent Skills

An **Agent Skill** is a domain knowledge module following the [agentskills.io](https://agentskills.io/specification) specification. Skills provide:

- **Instructions** — Prepended to the system prompt
- **References** — On-demand documents the agent can look up

## Creating a Skill

A skill is a directory with a `SKILL.md` file:

```
weather-expert/
├── SKILL.md           # Instructions (required)
└── references/        # On-demand lookup docs (optional)
    └── clothing-guide.md
```

### SKILL.md Format

```markdown
---
name: weather-expert
description: Guidelines for interpreting weather data
---

# Weather Expert Guidelines

## Temperature Interpretation
- Below 0°C: Freezing, warn about ice
- 0-10°C: Cold, recommend warm clothing  
- 10-20°C: Mild, light jacket sufficient
- Above 20°C: Warm, no jacket needed

For clothing recommendations, use the reference document.
```

## Using a Skill

```python
from pytest_aitest import Agent, Provider, MCPServer, Skill

skill = Skill.from_path("skills/weather-expert")

agent = Agent(
    name="with-skill",
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[weather_server],
    skill=skill,
)
```

## Testing Skill Effectiveness

Compare agents with and without skills:

```python
skill = Skill.from_path("skills/weather-expert")

agent_without_skill = Agent(
    name="without-skill",
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[weather_server],
)

agent_with_skill = Agent(
    name="with-skill",
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[weather_server],
    skill=skill,
)

AGENTS = [agent_without_skill, agent_with_skill]

@pytest.mark.parametrize("agent", AGENTS, ids=lambda a: a.name)
@pytest.mark.asyncio
async def test_clothing_recommendation(aitest_run, agent):
    """Does the skill improve clothing recommendations?"""
    result = await aitest_run(
        agent, 
        "It's 5°C in Paris. What should I wear?"
    )
    assert result.success
```

The report shows whether the skill improves performance.

## Using the skill_factory Fixture

For cleaner test setup, use the `skill_factory` fixture:

```python
@pytest.fixture
def weather_skill(skill_factory):
    return skill_factory("skills/weather-expert")

@pytest.mark.asyncio
async def test_with_skill(aitest_run, weather_skill):
    agent = Agent(
        name="test",
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[weather_server],
        skill=weather_skill,
    )
    result = await aitest_run(agent, "What should I wear in 5°C?")
    assert result.success
```

## Next Steps

- [Comparing Configurations](comparing.md) — Systematic testing patterns
- [Multi-Turn Sessions](sessions.md) — Conversations with context
