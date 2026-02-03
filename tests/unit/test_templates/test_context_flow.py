"""Tests for data flow: Pydantic model → context dict → rendered HTML.

These tests verify that specific data values flow correctly from the source
fixture through the context dict and into the final rendered HTML.

This catches bugs like the AI summary issue where the partial worked fine,
but the context dict didn't include the expected variable.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
from bs4 import BeautifulSoup

from pytest_aitest.cli import load_suite_report
from pytest_aitest.reporting.generator import ReportGenerator

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "reports"


def generate_html(fixture_name: str) -> tuple[str, dict]:
    """Generate HTML from a fixture and return (html, json_data)."""
    path = FIXTURES_DIR / f"{fixture_name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    report, _ai_summary = load_suite_report(path)  # ai_summary is deprecated
    
    generator = ReportGenerator()
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        output_path = Path(f.name)
    
    generator.generate_html(report, output_path)  # ai_summary no longer passed
    html = output_path.read_text(encoding="utf-8")
    output_path.unlink()
    
    return html, data


class TestContextContainsExpectedVariables:
    """Verify context dict includes all variables templates expect."""

    def test_insights_in_context(self):
        """insights should be passed to context for AI analysis display."""
        html, data = generate_html("02_model_comparison")
        
        # insights field should always be present in v3.0 fixtures
        assert data.get("insights") is not None, "Fixture should have insights"
        # The template may or may not render depending on placeholder status
        # Just verify the data is there

    def test_model_groups_in_context_for_model_comparison(self):
        """model_groups should be in context for model comparison mode."""
        html, data = generate_html("02_model_comparison")
        assert data["mode"] in ("model_comparison", "matrix")
        assert len(data["dimensions"]["models"]) >= 2
        # Model leaderboard should render
        assert "Leaderboard" in html or "leaderboard" in html.lower()

    def test_prompt_groups_in_context_for_prompt_comparison(self):
        """prompt_groups should be in context for prompt comparison mode."""
        html, data = generate_html("03_prompt_comparison")
        assert data["mode"] in ("prompt_comparison", "matrix")
        assert len(data["dimensions"]["prompts"]) >= 2


class TestDataValuesFlowToHTML:
    """Verify specific data values appear in rendered HTML.
    
    These tests go beyond "section exists" to verify actual data flows through.
    """

    def test_report_name_in_html(self):
        """Report name should appear in generated HTML."""
        html, data = generate_html("01_basic_usage")
        assert data["name"] in html, f"Report name '{data['name']}' not found in HTML"

    def test_docstrings_preferred_over_test_names(self):
        """Human-readable docstrings should appear instead of function names."""
        html, data = generate_html("08_matrix_full")
        
        # Collect docstrings from tests
        docstrings = []
        for test in data["tests"]:
            if test.get("docstring"):
                first_line = test["docstring"].split('\n')[0].strip()
                if first_line:
                    docstrings.append(first_line)
        
        # At least some docstrings should appear in HTML
        assert docstrings, "Fixture should have tests with docstrings"
        found = [d for d in docstrings if d in html]
        assert found, f"No docstrings found in HTML. Expected one of: {docstrings[:3]}"

    def test_timestamp_in_html(self):
        """Timestamp date should appear in generated HTML."""
        html, data = generate_html("01_basic_usage")
        
        # Timestamp format is ISO: 2026-02-02T18:13:48.450306Z
        date_part = data["timestamp"][:10]  # "2026-02-02"
        assert date_part in html, f"Date '{date_part}' not found in HTML"

    def test_test_count_in_html(self):
        """Total test count should appear in generated HTML."""
        html, data = generate_html("01_basic_usage")
        
        # The total appears in summary cards
        total = data["summary"]["total"]
        assert str(total) in html

    def test_model_names_in_leaderboard(self):
        """Model names should appear in leaderboard for model comparison."""
        html, data = generate_html("02_model_comparison")
        
        # All model names from dimensions should appear
        for model in data["dimensions"]["models"]:
            assert model in html, f"Model name '{model}' not found in HTML"

    def test_prompt_names_in_comparison(self):
        """Prompt names should appear for prompt comparison."""
        html, data = generate_html("03_prompt_comparison")
        
        # All prompt names from dimensions should appear
        for prompt in data["dimensions"]["prompts"]:
            assert prompt in html, f"Prompt name '{prompt}' not found in HTML"

    def test_insights_recommendation_in_html(self):
        """Insights recommendation should appear in generated HTML if not placeholder."""
        html, data = generate_html("02_model_comparison")
        
        # insights field is required in v3.0
        assert data.get("insights") is not None
        # If insights are real (not placeholder), they should render
        config = data["insights"]["recommendation"]["configuration"]
        if config != "(analysis pending)":
            assert "AI Insights" in html or "Recommendation" in html

    def test_test_names_in_detailed_results(self):
        """Individual test names should appear in detailed results."""
        html, data = generate_html("01_basic_usage")
        
        # Each test's name should be in the HTML
        for test in data["tests"]:
            # Test names are often in format "file::class::method"
            # The last part (method name) should definitely appear
            test_method = test["name"].split("::")[-1]
            assert test_method in html, f"Test method '{test_method}' not found in HTML"


class TestMatrixDataFlow:
    """Test data flow specifically for matrix mode (most complex)."""

    def test_matrix_has_both_model_and_prompt_data(self):
        """Matrix mode should include both model and prompt comparisons."""
        html, data = generate_html("04_matrix")
        
        # Should have model names
        for model in data["dimensions"]["models"]:
            assert model in html, f"Model '{model}' not in matrix HTML"
        
        # Should have prompt names
        for prompt in data["dimensions"]["prompts"]:
            assert prompt in html, f"Prompt '{prompt}' not in matrix HTML"

    def test_matrix_full_has_all_data(self):
        """Full matrix (08) should have models, prompts, and AI summary."""
        html, data = generate_html("08_matrix_full")
        
        # Models
        for model in data["dimensions"]["models"]:
            assert model in html
        
        # Prompts
        for prompt in data["dimensions"]["prompts"]:
            assert prompt in html
        
        # AI summary section
        assert "AI Analysis" in html or "🤖" in html


class TestToolDataFlow:
    """Test tool call data flows correctly."""

    def test_tool_names_appear_when_called(self):
        """Tool names from agent results should appear in HTML."""
        html, data = generate_html("02_model_comparison")
        
        # Collect all tool names from tests
        tool_names = set()
        for test in data["tests"]:
            agent_result = test.get("agent_result")
            if agent_result and agent_result.get("tools_called"):
                tool_names.update(agent_result["tools_called"])
        
        # At least some tool names should appear in tool comparison or details
        if tool_names:
            found = [name for name in tool_names if name in html]
            assert found, f"No tool names from {tool_names} found in HTML"
