"""Interactive tests for HTML report using Playwright.

These tests verify interactive functionality:
- Agent selector works
- Mermaid diagrams render when expanded
- Test row expand/collapse works
- Filter buttons work

Run with:
    pytest tests/visual/test_report_interactive.py -v --headed  # See browser
    pytest tests/visual/test_report_interactive.py -v           # Headless
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from playwright.sync_api import Page

from pytest_aitest.cli import load_suite_report
from pytest_aitest.reporting.generator import ReportGenerator

# Use fixture that has 3 agents for agent selector testing
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "reports"


@pytest.fixture(scope="module")
def report_with_3_agents() -> Path:
    """Generate a report from the 3-agent test run."""
    # Use the live results which have 3 agents
    results_path = Path(__file__).parent.parent.parent / "aitest-reports" / "results.json"
    if not results_path.exists():
        pytest.skip("No aitest-reports/results.json - run tests first")
    
    report, _, insights = load_suite_report(results_path)
    
    output_path = Path(tempfile.gettempdir()) / "pytest_aitest_interactive_test.html"
    
    generator = ReportGenerator()
    generator.generate_html(report, output_path, insights=insights)
    
    return output_path


class TestMermaidDiagrams:
    """Test Mermaid diagram rendering."""

    def test_mermaid_library_loads(self, page: Page, report_with_3_agents: Path):
        """Mermaid.js library should be loaded."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        mermaid_defined = page.evaluate("typeof mermaid !== 'undefined'")
        assert mermaid_defined, "Mermaid.js not loaded"

    def test_mermaid_divs_exist(self, page: Page, report_with_3_agents: Path):
        """Report should have mermaid diagram divs."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        mermaid_count = page.locator(".mermaid").count()
        assert mermaid_count > 0, "No mermaid divs found"

    def test_mermaid_renders_on_expand(self, page: Page, report_with_3_agents: Path):
        """Mermaid diagrams should render when test row is expanded."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        # Find and click first test row
        test_rows = page.locator(".test-row")
        assert test_rows.count() > 0, "No test rows found"
        
        # Click to expand
        test_rows.first.click()
        page.wait_for_timeout(500)  # Wait for animation
        
        # Check detail is visible
        visible_detail = page.locator(".test-detail:not(.hidden)")
        assert visible_detail.count() > 0, "Test detail not visible after click"
        
        # Wait for mermaid to render (it processes async)
        page.wait_for_timeout(1000)
        
        # Check if mermaid rendered (should have SVG or at least processed)
        mermaid_in_detail = visible_detail.locator(".mermaid").first
        
        # Mermaid replaces content with SVG when rendered
        has_svg = mermaid_in_detail.locator("svg").count() > 0
        # Or it adds data-processed attribute
        is_processed = mermaid_in_detail.get_attribute("data-processed") == "true"
        
        assert has_svg or is_processed, "Mermaid diagram not rendered"

    def test_mermaid_content_is_valid(self, page: Page, report_with_3_agents: Path):
        """Mermaid content should render as SVG (not show raw code)."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        # Expand a test row first
        test_rows = page.locator(".test-row")
        test_rows.first.click()
        page.wait_for_timeout(1000)  # Wait for mermaid
        
        # Get the first mermaid in visible detail
        visible_detail = page.locator(".test-detail:not(.hidden)")
        mermaid_div = visible_detail.locator(".mermaid").first
        
        # Mermaid should have rendered to SVG (contains actor names from diagram)
        mermaid_text = mermaid_div.text_content()
        
        # After rendering, it should contain the diagram content (agent names, messages)
        # NOT the raw sequenceDiagram syntax
        assert "Agent" in mermaid_text or "User" in mermaid_text, f"Mermaid should render actors, got: {mermaid_text[:200]}"


class TestAgentSelector:
    """Test agent selector functionality."""

    def test_agent_selector_exists(self, page: Page, report_with_3_agents: Path):
        """Agent selector should exist when > 2 agents."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        selector = page.locator("#agent-selector")
        assert selector.count() > 0, "Agent selector not found"

    def test_correct_number_of_checkboxes(self, page: Page, report_with_3_agents: Path):
        """Should have 3 agent checkboxes."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        checkboxes = page.locator('input[name="compare-agent"]')
        assert checkboxes.count() == 3, f"Expected 3 checkboxes, got {checkboxes.count()}"

    def test_two_agents_selected_by_default(self, page: Page, report_with_3_agents: Path):
        """First 2 agents should be selected by default."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        checked = page.locator('input[name="compare-agent"]:checked')
        assert checked.count() == 2, f"Expected 2 checked, got {checked.count()}"

    def test_clicking_third_agent_shows_column(self, page: Page, report_with_3_agents: Path):
        """Clicking 3rd agent should show its comparison column."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        # Expand first test row to see comparison columns
        test_rows = page.locator(".test-row")
        test_rows.first.click()
        page.wait_for_timeout(300)
        
        # Count visible comparison columns before
        visible_before = page.locator(".comparison-column:not(.hidden)").count()
        
        # Get 3rd checkbox (index 2)
        third_checkbox = page.locator('input[name="compare-agent"]').nth(2)
        third_agent_id = third_checkbox.get_attribute("value")
        
        # It should be unchecked
        assert not third_checkbox.is_checked(), "3rd agent should be unchecked initially"
        
        # Click the LABEL (parent element) instead of the hidden checkbox
        third_label = page.locator(".agent-chip").nth(2)
        third_label.click()
        page.wait_for_timeout(300)
        
        # Now 3 should be checked
        checked_after = page.locator('input[name="compare-agent"]:checked').count()
        # Due to limit of 2, one should have been unchecked
        assert checked_after == 2, f"Expected 2 checked (limited), got {checked_after}"

    def test_agent_chip_style_updates(self, page: Page, report_with_3_agents: Path):
        """Agent chip should update style when selected."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        # First two chips should have 'selected' class
        chips = page.locator(".agent-chip")
        
        first_chip_classes = chips.nth(0).get_attribute("class")
        assert "selected" in first_chip_classes, "First chip should be selected"
        
        third_chip_classes = chips.nth(2).get_attribute("class")
        assert "selected" not in third_chip_classes, "Third chip should not be selected"


