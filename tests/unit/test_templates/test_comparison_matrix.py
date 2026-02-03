"""Tests for comparison_matrix.html partial.

This component displays a grid comparing tests across models or prompts.
It should:
- Show correct header based on mode (model/prompt/matrix)
- Display columns for each comparison dimension
- Show pass/fail status, duration, and tokens per cell
- Be hidden when flags.show_comparison_grid is False
"""

from __future__ import annotations

from tests.unit.test_templates.conftest import (
    make_comparison_grid,
    make_flags,
    parse_html,
)


class TestComparisonMatrixHeaders:
    """Test comparison_matrix.html shows correct header per mode."""

    def test_model_comparison_header(self, render_partial):
        """Model comparison mode should show 'Test Results by Model'."""
        grid = make_comparison_grid(mode="model_comparison")
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        assert "Test Results by Model" in html

    def test_prompt_comparison_header(self, render_partial):
        """Prompt comparison mode should show 'Test Results by System Prompt'."""
        grid = make_comparison_grid(mode="prompt_comparison", columns=["brief", "detailed"])
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        assert "Test Results by System Prompt" in html

    def test_matrix_header(self, render_partial):
        """Matrix mode should show 'Comparison Matrix'."""
        grid = make_comparison_grid(mode="matrix")
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        assert "Comparison Matrix" in html


class TestComparisonMatrixHidden:
    """Test comparison_matrix.html is hidden when appropriate."""

    def test_hidden_when_flag_false(self, render_partial):
        """Should not render when show_comparison_grid is False."""
        grid = make_comparison_grid()
        flags = make_flags(show_comparison_grid=False)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        assert html.strip() == ""

    def test_hidden_when_no_grid(self, render_partial):
        """Should not render when comparison_grid is None."""
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=None, flags=flags)
        assert html.strip() == ""


class TestComparisonMatrixColumns:
    """Test comparison_matrix.html displays correct columns."""

    def test_has_model_columns(self, render_partial):
        """Should have column headers for each model."""
        grid = make_comparison_grid(
            mode="model_comparison",
            columns=["gpt-5-mini", "gpt-4.1"],
        )
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        soup = parse_html(html)
        
        headers = [th.get_text().strip() for th in soup.find_all("th")]
        assert "gpt-5-mini" in headers
        assert "gpt-4.1" in headers

    def test_has_prompt_columns(self, render_partial):
        """Should have column headers for each prompt."""
        grid = make_comparison_grid(
            mode="prompt_comparison",
            columns=["brief", "detailed", "structured"],
        )
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        soup = parse_html(html)
        
        headers = [th.get_text().strip() for th in soup.find_all("th")]
        assert "brief" in headers
        assert "detailed" in headers
        assert "structured" in headers


class TestComparisonMatrixRows:
    """Test comparison_matrix.html displays correct row content."""

    def test_has_test_name_in_row(self, render_partial):
        """Should show test name in each row."""
        grid = make_comparison_grid(
            rows=[
                {
                    "name": "test_weather_forecast",
                    "cells": [
                        {"test": {"outcome": "passed"}, "outcome": "passed", "duration": 1.2, "tokens": 100},
                    ],
                },
            ],
        )
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        assert "test_weather_forecast" in html

    def test_shows_pass_status(self, render_partial):
        """Should show checkmark for passed tests."""
        grid = make_comparison_grid(
            rows=[
                {
                    "name": "test_pass",
                    "cells": [
                        {"test": {"outcome": "passed"}, "outcome": "passed", "duration": 1.0, "tokens": 50},
                    ],
                },
            ],
        )
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        assert "✅" in html or "pass" in html.lower()

    def test_shows_fail_status(self, render_partial):
        """Should show X for failed tests."""
        grid = make_comparison_grid(
            rows=[
                {
                    "name": "test_fail",
                    "cells": [
                        {"test": {"outcome": "failed"}, "outcome": "failed", "duration": 1.0, "tokens": 50},
                    ],
                },
            ],
        )
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        assert "❌" in html or "fail" in html.lower()


class TestComparisonMatrixCellContent:
    """Test comparison_matrix.html cell content details."""

    def test_shows_duration(self, render_partial):
        """Should show duration in cells."""
        grid = make_comparison_grid(
            rows=[
                {
                    "name": "test_timing",
                    "cells": [
                        # Duration is in milliseconds, template divides by 1000
                        {"test": {"outcome": "passed"}, "outcome": "passed", "duration": 2500, "tokens": 100},
                    ],
                },
            ],
        )
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        # Duration should appear as seconds (2500ms -> 2.5s)
        assert "2.5" in html

    def test_shows_tokens(self, render_partial):
        """Should show token count in cells."""
        grid = make_comparison_grid(
            rows=[
                {
                    "name": "test_tokens",
                    "cells": [
                        {"test": {"outcome": "passed"}, "outcome": "passed", "duration": 1.0, "tokens": 1234},
                    ],
                },
            ],
        )
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        # Tokens should appear (maybe formatted as "1,234" or "1234")
        assert "1234" in html or "1,234" in html


class TestComparisonMatrixStructure:
    """Test comparison_matrix.html HTML structure."""

    def test_has_table_element(self, render_partial):
        """Should render as a table."""
        grid = make_comparison_grid()
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        soup = parse_html(html)
        
        table = soup.find("table", class_="matrix")
        assert table is not None, "Missing <table class='matrix'>"

    def test_has_section_wrapper(self, render_partial):
        """Should have section wrapper."""
        grid = make_comparison_grid()
        flags = make_flags(show_comparison_grid=True)
        
        html = render_partial("comparison_matrix.html", comparison_grid=grid, flags=flags)
        soup = parse_html(html)
        
        section = soup.find("section", class_="section")
        assert section is not None, "Missing <section class='section'>"
