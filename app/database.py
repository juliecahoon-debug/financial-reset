from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get database URL from .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Create database engine
engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
