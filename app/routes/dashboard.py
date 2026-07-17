from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.debt_service import DebtService
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary")
def get_dashboard_summary(
    monthly_income: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    debts = DebtService.get_user_debts(db, current_user.id)
    return DashboardService.get_dashboard_summary(debts, monthly_income)

@router.get("/cash-flow")
def get_cash_flow(
    monthly_income: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    debts = DebtService.get_user_debts(db, current_user.id)
    total_payments = sum(d.minimum_payment or 0 for d in debts)
    return DashboardService.get_cash_flow_analysis(monthly_income, total_payments)

@router.get("/health")
def get_health_metrics(
    monthly_income: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    debts = DebtService.get_user_debts(db, current_user.id)
    return DashboardService.get_financial_health_metrics(debts, monthly_income)

@router.get("/emergency-fund")
def get_emergency_fund(
    monthly_income: float,
    monthly_expenses: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    debts = DebtService.get_user_debts(db, current_user.id)
    return DashboardService.get_emergency_fund_recommendation(monthly_income, monthly_expenses, debts)
