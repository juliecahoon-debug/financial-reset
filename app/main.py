import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routes.user import router as user_router
from app.routes.auth import router as auth_router
from app.routes.debt import router as debt_router
from app.routes.hardship import router as hardship_router
from app.routes.collections import router as collection_router
from app.routes.resilience import router as resilience_router
from app.routes.strategy import router as strategy_router
from app.routes.dashboard import router as dashboard_router
from app.routes.spending import router as spending_router
from app.routes.goals import router as goals_router
from app.routes.balance_transfer import router as balance_transfer_router
from app.routes.transactions import router as transactions_router
from app.routes.calculators import router as calculators_router



# Create all database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Navorafi API",
    description="Financial crisis navigation - hardship programs, settlement, collections guidance",
    version="2.0.0-full"
)

# CORS middleware - origins from environment, defaults to localhost for development
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5000,http://localhost:8081,http://localhost:19006,http://127.0.0.1:5000")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
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
        "version": "2.0.0-full",
        "features": [
            "User authentication",
            "Debt tracking",
            "Hardship programs",
            "Collections guidance",
            "Resilience scoring",
            "Optimization strategies (avalanche/snowball)",
            "Financial dashboard & health metrics",
            "Spending analysis & budgeting",
            "Savings goals & scenarios",
            "Balance transfer planning",
            "Transaction import & analysis (CSV/PDF)",
            "Financial calculators"
        ]
    }

# Include routes
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(debt_router)
app.include_router(hardship_router)
app.include_router(collection_router)
app.include_router(resilience_router)
app.include_router(strategy_router)
app.include_router(dashboard_router)
app.include_router(spending_router)
app.include_router(goals_router)
app.include_router(balance_transfer_router)
app.include_router(transactions_router)
app.include_router(calculators_router)