from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class DebtType(str, enum.Enum):
    """Types of debt"""
    CREDIT_CARD = "credit_card"
    PERSONAL_LOAN = "personal_loan"
    STUDENT_LOAN = "student_loan"
    AUTO_LOAN = "auto_loan"
    MORTGAGE = "mortgage"
    MEDICAL = "medical"
    OTHER = "other"


class DebtStatus(str, enum.Enum):
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

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="debts")

    def __repr__(self):
        return f"<Debt(id={self.id}, user_id={self.user_id}, name={self.name}, balance={self.balance})>"
