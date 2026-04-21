from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.debt import DebtType, DebtStatus

class DebtCreate(BaseModel):
    """Schema for creating a debt"""
    name: str
    debt_type: DebtType
    balance: float
    original_balance: float
    minimum_payment: Optional[float] = None
    interest_rate: float
    opened_date: Optional[datetime] = None
    due_date: Optional[int] = None
    creditor: Optional[str] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None

class DebtUpdate(BaseModel):
    """Schema for updating a debt"""
    name: Optional[str] = None
    balance: Optional[float] = None
    minimum_payment: Optional[float] = None
    interest_rate: Optional[float] = None
    status: Optional[DebtStatus] = None
    notes: Optional[str] = None

class DebtResponse(BaseModel):
    """Schema for returning debt data"""
    id: int
    user_id: int
    name: str
    debt_type: DebtType
    status: DebtStatus
    balance: float
    original_balance: float
    minimum_payment: Optional[float]
    interest_rate: float
    opened_date: Optional[datetime]
    due_date: Optional[int]
    paid_off_date: Optional[datetime]
    creditor: Optional[str]
    account_number: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DebtCalculationResponse(BaseModel):
    """Schema for debt calculation results"""
    debt_id: int
    name: str
    balance: float
    interest_rate: float
    monthly_interest: float
    monthly_payment: float
    months_to_payoff: int
    total_interest_paid: float
    total_amount_paid: float
