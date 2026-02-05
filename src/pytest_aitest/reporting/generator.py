"""Report generation with composable renderers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from pytest_aitest.core.serialization import serialize_dataclass, to_dict_with_attr

if TYPE_CHECKING:
    from pytest_aitest.core.result import AgentResult
    from pytest_aitest.reporting.collector import SuiteReport


def _render_markdown(text: str) -> Markup:
    """Convert markdown to HTML, sanitized for safe output."""
    try:
        import markdown

        html = markdown.markdown(text, extensions=["extra"])
        return Markup(html)
    except ImportError:
        # Fallback: basic line break handling if markdown not installed
        import html

        escaped = html.escape(text)
        return Markup(escaped.replace("\n", "<br>"))


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


def generate_mermaid_sequence_pydantic(result: Any) -> str:
    """Generate Mermaid sequence diagram from Pydantic AgentResult.
    
    Works with pytest_aitest.models.AgentResult (Pydantic model).
    """
    if result is None:
        return ""
    
    lines = [
        "sequenceDiagram",
        "    participant User",
        "    participant Agent",
        "    participant Tools",
        "",
    ]

    for turn in result.turns:
        role = turn.role.value if hasattr(turn.role, 'value') else str(turn.role)
        
        if role == "user":
            content = _sanitize_mermaid_text(turn.content, 80)
            lines.append(f'    User->>Agent: "{content}"')

        elif role == "assistant":
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


def _get_metadata_field(metadata: Any | dict | None, field: str) -> Any:
    """Safely get a field from metadata (handles both objects and dicts)."""
    if not metadata:
        return None
    if isinstance(metadata, dict):
        return metadata.get(field)
    return getattr(metadata, field, None)


class ReportGenerator:
    """Generates HTML and JSON reports with smart layout selection.

    Automatically chooses the best report layout based on detected test dimensions:
    - Simple: Standard test list
    - Model comparison: Side-by-side model comparison table
    - Prompt comparison: Prompt variant comparison
    - Matrix: 2D grid of models x prompts

    Example:
        generator = ReportGenerator()
        generator.generate_html(suite_report, "report.html")
        generator.generate_json(suite_report, "report.json")
    """

    def __init__(self) -> None:
        # Use importlib.resources to find templates directory reliably
        import importlib.resources as resources

        templates_dir = resources.files("pytest_aitest").joinpath("templates")
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True,
        )
        self._env.filters["markdown"] = _render_markdown

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
        
        # Convert dataclass to dict with attribute access support for templates
        report_dict = to_dict_with_attr(report)
        
        # Build agent comparison data (groups tests by agent identity)
        agents_data = self._build_agents_data(report)
        all_agent_ids = [a["id"] for a in agents_data["agents"]]
        
        # Prepare template context
        context: dict[str, Any] = {
            "report": report_dict,
            "format_cost": self._format_cost,
            "generate_mermaid": generate_mermaid_sequence,
            "get_provider": get_provider,
            "to_file_url": _to_file_url,
            # AI insights (always provided, may be placeholder)
            "insights": serialize_dataclass(report_dict.get("insights", {})),
            # Agent comparison data
            "agents": agents_data["agents"],
            "agents_by_id": agents_data["agents_by_id"],
            "selected_agent_ids": agents_data["selected_agent_ids"],
            "all_agent_ids": all_agent_ids,
            "test_groups": self._build_test_groups(report, all_agent_ids),
            "total_tests": len(report.tests),
        }

        template = self._env.get_template("report.html")
        html = template.render(**context)
        Path(output_path).write_text(html, encoding="utf-8")
    
    @staticmethod
    def _format_cost(cost: float) -> str:
        """Format cost in USD."""
        if cost == 0:
            return "N/A"
        if cost < 0.01:
            return f"${cost:.6f}"
        return f"${cost:.4f}"
    
    def _build_agents_data(self, report: Any) -> dict[str, Any]:
        """Build agent data for the agent comparison view.
        
        Returns:
            dict with:
            - agents: list of agent dicts with metrics
            - agents_by_id: dict mapping agent_id to agent data
            - selected_agent_ids: list of 2 agent IDs to compare (top performers)
        """
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
            # Build agent identity from model + skill + prompt
            model = _get_metadata_field(test.metadata, "model") or "unknown"
            skill = _get_metadata_field(test.metadata, "skill")
            prompt_name = _get_metadata_field(test.metadata, "system_prompt")
            
            # Create a unique agent ID
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
            
            # outcome is already a string ("passed", "failed", "skipped")
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
                    # token_usage is a dict[str, int] with "prompt" and "completion" keys
                    stats["tokens"] += usage.get("prompt", 0) + usage.get("completion", 0)
        
        # Build agents list with computed metrics
        agents = []
        for agent_id, stats in agent_stats.items():
            total = stats["total"]
            passed = stats["passed"]
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            agents.append({
                "id": agent_id,
                "name": stats["model"],
                "skill": stats["skill"],
                "prompt_name": stats["prompt_name"],
                "passed": passed,
                "failed": stats["failed"],
                "total": total,
                "pass_rate": pass_rate,
                "cost": stats["cost"],
                "tokens": stats["tokens"],
                "duration_s": stats["duration_ms"] / 1000,
            })
        
        # Sort by pass rate (desc), then cost (asc) for winner determination
        agents.sort(key=lambda a: (-a["pass_rate"], a["cost"]))
        
        # Mark winner
        if agents:
            agents[0]["is_winner"] = True
        
        # Build lookup by ID
        agents_by_id = {a["id"]: a for a in agents}
        
        # Select top 2 for default comparison
        selected_agent_ids = [a["id"] for a in agents[:2]]
        
        return {
            "agents": agents,
            "agents_by_id": agents_by_id,
            "selected_agent_ids": selected_agent_ids,
        }
    
    def _extract_assertions(self, test: Any) -> list[dict[str, Any]]:
        """Extract assertions from a test result.
        
        Returns list of dicts with:
        - type: assertion type (tool_called, contains, etc.)
        - passed: bool
        - message: assertion message
        - details: optional details
        """
        if not test.assertions:
            return []
        
        result = []
        for assertion in test.assertions:
            # Handle both Pydantic Assertion objects and dicts
            if hasattr(assertion, 'type'):
                result.append({
                    "type": assertion.type,
                    "passed": assertion.passed,
                    "message": assertion.message or "",
                    "details": assertion.details,
                })
            else:
                result.append({
                    "type": assertion.get("type", "unknown"),
                    "passed": assertion.get("passed", True),
                    "message": assertion.get("message", ""),
                    "details": assertion.get("details"),
                })
        return result

    def _build_test_groups(self, report: Any, selected_agent_ids: list[str]) -> list[dict[str, Any]]:
        """Build test groups for the comparison view.
        
        Groups tests by session (class) and builds per-agent results.
        
        Returns:
            List of group dicts with:
            - type: "session" or "standalone"
            - name: group display name
            - tests: list of test dicts with results_by_agent
        """
        from collections import defaultdict
        
        # Group tests by session (class name) and base test name
        test_groups: dict[str, dict[str, list[Any]]] = defaultdict(lambda: defaultdict(list))
        
        for test in report.tests:
            # Extract class name and test name from full path
            parts = test.name.split("::")
            if len(parts) >= 2:
                class_name = parts[-2]
                test_name = parts[-1].split("[")[0]  # Remove params
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
                # Build results for each selected agent
                results_by_agent = {}
                has_difference = False
                has_failed = False
                outcomes = set()
                first_test = test_variants[0] if test_variants else None
                
                for test in test_variants:
                    # Determine agent ID
                    model = _get_metadata_field(test.metadata, "model") or "unknown"
                    skill = _get_metadata_field(test.metadata, "skill")
                    prompt_name = _get_metadata_field(test.metadata, "system_prompt")
                    
                    agent_id = model
                    if skill:
                        agent_id += f"+{skill}"
                    if prompt_name:
                        agent_id += f"+{prompt_name}"
                    
                    if agent_id in selected_agent_ids:
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
                                        tool_calls.append({
                                            "name": tc.name,
                                            "success": tc.error is None,
                                            "error": tc.error,
                                            "args": tc.arguments,
                                            "result": tc.result,
                                        })
                        
                        duration_ms = test.duration_ms or 0
                        turn_count = len(test.agent_result.turns) if test.agent_result and test.agent_result.turns else 0
                        results_by_agent[agent_id] = {
                            "test": test,
                            "outcome": outcome,
                            "passed": outcome == "passed",
                            "duration_ms": duration_ms,
                            "duration_s": duration_ms / 1000,
                            "tokens": (test.agent_result.token_usage.get("prompt", 0) + test.agent_result.token_usage.get("completion", 0)) if test.agent_result and test.agent_result.token_usage else 0,
                            "cost": test.agent_result.cost_usd if test.agent_result else 0,
                            "tool_calls": tool_calls,
                            "tool_count": len(tool_calls),
                            "final_response": test.agent_result.final_response if test.agent_result else None,
                            "turns": turn_count,
                            "mermaid": generate_mermaid_sequence(test.agent_result) if test.agent_result else None,
                            "error": test.error,
                            "assertions": self._extract_assertions(test),
                        }
                
                # Check for differences between agents
                if len(outcomes) > 1:
                    has_difference = True
                
                # Use test name as display name, or extract from docstring if available
                display_name = test_name
                if first_test and hasattr(first_test, 'docstring') and first_test.docstring:
                    first_line = first_test.docstring.split('\n')[0].strip()
                    if first_line:
                        display_name = first_line[:60] + ("…" if len(first_line) > 60 else "")
                
                test_list.append({
                    "id": test_name,
                    "display_name": display_name,
                    "results_by_agent": results_by_agent,
                    "has_difference": has_difference,
                    "has_failed": has_failed,
                })
            
            # Calculate group-level stats per agent
            agent_stats = {}
            for agent_id in selected_agent_ids:
                passed = sum(1 for t in test_list if t["results_by_agent"].get(agent_id, {}).get("outcome") == "passed")
                failed = sum(1 for t in test_list if t["results_by_agent"].get(agent_id, {}).get("outcome") != "passed" and agent_id in t["results_by_agent"])
                agent_stats[agent_id] = {"passed": passed, "failed": failed}
            
            result.append({
                "type": "session" if is_session else "standalone",
                "name": group_name,
                "tests": test_list,
                "agent_stats": agent_stats,
            })
        
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

        from pytest_aitest.core.serialization import serialize_dataclass
        
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
