from fastapi import FastAPI

from backend.app.core.config import settings


def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.get(f"{settings.api_v1_prefix}/health", tags=["system"])(health)
    return app


app = create_app()
