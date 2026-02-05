"""Reporting module - smart result aggregation and report generation."""

from pytest_aitest.reporting.collector import ReportCollector, SuiteReport, TestReport
from pytest_aitest.reporting.generator import (
    ReportGenerator,
    generate_mermaid_sequence,
    generate_session_mermaid,
    get_provider,
)
from pytest_aitest.reporting.insights import (
    InsightsGenerationError,
    create_placeholder_insights,
    generate_insights,
)

__all__ = [
    # Core exports
    "ReportCollector",
    "ReportGenerator",
    "SuiteReport",
    "TestReport",
    # Utilities
    "generate_mermaid_sequence",
    "generate_session_mermaid",
    "get_provider",
    # Insights generation
    "create_placeholder_insights",
    "generate_insights",
    "InsightsGenerationError",
]
