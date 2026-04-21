from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.debt import DebtCreate, DebtUpdate, DebtResponse, DebtCalculationResponse
from app.services.debt_service import DebtService
from app.models.user import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/debts", tags=["debts"])


@router.post("/", response_model=DebtResponse, status_code=status.HTTP_201_CREATED)
async def create_debt(
        debt: DebtCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a new debt"""
    db_debt = DebtService.create_debt(db, current_user.id, debt)
    return db_debt


@router.get("/", response_model=list[DebtResponse])
async def get_user_debts(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get all debts for current user"""
    debts = DebtService.get_user_debts(db, current_user.id)
    return debts


@router.get("/active", response_model=list[DebtResponse])
async def get_active_debts(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get active debts for current user"""
    debts = DebtService.get_active_debts(db, current_user.id)
    return debts


@router.get("/{debt_id}", response_model=DebtResponse)
async def get_debt(
        debt_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get specific debt"""
    debt = DebtService.get_debt_by_id(db, debt_id)

    if not debt or debt.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debt not found"
        )

    return debt


@router.put("/{debt_id}", response_model=DebtResponse)
async def update_debt(
        debt_id: int,
        debt_update: DebtUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update debt"""
    debt = DebtService.get_debt_by_id(db, debt_id)

    if not debt or debt.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debt not found"
        )

    updated_debt = DebtService.update_debt(db, debt_id, debt_update)
    return updated_debt


@router.delete("/{debt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_debt(
        debt_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete debt"""
    debt = DebtService.get_debt_by_id(db, debt_id)

    if not debt or debt.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debt not found"
        )

    DebtService.delete_debt(db, debt_id)
    return None


@router.get("/{debt_id}/calculate", response_model=DebtCalculationResponse)
async def calculate_debt_payoff(
        debt_id: int,
        monthly_payment: float,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Calculate payoff for a specific debt"""
    debt = DebtService.get_debt_by_id(db, debt_id)

    if not debt or debt.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debt not found"
        )

    payoff = DebtService.calculate_payoff(debt.balance, monthly_payment, debt.interest_rate)

    return {
        "debt_id": debt.id,
        "name": debt.name,
        "balance": debt.balance,
        "interest_rate": debt.interest_rate,
        "monthly_interest": round(DebtService.calculate_monthly_interest(debt.balance, debt.interest_rate), 2),
        "monthly_payment": monthly_payment,
        "months_to_payoff": payoff["months"],
        "total_interest_paid": payoff["total_interest"],
        "total_amount_paid": payoff["total_paid"]
    }


@router.get("/dashboard/summary", response_model=dict)
async def get_debt_summary(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get debt summary for dashboard"""
    debts = DebtService.get_user_debts(db, current_user.id)
    active_debts = DebtService.get_active_debts(db, current_user.id)

    return {
        "total_debts": len(debts),
        "active_debts": len(active_debts),
        "total_balance": DebtService.get_total_debt(debts),
        "total_monthly_payment": DebtService.get_total_monthly_payment(active_debts),
        "weighted_apr": DebtService.get_weighted_apr(active_debts),
        "debt_breakdown": {
            "by_type": {},
            "by_status": {}
        }
    }
