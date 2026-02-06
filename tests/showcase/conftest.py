"""Pytest configuration for showcase tests.

These tests generate the hero report for README demonstration.
"""


def pytest_configure(config):
    """Register showcase marker."""
    config.addinivalue_line(
        "markers",
        "showcase: mark test as part of the showcase suite for hero report",
    )


# Re-export fixtures from integration tests
pytest_plugins = ["tests.integration.conftest"]
