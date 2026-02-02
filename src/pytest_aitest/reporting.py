"""Reporting module for pytest-aitest.

This module provides backwards-compatible imports from the new package structure.
New code should import from pytest_aitest.reporting subpackage directly.
"""

# Re-export from reporting subpackage for backwards compatibility
from pytest_aitest.reporting.collector import ReportCollector, TestReport
from pytest_aitest.reporting.generator import (
    ReportGenerator,
    SuiteReport,
    generate_mermaid_sequence,
)

__all__ = [
    "ReportCollector",
    "ReportGenerator",
    "SuiteReport",
    "TestReport",
    "generate_mermaid_sequence",
]
