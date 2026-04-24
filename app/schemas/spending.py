from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum

class SpendingCategory(str, Enum):
    """Spending categories"""
    HOUSING = "housing"  # Rent/mortgage
    UTILITIES = "utilities"  # Gas, electric, water
    TRANSPORTATION = "transportation"  # Car payment, gas, insurance
    GROCERIES = "groceries"  # Food
    DINING = "dining"  # Restaurants, delivery
    ENTERTAINMENT = "entertainment"  # Movies, games, etc
    SHOPPING = "shopping"  # Clothes, non-essentials
    INSURANCE = "insurance"  # Health, auto, renters
    HEALTHCARE = "healthcare"  # Medical expenses
    SUBSCRIPTIONS = "subscriptions"  # Netflix, gym, etc
    PERSONAL_CARE = "personal_care"  # Haircuts, toiletries
    EDUCATION = "education"  # Courses, books
    DEBT_PAYMENTS = "debt_payments"  # Minimum debt payments
    SAVINGS = "savings"  # Emergency fund, retirement
    OTHER = "other"  # Miscellaneous

class BudgetCategory(BaseModel):
    """Budget allocation for a category"""
    category: SpendingCategory
    recommended_amount: float
    recommended_percentage: float
    notes: str

class BudgetRecommendation(BaseModel):
    """Budget recommendation based on income"""
    monthly_income: float
    budget_model: str  # "50/30/20" or "custom"
    needs_budget: float  # Essential (housing, food, utilities)
    needs_percentage: float
    wants_budget: float  # Lifestyle (dining, entertainment)
    wants_percentage: float
    savings_debt_budget: float  # Savings + debt payoff
    savings_debt_percentage: float
    categories: List[BudgetCategory]
    notes: str

class SpendingBreakdown(BaseModel):
    """User's spending breakdown"""
    category: SpendingCategory
    amount: float
    percentage: float
    vs_recommended: float  # Over/under recommendation
    status: str  # "Good", "Over", "Under"

class UserSpendingAnalysis(BaseModel):
    """Complete spending analysis for user"""
    monthly_income: float
    total_monthly_spending: float
    spending_percentage: float  # Spending as % of income
    remaining_after_spending: float
    discretionary_spending: float  # Entertainment, dining, shopping
    essential_spending: float  # Housing, utilities, groceries
    debt_payments: float
    breakdown_by_category: List[SpendingBreakdown]

class SavingsPotential(BaseModel):
    """Savings potential by category"""
    category: SpendingCategory
    current_spending: float
    recommended_spending: float
    potential_savings: float
    savings_percentage: float
    difficulty: str  # "Easy", "Medium", "Hard"
    tips: List[str]

class SavingsPotentialAnalysis(BaseModel):
    """Complete savings potential analysis"""
    total_current_spending: float
    total_recommended_spending: float
    total_potential_savings: float
    savings_percentage: float
    top_savings_opportunities: List[SavingsPotential]
    monthly_recommendation: str
    impact_on_debt_payoff: str  # "Could pay off X months faster"

class SpendingEstimate(BaseModel):
    """Estimated spending based on income"""
    monthly_income: float
    estimated_housing: float
    estimated_utilities: float
    estimated_transportation: float
    estimated_groceries: float
    estimated_dining: float
    estimated_entertainment: float
    estimated_subscriptions: float
    estimated_other: float
    total_estimated: float
    remaining_for_debt: float
    recommended_debt_payment: float
