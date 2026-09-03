from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    material: str = Field(default="PLA", min_length=1, max_length=40)

    @field_validator("name", "material")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("value must not be empty")
        return text


class ProjectUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("project name must not be empty")
        return name


class TaskRead(BaseModel):
    id: str
    project_id: str
    name: str
    type: TaskType
    status: TaskStatus
    progress: int
    updated_at: str
    stage: str | None = None
    error_message: str | None = None
    input_filename: str | None = None
    intermediate_filename: str | None = None
    output_filename: str | None = None


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
    file_kind: Literal["uploaded_model", "generated_model", "gcode"] = "uploaded_model"
    source_task_id: str | None = None
    created_at: str
    temporary: bool = False
    expires_at: str | None = None


class FileSelectionRequest(BaseModel):
    filename: str


class AdminSummaryRead(BaseModel):
    users: int
    projects: int
    tasks: int


class AdminUserRead(BaseModel):
    username: str
    role: str
    status: str
    last_active: str


TpmsType = Literal["gyroid", "schwarz_p", "diamond", "iwp", "neovius", "lidinoid"]


class SlicingRequest(BaseModel):
    input_filename: str | None = None
    infill_mode: Literal["standard", "tpms"] = "standard"
    slicing_engine: Literal["orca", "vsp"] = "orca"
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
    tpms_type: TpmsType = "gyroid"
    tpms_structure_type: Literal["sheet", "rod_negative", "rod_positive"] = "sheet"
    tpms_cell_size: float = Field(default=8, ge=2, le=30)
    tpms_wall_thickness_mm: float = Field(default=0.8, ge=0.2, le=6)
    tpms_level_set_offset: float = Field(default=0, ge=-1.5, le=1.5)
    tpms_gradient_target: Literal["density", "thickness"] = "density"
    tpms_gradient_axis: Literal["x", "y", "z", "radial"] = "x"
    tpms_gradient_start: float = -0.4
    tpms_gradient_end: float = 0.4
    tpms_gradient_curve: Literal["linear", "smooth", "ease_in", "ease_out"] = "linear"
    tpms_phase_x: float = Field(default=0, ge=-3.1416, le=3.1416)
    tpms_phase_y: float = Field(default=0, ge=-3.1416, le=3.1416)
    tpms_phase_z: float = Field(default=0, ge=-3.1416, le=3.1416)
    tpms_invert_field: bool = False
    tpms_quality: Literal["fast", "standard", "high"] = "fast"


class SlicingRunRead(BaseModel):
    task: TaskRead
    gcode_filename: str
    gcode_url: str
    intermediate_model_filename: str | None = None
    intermediate_model_url: str | None = None


class SlicerStatusRead(BaseModel):
    engine: str
    available: bool
    executable: str | None = None
    message: str


class ModelGenerationRequest(BaseModel):
    generation_domain: Literal["block", "boundary"] = "block"
    boundary_mode: Literal["auto", "closed", "footprint"] = "auto"
    tpms_type: TpmsType = "gyroid"
    structure_type: Literal["sheet", "rod_negative", "rod_positive"] = "sheet"
    cell_size: float = Field(default=8, ge=2, le=30)
    cell_size_x: float | None = Field(default=None, ge=2, le=30)
    cell_size_y: float | None = Field(default=None, ge=2, le=30)
    cell_size_z: float | None = Field(default=None, ge=2, le=30)
    cell_count_x: int = Field(default=2, ge=1, le=4)
    cell_count_y: int = Field(default=2, ge=1, le=4)
    cell_count_z: int = Field(default=2, ge=1, le=4)
    wall_thickness_mm: float = Field(default=0.8, ge=0.2, le=6)
    level_set_offset: float = Field(default=0, ge=-1.5, le=1.5)
    phase_shift_x: float = Field(default=0, ge=-3.1416, le=3.1416)
    phase_shift_y: float = Field(default=0, ge=-3.1416, le=3.1416)
    phase_shift_z: float = Field(default=0, ge=-3.1416, le=3.1416)
    gradient_axis: Literal["none", "x", "y", "z"] = "none"
    gradient_strength: float = Field(default=0, ge=-1.5, le=1.5)
    density_gradient_mode: Literal["none", "linear"] = "none"
    density_gradient_axis: Literal["x", "y", "z", "radial"] = "z"
    density_gradient_start_offset: float = Field(default=0, ge=-1.5, le=1.5)
    density_gradient_end_offset: float = Field(default=0, ge=-1.5, le=1.5)
    density_gradient_curve: Literal["linear", "smooth", "ease_in", "ease_out"] = "linear"
    thickness_gradient_mode: Literal["none", "linear"] = "none"
    thickness_gradient_axis: Literal["x", "y", "z", "radial"] = "z"
    thickness_gradient_start_mm: float = Field(default=0.8, ge=0.2, le=6)
    thickness_gradient_end_mm: float = Field(default=0.8, ge=0.2, le=6)
    thickness_gradient_curve: Literal["linear", "smooth", "ease_in", "ease_out"] = "linear"
    density_mode: Literal["manual", "target"] = "manual"
    target_relative_density: float = Field(default=0.3, ge=0.03, le=0.95)
    gyroid_term_weight: float = Field(default=1.0, ge=0.2, le=2.0)
    schwarz_cross_weight: float = Field(default=0.0, ge=-1.0, le=1.0)
    diamond_nodal_weight: float = Field(default=1.0, ge=0.2, le=2.0)
    iwp_second_harmonic_weight: float = Field(default=1.0, ge=0.2, le=2.0)
    neovius_product_weight: float = Field(default=4.0, ge=1.0, le=8.0)
    lidinoid_harmonic_weight: float = Field(default=0.5, ge=0.1, le=1.2)
    lidinoid_bias: float = Field(default=0.15, ge=-0.6, le=0.6)
    invert_field: bool = False
    quality: Literal["fast", "standard", "high"] = "fast"

    @model_validator(mode="after")
    def validate_wall_thickness(self) -> "ModelGenerationRequest":
        smallest_cell_size = min(
            self.cell_size_x or self.cell_size,
            self.cell_size_y or self.cell_size,
            self.cell_size_z or self.cell_size,
        )

        if self.structure_type == "sheet" and self.wall_thickness_mm >= smallest_cell_size / 2:
            raise ValueError("wall_thickness_mm must be less than half the cell size")

        if self.structure_type == "sheet" and self.density_mode == "target":
            raise ValueError("target density mode is only supported for solid modes")

        return self


class ModelGenerationRunRead(BaseModel):
    task: TaskRead
    model_filename: str
    model_url: str
    vertices: int
    triangles: int
    volume_mm3: float
    surface_area_mm2: float
    relative_density: float
    effective_level_set_offset: float
