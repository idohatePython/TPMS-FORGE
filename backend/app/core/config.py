from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TPMS-FORGE"
    app_env: str = "development"
    debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    secret_key: str = "change-me"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ]

    database_url: str = "postgresql+psycopg://tpms_forge:tpms_forge@localhost:5432/tpms_forge"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    storage_backend: str = "local"
    storage_root: Path = Path("storage")
    max_upload_size_mb: int = 200

    slicer_engine: str = "orca"
    orca_slicer_path: str = "orca-slicer"
    orca_machine_profile: Path | None = None
    orca_process_profile: Path | None = None
    orca_filament_profile: Path | None = None
    orca_windows_work_dir: Path | None = None
    vsp_slicer_path: Path | None = None
    prusa_slicer_path: str = "prusa-slicer"
    slicer_timeout_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
