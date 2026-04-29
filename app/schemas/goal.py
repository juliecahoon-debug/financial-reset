from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
from enum import Enum


class GoalType(str, Enum):
    HOUSE = "house"
    CAR = "car"
    VACATION = "vacation"
    RETIREMENT = "retirement"
    SAVINGS = "savings"
    EDUCATION = "education"
    OTHER = "other"


class GoalStatus(str, Enum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class GoalCreate(BaseModel):
    """Create goal"""
    goal_type: str
    name: str
    description: Optional[str] = None
    target_amount: float
    target_date: date
    priority: int = 1
    current_savings: float = 0
    annual_return_rate: float = 0.02


class GoalUpdate(BaseModel):
    """Update goal"""
    name: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[float] = None
    target_date: Optional[date] = None
    priority: Optional[int] = None
    current_savings: Optional[float] = None
    annual_return_rate: Optional[float] = None
    status: Optional[str] = None


class GoalResponse(BaseModel):
    """Goal response"""
    id: int
    goal_type: str
    name: str
    target_amount: float
    current_savings: float
    target_date: date
    priority: int
    status: str
    monthly_allocation: Optional[float]
    estimated_completion_date: Optional[date]
    created_at: datetime

    class Config:
        from_attributes = True


class GoalTimeline(BaseModel):
    """Goal timeline with debt payoff integration"""
    goal: GoalResponse
    debt_payoff_month: int
    debt_payoff_date: date
    goal_start_month: int
    goal_start_date: date
    goal_completion_month: int
    goal_completion_date: date
    monthly_allocation: float
    total_months: int
    total_years: float
    total_amount_invested: float
    estimated_interest_earned: float
    final_goal_amount: float


class Scenario(BaseModel):
    """What-if scenario"""
    id: int
    name: str
    monthly_debt_payment: float
    debt_payoff_months: int
    monthly_goal_allocation: float
    annual_return_rate: float
    total_months_to_goal: int
    total_invested: float
    total_interest_earned: float
    final_goal_amount: float
    estimated_credit_score_improvement: int

    class Config:
        from_attributes = True


class ScenarioComparison(BaseModel):
    """Compare multiple scenarios"""
    goal: GoalResponse
    scenarios: List[Scenario]
    recommended_scenario: int
    recommendation_reason: str


class GoalDashboard(BaseModel):
    """User's complete goal dashboard"""
    goals: List[GoalResponse]
    timeline: List[GoalTimeline]
    overall_timeline: dict  # When all goals achievable
    total_monthly_allocation: float
    total_target_amount: float
    total_current_savings: float
