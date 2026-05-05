from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HardshipPlanCreate(BaseModel):
    """Create hardship plan"""
    debt_id: int
    plan_type: str  # deferment, forbearance, settlement
    reason_for_hardship: str

    # Optional fields depending on type
    deferment_months: Optional[int] = None
    reduced_payment_amount: Optional[float] = None
    forbearance_months: Optional[int] = None
    settlement_percentage: Optional[float] = None


class HardshipPlanResponse(BaseModel):
    """Hardship plan response"""
    id: int
    debt_id: int
    plan_type: str
    status: str
    reason_for_hardship: str
    deferment_months: Optional[int]
    reduced_payment_amount: Optional[float]
    forbearance_months: Optional[int]
    settlement_percentage: Optional[float]
    settlement_amount: Optional[float]
    credit_impact: Optional[str]
    total_cost: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class HardshipPlanOption(BaseModel):
    """Hardship plan option (before applying)"""
    plan_type: str
    description: str
    pros: list[str]
    cons: list[str]
    credit_impact: str
    timeline: str
    estimated_cost: float
