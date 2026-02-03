"""Reporting module - smart result aggregation and report generation."""

# Re-export insight types from models (generated from JSON schema)
from pytest_aitest.models import (
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
from pytest_aitest.reporting.aggregator import (
    AdaptiveFlags,
    DimensionAggregator,
    GroupedResult,
    MatrixCell,
    ReportMode,
    TestDimensions,
)
from pytest_aitest.reporting.collector import ReportCollector, SuiteReport, TestReport
from pytest_aitest.reporting.generator import (
    ReportGenerator,
    generate_mermaid_sequence,
    generate_session_mermaid,
    get_provider,
)
from pytest_aitest.reporting.insights import (
    InsightsGenerationError,
    create_placeholder_insights,
    generate_insights,
)

__all__ = [  # noqa: RUF022 - intentionally grouped by category
    # Legacy exports (for backward compatibility)
    "AdaptiveFlags",
    "DimensionAggregator",
    "generate_mermaid_sequence",
    "generate_session_mermaid",
    "get_provider",
    "GroupedResult",
    "MatrixCell",
    "ReportCollector",
    "ReportGenerator",
    "ReportMode",
    "SuiteReport",
    "TestDimensions",
    "TestReport",
    # Insights generation
    "create_placeholder_insights",
    "generate_insights",
    "InsightsGenerationError",
    # AI Insight types (from models)
    "AIInsights",
    "AnalysisMetadata",
    "FailureAnalysis",
    "MCPServerFeedback",
    "OptimizationOpportunity",
    "PromptFeedback",
    "Recommendation",
    "SkillFeedback",
    "ToolFeedback",
]
