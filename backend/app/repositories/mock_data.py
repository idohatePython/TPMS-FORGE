from backend.app.schemas.projects import DashboardStatsRead, ProjectRead, TaskRead

PROJECTS: list[ProjectRead] = [
    ProjectRead(
        id="p-1001",
        name="Gyroid 轻量化支架",
        owner="machuang",
        material="PLA",
        model_file="bracket_raw.stl",
        updated_at="2026-07-03 10:35",
        status="running",
    ),
    ProjectRead(
        id="p-1002",
        name="Schwarz-P 多孔夹具",
        owner="machuang",
        material="PETG",
        model_file="fixture.obj",
        updated_at="2026-07-02 18:20",
        status="completed",
    ),
    ProjectRead(
        id="p-1003",
        name="Diamond 热交换样件",
        owner="researcher",
        material="Resin",
        model_file="heat_exchanger.stl",
        updated_at="2026-07-01 14:08",
        status="queued",
    ),
]

TASKS: list[TaskRead] = [
    TaskRead(
        id="mg-2048",
        project_id="p-1001",
        name="Gyroid 边界填充生成",
        type="model-generation",
        status="running",
        progress=64,
        updated_at="2026-07-03 10:41",
    ),
    TaskRead(
        id="sg-1024",
        project_id="p-1002",
        name="0.2mm 层高 G-code",
        type="slicing-gcode",
        status="completed",
        progress=100,
        updated_at="2026-07-02 19:04",
    ),
    TaskRead(
        id="mg-2049",
        project_id="p-1003",
        name="Diamond 单元阵列预览",
        type="model-generation",
        status="queued",
        progress=0,
        updated_at="2026-07-01 14:12",
    ),
]

PROJECT_FILES: dict[str, str] = {}
PROJECT_GCODE_FILES: dict[str, str] = {}

DASHBOARD_STATS = DashboardStatsRead(
    projects=len(PROJECTS),
    running_tasks=sum(task.status == "running" for task in TASKS),
    completed_tasks=sum(task.status == "completed" for task in TASKS),
    storage_gb=12.4,
)
