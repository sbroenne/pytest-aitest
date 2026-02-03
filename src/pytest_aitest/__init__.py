"""pytest-aitest: Pytest plugin for testing AI agents with MCP and CLI servers."""

import logging

# Configure library logging per Python best practices:
# https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
# Libraries should add NullHandler to prevent "No handler found" warnings
# when the application hasn't configured logging.
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Core types  # noqa: E402 - logging must be configured before submodule imports
from pytest_aitest.core import (  # noqa: E402
    Agent,
    AgentResult,
    AITestError,
    CLIExecution,
    CLIServer,
    EngineTimeoutError,
    MCPServer,
    Prompt,
    Provider,
    ServerStartError,
    Skill,
    SkillError,
    SkillInfo,
    SkillMetadata,
    ToolCall,
    ToolInfo,
    Turn,
    Wait,
    load_prompt,
    load_prompts,
    load_skill,
)

# Execution
from pytest_aitest.execution import AgentEngine, RetryConfig, ServerManager  # noqa: E402

# Reporting
from pytest_aitest.reporting import (  # noqa: E402
    DimensionAggregator,
    ReportCollector,
    ReportGenerator,
    SuiteReport,
    TestDimensions,
    TestReport,
)

__all__ = [  # noqa: RUF022 - intentionally grouped by category
    # Core
    "Agent",
    "AgentResult",
    "AITestError",
    "CLIExecution",
    "CLIServer",
    "EngineTimeoutError",
    "MCPServer",
    "Prompt",
    "Provider",
    "ServerStartError",
    "Skill",
    "SkillError",
    "SkillInfo",
    "SkillMetadata",
    "ToolCall",
    "ToolInfo",
    "Turn",
    "Wait",
    "load_prompt",
    "load_prompts",
    "load_skill",
    # Execution
    "AgentEngine",
    "RetryConfig",
    "ServerManager",
    # Reporting
    "DimensionAggregator",
    "ReportCollector",
    "ReportGenerator",
    "SuiteReport",
    "TestDimensions",
    "TestReport",
]

__version__ = "0.2.0"
