from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.debt import DebtStatus
from app.dependencies import get_current_user
from app.services.debt_service import DebtService
from app.services.strategy_service import StrategyService
from app.schemas.strategy import (
    StrategyComparison, FinancialScore, StrategyRecommendation, StrategyType  # ← ADD THIS
)

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.post("/compare", response_model=dict)
async def compare_strategies(
        monthly_payment: float = Query(..., gt=0, description="Monthly payment amount"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Compare Avalanche vs Snowball strategies"""

    # Get active debts
    debts = DebtService.get_active_debts(db, current_user.id)

    if not debts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active debts to optimize"
        )

    # Test if payment is sufficient
    test_result = StrategyService._simulate_payoff_accurate(debts, monthly_payment, StrategyType.AVALANCHE)

    # If insufficient payment, return error with recommendations
    if test_result.get("insufficient_payment") and test_result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=test_result["error"]
        )

    comparison = StrategyService.compare_strategies(debts, monthly_payment)
    return comparison.model_dump()


@router.get("/financial-score", response_model=FinancialScore)
async def get_financial_score(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Calculate financial health score"""

    debts = DebtService.get_user_debts(db, current_user.id)

    score = StrategyService.calculate_financial_score(debts, monthly_income)
    return score


@router.post("/recommend", response_model=StrategyRecommendation)
async def get_recommendation(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        available_payment: float = Query(..., gt=0, description="Available monthly payment"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get personalized strategy recommendation"""

    debts = DebtService.get_active_debts(db, current_user.id)

    if not debts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active debts to optimize"
        )

    recommendation = StrategyService.get_recommendation(
        debts, monthly_income, available_payment
    )
    return recommendation


@router.get("/avalanche", response_model=dict)
async def get_avalanche_strategy(
        monthly_payment: float = Query(..., gt=0, description="Monthly payment amount"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get Avalanche strategy details"""

    debts = DebtService.get_active_debts(db, current_user.id)

    if not debts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active debts"
        )

    strategy = StrategyService.get_avalanche_strategy(debts, monthly_payment)
    return strategy.model_dump()


@router.get("/snowball", response_model=dict)
async def get_snowball_strategy(
        monthly_payment: float = Query(..., gt=0, description="Monthly payment amount"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get Snowball strategy details"""

    debts = DebtService.get_active_debts(db, current_user.id)

    if not debts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active debts"
        )

    strategy = StrategyService.get_snowball_strategy(debts, monthly_payment)
    return strategy.model_dump()


@router.post("/insufficient-payment-recommendations")
async def get_insufficient_recommendations(
        monthly_payment: float = Query(..., gt=0),
        monthly_income: float = Query(..., gt=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get recommendations when payment is too low"""

    debts = DebtService.get_active_debts(db, current_user.id)

    if not debts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active debts"
        )

    recommendations = StrategyService.get_insufficient_payment_recommendations(
        debts, monthly_payment, monthly_income
    )

    return recommendations
