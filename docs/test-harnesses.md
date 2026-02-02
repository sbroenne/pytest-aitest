# Test Harnesses

Built-in MCP servers for testing agent behavior without external dependencies.

## Available Test Servers

| Server | Use Case | State |
|--------|----------|-------|
| `WeatherStore` | Basic tool usage | Stateless |
| `TodoStore` | CRUD operations | Stateful |
| `BankingService` | Multi-turn sessions | Stateful |

## WeatherStore

Mock weather data for testing natural language → tool usage.

### Use Case
- "Hello world" tests
- Testing tool selection
- Simple prompt → response validation

### Tools
| Tool | Description |
|------|-------------|
| `get_weather` | Get current weather for a city |
| `get_forecast` | Get multi-day forecast |
| `compare_weather` | Compare weather between cities |
| `list_cities` | List available cities |

### Available Cities
Paris, Tokyo, New York, Berlin, London, Sydney

### Example

```python
from pytest_aitest.testing import WeatherStore
from pytest_aitest.testing.weather_mcp import create_weather_server

@pytest.fixture
async def weather_server():
    """Weather MCP server."""
    server = create_weather_server()
    async with server:
        yield server

@pytest.fixture
def weather_agent(weather_server):
    return Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[weather_server],
    )

async def test_weather(aitest_run, weather_agent):
    result = await aitest_run(
        weather_agent,
        "What's the weather in Paris?"
    )
    
    assert result.success
    assert result.tool_was_called("get_weather")
    assert "paris" in result.final_response.lower()
```

### Direct Usage (without MCP)

```python
from pytest_aitest.testing import WeatherStore

store = WeatherStore()

# Get weather
result = store.get_weather("Paris")
assert result.success
print(result.value)  # {"city": "Paris", "temperature_celsius": 18, ...}

# Get forecast
result = store.get_forecast("Tokyo", days=3)
assert result.success
```

---

## TodoStore

Stateful task management for testing CRUD operations.

### Use Case
- Testing state changes across calls
- Multi-step workflows (add → complete → delete)
- Testing agent's ability to track IDs

### Tools
| Tool | Description |
|------|-------------|
| `add_task` | Create a new task |
| `complete_task` | Mark task as done |
| `delete_task` | Remove a task |
| `list_tasks` | List tasks (optional filtering) |
| `get_task` | Get task by ID |
| `update_task` | Update task properties |

### Example

```python
from pytest_aitest.testing import TodoStore
from pytest_aitest.testing.todo_mcp import create_todo_server

@pytest.fixture
async def todo_server():
    """Todo MCP server with fresh state."""
    server = create_todo_server()
    async with server:
        yield server

@pytest.fixture
def todo_agent(todo_server):
    return Agent(
        provider=Provider(model="azure/gpt-5-mini"),
        mcp_servers=[todo_server],
        system_prompt="You are a task management assistant.",
    )

async def test_add_and_complete(aitest_run, todo_agent):
    # Add task
    result = await aitest_run(
        todo_agent,
        "Add a task: Buy groceries"
    )
    assert result.tool_was_called("add_task")
    
    # Complete it
    result = await aitest_run(
        todo_agent,
        "Mark the groceries task as done"
    )
    assert result.tool_was_called("complete_task")
```

### Direct Usage

```python
from pytest_aitest.testing import TodoStore

store = TodoStore()

# Add task
result = store.add_task("Buy groceries", priority="high")
task_id = result.value["id"]

# Complete it
result = store.complete_task(task_id)
assert result.success

# List all tasks
result = store.list_tasks()
print(result.value["tasks"])
```

---

## BankingService

Realistic banking for testing multi-turn sessions.

### Use Case
- **Session testing**: Context retention across turns
- **Multi-step workflows**: Check balance → transfer → verify
- **State-dependent tests**: Actions change balances

### Tools
| Tool | Description |
|------|-------------|
| `get_balance` | Get balance for one account |
| `get_all_balances` | Get all account balances |
| `transfer` | Transfer between accounts |
| `get_transaction_history` | View recent transactions |
| `deposit` | Deposit to an account |
| `withdraw` | Withdraw from an account |

### Default Accounts
- **Checking**: $1,500.00
- **Savings**: $3,000.00

### Example (Session Test)

```python
from pytest_aitest.testing import BankingService
from pytest_aitest.testing.banking_mcp import create_banking_server

@pytest.fixture(scope="class")
def banking_service():
    """Shared banking state across tests."""
    return BankingService()

@pytest.fixture
async def banking_server(banking_service):
    """MCP server wrapping shared banking service."""
    server = create_banking_server(banking_service)
    async with server:
        yield server

@pytest.fixture(scope="class")
def session():
    """Conversation state."""
    return {"messages": []}

class TestBankingWorkflow:
    async def test_01_check_balances(self, aitest_run, banking_agent, session):
        result = await aitest_run(
            banking_agent,
            "I'm saving for a Paris trip. What are my balances?"
        )
        session["messages"] = result.messages
        assert result.tool_was_called("get_all_balances")
    
    async def test_02_transfer(self, aitest_run, banking_agent, session):
        result = await aitest_run(
            banking_agent,
            "Transfer $500 to savings for that trip.",
            messages=session["messages"],
        )
        session["messages"] = result.messages
        assert result.tool_was_called("transfer")
    
    async def test_03_verify_context(self, aitest_run, banking_agent, session):
        result = await aitest_run(
            banking_agent,
            "What was I saving for?",
            messages=session["messages"],
        )
        # Must remember "Paris" from conversation
        assert "paris" in result.final_response.lower()
```

### Direct Usage

```python
from pytest_aitest.testing import BankingService

bank = BankingService()

# Check balance
result = bank.get_balance("checking")
print(result.value)  # {"account": "checking", "balance": 1500.0, ...}

# Transfer
result = bank.transfer(
    from_account="checking",
    to_account="savings",
    amount=500
)
assert result.success

# Verify new balance
result = bank.get_balance("checking")
assert result.value["balance"] == 1000.0
```

---

## Creating Custom Test Servers

### 1. Create a Store Class

```python
from dataclasses import dataclass
from pytest_aitest.testing.types import ToolResult

@dataclass
class MyStore:
    state: dict = None
    
    def __post_init__(self):
        self.state = self.state or {}
    
    def my_tool(self, arg: str) -> ToolResult:
        """Do something."""
        return ToolResult(
            success=True,
            value={"result": arg.upper()},
        )
```

### 2. Create MCP Server Wrapper

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

def create_my_server(store: MyStore | None = None):
    """Create MCP server wrapping MyStore."""
    store = store or MyStore()
    server = Server("my-server")
    
    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="my_tool",
                description="Do something with input",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "arg": {"type": "string", "description": "Input"},
                    },
                    "required": ["arg"],
                },
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "my_tool":
            result = store.my_tool(arguments["arg"])
            return [TextContent(type="text", text=str(result.value))]
        raise ValueError(f"Unknown tool: {name}")
    
    return server
```

### 3. Use in Tests

```python
@pytest.fixture
async def my_server():
    server = create_my_server()
    async with server:
        yield server

async def test_my_tool(aitest_run, agent_with_my_server):
    result = await aitest_run(agent_with_my_server, "Use my tool")
    assert result.tool_was_called("my_tool")
```

## Best Practices

| Server | Best For | Avoid |
|--------|----------|-------|
| `WeatherStore` | Quick tests, demos | State-dependent tests |
| `TodoStore` | CRUD workflows | Extremely complex logic |
| `BankingService` | Session tests | Simple one-shot tests |
