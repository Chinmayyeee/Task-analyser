from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Task(models.Model):
    """
    Task model representing a task with priority-related attributes.

    Attributes:
        title: Name/description of the task
        due_date: When the task is due
        estimated_hours: Expected time to complete (in hours)
        importance: User-provided priority rating (1-10 scale)
        dependencies: List of task IDs this task depends on
        created_at: Timestamp when task was created
    """
    title = models.CharField(max_length=255)
    due_date = models.DateField()
    estimated_hours = models.FloatField(
        validators=[MinValueValidator(0.1)]
    )
    importance = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    dependencies = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
