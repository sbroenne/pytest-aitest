"""Tests for ai_summary.html partial.

This component displays LLM-generated analysis of test results.
It should:
- Render markdown content as HTML
- Be hidden when ai_summary is None or empty
- Show the "AI Analysis" header
"""

from __future__ import annotations

import pytest
from tests.unit.test_templates.conftest import parse_html


class TestAISummaryRendering:
    """Test ai_summary.html renders content correctly."""

    def test_renders_when_ai_summary_provided(self, render_partial):
        """Should render section when ai_summary has content."""
        html = render_partial("ai_summary.html", ai_summary="Test summary content")
        assert "AI Analysis" in html
        assert "Test summary content" in html

    def test_renders_markdown_bold(self, render_partial):
        """Should convert **bold** to <strong>."""
        html = render_partial("ai_summary.html", ai_summary="This is **bold** text")
        soup = parse_html(html)
        strong = soup.find("strong")
        assert strong is not None, "Markdown **bold** not rendered as <strong>"
        assert strong.get_text() == "bold"

    def test_renders_markdown_italic(self, render_partial):
        """Should convert *italic* to <em>."""
        html = render_partial("ai_summary.html", ai_summary="This is *italic* text")
        soup = parse_html(html)
        em = soup.find("em")
        assert em is not None, "Markdown *italic* not rendered as <em>"
        assert em.get_text() == "italic"

    def test_renders_markdown_headings(self, render_partial):
        """Should convert ### Heading to <h3>."""
        html = render_partial("ai_summary.html", ai_summary="### Verdict\nSome analysis")
        soup = parse_html(html)
        h3 = soup.find("h3")
        assert h3 is not None, "Markdown ### not rendered as <h3>"
        assert "Verdict" in h3.get_text()

    def test_renders_markdown_lists(self, render_partial):
        """Should convert markdown lists to <ul>/<li>."""
        html = render_partial("ai_summary.html", ai_summary="- Item 1\n- Item 2")
        soup = parse_html(html)
        ul = soup.find("ul")
        assert ul is not None, "Markdown list not rendered as <ul>"
        items = ul.find_all("li")
        assert len(items) == 2, f"Expected 2 list items, got {len(items)}"


class TestAISummaryHidden:
    """Test ai_summary.html is hidden when appropriate."""

    def test_hidden_when_none(self, render_partial):
        """Should render nothing when ai_summary is None."""
        html = render_partial("ai_summary.html", ai_summary=None)
        assert html.strip() == "", f"Expected empty output, got: {html[:100]}"

    def test_hidden_when_not_provided(self, render_partial):
        """Should render nothing when ai_summary not in context."""
        html = render_partial("ai_summary.html")
        assert html.strip() == "", f"Expected empty output, got: {html[:100]}"

    def test_hidden_when_empty_string(self, render_partial):
        """Should render nothing when ai_summary is empty string."""
        html = render_partial("ai_summary.html", ai_summary="")
        # Empty string is falsy, so should not render
        assert "AI Analysis" not in html


class TestAISummaryStructure:
    """Test ai_summary.html HTML structure."""

    def test_has_section_wrapper(self, render_partial):
        """Should have section element with correct class."""
        html = render_partial("ai_summary.html", ai_summary="Content")
        soup = parse_html(html)
        section = soup.find("section", class_="section")
        assert section is not None, "Missing <section class='section'> wrapper"

    def test_has_header_with_emoji(self, render_partial):
        """Should have header with robot emoji."""
        html = render_partial("ai_summary.html", ai_summary="Content")
        assert "🤖" in html, "Missing robot emoji in header"

    def test_content_in_ai_summary_class(self, render_partial):
        """Should wrap content in ai-summary class for styling."""
        html = render_partial("ai_summary.html", ai_summary="Test content")
        soup = parse_html(html)
        content_div = soup.find(class_="ai-summary")
        assert content_div is not None, "Missing .ai-summary wrapper for content"


class TestAISummaryRealContent:
    """Test with realistic AI summary content."""

    SAMPLE_SUMMARY = """### Verdict
**Recommended: gpt-5-mini** — both models achieved 100% accuracy.
*Confidence: High*

### Model Performance
- **gpt-4.1**: 100% (5/5), 3,000 tokens, $0.02
- **gpt-5-mini**: 100% (5/5), 5,000 tokens, $0.01

### Key Differences
No functional differences observed in this test suite.
"""

    def test_renders_realistic_summary(self, render_partial):
        """Should render realistic AI summary without errors."""
        html = render_partial("ai_summary.html", ai_summary=self.SAMPLE_SUMMARY)
        soup = parse_html(html)
        
        # Check structure rendered
        assert soup.find("h3"), "Headings not rendered"
        assert soup.find("strong"), "Bold text not rendered"
        assert soup.find("em"), "Italic text not rendered"
        assert soup.find("ul"), "Lists not rendered"

    def test_preserves_model_names(self, render_partial):
        """Should preserve model names in content."""
        html = render_partial("ai_summary.html", ai_summary=self.SAMPLE_SUMMARY)
        assert "gpt-4.1" in html
        assert "gpt-5-mini" in html

    def test_preserves_statistics(self, render_partial):
        """Should preserve statistics in content."""
        html = render_partial("ai_summary.html", ai_summary=self.SAMPLE_SUMMARY)
        assert "100%" in html
        assert "$0.02" in html or "0.02" in html
