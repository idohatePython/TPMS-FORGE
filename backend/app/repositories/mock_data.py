from backend.app.schemas.projects import ProjectRead, TaskRead

PROJECTS: list[ProjectRead] = [
    ProjectRead(
        id="p-1001",
        name="Gyroid 轻量化支架",
        owner="machuang",
        material="PLA",
        model_file="",
        updated_at="2026-07-03 10:35",
        status="queued",
    ),
    ProjectRead(
        id="p-1002",
        name="Schwarz-P 多孔夹具",
        owner="machuang",
        material="PETG",
        model_file="",
        updated_at="2026-07-02 18:20",
        status="queued",
    ),
    ProjectRead(
        id="p-1003",
        name="Diamond 热交换样件",
        owner="researcher",
        material="Resin",
        model_file="",
        updated_at="2026-07-01 14:08",
        status="queued",
    ),
]

TASKS: list[TaskRead] = []

PROJECT_FILES: dict[str, str] = {}
PROJECT_GCODE_FILES: dict[str, str] = {}
PROJECT_MODEL_TASK_FILES: dict[str, str] = {}