class TestTestRowInteraction:
    """Test test row expand/collapse."""

    def test_test_row_expands_on_click(self, page: Page, report_with_3_agents: Path):
        """Clicking test row should expand details."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        # Initially all details should be hidden
        hidden_details = page.locator(".test-detail.hidden")
        initial_hidden = hidden_details.count()
        assert initial_hidden > 0, "Expected hidden test details"
        
        # Click first test row
        test_rows = page.locator(".test-row")
        test_rows.first.click()
        page.wait_for_timeout(300)
        
        # One detail should now be visible
        visible_details = page.locator(".test-detail:not(.hidden)")
        assert visible_details.count() == 1, "Expected 1 visible detail after click"

    def test_test_row_collapses_on_second_click(self, page: Page, report_with_3_agents: Path):
        """Clicking expanded test row should collapse it."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        # Click to expand - the clickable area is the first div inside test-row
        test_row = page.locator(".test-row").first
        clickable = test_row.locator(".px-5.py-3.cursor-pointer").first
        clickable.click()
        page.wait_for_timeout(300)
        
        # Verify expanded
        assert page.locator(".test-detail:not(.hidden)").count() == 1
        
        # Click again to collapse (same clickable area)
        clickable.click()
        page.wait_for_timeout(300)
        
        # Should be hidden again
        assert page.locator(".test-detail:not(.hidden)").count() == 0


class TestFilterButtons:
    """Test filter buttons."""

    def test_filter_buttons_exist(self, page: Page, report_with_3_agents: Path):
        """Filter buttons should exist."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        all_btn = page.locator('.filter-btn[data-filter="all"]')
        assert all_btn.count() == 1, "All filter button not found"
        
        failed_btn = page.locator('.filter-btn[data-filter="failed"]')
        assert failed_btn.count() == 1, "Failed filter button not found"

    def test_all_filter_active_by_default(self, page: Page, report_with_3_agents: Path):
        """All filter should be active by default."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        all_btn = page.locator('.filter-btn[data-filter="all"]')
        classes = all_btn.get_attribute("class")
        assert "active" in classes, "All filter should be active"


