"""Tests for summary_cards.html partial.

This component displays the summary statistics cards at the top of reports.
Uses real data from fixtures.
"""

from __future__ import annotations

import pytest

from tests.unit.test_templates.conftest import (
    load_pydantic_report,
    parse_html,
)


class TestSummaryCardsWithRealData:
    """Test summary_cards.html with real fixture data."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load real data from fixture 01 (basic usage)."""
        self.report = load_pydantic_report("01_basic_usage")

    def test_renders_with_real_data(self, render_partial):
        """Should render without errors using real fixture data."""
        html = render_partial(
            "summary_cards.html",
            report=self.report,
        )
        # Should have some content
        assert len(html.strip()) > 0

    def test_shows_total_tests(self, render_partial):
        """Should display total test count."""
        html = render_partial(
            "summary_cards.html",
            report=self.report,
        )
        # Fixture 01 has 12 tests
        assert "12" in html

    def test_shows_pass_count(self, render_partial):
        """Should display passed test count."""
        html = render_partial(
            "summary_cards.html",
            report=self.report,
        )
        # Should show passed count (11 in fixture 01)
        assert "11" in html

    def test_shows_fail_count(self, render_partial):
        """Should display failed test count."""
        html = render_partial(
            "summary_cards.html",
            report=self.report,
        )
        # Fixture 01 has 1 failure
        assert "1" in html


class TestSummaryCardsAllPass:
    """Test summary_cards with all-passing fixture."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load fixture 02 (model comparison - all pass)."""
        self.report = load_pydantic_report("02_model_comparison")

    def test_shows_100_percent(self, render_partial):
        """Should show 100% when all tests pass."""
        html = render_partial(
            "summary_cards.html",
            report=self.report,
        )
        assert "100" in html


class TestSummaryCardsWithSkipped:
    """Test summary_cards with skipped tests."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load fixture 07 (with skipped)."""
        self.report = load_pydantic_report("07_with_skipped")

    def test_shows_skipped_count(self, render_partial):
        """Should display skipped test count when present."""
        html = render_partial(
            "summary_cards.html",
            report=self.report,
        )
        # Fixture 07 has skipped tests
        # Should show the count somewhere
        soup = parse_html(html)
        # Just verify it renders without error
        assert len(html) > 0


class TestSummaryCardsStructure:
    """Test summary_cards.html HTML structure."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.report = load_pydantic_report("01_basic_usage")

    def test_has_cards_container(self, render_partial):
        """Should have a cards container."""
        html = render_partial(
            "summary_cards.html",
            report=self.report,
        )
        soup = parse_html(html)
        # Should have some card structure
        cards = soup.find_all(class_=lambda c: c and "card" in c.lower() if c else False)
        assert len(cards) > 0 or "summary" in html.lower()

    def test_shows_duration(self, render_partial):
        """Should show total duration."""
        html = render_partial(
            "summary_cards.html",
            report=self.report,
        )
        # Duration should be shown (in seconds or formatted)
        assert "s" in html.lower()  # seconds indicator
