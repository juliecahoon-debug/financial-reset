from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from decimal import Decimal
from app.models.debt import DebtType, DebtStatus

class DebtCreate(BaseModel):
    """Schema for creating a debt"""
    name: str
    debt_type: DebtType
    creditor_name: str
    current_principal: Decimal
    original_balance: Decimal
    minimum_payment: Optional[Decimal] = None
    monthly_payment: Optional[Decimal] = None
    interest_rate: Decimal
    opened_date: Optional[datetime] = None
    due_date_day: Optional[int] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None

class DebtUpdate(BaseModel):
    """Schema for updating a debt"""
    name: Optional[str] = None
    current_principal: Optional[Decimal] = None
    minimum_payment: Optional[Decimal] = None
    monthly_payment: Optional[Decimal] = None
    interest_rate: Optional[Decimal] = None
    status: Optional[DebtStatus] = None
    notes: Optional[str] = None

class DebtResponse(BaseModel):
    """Schema for returning debt data"""
    id: int
    user_id: int
    name: str
    debt_type: DebtType
    status: Optional[DebtStatus]
    current_principal: Decimal
    original_balance: Decimal
    minimum_payment: Optional[Decimal]
    monthly_payment: Optional[Decimal]
    interest_rate: Decimal
    opened_date: Optional[datetime]
    due_date_day: Optional[int]
    paid_off_date: Optional[datetime]
    creditor_name: Optional[str]
    account_number: Optional[str]
    days_past_due: Optional[int]
    in_collections: Optional[bool]
    is_active: Optional[bool]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DebtCalculationResponse(BaseModel):
    """Schema for debt calculation results"""
    debt_id: int
    name: str
    current_principal: Decimal
    interest_rate: Decimal
    monthly_interest: float
    monthly_payment: float
    months_to_payoff: int
    total_interest_paid: float
    total_amount_paid: float
