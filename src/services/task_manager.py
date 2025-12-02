"""Task Manager for background task handling.

Implements task state machine with PENDING, RUNNING, COMPLETED, FAILED states.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """Task status enum representing the state machine states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Task dataclass representing a background task.
    
    Attributes:
        task_id: Unique identifier for the task
        status: Current status of the task
        created_at: Timestamp when task was created
        updated_at: Timestamp when task was last updated
        result: Result data when task completes successfully
        error: Error message when task fails
    """
    task_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    result: dict[str, Any] | None = None
    error: str | None = None


class TaskManager:
    """Manages background tasks and their state transitions.
    
    Provides methods to create tasks, update their status, and query task state.
    """
    
    def __init__(self) -> None:
        """Initialize the task manager with an empty task store."""
        self._tasks: dict[str, Task] = {}
    
    def create_task(self) -> str:
        """Create a new task with PENDING status.
        
        Returns:
            The unique task ID for the created task.
        """
        task_id = str(uuid.uuid4())
        now = datetime.utcnow()
        self._tasks[task_id] = Task(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        return task_id
    
    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> bool:
        """Update the status of an existing task.
        
        Args:
            task_id: The ID of the task to update
            status: The new status to set
            result: Optional result data (for COMPLETED status)
            error: Optional error message (for FAILED status)
            
        Returns:
            True if the task was found and updated, False otherwise.
        """
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        task.status = status
        task.updated_at = datetime.utcnow()
        task.result = result
        task.error = error
        return True
    
    def get_task(self, task_id: str) -> Task | None:
        """Get a task by its ID.
        
        Args:
            task_id: The ID of the task to retrieve
            
        Returns:
            The Task object if found, None otherwise.
        """
        return self._tasks.get(task_id)
