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
    file_url: str


class AdminSummaryRead(BaseModel):
    users: int
    projects: int
    tasks: int


class AdminUserRead(BaseModel):
    username: str
    role: str
    status: str
    last_active: str


class SlicingRequest(BaseModel):
    layer_height: float = 0.2
    line_width: float = 0.42
    print_speed: int = 60
    travel_speed: int = 150
    wall_loops: int = 2
    top_shell_layers: int = 4
    bottom_shell_layers: int = 3
    sparse_infill_density: int = 15
    sparse_infill_pattern: str = "gyroid"
    enable_support: bool = False
    support_type: str = "normal(auto)"
    brim_width: float = 0
    nozzle_temperature: int = 220
    bed_temperature: int = 60
    filament_type: str = "PLA"


class SlicingRunRead(BaseModel):
    task: TaskRead
    gcode_filename: str
    gcode_url: str
