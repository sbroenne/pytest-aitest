"""Test grid component - session-grouped test list with optional agent comparison."""

from __future__ import annotations

from htpy import Node, button, div, span

from .test_comparison import test_comparison
from .types import AgentData, TestData, TestGroupData, TestResultData


def _filter_button(label: str, filter_value: str, is_active: bool = False) -> Node:
    """Render a filter button."""
    active_class = "active" if is_active else ""
    return button(
        class_=f"filter-btn {active_class}",
        data_filter=filter_value,
        onclick=f"filterTests('{filter_value}')",
    )[label]


def _filter_bar(total_tests: int, comparison_mode: bool) -> Node:
    """Render the filter bar."""
    buttons = [_filter_button("All", "all", is_active=True)]
    if comparison_mode:
        buttons.append(_filter_button("Differences ⚡", "diff"))
    buttons.append(_filter_button("Failed ❌", "failed"))
    
    return div(".mb-4.flex.items-center.justify-between")[
        div(".flex.gap-2")[buttons],
        div(".text-sm.text-text-muted")[
            span(id="visible-count")[str(total_tests)],
            f" / {total_tests} tests",
        ],
    ]


def _status_icon(result: TestResultData | None) -> Node:
    """Render status icon for a test result."""
    if not result:
        return span(".text-text-muted")["⚪"]
    
    status_class = "text-green-400" if result.passed else "text-red-400"
    icon = "✅" if result.passed else "❌"
    return span(class_=status_class)[icon]


def _diff_indicator(has_difference: bool) -> Node | None:
    """Render difference indicator when results vary between agents."""
    if not has_difference:
        return None
    return span(".text-yellow-400", title="Results differ between agents")["⚡"]


def _test_metrics(result: TestResultData | None) -> Node | None:
    """Render metrics for a test result."""
    if not result:
        return None
    
    return div(".flex.items-center.gap-4.text-sm.text-text-muted")[
        span(".tabular-nums")[f"{result.duration_s:.1f}s"],
        span(".tabular-nums")[f"{result.tool_count}🔧"],
        span(".tabular-nums")[f"{result.tokens:,} tok"],
    ]


def _agent_result_badge(
    agent: AgentData,
    result: TestResultData | None,
    is_selected: bool,
) -> Node:
    """Render a small inline result badge for comparison mode."""
    hidden_class = "hidden" if not is_selected else ""
    
    if not result:
        status = span(".text-text-muted")["—"]
        duration = ""
    else:
        status_class = "text-green-400" if result.passed else "text-red-400"
        status_icon = "✅" if result.passed else "❌"
        status = span(class_=status_class)[status_icon]
        duration = span(".text-text-muted.tabular-nums")[f"{result.duration_s:.1f}s"]
    
    return div(
        class_=f"agent-result-item flex items-center gap-2 text-xs {hidden_class}",
        data_agent_id=agent.id,
    )[
        span(".text-text-muted")[f"{agent.name}:"],
        status,
        duration,
    ]


def _test_row(
    test: TestData,
    all_agent_ids: list[str],
    selected_agent_ids: list[str],
    agents_by_id: dict[str, AgentData],
    comparison_mode: bool,
) -> Node:
    """Render a single test row."""
    # Get first result for default display
    first_result = None
    if test.results_by_agent:
        first_result = next(iter(test.results_by_agent.values()), None)
    
    selected_set = set(selected_agent_ids)
    
    # Comparison mode inline results
    comparison_badges = None
    if comparison_mode:
        comparison_badges = div(".flex.gap-4.mt-2.pl-8")[
            [
                _agent_result_badge(
                    agents_by_id[agent_id],
                    test.results_by_agent.get(agent_id),
                    agent_id in selected_set,
                )
                for agent_id in all_agent_ids
            ]
        ]
    
    return div(
        class_="test-row border-b border-white/5",
        data_test_id=test.id,
        data_has_diff="true" if test.has_difference else "false",
        data_has_failed="true" if test.has_failed else "false",
    )[
        # Clickable header
        div(
            class_="px-5 py-3 hover:bg-white/[0.02] cursor-pointer transition-colors",
            onclick="toggleTestDetail(this.parentElement)",
        )[
            div(".flex.items-center.justify-between")[
                div(".flex.items-center.gap-3.min-w-0.flex-1")[
                    _status_icon(first_result),
                    span(".text-text-light.truncate")[test.display_name],
                    _diff_indicator(test.has_difference),
                ],
                _test_metrics(first_result),
            ],
            comparison_badges,
        ],
        # Expanded detail (hidden by default)
        div(".test-detail.hidden.border-t.border-white/10.bg-surface-elevated")[
            test_comparison(test, all_agent_ids, selected_agent_ids, agents_by_id)
        ],
    ]


