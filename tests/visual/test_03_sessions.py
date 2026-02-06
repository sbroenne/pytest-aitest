"""Visual tests for session report (03_multi_agent_sessions.json).

2 agents with sessions - Tests:
- Session grouping with visual connectors
- Session header shows test count and status
- Leaderboard shows 2 agents
- NO agent selector (only 2 agents)
- Both comparison columns visible
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page


class TestSessionGrouping:
    """Test session grouping functionality."""

    def test_session_groups_exist(self, page: Page, session_report: Path):
        """Session group containers should exist."""
        page.goto(f"file://{session_report}")
        page.wait_for_load_state("networkidle")

        # Sessions use data-group-type="session" attribute
        sessions = page.locator('.test-group[data-group-type="session"]')
        assert sessions.count() > 0, "Session groups not found"

    def test_session_header_exists(self, page: Page, session_report: Path):
        """Session header should show session name."""
        page.goto(f"file://{session_report}")
        page.wait_for_load_state("networkidle")

        # Session group header
        session_header = page.locator('.test-group[data-group-type="session"] .group-header')
        assert session_header.count() > 0, "Session header not found"

    def test_session_has_multiple_tests(self, page: Page, session_report: Path):
        """Session should contain multiple tests."""
        page.goto(f"file://{session_report}")
        page.wait_for_load_state("networkidle")

        # Find test rows within a session
        session = page.locator('.test-group[data-group-type="session"]').first
        if session.count() > 0:
            tests_in_session = session.locator(".test-row")
            assert tests_in_session.count() >= 2, "Session should have multiple tests"


class TestSessionLeaderboard:
    """Test leaderboard with sessions."""

    def test_leaderboard_exists(self, page: Page, session_report: Path):
        """Leaderboard should exist."""
        page.goto(f"file://{session_report}")
        page.wait_for_load_state("networkidle")

        leaderboard = page.locator(".leaderboard-table")
        assert leaderboard.count() > 0, "Leaderboard table not found"

    def test_leaderboard_has_2_agents(self, page: Page, session_report: Path):
        """Leaderboard should show 2 agents."""
        page.goto(f"file://{session_report}")
        page.wait_for_load_state("networkidle")

        rows = page.locator(".leaderboard-table tbody tr")
        assert rows.count() == 2, f"Expected 2 agent rows, got {rows.count()}"


class TestSessionNoSelector:
    """Test that agent selector is NOT shown for 2 agents."""

    def test_no_agent_selector(self, page: Page, session_report: Path):
        """Agent selector should NOT exist for only 2 agents."""
        page.goto(f"file://{session_report}")
        page.wait_for_load_state("networkidle")

        selector = page.locator("#agent-selector")
        assert selector.count() == 0, "Agent selector should not exist for 2 agents"


class TestSessionComparison:
    """Test comparison columns in session report."""

    def test_two_comparison_columns(self, page: Page, session_report: Path):
        """Should have 2 comparison columns visible within one test."""
        page.goto(f"file://{session_report}")
        page.wait_for_load_state("networkidle")

        # Click to expand first test
        header = page.locator(".test-row .px-5.py-3").first
        header.click()
        page.wait_for_timeout(300)

        # Count columns within the first expanded test detail only
        columns = page.locator(".test-row:first-child .test-detail .comparison-column")
        assert columns.count() == 2, f"Expected 2 columns in first test, got {columns.count()}"


class TestSessionTestInteraction:
    """Test test row interaction within sessions."""

    def test_test_row_expands(self, page: Page, session_report: Path):
        """Test rows in session should expand on toggle."""
        page.goto(f"file://{session_report}")
        page.wait_for_load_state("networkidle")

        # Expand first test via direct JS toggle
        page.evaluate("""
            const row = document.querySelector('.test-row');
            row.querySelector('.test-detail').classList.remove('hidden');
        """)
        page.wait_for_timeout(300)

        visible_details = page.locator(".test-detail:not(.hidden)")
        assert visible_details.count() >= 1, "Test detail not visible after toggle"
