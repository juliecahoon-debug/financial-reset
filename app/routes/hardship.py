from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.debt import Debt, HardshipPlan
from app.dependencies import get_current_user
from app.services.hardship_service import HardshipService
from app.schemas.hardship import (
    HardshipPlanCreate, HardshipPlanResponse, HardshipPlanOption
)
from pydantic import BaseModel

class CreateHardshipPlanRequest(BaseModel):
    debt_id: int
    plan_type: str
    reason_for_hardship: str

router = APIRouter(prefix="/hardship", tags=["hardship"])


@router.get("/options/{debt_id}")
async def get_hardship_options(
        debt_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get available hardship relief options for a debt"""

    debt = db.query(Debt).filter(
        Debt.id == debt_id,
        Debt.user_id == current_user.id
    ).first()

    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    options = HardshipService.get_hardship_options(debt)
    return options


@router.post("/recommend")
async def get_hardship_recommendation(
        debt_id: int = Query(..., gt=0),
        monthly_cash_available: float = Query(..., ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get recommended hardship plan based on user situation"""

    debt = db.query(Debt).filter(
        Debt.id == debt_id,
        Debt.user_id == current_user.id
    ).first()

    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    recommendation = HardshipService.recommend_hardship_plan(
        current_user,
        debt,
        monthly_cash_available
    )

    return recommendation


@router.post("/calculate/deferment")
async def calculate_deferment(
        debt_id: int = Query(..., gt=0),
        deferment_months: int = Query(6, ge=3, le=24),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Calculate deferment impact"""

    debt = db.query(Debt).filter(
        Debt.id == debt_id,
        Debt.user_id == current_user.id
    ).first()

    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    impact = HardshipService.calculate_deferment_impact(debt, deferment_months)
    return impact


@router.post("/calculate/forbearance")
async def calculate_forbearance(
        debt_id: int = Query(..., gt=0),
        reduced_payment: float = Query(..., gt=0),
        forbearance_months: int = Query(12, ge=6, le=36),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Calculate forbearance impact"""

    debt = db.query(Debt).filter(
        Debt.id == debt_id,
        Debt.user_id == current_user.id
    ).first()

    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    impact = HardshipService.calculate_forbearance_impact(
        debt,
        reduced_payment,
        forbearance_months
    )
    return impact


@router.post("/calculate/settlement")
async def calculate_settlement(
        debt_id: int = Query(..., gt=0),
        settlement_percentage: float = Query(0.50, ge=0.30, le=0.90),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Calculate settlement impact"""

    debt = db.query(Debt).filter(
        Debt.id == debt_id,
        Debt.user_id == current_user.id
    ).first()

    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    impact = HardshipService.calculate_settlement_impact(debt, settlement_percentage)
    return impact


@router.post("/create")
async def create_hardship_plan(
        request: CreateHardshipPlanRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Create a hardship plan for a debt"""

    debt_id = request.debt_id
    plan_type = request.plan_type
    reason_for_hardship = request.reason_for_hardship

    debt = db.query(Debt).filter(
        Debt.id == debt_id,
        Debt.user_id == current_user.id
    ).first()

    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    # Calculate details based on plan type
    settlement_percentage = 0.50
    settlement_amount = None
    reduced_payment_amount = 0
    forbearance_months = 0
    deferment_months = 0
    total_cost = 0

    if plan_type.lower() == "settlement":
        settlement_amount = debt.balance * settlement_percentage
        total_cost = settlement_amount

    elif plan_type.lower() == "forbearance":
        reduced_payment_amount = max(debt.minimum_payment * 0.50, 50)
        forbearance_months = 6
        interest_rate = debt.interest_rate / 100 if debt.interest_rate > 1 else debt.interest_rate
        balance = debt.balance
        for month in range(forbearance_months):
            monthly_interest = balance * (interest_rate / 12)
            total_cost += monthly_interest
            balance += monthly_interest
            balance -= reduced_payment_amount
        total_cost = round(total_cost, 2)

    elif plan_type.lower() == "deferment":
        deferment_months = 6
        interest_rate = debt.interest_rate / 100 if debt.interest_rate > 1 else debt.interest_rate
        balance = debt.balance
        for month in range(deferment_months):
            monthly_interest = balance * (interest_rate / 12)
            total_cost += monthly_interest
            balance += monthly_interest
        total_cost = round(total_cost, 2)

    # Create hardship plan
    hardship_plan = HardshipPlan(
        user_id=current_user.id,
        debt_id=debt_id,
        plan_type=plan_type,
        reason_for_hardship=reason_for_hardship,
        status="created",
        settlement_percentage=settlement_percentage if plan_type.lower() == "settlement" else 0,
        settlement_amount=settlement_amount,
        reduced_payment_amount=reduced_payment_amount,
        forbearance_months=forbearance_months,
        deferment_months=deferment_months,
        total_cost=total_cost
    )

    db.add(hardship_plan)
    db.commit()
    db.refresh(hardship_plan)

    return hardship_plan


@router.get("/user-plans")
async def get_user_hardship_plans(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get all hardship plans for current user"""

    plans = db.query(HardshipPlan).filter(
        HardshipPlan.user_id == current_user.id
    ).all()

    return plans


@router.get("/compare-all-options/{debt_id}")
async def compare_all_hardship_options(
        debt_id: int,
        custom_payment: float = None,  # Optional custom payment
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Compare hardship options with payment scenarios

    Query Parameters:
    - debt_id: ID of the debt (required)
    - custom_payment (optional): Custom monthly payment amount

    Returns:
    - 4 preset payment scenarios (min, 2x, 3x, 4x minimum)
    - Plus optional custom scenario if custom_payment provided
    - Plus hardship options (settlement, forbearance, deferment)
    """

    debt = db.query(Debt).filter(
        Debt.id == debt_id,
        Debt.user_id == current_user.id
    ).first()

    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    comparison = HardshipService.compare_all_hardship_options(debt, custom_payment)

    return comparison


