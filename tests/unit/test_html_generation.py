"""HTML report generation tests.

Tests structural correctness of HTML reports using BeautifulSoup.
Uses fixtures from tests/fixtures/reports/*.json to verify each report scenario
renders correctly with the expected sections.

Fixture Coverage Matrix:
| Section           | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 |
|-------------------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Header            | ✓  | ✓  | ✓  | ✓  | ✓  | ✓  | ✓  | ✓  |
| Summary Cards     | ✓  | ✓  | ✓  | ✓  | ✓  | ✓  | ✓  | ✓  |
| Model Leaderboard | ✗  | ✓  | ✗  | ✓  | ✓  | ✗  | ✗  | ✓  |
| Prompt Table      | ✗  | ✗  | ✓  | ✓  | ✗  | ✗  | ✗  | ✓  |
| Matrix Grid       | ✗  | ✗  | ✗  | ✓  | ✗  | ✗  | ✗  | ✓  |
| Tool Comparison   | ✗  | ✓  | ✓  | ✓  | ✓  | ✗  | ✗  | ✓  |
| AI Summary        | ✗  | ✗  | ✗  | ✗  | ✗  | ✓  | ✗  | ✓  |
| Skipped Badge     | ✗  | ✗  | ✗  | ✗  | ✗  | ✗  | ✓  | ✗  |
| Test List         | ✓  | ✓  | ✓  | ✓  | ✓  | ✓  | ✓  | ✓  |
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from bs4 import BeautifulSoup

from pytest_aitest.cli import load_suite_report
from pytest_aitest.reporting.generator import ReportGenerator

if TYPE_CHECKING:
    pass

# =============================================================================
# Fixtures
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "reports"

# All fixture files
FIXTURE_FILES = sorted(FIXTURES_DIR.glob("*.json"))
FIXTURE_IDS = [f.stem for f in FIXTURE_FILES]


@pytest.fixture(params=FIXTURE_FILES, ids=FIXTURE_IDS)
def fixture_path(request) -> Path:
    """Get fixture path."""
    return request.param


@pytest.fixture
def fixture_json(fixture_path) -> dict:
    """Load a JSON fixture."""
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def fixture_html(fixture_path) -> str:
    """Generate HTML from a fixture."""
    report, _ai_summary = load_suite_report(fixture_path)  # ai_summary deprecated
    generator = ReportGenerator()
    
    # Generate to temp file and read back
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        output_path = Path(f.name)
    
    generator.generate_html(report, output_path)
    html = output_path.read_text(encoding="utf-8")
    output_path.unlink()  # Clean up
    return html


@pytest.fixture
def soup(fixture_html) -> BeautifulSoup:
    """Parse HTML into BeautifulSoup."""
    return BeautifulSoup(fixture_html, "lxml")


def load_fixture(name: str) -> dict:
    """Load a specific fixture by name (without .json extension)."""
    path = FIXTURES_DIR / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def generate_html_from_fixture(name: str) -> str:
    """Generate HTML from a named fixture."""
    path = FIXTURES_DIR / f"{name}.json"
    report, _ai_summary = load_suite_report(path)  # ai_summary deprecated
    generator = ReportGenerator()
    
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        output_path = Path(f.name)
    
    generator.generate_html(report, output_path)
    html = output_path.read_text(encoding="utf-8")
    output_path.unlink()
    return html


def parse_html(html: str) -> BeautifulSoup:
    """Parse HTML string to BeautifulSoup."""
    return BeautifulSoup(html, "lxml")


# =============================================================================
# Common Structure Tests (all fixtures)
# =============================================================================


class TestCommonStructure:
    """Tests that apply to all fixtures."""

    def test_has_doctype(self, fixture_html):
        """HTML should start with doctype."""
        assert fixture_html.strip().startswith("<!DOCTYPE html>")

    def test_has_html_head_body(self, soup):
        """HTML should have html, head, and body tags."""
        assert soup.html is not None
        assert soup.head is not None
        assert soup.body is not None

    def test_has_title(self, soup):
        """Page should have a title."""
        title = soup.find("title")
        assert title is not None
        assert title.string is not None
        assert "pytest-aitest" in title.string.lower()

    def test_has_header_section(self, soup):
        """Report should have a header section."""
        header = soup.find("header") or soup.find(class_="header")
        assert header is not None, "Missing header section"

    def test_has_summary_section(self, soup):
        """Report should have a summary section with key metrics."""
        # Look for summary cards or stats
        summary = (
            soup.find(id="summary") 
            or soup.find(class_="summary")
            or soup.find("section", class_=lambda c: c and "summary" in c)
        )
        assert summary is not None, "Missing summary section"

    def test_has_test_list(self, soup):
        """Report should have a test results list."""
        # Look for test items
        test_items = soup.find_all(class_=lambda c: c and "test" in c.lower())
        assert len(test_items) > 0, "Missing test results list"


# =============================================================================
# Fixture-Specific Tests
# =============================================================================


class TestBasicUsage:
    """Tests for 01_basic_usage.json - simple mode with pass/fail."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_fixture("01_basic_usage")
        self.html = generate_html_from_fixture("01_basic_usage")
        self.soup = parse_html(self.html)

    def test_mode_is_simple(self):
        """Basic usage should be simple mode."""
        assert self.data["mode"] == "simple"

    def test_no_model_leaderboard(self):
        """Simple mode should NOT have model leaderboard."""
        leaderboard = self.soup.find(id="model-leaderboard")
        # Either missing or hidden
        if leaderboard:
            assert "hidden" in leaderboard.get("class", []) or leaderboard.get("style", "") == "display:none"

    def test_shows_failed_test(self):
        """Should show failed test with appropriate badge."""
        # Find failed badge or status
        failed = self.soup.find(class_=lambda c: c and "fail" in c.lower())
        assert failed is not None, "Missing failed test indicator"


