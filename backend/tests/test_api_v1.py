from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.modules.admin.router import read_admin_summary
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.auth.router import login, read_me
from backend.app.modules.files.router import upload_project_file
from backend.app.modules.model_tasks.router import read_model_task
from backend.app.modules.projects.router import list_projects, read_project
from backend.app.modules.slicing_tasks.router import read_slicing_task
from backend.app.schemas.auth import LoginRequest, UserRead


def make_user(role: str = "user") -> UserRead:
    if role == "admin":
        return UserRead(id="admin-001", username="machuang", role="admin")
    return UserRead(id="user-001", username="machuang", role="user")


def test_login_and_read_current_user() -> None:
    token = login(LoginRequest(username="machuang", password="dev-only", role="admin"))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token.access_token)
    current_user = get_current_user(credentials)

    response = read_me(current_user)

    assert response.username == "machuang"
    assert response.role == "admin"


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

    assert response.projects >= 1


def test_upload_accepts_stl_and_rejects_unknown_project() -> None:
    current_user = make_user()
    file = UploadFile(filename="part.stl", file=BytesIO(b"solid mock"))

    response = upload_project_file("p-1001", current_user, file)

    assert response.filename == "part.stl"

    with pytest.raises(HTTPException) as error:
        missing_file = UploadFile(filename="part.stl", file=BytesIO(b"solid mock"))
        upload_project_file("missing", current_user, missing_file)

    assert error.value.status_code == 404
