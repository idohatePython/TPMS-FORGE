from pathlib import Path
from typing import Protocol

from backend.app.core.config import settings


class StorageService(Protocol):
    def project_dir(self, user_id: int, project_id: int) -> Path:
        """Return the root storage directory for a user project."""


class LocalStorageService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.storage_root

    def project_dir(self, user_id: int, project_id: int) -> Path:
        return self.root / "users" / str(user_id) / "projects" / str(project_id)


def get_storage_service() -> StorageService:
    return LocalStorageService()

