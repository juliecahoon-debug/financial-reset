from typing import Dict
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.models.user import User
from app.dependencies import get_current_user
from app.services.spending_service import SpendingService
from app.schemas.spending import (
    BudgetRecommendation, SpendingEstimate,
    UserSpendingAnalysis, SavingsPotentialAnalysis
)

router = APIRouter(prefix="/spending", tags=["spending"])


class SpendingAnalysisRequest(BaseModel):
    monthly_income: float
    spending_by_category: Dict[str, float]


@router.get("/budget", response_model=BudgetRecommendation)
async def get_budget_recommendation(
        monthly_income: float = Query(..., ge=0),
        current_user: User = Depends(get_current_user)
):
    """Get a 50/30/20 budget recommendation."""
    return SpendingService.get_budget_recommendation(monthly_income)


@router.get("/estimate", response_model=SpendingEstimate)
async def estimate_spending(
        monthly_income: float = Query(..., ge=0),
        current_user: User = Depends(get_current_user)
):
    """Estimate monthly spending based on income."""
    return SpendingService.estimate_spending(monthly_income)


@router.post("/analyze", response_model=UserSpendingAnalysis)
async def analyze_user_spending(
        request: SpendingAnalysisRequest,
        current_user: User = Depends(get_current_user)
):
    """Analyze the user's actual spending against recommendations."""
    return SpendingService.analyze_user_spending(
        request.monthly_income, request.spending_by_category
    )


@router.post("/savings-potential", response_model=SavingsPotentialAnalysis)
async def calculate_savings_potential(
        request: SpendingAnalysisRequest,
        current_user: User = Depends(get_current_user)
):
    """Identify where the user can save money."""
    return SpendingService.calculate_savings_potential(
        request.monthly_income, request.spending_by_category
    )