class TestModelComparison:
    """Tests for 02_model_comparison.json - 2 models."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_fixture("02_model_comparison")
        self.html = generate_html_from_fixture("02_model_comparison")
        self.soup = parse_html(self.html)

    def test_mode_is_model_comparison(self):
        """Should be model_comparison mode."""
        assert self.data["mode"] == "model_comparison"

    def test_has_model_leaderboard(self):
        """Should have model leaderboard section."""
        leaderboard = (
            self.soup.find(id="model-leaderboard")
            or self.soup.find(class_=lambda c: c and "leaderboard" in c.lower())
            or self.soup.find(string=lambda s: s and "leaderboard" in s.lower())
        )
        assert leaderboard is not None, "Missing model leaderboard"

    def test_has_comparison_grid(self):
        """Should have comparison grid showing tests by model."""
        grid_header = self.soup.find(string=lambda s: s and "Test Results by Model" in s)
        assert grid_header is not None, "Missing 'Test Results by Model' comparison grid"

    def test_comparison_grid_has_model_columns(self):
        """Comparison grid should have columns for each model."""
        # Find the comparison grid table
        tables = self.soup.find_all("table", class_="matrix")
        grid_found = False
        for table in tables:
            headers = [th.get_text().strip() for th in table.find_all("th")]
            if "gpt-4.1" in headers and "gpt-5-mini" in headers:
                grid_found = True
                break
        assert grid_found, "Comparison grid should have model columns"

    def test_shows_both_models(self):
        """Should show both models (gpt-5-mini and gpt-4.1)."""
        html_lower = self.html.lower()
        assert "gpt-5-mini" in html_lower or "gpt5-mini" in html_lower
        assert "gpt-4.1" in html_lower

    def test_has_tool_comparison(self):
        """Should have tool comparison grid."""
        tool_section = (
            self.soup.find(id="tool-comparison")
            or self.soup.find(class_=lambda c: c and "tool" in c.lower())
            or self.soup.find(string=lambda s: s and "tool" in s.lower())
        )
        assert tool_section is not None, "Missing tool comparison"


class TestPromptComparison:
    """Tests for 03_prompt_comparison.json - 3 prompts."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_fixture("03_prompt_comparison")
        self.html = generate_html_from_fixture("03_prompt_comparison")
        self.soup = parse_html(self.html)

    def test_mode_is_prompt_comparison(self):
        """Should be prompt_comparison mode."""
        assert self.data["mode"] == "prompt_comparison"

    def test_has_prompt_table(self):
        """Should have prompt comparison table."""
        prompt_section = (
            self.soup.find(id="prompt-comparison")
            or self.soup.find(class_=lambda c: c and "prompt" in c.lower())
            or self.soup.find(string=lambda s: s and "system prompt" in s.lower())
        )
        assert prompt_section is not None, "Missing system prompt comparison"

    def test_has_comparison_grid(self):
        """Should have comparison grid showing tests by system prompt."""
        grid_header = self.soup.find(string=lambda s: s and "Test Results by System Prompt" in s)
        assert grid_header is not None, "Missing 'Test Results by System Prompt' comparison grid"

    def test_comparison_grid_has_prompt_columns(self):
        """Comparison grid should have columns for each prompt."""
        # Find the comparison grid table
        tables = self.soup.find_all("table", class_="matrix")
        grid_found = False
        for table in tables:
            headers = [th.get_text().strip().lower() for th in table.find_all("th")]
            # Check if all three prompts are represented
            if any("brief" in h for h in headers) and any("detailed" in h for h in headers):
                grid_found = True
                break
        assert grid_found, "Comparison grid should have prompt columns"

    def test_shows_all_prompts(self):
        """Should show all three prompts."""
        html_lower = self.html.lower()
        assert "brief" in html_lower
        assert "detailed" in html_lower
        assert "structured" in html_lower


