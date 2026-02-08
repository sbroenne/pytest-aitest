"""Integration tests for SSE and Streamable HTTP transports.

Tests that the MCPServer transport feature works end-to-end by starting a
FastMCP-based banking server as a subprocess with non-stdio transports and
connecting to it via the MCP SDK client.

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
    BANKING_PROMPT,
    DEFAULT_MAX_TURNS,
    DEFAULT_MODEL,
    DEFAULT_RPM,
    DEFAULT_TPM,
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
# Fixtures — start the SDK banking server as a subprocess
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def streamable_http_server():
    """Start the banking server with streamable-http transport."""
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-m",
            "pytest_aitest.testing.banking_mcp",
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
        wait=Wait.for_tools(["get_balance", "get_all_balances"]),
    )
    yield server
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="module")
def sse_server():
    """Start the banking server with SSE transport."""
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-m",
            "pytest_aitest.testing.banking_mcp",
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
        wait=Wait.for_tools(["get_balance", "get_all_balances"]),
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
    """Tests using the streamable-http transport."""

    async def test_balance_check(self, aitest_run, streamable_http_server):
        """Agent can check balance via streamable-http."""
        agent = Agent(
            name="banking-streamable-http",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            mcp_servers=[streamable_http_server],
            system_prompt=BANKING_PROMPT,
            max_turns=DEFAULT_MAX_TURNS,
        )
        result = await aitest_run(agent, "What's my checking account balance?")
        assert result.success
        assert result.tool_was_called("get_balance") or result.tool_was_called("get_all_balances")

    async def test_transfer(self, aitest_run, streamable_http_server):
        """Agent can perform a transfer via streamable-http."""
        agent = Agent(
            name="banking-streamable-http",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            mcp_servers=[streamable_http_server],
            system_prompt=BANKING_PROMPT,
            max_turns=DEFAULT_MAX_TURNS,
        )
        result = await aitest_run(agent, "Transfer $50 from checking to savings")
        assert result.success
        assert result.tool_was_called("transfer")


# ---------------------------------------------------------------------------
# SSE tests
# ---------------------------------------------------------------------------


class TestSSE:
    """Tests using the SSE transport."""

    async def test_balance_check(self, aitest_run, sse_server):
        """Agent can check balance via SSE."""
        agent = Agent(
            name="banking-sse",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            mcp_servers=[sse_server],
            system_prompt=BANKING_PROMPT,
            max_turns=DEFAULT_MAX_TURNS,
        )
        result = await aitest_run(agent, "What's my checking account balance?")
        assert result.success
        assert result.tool_was_called("get_balance") or result.tool_was_called("get_all_balances")

    async def test_transfer(self, aitest_run, sse_server):
        """Agent can perform a transfer via SSE."""
        agent = Agent(
            name="banking-sse",
            provider=Provider(
                model=f"azure/{DEFAULT_MODEL}",
                rpm=DEFAULT_RPM,
                tpm=DEFAULT_TPM,
            ),
            mcp_servers=[sse_server],
            system_prompt=BANKING_PROMPT,
            max_turns=DEFAULT_MAX_TURNS,
        )
        result = await aitest_run(agent, "Transfer $50 from checking to savings")
        assert result.success
        assert result.tool_was_called("transfer")
