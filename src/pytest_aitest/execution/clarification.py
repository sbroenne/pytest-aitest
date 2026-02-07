"""Clarification detection using LLM-as-judge.

Detects when an agent asks for user input instead of executing the requested task.
Uses a separate LLM call to semantically classify each final response.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from typing import Any

import litellm

_logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = (
    "Classify if an AI assistant is asking for user "
    "input BEFORE completing a task.\n"
    "\n"
    "Answer YES if the assistant:\n"
    '- Asks "Would you like me to...", "Should I proceed...", '
    '"Do you want me to..."\n'
    '- Asks "Which would you prefer?", "What format?", "Which option?"\n'
    "- Requests confirmation before doing something: "
    '"Do you want me to proceed?"\n'
    '- Asks for missing information: "What should the filename be?"\n'
    '- Says "I\'m about to..." and then asks for permission\n'
    "- Asks the user to provide, confirm, or clarify something "
    "before acting\n"
    "\n"
    "Answer NO if the response:\n"
    '- STARTS with a checkmark or "Done!" or "Complete" '
    'or "Successfully" (completed work)\n'
    "- Uses past tense to describe actions: "
    '"created", "added", "completed", "saved"\n'
    "- Contains a summary of what was accomplished\n"
    '- Ends with "Let me know if..." AFTER describing completed work\n'
    "- Provides requested information directly "
    "(e.g., account balances, data)\n"
    "\n"
    "CRITICAL RULE: If the response provides the requested information "
    "(even partially), answer NO.\n"
    "\n"
    "Examples:\n"
    '- "Would you like me to check your balance?" → YES\n'
    '- "Should I proceed with the transfer?" → YES\n'
    '- "What account would you like to check?" → YES\n'
    '- "Your checking account balance is $1,500." → NO '
    "(provides information)\n"
    '- "Done! I transferred $100 to savings." → NO (completed work)\n'
    '- "Here are your balances: ... Let me know if you need anything." '
    "→ NO (completed)\n"
    "\n"
    'Respond ONLY "YES" or "NO".'
)


async def check_clarification(
    response_text: str,
    *,
    judge_model: str,
    azure_ad_token_provider: Callable[[], str] | None = None,
    timeout_seconds: float = 10.0,
) -> bool:
    """Check if an agent response is asking for clarification.

    Uses a judge LLM to semantically classify the response. Fails open
    (returns False) on any error, so detection never breaks test execution.

    Args:
        response_text: The agent's final response text to classify.
        judge_model: LiteLLM model string for the judge (e.g., "azure/gpt-5-mini").
        azure_ad_token_provider: Optional Azure AD token provider for auth.
        timeout_seconds: Timeout for the judge LLM call.

    Returns:
        True if the response is asking for clarification, False otherwise.
    """
    if not response_text or not response_text.strip():
        return False

    try:
        async with asyncio.timeout(timeout_seconds):
            kwargs: dict[str, Any] = {
                "model": judge_model,
                "messages": [
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Classify this AI assistant response:\n\n{response_text}",
                    },
                ],
                "max_tokens": 5,
                "temperature": 0.0,
            }

            # Use Azure AD auth if available and model is Azure
            if azure_ad_token_provider and judge_model.startswith("azure/"):
                kwargs["azure_ad_token_provider"] = azure_ad_token_provider

            # Pass through rate limit params if set
            if os.environ.get("AITEST_JUDGE_RPM"):
                kwargs["rpm"] = int(os.environ["AITEST_JUDGE_RPM"])

            response = await litellm.acompletion(**kwargs)

            answer: str = response.choices[0].message.content or ""  # type: ignore[union-attr]
            answer = answer.strip().upper()
            is_clarification = answer.startswith("YES")

            if is_clarification:
                _logger.info(
                    "Clarification detected in response: %s",
                    response_text[:100],
                )

            return is_clarification

    except TimeoutError:
        _logger.debug("Clarification judge timed out after %ss", timeout_seconds)
        return False
    except Exception:
        _logger.debug("Clarification judge failed, skipping detection", exc_info=True)
        return False
