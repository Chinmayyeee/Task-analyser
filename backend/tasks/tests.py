from datetime import date, timedelta
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from .scoring import (
    calculate_urgency_score,
    calculate_importance_score,
    calculate_effort_score,
    calculate_dependency_score,
    calculate_priority_score,
    analyze_tasks,
    detect_circular_dependencies,
    get_suggested_tasks,
    STRATEGY_WEIGHTS,
)


class UrgencyScoreTests(TestCase):
    """Tests for the urgency scoring component."""

    def setUp(self):
        self.today = date(2025, 11, 26)

    def test_overdue_task_high_urgency(self):
        """Past due tasks should have very high urgency (>100)."""
        past_date = self.today - timedelta(days=3)
        score, explanation = calculate_urgency_score(past_date, self.today)

        self.assertGreater(score, 100)
        self.assertIn('OVERDUE', explanation)

    def test_due_today_maximum_urgency(self):
        """Tasks due today should have score of 100."""
        score, explanation = calculate_urgency_score(self.today, self.today)

        self.assertEqual(score, 100)
        self.assertIn('TODAY', explanation)

    def test_due_tomorrow_very_high_urgency(self):
        """Tasks due tomorrow should have score of 95."""
        tomorrow = self.today + timedelta(days=1)
        score, explanation = calculate_urgency_score(tomorrow, self.today)

        self.assertEqual(score, 95)
        self.assertIn('TOMORROW', explanation)

    def test_due_within_week_high_urgency(self):
        """Tasks due within a week should have high urgency."""
        next_week = self.today + timedelta(days=5)
        score, explanation = calculate_urgency_score(next_week, self.today)

        self.assertGreaterEqual(score, 70)
        self.assertLess(score, 95)

    def test_due_far_future_low_urgency(self):
        """Tasks due far in the future should have low urgency."""
        far_future = self.today + timedelta(days=60)
        score, explanation = calculate_urgency_score(far_future, self.today)

        self.assertLess(score, 30)


class ImportanceScoreTests(TestCase):
    """Tests for the importance scoring component."""

    def test_maximum_importance(self):
        """Importance of 10 should yield score of 100."""
        score, explanation = calculate_importance_score(10)

        self.assertEqual(score, 100)
        self.assertIn('Critical', explanation)

    def test_minimum_importance(self):
        """Importance of 1 should yield score of 10."""
        score, explanation = calculate_importance_score(1)

        self.assertEqual(score, 10)
        self.assertIn('Minimal', explanation)

    def test_medium_importance(self):
        """Importance of 5 should yield score of 50."""
        score, explanation = calculate_importance_score(5)

        self.assertEqual(score, 50)
        self.assertIn('Medium', explanation)

    def test_importance_linear_scaling(self):
        """Importance scores should scale linearly."""
        for i in range(1, 11):
            score, _ = calculate_importance_score(i)
            self.assertEqual(score, i * 10)


class EffortScoreTests(TestCase):
    """Tests for the effort scoring component (quick wins prioritization)."""

    def test_quick_task_high_score(self):
        """Tasks under 1 hour should score 100 (quick win)."""
        score, explanation = calculate_effort_score(0.5)

        self.assertEqual(score, 100)
        self.assertIn('Quick win', explanation)

    def test_short_task_high_score(self):
        """Tasks 1-2 hours should score 85."""
        score, explanation = calculate_effort_score(1.5)

        self.assertEqual(score, 85)

    def test_medium_task_moderate_score(self):
        """Tasks 2-4 hours should score 70."""
        score, explanation = calculate_effort_score(3)

        self.assertEqual(score, 70)

    def test_long_task_low_score(self):
        """Very long tasks should have lower scores."""
        score, explanation = calculate_effort_score(20)

        self.assertLessEqual(score, 30)


class DependencyScoreTests(TestCase):
    """Tests for the dependency scoring component."""

    def test_no_dependents_zero_score(self):
        """Tasks with no dependents should score 0."""
        tasks = [
            {'id': 1, 'dependencies': []},
            {'id': 2, 'dependencies': []},
        ]
        score, explanation = calculate_dependency_score(1, tasks)

        self.assertEqual(score, 0)

    def test_one_dependent_moderate_score(self):
        """Tasks blocking one other task should score 50."""
        tasks = [
            {'id': 1, 'dependencies': []},
            {'id': 2, 'dependencies': [1]},  # Task 2 depends on Task 1
        ]
        score, explanation = calculate_dependency_score(1, tasks)

        self.assertEqual(score, 50)
        self.assertIn('Blocks 1', explanation)

    def test_multiple_dependents_high_score(self):
        """Tasks blocking many others should have high scores."""
        tasks = [
            {'id': 1, 'dependencies': []},
            {'id': 2, 'dependencies': [1]},
            {'id': 3, 'dependencies': [1]},
            {'id': 4, 'dependencies': [1]},
        ]
        score, explanation = calculate_dependency_score(1, tasks)

        self.assertGreater(score, 75)

    def test_no_task_id_returns_zero(self):
        """Tasks without ID should return 0 dependency score."""
        tasks = [{'id': 1, 'dependencies': []}]
        score, explanation = calculate_dependency_score(None, tasks)

        self.assertEqual(score, 0)


