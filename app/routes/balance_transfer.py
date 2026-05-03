from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.balance_transfer_service import BalanceTransferService
from app.services.debt_service import DebtService
from app.schemas.balance_transfer import (
    BalanceTransferCreate, BalanceTransferUpdate, BalanceTransferResponse
)

router = APIRouter(prefix="/strategies/balance-transfer", tags=["balance-transfer"])


@router.post("/create", response_model=BalanceTransferResponse)
async def create_balance_transfer(
        bt: BalanceTransferCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create new balance transfer offer"""

    db_bt = BalanceTransferService.create_balance_transfer(db, current_user.id, bt)
    return db_bt


@router.get("/list", response_model=list[BalanceTransferResponse])
async def get_balance_transfers(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get all balance transfer offers"""

    transfers = BalanceTransferService.get_user_balance_transfers(db, current_user.id)
    return transfers


@router.post("/compare")
async def compare_balance_transfer(
        transfer_amount: float = Query(..., gt=0, description="Amount to transfer"),
        promo_months: int = Query(..., gt=0, le=24, description="Promo period in months"),
        balance_transfer_fee: float = Query(0.03, ge=0, le=0.10, description="Transfer fee %"),
        regular_apr: float = Query(0.20, ge=0, le=1.0, description="APR after promo"),
        monthly_payment: float = Query(..., gt=0, description="Monthly payment amount"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Compare balance transfer strategy with current strategy"""

    debts = DebtService.get_active_debts(db, current_user.id)

    if not debts:
        raise HTTPException(status_code=400, detail="No debts found")

    comparison = BalanceTransferService.compare_with_current_strategy(
        debts,
        monthly_payment,
        transfer_amount,
        promo_months,
        balance_transfer_fee,
        regular_apr
    )

    return comparison


@router.post("/calculate")
async def calculate_balance_transfer(
        transfer_amount: float = Query(..., gt=0),
        promo_months: int = Query(..., gt=0),
        balance_transfer_fee: float = Query(0.03),
        regular_apr: float = Query(0.20),
        monthly_payment: float = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Calculate balance transfer scenario"""

    debts = DebtService.get_active_debts(db, current_user.id)

    if not debts:
        raise HTTPException(status_code=400, detail="No debts found")

    result = BalanceTransferService.calculate_balance_transfer_strategy(
        debts,
        transfer_amount,
        promo_months,
        balance_transfer_fee,
        regular_apr,
        monthly_payment
    )

    return result
