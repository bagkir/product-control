from typing import Any, Literal

from pydantic import BaseModel

TaskStatus = Literal[
    "PENDING",
    "STARTED",
    "PROGRESS",
    "SUCCESS",
    "FAILURE",
    "RETRY",
]


class TaskProgress(BaseModel):
    current: int
    total: int
    progress: float


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: dict[str, Any] | TaskProgress | None = None
    message: str | None = None
