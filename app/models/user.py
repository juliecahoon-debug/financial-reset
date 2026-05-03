from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    """User model for storing user information"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship to debts
    debts = relationship("Debt", back_populates="user")

    # Add to User class:
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")

    # Add to User class:
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    balance_transfers = relationship("BalanceTransfer", back_populates="user", cascade="all, delete-orphan")
    consolidation_loans = relationship("ConsolidationLoan", back_populates="user", cascade="all, delete-orphan")
    scenarios = relationship("Scenario", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
