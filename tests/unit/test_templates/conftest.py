"""Shared fixtures and helpers for template component tests.

Provides utilities to render individual Jinja2 partials in isolation
with data extracted from real test fixtures (from integration tests).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

# Directories
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "src" / "pytest_aitest" / "templates"
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "reports"


# =============================================================================
# Template Helper Functions (same as generator.py)
# =============================================================================

def _render_markdown(text: str) -> Markup:
    """Convert markdown to HTML, sanitized for safe output."""
    try:
        import markdown
        html = markdown.markdown(text, extensions=["extra"])
        return Markup(html)
    except ImportError:
        import html as html_module
        escaped = html_module.escape(text)
        return Markup(escaped.replace("\n", "<br>"))


def get_provider(model_name: str) -> str:
    """Extract provider name from model string for badge styling."""
    model_lower = model_name.lower()
    if "azure" in model_lower:
        return "azure"
    elif "openai" in model_lower or model_lower.startswith("gpt"):
        return "openai"
    elif "anthropic" in model_lower or "claude" in model_lower:
        return "anthropic"
    elif "vertex" in model_lower or "gemini" in model_lower:
        return "vertex"
    return "default"


def format_cost(cost: float) -> str:
    """Format cost as a dollar string."""
    if cost < 0.01:
        return f"${cost:.4f}"
    return f"${cost:.2f}"


# =============================================================================
# Fixture Data Extraction
# =============================================================================

def load_fixture(name: str) -> dict[str, Any]:
    """Load raw JSON fixture."""
    path = FIXTURES_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_pydantic_report(name: str):
    """Load fixture and convert to Pydantic report."""
    from pytest_aitest.cli import load_suite_report
    from pytest_aitest.models.converter import convert_suite_report
    
    path = FIXTURES_DIR / f"{name}.json"
    report, ai_summary = load_suite_report(path)
    return convert_suite_report(report, ai_summary=ai_summary)


def extract_model_groups(fixture_name: str) -> list[dict[str, Any]]:
    """Extract model_groups data from a fixture (for model_leaderboard tests)."""
    from pytest_aitest.reporting.generator import ReportGenerator
    
    report = load_pydantic_report(fixture_name)
    gen = ReportGenerator()
    return gen._build_model_rankings(report)


def extract_prompt_groups(fixture_name: str) -> list[dict[str, Any]]:
    """Extract prompt_groups data from a fixture (for prompt_comparison tests)."""
    from pytest_aitest.reporting.generator import ReportGenerator
    
    report = load_pydantic_report(fixture_name)
    gen = ReportGenerator()
    return gen._build_prompt_rankings(report)


def extract_comparison_grid(fixture_name: str, mode: str) -> dict[str, Any]:
    """Extract comparison_grid data from a fixture."""
    from pytest_aitest.reporting.generator import ReportGenerator
    
    report = load_pydantic_report(fixture_name)
    gen = ReportGenerator()
    return gen._build_comparison_grid(report, mode)


def extract_ai_summary(fixture_name: str) -> str | None:
    """Extract ai_summary from a fixture."""
    report = load_pydantic_report(fixture_name)
    return report.ai_summary


def extract_flags(fixture_name: str) -> dict[str, Any]:
    """Extract adaptive flags from a fixture."""
    from pytest_aitest.reporting.generator import ReportGenerator
    
    report = load_pydantic_report(fixture_name)
    gen = ReportGenerator()
    return gen._build_adaptive_flags(report)


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture
def jinja_env() -> Environment:
    """Create Jinja2 environment configured like the real generator."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["markdown"] = _render_markdown
    return env


def _to_file_url(path: str) -> str:
    """Convert file path to file:// URL."""
    from pathlib import Path
    return Path(path).resolve().as_uri()


@pytest.fixture
def render_partial(jinja_env: Environment):
    """Fixture to render a partial template with given context.
    
    Usage:
        def test_something(render_partial):
            html = render_partial("ai_summary.html", ai_summary="**Bold**")
            assert "<strong>" in html
    """
    def _render(template_name: str, **context: Any) -> str:
        # Partials are in the partials/ subdirectory
        if not template_name.startswith("partials/"):
            template_name = f"partials/{template_name}"
        template = jinja_env.get_template(template_name)
        
        # Add common helper functions that templates expect
        context.setdefault("get_provider", get_provider)
        context.setdefault("format_cost", format_cost)
        context.setdefault("to_file_url", _to_file_url)
        
        return template.render(**context)
    return _render


def parse_html(html: str) -> BeautifulSoup:
    """Parse HTML string to BeautifulSoup for assertions."""
    return BeautifulSoup(html, "lxml")


# =============================================================================
# Test Data Factories (for simple/minimal cases only)
# =============================================================================

def make_flags(**overrides: Any) -> dict[str, Any]:
    """Create adaptive flags dict with sensible defaults."""
    defaults = {
        "show_model_leaderboard": False,
        "show_prompt_comparison": False,
        "show_comparison_grid": False,
        "show_matrix": False,
        "show_tool_comparison": False,
        "show_side_by_side": False,
        "show_sessions": False,
        "show_ai_summary": False,
        "has_failures": False,
        "has_skipped": False,
        "model_count": 1,
        "prompt_count": 1,
        "single_model_name": "gpt-5-mini",
        "single_prompt_name": None,
    }
    defaults.update(overrides)
    return defaults


def make_model_ranking(
    name: str,
    rank: int = 1,
    passed: int = 5,
    failed: int = 0,
    total: int = 5,
    pass_rate: float = 100.0,
    total_tokens: int = 500,
    total_cost: float = 0.02,
    avg_duration_ms: float = 1000.0,
) -> dict[str, Any]:
    """Create a model ranking dict for leaderboard testing."""
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    return {
        "dimension_value": name,
        "rank": rank,
        "medal": medals.get(rank),
        "passed": passed,
        "failed": failed,
        "total": total,
        "pass_rate": pass_rate,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "avg_duration_ms": avg_duration_ms,
        "efficiency": total_tokens / passed if passed > 0 else float("inf"),
    }


def make_comparison_grid(
    mode: str = "model_comparison",
    columns: list[str] | None = None,
    rows: list[dict] | None = None,
) -> dict[str, Any]:
    """Create a comparison grid for testing."""
    if columns is None:
        columns = ["gpt-5-mini", "gpt-4.1"]
    if rows is None:
        rows = [
            {
                "name": "test_weather",
                "cells": [
                    {"test": {"outcome": "passed"}, "outcome": "passed", "duration": 1200, "tokens": 100},
                    {"test": {"outcome": "passed"}, "outcome": "passed", "duration": 800, "tokens": 80},
                ],
            },
        ]
    return {
        "mode": mode,
        "columns": columns,
        "rows": rows,
    }

