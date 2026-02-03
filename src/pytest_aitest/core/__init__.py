"""Core module - agent configuration and result types."""

from pytest_aitest.core.agent import (
    Agent,
    CLIExecution,
    CLIServer,
    MCPServer,
    Provider,
    Wait,
)
from pytest_aitest.core.auth import get_azure_ad_token_provider, get_azure_auth_kwargs
from pytest_aitest.core.errors import AITestError, EngineTimeoutError, ServerStartError
from pytest_aitest.core.prompt import Prompt, load_prompt, load_prompts
from pytest_aitest.core.result import AgentResult, SkillInfo, ToolCall, ToolInfo, Turn
from pytest_aitest.core.skill import Skill, SkillError, SkillMetadata, load_skill

__all__ = [
    "Agent",
    "AgentResult",
    "AITestError",
    "CLIExecution",
    "CLIServer",
    "EngineTimeoutError",
    "get_azure_ad_token_provider",
    "get_azure_auth_kwargs",
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
]
