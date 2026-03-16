from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.logging_config import init_logging


def create_app() -> FastAPI:
    settings = get_settings()
    init_logging(settings.logging)

    app = FastAPI(title=settings.app.name)
    app.include_router(health_router, prefix="/api/v1")
    return app
