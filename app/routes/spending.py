from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.spending_service import SpendingService
from app.schemas.spending import (
    BudgetRecommendation, SpendingEstimate,
    UserSpendingAnalysis, SavingsPotentialAnalysis
)

router = APIRouter(prefix="/spending", tags=["spending"])


@router.get("/budget-recommendation", response_model=BudgetRecommendation)
async def get_budget_recommendation(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get budget recommendation based on 50/30/20 rule"""

    recommendation = SpendingService.get_budget_recommendation(monthly_income)
    return recommendation


@router.get("/estimate", response_model=SpendingEstimate)
async def estimate_spending(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get estimated spending breakdown based on income"""

    estimate = SpendingService.estimate_spending(monthly_income)
    return estimate


@router.post("/analyze", response_model=UserSpendingAnalysis)
async def analyze_spending(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        spending_data: dict = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Analyze user's spending against budget

    spending_data example:
    {
        "housing": 1200,
        "utilities": 200,
        "transportation": 400,
        "groceries": 300,
        "dining": 400,
        "entertainment": 200,
        "shopping": 150,
        "subscriptions": 50,
        "other": 100
    }
    """

    if spending_data is None:
        spending_data = {}

    analysis = SpendingService.analyze_user_spending(monthly_income, spending_data)
    return analysis


@router.post("/savings-potential", response_model=SavingsPotentialAnalysis)
async def calculate_savings_potential(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        spending_data: dict = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Calculate where user can save money

    spending_data example (same format as analyze endpoint):
    {
        "housing": 1500,
        "utilities": 250,
        "transportation": 600,
        "groceries": 250,
        "dining": 600,
        "entertainment": 300,
        "shopping": 300,
        "subscriptions": 100
    }
    """

    if spending_data is None:
        spending_data = {}

    potential = SpendingService.calculate_savings_potential(monthly_income, spending_data)
    return potential


@router.get("/quick-analysis", response_model=dict)
async def quick_spending_analysis(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get quick spending analysis without detailed data
    Uses estimated spending
    """

    estimate = SpendingService.estimate_spending(monthly_income)
    budget = SpendingService.get_budget_recommendation(monthly_income)

    return {
        "monthly_income": monthly_income,
        "estimate": estimate,
        "budget_recommendation": budget,
        "message": "Enter your actual spending to get detailed savings analysis"
    }
