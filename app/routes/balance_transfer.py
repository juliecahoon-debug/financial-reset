from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.debt_service import DebtService
from app.services.balance_transfer_service import BalanceTransferService
from app.schemas.balance_transfer import BalanceTransferCreate, BalanceTransferResponse

router = APIRouter(prefix="/balance-transfer", tags=["balance-transfer"])


@router.post("/", response_model=BalanceTransferResponse, status_code=status.HTTP_201_CREATED)
async def create_balance_transfer(
        bt: BalanceTransferCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Save a balance transfer offer."""
    return BalanceTransferService.create_balance_transfer(db, current_user.id, bt)


@router.get("/", response_model=list[BalanceTransferResponse])
async def get_user_balance_transfers(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """List the current user's saved balance transfer offers."""
    return BalanceTransferService.get_user_balance_transfers(db, current_user.id)


@router.post("/calculate")
async def calculate_balance_transfer_strategy(
        transfer_amount: float = Query(..., gt=0),
        promo_months: int = Query(..., gt=0),
        balance_transfer_fee: float = Query(0.03, ge=0),
        regular_apr: float = Query(0.0, ge=0),
        monthly_payment: float = Query(None, gt=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Calculate a balance transfer payoff strategy."""
    debts = DebtService.get_active_debts(db, current_user.id)
    return BalanceTransferService.calculate_balance_transfer_strategy(
        debts, transfer_amount, promo_months, balance_transfer_fee, regular_apr, monthly_payment
    )


@router.post("/compare")
async def compare_with_current_strategy(
        current_monthly_payment: float = Query(..., gt=0),
        transfer_amount: float = Query(..., gt=0),
        promo_months: int = Query(..., gt=0),
        balance_transfer_fee: float = Query(0.03, ge=0),
        regular_apr: float = Query(0.0, ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Compare a balance transfer against the current payoff strategy."""
    debts = DebtService.get_active_debts(db, current_user.id)
    return BalanceTransferService.compare_with_current_strategy(
        debts, current_monthly_payment, transfer_amount, promo_months,
        balance_transfer_fee, regular_apr
    )
