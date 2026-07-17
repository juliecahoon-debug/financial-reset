from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.spending_service import SpendingService
from app.schemas.spending import SpendingBreakdown

router = APIRouter(prefix="/spending", tags=["spending"])

@router.get("/budget")
def get_budget_recommendation(
    monthly_income: float,
    current_user: User = Depends(get_current_user)
):
    return SpendingService.get_budget_recommendation(monthly_income)

@router.get("/estimate")
def estimate_spending(
    monthly_income: float,
    current_user: User = Depends(get_current_user)
):
    return SpendingService.estimate_spending(monthly_income)

class SpendingAnalysisRequest(BaseModel):
    monthly_income: float
    actual_spending: List[SpendingBreakdown]
    monthly_debt_payments: Optional[float] = 0

@router.post("/analyze")
def analyze_spending(
    req: SpendingAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    return SpendingService.analyze_user_spending(
        req.monthly_income,
        req.actual_spending,
        req.monthly_debt_payments
    )

@router.post("/savings-potential")
def savings_potential(
    req: SpendingAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    return SpendingService.calculate_savings_potential(
        req.monthly_income,
        req.actual_spending
    )
