"""Report generation with htpy components."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pytest_aitest.core.serialization import serialize_dataclass
from pytest_aitest.reporting.components import full_report
from pytest_aitest.reporting.components.types import (
    AgentData,
    AgentStats,
    AIInsightsData,
    AssertionData,
    ReportContext,
    ReportMetadata,
    TestData,
    TestGroupData,
    TestResultData,
    ToolCallData,
)

if TYPE_CHECKING:
    from pytest_aitest.core.result import AgentResult
    from pytest_aitest.reporting.collector import SuiteReport


def get_provider(model_name: str) -> str:
    """Extract provider name from model string for badge styling."""
    model_lower = model_name.lower()
    if "azure" in model_lower:
        return "azure"
    elif "openai" in model_lower or model_lower.startswith("gpt"):
        return "openai"
    elif "anthropic" in model_lower or "claude" in model_lower:
        return "anthropic"
    elif "vertex" in model_lower or "gemini" in model_lower:
        return "vertex"
    return "default"


def _sanitize_mermaid_text(text: str, limit: int) -> str:
    cleaned = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    cleaned = cleaned.replace('"', "'")
    cleaned = " ".join(cleaned.split())
    return cleaned[:limit]


def _to_file_url(path: str) -> str:
    return Path(path).resolve().as_uri()


def _get_metadata_field(metadata: Any | dict | None, field: str) -> Any:
    """Safely get a field from metadata (handles both objects and dicts)."""
    if not metadata:
        return None
    if isinstance(metadata, dict):
        return metadata.get(field)
    return getattr(metadata, field, None)


class ReportGenerator:
    """Generates HTML and JSON reports using htpy components.

    Example:
        generator = ReportGenerator()
        generator.generate_html(suite_report, "report.html")
        generator.generate_json(suite_report, "report.json")
    """
    
    @staticmethod
    def _format_cost(cost: float) -> str:
        """Format cost in USD."""
        if cost == 0:
            return "N/A"
        if cost < 0.01:
            return f"${cost:.6f}"
        return f"${cost:.4f}"

    def generate_html(
        self,
        report: SuiteReport,
        output_path: str | Path,
        *,
        ai_summary: str | None = None,  # DEPRECATED
        insights: Any | None = None,
    ) -> None:
        """Generate HTML report from test results and AI insights.

        Args:
            report: Test suite report data (dataclass)
            output_path: Path to write HTML file
            ai_summary: DEPRECATED - use insights parameter instead
            insights: AIInsights object (if None, placeholder is used)
        """
        # Build typed data structures for htpy components
        context = self._build_report_context(report, insights=insights)
        
        # Render with htpy - htpy automatically outputs doctype lowercase
        html_node = full_report(context)
        html_str = str(html_node)
        Path(output_path).write_text(html_str, encoding="utf-8")
    
    def _build_report_context(
        self, 
        report: SuiteReport, 
        *, 
        insights: Any | None = None,
    ) -> ReportContext:
        """Build typed ReportContext from SuiteReport."""
        # Build report metadata
        ts = report.timestamp
        timestamp_str = ts.isoformat() if isinstance(ts, datetime) else str(ts)
        
        # Get analysis cost from insights dict if available
        analysis_cost = None
        if insights and isinstance(insights, dict):
            analysis_cost = insights.get('cost_usd')
        
        report_meta = ReportMetadata(
            name=report.name,
            timestamp=timestamp_str,
            passed=report.passed,
            failed=report.failed,
            total=report.total,
            duration_ms=report.duration_ms or 0,
            total_cost_usd=report.total_cost_usd or 0,
            suite_docstring=getattr(report, 'suite_docstring', None),
            analysis_cost_usd=analysis_cost,
        )
        
        # Build agents
        agents, agents_by_id = self._build_agents(report)
        all_agent_ids = [a.id for a in agents]
        selected_agent_ids = [a.id for a in agents[:2]]
        
        # Build test groups
        test_groups = self._build_test_groups_typed(report, all_agent_ids, agents_by_id)
        
        # Build AI insights from passed-in insights dict
        insights_data = None
        if insights and isinstance(insights, dict):
            markdown_summary = insights.get('markdown_summary')
            if markdown_summary:
                insights_data = AIInsightsData(markdown_summary=markdown_summary)
        
        return ReportContext(
            report=report_meta,
            agents=agents,
            agents_by_id=agents_by_id,
            all_agent_ids=all_agent_ids,
            selected_agent_ids=selected_agent_ids,
            test_groups=test_groups,
            total_tests=len(report.tests),
            insights=insights_data,
        )
    
    def _build_agents(self, report: SuiteReport) -> tuple[list[AgentData], dict[str, AgentData]]:
        """Build agent data from test results."""
        from collections import defaultdict
        
        # Group tests by agent identity
        agent_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "cost": 0.0,
            "tokens": 0,
            "duration_ms": 0,
            "skill": None,
            "prompt_name": None,
            "model": None,
        })
        
        for test in report.tests:
            model = _get_metadata_field(test.metadata, "model") or "unknown"
            skill = _get_metadata_field(test.metadata, "skill")
            prompt_name = _get_metadata_field(test.metadata, "system_prompt")
            
            agent_id = model
            if skill:
                agent_id += f"+{skill}"
            if prompt_name:
                agent_id += f"+{prompt_name}"
            
            stats = agent_stats[agent_id]
            stats["model"] = model
            stats["skill"] = skill
            stats["prompt_name"] = prompt_name
            stats["total"] += 1
            
            if test.outcome == "passed":
                stats["passed"] += 1
            else:
                stats["failed"] += 1
            
            if test.duration_ms:
                stats["duration_ms"] += test.duration_ms
            
            if test.agent_result:
                if test.agent_result.cost_usd:
                    stats["cost"] += test.agent_result.cost_usd
                if test.agent_result.token_usage:
                    usage = test.agent_result.token_usage
                    stats["tokens"] += usage.get("prompt", 0) + usage.get("completion", 0)
        
        # Build typed agents list
        agents = []
        for agent_id, stats in agent_stats.items():
            total = stats["total"]
            passed = stats["passed"]
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            agents.append(AgentData(
                id=agent_id,
                name=stats["model"],
                skill=stats["skill"],
                prompt_name=stats["prompt_name"],
                passed=passed,
                failed=stats["failed"],
                total=total,
                pass_rate=pass_rate,
                cost=stats["cost"],
                tokens=stats["tokens"],
                duration_s=stats["duration_ms"] / 1000,
            ))
        
        # Sort by pass rate (desc), then cost (asc)
        agents.sort(key=lambda a: (-a.pass_rate, a.cost))
        
        # Mark winner
        if agents:
            agents[0] = AgentData(
                id=agents[0].id,
                name=agents[0].name,
                skill=agents[0].skill,
                prompt_name=agents[0].prompt_name,           
                passed=agents[0].passed,
                failed=agents[0].failed,
                total=agents[0].total,
                pass_rate=agents[0].pass_rate,
                cost=agents[0].cost,
                tokens=agents[0].tokens,
                duration_s=agents[0].duration_s,
                is_winner=True,
            )
        
        agents_by_id = {a.id: a for a in agents}
        return agents, agents_by_id
    
    def _build_test_groups_typed(
        self,
        report: SuiteReport,
        all_agent_ids: list[str],
        agents_by_id: dict[str, AgentData],
    ) -> list[TestGroupData]:
        """Build typed test groups for htpy components."""
        from collections import defaultdict
        
        # Group tests by session (class name) and base test name
        test_groups: dict[str, dict[str, list[Any]]] = defaultdict(lambda: defaultdict(list))
        
        for test in report.tests:
            parts = test.name.split("::")
            if len(parts) >= 2:
                class_name = parts[-2]
                test_name = parts[-1].split("[")[0]
            else:
                class_name = "standalone"
                test_name = parts[-1].split("[")[0]
            
            test_groups[class_name][test_name].append(test)
        
        # Build result structure
        result = []
        for group_name, tests_by_name in test_groups.items():
            is_session = group_name.startswith("Test") and len(tests_by_name) > 1
            
            test_list = []
            for test_name, test_variants in tests_by_name.items():
                results_by_agent: dict[str, TestResultData] = {}
                has_difference = False
                has_failed = False
                outcomes = set()
                first_test = test_variants[0] if test_variants else None
                
                for test in test_variants:
                    model = _get_metadata_field(test.metadata, "model") or "unknown"
                    skill = _get_metadata_field(test.metadata, "skill")
                    prompt_name = _get_metadata_field(test.metadata, "system_prompt")
                    
                    agent_id = model
                    if skill:
                        agent_id += f"+{skill}"
                    if prompt_name:
                        agent_id += f"+{prompt_name}"
                    
                    if agent_id in all_agent_ids:
                        outcome = test.outcome or "unknown"
                        outcomes.add(outcome)
                        
                        if outcome != "passed":
                            has_failed = True
                        
                        # Extract tool calls
                        tool_calls = []
                        if test.agent_result and test.agent_result.turns:
                            for turn in test.agent_result.turns:
                                if turn.tool_calls:
                                    for tc in turn.tool_calls:
                                        tool_calls.append(ToolCallData(
                                            name=tc.name,
                                            success=tc.error is None,
                                            error=tc.error,
                                            args=tc.arguments,
                                            result=tc.result,
                                        ))
                        
                        # Extract assertions
                        assertions_data = []
                        if test.assertions:
                            for a in test.assertions:
                                if hasattr(a, 'type'):
                                    assertions_data.append(AssertionData(
                                        type=a.type,
                                        passed=a.passed,
                                        message=a.message or "",
                                        details=a.details,
                                    ))
                                else:
                                    assertions_data.append(AssertionData(
                                        type=a.get("type", "unknown"),
                                        passed=a.get("passed", True),
                                        message=a.get("message", ""),
                                        details=a.get("details"),
                                    ))
                        
                        duration_ms = test.duration_ms or 0
                        has_result = test.agent_result and test.agent_result.turns
                        turn_count = len(test.agent_result.turns) if has_result else 0
                        tokens = 0
                        if test.agent_result and test.agent_result.token_usage:
                            usage = test.agent_result.token_usage
                            tokens = usage.get("prompt", 0) + usage.get("completion", 0)
                        
                        agent_result = test.agent_result
                        mermaid = generate_mermaid_sequence(agent_result) if agent_result else None
                        final_resp = agent_result.final_response if agent_result else None
                        results_by_agent[agent_id] = TestResultData(
                            outcome=outcome,
                            passed=outcome == "passed",
                            duration_s=duration_ms / 1000,
                            tokens=tokens,
                            cost=agent_result.cost_usd if agent_result else 0,
                            tool_calls=tool_calls,
                            tool_count=len(tool_calls),
                            turns=turn_count,
                            mermaid=mermaid,
                            final_response=final_resp,
                            error=test.error,
                            assertions=assertions_data,
                        )
                
                if len(outcomes) > 1:
                    has_difference = True
                
                display_name = test_name
                if first_test and hasattr(first_test, 'docstring') and first_test.docstring:
                    first_line = first_test.docstring.split('\n')[0].strip()
                    if first_line:
                        display_name = first_line[:60] + ("…" if len(first_line) > 60 else "")
                
                test_list.append(TestData(
                    id=test_name,
                    display_name=display_name,
                    results_by_agent=results_by_agent,
                    has_difference=has_difference,
                    has_failed=has_failed,
                ))
            
            # Calculate group-level stats per agent
            agent_stats: dict[str, AgentStats] = {}
            for agent_id in all_agent_ids:
                passed = sum(
                    1 for t in test_list 
                    if t.results_by_agent.get(agent_id) 
                    and t.results_by_agent[agent_id].outcome == "passed"
                )
                failed = sum(
                    1 for t in test_list 
                    if t.results_by_agent.get(agent_id) 
                    and t.results_by_agent[agent_id].outcome != "passed"
                )
                agent_stats[agent_id] = AgentStats(passed=passed, failed=failed)
            
            result.append(TestGroupData(
                type="session" if is_session else "standalone",
                name=group_name,
                tests=test_list,
                agent_stats=agent_stats,
            ))
        
        return result

    def generate_json(
        self,
        report: SuiteReport,
        output_path: str | Path,
        *,
        ai_summary: str | None = None,  # DEPRECATED
        insights: Any | None = None,
    ) -> None:
        """Generate JSON report from dataclass.

        Args:
            report: Test suite report data
            output_path: Path to write JSON file
            ai_summary: DEPRECATED - use insights parameter instead
            insights: AIInsights object (if None, placeholder is used)
        """
        import json

        
        # Serialize dataclass to dict
        report_dict = serialize_dataclass(report)
        json_str = json.dumps(report_dict, indent=2, default=str)
        Path(output_path).write_text(json_str, encoding="utf-8")




def generate_mermaid_sequence(result: AgentResult) -> str:
    """Generate Mermaid sequence diagram from agent result.

    Example output:
        sequenceDiagram
            participant User
            participant Agent
            participant Tools

            User->>Agent: Hello!
            Agent->>Tools: read_file(path="/tmp/test.txt")
            Tools-->>Agent: File contents...
            Agent->>User: Here is the file...
    """
    lines = [
        "sequenceDiagram",
        "    participant User",
        "    participant Agent",
        "    participant Tools",
        "",
    ]

    for turn in result.turns:
        if turn.role == "user":
            content = _sanitize_mermaid_text(turn.content, 80)
            lines.append(f'    User->>Agent: "{content}"')

        elif turn.role == "assistant":
            if turn.tool_calls:
                for tc in turn.tool_calls:
                    args_preview = _sanitize_mermaid_text(str(tc.arguments), 60)
                    lines.append(f'    Agent->>Tools: "{tc.name}({args_preview})"')
                    if tc.error:
                        err_preview = _sanitize_mermaid_text(str(tc.error), 60)
                        lines.append(f'    Tools--xAgent: "Error: {err_preview}"')
                    elif tc.result:
                        result_preview = _sanitize_mermaid_text(tc.result, 60)
                        lines.append(f'    Tools-->>Agent: "{result_preview}"')
            else:
                content = _sanitize_mermaid_text(turn.content, 80)
                lines.append(f'    Agent->>User: "{content}"')

    return "\n".join(lines)


def generate_session_mermaid(session: Any) -> str:
    """Generate Mermaid sequence diagram showing session workflow.

    Shows how tests in a session build on each other's conversation context.

    Example output:
        sequenceDiagram
            participant Test1 as test_step1
            participant Test2 as test_step2
            participant Agent

            Test1->>Agent: Initial prompt
            Agent-->>Test1: Response (3 tool calls)
            Note over Test1,Test2: Context: 4 messages
            Test2->>Agent: Follow-up prompt
            Agent-->>Test2: Response (2 tool calls)
    """
    if not session.tests:
        return ""

    lines = ["sequenceDiagram"]

    # Add participants for each test
    for i, test in enumerate(session.tests):
        test_name = test.name.split("::")[-1]
        lines.append(f"    participant T{i} as {test_name}")
    lines.append("    participant Agent")
    lines.append("")

    # Show flow between tests
    for i, test in enumerate(session.tests):
        result = test.agent_result
        if not result:
            continue

        # Get prompt (first user message in this test's turns)
        prompt = "..."
        for turn in result.turns:
            if turn.role == "user":
                prompt = _sanitize_mermaid_text(turn.content, 50)
                break

        # Test sends prompt to agent
        lines.append(f'    T{i}->>Agent: "{prompt}"')

        # Agent responds
        tool_count = len(result.all_tool_calls)
        if tool_count > 0:
            lines.append(f"    Agent-->>T{i}: Response ({tool_count} tool calls)")
        else:
            lines.append(f"    Agent-->>T{i}: Response")

        # Show context carried to next test
        if i < len(session.tests) - 1:
            ctx_count = result.session_context_count if result else 0
            msg_count = len(result.messages) if result else 0
            delta = msg_count - ctx_count
            lines.append(f"    Note over T{i},T{i + 1}: +{delta} msgs → {msg_count} total")

    return "\n".join(lines)
