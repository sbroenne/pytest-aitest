"""Tests for prompt_comparison.html partial.

This component displays a comparison table of prompts.
Uses real data from fixtures/reports/03_prompt_comparison.json
"""

from __future__ import annotations

import pytest

from tests.unit.test_templates.conftest import (
    extract_flags,
    extract_prompt_groups,
    make_flags,
    parse_html,
)


class TestPromptComparisonWithRealData:
    """Test prompt_comparison.html with real fixture data."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load real data from fixture 03 (prompt comparison)."""
        self.prompt_groups = extract_prompt_groups("03_prompt_comparison")
        self.flags = extract_flags("03_prompt_comparison")

    def test_renders_with_real_data(self, render_partial):
        """Should render without errors using real fixture data."""
        html = render_partial(
            "prompt_comparison.html",
            flags=self.flags,
            prompt_groups=self.prompt_groups,
        )
        assert "Prompt" in html

    def test_shows_real_prompt_names(self, render_partial):
        """Should display actual prompt names from fixture."""
        html = render_partial(
            "prompt_comparison.html",
            flags=self.flags,
            prompt_groups=self.prompt_groups,
        )
        # Fixture 03 has brief, detailed, structured prompts
        html_lower = html.lower()
        assert "brief" in html_lower
        assert "detailed" in html_lower
        assert "structured" in html_lower

    def test_shows_statistics(self, render_partial):
        """Should display statistics for each prompt."""
        html = render_partial(
            "prompt_comparison.html",
            flags=self.flags,
            prompt_groups=self.prompt_groups,
        )
        # Should show pass rates
        assert "%" in html or "100" in html


class TestPromptComparisonHidden:
    """Test prompt_comparison.html is hidden when appropriate."""

    def test_hidden_when_flag_false(self, render_partial):
        """Should not render when show_prompt_comparison is False."""
        flags = make_flags(show_prompt_comparison=False)
        prompt_groups = [{"dimension_value": "test", "passed": 1, "total": 1, "pass_rate": 100}]
        
        html = render_partial("prompt_comparison.html", flags=flags, prompt_groups=prompt_groups)
        assert html.strip() == ""

    def test_hidden_when_no_groups(self, render_partial):
        """Should not render when prompt_groups is empty."""
        flags = make_flags(show_prompt_comparison=True)
        
        html = render_partial("prompt_comparison.html", flags=flags, prompt_groups=[])
        # Empty groups should result in no content
        assert "Prompt Comparison" not in html


class TestPromptComparisonStructure:
    """Test prompt_comparison.html HTML structure."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.prompt_groups = extract_prompt_groups("03_prompt_comparison")
        self.flags = extract_flags("03_prompt_comparison")

    def test_has_section_wrapper(self, render_partial):
        """Should have section wrapper."""
        html = render_partial(
            "prompt_comparison.html",
            flags=self.flags,
            prompt_groups=self.prompt_groups,
        )
        soup = parse_html(html)
        section = soup.find("section", class_="section")
        assert section is not None

    def test_has_table_structure(self, render_partial):
        """Should render prompts in a table or list."""
        html = render_partial(
            "prompt_comparison.html",
            flags=self.flags,
            prompt_groups=self.prompt_groups,
        )
        soup = parse_html(html)
        # Should have some structured display
        table = soup.find("table") or soup.find("div", class_=lambda c: c and "card" in c.lower() if c else False)
        assert table is not None or len(self.prompt_groups) == 0
