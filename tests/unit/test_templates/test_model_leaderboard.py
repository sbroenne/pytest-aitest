"""Tests for model_leaderboard.html partial.

This component displays a ranked leaderboard of models.
It should:
- Show models ranked by pass rate
- Display medals (🥇, 🥈, 🥉) for top 3
- Show pass rate, tokens, cost for each model
- Be hidden when flags.show_model_leaderboard is False

Uses real data from fixtures/reports/02_model_comparison.json
"""

from __future__ import annotations

import pytest

from tests.unit.test_templates.conftest import (
    extract_flags,
    extract_model_groups,
    make_flags,
    make_model_ranking,
    parse_html,
)


class TestModelLeaderboardWithRealData:
    """Test model_leaderboard.html with real fixture data."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load real data from fixture 02 (model comparison)."""
        self.model_groups = extract_model_groups("02_model_comparison")
        self.flags = extract_flags("02_model_comparison")

    def test_renders_with_real_data(self, render_partial):
        """Should render without errors using real fixture data."""
        html = render_partial(
            "model_leaderboard.html",
            flags=self.flags,
            model_groups=self.model_groups,
        )
        assert "Model Leaderboard" in html

    def test_shows_real_model_names(self, render_partial):
        """Should display actual model names from fixture."""
        html = render_partial(
            "model_leaderboard.html",
            flags=self.flags,
            model_groups=self.model_groups,
        )
        # Fixture 02 has gpt-4.1 and gpt-5-mini
        assert "gpt-4.1" in html
        assert "gpt-5-mini" in html

    def test_shows_real_statistics(self, render_partial):
        """Should display actual statistics from fixture."""
        html = render_partial(
            "model_leaderboard.html",
            flags=self.flags,
            model_groups=self.model_groups,
        )
        # Both models have 100% pass rate in fixture 02
        assert "100" in html

    def test_shows_medals(self, render_partial):
        """Should display medals for ranked models."""
        html = render_partial(
            "model_leaderboard.html",
            flags=self.flags,
            model_groups=self.model_groups,
        )
        # Should have gold and silver medals
        assert "🥇" in html
        assert "🥈" in html


class TestModelLeaderboardRendering:
    """Test model_leaderboard.html basic rendering."""

    def test_renders_when_flag_true(self, render_partial):
        """Should render section when show_model_leaderboard is True."""
        flags = make_flags(show_model_leaderboard=True)
        model_groups = [
            make_model_ranking("gpt-5-mini", rank=1),
            make_model_ranking("gpt-4.1", rank=2),
        ]
        
        html = render_partial("model_leaderboard.html", flags=flags, model_groups=model_groups)
        assert "Model Leaderboard" in html


class TestModelLeaderboardHidden:
    """Test model_leaderboard.html is hidden when appropriate."""

    def test_hidden_when_flag_false(self, render_partial):
        """Should not render when show_model_leaderboard is False."""
        flags = make_flags(show_model_leaderboard=False)
        model_groups = [make_model_ranking("gpt-5-mini")]
        
        html = render_partial("model_leaderboard.html", flags=flags, model_groups=model_groups)
        assert html.strip() == ""

    def test_hidden_when_no_groups(self, render_partial):
        """Should not render when model_groups is empty."""
        flags = make_flags(show_model_leaderboard=True)
        
        html = render_partial("model_leaderboard.html", flags=flags, model_groups=[])
        assert "Model Leaderboard" not in html


class TestModelLeaderboardMedals:
    """Test model_leaderboard.html displays correct medals."""

    def test_gold_medal_for_first(self, render_partial):
        """First place should have gold medal."""
        flags = make_flags(show_model_leaderboard=True)
        model_groups = [
            make_model_ranking("winner", rank=1),
            make_model_ranking("runner-up", rank=2),
        ]
        
        html = render_partial("model_leaderboard.html", flags=flags, model_groups=model_groups)
        assert "🥇" in html

    def test_silver_medal_for_second(self, render_partial):
        """Second place should have silver medal."""
        flags = make_flags(show_model_leaderboard=True)
        model_groups = [
            make_model_ranking("winner", rank=1),
            make_model_ranking("runner-up", rank=2),
        ]
        
        html = render_partial("model_leaderboard.html", flags=flags, model_groups=model_groups)
        assert "🥈" in html

    def test_bronze_medal_for_third(self, render_partial):
        """Third place should have bronze medal."""
        flags = make_flags(show_model_leaderboard=True)
        model_groups = [
            make_model_ranking("first", rank=1),
            make_model_ranking("second", rank=2),
            make_model_ranking("third", rank=3),
        ]
        
        html = render_partial("model_leaderboard.html", flags=flags, model_groups=model_groups)
        assert "🥉" in html


class TestModelLeaderboardStructure:
    """Test model_leaderboard.html HTML structure."""

    def test_has_section_wrapper(self, render_partial):
        """Should have section wrapper."""
        flags = make_flags(show_model_leaderboard=True)
        model_groups = [make_model_ranking("model")]
        
        html = render_partial("model_leaderboard.html", flags=flags, model_groups=model_groups)
        soup = parse_html(html)
        
        section = soup.find("section", class_="section")
        assert section is not None

    def test_has_trophy_emoji(self, render_partial):
        """Should have trophy emoji in header."""
        flags = make_flags(show_model_leaderboard=True)
        model_groups = [make_model_ranking("model")]
        
        html = render_partial("model_leaderboard.html", flags=flags, model_groups=model_groups)
        assert "🏆" in html
