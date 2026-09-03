from pathlib import Path
from time import time
from typing import Protocol

from backend.app.core.config import settings


class StorageService(Protocol):
    def project_dir(self, user_id: str, project_id: str) -> Path:
        """Return the root storage directory for a user project."""

    def input_dir(self, user_id: str, project_id: str) -> Path:
        """Return the project input model directory."""

    def output_dir(self, user_id: str, project_id: str) -> Path:
        """Return the project output directory."""

    def generated_dir(self, user_id: str, project_id: str) -> Path:
        """Return the generated model directory."""

    def list_input_files(self, user_id: str, project_id: str) -> list[Path]:
        """Return persisted STL/OBJ inputs, newest first."""

    def find_input_file(self, user_id: str, project_id: str, filename: str) -> Path | None:
        """Return one persisted input file when it exists."""

    def list_generated_files(self, user_id: str, project_id: str) -> list[Path]:
        """Return generated STL models, newest first."""

    def find_model_file(self, user_id: str, project_id: str, filename: str) -> Path | None:
        """Return an uploaded or generated model."""

    def set_latest_input_file(self, user_id: str, project_id: str, filename: str) -> None:
        """Persist the model selected by the most recent upload."""

    def latest_input_file(self, user_id: str, project_id: str) -> Path | None:
        """Return the persisted selected model, falling back to the newest input."""

    def delete_input_file(self, user_id: str, project_id: str, filename: str) -> Path | None:
        """Delete one input and return the newly selected input, if any."""

    def list_output_files(self, user_id: str, project_id: str) -> list[Path]:
        """Return persisted G-code outputs, newest first."""

    def find_output_file(self, user_id: str, project_id: str, filename: str) -> Path | None:
        """Return one persisted G-code output when it exists."""

    def delete_output_file(self, user_id: str, project_id: str, filename: str) -> bool:
        """Delete one persisted G-code output."""


class LocalStorageService:
    temporary_input_ttl_seconds = 24 * 60 * 60

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

    def generated_dir(self, user_id: str, project_id: str) -> Path:
        path = self.project_dir(user_id, project_id) / "generated"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def list_input_files(self, user_id: str, project_id: str) -> list[Path]:
        directory = self.input_dir(user_id, project_id)
        cutoff = time() - self.temporary_input_ttl_seconds
        for path in directory.iterdir():
            if path.is_file() and path.suffix.lower() in {".stl", ".obj"} and path.stat().st_mtime < cutoff:
                path.unlink()
        files = [
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in {".stl", ".obj"}
        ]
        return sorted(files, key=lambda path: path.stat().st_mtime_ns, reverse=True)

    def find_input_file(self, user_id: str, project_id: str, filename: str) -> Path | None:
        candidate = self.input_dir(user_id, project_id) / Path(filename).name
        if candidate.is_file() and candidate.suffix.lower() in {".stl", ".obj"}:
            return candidate
        return None

    def list_generated_files(self, user_id: str, project_id: str) -> list[Path]:
        files = [
            path
            for path in self.generated_dir(user_id, project_id).iterdir()
            if path.is_file() and path.suffix.lower() in {".stl", ".obj"}
        ]
        return sorted(files, key=lambda path: path.stat().st_mtime_ns, reverse=True)

    def find_model_file(self, user_id: str, project_id: str, filename: str) -> Path | None:
        uploaded = self.find_input_file(user_id, project_id, filename)
        if uploaded is not None:
            return uploaded
        candidate = self.generated_dir(user_id, project_id) / Path(filename).name
        return candidate if candidate.is_file() and candidate.suffix.lower() in {".stl", ".obj"} else None

    def set_latest_input_file(self, user_id: str, project_id: str, filename: str) -> None:
        selected = self.find_model_file(user_id, project_id, filename)
        if selected is None:
            raise FileNotFoundError(filename)
        pointer = self.project_dir(user_id, project_id) / ".selected-input"
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text(selected.name, encoding="utf-8")

    def latest_input_file(self, user_id: str, project_id: str) -> Path | None:
        pointer = self.project_dir(user_id, project_id) / ".selected-input"
        if pointer.is_file():
            filename = pointer.read_text(encoding="utf-8").strip()
            selected = self.find_model_file(user_id, project_id, filename)
            if selected is not None:
                return selected
        files = self.list_input_files(user_id, project_id)
        return files[0] if files else None

    def delete_input_file(self, user_id: str, project_id: str, filename: str) -> Path | None:
        selected = self.find_input_file(user_id, project_id, filename)
        if selected is None:
            return None
        selected.unlink()

        pointer = self.project_dir(user_id, project_id) / ".selected-input"
        if pointer.is_file() and pointer.read_text(encoding="utf-8").strip() == selected.name:
            pointer.unlink()
        return self.latest_input_file(user_id, project_id)

    def list_output_files(self, user_id: str, project_id: str) -> list[Path]:
        directory = self.output_dir(user_id, project_id)
        files = [
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() == ".gcode"
        ]
        return sorted(files, key=lambda path: path.stat().st_mtime_ns, reverse=True)

    def find_output_file(self, user_id: str, project_id: str, filename: str) -> Path | None:
        candidate = self.output_dir(user_id, project_id) / Path(filename).name
        return candidate if candidate.is_file() and candidate.suffix.lower() == ".gcode" else None

    def delete_output_file(self, user_id: str, project_id: str, filename: str) -> bool:
        output = self.find_output_file(user_id, project_id, filename)
        if output is None:
            return False
        output.unlink()
        return True


def get_storage_service() -> StorageService:
    return LocalStorageService()
