from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.debt_service import DebtService
from app.services.strategy_service import StrategyService

router = APIRouter(prefix="/strategy", tags=["strategy"])

@router.get("/compare")
def compare_strategies(
    monthly_payment: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    debts = DebtService.get_user_debts(db, current_user.id)
    if not debts:
        raise HTTPException(status_code=404, detail="No debts found")
    return StrategyService.compare_strategies(debts, monthly_payment)

@router.get("/score")
def financial_score(
    monthly_income: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    debts = DebtService.get_user_debts(db, current_user.id)
    return StrategyService.calculate_financial_score(debts, monthly_income)

@router.get("/recommendation")
def get_recommendation(
    monthly_income: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    debts = DebtService.get_user_debts(db, current_user.id)
    score = StrategyService.calculate_financial_score(debts, monthly_income)
    return StrategyService.get_recommendation(debts, monthly_income, score)
