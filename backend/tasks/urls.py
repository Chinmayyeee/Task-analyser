from django.urls import path
from . import views

urlpatterns = [
    path('tasks/analyze/', views.analyze_tasks_view, name='analyze_tasks'),
    path('tasks/suggest/', views.suggest_tasks_view, name='suggest_tasks'),
    path('health/', views.health_check, name='health_check'),
]
