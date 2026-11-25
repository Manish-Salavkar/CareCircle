"""API routers."""

from app.routers.assistant import router as assistant_router
from app.routers.family import router as family_router
from app.routers.health import router as health_router
from app.routers.tasks import router as tasks_router
from app.routers.today import router as today_router

__all__ = [
    "assistant_router",
    "family_router",
    "health_router",
    "tasks_router",
    "today_router",
]
