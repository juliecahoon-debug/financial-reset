from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class StrategyType(str, Enum):
    """Types of debt payoff strategies"""
    AVALANCHE = "avalanche"  # Highest APR first
    SNOWBALL = "snowball"    # Lowest balance first
    CUSTOM = "custom"        # Custom payment amounts

class DebtPayoffProjection(BaseModel):
    """Projection for a single debt"""
    debt_id: int
    debt_name: str
    months_to_payoff: int
    total_interest_paid: float
    payoff_order: int  # Order in which debt will be paid off

class StrategyProjection(BaseModel):
    """Complete strategy projection"""
    strategy_type: StrategyType
    total_months: int  # Total months to pay off all debt
    total_years: float
    total_interest_paid: float
    total_amount_paid: float
    monthly_payment_needed: float
    debt_payoff_order: List[DebtPayoffProjection]

class StrategyComparison(BaseModel):
    """Comparison of different strategies"""
    avalanche: StrategyProjection
    snowball: StrategyProjection
    recommended: StrategyType
    savings: dict  # {"interest_saved": X, "months_saved": Y}

class FinancialScore(BaseModel):
    """User's financial score and urgency"""
    debt_to_income_ratio: float  # Total debt / monthly income
    urgency_score: int  # 0-100 (higher = more urgent)
    urgency_level: str  # "Critical", "High", "Moderate", "Low", "Healthy"
    total_debt: float
    total_monthly_income: float
    average_interest_rate: float
    monthly_payment_capacity: float
    months_to_debt_free_minimum: int  # With minimum payments
    recommended_monthly_payment: float

class StrategyRecommendation(BaseModel):
    """Recommended strategy for user"""
    recommended_strategy: StrategyType
    reason: str
    monthly_payment_suggested: float
    timeline_months: int
    total_interest_with_strategy: float
    urgency_assessment: str
