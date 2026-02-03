# System Prompts

System prompts define agent behavior. Test different prompts to find what works.

## Adding a System Prompt

```python
agent = Agent(
    name="concise-assistant",
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[weather_server],
    system_prompt="You are a weather assistant. Be concise and direct.",
)
```

## How Prompts Affect Behavior

Different system prompts produce different behaviors:

| System Prompt | Behavior |
|---------------|----------|
| "Be concise." | Short, direct answers |
| "Explain your reasoning." | Verbose, step-by-step responses |
| "Use bullet points." | Structured output format |
| "If unsure, ask clarifying questions." | More cautious, interactive |

The system prompt affects both the *quality* of responses and the *cost* (longer prompts → more tokens).

## System Prompt vs Agent Skill

| Aspect | System Prompt | Agent Skill |
|--------|---------------|-------------|
| Purpose | Define behavior | Provide domain knowledge |
| Content | Instructions | Reference material |
| Example | "Be concise" | "Temperature chart..." |
| Parameter | `system_prompt=` | `skill=` |

You can use both together. The skill content is prepended to the system prompt.

## Comparing Prompts

Test different prompts to find what works best:

```python
PROMPTS = {
    "brief": "Be concise. One sentence max.",
    "detailed": "Explain your reasoning step by step.",
    "structured": "Use bullet points for clarity.",
}

AGENTS = [
    Agent(
        name=f"prompt-{name}",
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[weather_server],
        system_prompt=prompt,
    )
    for name, prompt in PROMPTS.items()
]

@pytest.mark.parametrize("agent", AGENTS, ids=lambda a: a.name)
@pytest.mark.asyncio
async def test_weather_query(aitest_run, agent):
    result = await aitest_run(agent, "What's the weather in Paris?")
    assert result.success
```

The report shows which prompt performs best for your use case.

## Next Steps

- [Agent Skills](skills.md) — Add domain knowledge
- [Comparing Configurations](comparing.md) — Systematic comparison patterns
