"""
Priority Scoring Algorithm for Task Analyzer

This module implements a multi-factor scoring system that calculates task priority
based on urgency, importance, effort, and dependencies.

Scoring Components:
1. Urgency Score (0-100): Based on days until due date
   - Past due tasks receive maximum urgency + penalty
   - Tasks due today/tomorrow receive very high urgency
   - Urgency decreases as due date is further away

2. Importance Score (0-100): Direct mapping from user rating (1-10 scale)

3. Effort Score (0-100): Quick wins prioritization
   - Lower effort tasks score higher (inverse relationship)
   - Capped at reasonable bounds

4. Dependency Score (0-100): Tasks blocking others get priority boost
   - Based on how many other tasks depend on this task
"""

from datetime import date, timedelta
from typing import Optional


# Default weights for the "Smart Balance" strategy
DEFAULT_WEIGHTS = {
    'urgency': 0.35,
    'importance': 0.30,
    'effort': 0.15,
    'dependency': 0.20,
}

# Strategy-specific weight presets
STRATEGY_WEIGHTS = {
    'smart_balance': DEFAULT_WEIGHTS,
    'fastest_wins': {
        'urgency': 0.15,
        'importance': 0.15,
        'effort': 0.60,
        'dependency': 0.10,
    },
    'high_impact': {
        'urgency': 0.15,
        'importance': 0.60,
        'effort': 0.10,
        'dependency': 0.15,
    },
    'deadline_driven': {
        'urgency': 0.60,
        'importance': 0.20,
        'effort': 0.05,
        'dependency': 0.15,
    },
}


