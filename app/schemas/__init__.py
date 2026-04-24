from app.schemas.user import UserCreate, UserUpdate, UserResponse, LoginRequest, TokenResponse
from app.schemas.debt import DebtCreate, DebtUpdate, DebtResponse, DebtCalculationResponse
from app.schemas.strategy import (
    StrategyType, DebtPayoffProjection, StrategyProjection,
    StrategyComparison, FinancialScore, StrategyRecommendation
)
from app.schemas.spending import (
    SpendingCategory, BudgetCategory, BudgetRecommendation,
    SpendingBreakdown, UserSpendingAnalysis, SavingsPotential,
    SavingsPotentialAnalysis, SpendingEstimate
)
from app.schemas.dashboard import (
    DebtBreakdown, DashboardSummary, EmergencyFundRecommendation,
    CashFlowAnalysis, FinancialHealthMetrics, DebtPayoffProjection,
    FinancialGoal
)

__all__ = [
    "UserCreate", "UserUpdate", "UserResponse", "LoginRequest", "TokenResponse",
    "DebtCreate", "DebtUpdate", "DebtResponse", "DebtCalculationResponse",
    "StrategyType", "DebtPayoffProjection", "StrategyProjection",
    "StrategyComparison", "FinancialScore", "StrategyRecommendation",
    "DebtBreakdown", "DashboardSummary", "EmergencyFundRecommendation",
    "CashFlowAnalysis", "FinancialHealthMetrics", "FinancialGoal",
    "SpendingCategory", "BudgetCategory", "BudgetRecommendation",
    "SpendingBreakdown", "UserSpendingAnalysis", "SavingsPotential",
    "SavingsPotentialAnalysis", "SpendingEstimate"
]

