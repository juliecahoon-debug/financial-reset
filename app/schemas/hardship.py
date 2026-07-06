from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime
from app.models.debt import ReliefProgramType


class HardshipPlanCreate(BaseModel):
    """Create hardship plan"""
    debt_id: int
    program_type: ReliefProgramType  # deferment, forbearance, settlement, etc.
    description: Optional[str] = None

    # Optional financial terms depending on type
    duration_months: Optional[int] = None
    monthly_payment_during: Optional[Decimal] = None
    settlement_percentage: Optional[Decimal] = None
    settlement_lump_sum: Optional[Decimal] = None


class HardshipPlanResponse(BaseModel):
    """Hardship plan response"""
    id: int
    debt_id: int
    hardship_case_id: int
    program_type: ReliefProgramType
    program_name: Optional[str]
    status: str
    description: Optional[str]
    duration_months: Optional[int]
    monthly_payment_during: Optional[Decimal]
    settlement_percentage: Optional[Decimal]
    settlement_lump_sum: Optional[Decimal]
    credit_reporting_treatment: Optional[str]
    total_cost: Optional[Decimal]
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