def calculate_urgency_score(due_date: date, today: Optional[date] = None) -> tuple[float, str]:
    """
    Calculate urgency score based on days until due date.

    Args:
        due_date: The task's due date
        today: Reference date (defaults to current date)

    Returns:
        Tuple of (score, explanation)
    """
    if today is None:
        today = date.today()

    days_until_due = (due_date - today).days

    if days_until_due < 0:
        # Past due - maximum urgency with penalty
        days_overdue = abs(days_until_due)
        score = min(100 + (days_overdue * 5), 150)  # Cap at 150 for past due
        explanation = f"OVERDUE by {days_overdue} day(s)"
    elif days_until_due == 0:
        score = 100
        explanation = "Due TODAY"
    elif days_until_due == 1:
        score = 95
        explanation = "Due TOMORROW"
    elif days_until_due <= 3:
        score = 85
        explanation = f"Due in {days_until_due} days (this week)"
    elif days_until_due <= 7:
        score = 70
        explanation = f"Due in {days_until_due} days (within a week)"
    elif days_until_due <= 14:
        score = 50
        explanation = f"Due in {days_until_due} days (within 2 weeks)"
    elif days_until_due <= 30:
        score = 30
        explanation = f"Due in {days_until_due} days (within a month)"
    else:
        # Far future - minimal urgency
        score = max(10, 30 - (days_until_due - 30) // 7)
        explanation = f"Due in {days_until_due} days (low urgency)"

    return score, explanation


def calculate_importance_score(importance: int) -> tuple[float, str]:
    """
    Convert importance rating (1-10) to score (0-100).

    Args:
        importance: User-provided importance rating (1-10)

    Returns:
        Tuple of (score, explanation)
    """
    # Direct linear mapping: 1 -> 10, 10 -> 100
    score = importance * 10

    if importance >= 9:
        level = "Critical"
    elif importance >= 7:
        level = "High"
    elif importance >= 5:
        level = "Medium"
    elif importance >= 3:
        level = "Low"
    else:
        level = "Minimal"

    explanation = f"Importance: {level} ({importance}/10)"
    return score, explanation


def calculate_effort_score(estimated_hours: float) -> tuple[float, str]:
    """
    Calculate effort score - lower effort tasks get higher scores (quick wins).

    Args:
        estimated_hours: Estimated time to complete the task

    Returns:
        Tuple of (score, explanation)
    """
    if estimated_hours <= 1:
        score = 100
        explanation = "Quick win (under 1 hour)"
    elif estimated_hours <= 2:
        score = 85
        explanation = "Short task (1-2 hours)"
    elif estimated_hours <= 4:
        score = 70
        explanation = "Medium task (2-4 hours)"
    elif estimated_hours <= 8:
        score = 50
        explanation = "Half-day task (4-8 hours)"
    elif estimated_hours <= 16:
        score = 30
        explanation = "Full day task (8-16 hours)"
    else:
        score = max(10, 30 - (estimated_hours - 16) // 8 * 5)
        explanation = f"Large task ({estimated_hours} hours)"

    return score, explanation


def calculate_dependency_score(task_id: Optional[int], all_tasks: list[dict]) -> tuple[float, str]:
    """
    Calculate dependency score based on how many tasks depend on this task.
    Tasks that block others should be prioritized.

    Args:
        task_id: The ID of the current task
        all_tasks: List of all tasks to check dependencies

    Returns:
        Tuple of (score, explanation)
    """
    if task_id is None:
        return 0, "No task ID (dependency check skipped)"

    # Count how many tasks depend on this task
    dependent_count = 0
    for task in all_tasks:
        dependencies = task.get('dependencies', [])
        if task_id in dependencies:
            dependent_count += 1

    if dependent_count == 0:
        score = 0
        explanation = "No tasks blocked by this"
    elif dependent_count == 1:
        score = 50
        explanation = "Blocks 1 other task"
    elif dependent_count == 2:
        score = 75
        explanation = "Blocks 2 other tasks"
    else:
        score = min(100, 50 + dependent_count * 15)
        explanation = f"Blocks {dependent_count} other tasks (high priority)"

    return score, explanation


def detect_circular_dependencies(tasks: list[dict]) -> list[tuple[int, int]]:
    """
    Detect circular dependencies in the task list.

    Args:
        tasks: List of tasks with dependencies

    Returns:
        List of tuples representing circular dependency pairs
    """
    circular = []
    task_ids = {task.get('id') for task in tasks if task.get('id') is not None}

    # Build adjacency list
    graph = {}
    for task in tasks:
        task_id = task.get('id')
        if task_id is not None:
            graph[task_id] = task.get('dependencies', [])

    # DFS to detect cycles
    def has_cycle(node, visited, rec_stack, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in task_ids:
                continue
            if neighbor not in visited:
                cycle = has_cycle(neighbor, visited, rec_stack, path)
                if cycle:
                    return cycle
            elif neighbor in rec_stack:
                # Found cycle
                cycle_start = path.index(neighbor)
                return path[cycle_start:]

        path.pop()
        rec_stack.remove(node)
        return None

    visited = set()
    for task_id in task_ids:
        if task_id not in visited:
            cycle = has_cycle(task_id, visited, set(), [])
            if cycle and len(cycle) >= 2:
                for i in range(len(cycle)):
                    circular.append((cycle[i], cycle[(i + 1) % len(cycle)]))

    return circular


def calculate_priority_score(
    task: dict,
    all_tasks: list[dict],
    strategy: str = 'smart_balance',
    custom_weights: Optional[dict] = None,
    today: Optional[date] = None
) -> dict:
    """
    Calculate the overall priority score for a task.

    Args:
        task: Task data dictionary
        all_tasks: List of all tasks (for dependency calculation)
        strategy: Scoring strategy to use
        custom_weights: Optional custom weights (overrides strategy)
        today: Reference date for urgency calculation

    Returns:
        Dictionary with task data plus priority_score, priority_level, and explanation
    """
    # Get weights based on strategy or custom
    if custom_weights:
        weights = {**DEFAULT_WEIGHTS, **custom_weights}
    else:
        weights = STRATEGY_WEIGHTS.get(strategy, DEFAULT_WEIGHTS)

    # Normalize weights to sum to 1
    total_weight = sum(weights.values())
    weights = {k: v / total_weight for k, v in weights.items()}

    # Calculate individual scores
    urgency_score, urgency_exp = calculate_urgency_score(task['due_date'], today)
    importance_score, importance_exp = calculate_importance_score(task['importance'])
    effort_score, effort_exp = calculate_effort_score(task['estimated_hours'])
    dependency_score, dependency_exp = calculate_dependency_score(
        task.get('id'), all_tasks
    )

    # Calculate weighted score
    weighted_score = (
        urgency_score * weights['urgency'] +
        importance_score * weights['importance'] +
        effort_score * weights['effort'] +
        dependency_score * weights['dependency']
    )

    # Normalize to 0-100 scale (accounting for past-due bonus)
    priority_score = min(100, weighted_score)

    # Determine priority level
    if priority_score >= 80 or urgency_score > 100:
        priority_level = "High"
    elif priority_score >= 50:
        priority_level = "Medium"
    else:
        priority_level = "Low"

    # Build explanation
    explanations = [urgency_exp, importance_exp, effort_exp]
    if dependency_score > 0:
        explanations.append(dependency_exp)

    explanation = " | ".join(explanations)

    return {
        **task,
        'priority_score': round(priority_score, 2),
        'priority_level': priority_level,
        'explanation': explanation,
        'score_breakdown': {
            'urgency': round(urgency_score, 2),
            'importance': round(importance_score, 2),
            'effort': round(effort_score, 2),
            'dependency': round(dependency_score, 2),
        }
    }


def analyze_tasks(
    tasks: list[dict],
    strategy: str = 'smart_balance',
    custom_weights: Optional[dict] = None
) -> dict:
    """
    Analyze a list of tasks and return them sorted by priority.

    Args:
        tasks: List of task dictionaries
        strategy: Scoring strategy to use
        custom_weights: Optional custom weights

    Returns:
        Dictionary with sorted tasks and metadata
    """
    # Validate and convert dates
    processed_tasks = []
    for task in tasks:
        processed = dict(task)
        if isinstance(processed['due_date'], str):
            processed['due_date'] = date.fromisoformat(processed['due_date'])
        processed_tasks.append(processed)

    # Check for circular dependencies
    circular_deps = detect_circular_dependencies(processed_tasks)

    # Calculate scores for each task
    scored_tasks = [
        calculate_priority_score(task, processed_tasks, strategy, custom_weights)
        for task in processed_tasks
    ]

    # Sort by priority score (descending)
    scored_tasks.sort(key=lambda x: x['priority_score'], reverse=True)

    # Convert dates back to string for JSON serialization
    for task in scored_tasks:
        if isinstance(task['due_date'], date):
            task['due_date'] = task['due_date'].isoformat()

    return {
        'tasks': scored_tasks,
        'strategy': strategy,
        'circular_dependencies': circular_deps,
        'total_tasks': len(scored_tasks),
    }


def get_suggested_tasks(
    tasks: list[dict],
    count: int = 3,
    strategy: str = 'smart_balance'
) -> list[dict]:
    """
    Get the top N suggested tasks to work on today.

    Args:
        tasks: List of task dictionaries
        count: Number of suggestions to return
        strategy: Scoring strategy to use

    Returns:
        List of top tasks with detailed explanations
    """
    result = analyze_tasks(tasks, strategy)
    suggestions = []

    for i, task in enumerate(result['tasks'][:count]):
        reason_parts = []

        # Build detailed reason based on score breakdown
        breakdown = task.get('score_breakdown', {})

        if breakdown.get('urgency', 0) >= 80:
            reason_parts.append("urgent deadline")
        if breakdown.get('importance', 0) >= 80:
            reason_parts.append("high importance")
        if breakdown.get('effort', 0) >= 80:
            reason_parts.append("quick to complete")
        if breakdown.get('dependency', 0) > 0:
            reason_parts.append("unblocks other tasks")

        if not reason_parts:
            reason_parts.append("balanced priority")

        suggestion = {
            **task,
            'rank': i + 1,
            'reason': f"Recommended because: {', '.join(reason_parts)}",
        }
        suggestions.append(suggestion)

    return suggestions
