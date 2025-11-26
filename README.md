# Smart Task Analyzer

A task management system that intelligently scores and prioritizes tasks based on multiple factors including urgency, importance, effort, and dependencies.

## Table of Contents

- [Setup Instructions](#setup-instructions)
- [Running the Application](#running-the-application)
- [Algorithm Explanation](#algorithm-explanation)
- [Design Decisions](#design-decisions)
- [API Documentation](#api-documentation)
- [Future Improvements](#future-improvements)

## Setup Instructions

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- Modern web browser

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run database migrations:
   ```bash
   python manage.py migrate
   ```

5. Start the Django development server:
   ```bash
   python manage.py runserver
   ```

   The API will be available at `http://localhost:8000/api/`

### Frontend Setup

1. Open `frontend/index.html` in a web browser, or serve it using a simple HTTP server:
   ```bash
   cd frontend
   python -m http.server 3000
   ```

   Then open `http://localhost:3000` in your browser.

### Running Tests

```bash
cd backend
python manage.py test tasks
```

## Running the Application

1. Start the backend server (terminal 1):
   ```bash
   cd backend && python manage.py runserver
   ```

2. Open the frontend (terminal 2 or browser):
   ```bash
   cd frontend && python -m http.server 3000
   ```

3. Navigate to `http://localhost:3000` in your browser

4. Add tasks using the form or paste JSON, select a strategy, and click "Analyze Tasks"

## Algorithm Explanation

The Smart Task Analyzer uses a weighted multi-factor scoring system to calculate task priority. Each task receives a score from 0-100 based on four key components:

### Scoring Components

#### 1. Urgency Score (Default Weight: 35%)

Calculated based on days until the due date:

| Condition | Score | Description |
|-----------|-------|-------------|
| Past due | 100-150 | Maximum urgency with overdue penalty |
| Due today | 100 | Maximum urgency |
| Due tomorrow | 95 | Very high urgency |
| Due within 3 days | 85 | High urgency |
| Due within 1 week | 70 | Moderate-high urgency |
| Due within 2 weeks | 50 | Moderate urgency |
| Due within 1 month | 30 | Low urgency |
| Beyond 1 month | 10-30 | Minimal urgency (decreases with distance) |

**Design rationale**: Past-due tasks receive scores exceeding 100 to ensure they always rise to the top regardless of other factors. The scoring curve is steeper for near-term deadlines to create appropriate urgency.

#### 2. Importance Score (Default Weight: 30%)

Direct linear mapping from user-provided rating:
- Score = Importance × 10 (e.g., importance of 8 → score of 80)

**Levels**: Critical (9-10), High (7-8), Medium (5-6), Low (3-4), Minimal (1-2)

#### 3. Effort Score (Default Weight: 15%)

Implements "quick wins" prioritization - shorter tasks score higher:

| Estimated Hours | Score | Description |
|-----------------|-------|-------------|
| < 1 hour | 100 | Quick win |
| 1-2 hours | 85 | Short task |
| 2-4 hours | 70 | Medium task |
| 4-8 hours | 50 | Half-day task |
| 8-16 hours | 30 | Full day task |
| 16+ hours | 10-30 | Large task |

**Design rationale**: Completing quick tasks creates momentum and reduces cognitive overhead. This follows the "two-minute rule" principle from productivity methodologies.

#### 4. Dependency Score (Default Weight: 20%)

Tasks that block other tasks receive priority boosts:

| Blocking Count | Score |
|----------------|-------|
| 0 tasks | 0 |
| 1 task | 50 |
| 2 tasks | 75 |
| 3+ tasks | 80-100 |

**Design rationale**: Completing blocker tasks unblocks more work and improves overall project flow.

### Sorting Strategies

The algorithm supports four predefined strategies that adjust component weights:

| Strategy | Urgency | Importance | Effort | Dependency |
|----------|---------|------------|--------|------------|
| **Smart Balance** | 35% | 30% | 15% | 20% |
| **Fastest Wins** | 15% | 15% | 60% | 10% |
| **High Impact** | 15% | 60% | 10% | 15% |
| **Deadline Driven** | 60% | 20% | 5% | 15% |

### Final Score Calculation

```
priority_score = (urgency × weight_urgency) +
                 (importance × weight_importance) +
                 (effort × weight_effort) +
                 (dependency × weight_dependency)
```

Weights are normalized to sum to 1.0. The final score is capped at 100 (except for overdue tasks which can exceed this to ensure top priority).

### Circular Dependency Detection

The algorithm uses depth-first search (DFS) to detect circular dependencies in the task graph. When detected, users are warned but tasks are still scored (dependency scores are calculated based on what can be determined).

## Design Decisions

### 1. Stateless API Design

**Decision**: Tasks are not persisted to a database; instead, the API accepts tasks as JSON input and returns scored results.

**Rationale**:
- Simpler deployment (no database setup required beyond SQLite)
- Allows users to maintain their own task storage
- API can be used as a pure scoring service
- Easier testing and no state management complexity

### 2. Configurable Weights

**Decision**: Allow users to pass custom weights to override strategy defaults.

**Rationale**: Different users have different prioritization preferences. Making weights configurable allows the algorithm to adapt without code changes.

### 3. Overdue Task Handling

**Decision**: Overdue tasks receive scores exceeding 100 (up to 150) rather than being clamped to 100.

**Rationale**: This ensures overdue tasks always appear at the top of the priority list, regardless of how they score on other factors. This reflects real-world urgency where past-due items require immediate attention.

### 4. Explanation Generation

**Decision**: Each scored task includes a human-readable explanation of why it received its score.

**Rationale**: Transparency in scoring helps users understand and trust the algorithm's recommendations. It also aids in debugging and fine-tuning weight configurations.

### 5. Frontend-Backend Separation

**Decision**: Complete separation between Django backend (API only) and static HTML/CSS/JS frontend.

**Rationale**:
- Cleaner architecture with single responsibility
- Frontend can be served from CDN or static hosting
- API can be consumed by multiple clients (web, mobile, CLI)
- Easier to test each component independently

### Trade-offs Made

1. **No persistence vs. convenience**: Users must provide all tasks on each request, but this simplifies the system and avoids session management.

2. **Linear importance scaling**: Simple and predictable, but doesn't capture non-linear real-world priority differences between, say, importance 9 vs 10.

3. **Static effort thresholds**: Uses fixed hour ranges rather than percentile-based scoring relative to the task set. Simpler to understand but may not adapt well to teams with very different task size distributions.

## API Documentation

### POST /api/tasks/analyze/

Analyze tasks and return them sorted by priority score.

**Request Body:**
```json
{
  "tasks": [
    {
      "id": 1,
      "title": "Fix login bug",
      "due_date": "2025-11-30",
      "estimated_hours": 3,
      "importance": 8,
      "dependencies": []
    }
  ],
  "strategy": "smart_balance",
  "weights": {
    "urgency": 0.35,
    "importance": 0.30,
    "effort": 0.15,
    "dependency": 0.20
  }
}
```

**Response:**
```json
{
  "tasks": [
    {
      "id": 1,
      "title": "Fix login bug",
      "due_date": "2025-11-30",
      "estimated_hours": 3,
      "importance": 8,
      "dependencies": [],
      "priority_score": 75.5,
      "priority_level": "Medium",
      "explanation": "Due in 4 days (this week) | Importance: High (8/10) | Medium task (2-4 hours)",
      "score_breakdown": {
        "urgency": 85,
        "importance": 80,
        "effort": 70,
        "dependency": 0
      }
    }
  ],
  "strategy": "smart_balance",
  "circular_dependencies": [],
  "total_tasks": 1
}
```

### POST /api/tasks/suggest/

Get top N task recommendations with explanations.

**Request Body:**
```json
{
  "tasks": [...],
  "count": 3,
  "strategy": "smart_balance"
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "rank": 1,
      "title": "...",
      "priority_score": 85.5,
      "reason": "Recommended because: urgent deadline, high importance",
      ...
    }
  ],
  "total_tasks": 10,
  "strategy": "smart_balance"
}
```

### GET /api/health/

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "task-analyzer"
}
```

## Future Improvements

With more time, the following enhancements could be implemented:

1. **Eisenhower Matrix View**: Visual 2D grid displaying tasks by Urgent vs Important axes for better decision-making visualization.

2. **Learning System**: Track which suggested tasks users actually complete and adjust algorithm weights based on feedback to personalize recommendations.

3. **Date Intelligence**: Factor in weekends and holidays when calculating urgency. A task due Monday is more urgent on Friday than one due Wednesday.

4. **Dependency Graph Visualization**: Interactive visualization showing task dependencies and highlighting circular dependencies or critical paths.

5. **Task Persistence**: Optional database storage with user accounts to maintain task history and track completion rates.

6. **Recurring Tasks**: Support for tasks that repeat on schedules (daily standup, weekly reports, etc.).

7. **Team Collaboration**: Multi-user support with shared task pools and workload balancing.

8. **Integration APIs**: Connect with popular task management tools (Jira, Asana, Trello) to import/export tasks.

9. **Mobile App**: Native mobile application for on-the-go task management.

10. **Advanced Analytics**: Historical analysis of task completion patterns, estimation accuracy, and productivity trends.

## Project Structure

```
task-analyzer/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── task_analyzer/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── tasks/
│       ├── __init__.py
│       ├── models.py
│       ├── views.py
│       ├── serializers.py
│       ├── scoring.py
│       ├── urls.py
│       └── tests.py
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── script.js
└── README.md
```

## License

This project was created as a technical assessment for Singularium.