class CircularDependencyTests(TestCase):
    """Tests for circular dependency detection."""

    def test_no_circular_dependencies(self):
        """Should return empty list when no circular dependencies exist."""
        tasks = [
            {'id': 1, 'dependencies': []},
            {'id': 2, 'dependencies': [1]},
            {'id': 3, 'dependencies': [2]},
        ]
        circular = detect_circular_dependencies(tasks)

        self.assertEqual(len(circular), 0)

    def test_simple_circular_dependency(self):
        """Should detect simple A -> B -> A cycle."""
        tasks = [
            {'id': 1, 'dependencies': [2]},
            {'id': 2, 'dependencies': [1]},
        ]
        circular = detect_circular_dependencies(tasks)

        self.assertGreater(len(circular), 0)

    def test_complex_circular_dependency(self):
        """Should detect longer cycles (A -> B -> C -> A)."""
        tasks = [
            {'id': 1, 'dependencies': [3]},
            {'id': 2, 'dependencies': [1]},
            {'id': 3, 'dependencies': [2]},
        ]
        circular = detect_circular_dependencies(tasks)

        self.assertGreater(len(circular), 0)


class PriorityScoreTests(TestCase):
    """Tests for the overall priority scoring function."""

    def setUp(self):
        self.today = date(2025, 11, 26)
        self.base_task = {
            'id': 1,
            'title': 'Test Task',
            'due_date': self.today + timedelta(days=3),
            'estimated_hours': 2,
            'importance': 5,
            'dependencies': [],
        }

    def test_score_within_range(self):
        """Priority score should be between 0 and 100."""
        result = calculate_priority_score(
            self.base_task, [self.base_task], 'smart_balance', None, self.today
        )

        self.assertGreaterEqual(result['priority_score'], 0)
        self.assertLessEqual(result['priority_score'], 100)

    def test_high_urgency_high_importance_high_score(self):
        """Task with high urgency and importance should score high."""
        task = {
            **self.base_task,
            'due_date': self.today,  # Due today
            'importance': 10,  # Maximum importance
            'estimated_hours': 0.5,  # Quick task
        }
        result = calculate_priority_score(task, [task], 'smart_balance', None, self.today)

        self.assertGreaterEqual(result['priority_score'], 80)
        self.assertEqual(result['priority_level'], 'High')

    def test_low_urgency_low_importance_low_score(self):
        """Task with low urgency and importance should score low."""
        task = {
            **self.base_task,
            'due_date': self.today + timedelta(days=60),  # Far future
            'importance': 1,  # Minimum importance
            'estimated_hours': 20,  # Long task
        }
        result = calculate_priority_score(task, [task], 'smart_balance', None, self.today)

        self.assertLess(result['priority_score'], 30)
        self.assertEqual(result['priority_level'], 'Low')

    def test_explanation_generated(self):
        """Result should include explanation."""
        result = calculate_priority_score(
            self.base_task, [self.base_task], 'smart_balance', None, self.today
        )

        self.assertIn('explanation', result)
        self.assertTrue(len(result['explanation']) > 0)


class StrategyTests(TestCase):
    """Tests for different sorting strategies."""

    def setUp(self):
        self.today = date(2025, 11, 26)
        # Create tasks that would rank differently under different strategies
        self.tasks = [
            {
                'id': 1,
                'title': 'Quick unimportant task',
                'due_date': self.today + timedelta(days=30),
                'estimated_hours': 0.5,
                'importance': 2,
                'dependencies': [],
            },
            {
                'id': 2,
                'title': 'Long important task',
                'due_date': self.today + timedelta(days=30),
                'estimated_hours': 20,
                'importance': 10,
                'dependencies': [],
            },
            {
                'id': 3,
                'title': 'Urgent medium task',
                'due_date': self.today + timedelta(days=1),
                'estimated_hours': 4,
                'importance': 5,
                'dependencies': [],
            },
        ]

    def test_fastest_wins_prioritizes_effort(self):
        """Fastest wins strategy should prioritize quick tasks."""
        result = analyze_tasks(self.tasks, 'fastest_wins')

        # Quick task should rank first
        self.assertEqual(result['tasks'][0]['id'], 1)

    def test_high_impact_prioritizes_importance(self):
        """High impact strategy should prioritize important tasks."""
        result = analyze_tasks(self.tasks, 'high_impact')

        # Important task should rank first
        self.assertEqual(result['tasks'][0]['id'], 2)

    def test_deadline_driven_prioritizes_urgency(self):
        """Deadline driven strategy should prioritize urgent tasks."""
        result = analyze_tasks(self.tasks, 'deadline_driven')

        # Urgent task should rank first
        self.assertEqual(result['tasks'][0]['id'], 3)

    def test_custom_weights_applied(self):
        """Custom weights should override strategy weights."""
        custom = {'urgency': 0, 'importance': 0, 'effort': 1, 'dependency': 0}
        result = analyze_tasks(self.tasks, 'smart_balance', custom)

        # With only effort weight, quick task should rank first
        self.assertEqual(result['tasks'][0]['id'], 1)


