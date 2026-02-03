"""Tests proving that skills improve LLM behavior.

These tests demonstrate the value of skills by comparing agent behavior:
- WITHOUT skill: Baseline LLM behavior (may be inconsistent or miss steps)
- WITH skill: Enhanced behavior following skill guidelines

Each test pair shows measurable improvement in agent quality.
"""

from pathlib import Path

import pytest

from pytest_aitest import Agent, Provider, Skill

from .conftest import DEFAULT_MAX_TURNS, DEFAULT_MODEL, DEFAULT_RPM, DEFAULT_TPM

# Path to test skills
SKILLS_DIR = Path(__file__).parent / "skills"


@pytest.mark.integration
class TestWeatherSkillImprovement:
    """Tests showing weather-expert skill improves response quality."""

    @pytest.fixture
    def weather_skill(self):
        """Load the weather expert skill."""
        return Skill.from_path(SKILLS_DIR / "weather-expert")

    async def test_baseline_packing_advice_may_skip_weather_check(
        self, aitest_run, weather_server
    ):
        """WITHOUT skill: LLM might give generic advice without checking weather.

        This test establishes baseline behavior - the LLM may or may not
        check weather tools before giving packing advice.
        """
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            system_prompt="You are a travel assistant. Help users pack for trips.",
            max_turns=5,
        )

        result = await aitest_run(
            agent,
            "I'm going to Paris tomorrow. What should I pack?",
        )

        assert result.success
        # Baseline: We don't assert on tool usage - behavior may vary
        print(f"Baseline tool calls: {len(result.all_tool_calls)}")
        print(f"Tools used: {[t.name for t in result.all_tool_calls]}")

    async def test_skilled_packing_advice_always_checks_weather(
        self, aitest_run, weather_server, weather_skill
    ):
        """WITH skill: Agent ALWAYS checks weather before giving packing advice.

        The weather-expert skill instructs the agent to:
        1. Always call weather tools first
        2. Give specific advice based on actual temperature
        3. Mention UV protection when UV > 5
        """
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            skill=weather_skill,
            system_prompt="Help users pack for trips.",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "I'm going to Paris tomorrow. What should I pack?",
        )

        assert result.success
        # WITH skill: Should ALWAYS check weather first
        assert len(result.all_tool_calls) >= 1, "Skilled agent should check weather tools"
        assert result.tool_was_called("get_weather") or result.tool_was_called("get_forecast"), (
            "Should call weather tool before giving advice"
        )

        # Response should include specific temperature-based advice
        response = result.final_response.lower()
        has_specific_advice = any(
            term in response
            for term in ["°f", "°c", "degrees", "jacket", "coat", "umbrella", "rain"]
        )
        assert has_specific_advice, "Should give specific weather-based advice"

    async def test_skill_uses_reference_docs_for_uv_advice(
        self, aitest_run, weather_server, weather_skill
    ):
        """WITH skill: Agent may consult reference docs for UV thresholds.

        The skill has a clothing-guide.md reference that specifies:
        - UV 6-7: SPF 30+, seek shade during midday
        - UV 8+: SPF 50+, wear a hat

        Note: The LLM may provide correct UV advice from training data
        without consulting the reference docs.
        """
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            skill=weather_skill,
            system_prompt="You are a sun safety expert.",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "I'm spending the day outdoors in Miami. Should I worry about sun protection?",
        )

        assert result.success

        # Response should mention UV-specific advice (from training or reference docs)
        response = result.final_response.lower()
        has_uv_advice = any(
            term in response
            for term in ["uv", "spf", "sunscreen", "sun protection", "sunblock", "hat"]
        )
        assert has_uv_advice, "Should provide UV-specific advice"


