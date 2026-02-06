"""Azure authentication utilities for LiteLLM.

This module provides shared authentication helpers used by both the agent engine
and the insights generator.
"""

from __future__ import annotations

import functools
import logging
import os
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_logger = logging.getLogger(__name__)


@functools.cache
def get_azure_ad_token_provider() -> Callable[[], str] | None:
    """Get Azure AD token provider for Entra ID authentication.

    Uses LiteLLM's built-in helper which leverages DefaultAzureCredential.
    Cached at module level to avoid recreating credentials on each call.

    Supports:
    - Azure CLI credentials (az login)
    - Managed Identity
    - Environment variables (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, ...)
    - Visual Studio Code credentials

    Returns:
        Token provider callable, or None if not available.
    """
    try:
        from litellm.secret_managers.get_azure_ad_token_provider import (
            get_azure_ad_token_provider as _get_provider,
        )

        return _get_provider()
    except ImportError:
        _logger.debug("azure-identity not installed, Azure AD auth unavailable")
        return None
    except Exception:
        _logger.debug("Azure AD credential not available", exc_info=True)
        return None


def get_azure_auth_kwargs(model: str) -> dict:
    """Get authentication kwargs for LiteLLM completion calls.

    Automatically detects if Azure AD auth is needed based on model prefix
    and environment variables.

    Args:
        model: The LiteLLM model identifier (e.g., "azure/gpt-5-mini")

    Returns:
        Dict with azure_ad_token_provider if needed, empty dict otherwise.
    """
    if not model.startswith("azure/"):
        return {}

    # If API key is set, use that instead of AD auth
    if os.environ.get("AZURE_API_KEY") or os.environ.get("AZURE_OPENAI_API_KEY"):
        return {}

    provider = get_azure_ad_token_provider()
    if provider:
        return {"azure_ad_token_provider": provider}

    return {}
