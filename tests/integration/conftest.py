"""Fixtures for integration tests.

Centralized configuration and server fixtures for all integration tests.
Tests should import constants from here and create agents inline.

Example:
    from tests.integration.conftest import (
        DEFAULT_MODEL, DEFAULT_RPM, DEFAULT_TPM, DEFAULT_MAX_TURNS,
        BENCHMARK_MODELS, WEATHER_PROMPT, TODO_PROMPT,
    )

    @pytest.mark.asyncio
    async def test_weather(aitest_run, weather_server):
        agent = Agent(
            name="weather-test",
            provider=Provider(model=f"azure/{DEFAULT_MODEL}", rpm=DEFAULT_RPM, tpm=DEFAULT_TPM),
            mcp_servers=[weather_server],
            system_prompt=WEATHER_PROMPT,
            max_turns=DEFAULT_MAX_TURNS,
        )
        result = await aitest_run(agent, "What's the weather in Paris?")
        assert result.success
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Load .env from workspace root
_env_file = Path(__file__).parents[4] / ".env"
if _env_file.exists():
    from dotenv import load_dotenv

    load_dotenv(_env_file)

# LiteLLM bug workaround: their logging code expects AZURE_API_BASE but
# Azure SDK uses AZURE_OPENAI_ENDPOINT. Set both to silence the warning.
if os.environ.get("AZURE_OPENAI_ENDPOINT") and not os.environ.get("AZURE_API_BASE"):
    os.environ["AZURE_API_BASE"] = os.environ["AZURE_OPENAI_ENDPOINT"]

from pytest_aitest import MCPServer, Wait

# =============================================================================
# Pytest Configuration Hooks
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest plugins for integration tests."""
    # Configure pytest-llm-assert to use Azure instead of OpenAI
    # This fixture is used for semantic assertions in tests
    azure_base = os.environ.get("AZURE_API_BASE") or os.environ.get("AZURE_OPENAI_ENDPOINT")
    if azure_base:
        # Override the default options for llm_assert fixture
        config.option.llm_model = "azure/gpt-5-mini"
        config.option.llm_api_base = azure_base

# =============================================================================
# Test Configuration Constants
# =============================================================================

# Default model for most tests (cheapest Azure deployment)
DEFAULT_MODEL = "gpt-5-mini"

# Models for benchmark comparison (cheap vs capable)
BENCHMARK_MODELS = ["gpt-5-mini", "gpt-5.1-chat"]

# Rate limits for Azure deployments
DEFAULT_RPM = 10
DEFAULT_TPM = 10000

# Default turn limits
DEFAULT_MAX_TURNS = 5

# =============================================================================
# System Prompts
# =============================================================================

WEATHER_PROMPT = """You are a weather assistant with access to real-time weather tools.

IMPORTANT: Always use the available tools to get weather data. Never guess or use your training data for weather information - it may be outdated. The tools provide current, accurate data.

Available tools:
- get_weather: Get current weather for a city
- get_forecast: Get multi-day forecast for a city
- list_cities: See which cities have weather data
- compare_weather: Compare weather between two cities

When asked about weather, ALWAYS call the appropriate tool first, then respond based on the tool's output."""

TODO_PROMPT = """You are a task management assistant with access to a todo list system.

IMPORTANT: Always use the available tools to manage tasks. The tools are the only way to create, modify, or view tasks.

Available tools:
- add_task: Add a new task (with optional list name and priority)
- complete_task: Mark a task as done (requires task_id)
- list_tasks: View tasks (can filter by list or completion status)
- get_lists: See all available list names
- delete_task: Remove a task permanently
- set_priority: Change task priority (low, normal, high)

When asked to manage tasks, ALWAYS use the appropriate tools. After modifying tasks, use list_tasks to verify and show the user the current state."""

KEYVALUE_PROMPT = "You are a helpful assistant. Use the tools to complete tasks."

# =============================================================================
# MCP Server Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def weather_server():
    """Weather MCP server - simple "hello world" for testing."""
    return MCPServer(
        command=[
            sys.executable,
            "-u",
            "-m",
            "pytest_aitest.testing.weather_mcp",
        ],
        wait=Wait.for_tools(["get_weather", "get_forecast", "list_cities"]),
    )


@pytest.fixture(scope="module")
def todo_server():
    """Todo MCP server - stateful task management."""
    return MCPServer(
        command=[
            sys.executable,
            "-u",
            "-m",
            "pytest_aitest.testing.todo_mcp",
        ],
        wait=Wait.for_tools(["add_task", "list_tasks", "complete_task"]),
    )


@pytest.fixture(scope="module")
def keyvalue_server():
    """KeyValue MCP server - simple key-value store."""
    return MCPServer(
        command=[
            sys.executable,
            "-u",
            "-m",
            "pytest_aitest.testing.mcp_server",
        ],
        wait=Wait.for_tools(["get", "set", "list_keys"]),
    )
