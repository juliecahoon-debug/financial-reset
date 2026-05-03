from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BalanceTransferCreate(BaseModel):
    """Create balance transfer"""
    card_name: str
    intro_apr: float = 0.0
    regular_apr: float
    promo_months: int
    balance_transfer_fee: float = 0.03
    credit_limit: float


class BalanceTransferUpdate(BaseModel):
    """Update balance transfer"""
    transfer_amount: Optional[float] = None
    status: Optional[str] = None


class BalanceTransferResponse(BaseModel):
    """Balance transfer response"""
    id: int
    card_name: str
    intro_apr: float
    regular_apr: float
    promo_months: int
    balance_transfer_fee: float
    credit_limit: float
    transfer_amount: Optional[float]
    estimated_monthly_payment: Optional[float]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class BalanceTransferComparison(BaseModel):
    """Balance transfer vs current strategy comparison"""
    current_strategy: dict  # Avalanche/Snowball result
    balance_transfer_strategy: dict  # BT result
    interest_saved: float
    months_saved: int
    recommendation: str
