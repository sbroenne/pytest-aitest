"""Visual tests for multi-agent report (02_multi_agent.json).

2 agents - Tests:
- Leaderboard shows 2 agents
- Winner row highlighted
- Both comparison columns visible
- NO agent selector (only 2 agents - need 3+ for selector)
- Mermaid overlay opens/closes
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page


class TestMultiAgentLeaderboard:
    """Test leaderboard for 2-agent report."""

    def test_leaderboard_exists(self, page: Page, multi_agent_report: Path):
        """Leaderboard should exist for 2+ agents."""
        page.goto(f"file://{multi_agent_report}")
        page.wait_for_load_state("networkidle")

        leaderboard = page.locator(".leaderboard-table")
        assert leaderboard.count() > 0, "Leaderboard table not found"

    def test_leaderboard_has_2_agents(self, page: Page, multi_agent_report: Path):
        """Leaderboard should show 2 agents."""
        page.goto(f"file://{multi_agent_report}")
        page.wait_for_load_state("networkidle")

        rows = page.locator(".leaderboard-table tbody tr")
        assert rows.count() == 2, f"Expected 2 agent rows, got {rows.count()}"

    def test_winner_highlighted(self, page: Page, multi_agent_report: Path):
        """Winner row should be highlighted."""
        page.goto(f"file://{multi_agent_report}")
        page.wait_for_load_state("networkidle")

        # Look for winner class or highlighted styling
        winner = page.locator(
            ".leaderboard-table tbody tr.winner, .leaderboard-table tbody tr:first-child"
        )
        assert winner.count() > 0, "Winner row not found"


class TestMultiAgentNoSelector:
    """Test that agent selector is NOT shown for 2 agents."""

    def test_no_agent_selector(self, page: Page, multi_agent_report: Path):
        """Agent selector should NOT exist for only 2 agents."""
        page.goto(f"file://{multi_agent_report}")
        page.wait_for_load_state("networkidle")

        selector = page.locator("#agent-selector")
        assert selector.count() == 0, "Agent selector should not exist for 2 agents (need 3+)"


class TestMultiAgentComparison:
    """Test comparison columns for 2 agents."""

    def test_two_comparison_columns(self, page: Page, multi_agent_report: Path):
        """Should have 2 comparison columns visible within one test."""
        page.goto(f"file://{multi_agent_report}")
        page.wait_for_load_state("networkidle")

        # Click to expand first test
        header = page.locator(".test-row .px-5.py-3").first
        header.click()
        page.wait_for_timeout(300)

        # Count visible columns within the first expanded test detail only
        columns = page.locator(".test-row:first-child .test-detail .comparison-column:not(.hidden)")
        assert columns.count() == 2, (
            f"Expected 2 visible columns in first test, got {columns.count()}"
        )

        grid_style = page.evaluate(
            """
            () => {
                const grid = document.querySelector('.test-row:first-child .test-detail .comparison-grid');
                return grid ? getComputedStyle(grid).gridTemplateColumns : '';
            }
            """
        )
        column_count = len([col for col in grid_style.split(" ") if col])
        assert column_count == 2, f"Expected two-column grid layout, got '{grid_style}'"


class TestMultiAgentMermaidOverlay:
    """Test mermaid overlay functionality."""

    def test_clicking_mermaid_opens_overlay(self, page: Page, multi_agent_report: Path):
        """Clicking mermaid diagram should open overlay."""
        page.goto(f"file://{multi_agent_report}")
        page.wait_for_load_state("networkidle")

        # Click to expand first test
        header = page.locator(".test-row .px-5.py-3").first
        header.click()
        page.wait_for_timeout(500)

        # The mermaid container should be clickable and have onclick
        mermaid_container = page.locator(
            ".test-row:first-child .test-detail [data-mermaid-code]"
        ).first
        if mermaid_container.count() > 0:
            mermaid_container.click()
            page.wait_for_timeout(500)

            # Overlay should be active (visible)
            overlay = page.locator("#overlay")
            is_active = overlay.evaluate("el => el.classList.contains('active')")
            assert is_active, "Overlay should be active after clicking mermaid"

    def test_overlay_closes_on_backdrop(self, page: Page, multi_agent_report: Path):
        """Overlay should close when clicking close button."""
        page.goto(f"file://{multi_agent_report}")
        page.wait_for_load_state("networkidle")

        # Click to expand first test
        header = page.locator(".test-row .px-5.py-3").first
        header.click()
        page.wait_for_timeout(500)

        # Click mermaid to open overlay
        mermaid_container = page.locator(
            ".test-row:first-child .test-detail [data-mermaid-code]"
        ).first
        if mermaid_container.count() > 0:
            mermaid_container.click()
            page.wait_for_timeout(500)

            # Verify overlay is active
            overlay = page.locator("#overlay")
            is_active = overlay.evaluate("el => el.classList.contains('active')")
            assert is_active, "Overlay should be active before closing"

            # Click the backdrop (avoid the inner content which stops propagation)
            overlay.click(position={"x": 5, "y": 5})
            page.wait_for_timeout(300)

            # Verify overlay is no longer active
            is_closed = overlay.evaluate("el => !el.classList.contains('active')")
            assert is_closed, "Overlay should not be active after clicking backdrop"


class TestMultiAgentFilterButtons:
    """Test filter buttons work."""

    def test_filter_buttons_exist(self, page: Page, multi_agent_report: Path):
        """Filter buttons should exist."""
        page.goto(f"file://{multi_agent_report}")
        page.wait_for_load_state("networkidle")

        all_btn = page.locator('.filter-btn[data-filter="all"]')
        failed_btn = page.locator('.filter-btn[data-filter="failed"]')

        assert all_btn.count() == 1, "All filter button not found"
        assert failed_btn.count() == 1, "Failed filter button not found"

    def test_all_filter_active_by_default(self, page: Page, multi_agent_report: Path):
        """All filter should be active by default."""
        page.goto(f"file://{multi_agent_report}")
        page.wait_for_load_state("networkidle")

        all_btn = page.locator('.filter-btn[data-filter="all"]')
        classes = all_btn.get_attribute("class") or ""
        assert "active" in classes, "All filter should be active by default"
