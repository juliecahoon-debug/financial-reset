from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routes.user import router as user_router

# Create all database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Financial Reset API",
    description="Debt consolidation and financial optimization",
    version="0.1.0"
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
        "version": "0.1.0"
    }

# Include user routes
app.include_router(user_router)
