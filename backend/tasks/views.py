from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import TaskAnalyzeRequestSerializer, TaskInputSerializer
from .scoring import analyze_tasks, get_suggested_tasks


@api_view(['POST'])
def analyze_tasks_view(request):
    """
    Analyze a list of tasks and return them sorted by priority score.

    POST /api/tasks/analyze/

    Request body:
    {
        "tasks": [
            {
                "id": 1,  // optional
                "title": "Task name",
                "due_date": "2025-11-30",
                "estimated_hours": 3,
                "importance": 8,
                "dependencies": []  // optional
            },
            ...
        ],
        "strategy": "smart_balance",  // optional: smart_balance, fastest_wins, high_impact, deadline_driven
        "weights": {  // optional custom weights
            "urgency": 0.35,
            "importance": 0.30,
            "effort": 0.15,
            "dependency": 0.20
        }
    }

    Response:
    {
        "tasks": [...sorted tasks with priority_score, priority_level, explanation...],
        "strategy": "smart_balance",
        "circular_dependencies": [],
        "total_tasks": 5
    }
    """
    serializer = TaskAnalyzeRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid input', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    validated_data = serializer.validated_data
    tasks = validated_data['tasks']
    strategy = validated_data.get('strategy', 'smart_balance')
    custom_weights = validated_data.get('weights') or None

    # Handle empty task list
    if not tasks:
        return Response(
            {'error': 'No tasks provided'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        result = analyze_tasks(
            tasks=tasks,
            strategy=strategy,
            custom_weights=custom_weights
        )
        return Response(result, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response(
            {'error': 'Invalid task data', 'details': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': 'Processing error', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def suggest_tasks_view(request):
    """
    Return the top 3 tasks the user should work on today with explanations.

    POST /api/tasks/suggest/

    Request body:
    {
        "tasks": [...],  // same format as analyze endpoint
        "count": 3,  // optional, default 3
        "strategy": "smart_balance"  // optional
    }

    Response:
    {
        "suggestions": [
            {
                "rank": 1,
                "title": "...",
                "priority_score": 85.5,
                "reason": "Recommended because: urgent deadline, high importance",
                ...
            },
            ...
        ],
        "total_tasks": 10
    }
    """
    # Validate tasks
    tasks_data = request.data.get('tasks', [])
    count = request.data.get('count', 3)
    strategy = request.data.get('strategy', 'smart_balance')

    if not tasks_data:
        return Response(
            {'error': 'No tasks provided'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate each task
    validated_tasks = []
    for i, task in enumerate(tasks_data):
        task_serializer = TaskInputSerializer(data=task)
        if not task_serializer.is_valid():
            return Response(
                {'error': f'Invalid task at index {i}', 'details': task_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        validated_tasks.append(task_serializer.validated_data)

    try:
        suggestions = get_suggested_tasks(
            tasks=validated_tasks,
            count=min(count, len(validated_tasks)),
            strategy=strategy
        )

        return Response({
            'suggestions': suggestions,
            'total_tasks': len(validated_tasks),
            'strategy': strategy,
        }, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response(
            {'error': 'Invalid task data', 'details': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': 'Processing error', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def health_check(request):
    """Simple health check endpoint."""
    return Response({'status': 'ok', 'service': 'task-analyzer'})
