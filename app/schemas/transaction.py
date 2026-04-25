from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
from app.schemas.spending import SpendingCategory


class TransactionCreate(BaseModel):
    """Create transaction from CSV import"""
    date: date
    description: str
    amount: float
    merchant: Optional[str] = None
    category: Optional[str] = None
    source_type: str = "csv"  # csv, pdf, plaid
    source_file: Optional[str] = None
    account_type: Optional[str] = None
    account_number: Optional[str] = None


class TransactionUpdate(BaseModel):
    """Update transaction (e.g., fix category)"""
    category: Optional[str] = None
    merchant: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurring_pattern: Optional[str] = None


class TransactionResponse(BaseModel):
    """Transaction response"""
    id: int
    date: date
    description: str
    amount: float
    merchant: Optional[str]
    category: str
    confidence: float
    is_recurring: bool
    recurring_pattern: Optional[str]
    source_type: str
    account_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionSummary(BaseModel):
    """Summary of transactions by category"""
    category: str
    count: int
    total_amount: float
    average_amount: float
    percentage_of_total_spending: float  # % of total spending
    percentage_of_budget: Optional[float] = None  # % of budgeted amount



class RecurringTransaction(BaseModel):
    """Detected recurring transaction"""
    description: str
    merchant: Optional[str]
    amount: float
    pattern: str  # "monthly", "weekly", "bi-weekly", etc
    confidence: float  # How confident in the pattern
    occurrences: int  # How many times detected
    monthly_cost: float
    annual_cost: float
    cancellation_tip: Optional[str] = None


class CSVUploadResponse(BaseModel):
    """Response after CSV upload"""
    file_name: str
    total_transactions: int
    transactions_imported: int
    transactions_with_errors: int
    categories_detected: List[str]
    recurring_detected: int
    message: str


class TransactionAnalysisSummary(BaseModel):
    """Summary of actual transactions vs budget"""
    period: str  # "monthly", "all-time"
    total_transactions: int
    total_spending: float
    average_transaction: float
    largest_transaction: float
    category_summary: List[TransactionSummary]
    recurring_transactions: List[RecurringTransaction]
    top_merchants: List[dict]  # {merchant, amount, count}
    comparison_to_budget: dict  # {category, actual, budgeted, difference}
