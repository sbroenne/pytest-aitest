"""Serialization helpers for dataclasses to JSON-compatible dicts."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pytest_aitest.reporting.collector import SuiteReport


def serialize_dataclass(obj: Any) -> Any:
    """Convert dataclass to dict recursively, handling special types."""
    if is_dataclass(obj):
        data = asdict(obj)
        return {k: serialize_dataclass(v) for k, v in data.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_dataclass(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_dataclass(v) for k, v in obj.items()}
    else:
        # For enums, strings, numbers, etc.
        return obj


class DictWithAttrAccess(dict):
    """Dict that allows attribute access to keys for backward compatibility."""
    
    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")
    
    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


def to_dict_with_attr(obj: Any) -> Any:
    """Convert dataclass to dict with attribute access support."""
    if is_dataclass(obj):
        data = asdict(obj)
        result = DictWithAttrAccess()
        for k, v in data.items():
            result[k] = to_dict_with_attr(v)
        return result
    elif isinstance(obj, (list, tuple)):
        return [to_dict_with_attr(item) for item in obj]
    elif isinstance(obj, dict):
        result = DictWithAttrAccess()
        for k, v in obj.items():
            result[k] = to_dict_with_attr(v)
        return result
    else:
        return obj


def deserialize_suite_report(data: dict[str, Any]) -> SuiteReport:
    """Deserialize a SuiteReport from a dict (from JSON).
    
    Reconstructs the full dataclass hierarchy from the serialized format.
    """
    from pytest_aitest.core.result import AgentResult, ToolCall, Turn
    from pytest_aitest.reporting.collector import SuiteReport, TestReport
    
    # Reconstruct tests
    tests = []
    for test_data in data.get("tests", []):
        # Reconstruct agent result if present
        agent_result = None
        if test_data.get("agent_result"):
            ar_data = test_data["agent_result"]
            
            # Reconstruct turns
            turns = []
            for turn_data in ar_data.get("turns", []):
                # Reconstruct tool calls
                tool_calls = []
                for tc_data in turn_data.get("tool_calls", []):
                    tool_calls.append(ToolCall(
                        name=tc_data["name"],
                        arguments=tc_data.get("arguments", {}),
                        result=tc_data.get("result"),
                        error=tc_data.get("error"),
                        duration_ms=tc_data.get("duration_ms"),
                    ))
                
                turns.append(Turn(
                    role=turn_data["role"],
                    content=turn_data["content"],
                    tool_calls=tool_calls,
                ))
            
            # Reconstruct agent result
            agent_result = AgentResult(
                turns=turns,
                success=ar_data.get("success", False),
                error=ar_data.get("error"),
                duration_ms=ar_data.get("duration_ms", 0.0),
                token_usage=ar_data.get("token_usage", {}),
                cost_usd=ar_data.get("cost_usd", 0.0),
                session_context_count=ar_data.get("session_context_count", 0),
                agent_name=ar_data.get("agent_name", ""),
                model=ar_data.get("model", ""),
            )
        
        # Reconstruct test report
        test_report = TestReport(
            name=test_data["name"],
            outcome=test_data["outcome"],
            duration_ms=test_data["duration_ms"],
            agent_result=agent_result,
            error=test_data.get("error"),
            assertions=test_data.get("assertions", []),
            metadata=test_data.get("metadata", {}),
            docstring=test_data.get("docstring"),
        )
        tests.append(test_report)
    
    # Reconstruct suite report
    return SuiteReport(
        name=data["name"],
        timestamp=data["timestamp"],
        duration_ms=data["duration_ms"],
        tests=tests,
        passed=data.get("passed", 0),
        failed=data.get("failed", 0),
        skipped=data.get("skipped", 0),
    )

