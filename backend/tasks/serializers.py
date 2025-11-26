from rest_framework import serializers
from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task model."""

    class Meta:
        model = Task
        fields = ['id', 'title', 'due_date', 'estimated_hours', 'importance', 'dependencies', 'created_at']
        read_only_fields = ['id', 'created_at']


class TaskInputSerializer(serializers.Serializer):
    """
    Serializer for validating task input data (without requiring database storage).
    Used for the analyze endpoint which accepts tasks as JSON input.
    """
    id = serializers.IntegerField(required=False)
    title = serializers.CharField(max_length=255)
    due_date = serializers.DateField()
    estimated_hours = serializers.FloatField(min_value=0.1)
    importance = serializers.IntegerField(min_value=1, max_value=10)
    dependencies = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )


class TaskAnalyzeRequestSerializer(serializers.Serializer):
    """Serializer for the analyze endpoint request body."""
    tasks = TaskInputSerializer(many=True)
    strategy = serializers.ChoiceField(
        choices=['smart_balance', 'fastest_wins', 'high_impact', 'deadline_driven'],
        default='smart_balance',
        required=False
    )
    weights = serializers.DictField(
        child=serializers.FloatField(min_value=0, max_value=1),
        required=False,
        default=dict
    )


class ScoredTaskSerializer(serializers.Serializer):
    """Serializer for tasks with calculated priority scores."""
    id = serializers.IntegerField(required=False)
    title = serializers.CharField()
    due_date = serializers.DateField()
    estimated_hours = serializers.FloatField()
    importance = serializers.IntegerField()
    dependencies = serializers.ListField(child=serializers.IntegerField())
    priority_score = serializers.FloatField()
    priority_level = serializers.CharField()
    explanation = serializers.CharField()
