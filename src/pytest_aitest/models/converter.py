"""Convert legacy dataclass models to Pydantic schema models.

This module provides converters to transform the internal collector dataclasses
to the Pydantic models defined by the JSON schema for serialization.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pytest_aitest.models import (
    AIInsights,
    Assertion,
    FloatStats,
    IntStats,
    Mode,
    Outcome,
    Recommendation,
    Role,
    SuiteSummary,
    TestDimensions,
    TestMetadata,
    TokenUsage,
)
from pytest_aitest.models import AgentResult as PydanticAgentResult
from pytest_aitest.models import SuiteReport as PydanticSuiteReport
from pytest_aitest.models import TestReport as PydanticTestReport
from pytest_aitest.models import ToolCall as PydanticToolCall
from pytest_aitest.models import Turn as PydanticTurn
from pytest_aitest.reporting.aggregator import DimensionAggregator, ReportMode
from pytest_aitest.schema import SCHEMA_VERSION

if TYPE_CHECKING:
    from pytest_aitest.core.result import AgentResult, ToolCall, Turn
    from pytest_aitest.reporting.collector import SuiteReport, TestReport


def convert_tool_call(tc: ToolCall) -> PydanticToolCall:
    """Convert a legacy ToolCall to Pydantic model."""
    return PydanticToolCall(
        name=tc.name,
        arguments=tc.arguments,
        result=tc.result,
        error=tc.error,
        duration_ms=tc.duration_ms,  # Now tracked by engine
    )


def convert_turn(turn: Turn) -> PydanticTurn:
    """Convert a legacy Turn to Pydantic model."""
    role_map = {
        "user": Role.USER,
        "assistant": Role.ASSISTANT,
        "tool": Role.TOOL,
        "system": Role.SYSTEM,
    }
    return PydanticTurn(
        role=role_map.get(turn.role, Role.USER),
        content=turn.content,
        tool_calls=[convert_tool_call(tc) for tc in turn.tool_calls],
    )


def convert_agent_result(result: AgentResult) -> PydanticAgentResult:
    """Convert a legacy AgentResult to Pydantic model."""
    return PydanticAgentResult(
        success=result.success,
        error=result.error,
        duration_ms=result.duration_ms,
        turns=[convert_turn(t) for t in result.turns],
        token_usage=TokenUsage(
            prompt=result.token_usage.get("prompt", 0),
            completion=result.token_usage.get("completion", 0),
            total=result.token_usage.get("prompt", 0) + result.token_usage.get("completion", 0),
        ),
        cost_usd=result.cost_usd,
        final_response=result.final_response,
        tools_called=list(result.tool_names_called),
        session_context_count=result.session_context_count,
        rate_limit_stats=None,  # Not tracked in legacy model
    )


def convert_test_report(test: TestReport) -> PydanticTestReport:
    """Convert a legacy TestReport to Pydantic model."""
    outcome_map = {
        "passed": Outcome.PASSED,
        "failed": Outcome.FAILED,
        "skipped": Outcome.SKIPPED,
    }
    
    # Build metadata from legacy metadata dict
    metadata = TestMetadata(
        model=test.metadata.get("model") if test.metadata else None,
        prompt=test.metadata.get("prompt") if test.metadata else None,
        session=test.metadata.get("session") if test.metadata else None,
        file=test.name.split("::")[0] if "::" in test.name else None,
    )
    
    # Convert assertions
    assertions = None
    if test.assertions:
        assertions = [
            Assertion(
                type=a.get("type", "unknown"),
                passed=a.get("passed", False),
                message=a.get("message"),
                details=a.get("details"),
            )
            for a in test.assertions
        ]
    
    return PydanticTestReport(
        name=test.name,
        outcome=outcome_map.get(test.outcome, Outcome.FAILED),
        duration_ms=test.duration_ms,
        docstring=test.docstring,
        error=test.error,
        error_count=1 if test.error else 0,
        metadata=metadata,
        assertions=assertions,
        agent_result=convert_agent_result(test.agent_result) if test.agent_result else None,
    )


def convert_suite_report(
    report: SuiteReport,
    *,
    insights: AIInsights | None = None,
) -> PydanticSuiteReport:
    """Convert a legacy SuiteReport to Pydantic model.
    
    Args:
        report: Legacy suite report from collector
        insights: AI-generated insights (if None, placeholder is used)
        
    Returns:
        Pydantic SuiteReport model ready for JSON serialization
    """
    # Detect dimensions using aggregator
    aggregator = DimensionAggregator()
    dims = aggregator.detect_dimensions(report)
    
    # Map mode
    mode_map = {
        ReportMode.SIMPLE: Mode.SIMPLE,
        ReportMode.MODEL_COMPARISON: Mode.MODEL_COMPARISON,
        ReportMode.PROMPT_COMPARISON: Mode.PROMPT_COMPARISON,
        ReportMode.MATRIX: Mode.MATRIX,
    }
    
    # Build dimensions
    dimensions = TestDimensions(
        models=dims.models,
        prompts=dims.prompts,
        base_tests=dims.base_tests,
        files=report.test_files if report.test_files else None,
        sessions=None,  # TODO: Extract sessions
    )
    
    # Build summary
    summary = SuiteSummary(
        total=report.total,
        passed=report.passed,
        failed=report.failed,
        skipped=report.skipped,
        pass_rate=report.pass_rate,
        total_tokens=report.total_tokens,
        total_cost_usd=report.total_cost_usd,
        total_tool_calls=report.tool_call_count,
        token_stats=IntStats(**report.token_stats) if report.token_stats else None,
        cost_stats=FloatStats(**report.cost_stats) if report.cost_stats else None,
        duration_stats=FloatStats(**report.duration_stats) if report.duration_stats else None,
    )
    
    # Parse timestamp
    try:
        timestamp = datetime.fromisoformat(report.timestamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        timestamp = datetime.now(timezone.utc)
    
    # Create placeholder insights - will be replaced by AI analysis
    # The placeholder has enough info to be valid but indicates analysis needed
    placeholder_insights = AIInsights(
        recommendation=Recommendation(
            configuration="(analysis pending)",
            summary="AI analysis has not been run yet",
            reasoning="Run with --aitest-html to generate AI-powered insights",
            alternatives=[],
        ),
        failures=[],
        mcp_feedback=[],
        prompt_feedback=[],
        skill_feedback=[],
        optimizations=[],
    )
    
    return PydanticSuiteReport(
        schema_version=SCHEMA_VERSION,
        name=report.name,
        timestamp=timestamp,
        duration_ms=report.duration_ms,
        mode=mode_map.get(dims.mode, Mode.SIMPLE),
        dimensions=dimensions,
        summary=summary,
        insights=insights if insights else placeholder_insights,
        tests=[convert_test_report(t) for t in report.tests],
        analysis_metadata=None,
    )
