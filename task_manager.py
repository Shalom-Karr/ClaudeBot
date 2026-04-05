"""
Task Manager — In-memory task state tracking for the GroupMe → Copilot pipeline.

Tracks tasks from creation through Gemini prompt crafting, GitHub issue creation,
Copilot assignment, and PR completion.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    """Lifecycle states for a task."""
    RECEIVED = "received"           # GroupMe message received
    PROMPTING = "prompting"         # Gemini is crafting the prompt
    ISSUE_CREATED = "issue_created" # GitHub issue created
    COPILOT_ASSIGNED = "assigned"   # Copilot assigned to the issue
    PR_CREATED = "pr_created"       # Copilot opened a PR
    COMPLETED = "completed"         # PR merged or task done
    FAILED = "failed"               # Something went wrong


@dataclass
class Task:
    """A single task flowing through the pipeline."""
    task_id: str
    description: str
    group_id: str
    requester: str
    status: TaskStatus = TaskStatus.RECEIVED
    gemini_prompt: Optional[str] = None
    issue_number: Optional[int] = None
    issue_url: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.updated_at:
            self.updated_at = self.created_at


class TaskManager:
    """Manages task lifecycle and state."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._group_tasks: dict[str, list[str]] = {}  # group_id -> [task_id, ...]
        self._issue_to_task: dict[int, str] = {}       # issue_number -> task_id
        self._counter: int = 0

    def create_task(self, description: str, group_id: str, requester: str) -> Task:
        """Create a new task and return it."""
        self._counter += 1
        task_id = f"task-{self._counter}"
        task = Task(
            task_id=task_id,
            description=description,
            group_id=group_id,
            requester=requester,
        )
        self._tasks[task_id] = task
        self._group_tasks.setdefault(group_id, []).append(task_id)
        return task

    def update_status(self, task_id: str, status: TaskStatus, **kwargs: object) -> Optional[Task]:
        """Update a task's status and optional fields."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.status = status
        task.updated_at = datetime.now(timezone.utc).isoformat()
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        # Keep the issue→task mapping updated
        if task.issue_number and task.issue_number not in self._issue_to_task:
            self._issue_to_task[task.issue_number] = task_id
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_task_by_issue(self, issue_number: int) -> Optional[Task]:
        """Get a task by its GitHub issue number."""
        task_id = self._issue_to_task.get(issue_number)
        return self._tasks.get(task_id) if task_id else None

    def get_group_tasks(self, group_id: str, limit: int = 5) -> list[Task]:
        """Get recent tasks for a group."""
        task_ids = self._group_tasks.get(group_id, [])
        return [self._tasks[tid] for tid in reversed(task_ids[-limit:])]

    def get_active_task(self, group_id: str) -> Optional[Task]:
        """Get the most recent non-completed task for a group."""
        task_ids = self._group_tasks.get(group_id, [])
        for tid in reversed(task_ids):
            task = self._tasks[tid]
            if task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                return task
        return None
