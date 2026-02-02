"""Pydantic models for pytest-aitest.

This module exports the extended models with computed properties.
The base models are auto-generated from schema/report.schema.json.
"""

# Re-export all generated types
from ._generated import (
    Assertion,
    FloatStats,
    IntStats,
    Mode,
    Outcome,
    RateLimitStats,
    Role,
    SuiteSummary,
    TestDimensions,
    TestMetadata,
    TokenUsage,
    ToolCall,
    Turn,
)

# Export extended models (these shadow the generated ones)
from .extensions import AgentResult, SuiteReport, TestReport

__all__ = [
    # Enums
    "Mode",
    "Outcome",
    "Role",
    # Stats
    "IntStats",
    "FloatStats",
    # Core types
    "ToolCall",
    "Turn",
    "TokenUsage",
    "RateLimitStats",
    "Assertion",
    "TestMetadata",
    "TestDimensions",
    "SuiteSummary",
    # Main models (extended)
    "AgentResult",
    "TestReport",
    "SuiteReport",
]