def _group_header(
    group: TestGroupData,
    selected_agent_ids: list[str],
    comparison_mode: bool,
) -> Node:
    """Render a group header."""
    icon = "🔗" if group.type == "session" else "📋"
    
    # Per-agent stats in comparison mode
    stats_nodes = None
    if comparison_mode:
        stats_list = []
        for agent_id in selected_agent_ids:
            stats = group.agent_stats.get(agent_id)
            if stats:
                status_class = "text-green-400" if stats.failed == 0 else "text-red-400"
                total = stats.passed + stats.failed
                stats_list.append(
                    div(class_=f"text-sm {status_class}")[f"{stats.passed}/{total}"]
                )
        stats_nodes = stats_list
    
    header_cls = (
        "group-header px-5 py-3 bg-surface-elevated border-b border-white/10 "
        "flex justify-between items-center cursor-pointer"
    )
    return div(
        class_=header_cls,
        onclick="toggleGroup(this.parentElement)",
    )[
        div(".flex.items-center.gap-3")[
            span(".text-lg")[icon],
            span(".font-medium.text-text-light")[group.name],
            span(".text-sm.text-text-muted")[f"({len(group.tests)} tests)"],
        ],
        div(".flex.items-center.gap-4")[
            stats_nodes,
            span(".text-text-muted.transition-transform.duration-200.expand-icon")["▼"],
        ],
    ]


def _test_group(
    group: TestGroupData,
    all_agent_ids: list[str],
    selected_agent_ids: list[str],
    agents_by_id: dict[str, AgentData],
    comparison_mode: bool,
) -> Node:
    """Render a test group (session or standalone)."""
    return div(
        class_="card overflow-hidden test-group",
        data_group_type=group.type,
    )[
        _group_header(group, selected_agent_ids, comparison_mode),
        div(".group-content")[
            [
                _test_row(test, all_agent_ids, selected_agent_ids, agents_by_id, comparison_mode)
                for test in group.tests
            ]
        ],
    ]


def _grid_styles() -> Node:
    """CSS for test grid behavior."""
    from htpy import style
    
    return style[
        """
.test-group.collapsed .group-content {
    display: none;
}
.test-group.collapsed .expand-icon {
    transform: rotate(-90deg);
}
.test-row.hidden {
    display: none;
}
"""
    ]


def test_grid(
    test_groups: list[TestGroupData],
    all_agent_ids: list[str],
    selected_agent_ids: list[str],
    agents_by_id: dict[str, AgentData],
    total_tests: int,
) -> Node:
    """Render the test grid.
    
    Shows session-grouped test list with optional agent comparison.
    
    Args:
        test_groups: List of test groups (sessions or standalone).
        all_agent_ids: All agent IDs.
        selected_agent_ids: Currently selected agent IDs.
        agents_by_id: Mapping of agent ID to agent data.
        total_tests: Total number of tests.
    
    Returns:
        htpy Node for the test grid.
    """
    comparison_mode = len(all_agent_ids) > 1
    
    return [
        _filter_bar(total_tests, comparison_mode),
        div(".space-y-4", id="test-groups")[
            [
                _test_group(group, all_agent_ids, selected_agent_ids, agents_by_id, comparison_mode)
                for group in test_groups
            ]
        ],
        _grid_styles(),
    ]