class TestMatrix:
    """Tests for 04_matrix.json - 2 models × 3 prompts."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_fixture("04_matrix")
        self.html = generate_html_from_fixture("04_matrix")
        self.soup = parse_html(self.html)

    def test_mode_is_matrix(self):
        """Should be matrix mode."""
        assert self.data["mode"] == "matrix"

    def test_has_matrix_grid(self):
        """Should have matrix grid."""
        matrix = (
            self.soup.find(id="matrix")
            or self.soup.find(class_=lambda c: c and "matrix" in c.lower())
            or self.soup.find("table", class_=lambda c: c and "grid" in c.lower() if c else False)
        )
        assert matrix is not None, "Missing matrix grid"

    def test_has_comparison_matrix_header(self):
        """Should have 'Comparison Matrix' header (not by Model or by Prompt)."""
        grid_header = self.soup.find(string=lambda s: s and "Comparison Matrix" in s)
        assert grid_header is not None, "Missing 'Comparison Matrix' header"

    def test_has_model_leaderboard(self):
        """Matrix mode should also have model leaderboard."""
        leaderboard = (
            self.soup.find(id="model-leaderboard")
            or self.soup.find(class_=lambda c: c and "leaderboard" in c.lower())
        )
        assert leaderboard is not None, "Missing model leaderboard in matrix mode"


class TestSessions:
    """Tests for 05_sessions.json - session continuity."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_fixture("05_sessions")
        self.html = generate_html_from_fixture("05_sessions")
        self.soup = parse_html(self.html)

    def test_has_session_info(self):
        """Should show session information."""
        # Sessions might be shown as groups or with context counts
        session_indicator = (
            self.soup.find(class_=lambda c: c and "session" in c.lower())
            or self.soup.find(string=lambda s: s and "session" in s.lower())
            or self.soup.find(string=lambda s: s and "context" in s.lower())
        )
        assert session_indicator is not None, "Missing session information"


