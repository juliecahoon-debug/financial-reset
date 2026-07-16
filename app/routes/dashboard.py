from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.debt_service import DebtService
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import (
    DashboardSummary, EmergencyFundRecommendation,
    CashFlowAnalysis, FinancialHealthMetrics
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
        monthly_income: float = Query(..., ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get the complete financial dashboard summary."""
    debts = DebtService.get_user_debts(db, current_user.id)
    return DashboardService.get_dashboard_summary(debts, monthly_income)


@router.get("/emergency-fund", response_model=EmergencyFundRecommendation)
async def get_emergency_fund_recommendation(
        monthly_income: float = Query(..., ge=0),
        monthly_expenses: float = Query(..., ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get an emergency fund recommendation."""
    return DashboardService.get_emergency_fund_recommendation(monthly_income, monthly_expenses)


@router.get("/cash-flow", response_model=CashFlowAnalysis)
async def get_cash_flow_analysis(
        monthly_income: float = Query(..., ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Analyze monthly cash flow after debt payments."""
    debts = DebtService.get_active_debts(db, current_user.id)
    total_debt_payments = DebtService.get_total_monthly_payment(debts)
    return DashboardService.get_cash_flow_analysis(monthly_income, total_debt_payments)


@router.get("/health", response_model=FinancialHealthMetrics)
async def get_financial_health_metrics(
        monthly_income: float = Query(..., ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get comprehensive financial health metrics."""
    debts = DebtService.get_user_debts(db, current_user.id)
    return DashboardService.get_financial_health_metrics(debts, monthly_income)
