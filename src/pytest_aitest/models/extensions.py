"""Extended Pydantic models with computed properties and helper methods.

These extend the auto-generated models with business logic.
"""

from __future__ import annotations

from typing import Any

from ._generated import (
    AgentResult as _AgentResult,
    PytestAitestReport as _PytestAitestReport,
    TestReport as _TestReport,
    ToolCall,
    Turn,
)


class AgentResult(_AgentResult):
    """Extended AgentResult with computed properties for inspection."""

    @property
    def all_tool_calls(self) -> list[ToolCall]:
        """Get all tool calls across all turns."""
        calls = []
        for turn in self.turns:
            calls.extend(turn.tool_calls)
        return calls

    @property
    def tool_names_called(self) -> set[str]:
        """Get set of all tool names that were called."""
        return {call.name for call in self.all_tool_calls}

    def tool_was_called(self, name: str) -> bool:
        """Check if a specific tool was called."""
        return name in self.tool_names_called

    def tool_call_count(self, name: str) -> int:
        """Count how many times a specific tool was called."""
        return len(self.tool_calls_for(name))

    def tool_calls_for(self, name: str) -> list[ToolCall]:
        """Get all calls to a specific tool."""
        return [c for c in self.all_tool_calls if c.name == name]

    def tool_call_arg(self, tool_name: str, arg_name: str) -> Any:
        """Get argument value from the first call to a tool."""
        calls = self.tool_calls_for(tool_name)
        if calls:
            return calls[0].arguments.get(arg_name)
        return None

    @property
    def computed_final_response(self) -> str:
        """Compute final response from turns if not set."""
        if self.final_response:
            return self.final_response
        for turn in reversed(self.turns):
            if turn.role == "assistant" and turn.content:
                return turn.content
        return ""

    @property
    def all_responses(self) -> list[str]:
        """Get all assistant responses."""
        return [t.content for t in self.turns if t.role == "assistant"]

    @property
    def is_session_continuation(self) -> bool:
        """Check if this result is part of a multi-turn session."""
        return (self.session_context_count or 0) > 0

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        if self.token_usage:
            return (self.token_usage.prompt or 0) + (self.token_usage.completion or 0)
        return 0


class TestReport(_TestReport):
    """Extended TestReport with computed properties."""

    @property
    def is_passed(self) -> bool:
        return self.outcome == "passed"

    @property
    def is_failed(self) -> bool:
        return self.outcome == "failed"

    @property
    def short_name(self) -> str:
        """Extract just the test function name from the full node ID."""
        return self.name.split("::")[-1]

    @property
    def display_name(self) -> str:
        """Human-readable test name: docstring if available, else short test name."""
        if self.docstring:
            return self.docstring.split("\n")[0].strip()
        return self.short_name

    @property
    def model(self) -> str | None:
        """Get model name from metadata if present."""
        return self.metadata.model if self.metadata else None

    @property
    def prompt_name(self) -> str | None:
        """Get prompt name from metadata if present."""
        return self.metadata.prompt if self.metadata else None

    @property
    def tokens_used(self) -> int:
        """Get total tokens used from agent_result if present."""
        if self.agent_result:
            return (
                (self.agent_result.token_usage.prompt or 0)
                + (self.agent_result.token_usage.completion or 0)
            )
        return 0

    @property
    def tool_call_names(self) -> list[str]:
        """Get tool call names from agent_result if present."""
        if self.agent_result:
            return [tc.name for turn in self.agent_result.turns for tc in turn.tool_calls]
        return []


class SuiteReport(_PytestAitestReport):
    """Extended SuiteReport with computed statistics."""

    @property
    def total(self) -> int:
        return self.summary.total

    @property
    def passed(self) -> int:
        return self.summary.passed

    @property
    def failed(self) -> int:
        return self.summary.failed

    @property
    def skipped(self) -> int:
        return self.summary.skipped

    @property
    def pass_rate(self) -> float:
        return self.summary.pass_rate

    @property
    def total_tokens(self) -> int:
        """Sum of all tokens used."""
        return self.summary.total_tokens or 0

    @property
    def total_cost_usd(self) -> float:
        """Sum of all costs in USD."""
        return self.summary.total_cost_usd or 0.0

    @property
    def token_stats(self) -> dict[str, int]:
        """Get min/max/avg token usage."""
        if self.summary.token_stats:
            return {
                "min": self.summary.token_stats.min,
                "max": self.summary.token_stats.max,
                "avg": self.summary.token_stats.avg,
            }
        return {"min": 0, "max": 0, "avg": 0}

    @property
    def cost_stats(self) -> dict[str, float]:
        """Get min/max/avg cost in USD."""
        if self.summary.cost_stats:
            return {
                "min": self.summary.cost_stats.min,
                "max": self.summary.cost_stats.max,
                "avg": self.summary.cost_stats.avg,
            }
        return {"min": 0.0, "max": 0.0, "avg": 0.0}

    @property
    def duration_stats(self) -> dict[str, float]:
        """Get min/max/avg duration in ms."""
        if self.summary.duration_stats:
            return {
                "min": self.summary.duration_stats.min,
                "max": self.summary.duration_stats.max,
                "avg": self.summary.duration_stats.avg,
            }
        return {"min": 0.0, "max": 0.0, "avg": 0.0}

    @property
    def tool_call_count(self) -> int:
        """Total number of tool calls across all tests."""
        return self.summary.total_tool_calls or 0

    @property
    def test_files(self) -> list[str]:
        """Unique test file paths."""
        if self.dimensions and self.dimensions.files:
            return self.dimensions.files
        files = set()
        for t in self.tests:
            if "::" in t.name:
                files.add(t.name.split("::")[0])
        return sorted(files)

    @property
    def models_used(self) -> list[str]:
        """Unique models used across tests."""
        if self.dimensions:
            return self.dimensions.models
        return []

    @property
    def prompts_used(self) -> list[str]:
        """Unique prompts used across tests."""
        if self.dimensions:
            return self.dimensions.prompts
        return []
