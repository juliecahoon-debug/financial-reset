from app.routes.user import router as user_router
from app.routes.auth import router as auth_router
from app.routes.debt import router as debt_router
from app.routes.strategy import router as strategy_router
from app.routes.dashboard import router as dashboard_router
from app.routes.spending import router as spending_router
from app.routes.transaction import router as transaction_router

__all__ = [
    "user_router", "auth_router", "debt_router", "strategy_router",
    "dashboard_router", "spending_router", "transaction_router"
]
