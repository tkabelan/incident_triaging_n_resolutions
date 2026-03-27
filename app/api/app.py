from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.errors import router as errors_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.logging_config import init_logging


def create_app() -> FastAPI:
    settings = get_settings()
    init_logging(settings.logging)

    app = FastAPI(title=settings.app.name)
    if settings.deployment.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.deployment.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(errors_router, prefix="/api/v1")
    return app
