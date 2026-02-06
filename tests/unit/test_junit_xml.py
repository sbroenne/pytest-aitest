"""Tests for plugin JUnit XML enrichment."""

from __future__ import annotations

from dataclasses import dataclass, field

from pytest_aitest.core.result import AgentResult, SkillInfo, ToolCall, Turn
from pytest_aitest.plugin import _add_junit_properties


@dataclass
class MockReport:
    """Mock pytest report with user_properties."""

    user_properties: list[tuple[str, str]] = field(default_factory=list)


class TestAddJunitProperties:
    """Tests for _add_junit_properties function."""

    def test_basic_agent_identity(self) -> None:
        """Test agent name and model are added."""
        report = MockReport()
        result = AgentResult(
            turns=[],
            success=True,
            agent_name="test-agent",
            model="gpt-5-mini",
        )

        _add_junit_properties(report, result, {})

        props = dict(report.user_properties)
        assert props["aitest.agent.name"] == "test-agent"
        assert props["aitest.model"] == "gpt-5-mini"
        assert props["aitest.success"] == "true"

    def test_skill_info(self) -> None:
        """Test skill name is added."""
        report = MockReport()
        result = AgentResult(
            turns=[],
            success=True,
            skill_info=SkillInfo(
                name="weather-expert",
                description="Weather knowledge",
                instruction_content="Expert weather advice",
            ),
        )

        _add_junit_properties(report, result, {})

        props = dict(report.user_properties)
        assert props["aitest.skill"] == "weather-expert"

    def test_prompt_from_metadata(self) -> None:
        """Test system prompt name from metadata."""
        report = MockReport()
        result = AgentResult(turns=[], success=True)

        _add_junit_properties(report, result, {"prompt": "concise"})

        props = dict(report.user_properties)
        assert props["aitest.prompt"] == "concise"

    def test_token_usage(self) -> None:
        """Test token counts are added."""
        report = MockReport()
        result = AgentResult(
            turns=[],
            success=True,
            token_usage={
                "prompt_tokens": 1250,
                "completion_tokens": 89,
                "total_tokens": 1339,
            },
        )

        _add_junit_properties(report, result, {})

        props = dict(report.user_properties)
        assert props["aitest.tokens.input"] == "1250"
        assert props["aitest.tokens.output"] == "89"
        assert props["aitest.tokens.total"] == "1339"

    def test_cost(self) -> None:
        """Test cost is added with proper formatting."""
        report = MockReport()
        result = AgentResult(
            turns=[],
            success=True,
            cost_usd=0.000425,
        )

        _add_junit_properties(report, result, {})

        props = dict(report.user_properties)
        assert props["aitest.cost_usd"] == "0.000425"

    def test_turns_count(self) -> None:
        """Test turn count is added."""
        report = MockReport()
        result = AgentResult(
            turns=[
                Turn(role="user", content="Hello"),
                Turn(role="assistant", content="Hi there"),
                Turn(role="user", content="Thanks"),
            ],
            success=True,
        )

        _add_junit_properties(report, result, {})

        props = dict(report.user_properties)
        assert props["aitest.turns"] == "3"

    def test_tools_called(self) -> None:
        """Test tools called are listed."""
        report = MockReport()
        result = AgentResult(
            turns=[
                Turn(
                    role="assistant",
                    content="",
                    tool_calls=[
                        ToolCall(name="get_weather", arguments={"city": "Paris"}),
                        ToolCall(name="get_forecast", arguments={"city": "Paris"}),
                    ],
                ),
                Turn(
                    role="assistant",
                    content="",
                    tool_calls=[
                        ToolCall(name="get_weather", arguments={"city": "London"}),
                    ],
                ),
            ],
            success=True,
        )

        _add_junit_properties(report, result, {})

        props = dict(report.user_properties)
        # Should be unique and sorted
        assert props["aitest.tools.called"] == "get_forecast,get_weather"

    def test_failure_status(self) -> None:
        """Test failed agent shows false."""
        report = MockReport()
        result = AgentResult(turns=[], success=False, error="Timeout")

        _add_junit_properties(report, result, {})

        props = dict(report.user_properties)
        assert props["aitest.success"] == "false"

    def test_no_user_properties_attribute(self) -> None:
        """Test graceful handling when report lacks user_properties."""

        class BareReport:
            pass

        report = BareReport()
        result = AgentResult(turns=[], success=True)

        # Should not raise
        _add_junit_properties(report, result, {})

    def test_full_example(self) -> None:
        """Test complete example with all fields populated."""
        report = MockReport()
        result = AgentResult(
            turns=[
                Turn(
                    role="assistant",
                    content="Weather in Paris: 18°C",
                    tool_calls=[ToolCall(name="get_weather", arguments={"city": "Paris"})],
                ),
            ],
            success=True,
            agent_name="weather-agent",
            model="gpt-5-mini",
            skill_info=SkillInfo(name="weather-expert", description="", instruction_content=""),
            token_usage={"prompt_tokens": 500, "completion_tokens": 50, "total_tokens": 550},
            cost_usd=0.00125,
        )

        _add_junit_properties(report, result, {"prompt": "detailed"})

        props = dict(report.user_properties)
        assert props["aitest.agent.name"] == "weather-agent"
        assert props["aitest.model"] == "gpt-5-mini"
        assert props["aitest.skill"] == "weather-expert"
        assert props["aitest.prompt"] == "detailed"
        assert props["aitest.tokens.input"] == "500"
        assert props["aitest.tokens.output"] == "50"
        assert props["aitest.tokens.total"] == "550"
        assert props["aitest.cost_usd"] == "0.001250"
        assert props["aitest.turns"] == "1"
        assert props["aitest.tools.called"] == "get_weather"
        assert props["aitest.success"] == "true"
