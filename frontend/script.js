/**
 * Smart Task Analyzer - Frontend JavaScript
 * Handles task management, API communication, and UI interactions
 */

// Configuration
const API_BASE_URL = 'http://localhost:8000/api';

// State
let tasks = [];
let taskIdCounter = 1;

// DOM Elements
const taskForm = document.getElementById('task-form');
const taskList = document.getElementById('task-list');
const taskCount = document.getElementById('task-count');
const importanceInput = document.getElementById('importance');
const importanceValue = document.getElementById('importance-value');
const jsonInput = document.getElementById('json-input');
const importJsonBtn = document.getElementById('import-json');
const clearTasksBtn = document.getElementById('clear-tasks');
const analyzeBtn = document.getElementById('analyze-btn');
const resultsSection = document.getElementById('results-section');
const resultsList = document.getElementById('results-list');
const suggestionsList = document.getElementById('suggestions-list');
const warningsContainer = document.getElementById('warnings-container');
const warningsList = document.getElementById('warnings-list');
const loadingOverlay = document.getElementById('loading');

// Tab Elements
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    initializeForm();
    initializeImportance();
    setDefaultDueDate();
});

/**
 * Tab Navigation
 */
function initializeTabs() {
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;

            // Update active states
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(`${tabId}-tab`).classList.add('active');
        });
    });
}

/**
 * Form Initialization and Handlers
 */
function initializeForm() {
    // Task form submission
    taskForm.addEventListener('submit', (e) => {
        e.preventDefault();
        addTaskFromForm();
    });

    // JSON import
    importJsonBtn.addEventListener('click', importTasksFromJson);

    // Clear all tasks
    clearTasksBtn.addEventListener('click', clearAllTasks);

    // Analyze button
    analyzeBtn.addEventListener('click', analyzeTasks);
}

function initializeImportance() {
    importanceInput.addEventListener('input', () => {
        importanceValue.textContent = importanceInput.value;
    });
}

function setDefaultDueDate() {
    const dueDateInput = document.getElementById('due_date');
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    dueDateInput.value = tomorrow.toISOString().split('T')[0];
}

/**
 * Task Management
 */
function addTaskFromForm() {
    const formData = new FormData(taskForm);

    const task = {
        id: taskIdCounter++,
        title: formData.get('title').trim(),
        due_date: formData.get('due_date'),
        estimated_hours: parseFloat(formData.get('estimated_hours')),
        importance: parseInt(formData.get('importance')),
        dependencies: parseDependencies(formData.get('dependencies'))
    };

    // Validation
    if (!task.title) {
        showError('Task title is required');
        return;
    }

    if (!task.due_date) {
        showError('Due date is required');
        return;
    }

    if (isNaN(task.estimated_hours) || task.estimated_hours <= 0) {
        showError('Estimated hours must be a positive number');
        return;
    }

    tasks.push(task);
    renderTaskList();
    updateAnalyzeButton();
    taskForm.reset();
    setDefaultDueDate();
    importanceValue.textContent = '5';
    importanceInput.value = 5;

    showSuccess(`Task "${task.title}" added`);
}

function parseDependencies(depsString) {
    if (!depsString || !depsString.trim()) {
        return [];
    }

    return depsString
        .split(',')
        .map(s => parseInt(s.trim()))
        .filter(n => !isNaN(n));
}

function importTasksFromJson() {
    const jsonText = jsonInput.value.trim();

    if (!jsonText) {
        showError('Please paste a JSON array of tasks');
        return;
    }

    try {
        const importedTasks = JSON.parse(jsonText);

        if (!Array.isArray(importedTasks)) {
            showError('JSON must be an array of tasks');
            return;
        }

        // Validate and add each task
        let addedCount = 0;
        for (const task of importedTasks) {
            if (!validateTask(task)) {
                continue;
            }

            // Assign ID if not present
            if (!task.id) {
                task.id = taskIdCounter++;
            } else {
                taskIdCounter = Math.max(taskIdCounter, task.id + 1);
            }

            // Ensure dependencies is an array
            if (!task.dependencies) {
                task.dependencies = [];
            }

            tasks.push(task);
            addedCount++;
        }

        if (addedCount > 0) {
            renderTaskList();
            updateAnalyzeButton();
            jsonInput.value = '';
            showSuccess(`Imported ${addedCount} task(s)`);
        } else {
            showError('No valid tasks found in JSON');
        }
    } catch (e) {
        showError(`Invalid JSON: ${e.message}`);
    }
}

function validateTask(task) {
    if (!task.title || typeof task.title !== 'string') {
        return false;
    }
    if (!task.due_date) {
        return false;
    }
    if (typeof task.estimated_hours !== 'number' || task.estimated_hours <= 0) {
        return false;
    }
    if (typeof task.importance !== 'number' || task.importance < 1 || task.importance > 10) {
        return false;
    }
    return true;
}

function removeTask(taskId) {
    tasks = tasks.filter(t => t.id !== taskId);
    renderTaskList();
    updateAnalyzeButton();
}

function clearAllTasks() {
    if (tasks.length === 0) return;

    if (confirm('Are you sure you want to clear all tasks?')) {
        tasks = [];
        taskIdCounter = 1;
        renderTaskList();
        updateAnalyzeButton();
        resultsSection.style.display = 'none';
    }
}

/**
 * UI Rendering
 */
