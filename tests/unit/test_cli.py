"""Tests for CLI report regeneration."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

from pytest_aitest.cli import (
    _deserialize_agent_result,
    _deserialize_test,
    _deserialize_tool_call,
    _deserialize_turn,
    get_config_value,
    load_config_from_pyproject,
    load_suite_report,
    main,
)
from pytest_aitest.core.result import AgentResult, ToolCall, Turn
from pytest_aitest.reporting.collector import TestReport


class TestConfigLoading:
    """Tests for configuration loading from pyproject.toml and env vars."""

    def test_cli_value_takes_precedence(self) -> None:
        with mock.patch.dict(os.environ, {"AITEST_SUMMARY_MODEL": "env-model"}):
            result = get_config_value("summary-model", "cli-model", "AITEST_SUMMARY_MODEL")
            assert result == "cli-model"

    def test_env_var_over_pyproject(self, tmp_path: Path, monkeypatch: mock.MagicMock) -> None:
        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.pytest-aitest-report]\nsummary-model = "toml-model"')

        monkeypatch.chdir(tmp_path)
        with mock.patch.dict(os.environ, {"AITEST_SUMMARY_MODEL": "env-model"}):
            result = get_config_value("summary-model", None, "AITEST_SUMMARY_MODEL")
            assert result == "env-model"

    def test_pyproject_fallback(self, tmp_path: Path, monkeypatch: mock.MagicMock) -> None:
        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.pytest-aitest-report]\nsummary-model = "toml-model"')

        monkeypatch.chdir(tmp_path)
        # Clear env var if set
        env = {k: v for k, v in os.environ.items() if k != "AITEST_SUMMARY_MODEL"}
        with mock.patch.dict(os.environ, env, clear=True):
            result = get_config_value("summary-model", None, "AITEST_SUMMARY_MODEL")
            assert result == "toml-model"

    def test_returns_none_when_not_configured(
        self, tmp_path: Path, monkeypatch: mock.MagicMock
    ) -> None:
        monkeypatch.chdir(tmp_path)
        env = {k: v for k, v in os.environ.items() if k != "AITEST_SUMMARY_MODEL"}
        with mock.patch.dict(os.environ, env, clear=True):
            result = get_config_value("summary-model", None, "AITEST_SUMMARY_MODEL")
            assert result is None

    def test_load_config_no_pyproject(self, tmp_path: Path, monkeypatch: mock.MagicMock) -> None:
        monkeypatch.chdir(tmp_path)
        result = load_config_from_pyproject()
        assert result == {}


class TestDeserializeToolCall:
    """Tests for ToolCall deserialization."""

    def test_basic_tool_call(self) -> None:
        data = {
            "name": "get_weather",
            "arguments": {"city": "Paris"},
            "result": "Sunny, 20°C",
            "error": None,
        }
        tc = _deserialize_tool_call(data)

        assert isinstance(tc, ToolCall)
        assert tc.name == "get_weather"
        assert tc.arguments == {"city": "Paris"}
        assert tc.result == "Sunny, 20°C"
        assert tc.error is None

    def test_tool_call_with_error(self) -> None:
        data = {
            "name": "read_file",
            "arguments": {"path": "/missing"},
            "result": None,
            "error": "File not found",
        }
        tc = _deserialize_tool_call(data)

        assert tc.error == "File not found"
        assert tc.result is None


class TestDeserializeTurn:
    """Tests for Turn deserialization."""

    def test_user_turn(self) -> None:
        data = {
            "role": "user",
            "content": "What's the weather?",
            "tool_calls": [],
        }
        turn = _deserialize_turn(data)

        assert isinstance(turn, Turn)
        assert turn.role == "user"
        assert turn.content == "What's the weather?"
        assert turn.tool_calls == []

    def test_assistant_turn_with_tools(self) -> None:
        data = {
            "role": "assistant",
            "content": "Here's the weather",
            "tool_calls": [
                {"name": "get_weather", "arguments": {}, "result": "Sunny", "error": None}
            ],
        }
        turn = _deserialize_turn(data)

        assert turn.role == "assistant"
        assert len(turn.tool_calls) == 1
        assert turn.tool_calls[0].name == "get_weather"


class TestDeserializeAgentResult:
    """Tests for AgentResult deserialization."""

    def test_successful_result(self) -> None:
        data = {
            "success": True,
            "error": None,
            "duration_ms": 1500.0,
            "token_usage": {"prompt": 100, "completion": 50},
            "cost_usd": 0.001,
            "turns": [
                {"role": "user", "content": "Hello", "tool_calls": []},
                {"role": "assistant", "content": "Hi!", "tool_calls": []},
            ],
        }
        result = _deserialize_agent_result(data)

        assert isinstance(result, AgentResult)
        assert result.success is True
        assert result.duration_ms == 1500.0
        assert result.token_usage == {"prompt": 100, "completion": 50}
        assert result.cost_usd == 0.001
        assert len(result.turns) == 2

    def test_failed_result(self) -> None:
        data = {
            "success": False,
            "error": "Rate limit exceeded",
            "duration_ms": 500.0,
            "token_usage": {},
            "cost_usd": 0.0,
            "turns": [],
        }
        result = _deserialize_agent_result(data)

        assert result.success is False
        assert result.error == "Rate limit exceeded"


class TestDeserializeTest:
    """Tests for TestReport deserialization."""

    def test_basic_test(self) -> None:
        data = {
            "name": "test_example",
            "outcome": "passed",
            "duration_ms": 100.0,
            "metadata": {"model": "gpt-4"},
        }
        test = _deserialize_test(data)

        assert isinstance(test, TestReport)
        assert test.name == "test_example"
        assert test.outcome == "passed"
        assert test.duration_ms == 100.0
        assert test.metadata == {"model": "gpt-4"}

    def test_test_with_agent_result(self) -> None:
        data = {
            "name": "test_weather",
            "outcome": "passed",
            "duration_ms": 5000.0,
            "metadata": {},
            "agent_result": {
                "success": True,
                "error": None,
                "duration_ms": 4000.0,
                "token_usage": {"prompt": 200, "completion": 100},
                "cost_usd": 0.002,
                "turns": [],
            },
        }
        test = _deserialize_test(data)

        assert test.agent_result is not None
        assert test.agent_result.success is True
        assert test.agent_result.cost_usd == 0.002

    def test_test_with_docstring(self) -> None:
        data = {
            "name": "test_example",
            "outcome": "passed",
            "duration_ms": 100.0,
            "metadata": {},
            "docstring": "Test that the example works correctly.",
        }
        test = _deserialize_test(data)

        assert test.docstring == "Test that the example works correctly."


class TestLoadSuiteReport:
    """Tests for loading SuiteReport from JSON."""

    def test_load_basic_report(self, tmp_path: Path) -> None:
        json_data = {
            "name": "test-suite",
            "timestamp": "2026-01-31T12:00:00Z",
            "duration_ms": 1000.0,
            "summary": {"passed": 2, "failed": 1, "skipped": 0},
            "tests": [
                {"name": "test_a", "outcome": "passed", "duration_ms": 100.0, "metadata": {}},
                {"name": "test_b", "outcome": "passed", "duration_ms": 200.0, "metadata": {}},
                {"name": "test_c", "outcome": "failed", "duration_ms": 300.0, "metadata": {}},
            ],
        }
        json_path = tmp_path / "results.json"
        json_path.write_text(json.dumps(json_data))

        report, ai_summary = load_suite_report(json_path)

        assert report.name == "test-suite"
        assert report.passed == 2
        assert report.failed == 1
        assert len(report.tests) == 3
        assert ai_summary is None

    def test_load_report_with_ai_summary(self, tmp_path: Path) -> None:
        json_data = {
            "name": "test-suite",
            "timestamp": "2026-01-31T12:00:00Z",
            "duration_ms": 1000.0,
            "summary": {"passed": 1, "failed": 0, "skipped": 0},
            "tests": [],
            "ai_summary": "All tests passed successfully.",
        }
        json_path = tmp_path / "results.json"
        json_path.write_text(json.dumps(json_data))

        report, ai_summary = load_suite_report(json_path)

        assert ai_summary == "All tests passed successfully."


class TestMainCLI:
    """Tests for main CLI entry point."""

    def test_missing_json_file(self, tmp_path: Path) -> None:
        result = main([str(tmp_path / "nonexistent.json"), "--html", "out.html"])
        assert result == 1  # Error exit code

    def test_no_output_format(self, tmp_path: Path) -> None:
        json_path = tmp_path / "results.json"
        json_path.write_text('{"name": "test", "tests": [], "summary": {}}')

        result = main([str(json_path)])
        assert result == 1  # Error: no output format specified

    def test_summary_without_model(self, tmp_path: Path) -> None:
        json_path = tmp_path / "results.json"
        json_path.write_text('{"name": "test", "tests": [], "summary": {}}')

        result = main([str(json_path), "--html", "out.html", "--summary"])
        assert result == 1  # Error: --summary requires --summary-model

    def test_generate_html(self, tmp_path: Path) -> None:
        json_data = {
            "name": "test-suite",
            "timestamp": "2026-01-31T12:00:00Z",
            "duration_ms": 100.0,
            "summary": {"passed": 1, "failed": 0, "skipped": 0},
            "tests": [
                {"name": "test_a", "outcome": "passed", "duration_ms": 100.0, "metadata": {}}
            ],
        }
        json_path = tmp_path / "results.json"
        json_path.write_text(json.dumps(json_data), encoding="utf-8")
        html_path = tmp_path / "report.html"

        result = main([str(json_path), "--html", str(html_path)])

        assert result == 0
        assert html_path.exists()
        assert "test-suite" in html_path.read_text(encoding="utf-8")

    def test_generate_markdown(self, tmp_path: Path) -> None:
        json_data = {
            "name": "test-suite",
            "timestamp": "2026-01-31T12:00:00Z",
            "duration_ms": 100.0,
            "summary": {"passed": 1, "failed": 0, "skipped": 0},
            "tests": [
                {"name": "test_a", "outcome": "passed", "duration_ms": 100.0, "metadata": {}}
            ],
        }
        json_path = tmp_path / "results.json"
        json_path.write_text(json.dumps(json_data), encoding="utf-8")
        md_path = tmp_path / "report.md"

        result = main([str(json_path), "--md", str(md_path)])

        assert result == 0
        assert md_path.exists()
        assert "# test-suite" in md_path.read_text(encoding="utf-8")

    def test_generate_both_formats(self, tmp_path: Path) -> None:
        json_data = {
            "name": "test-suite",
            "timestamp": "2026-01-31T12:00:00Z",
            "duration_ms": 100.0,
            "summary": {"passed": 1, "failed": 0, "skipped": 0},
            "tests": [],
        }
        json_path = tmp_path / "results.json"
        json_path.write_text(json.dumps(json_data), encoding="utf-8")
        html_path = tmp_path / "report.html"
        md_path = tmp_path / "report.md"

        result = main([str(json_path), "--html", str(html_path), "--md", str(md_path)])

        assert result == 0
        assert html_path.exists()
        assert md_path.exists()

    def test_preserves_existing_ai_summary(self, tmp_path: Path) -> None:
        json_data = {
            "name": "test-suite",
            "timestamp": "2026-01-31T12:00:00Z",
            "duration_ms": 100.0,
            "summary": {"passed": 1, "failed": 0, "skipped": 0},
            "tests": [],
            "ai_summary": "Existing summary from test run.",
        }
        json_path = tmp_path / "results.json"
        json_path.write_text(json.dumps(json_data), encoding="utf-8")
        md_path = tmp_path / "report.md"

        result = main([str(json_path), "--md", str(md_path)])

        assert result == 0
        content = md_path.read_text(encoding="utf-8")
        assert "Existing summary from test run." in content
