"""
Core data models for the Claude Debugger system.
"""
import uuid
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Type of debugging task."""
    BUG = "Bug"
    FEATURE_TEST = "Feature Test"


class TaskStatus(str, Enum):
    """Status of a debugging task."""
    ENQUEUED = "ENQUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskItem(BaseModel):
    """A debugging task item to be processed."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_root: Path
    task_type: TaskType
    description: str
    status: TaskStatus = TaskStatus.ENQUEUED
    created_at: Optional[str] = None

    class Config:
        """Pydantic config."""
        use_enum_values = True
        arbitrary_types_allowed = True


class UiEvent(BaseModel):
    """Event to be sent to the UI thread."""
    kind: str
    task_id: uuid.UUID
    payload: str

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True


class StepResult(BaseModel):
    """Result of a pipeline step."""
    success: bool
    output: str
    sentinel_found: bool = False
    error: Optional[str] = None