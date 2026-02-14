"""Adapter between pytest-aitest config types and PydanticAI types.

Converts our Agent/Provider/MCPServer config into PydanticAI Agent + toolsets,
and converts PydanticAI AgentRunResult back into our AgentResult for reporting.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.mcp import MCPServerSSE, MCPServerStdio, MCPServerStreamableHTTP
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.usage import UsageLimits

from pytest_aitest.core.result import AgentResult, SkillInfo, ToolCall, ToolInfo, Turn

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult
    from pydantic_ai.mcp import MCPServer as PydanticMCPServer
    from pydantic_ai.models import Model
    from pydantic_ai.toolsets import AbstractToolset

    from pytest_aitest.core.agent import Agent, MCPServer

_logger = logging.getLogger(__name__)


def build_pydantic_model(agent: Agent) -> Model:
    """Convert our Provider config into a PydanticAI Model instance.

    Handles Azure Entra ID auth (no API key) and standard OpenAI-compatible providers.
    """
    return build_model_from_string(agent.provider.model)


def build_model_from_string(model_str: str) -> Any:
    """Convert a model string (e.g. "azure/gpt-5-mini") to a PydanticAI Model.

    Handles Azure Entra ID auth and standard provider string conversion.
    """
    if model_str.startswith("azure/"):
        return _build_azure_model(model_str)

    # For non-Azure models, use PydanticAI's string-based model resolution
    # Convert our format "provider/model" to pydantic-ai format "provider:model"
    if "/" in model_str:
        provider, model_name = model_str.split("/", 1)
        return f"{provider}:{model_name}"

    return model_str


@functools.lru_cache(maxsize=8)
def _build_azure_model(model_str: str) -> Any:
    """Build an Azure OpenAI model with Entra ID or API key auth.

    Cached to reuse the same AsyncAzureOpenAI client across calls.
    """
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    deployment = model_str.removeprefix("azure/")
    azure_endpoint = os.environ.get("AZURE_API_BASE") or os.environ.get("AZURE_OPENAI_ENDPOINT")
    if not azure_endpoint:
        msg = (
            "AZURE_API_BASE or AZURE_OPENAI_ENDPOINT environment variable is required "
            "for Azure OpenAI models"
        )
        raise ValueError(msg)

    # Check if API key is available
    api_key = os.environ.get("AZURE_API_KEY") or os.environ.get("AZURE_OPENAI_API_KEY")

    if api_key:
        from openai import AsyncAzureOpenAI

        client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version="2024-07-01-preview",
        )
    else:
        # Use Entra ID (DefaultAzureCredential)
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        from openai import AsyncAzureOpenAI

        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            azure_ad_token_provider=token_provider,
            api_version="2024-07-01-preview",
        )

    return OpenAIChatModel(deployment, provider=OpenAIProvider(openai_client=client))


def build_mcp_toolsets(mcp_servers: list[MCPServer]) -> list[PydanticMCPServer]:
    """Convert our MCPServer configs into PydanticAI MCP toolsets."""
    toolsets: list[PydanticMCPServer] = []

    for cfg in mcp_servers:
        match cfg.transport:
            case "stdio":
                env = {**os.environ, **cfg.env} if cfg.env else None
                toolsets.append(
                    MCPServerStdio(
                        cfg.command[0],
                        args=[*cfg.command[1:], *cfg.args],
                        env=env,
                        cwd=cfg.cwd,
                        timeout=cfg.wait.timeout_ms / 1000,
                    )
                )
            case "sse":
                assert cfg.url is not None
                toolsets.append(
                    MCPServerSSE(
                        cfg.url,
                        headers=cfg.headers or None,
                        timeout=cfg.wait.timeout_ms / 1000,
                    )
                )
            case "streamable-http":
                assert cfg.url is not None
                toolsets.append(
                    MCPServerStreamableHTTP(
                        cfg.url,
                        headers=cfg.headers or None,
                        timeout=cfg.wait.timeout_ms / 1000,
                    )
                )

    return toolsets


def build_system_prompt(agent: Agent) -> str | None:
    """Build the complete system prompt with skill content prepended."""
    parts: list[str] = []

    if agent.skill:
        parts.append(agent.skill.content)

    if agent.system_prompt:
        parts.append(agent.system_prompt)

    return "\n\n".join(parts) if parts else None


def build_pydantic_agent(
    agent: Agent,
    toolsets: list[AbstractToolset],
) -> PydanticAgent[None, str]:
    """Create a PydanticAI Agent from our Agent config."""
    model = build_pydantic_model(agent)
    instructions = build_system_prompt(agent)

    # Build model settings
    from pydantic_ai.settings import ModelSettings

    model_settings_kwargs: dict[str, Any] = {}
    if agent.provider.temperature is not None:
        model_settings_kwargs["temperature"] = agent.provider.temperature
    if agent.provider.max_tokens is not None:
        model_settings_kwargs["max_tokens"] = agent.provider.max_tokens

    settings = ModelSettings(**model_settings_kwargs) if model_settings_kwargs else None

    return PydanticAgent(
        model,
        instructions=instructions,
        toolsets=toolsets,
        model_settings=settings,
    )


def build_usage_limits(agent: Agent) -> UsageLimits:
    """Build PydanticAI UsageLimits from our Agent config."""
    return UsageLimits(request_limit=agent.max_turns)


def adapt_result(
    pydantic_result: AgentRunResult[str],
    *,
    start_time: float,
    available_tools: list[ToolInfo],
    skill_info: SkillInfo | None,
    effective_system_prompt: str,
    session_context_count: int = 0,
) -> AgentResult:
    """Convert PydanticAI AgentRunResult into our AgentResult for reporting."""
    duration_ms = (time.perf_counter() - start_time) * 1000

    # Extract usage
    usage = pydantic_result.usage()
    token_usage = {
        "prompt": usage.input_tokens,
        "completion": usage.output_tokens,
    }

    # Convert messages to our Turn format
    turns = _extract_turns(pydantic_result.all_messages())

    # Store PydanticAI messages directly for session continuity
    raw_messages = pydantic_result.all_messages()

    return AgentResult(
        turns=turns,
        success=True,
        duration_ms=duration_ms,
        token_usage=token_usage,
        cost_usd=0.0,  # PydanticAI doesn't provide cost; computed later if needed
        _messages=raw_messages,
        session_context_count=session_context_count,
        available_tools=available_tools,
        skill_info=skill_info,
        effective_system_prompt=effective_system_prompt,
    )


def _extract_turns(messages: list[ModelMessage]) -> list[Turn]:
    """Convert PydanticAI message history into our Turn list.

    Extracts user prompts, assistant text, and tool calls into our Turn format.
    System prompts and tool return parts are intentionally skipped (they're
    infrastructure, not user-visible conversation turns).
    """
    turns: list[Turn] = []

    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, UserPromptPart):
                    content = part.content if isinstance(part.content, str) else str(part.content)
                    turns.append(Turn(role="user", content=content))
                # SystemPromptPart and ToolReturnPart are intentionally skipped
        elif isinstance(msg, ModelResponse):
            tool_calls: list[ToolCall] = []
            text_content = ""

            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    # Parse args — could be string or dict
                    if isinstance(part.args, str):
                        try:
                            arguments = json.loads(part.args)
                        except (json.JSONDecodeError, TypeError):
                            arguments = {"raw": part.args}
                    else:
                        arguments = part.args if isinstance(part.args, dict) else {}

                    # Find matching ToolReturnPart in subsequent messages
                    result_text = _find_tool_result(messages, part.tool_call_id)

                    tool_calls.append(
                        ToolCall(
                            name=part.tool_name,
                            arguments=arguments,
                            result=result_text,
                        )
                    )
                elif isinstance(part, TextPart):
                    text_content += part.content
                else:
                    _logger.debug("Skipping unhandled response part type: %s", type(part).__name__)

            turns.append(Turn(role="assistant", content=text_content, tool_calls=tool_calls))

    return turns


def _find_tool_result(messages: list[ModelMessage], tool_call_id: str | None) -> str | None:
    """Find the result of a tool call by its ID in the message history."""
    if not tool_call_id:
        return None

    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and part.tool_call_id == tool_call_id:
                    return str(part.content)
    return None


def extract_tool_info_from_messages(messages: list[ModelMessage]) -> list[str]:
    """Extract tool names that were called from message history."""
    tool_names: set[str] = set()
    for msg in messages:
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    tool_names.add(part.tool_name)
    return list(tool_names)