class TestWithAIInsights:
    """Tests for fixtures with AI insights (v3.0 schema)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        # Use any fixture - all have insights in v3.0
        self.data = load_fixture("02_model_comparison")
        self.html = generate_html_from_fixture("02_model_comparison")
        self.soup = parse_html(self.html)

    def test_has_insights_field(self):
        """Fixture should have insights field (v3.0 requirement)."""
        assert self.data.get("insights") is not None

    def test_insights_has_recommendation(self):
        """Insights should have recommendation structure."""
        insights = self.data.get("insights")
        assert insights.get("recommendation") is not None
        assert insights["recommendation"].get("configuration") is not None


class TestWithSkipped:
    """Tests for 07_with_skipped.json - tests with skipped marker.
    
    Note: Currently pytest-aitest doesn't capture skipped tests in JSON
    because they don't go through aitest_run. The fixture contains only
    the tests that actually ran.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_fixture("07_with_skipped")
        self.html = generate_html_from_fixture("07_with_skipped")
        self.soup = parse_html(self.html)

    def test_summary_has_tests(self):
        """Summary should show test count (excluding skipped)."""
        # Skipped tests don't run through aitest_run, so they're not in the JSON
        assert self.data["summary"]["total"] >= 1

    def test_shows_pass_status(self):
        """Should show passing tests."""
        passed_indicator = (
            self.soup.find(class_=lambda c: c and "pass" in c.lower())
            or self.soup.find(string=lambda s: s and "passed" in s.lower())
        )
        assert passed_indicator is not None, "Missing pass indicator"

    def test_generates_valid_html(self):
        """Should generate valid HTML structure."""
        assert self.soup.find("html") is not None
        assert self.soup.find("body") is not None


class TestMatrixFull:
    """Tests for 08_matrix_full.json - all features combined."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_fixture("08_matrix_full")
        self.html = generate_html_from_fixture("08_matrix_full")
        self.soup = parse_html(self.html)

    def test_mode_is_matrix(self):
        """Should be matrix mode."""
        assert self.data["mode"] == "matrix"

    def test_has_all_sections(self):
        """Should have all major sections."""
        # Matrix mode should have everything
        html_lower = self.html.lower()
        
        # Check for various sections (flexible matching)
        assert "leaderboard" in html_lower or "ranking" in html_lower, "Missing leaderboard"
        assert "matrix" in html_lower or "grid" in html_lower, "Missing matrix"
        
    def test_has_insights(self):
        """Full matrix should have insights (v3.0)."""
        assert self.data.get("insights") is not None, "Missing insights"

    def test_correct_test_count(self):
        """Should have 18 tests (2 models × 3 prompts × 3 test cases)."""
        assert self.data["summary"]["total"] == 18


# =============================================================================
# Snapshot Tests (using syrupy)
# =============================================================================


class TestHTMLSnapshots:
    """Snapshot tests for HTML regression detection.
    
    These tests capture the HTML structure and compare against golden masters.
    Run `pytest --snapshot-update` to update snapshots when intentional changes are made.
    """

    @pytest.fixture(params=FIXTURE_FILES[:3], ids=FIXTURE_IDS[:3])  # Limit to avoid huge snapshots
    def fixture_for_snapshot(self, request) -> tuple[str, str]:
        """Load fixture and generate HTML."""
        fixture_name = request.param.stem
        html = generate_html_from_fixture(fixture_name)
        return fixture_name, html

    def test_html_structure_snapshot(self, fixture_for_snapshot, snapshot):
        """Snapshot test for HTML structure.
        
        Captures key structural elements rather than full HTML to reduce noise.
        """
        name, html = fixture_for_snapshot
        soup = parse_html(html)
        
        # Extract structural elements
        structure = {
            "title": soup.title.string if soup.title else None,
            "sections": [
                elem.get("id") or elem.get("class", ["unnamed"])[0]
                for elem in soup.find_all("section")
            ],
            "table_count": len(soup.find_all("table")),
            "has_header": soup.header is not None,
            "has_footer": soup.footer is not None,
        }
        
        assert structure == snapshot
