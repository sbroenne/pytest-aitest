"""Tests for ai_summary.html partial (now ai_insights).

This component displays AI-generated insights about test results.
It should:
- Render structured insights (recommendation, failures, optimizations)
- Not render when insights not provided (no pending state - AI is mandatory for reports)
- Show the "AI Insights" header when insights are present
"""

from __future__ import annotations

import pytest
from tests.unit.test_templates.conftest import parse_html


# Test insights object that mimics the Pydantic model
class MockRecommendation:
    configuration = "fast-agent"
    summary = "100% pass rate at lowest cost"
    reasoning = "Outperformed other configurations"


class MockInsights:
    recommendation = MockRecommendation()
    failures = []
    optimizations = []


class TestAIInsightsRendering:
    """Test ai_summary.html renders insights correctly."""

    def test_renders_when_insights_provided(self, render_partial):
        """Should render section when insights have real content."""
        html = render_partial("ai_summary.html", insights=MockInsights())
        assert "AI Insights" in html
        assert "fast-agent" in html

    def test_not_rendered_when_no_insights(self, render_partial):
        """Should not render when insights not provided (AI is mandatory for reports)."""
        html = render_partial("ai_summary.html")
        # When no insights provided, section doesn't render
        assert html.strip() == "" or "AI Insights" not in html

    def test_not_rendered_when_insights_none(self, render_partial):
        """Should not render when insights is explicitly None."""
        html = render_partial("ai_summary.html", insights=None)
        assert html.strip() == "" or "AI Insights" not in html


class TestAIInsightsStructure:
    """Test ai_summary.html has correct HTML structure."""

    def test_has_section_wrapper(self, render_partial):
        """Should have section.section wrapper."""
        html = render_partial("ai_summary.html", insights=MockInsights())
        soup = parse_html(html)
        section = soup.find("section", class_="section")
        assert section is not None, "Should have <section class='section'>"

    def test_has_header_with_title(self, render_partial):
        """Should have AI Insights header."""
        html = render_partial("ai_summary.html", insights=MockInsights())
        soup = parse_html(html)
        h2 = soup.find("h2")
        assert h2 is not None, "Should have <h2> header"
        assert "AI Insights" in h2.get_text()

    def test_shows_recommendation(self, render_partial):
        """Should display recommendation section."""
        html = render_partial("ai_summary.html", insights=MockInsights())
        assert "Recommendation" in html
        assert "fast-agent" in html


class TestAIInsightsWithFailures:
    """Test failure analysis rendering."""

    def test_shows_failure_count(self, render_partial):
        """Should show failure count when there are failures."""
        class MockFailure:
            configuration = "slow-agent"
            test_id = "test_foo"
            problem = "Timed out"
            root_cause = "Network issues"
            suggested_fix = "Add retry logic"
        
        class InsightsWithFailures:
            recommendation = MockRecommendation()
            failures = [MockFailure()]
            optimizations = []
        
        html = render_partial("ai_summary.html", insights=InsightsWithFailures())
        assert "Failure Analysis" in html
        assert "1" in html  # failure count


class TestAIInsightsWithOptimizations:
    """Test optimization rendering."""

    def test_shows_optimizations(self, render_partial):
        """Should show optimization opportunities."""
        class MockOpt:
            category = "cost"
            severity = "recommended"
            title = "Reduce model calls"
            current_state = "Making 5 calls per test"
            suggested_change = "Batch requests"
            expected_impact = "50% cost reduction"
        
        class InsightsWithOpts:
            recommendation = MockRecommendation()
            failures = []
            optimizations = [MockOpt()]
        
        html = render_partial("ai_summary.html", insights=InsightsWithOpts())
        assert "Optimization" in html
        assert "Reduce model calls" in html
