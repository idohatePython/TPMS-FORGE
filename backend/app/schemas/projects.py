from typing import Literal

from pydantic import BaseModel

TaskStatus = Literal["queued", "running", "completed", "failed"]
TaskType = Literal["model-generation", "slicing-gcode"]


class ProjectRead(BaseModel):
    id: str
    name: str
    owner: str
    material: str
    model_file: str
    updated_at: str
    status: TaskStatus


class TaskRead(BaseModel):
    id: str
    project_id: str
    name: str
    type: TaskType
    status: TaskStatus
    progress: int
    updated_at: str


class DashboardStatsRead(BaseModel):
    projects: int
    running_tasks: int
    completed_tasks: int
    storage_gb: float


class FileUploadRead(BaseModel):
    project_id: str
    filename: str
    content_type: str | None
    size_bytes: int
    status: Literal["accepted"]


class AdminSummaryRead(BaseModel):
    users: int
    projects: int
    tasks: int


class AdminUserRead(BaseModel):
    username: str
    role: str
    status: str
    last_active: str
