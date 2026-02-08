# MCP Server Implementation Guide

This guide explains how to create MCP servers for pytest-aitest and covers both the hand-rolled JSON-RPC approach and the FastMCP approach.

## Overview

pytest-aitest includes two types of MCP servers for testing:

1. **Hand-rolled JSON-RPC servers** - Full control over MCP protocol
2. **FastMCP servers** - Simpler, declarative approach using the FastMCP framework

Both approaches work perfectly with pytest-aitest. Choose based on your needs:

- Use **FastMCP** for most cases - it's simpler and supports all three transports
- Use **hand-rolled** when you need fine-grained protocol control

## FastMCP Servers (Recommended)

FastMCP servers are the modern approach and are recommended for new servers.

### Example: Todo Server with FastMCP

```python
"""Todo MCP server using FastMCP."""

import argparse
import json
from mcp.server.fastmcp import FastMCP
from your_app import TodoStore

mcp = FastMCP("my-todo-server")
_store = TodoStore()

@mcp.tool()
def add_task(title: str, priority: str = "normal") -> str:
    """Add a new task.
    
    Args:
        title: Task description.
        priority: Task priority ('low', 'normal', 'high').
    """
    result = _store.add_task(title, priority)
    if result.success:
        return json.dumps(result.value)
    return f"Error: {result.error}"

@mcp.tool()
def list_tasks() -> str:
    """List all tasks."""
    result = _store.list_tasks()
    return json.dumps(result.value)

def main():
    """Run server with transport selection."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
    )
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    # Configure FastMCP
    mcp.settings.host = args.host
    mcp.settings.port = args.port

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.run(transport="sse")
    elif args.transport == "streamable-http":
        mcp.settings.stateless_http = True
        mcp.settings.json_response = True
        mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()
```

### Transport Support

FastMCP servers support all three transports:

```bash
# stdio (default) - for local subprocess
python -m your_module.server

# SSE - for remote HTTP connections
python -m your_module.server --transport sse --port 8080

# Streamable HTTP - for production HTTP
python -m your_module.server --transport streamable-http --port 8080
```

## Hand-rolled JSON-RPC Servers

For cases where you need fine control over the MCP protocol:

### Example: Banking Server with Hand-rolled JSON-RPC

```python
"""Banking MCP server with hand-rolled JSON-RPC."""

import asyncio
import json
import sys
from typing import Any

class BankingMCPServer:
    def __init__(self):
        self.service = BankingService()

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "banking-server", "version": "1.0.0"},
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.service.get_tool_schemas()},
            }

        if method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = await self.service.call_tool_async(tool_name, arguments)
            
            content = [{"type": "text", "text": json.dumps(result.value)}]
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": content, "isError": not result.success},
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    def run_sync(self):
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = asyncio.run(self.handle_request(request))
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
```

## Using MCP Servers in Tests

### stdio Transport (Most Common)

```python
from pytest_aitest import Agent, MCPServer, Provider, Wait

# Hand-rolled server
todo_server = MCPServer(
    command=["python", "-m", "your_app.todo_mcp"],
    wait=Wait.for_tools(["add_task", "list_tasks"]),
)

# FastMCP server (same usage)
todo_server = MCPServer(
    command=["python", "-m", "your_app.todo_sdk_mcp"],
    wait=Wait.for_tools(["add_task", "list_tasks"]),
)

agent = Agent(
    provider=Provider(model="azure/gpt-5-mini"),
    mcp_servers=[todo_server],
    system_prompt="You are a todo assistant.",
)

result = await aitest_run(agent, "Add task 'Buy milk'")
assert result.tool_was_called("add_task")
```

### SSE and Streamable HTTP Transports

```python
# Start server as subprocess with specific transport
import subprocess
import sys

port = 8080
proc = subprocess.Popen([
    sys.executable, "-m", "your_app.todo_sdk_mcp",
    "--transport", "sse",
    "--port", str(port),
])

# Connect via SSE
todo_server = MCPServer(
    transport="sse",
    url=f"http://127.0.0.1:{port}/sse",
    wait=Wait.for_tools(["add_task", "list_tasks"]),
)

# Or streamable-http
todo_server = MCPServer(
    transport="streamable-http",
    url=f"http://127.0.0.1:{port}/mcp",
    wait=Wait.for_tools(["add_task", "list_tasks"]),
)
```

## Testing Your MCP Server

### Unit Tests (No LLM)

```python
import pytest
from pytest_aitest import MCPServer, Wait
from pytest_aitest.execution.servers import MCPServerProcess

@pytest.mark.asyncio
async def test_server_starts_and_lists_tools():
    config = MCPServer(
        command=["python", "-m", "your_app.server"],
        wait=Wait.for_tools(["tool1", "tool2"]),
    )
    server = MCPServerProcess(config)
    
    try:
        await server.start()
        tools = server.get_tools()
        assert "tool1" in tools
        assert "tool2" in tools
    finally:
        await server.stop()

@pytest.mark.asyncio
async def test_tool_call():
    config = MCPServer(
        command=["python", "-m", "your_app.server"],
        wait=Wait.for_tools(["add_task"]),
    )
    server = MCPServerProcess(config)
    
    try:
        await server.start()
        result = await server.call_tool("add_task", {"title": "Test"})
        assert "Test" in result
    finally:
        await server.stop()
```

### Integration Tests (With LLM)

```python
from pytest_aitest import Agent, MCPServer, Provider

async def test_agent_uses_server(aitest_run):
    server = MCPServer(
        command=["python", "-m", "your_app.server"],
        wait=Wait.for_tools(["add_task"]),
    )
    
    agent = Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[server],
        system_prompt="You are a helpful assistant.",
    )
    
    result = await aitest_run(agent, "Add a task called 'Buy milk'")
    assert result.success
    assert result.tool_was_called("add_task")
```

## Best Practices

1. **Always include Wait configuration** - Ensures server is ready before tests
2. **Use Wait.for_tools()** - More reliable than time-based waits
3. **Implement proper error handling** - Return errors as tool results, not exceptions
4. **Keep tools focused** - One clear purpose per tool
5. **Add good descriptions** - LLMs rely on tool descriptions
6. **Return JSON strings** - Consistent format for all tools
7. **Test without LLM first** - Unit tests catch infrastructure issues

## Examples in pytest-aitest

The repository includes four reference servers:

| Server | Type | File |
|--------|------|------|
| Todo (hand-rolled) | JSON-RPC | `src/pytest_aitest/testing/todo_mcp.py` |
| Todo (FastMCP) | FastMCP | `src/pytest_aitest/testing/todo_sdk_mcp.py` |
| Banking (hand-rolled) | JSON-RPC | `src/pytest_aitest/testing/banking_mcp.py` |
| Banking (FastMCP) | FastMCP | `src/pytest_aitest/testing/banking_sdk_mcp.py` |

All four servers are tested in `tests/unit/test_mcp_servers.py`.

## Migration Guide

If you have a hand-rolled JSON-RPC server and want to migrate to FastMCP:

1. **Install FastMCP** (included in `mcp` package)
2. **Convert handlers to @mcp.tool() decorators**
3. **Add transport CLI args** (see examples above)
4. **Test with existing tests** - should work without changes
5. **Update documentation** - note the new transport options

The migration is non-breaking - both server types can coexist in your codebase.
