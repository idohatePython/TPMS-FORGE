from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.core.config import settings
from backend.app.modules.admin.router import list_admin_users, read_admin_summary
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.auth.router import login, read_me
from backend.app.modules.files.router import (
    delete_project_file,
    delete_project_gcode_file,
    list_project_files,
    list_project_gcode_files,
    read_latest_project_file,
    upload_project_file,
)
from backend.app.modules.model_tasks.router import read_model_task
from backend.app.modules.projects.router import list_projects, read_project
from backend.app.modules.slicing_tasks.router import read_slicing_task
from backend.app.repositories.mock_data import PROJECT_FILES
from backend.app.schemas.auth import LoginRequest, UserRead
from backend.app.services.storage import get_storage_service


def make_user(role: str = "user") -> UserRead:
    if role == "admin":
        return UserRead(id="admin-001", username="machuang", role="admin")
    return UserRead(id="user-001", username="machuang", role="user")


def test_login_regular_user_and_read_current_user() -> None:
    token = login(LoginRequest(identifier="researcher", password="dev-only"))
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token.access_token,
    )
    current_user = get_current_user(credentials)

    response = read_me(current_user)

    assert response.username == "researcher"
    assert response.role == "user"


def test_login_admin_role_is_decided_by_account() -> None:
    token = login(LoginRequest(identifier="admin", password="admin-only"))

    assert token.user.username == "admin"
    assert token.user.role == "admin"

@pytest.mark.parametrize(
    ("identifier", "password"),
    [
        ("researcher", "wrong-password"),
        ("admin", "wrong-password"),
        ("missing-user", "dev-only"),
    ],
)
def test_login_rejects_invalid_credentials(
    identifier: str,
    password: str,
) -> None:
    with pytest.raises(HTTPException) as error:
        login(
            LoginRequest(
                identifier=identifier,
                password=password,
            )
        )

    assert error.value.status_code == 401
    assert error.value.detail == "账号或密码错误"
    
def test_projects_require_authentication_dependency() -> None:
    with pytest.raises(HTTPException) as error:
        get_current_user(None)

    assert error.value.status_code == 401


def test_list_and_read_projects() -> None:
    current_user = make_user()

    projects = list_projects(current_user)
    project = read_project("p-1001", current_user)

    assert projects[0].id == "p-1001"
    assert project.model_file == "bracket_raw.stl"


def test_read_task_endpoints() -> None:
    current_user = make_user()

    model_task = read_model_task("mg-2048", current_user)
    slicing_task = read_slicing_task("sg-1024", current_user)

    assert model_task.type == "model-generation"
    assert slicing_task.type == "slicing-gcode"


def test_admin_endpoint_requires_admin_role() -> None:
    response = read_admin_summary(make_user("admin"))
    users = list_admin_users(make_user("admin"))

    assert response.projects >= 1
    assert users[0].username == "machuang"


def test_upload_accepts_stl_and_rejects_unknown_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "storage_root", tmp_path)
    current_user = make_user()
    file = UploadFile(filename="part.stl", file=BytesIO(b"solid mock"))

    response = upload_project_file("p-1001", current_user, file)

    assert response.filename == "part.stl"

    with pytest.raises(HTTPException) as error:
        missing_file = UploadFile(filename="part.stl", file=BytesIO(b"solid mock"))
        upload_project_file("missing", current_user, missing_file)

    assert error.value.status_code == 404


def test_uploaded_models_persist_without_the_in_memory_file_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "storage_root", tmp_path)
    current_user = make_user()
    first = UploadFile(filename="first.stl", file=BytesIO(b"solid first"))
    second = UploadFile(filename="Phone Holder.stl", file=BytesIO(b"solid phone holder"))

    upload_project_file("p-1001", current_user, first)
    upload_project_file("p-1001", current_user, second)
    PROJECT_FILES.clear()

    saved_files = list_project_files("p-1001", current_user)
    latest = read_latest_project_file("p-1001", current_user)

    assert {file.filename for file in saved_files} == {"first.stl", "Phone Holder.stl"}
    assert latest.filename == "Phone Holder.stl"
    assert Path(PROJECT_FILES["p-1001"]).exists()


def test_project_file_management_lists_and_deletes_models_and_gcode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "storage_root", tmp_path)
    current_user = make_user()
    model = UploadFile(filename="part.stl", file=BytesIO(b"solid"))
    upload_project_file("p-1001", current_user, model)

    output = get_storage_service().output_dir(current_user.id, "p-1001") / "part.gcode"
    output.write_text("G1 X1 Y1", encoding="utf-8")

    assert [file.filename for file in list_project_files("p-1001", current_user)] == ["part.stl"]
    gcode_files = list_project_gcode_files("p-1001", current_user)
    assert [file.filename for file in gcode_files] == ["part.gcode"]

    assert delete_project_file("p-1001", "part.stl", current_user).status_code == 204
    assert delete_project_gcode_file("p-1001", "part.gcode", current_user).status_code == 204
    model_path = (
        tmp_path / "users" / current_user.id / "projects" / "p-1001" / "inputs" / "part.stl"
    )
    assert not model_path.exists()
    assert not output.exists()
