from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


class DebtBreakdown(BaseModel):
    """Debt breakdown by type"""
    debt_type: str
    count: int
    total_balance: float
    total_minimum_payment: float
    average_apr: float


class DebtStatus(BaseModel):
    """Debt status breakdown"""
    status: str
    count: int
    total_balance: float


class DashboardSummary(BaseModel):
    """Complete financial dashboard summary"""
    total_debt: float
    total_assets: Optional[float] = 0  # For future use
    net_worth: Optional[float] = 0

    monthly_income: float
    total_monthly_payments: float
    available_monthly_cash: float  # Income minus debt payments

    debt_to_income_ratio: float
    urgency_score: int  # 0-100
    urgency_level: str  # Critical, High, Moderate, Low, Healthy

    total_debts_count: int
    active_debts_count: int
    paid_off_debts_count: int

    average_apr: float
    highest_apr: float
    lowest_apr: float

    months_to_debt_free_minimum: int
    months_to_debt_free_recommended: int

    debt_breakdown_by_type: List[DebtBreakdown]
    debt_breakdown_by_status: List[DebtStatus]


class EmergencyFundRecommendation(BaseModel):
    """Emergency fund recommendation"""
    current_emergency_fund: float
    recommended_amount: float
    months_of_expenses: float
    savings_needed: float
    priority: str  # "Critical", "High", "Moderate", "Low"
    reason: str


class CashFlowAnalysis(BaseModel):
    """Monthly cash flow analysis"""
    monthly_income: float
    fixed_debt_payments: float
    flexible_spending: Optional[float] = None
    remaining_after_debt: float
    cash_flow_health: str  # "Positive", "Tight", "Negative"
    recommendations: List[str]


class FinancialHealthMetrics(BaseModel):
    """Comprehensive financial health metrics"""
    debt_to_income: float
    payment_to_income: float
    apr_average: float
    debt_count: int
    payment_months: int
    urgency_score: int
    overall_health_score: int  # 0-100
    health_rating: str  # A, B, C, D, F


class DebtPayoffProjection(BaseModel):
    """Projection for debt payoff with current payment"""
    strategy: str  # "Avalanche", "Snowball"
    total_months: int
    total_years: float
    total_interest: float
    monthly_payment_recommended: float
    payoff_date: datetime


class FinancialGoal(BaseModel):
    """Financial goal tracking"""
    goal_type: str  # "DebtFree", "EmergencyFund", "SavingsTarget"
    current_progress: float
    target_amount: float
    progress_percentage: float
    months_to_goal: int
    status: str  # "On Track", "Behind", "Ahead"
