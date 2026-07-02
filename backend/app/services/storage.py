from pathlib import Path
from typing import Protocol

from backend.app.core.config import settings


class StorageService(Protocol):
    def project_dir(self, user_id: str, project_id: str) -> Path:
        """Return the root storage directory for a user project."""

    def input_dir(self, user_id: str, project_id: str) -> Path:
        """Return the project input model directory."""

    def output_dir(self, user_id: str, project_id: str) -> Path:
        """Return the project output directory."""


class LocalStorageService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.storage_root

    def project_dir(self, user_id: str, project_id: str) -> Path:
        return self.root / "users" / str(user_id) / "projects" / str(project_id)

    def input_dir(self, user_id: str, project_id: str) -> Path:
        path = self.project_dir(user_id, project_id) / "inputs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def output_dir(self, user_id: str, project_id: str) -> Path:
        path = self.project_dir(user_id, project_id) / "outputs"
        path.mkdir(parents=True, exist_ok=True)
        return path


def get_storage_service() -> StorageService:
    return LocalStorageService()
