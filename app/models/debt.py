from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
from enum import Enum

class DebtType(str, Enum):
    """Types of debt"""
    CREDIT_CARD = "credit_card"
    PERSONAL_LOAN = "personal_loan"
    STUDENT_LOAN = "student_loan"
    AUTO_LOAN = "auto_loan"
    MORTGAGE = "mortgage"
    MEDICAL = "medical"
    OTHER = "other"


class DebtStatus(str, Enum):
    """Status of debt"""
    ACTIVE = "active"
    PAID_OFF = "paid_off"
    IN_HARDSHIP = "in_hardship"
    SETTLED = "settled"


class Debt(Base):
    """Debt model for storing user debts"""
    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Debt details
    name = Column(String(255), nullable=False)  # e.g., "Chase Credit Card"
    debt_type = Column(SQLEnum(DebtType), default=DebtType.CREDIT_CARD)
    status = Column(SQLEnum(DebtStatus), default=DebtStatus.ACTIVE)

    # Financial details
    balance = Column(Float, nullable=False)  # Current balance owed
    original_balance = Column(Float, nullable=False)  # Original amount borrowed
    minimum_payment = Column(Float)  # Minimum monthly payment
    interest_rate = Column(Float, nullable=False)  # Annual percentage rate (APR)

    # Dates
    opened_date = Column(DateTime)  # When account was opened
    due_date = Column(Integer)  # Day of month payment is due (1-31)
    paid_off_date = Column(DateTime)  # When debt was paid off

    # Metadata
    creditor = Column(String(255))  # Name of creditor/lender
    account_number = Column(String(255))  # Last 4 digits or masked number
    notes = Column(String(1000))  # Additional notes

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="debts")

    def __repr__(self):
        return f"<Debt(id={self.id}, user_id={self.user_id}, name={self.name}, balance={self.balance})>"


# Add to imports at top:
from app.schemas.spending import SpendingCategory


# Add this class to the file:
class Transaction(Base):
    """User bank transactions from CSV/PDF uploads"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Transaction details
    date = Column(Date, nullable=False, index=True)
    description = Column(String(500), nullable=False)
    amount = Column(Float, nullable=False)
    merchant = Column(String(255), nullable=True)

    # Categorization
    category = Column(String(50), nullable=True, default="other")  # SpendingCategory value
    confidence = Column(Float, default=0.5)  # How confident in auto-categorization (0-1)

    # Recurring detection
    is_recurring = Column(Boolean, default=False)
    recurring_pattern = Column(String(100), nullable=True)  # "monthly", "weekly", etc
    recurring_group_id = Column(Integer, nullable=True)  # Groups recurring transactions

    # Source info
    source_type = Column(String(50), nullable=False)  # "csv", "pdf", "plaid"
    source_file = Column(String(255), nullable=True)  # Original file name
    account_type = Column(String(50), nullable=True)  # "checking", "savings", "credit_card"
    account_number = Column(String(20), nullable=True)  # Last 4 digits

    # Metadata
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction {self.id}: {self.merchant} ${self.amount}>"