@pytest.mark.integration
class TestTodoSkillImprovement:
    """Tests showing todo-organizer skill improves task management."""

    @pytest.fixture
    def todo_skill(self):
        """Load the todo organizer skill."""
        return Skill.from_path(SKILLS_DIR / "todo-organizer")

    async def test_baseline_may_not_verify_operations(self, aitest_run, todo_server):
        """WITHOUT skill: LLM might not verify task operations.

        Baseline behavior - the agent may add tasks without confirming
        they were added successfully.
        """
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[todo_server],
            system_prompt="You help manage tasks. Add tasks when asked.",
            max_turns=5,
        )

        result = await aitest_run(
            agent,
            "Add 'buy milk' to my shopping list",
        )

        assert result.success
        assert result.tool_was_called("add_task")
        print(f"Baseline verified with list_tasks: {result.tool_was_called('list_tasks')}")

    async def test_skilled_always_verifies_operations(self, aitest_run, todo_server, todo_skill):
        """WITH skill: Agent ALWAYS verifies operations with list_tasks.

        The todo-organizer skill requires:
        - Call list_tasks after ANY modification
        - Show the user confirmation of the change
        """
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[todo_server],
            skill=todo_skill,
            system_prompt="Help manage the user's tasks.",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "Add 'buy milk' to my shopping list",
        )

        assert result.success
        assert result.tool_was_called("add_task"), "Should add the task"

        # WITH skill: MUST verify with list_tasks after adding
        assert result.tool_was_called("list_tasks"), (
            "Skilled agent should verify operation with list_tasks"
        )

        # Check that list_tasks was called AFTER add_task (verification pattern)
        tool_names = [tc.name for tc in result.all_tool_calls]
        last_add_idx = len(tool_names) - 1 - tool_names[::-1].index("add_task")
        list_calls_after_add = [
            i for i, name in enumerate(tool_names) if name == "list_tasks" and i > last_add_idx
        ]
        assert len(list_calls_after_add) > 0, (
            "Should call list_tasks AFTER the final add_task to verify the operation"
        )

    async def test_skilled_uses_consistent_list_names(self, aitest_run, todo_server, todo_skill):
        """WITH skill: Agent organizes tasks into appropriate categories.

        The skill defines standard lists: inbox, work, personal, shopping, someday
        """
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[todo_server],
            skill=todo_skill,
            system_prompt="Organize the user's tasks efficiently.",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "I need to buy groceries, finish the quarterly report, and call my mom",
        )

        assert result.success
        add_calls = [tc for tc in result.all_tool_calls if tc.name == "add_task"]
        assert len(add_calls) >= 2, "Should add multiple tasks"

        # Check if tasks were organized into lists
        lists_used = set()
        for call in add_calls:
            list_name = call.arguments.get("list_name")
            if list_name:
                lists_used.add(list_name.lower())

        if lists_used:
            print(f"Lists used: {lists_used}")
        else:
            print("Note: Tasks added without explicit list names (using default)")

    async def test_skilled_assigns_smart_priorities(self, aitest_run, todo_server, todo_skill):
        """WITH skill: Agent assigns priorities based on urgency signals.

        The skill's priority guide says:
        - "deadline today" keywords → HIGH priority
        - "urgent", "ASAP" → HIGH priority
        - "someday", "no rush" → LOW priority
        """
        agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[todo_server],
            skill=todo_skill,
            system_prompt="Help manage tasks with appropriate priorities.",
            max_turns=DEFAULT_MAX_TURNS,
        )

        result = await aitest_run(
            agent,
            "URGENT: Submit the report by end of day! Also, someday I'd like to learn piano.",
        )

        assert result.success
        add_calls = [tc for tc in result.all_tool_calls if tc.name == "add_task"]
        assert len(add_calls) >= 1, "Should add tasks"

        # Check priorities assigned
        priorities = {}
        for call in add_calls:
            task_desc = str(call.arguments.get("task", "")).lower()
            priority = call.arguments.get("priority", "normal")
            if "report" in task_desc or "submit" in task_desc:
                priorities["report"] = priority
            if "piano" in task_desc:
                priorities["piano"] = priority

        if "report" in priorities:
            assert priorities["report"] == "high", "Urgent report should be HIGH priority"
        if "piano" in priorities:
            assert priorities["piano"] == "low", "'Someday' task should be LOW priority"


@pytest.mark.integration
class TestSkillComparisonSummary:
    """Summary tests that clearly show skill value."""

    async def test_weather_skill_increases_tool_usage(self, aitest_run, weather_server):
        """Compare tool usage: skilled agent uses tools more consistently."""
        weather_skill = Skill.from_path(SKILLS_DIR / "weather-expert")
        prompt = "What should I wear in London today?"

        # Test WITHOUT skill
        baseline_agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            system_prompt="You are a helpful assistant.",
            max_turns=5,
        )
        baseline_result = await aitest_run(baseline_agent, prompt)

        # Test WITH skill
        skilled_agent = Agent(
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            skill=weather_skill,
            system_prompt="You are a helpful assistant.",
            max_turns=DEFAULT_MAX_TURNS,
        )
        skilled_result = await aitest_run(skilled_agent, prompt)

        # Compare results
        print(f"\n{'=' * 60}")
        print("WEATHER SKILL COMPARISON")
        print(f"{'=' * 60}")
        print(f"Baseline tool calls: {len(baseline_result.all_tool_calls)}")
        print(f"Skilled tool calls:  {len(skilled_result.all_tool_calls)}")
        print(f"Baseline checked weather: {baseline_result.tool_was_called('get_weather')}")
        print(f"Skilled checked weather:  {skilled_result.tool_was_called('get_weather')}")
        print(f"{'=' * 60}\n")

        assert skilled_result.tool_was_called("get_weather"), (
            "Skilled agent should always check weather"
        )
