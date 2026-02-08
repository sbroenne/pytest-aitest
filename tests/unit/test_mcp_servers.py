"""Unit tests for MCP server process management.

These tests verify that MCP servers start correctly, tools are discovered,
and basic tool calls work - WITHOUT using LLM. This ensures the infrastructure
works before expensive integration tests.
"""

from __future__ import annotations

import sys

import pytest

from pytest_aitest import MCPServer, Wait
from pytest_aitest.execution.servers import MCPServerProcess


class TestMCPServerStdio:
    """Test stdio transport for MCP servers."""

    @pytest.mark.asyncio
    async def test_todo_mcp_starts_and_lists_tools(self):
        """Todo MCP server starts and discovers tools via stdio."""
        config = MCPServer(
            command=[sys.executable, "-u", "-m", "pytest_aitest.testing.todo_mcp"],
            wait=Wait.for_tools(["add_task", "list_tasks", "complete_task"]),
        )
        server = MCPServerProcess(config)

        try:
            await server.start()
            tools = server.get_tools()

            # Verify all expected tools are present
            expected_tools = [
                "add_task",
                "complete_task",
                "uncomplete_task",
                "delete_task",
                "list_tasks",
                "get_lists",
                "set_priority",
            ]
            for tool_name in expected_tools:
                assert tool_name in tools, f"Tool {tool_name} not found"
                assert "description" in tools[tool_name]
                assert "inputSchema" in tools[tool_name]
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_banking_mcp_starts_and_lists_tools(self):
        """Banking MCP server starts and discovers tools via stdio."""
        config = MCPServer(
            command=[sys.executable, "-u", "-m", "pytest_aitest.testing.banking_mcp"],
            wait=Wait.for_tools(
                ["get_balance", "get_all_balances", "transfer", "deposit", "withdraw"]
            ),
        )
        server = MCPServerProcess(config)

        try:
            await server.start()
            tools = server.get_tools()

            # Verify all expected tools are present
            expected_tools = [
                "get_balance",
                "get_all_balances",
                "transfer",
                "deposit",
                "withdraw",
                "get_transactions",
            ]
            for tool_name in expected_tools:
                assert tool_name in tools, f"Tool {tool_name} not found"
                assert "description" in tools[tool_name]
                assert "inputSchema" in tools[tool_name]
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_todo_sdk_mcp_starts_and_lists_tools(self):
        """Todo SDK (FastMCP) server starts and discovers tools via stdio."""
        config = MCPServer(
            command=[sys.executable, "-u", "-m", "pytest_aitest.testing.todo_sdk_mcp"],
            wait=Wait.for_tools(["add_task", "list_tasks", "complete_task"]),
        )
        server = MCPServerProcess(config)

        try:
            await server.start()
            tools = server.get_tools()

            # Verify all expected tools are present
            expected_tools = [
                "add_task",
                "complete_task",
                "uncomplete_task",
                "delete_task",
                "list_tasks",
                "get_lists",
                "set_priority",
            ]
            for tool_name in expected_tools:
                assert tool_name in tools, f"Tool {tool_name} not found"
                assert "description" in tools[tool_name]
                assert "inputSchema" in tools[tool_name]
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_banking_sdk_mcp_starts_and_lists_tools(self):
        """Banking SDK (FastMCP) server starts and discovers tools via stdio."""
        config = MCPServer(
            command=[sys.executable, "-u", "-m", "pytest_aitest.testing.banking_sdk_mcp"],
            wait=Wait.for_tools(
                ["get_balance", "get_all_balances", "transfer", "deposit", "withdraw"]
            ),
        )
        server = MCPServerProcess(config)

        try:
            await server.start()
            tools = server.get_tools()

            # Verify all expected tools are present
            expected_tools = [
                "get_balance",
                "get_all_balances",
                "transfer",
                "deposit",
                "withdraw",
                "get_transactions",
            ]
            for tool_name in expected_tools:
                assert tool_name in tools, f"Tool {tool_name} not found"
                assert "description" in tools[tool_name]
                assert "inputSchema" in tools[tool_name]
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_todo_mcp_tool_call(self):
        """Can call tools on todo MCP server."""
        config = MCPServer(
            command=[sys.executable, "-u", "-m", "pytest_aitest.testing.todo_mcp"],
            wait=Wait.for_tools(["add_task", "list_tasks"]),
        )
        server = MCPServerProcess(config)

        try:
            await server.start()

            # Add a task
            result = await server.call_tool("add_task", {"title": "Test task"})
            assert "Test task" in result or "message" in result.lower()

            # List tasks
            result = await server.call_tool("list_tasks", {})
            assert "Test task" in result or "[]" in result
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_banking_mcp_tool_call(self):
        """Can call tools on banking MCP server."""
        config = MCPServer(
            command=[sys.executable, "-u", "-m", "pytest_aitest.testing.banking_mcp"],
            wait=Wait.for_tools(["get_balance"]),
        )
        server = MCPServerProcess(config)

        try:
            await server.start()

            # Get balance
            result = await server.call_tool("get_balance", {"account": "checking"})
            assert "balance" in result.lower() or "1500" in result or "1,500" in result
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_todo_sdk_mcp_tool_call(self):
        """Can call tools on todo SDK (FastMCP) server."""
        config = MCPServer(
            command=[sys.executable, "-u", "-m", "pytest_aitest.testing.todo_sdk_mcp"],
            wait=Wait.for_tools(["add_task", "list_tasks"]),
        )
        server = MCPServerProcess(config)

        try:
            await server.start()

            # Add a task
            result = await server.call_tool("add_task", {"title": "SDK test task"})
            assert "SDK test task" in result or "message" in result.lower()

            # List tasks
            result = await server.call_tool("list_tasks", {})
            assert "SDK test task" in result or "[]" in result
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_banking_sdk_mcp_tool_call(self):
        """Can call tools on banking SDK (FastMCP) server."""
        config = MCPServer(
            command=[sys.executable, "-u", "-m", "pytest_aitest.testing.banking_sdk_mcp"],
            wait=Wait.for_tools(["get_balance"]),
        )
        server = MCPServerProcess(config)

        try:
            await server.start()

            # Get balance
            result = await server.call_tool("get_balance", {"account": "checking"})
            assert "balance" in result.lower() or "1500" in result or "1,500" in result
        finally:
            await server.stop()
