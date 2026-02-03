"""Tests for report composition - verifying flags correctly include/exclude sections.

This tests the integration between:
1. Generator builds context with flags
2. Template renders correct sections based on flags

These tests verify that when a flag is True, the corresponding section
appears in the HTML, and when False, it doesn't.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from bs4 import BeautifulSoup

from pytest_aitest.cli import load_suite_report
from pytest_aitest.reporting.generator import ReportGenerator

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "reports"


def generate_html(fixture_name: str) -> tuple[str, dict]:
    """Generate HTML from a fixture and return (html, json_data)."""
    path = FIXTURES_DIR / f"{fixture_name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    report, _ai_summary = load_suite_report(path)  # ai_summary deprecated
    
    generator = ReportGenerator()
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        output_path = Path(f.name)
    
    generator.generate_html(report, output_path)  # ai_summary no longer passed
    html = output_path.read_text(encoding="utf-8")
    output_path.unlink()
    
    return html, data


def parse_html(html: str) -> BeautifulSoup:
    """Parse HTML for assertions."""
    return BeautifulSoup(html, "lxml")


class TestAIInsightsComposition:
    """Test AI insights section (v3.0 schema)."""

    def test_insights_field_in_fixtures(self):
        """All v3.0 fixtures should have insights field."""
        _, data = generate_html("02_model_comparison")
        assert data.get("insights") is not None, "Fixture should have insights"

    def test_insights_always_present_in_reports(self):
        """Reports should always have real insights (AI analysis is mandatory)."""
        html, data = generate_html("02_model_comparison")
        
        # Real reports always have insights (AI analysis is mandatory for report generation)
        # Fixture 02 has real insights
        config = data["insights"]["recommendation"]["configuration"]
        assert config != "(analysis pending)", "Real reports should have real insights"
        
        # HTML should show AI Insights section
        assert "AI Insights" in html, "Reports should always have AI insights"


class TestModelLeaderboardComposition:
    """Test model leaderboard appears with 2+ models."""

    def test_leaderboard_in_model_comparison(self):
        """Fixture 02 has 2 models - should show leaderboard."""
        html, data = generate_html("02_model_comparison")
        soup = parse_html(html)
        
        # Should have leaderboard section
        leaderboard = (
            soup.find(id="model-leaderboard") or
            soup.find(string=lambda s: s and "Model Leaderboard" in s)
        )
        assert leaderboard is not None, "Missing model leaderboard section"

    def test_leaderboard_has_both_models(self):
        """Leaderboard should list both models."""
        html, _ = generate_html("02_model_comparison")
        
        assert "gpt-5-mini" in html.lower() or "gpt5-mini" in html.lower()
        assert "gpt-4.1" in html.lower()

    def test_no_leaderboard_in_simple_mode(self):
        """Fixture 01 has 1 model - no leaderboard."""
        html, _ = generate_html("01_basic_usage")
        
        assert "Model Leaderboard" not in html


class TestComparisonGridComposition:
    """Test comparison grid appears in comparison modes."""

    def test_grid_header_model_comparison(self):
        """Model comparison should show 'Test Results by Model'."""
        html, _ = generate_html("02_model_comparison")
        assert "Test Results by Model" in html

    def test_grid_header_prompt_comparison(self):
        """Prompt comparison should show 'Test Results by System Prompt'."""
        html, _ = generate_html("03_prompt_comparison")
        assert "Test Results by System Prompt" in html

    def test_grid_header_matrix(self):
        """Matrix mode should show 'Comparison Matrix'."""
        html, _ = generate_html("04_matrix")
        assert "Comparison Matrix" in html

    def test_no_grid_in_simple_mode(self):
        """Simple mode should not show comparison grid."""
        html, _ = generate_html("01_basic_usage")
        soup = parse_html(html)
        
        # Should not have comparison grid table
        matrix_tables = soup.find_all("table", class_="matrix")
        # Filter out any tables that are actually in the rendered content
        # Simple mode shouldn't have a matrix section at all
        matrix_section = soup.find("h2", string=lambda s: s and "Test Results by" in s)
        assert matrix_section is None, "Simple mode should not have comparison grid"


class TestPromptComparisonComposition:
    """Test prompt comparison section appears with 2+ prompts."""

    def test_prompt_table_in_prompt_comparison(self):
        """Fixture 03 has 3 prompts - should show prompt table."""
        html, _ = generate_html("03_prompt_comparison")
        
        # Should mention all prompts
        assert "brief" in html.lower()
        assert "detailed" in html.lower()
        assert "structured" in html.lower()

    def test_no_prompt_table_in_model_comparison(self):
        """Model comparison (single prompt) should not show prompt table."""
        html, _ = generate_html("02_model_comparison")
        
        # Should not have dedicated prompt comparison section
        # (but may mention prompt in other contexts)
        assert "Prompt Comparison" not in html or "prompt_comparison" not in html.lower()


class TestToolComparisonComposition:
    """Test tool comparison appears when tests use tools."""

    def test_tool_comparison_in_model_comparison(self):
        """Fixture 02 uses tools - should show tool comparison."""
        html, _ = generate_html("02_model_comparison")
        soup = parse_html(html)
        
        # Should have tool section
        tool_section = (
            soup.find(string=lambda s: s and "tool" in s.lower()) or
            soup.find(class_=lambda c: c and "tool" in c.lower() if c else False)
        )
        assert tool_section is not None, "Missing tool comparison section"


class TestMatrixModeComposition:
    """Test matrix mode has all expected sections."""

    def test_matrix_has_leaderboard(self):
        """Matrix mode should have model leaderboard."""
        html, _ = generate_html("04_matrix")
        assert "Model Leaderboard" in html or "leaderboard" in html.lower()

    def test_matrix_has_grid(self):
        """Matrix mode should have comparison matrix."""
        html, _ = generate_html("04_matrix")
        assert "Comparison Matrix" in html

    def test_matrix_full_has_all_sections(self):
        """Fixture 08 should have leaderboard and matrix sections."""
        html, data = generate_html("08_matrix_full")
        
        # Major sections (except AI Insights which are placeholder)
        assert "Model Leaderboard" in html or "leaderboard" in html.lower()
        assert "Comparison Matrix" in html
        # AI Insights won't render because fixture has placeholder
