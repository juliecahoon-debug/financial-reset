from fastapi import APIRouter, Depends, HTTPException, status, Query
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
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get complete financial dashboard summary"""

    debts = DebtService.get_user_debts(db, current_user.id)

    summary = DashboardService.get_dashboard_summary(debts, monthly_income)
    return summary


@router.get("/emergency-fund", response_model=EmergencyFundRecommendation)
async def get_emergency_fund(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        monthly_expenses: float = Query(..., gt=0, description="Monthly expenses"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get emergency fund recommendation"""

    recommendation = DashboardService.get_emergency_fund_recommendation(monthly_income, monthly_expenses)
    return recommendation


@router.get("/cash-flow", response_model=CashFlowAnalysis)
async def get_cash_flow(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Analyze monthly cash flow"""

    debts = DebtService.get_active_debts(db, current_user.id)
    total_payments = DebtService.get_total_monthly_payment(debts)

    analysis = DashboardService.get_cash_flow_analysis(monthly_income, total_payments)
    return analysis


@router.get("/health", response_model=FinancialHealthMetrics)
async def get_financial_health(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get comprehensive financial health metrics"""

    debts = DebtService.get_user_debts(db, current_user.id)

    metrics = DashboardService.get_financial_health_metrics(debts, monthly_income)
    return metrics


@router.get("/overview", response_model=dict)
async def get_complete_overview(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        monthly_expenses: float = Query(..., gt=0, description="Monthly expenses"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get complete financial overview (all metrics at once)"""

    debts = DebtService.get_user_debts(db, current_user.id)

    return {
        "summary": DashboardService.get_dashboard_summary(debts, monthly_income),
        "health": DashboardService.get_financial_health_metrics(debts, monthly_income),
        "cash_flow": DashboardService.get_cash_flow_analysis(monthly_income,
                                                             DebtService.get_total_monthly_payment(debts)),
        "emergency_fund": DashboardService.get_emergency_fund_recommendation(monthly_income, monthly_expenses)
    }
