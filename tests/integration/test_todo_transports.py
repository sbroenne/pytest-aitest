"""Integration tests for Todo MCP server with all transports.

Tests that the TodoStore MCP server works end-to-end across all three
transports (stdio, sse, streamable-http) by starting the server as a subprocess
and connecting via the MCP SDK client.

Requires: Azure OpenAI access (uses DEFAULT_MODEL).
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time

import pytest

from pytest_aitest import Agent, MCPServer, Provider, Wait

from .conftest import (
    DEFAULT_MAX_TURNS,
    DEFAULT_MODEL,
    DEFAULT_RPM,
    DEFAULT_TPM,
    TODO_PROMPT,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Find a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, host: str = "127.0.0.1", timeout: float = 15.0) -> None:
    """Block until *host:port* accepts a TCP connection or *timeout* expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.3)
    msg = f"Server on {host}:{port} did not start within {timeout}s"
    raise TimeoutError(msg)


# ---------------------------------------------------------------------------
# Fixtures — start the SDK todo server with different transports
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def streamable_http_todo_server():
    """Start the todo server with streamable-http transport."""
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-m",
            "pytest_aitest.testing.todo_mcp",
            "--transport",
            "streamable-http",
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_port(port)
    except TimeoutError:
        proc.kill()
        stdout, stderr = proc.communicate(timeout=5)
        msg = (
            f"Streamable HTTP server failed to start.\n"
            f"stdout: {stdout.decode(errors='replace')}\n"
            f"stderr: {stderr.decode(errors='replace')}"
        )
        raise RuntimeError(msg) from None

    server = MCPServer(
        transport="streamable-http",
        url=f"http://127.0.0.1:{port}/mcp",
        wait=Wait.for_tools(["add_task", "list_tasks", "complete_task"]),
    )
    yield server
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="module")
def sse_todo_server():
    """Start the todo server with SSE transport."""
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-m",
            "pytest_aitest.testing.todo_mcp",
            "--transport",
            "sse",
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_port(port)
    except TimeoutError:
        proc.kill()
        stdout, stderr = proc.communicate(timeout=5)
        msg = (
            f"SSE server failed to start.\n"
            f"stdout: {stdout.decode(errors='replace')}\n"
            f"stderr: {stderr.decode(errors='replace')}"
        )
        raise RuntimeError(msg) from None

    server = MCPServer(
        transport="sse",
        url=f"http://127.0.0.1:{port}/sse",
        wait=Wait.for_tools(["add_task", "list_tasks", "complete_task"]),
    )
    yield server
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------------------
# Streamable HTTP tests
# ---------------------------------------------------------------------------


class TestStreamableHTTP:
    """Tests using the streamable-http transport with todo server."""

    async def test_add_and_list_tasks(self, aitest_run, streamable_http_todo_server):
        """Agent can add tasks and list them via streamable-http."""
        agent = Agent(
            name="todo-streamable-http",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            mcp_servers=[streamable_http_todo_server],
            system_prompt=TODO_PROMPT,
            max_turns=DEFAULT_MAX_TURNS,
        )
        result = await aitest_run(
            agent, "Add a task 'Buy milk' and then list all tasks"
        )
        assert result.success
        assert result.tool_was_called("add_task")
        assert result.tool_was_called("list_tasks")

    async def test_complete_task_workflow(self, aitest_run, streamable_http_todo_server):
        """Agent can complete a task via streamable-http."""
        agent = Agent(
            name="todo-streamable-http",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            mcp_servers=[streamable_http_todo_server],
            system_prompt=TODO_PROMPT,
            max_turns=DEFAULT_MAX_TURNS,
        )
        result = await aitest_run(
            agent,
            "Add a task 'Test task' and then mark it as complete. Show me the result.",
        )
        assert result.success
        assert result.tool_was_called("add_task")
        assert result.tool_was_called("complete_task")


# ---------------------------------------------------------------------------
# SSE tests
# ---------------------------------------------------------------------------


class TestSSE:
    """Tests using the SSE transport with todo server."""

    async def test_add_and_list_tasks(self, aitest_run, sse_todo_server):
        """Agent can add tasks and list them via SSE."""
        agent = Agent(
            name="todo-sse",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            mcp_servers=[sse_todo_server],
            system_prompt=TODO_PROMPT,
            max_turns=DEFAULT_MAX_TURNS,
        )
        result = await aitest_run(
            agent, "Add a task 'Buy bread' and then list all tasks"
        )
        assert result.success
        assert result.tool_was_called("add_task")
        assert result.tool_was_called("list_tasks")

    async def test_complete_task_workflow(self, aitest_run, sse_todo_server):
        """Agent can complete a task via SSE."""
        agent = Agent(
            name="todo-sse",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            mcp_servers=[sse_todo_server],
            system_prompt=TODO_PROMPT,
            max_turns=DEFAULT_MAX_TURNS,
        )
        result = await aitest_run(
            agent,
            "Add a task 'Another test' and then mark it as complete.",
        )
        assert result.success
        assert result.tool_was_called("add_task")
        assert result.tool_was_called("complete_task")
