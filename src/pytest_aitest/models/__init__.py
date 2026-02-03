"""Pydantic models for pytest-aitest.

This module exports the extended models with computed properties.
The base models are auto-generated from schema/report.schema.json.
"""

# Re-export all generated types
from ._generated import (
    # Enums
    Category,
    Effectiveness,
    Impact,
    Mode,
    Outcome,
    Role,
    Severity,
    Status,
    # Stats
    FloatStats,
    IntStats,
    # Core types
    Assertion,
    RateLimitStats,
    SuiteSummary,
    TestDimensions,
    TestMetadata,
    TokenUsage,
    ToolCall,
    Turn,
    # AI Insights (new in v3.0)
    AIInsights,
    AnalysisMetadata,
    FailureAnalysis,
    MCPServerFeedback,
    OptimizationOpportunity,
    PromptFeedback,
    Recommendation,
    SkillFeedback,
    ToolFeedback,
)

# Export extended models (these shadow the generated ones)
from .extensions import AgentResult, SuiteReport, TestReport

__all__ = [
    # Enums
    "Category",
    "Effectiveness",
    "Impact",
    "Mode",
    "Outcome",
    "Role",
    "Severity",
    "Status",
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
    # AI Insights (new in v3.0)
    "AIInsights",
    "AnalysisMetadata",
    "FailureAnalysis",
    "MCPServerFeedback",
    "OptimizationOpportunity",
    "PromptFeedback",
    "Recommendation",
    "SkillFeedback",
    "ToolFeedback",
    # Main models (extended)
    "AgentResult",
    "TestReport",
    "SuiteReport",
]
