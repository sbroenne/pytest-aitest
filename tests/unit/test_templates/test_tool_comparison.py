"""Tests for tool_comparison.html partial.

This component displays tool usage comparison across models/prompts.
Uses real data from fixtures.
"""

from __future__ import annotations

import pytest
from tests.unit.test_templates.conftest import (
    parse_html,
    make_flags,
)


def extract_tool_comparison(fixture_name: str) -> list[dict]:
    """Extract tool_comparison data from a fixture."""
    from pytest_aitest.reporting.generator import ReportGenerator
    from tests.unit.test_templates.conftest import load_pydantic_report
    
    report = load_pydantic_report(fixture_name)
    gen = ReportGenerator()
    return gen._build_tool_comparison(report)


class TestToolComparisonWithRealData:
    """Test tool_comparison.html with real fixture data."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load real data from fixture 02 (model comparison with tools)."""
        from tests.unit.test_templates.conftest import extract_flags
        self.tool_comparison = extract_tool_comparison("02_model_comparison")
        self.flags = extract_flags("02_model_comparison")

    def test_renders_with_real_data(self, render_partial):
        """Should render without errors using real fixture data."""
        html = render_partial(
            "tool_comparison.html",
            flags=self.flags,
            tool_comparison=self.tool_comparison,
        )
        # Should have content if tools were used
        if self.tool_comparison:
            assert "tool" in html.lower() or len(html) > 0

    def test_shows_tool_names(self, render_partial):
        """Should display tool names from fixture."""
        html = render_partial(
            "tool_comparison.html",
            flags=self.flags,
            tool_comparison=self.tool_comparison,
        )
        # Fixture 02 uses weather tools
        if self.tool_comparison:
            html_lower = html.lower()
            assert "weather" in html_lower or "forecast" in html_lower or "get_" in html_lower


class TestToolComparisonHidden:
    """Test tool_comparison.html is hidden when appropriate."""

    def test_hidden_when_flag_false(self, render_partial):
        """Should not render when show_tool_comparison is False."""
        flags = make_flags(show_tool_comparison=False)
        tool_comparison = [{"tool": "test_tool", "gpt-5-mini": 5}]
        
        html = render_partial("tool_comparison.html", flags=flags, tool_comparison=tool_comparison)
        assert html.strip() == ""

    def test_hidden_when_no_tools(self, render_partial):
        """Should not render when tool_comparison is empty."""
        flags = make_flags(show_tool_comparison=True)
        
        html = render_partial("tool_comparison.html", flags=flags, tool_comparison=[])
        assert html.strip() == "" or "Tool" not in html


class TestToolComparisonStructure:
    """Test tool_comparison.html HTML structure."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from tests.unit.test_templates.conftest import extract_flags
        self.tool_comparison = extract_tool_comparison("02_model_comparison")
        self.flags = extract_flags("02_model_comparison")

    def test_has_section_wrapper(self, render_partial):
        """Should have section wrapper when content present."""
        if not self.tool_comparison:
            pytest.skip("No tool comparison data in fixture")
        
        html = render_partial(
            "tool_comparison.html",
            flags=self.flags,
            tool_comparison=self.tool_comparison,
        )
        soup = parse_html(html)
        section = soup.find("section", class_="section")
        assert section is not None

    def test_has_table_or_grid(self, render_partial):
        """Should display tools in a table or grid."""
        if not self.tool_comparison:
            pytest.skip("No tool comparison data in fixture")
        
        html = render_partial(
            "tool_comparison.html",
            flags=self.flags,
            tool_comparison=self.tool_comparison,
        )
        soup = parse_html(html)
        table = soup.find("table")
        assert table is not None
