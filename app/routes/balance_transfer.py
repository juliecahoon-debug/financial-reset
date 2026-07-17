from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.balance_transfer_service import BalanceTransferService
from app.services.debt_service import DebtService
from app.schemas.balance_transfer import BalanceTransferCreate

router = APIRouter(prefix="/balance-transfer", tags=["balance-transfer"])

@router.post("/")
def create_balance_transfer(
    bt: BalanceTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return BalanceTransferService.create_balance_transfer(db, current_user.id, bt)

@router.get("/")
def get_balance_transfers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return BalanceTransferService.get_user_balance_transfers(db, current_user.id)

class BTStrategyRequest(BaseModel):
    transfer_amount: float
    promo_months: int
    balance_transfer_fee: float = 0.03
    regular_apr: float = 0.0
    monthly_payment: Optional[float] = None

@router.post("/calculate")
def calculate_strategy(
    req: BTStrategyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    debts = DebtService.get_user_debts(db, current_user.id)
    return BalanceTransferService.calculate_balance_transfer_strategy(
        debts,
        req.transfer_amount,
        req.promo_months,
        req.balance_transfer_fee,
        req.regular_apr,
        req.monthly_payment
    )

class APRComparisonRequest(BaseModel):
    cards: List[BalanceTransferCreate]
    transfer_balance: float
    monthly_payment: float

@router.post("/compare-apr")
def compare_apr(
    req: APRComparisonRequest,
    current_user: User = Depends(get_current_user)
):
    results = []
    for card in req.cards:
        strategy = BalanceTransferService.calculate_balance_transfer_strategy(
            debts=[],
            transfer_amount=req.transfer_balance,
            promo_months=card.promo_months,
            balance_transfer_fee=card.balance_transfer_fee,
            regular_apr=card.regular_apr,
            monthly_payment=req.monthly_payment
        )
        results.append({
            "card_name": card.card_name,
            "intro_apr": card.intro_apr,
            "regular_apr": card.regular_apr,
            "promo_months": card.promo_months,
            "transfer_fee": card.balance_transfer_fee,
            "strategy": strategy
        })
    results.sort(key=lambda x: x["strategy"].get("total_cost", float("inf")))
    return {"comparison": results, "best_option": results[0]["card_name"] if results else None}
