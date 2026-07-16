from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.debt_service import DebtService
from app.services.strategy_service import StrategyService
from app.schemas.strategy import (
    StrategyProjection, StrategyComparison, FinancialScore, StrategyRecommendation
)

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.get("/avalanche", response_model=StrategyProjection)
async def get_avalanche_strategy(
        monthly_payment: float = Query(..., gt=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Avalanche strategy: pay highest APR first."""
    debts = DebtService.get_active_debts(db, current_user.id)
    return StrategyService.get_avalanche_strategy(debts, monthly_payment)


@router.get("/snowball", response_model=StrategyProjection)
async def get_snowball_strategy(
        monthly_payment: float = Query(..., gt=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Snowball strategy: pay lowest balance first."""
    debts = DebtService.get_active_debts(db, current_user.id)
    return StrategyService.get_snowball_strategy(debts, monthly_payment)


@router.get("/compare", response_model=StrategyComparison)
async def compare_strategies(
        monthly_payment: float = Query(..., gt=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Compare Avalanche vs Snowball strategies."""
    debts = DebtService.get_active_debts(db, current_user.id)
    return StrategyService.compare_strategies(debts, monthly_payment)


@router.get("/score", response_model=FinancialScore)
async def get_financial_score(
        monthly_income: float = Query(..., ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Calculate the user's financial health score."""
    debts = DebtService.get_active_debts(db, current_user.id)
    return StrategyService.calculate_financial_score(debts, monthly_income)


@router.get("/recommendation", response_model=StrategyRecommendation)
async def get_strategy_recommendation(
        monthly_income: float = Query(..., ge=0),
        available_monthly_payment: float = Query(..., ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get a personalized strategy recommendation."""
    debts = DebtService.get_active_debts(db, current_user.id)
    return StrategyService.get_recommendation(debts, monthly_income, available_monthly_payment)


@router.get("/insufficient-payment")
async def get_insufficient_payment_recommendations(
        monthly_payment: float = Query(..., ge=0),
        monthly_income: float = Query(..., ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get alternatives when the monthly payment is too low."""
    debts = DebtService.get_active_debts(db, current_user.id)
    return StrategyService.get_insufficient_payment_recommendations(
        debts, monthly_payment, monthly_income
    )
