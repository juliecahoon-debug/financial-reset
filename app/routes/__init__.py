from app.routes.user import router as user_router
from app.routes.auth import router as auth_router
from app.routes.debt import router as debt_router
from app.routes.hardship import router as hardship_router


__all__ = [
    "user_router",
    "auth_router",
    "debt_router",
    "hardship_router"
]
