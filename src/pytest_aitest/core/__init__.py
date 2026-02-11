"""Core module - agent configuration and result types."""

from pytest_aitest.core.agent import (
    Agent,
    ClarificationDetection,
    ClarificationLevel,
    CLIExecution,
    CLIServer,
    GitHubCopilotServer,
    MCPServer,
    Provider,
    Wait,
)
from pytest_aitest.core.auth import get_azure_ad_token_provider, get_azure_auth_kwargs
from pytest_aitest.core.errors import AITestError, EngineTimeoutError, ServerStartError
from pytest_aitest.core.prompt import Prompt, load_prompt, load_prompts, load_system_prompts
from pytest_aitest.core.result import (
    AgentResult,
    ClarificationStats,
    SkillInfo,
    ToolCall,
    ToolInfo,
    Turn,
)
from pytest_aitest.core.skill import Skill, SkillError, SkillMetadata, load_skill

__all__ = [
    "AITestError",
    "Agent",
    "AgentResult",
    "CLIExecution",
    "CLIServer",
    "ClarificationDetection",
    "ClarificationLevel",
    "ClarificationStats",
    "EngineTimeoutError",
    "GitHubCopilotServer",
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
    "get_azure_ad_token_provider",
    "get_azure_auth_kwargs",
    "load_prompt",
    "load_prompts",
    "load_skill",
    "load_system_prompts",
]
