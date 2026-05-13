from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
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
    """
    Get available hardship relief options for a debt.

    ⚠️  IMPORTANT DISCLAIMERS & LEGAL NOTICES:

    EDUCATIONAL PURPOSE ONLY:
    - This information is provided for EDUCATIONAL purposes only
    - This is NOT legal or financial advice
    - Consult with a lawyer or financial advisor for your specific situation

    CREDITOR VARIATIONS:
    - Actual programs vary SIGNIFICANTLY by creditor and situation
    - Terms, conditions, requirements, and availability are subject to change
    - Contact your creditor DIRECTLY to confirm eligibility and terms

    NO GUARANTEE:
    - Offering these options does NOT guarantee approval
    - Your creditor may deny your request for hardship assistance

    CREDIT IMPACT:
    - Some hardship programs (especially settlement) severely impact credit score
    - Forbearance/deferment may extend your payoff timeline
    - Default/charge-off will damage your credit for 7 years

    TAX IMPLICATIONS - VERY IMPORTANT:
    - Forgiven debt may be considered TAXABLE INCOME
    - Consult a CPA or tax professional BEFORE settling

    This API returns RECOMMENDATIONS based on your situation, but the actual
    available programs depend on YOUR specific creditor's policies.
    """

    # VERIFY DEBT EXISTS AND BELONGS TO USER
    debt = db.query(Debt).filter(
        Debt.id == debt_id,
        Debt.user_id == current_user.id
    ).first()

    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    # GET HARDSHIP OPTIONS FROM YOUR EXISTING SERVICE
    options = HardshipService.get_hardship_options(debt)

    # BUILD ENHANCED RESPONSE WITH DISCLAIMERS
    response = {
        "debt_id": debt_id,
        "debt_name": debt.name,
        "debt_type": debt.debt_type,
        "creditor": debt.creditor,
        "current_balance": float(debt.balance),
        "interest_rate": float(debt.interest_rate) if debt.interest_rate else None,
        "minimum_payment": float(debt.minimum_payment) if hasattr(debt, 'minimum_payment') else None,
        "status": debt.status,
        "days_late": getattr(debt, 'days_late', 0),

        "available_options": options,

        "disclaimers": {
            "information_type": "EDUCATIONAL INFORMATION ONLY",
            "not_legal_advice": "This is not legal or financial advice. Consult a lawyer or financial advisor.",
            "not_lender_decision": "This information does not represent a creditor's actual decision.",
            "creditor_variation": "These are POTENTIAL options. Your creditor's actual programs may differ.",
            "no_guarantee": "These options are not guaranteed. Your creditor may deny your request.",
            "must_contact_creditor": "You MUST contact your creditor directly to confirm eligibility.",
            "tax_warning": "Forgiven debt may be considered taxable income. Consult a CPA before settling.",
            "credit_impact": "These programs may negatively impact your credit score.",
            "data_currency": "Creditor policies change. Verify all terms with creditor before accepting.",
            "settlement_critical": "Settlement severely damages credit for 7 years.",
        },

        "recommended_next_steps": get_recommended_steps(debt),
        "creditor_contact": get_creditor_contact(debt),
        "warnings": get_situation_warnings(debt),

        "resources": {
            "credit_counseling": {
                "organization": "NFCC",
                "phone": "1-800-388-2227",
                "website": "www.nfcc.org",
                "services": "FREE credit counseling"
            }
        },

        "timestamp": datetime.utcnow().isoformat(),
        "note": "Verify with your creditor. Policies change frequently.",
    }

    return response


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


def get_recommended_steps(debt: Debt) -> list:
    """Get recommended action steps."""
    return [
        {
            "step": 1,
            "action": "Review the hardship options above",
            "why": "Understand what programs might be available",
            "time": "5-10 minutes"
        },
        {
            "step": 2,
            "action": f"Contact {debt.creditor}'s hardship department",
            "why": "Confirm which programs apply to YOUR account",
            "tip": "Say: 'I'm experiencing financial hardship and would like to discuss payment relief options'",
            "time": "15-30 minutes"
        },
        {
            "step": 3,
            "action": "Ask about EACH option specifically",
            "why": "Get detailed information",
            "time": "20-40 minutes"
        },
        {
            "step": 4,
            "action": "Get everything in WRITING",
            "why": "Protect yourself. Verbal agreements don't protect you.",
            "critical": "DO NOT pay until you have written agreement",
            "time": "15-30 minutes"
        },
        {
            "step": 5,
            "action": "Understand the FULL impact",
            "why": "Know how this affects your finances",
            "time": "30-60 minutes"
        },
        {
            "step": 6,
            "action": "Talk to a credit counselor (optional)",
            "where": "Call NFCC at 1-800-388-2227 (FREE)",
            "time": "60 minutes"
        },
        {
            "step": 7,
            "action": "Make your decision and start payments",
            "why": "Once you understand everything, move forward",
            "time": "Ongoing"
        }
    ]


def get_creditor_contact(debt: Debt) -> dict:
    """Get creditor contact information."""
    creditor_info = {
        "Chase": {"phone": "1-800-945-9060", "department": "Hardship Program"},
        "Capital One": {"phone": "1-877-383-4802", "department": "Hardship Department"},
        "American Express": {"phone": "1-800-567-1234", "department": "Hardship / Customer Service"},
        "Discover": {"phone": "1-800-347-2683", "department": "Customer Service"},
    }

    known = creditor_info.get(debt.creditor)

    if known:
        return {
            "creditor_name": debt.creditor,
            "phone": known["phone"],
            "department": known["department"],
            "what_to_say": "I'm experiencing financial hardship and would like to discuss payment relief options.",
            "have_ready": ["Account number", "SSN", "Brief hardship explanation", "Income info"]
        }
    else:
        return {
            "creditor_name": debt.creditor,
            "phone": "See back of your card",
            "department": "Hardship Department",
            "note": f"Search '{debt.creditor} hardship program' online"
        }


def get_situation_warnings(debt: Debt) -> list:
    """Generate warnings based on debt situation."""
    warnings = []
    days_late = getattr(debt, 'days_late', 0)

    if days_late is None or days_late == 0:
        warnings.append({"severity": "LOW", "message": "Account is current. Act proactively if struggling."})
    elif days_late < 30:
        warnings.append({"severity": "MEDIUM", "message": "Account approaching 30 days late. Act quickly."})
    elif days_late < 60:
        warnings.append({"severity": "HIGH", "message": "Account 30+ days late. Contact creditor immediately."})
    elif days_late < 120:
        warnings.append({"severity": "CRITICAL", "message": "Charge-off imminent. Contact creditor today."})
    else:
        warnings.append({"severity": "CRITICAL", "message": "Account likely charged off. Settlement still possible."})

    if debt.interest_rate and debt.interest_rate > 20:
        warnings.append({"severity": "MEDIUM",
                         "message": f"High interest rate ({debt.interest_rate}%). Settlement may save money."})

    if debt.balance and debt.balance > 5000:
        warnings.append({"severity": "MEDIUM", "message": "Large balance. Better negotiating power."})

    return warnings