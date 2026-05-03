from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routes.user import router as user_router
from app.routes.auth import router as auth_router
from app.routes.debt import router as debt_router
from app.routes.strategy import router as strategy_router
from app.routes.dashboard import router as dashboard_router
from app.routes.spending import router as spending_router
from app.routes.transaction import router as transaction_router
from app.routes.goal import router as goal_router
from app.routes.balance_transfer import router as balance_transfer_router
from app.routes.consolidation import router as consolidation_router



# Create all database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Financial Reset API",
    description="Debt consolidation and financial optimization with transaction analysis",
    version="0.9.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health():
    """Simple health check"""
    return {
        "status": "healthy",
        "message": "Financial Reset API is running!"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Financial Reset API",
        "docs": "/docs",
        "version": "0.7.0",
        "features": [
            "User authentication",
            "Debt tracking",
            "Optimization strategies",
            "Financial dashboard",
            "Spending analysis",
            "Transaction import & analysis"
        ]
    }

# Include routes
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(debt_router)
app.include_router(strategy_router)
app.include_router(dashboard_router)
app.include_router(spending_router)
app.include_router(transaction_router)
app.include_router(goal_router)
app.include_router(balance_transfer_router)
app.include_router(consolidation_router)
