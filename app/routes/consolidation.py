from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.consolidation_service import ConsolidationService
from app.services.debt_service import DebtService

router = APIRouter(prefix="/strategies/consolidation", tags=["consolidation"])


@router.post("/calculate")
async def calculate_consolidation(
        consolidation_apr: float = Query(..., ge=0, le=1.0, description="APR for consolidation loan"),
        loan_term_months: int = Query(60, ge=12, le=180, description="Loan term in months"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Calculate consolidation loan scenario"""

    debts = DebtService.get_active_debts(db, current_user.id)

    if not debts:
        raise HTTPException(status_code=400, detail="No debts found")

    result = ConsolidationService.calculate_consolidation_payoff(
        debts,
        consolidation_apr,
        loan_term_months
    )

    return result


@router.post("/compare-terms")
async def compare_loan_terms(
        consolidation_apr: float = Query(..., ge=0, le=1.0),
        monthly_payment: float = Query(..., gt=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Compare different loan term options (36, 60, 84 months)"""

    debts = DebtService.get_active_debts(db, current_user.id)

    if not debts:
        raise HTTPException(status_code=400, detail="No debts found")

    # Compare all term options
    terms = [36, 60, 84]
    comparisons = []

    for term in terms:
        result = ConsolidationService.calculate_consolidation_payoff(
            debts,
            consolidation_apr,
            term
        )
        comparisons.append(result)

    return comparisons


@router.post("/compare-with-current")
async def compare_consolidation_with_current(
        consolidation_apr: float = Query(..., ge=0, le=1.0),
        loan_term_months: int = Query(60, ge=12, le=180),
        monthly_payment: float = Query(..., gt=0, description="Your current monthly payment"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Compare consolidation with current payoff strategy"""

    debts = DebtService.get_active_debts(db, current_user.id)

    if not debts:
        raise HTTPException(status_code=400, detail="No debts found")

    comparison = ConsolidationService.compare_with_current_strategy(
        debts,
        monthly_payment,
        consolidation_apr,
        loan_term_months
    )

    return comparison
