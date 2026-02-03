# Skills vs Prompts

When to use each and how they work together.

## The Difference

**System prompts** define behavior: *how* the agent should act.

**Skills** provide knowledge: *what* the agent should know.

```python
agent = Agent(
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[weather_server],
    
    # Behavior: how to act
    system_prompt="You are a helpful weather assistant. Be concise.",
    
    # Knowledge: what to know
    skill=Skill.from_path("skills/weather-expert"),
)
```

## System Prompts

### What They're Good For

- Defining persona and tone
- Setting output format expectations
- Establishing constraints ("don't make up data")
- Guiding tool selection order

### Example

```python
system_prompt = """
You are a weather assistant.

Rules:
- Always check the weather before answering weather questions
- If location is ambiguous, ask for clarification
- Report temperatures in both Celsius and Fahrenheit
- Be concise but friendly
"""
```

### Characteristics

- Usually short (100-500 tokens)
- Focus on behavior, not facts
- Apply to all interactions
- Easy to A/B test

## Skills

### What They're Good For

- Domain-specific knowledge
- Reference data (thresholds, categories, mappings)
- Decision trees and heuristics
- Examples and templates

### Example

A weather skill might include:

```markdown
# Weather Expert Skill

## Temperature Categories
- Below 0°C: Freezing
- 0-10°C: Cold  
- 10-20°C: Cool
- 20-30°C: Warm
- Above 30°C: Hot

## Clothing Recommendations
- Freezing: Heavy coat, hat, gloves
- Cold: Warm jacket, layers
- Cool: Light jacket
- Warm: Light clothing
- Hot: Breathable fabrics, sun protection

## Severe Weather Alerts
When conditions include: thunderstorm, tornado, hurricane, blizzard
→ Always warn the user and recommend staying indoors
```

### Characteristics

- Can be long (500-5000+ tokens)
- Focus on facts and knowledge
- Structured as markdown files
- Follow [agentskills.io](https://agentskills.io) format

## How They Combine

When an agent has both, the skill is prepended to the system prompt:

```
[Skill content]

---

[System prompt]
```

The LLM sees the knowledge first, then the behavioral instructions.

### Example Combined Context

```
# Weather Expert Skill

## Temperature Categories
- Below 0°C: Freezing
...

## Clothing Recommendations  
- Freezing: Heavy coat, hat, gloves
...

---

You are a weather assistant.

Rules:
- Always check the weather before answering weather questions
- If location is ambiguous, ask for clarification
- Report temperatures in both Celsius and Fahrenheit
- Be concise but friendly
```

## Decision Guide

### Put It in the System Prompt If...

✅ It's about behavior or style  
✅ It's short (< 200 tokens)  
✅ It applies to every interaction  
✅ You want to A/B test variations  

### Put It in a Skill If...

✅ It's domain knowledge or reference data  
✅ It's structured (tables, lists, decision trees)  
✅ It might be reused across agents  
✅ It's long (> 200 tokens)  
✅ It follows the [agentskills.io](https://agentskills.io) format  

### Examples

| Content | Where | Why |
|---------|-------|-----|
| "Be concise" | Prompt | Behavior |
| Temperature thresholds | Skill | Reference data |
| "Use get_weather first" | Prompt | Tool guidance |
| Clothing recommendations | Skill | Domain knowledge |
| Output format template | Prompt | Behavior |
| Error code meanings | Skill | Reference data |

## Testing Implications

### Testing System Prompts

Use Arena mode to compare prompt variations:

```python
@pytest.mark.parametrize("prompt", PROMPTS)
async def test_prompt(aitest_run, prompt):
    agent = Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        system_prompt=prompt.system_prompt,
        mcp_servers=[server],
    )
    result = await aitest_run(agent, "What's the weather?")
    assert result.success
```

### Testing Skills

Test that skills improve performance on domain-specific queries:

```python
async def test_with_skill(aitest_run):
    agent = Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        skill=Skill.from_path("skills/weather-expert"),
        mcp_servers=[weather_server],
    )
    result = await aitest_run(
        agent, 
        "What should I wear in Paris today?"
    )
    assert result.success
    # Skill should enable clothing recommendations
    assert "jacket" in result.final_response.lower() or \
           "coat" in result.final_response.lower()
```

### Testing Both Together

Matrix mode with prompts and skills:

```python
@pytest.mark.parametrize("prompt", PROMPTS)
@pytest.mark.parametrize("skill", [None, weather_skill])
async def test_prompt_skill_combo(aitest_run, prompt, skill):
    agent = Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        system_prompt=prompt.system_prompt,
        skill=skill,
        mcp_servers=[weather_server],
    )
    result = await aitest_run(agent, "Weather query...")
    assert result.success
```

## Anti-Patterns

### ❌ Putting Knowledge in Prompts

```python
# Bad: prompt is too long and hard to maintain
system_prompt = """
You are a weather assistant.

Temperature categories:
- Below 0°C: Freezing
- 0-10°C: Cold
... [500 more lines of reference data]

Be concise and helpful.
"""
```

### ❌ Putting Behavior in Skills

```markdown
# Bad: skill contains behavioral instructions

You should always be polite and professional.
Never make assumptions about the user.
Always double-check your work.
```

### ❌ Duplicating Content

If the same knowledge appears in both the skill and the prompt, the LLM sees it twice, wasting tokens and potentially causing confusion.

## Summary

| Aspect | System Prompt | Skill |
|--------|---------------|-------|
| Purpose | Behavior | Knowledge |
| Length | Short | Long |
| Content | Instructions | Reference data |
| Format | Free text | Structured markdown |
| Testing | Arena mode | Direct assertions |
| Reuse | Per-agent | Across agents |
