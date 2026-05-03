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


class Goal(Base):
    """User financial goals"""
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Goal details
    goal_type = Column(String(50), nullable=False)  # house, car, vacation, retirement, savings
    name = Column(String(255), nullable=False)  # "Down payment for house", "New car"
    description = Column(String(500), nullable=True)
    target_amount = Column(Float, nullable=False)
    current_savings = Column(Float, default=0)
    target_date = Column(Date, nullable=False)
    priority = Column(Integer, default=1)  # 1=highest, 10=lowest

    # Metadata
    status = Column(String(50), default="active")  # active, achieved, paused, cancelled
    monthly_allocation = Column(Float, nullable=True)  # Auto-calculated
    estimated_completion_date = Column(Date, nullable=True)

    # Interest/growth assumptions
    annual_return_rate = Column(Float, default=0.02)  # Default 2% (HYSA)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="goals")

    def __repr__(self):
        return f"<Goal {self.id}: {self.name} - ${self.target_amount}>"


class Scenario(Base):
    """What-if scenarios for goal planning"""
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False, index=True)

    # Scenario details
    name = Column(String(255), nullable=False)  # "Conservative", "Aggressive", etc
    description = Column(String(500), nullable=True)

    # Assumptions for this scenario
    monthly_debt_payment = Column(Float, nullable=False)
    monthly_debt_payoff_months = Column(Integer, nullable=False)
    monthly_goal_allocation = Column(Float, nullable=False)
    annual_return_rate = Column(Float, default=0.02)

    # Results
    total_months_to_goal = Column(Integer, nullable=True)
    debt_payoff_month = Column(Integer, nullable=True)
    goal_completion_month = Column(Integer, nullable=True)
    total_invested = Column(Float, nullable=True)
    total_interest_earned = Column(Float, nullable=True)
    final_goal_amount = Column(Float, nullable=True)

    # Credit impact
    estimated_credit_score_improvement = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="scenarios")

    def __repr__(self):
        return f"<Scenario {self.id}: {self.name}>"


class BalanceTransfer(Base):
    """Balance transfer promotional offer"""
    __tablename__ = "balance_transfers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Card details
    card_name = Column(String(255), nullable=False)  # "Chase Sapphire", "Amex Blue", etc
    intro_apr = Column(Float, default=0.0)  # 0% for promo period
    regular_apr = Column(Float, nullable=False)  # APR after promo ends
    promo_months = Column(Integer, nullable=False)  # How long 0% lasts
    balance_transfer_fee = Column(Float, default=0.03)  # 3% is standard
    credit_limit = Column(Float, nullable=False)  # How much you can transfer

    # Status
    status = Column(String(50), default="available")  # available, selected, completed

    # User's decision
    transfer_amount = Column(Float, nullable=True)  # How much they'll transfer
    estimated_monthly_payment = Column(Float, nullable=True)  # What they'll pay

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="balance_transfers")

    def __repr__(self):
        return f"<BalanceTransfer {self.id}: {self.card_name}>"


class ConsolidationLoan(Base):
    """Debt consolidation loan offer"""
    __tablename__ = "consolidation_loans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Loan details
    lender_name = Column(String(255), nullable=False)  # "SoFi", "LendingClub", etc
    loan_amount = Column(Float, nullable=False)  # Total debt being consolidated
    loan_apr = Column(Float, nullable=False)  # Interest rate offered
    loan_term_months = Column(Integer, nullable=False)  # 36, 60, 84 months
    monthly_payment = Column(Float, nullable=False)  # Fixed payment
    origination_fee = Column(Float, default=0.02)  # 2% typical

    # Status
    status = Column(String(50), default="available")  # available, selected, completed

    # Comparison metrics
    total_interest = Column(Float, nullable=True)  # Total interest paid
    total_payoff = Column(Float, nullable=True)  # Principal + interest

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="consolidation_loans")

    def __repr__(self):
        return f"<ConsolidationLoan {self.id}: {self.lender_name}>"
