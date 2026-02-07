"""Fixtures conftest - imports from integration tests."""

# Import all fixtures from integration conftest
# Re-export pytest_configure so llm_assert uses Azure
from tests.integration.conftest import (  # noqa: F401
    banking_server,
    pytest_configure,  # noqa: F401
    todo_server,
    weather_server,
)
