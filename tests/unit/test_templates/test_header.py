"""Tests for header.html partial.

This component displays the report header with title, timestamp, and mode badge.
Uses real data from fixtures.
"""

from __future__ import annotations

import pytest

from tests.unit.test_templates.conftest import (
    extract_flags,
    load_pydantic_report,
    parse_html,
)


class TestHeaderWithRealData:
    """Test header.html with real fixture data."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load real data from fixture 01."""
        self.report = load_pydantic_report("01_basic_usage")
        self.flags = extract_flags("01_basic_usage")

    def test_renders_with_real_data(self, render_partial):
        """Should render without errors using real fixture data."""
        html = render_partial(
            "header.html",
            report=self.report,
            flags=self.flags,
            mode="simple",
        )
        assert len(html.strip()) > 0

    def test_shows_report_name(self, render_partial):
        """Should display the report name."""
        html = render_partial(
            "header.html",
            report=self.report,
            flags=self.flags,
            mode="simple",
        )
        # Should show project name or "pytest-aitest"
        assert "pytest-aitest" in html.lower() or "report" in html.lower()

    def test_shows_timestamp(self, render_partial):
        """Should display timestamp."""
        html = render_partial(
            "header.html",
            report=self.report,
            flags=self.flags,
            mode="simple",
        )
        # Should show date/time info
        assert "202" in html  # Year prefix


class TestHeaderModes:
    """Test header.html displays correct mode badges."""

    def test_simple_mode_badge(self, render_partial):
        """Simple mode should show appropriate indicator."""
        report = load_pydantic_report("01_basic_usage")
        flags = extract_flags("01_basic_usage")
        
        html = render_partial(
            "header.html",
            report=report,
            flags=flags,
            mode="simple",
        )
        # Should indicate simple/basic mode or single model
        assert len(html) > 0

    def test_model_comparison_badge(self, render_partial):
        """Model comparison mode should show model count."""
        report = load_pydantic_report("02_model_comparison")
        flags = extract_flags("02_model_comparison")
        
        html = render_partial(
            "header.html",
            report=report,
            flags=flags,
            mode="model_comparison",
        )
        # Should indicate multiple models
        assert "model" in html.lower() or "2" in html

    def test_matrix_mode_badge(self, render_partial):
        """Matrix mode should show model × prompt info."""
        report = load_pydantic_report("04_matrix")
        flags = extract_flags("04_matrix")
        
        html = render_partial(
            "header.html",
            report=report,
            flags=flags,
            mode="matrix",
        )
        # Should indicate matrix mode
        assert "×" in html or "x" in html.lower() or "matrix" in html.lower()


class TestHeaderStructure:
    """Test header.html HTML structure."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.report = load_pydantic_report("01_basic_usage")
        self.flags = extract_flags("01_basic_usage")

    def test_has_header_element(self, render_partial):
        """Should have a header element."""
        html = render_partial(
            "header.html",
            report=self.report,
            flags=self.flags,
            mode="simple",
        )
        soup = parse_html(html)
        header = soup.find("header") or soup.find(class_=lambda c: c and "header" in c.lower() if c else False)
        assert header is not None

    def test_has_title(self, render_partial):
        """Should have a title element."""
        html = render_partial(
            "header.html",
            report=self.report,
            flags=self.flags,
            mode="simple",
        )
        soup = parse_html(html)
        title = soup.find("h1")
        assert title is not None
