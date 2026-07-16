from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.debt_service import DebtService
from app.services.consolidation_service import ConsolidationService

router = APIRouter(prefix="/consolidation", tags=["consolidation"])


@router.post("/calculate")
async def calculate_consolidation_payoff(
        consolidation_apr: float = Query(..., ge=0),
        loan_term_months: int = Query(..., gt=0),
        origination_fee: float = Query(0.02, ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Calculate a debt consolidation payoff plan."""
    debts = DebtService.get_active_debts(db, current_user.id)
    return ConsolidationService.calculate_consolidation_payoff(
        debts, consolidation_apr, loan_term_months, origination_fee
    )


@router.post("/compare-terms")
async def compare_loan_terms(
        consolidation_apr: float = Query(..., ge=0),
        monthly_payment_current: float = Query(..., gt=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Compare consolidation loan term options (36/60/84 months)."""
    debts = DebtService.get_active_debts(db, current_user.id)
    return ConsolidationService.compare_loan_terms(
        debts, consolidation_apr, monthly_payment_current
    )


@router.post("/compare")
async def compare_with_current_strategy(
        current_monthly_payment: float = Query(..., gt=0),
        consolidation_apr: float = Query(..., ge=0),
        loan_term_months: int = Query(60, gt=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Compare consolidation against the current payoff strategy."""
    debts = DebtService.get_active_debts(db, current_user.id)
    return ConsolidationService.compare_with_current_strategy(
        debts, current_monthly_payment, consolidation_apr, loan_term_months
    )
