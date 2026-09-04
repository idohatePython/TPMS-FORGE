from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.logging import configure_logging
from backend.app.modules.admin.router import router as admin_router
from backend.app.modules.auth.router import router as auth_router
from backend.app.modules.demo.router import router as demo_router
from backend.app.modules.files.router import router as files_router
from backend.app.modules.model_tasks.router import project_router as project_model_tasks_router
from backend.app.modules.model_tasks.router import router as model_tasks_router
from backend.app.modules.projects.router import dashboard_router
from backend.app.modules.projects.router import router as projects_router
from backend.app.modules.slicing_tasks.router import project_router as project_slicing_tasks_router
from backend.app.modules.slicing_tasks.router import router as slicing_tasks_router


def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-TPMS-Vertices",
            "X-TPMS-Triangles",
            "X-TPMS-Duration-Ms",
        ],
    )

    app.get(f"{settings.api_v1_prefix}/health", tags=["system"])(health)
    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(demo_router, prefix=settings.api_v1_prefix)
    app.include_router(dashboard_router, prefix=settings.api_v1_prefix)
    app.include_router(projects_router, prefix=settings.api_v1_prefix)
    app.include_router(files_router, prefix=settings.api_v1_prefix)
    app.include_router(project_model_tasks_router, prefix=settings.api_v1_prefix)
    app.include_router(model_tasks_router, prefix=settings.api_v1_prefix)
    app.include_router(project_slicing_tasks_router, prefix=settings.api_v1_prefix)
    app.include_router(slicing_tasks_router, prefix=settings.api_v1_prefix)
    app.include_router(admin_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