class AnalyzeTasksTests(TestCase):
    """Tests for the analyze_tasks function."""

    def test_returns_sorted_tasks(self):
        """Tasks should be returned sorted by priority score (descending)."""
        tasks = [
            {'id': 1, 'title': 'Low', 'due_date': '2026-01-01', 'estimated_hours': 10, 'importance': 1, 'dependencies': []},
            {'id': 2, 'title': 'High', 'due_date': '2025-11-27', 'estimated_hours': 1, 'importance': 10, 'dependencies': []},
        ]
        result = analyze_tasks(tasks, 'smart_balance')

        self.assertEqual(result['tasks'][0]['id'], 2)  # High priority first
        self.assertGreater(result['tasks'][0]['priority_score'], result['tasks'][1]['priority_score'])

    def test_handles_string_dates(self):
        """Should handle date strings in ISO format."""
        tasks = [
            {'id': 1, 'title': 'Test', 'due_date': '2025-12-15', 'estimated_hours': 2, 'importance': 5, 'dependencies': []},
        ]
        result = analyze_tasks(tasks, 'smart_balance')

        self.assertEqual(len(result['tasks']), 1)
        self.assertEqual(result['tasks'][0]['due_date'], '2025-12-15')

    def test_includes_metadata(self):
        """Result should include strategy and total_tasks metadata."""
        tasks = [
            {'id': 1, 'title': 'Test', 'due_date': '2025-12-15', 'estimated_hours': 2, 'importance': 5, 'dependencies': []},
        ]
        result = analyze_tasks(tasks, 'fastest_wins')

        self.assertEqual(result['strategy'], 'fastest_wins')
        self.assertEqual(result['total_tasks'], 1)


class SuggestedTasksTests(TestCase):
    """Tests for the get_suggested_tasks function."""

    def test_returns_requested_count(self):
        """Should return the requested number of suggestions."""
        tasks = [
            {'id': i, 'title': f'Task {i}', 'due_date': '2025-12-15', 'estimated_hours': 2, 'importance': 5, 'dependencies': []}
            for i in range(1, 6)
        ]

        suggestions = get_suggested_tasks(tasks, count=3)

        self.assertEqual(len(suggestions), 3)

    def test_includes_rank_and_reason(self):
        """Suggestions should include rank and reason fields."""
        tasks = [
            {'id': 1, 'title': 'Test', 'due_date': '2025-12-15', 'estimated_hours': 2, 'importance': 8, 'dependencies': []},
        ]

        suggestions = get_suggested_tasks(tasks, count=1)

        self.assertEqual(suggestions[0]['rank'], 1)
        self.assertIn('reason', suggestions[0])
        self.assertIn('Recommended because', suggestions[0]['reason'])


class APIEndpointTests(APITestCase):
    """Tests for the API endpoints."""

    def test_analyze_endpoint_success(self):
        """POST /api/tasks/analyze/ should return sorted tasks."""
        data = {
            'tasks': [
                {'title': 'Task 1', 'due_date': '2025-12-15', 'estimated_hours': 2, 'importance': 8, 'dependencies': []},
                {'title': 'Task 2', 'due_date': '2025-12-20', 'estimated_hours': 4, 'importance': 5, 'dependencies': []},
            ],
            'strategy': 'smart_balance'
        }

        response = self.client.post('/api/tasks/analyze/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['tasks']), 2)
        self.assertIn('priority_score', response.data['tasks'][0])

    def test_analyze_endpoint_empty_tasks(self):
        """Should return 400 for empty task list."""
        data = {'tasks': []}

        response = self.client.post('/api/tasks/analyze/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_analyze_endpoint_invalid_task(self):
        """Should return 400 for invalid task data."""
        data = {
            'tasks': [
                {'title': 'Missing fields'}  # Missing required fields
            ]
        }

        response = self.client.post('/api/tasks/analyze/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_suggest_endpoint_success(self):
        """POST /api/tasks/suggest/ should return top suggestions."""
        data = {
            'tasks': [
                {'title': 'Task 1', 'due_date': '2025-12-15', 'estimated_hours': 2, 'importance': 8, 'dependencies': []},
                {'title': 'Task 2', 'due_date': '2025-12-20', 'estimated_hours': 4, 'importance': 5, 'dependencies': []},
            ],
            'count': 2
        }

        response = self.client.post('/api/tasks/suggest/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['suggestions']), 2)
        self.assertIn('reason', response.data['suggestions'][0])

    def test_health_endpoint(self):
        """GET /api/health/ should return ok status."""
        response = self.client.get('/api/health/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ok')