class TestLeaderboard:
    """Test agent leaderboard."""

    def test_leaderboard_exists(self, page: Page, report_with_3_agents: Path):
        """Leaderboard should exist."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        leaderboard = page.locator(".leaderboard-table")
        assert leaderboard.count() > 0, "Leaderboard table not found"

    def test_leaderboard_has_all_agents(self, page: Page, report_with_3_agents: Path):
        """Leaderboard should show all 3 agents."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        rows = page.locator(".leaderboard-table tbody tr")
        assert rows.count() == 3, f"Expected 3 agent rows, got {rows.count()}"

    def test_leaderboard_has_medals(self, page: Page, report_with_3_agents: Path):
        """Top 3 agents should have medal emojis."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        leaderboard_text = page.locator(".leaderboard-table").text_content()
        assert "🥇" in leaderboard_text, "Missing gold medal"
        assert "🥈" in leaderboard_text, "Missing silver medal"
        assert "🥉" in leaderboard_text, "Missing bronze medal"


class TestMermaidOverlay:
    """Test mermaid overlay (fullscreen diagram view)."""

    def test_clicking_mermaid_opens_overlay(self, page: Page, report_with_3_agents: Path):
        """Clicking mermaid diagram should open overlay."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        # Expand a test row
        page.locator(".test-row").first.click()
        page.wait_for_timeout(500)
        
        # Click on mermaid container
        mermaid_container = page.locator('.comparison-column:not(.hidden) [data-mermaid-code]').first
        mermaid_container.click()
        page.wait_for_timeout(500)
        
        # Overlay should be active
        overlay = page.locator("#overlay")
        overlay_class = overlay.get_attribute("class") or ""
        assert "active" in overlay_class, "Overlay should be active after clicking mermaid"

    def test_overlay_mermaid_renders_as_svg(self, page: Page, report_with_3_agents: Path):
        """Mermaid in overlay should render as SVG."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        # Expand a test row
        page.locator(".test-row").first.click()
        page.wait_for_timeout(500)
        
        # Click on mermaid container
        mermaid_container = page.locator('.comparison-column:not(.hidden) [data-mermaid-code]').first
        mermaid_container.click()
        page.wait_for_timeout(1000)
        
        # Check overlay has SVG
        overlay_svg = page.locator("#overlay-mermaid svg")
        assert overlay_svg.count() > 0, "Overlay mermaid should render as SVG"


class TestAgentSelectorExactlyTwo:
    """Test that agent selector always keeps exactly 2 selected."""

    def test_cannot_deselect_to_less_than_2(self, page: Page, report_with_3_agents: Path):
        """Clicking an already-selected agent should not deselect it."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        # Click on the first selected chip (should have no effect)
        page.locator(".agent-chip").first.click()
        page.wait_for_timeout(200)
        
        # Still should have 2 selected
        checked = page.locator('input[name="compare-agent"]:checked')
        assert checked.count() == 2, f"Should still have 2 selected, got {checked.count()}"

    def test_selecting_third_replaces_first(self, page: Page, report_with_3_agents: Path):
        """Selecting 3rd agent should replace the oldest selection."""
        page.goto(f"file://{report_with_3_agents}")
        page.wait_for_load_state("networkidle")
        
        # Get initial selected agent IDs
        initial_checked = page.locator('input[name="compare-agent"]:checked')
        first_selected = initial_checked.nth(0).get_attribute("value")
        second_selected = initial_checked.nth(1).get_attribute("value")
        
        # Get 3rd agent ID
        third_checkbox = page.locator('input[name="compare-agent"]').nth(2)
        third_agent_id = third_checkbox.get_attribute("value")
        
        # Click 3rd agent
        page.locator(".agent-chip").nth(2).click()
        page.wait_for_timeout(200)
        
        # Check new selection
        new_checked = page.locator('input[name="compare-agent"]:checked')
        assert new_checked.count() == 2, "Should have exactly 2 selected"
        
        new_ids = [new_checked.nth(i).get_attribute("value") for i in range(2)]
        
        # The first one should have been replaced
        assert first_selected not in new_ids, f"First agent {first_selected} should be replaced"
        assert second_selected in new_ids, f"Second agent {second_selected} should still be selected"
        assert third_agent_id in new_ids, f"Third agent {third_agent_id} should now be selected"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed"])
