"""Fixtures conftest - imports from integration tests."""

# Import all fixtures from integration conftest
from tests.integration.conftest import (  # noqa: F401
    banking_server,
    todo_server,
    weather_server,
)