function renderTaskList() {
    taskList.innerHTML = '';
    taskCount.textContent = tasks.length;

    tasks.forEach(task => {
        const li = document.createElement('li');
        li.className = 'task-item';
        li.innerHTML = `
            <div class="task-item-info">
                <div class="task-item-title">${escapeHtml(task.title)}</div>
                <div class="task-item-meta">
                    Due: ${task.due_date} | ${task.estimated_hours}h | Importance: ${task.importance}/10
                    ${task.dependencies.length ? ` | Deps: [${task.dependencies.join(', ')}]` : ''}
                </div>
            </div>
            <button class="task-item-remove" onclick="removeTask(${task.id})" title="Remove task">
                &times;
            </button>
        `;
        taskList.appendChild(li);
    });
}

function updateAnalyzeButton() {
    analyzeBtn.disabled = tasks.length === 0;
}

function renderResults(data) {
    resultsSection.style.display = 'block';

    // Render suggestions
    renderSuggestions(data.suggestions || data.tasks.slice(0, 3));

    // Render all tasks
    renderAllTasks(data.tasks);

    // Render warnings (circular dependencies)
    renderWarnings(data.circular_dependencies);

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function renderSuggestions(suggestions) {
    suggestionsList.innerHTML = '';

    suggestions.forEach((task, index) => {
        const card = document.createElement('div');
        card.className = 'suggestion-card';
        card.innerHTML = `
            <div class="suggestion-rank">${index + 1}</div>
            <div class="suggestion-title">${escapeHtml(task.title)}</div>
            <div class="suggestion-score">${task.priority_score.toFixed(1)}</div>
            <div class="suggestion-reason">${task.reason || task.explanation}</div>
        `;
        suggestionsList.appendChild(card);
    });
}

function renderAllTasks(scoredTasks) {
    resultsList.innerHTML = '';

    scoredTasks.forEach(task => {
        const priorityClass = task.priority_level.toLowerCase();
        const card = document.createElement('div');
        card.className = `result-card priority-${priorityClass}`;
        card.innerHTML = `
            <div class="result-score">
                <div class="result-score-value">${task.priority_score.toFixed(1)}</div>
                <div class="result-score-label">Score</div>
            </div>
            <div class="result-info">
                <div class="result-title">
                    ${escapeHtml(task.title)}
                    <span class="priority-badge ${priorityClass}">${task.priority_level}</span>
                </div>
                <div class="result-meta">
                    <span>Due: ${task.due_date}</span>
                    <span>Effort: ${task.estimated_hours}h</span>
                    <span>Importance: ${task.importance}/10</span>
                </div>
                <div class="result-explanation">${escapeHtml(task.explanation)}</div>
            </div>
        `;
        resultsList.appendChild(card);
    });
}

function renderWarnings(circularDeps) {
    if (!circularDeps || circularDeps.length === 0) {
        warningsContainer.style.display = 'none';
        return;
    }

    warningsContainer.style.display = 'block';
    warningsList.innerHTML = '';

    const seen = new Set();
    circularDeps.forEach(([from, to]) => {
        const key = `${Math.min(from, to)}-${Math.max(from, to)}`;
        if (seen.has(key)) return;
        seen.add(key);

        const warning = document.createElement('div');
        warning.className = 'warning-item';
        warning.textContent = `Circular dependency detected: Task ${from} <-> Task ${to}`;
        warningsList.appendChild(warning);
    });
}

/**
 * API Communication
 */
async function analyzeTasks() {
    if (tasks.length === 0) {
        showError('Add at least one task to analyze');
        return;
    }

    const strategy = document.querySelector('input[name="strategy"]:checked').value;

    showLoading(true);

    try {
        // First, get the analysis
        const analyzeResponse = await fetch(`${API_BASE_URL}/tasks/analyze/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                tasks: tasks,
                strategy: strategy
            })
        });

        if (!analyzeResponse.ok) {
            const error = await analyzeResponse.json();
            throw new Error(error.error || 'Analysis failed');
        }

        const analyzeData = await analyzeResponse.json();

        // Then, get suggestions
        const suggestResponse = await fetch(`${API_BASE_URL}/tasks/suggest/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                tasks: tasks,
                strategy: strategy,
                count: 3
            })
        });

        let suggestions = analyzeData.tasks.slice(0, 3);

        if (suggestResponse.ok) {
            const suggestData = await suggestResponse.json();
            suggestions = suggestData.suggestions;
        }

        renderResults({
            tasks: analyzeData.tasks,
            suggestions: suggestions,
            circular_dependencies: analyzeData.circular_dependencies
        });

        showSuccess('Analysis complete!');
    } catch (error) {
        console.error('Analysis error:', error);
        showError(error.message || 'Failed to analyze tasks. Make sure the backend server is running.');
    } finally {
        showLoading(false);
    }
}

/**
 * UI Helpers
 */
function showLoading(show) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
}

function showError(message) {
    showToast('error', message);
}

function showSuccess(message) {
    showToast('success', message);
}

function showToast(type, message) {
    const toast = document.getElementById(`${type}-toast`);
    const messageEl = document.getElementById(`${type}-message`);

    messageEl.textContent = message;
    toast.style.display = 'flex';

    // Auto-hide after 4 seconds
    setTimeout(() => {
        toast.style.display = 'none';
    }, 4000);
}

// Toast close buttons
document.querySelectorAll('.toast-close').forEach(btn => {
    btn.addEventListener('click', () => {
        btn.parentElement.style.display = 'none';
    });
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Expose removeTask to global scope for inline onclick
window.removeTask = removeTask;
