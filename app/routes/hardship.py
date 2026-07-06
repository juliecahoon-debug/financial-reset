from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.debt import Debt, HardshipPlan, HardshipCase, HardshipType, HardshipStatus
from app.dependencies import get_current_user
from app.services.hardship_service import HardshipService, _min_payment, _program_type
from app.schemas.hardship import (
    HardshipPlanCreate, HardshipPlanResponse, HardshipPlanOption
)
from pydantic import BaseModel
from datetime import datetime


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

    # FILTER OPTIONS BY DEBT TYPE (Remove non-applicable hardship programs)
    if debt.debt_type == "credit_card":
        # Credit cards: Only settlement, forbearance, hardship program
        # REMOVE: deferment (not applicable to credit cards)
        options = [opt for opt in options if opt.get("plan_type") in ["settlement", "forbearance", "hardship_program"]]

    elif debt.debt_type == "student_loan":
        # Student loans: All options available
        pass

    elif debt.debt_type == "auto_loan":
        # Auto loans: settlement, forbearance, deferment
        options = [opt for opt in options if opt.get("plan_type") in ["settlement", "forbearance", "deferment"]]

    elif debt.debt_type == "personal_loan":
        # Personal loans: Usually just settlement and forbearance
        options = [opt for opt in options if opt.get("plan_type") in ["settlement", "forbearance"]]

    # FILTER OUT SETTLEMENT FOR CURRENT ACCOUNTS (0 days late)
    if getattr(debt, 'days_late', 0) == 0:
        options = [opt for opt in options if opt.get("plan_type") != "settlement"]

    # BUILD ENHANCED RESPONSE WITH DISCLAIMERS
    response = {
        "debt_id": debt_id,
        "debt_name": debt.name,
        "debt_type": debt.debt_type,
        "creditor": debt.creditor_name,
        "current_balance": float(float(debt.current_principal)),
        "interest_rate": float(float(debt.interest_rate)) if float(debt.interest_rate) else None,
        "minimum_payment": float(_min_payment(debt)) if hasattr(debt, 'minimum_payment') else None,
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
    """
    Get recommended hardship plan based on user situation.

    ⚠️  IMPORTANT DISCLAIMERS:

    RECOMMENDATION IS NOT A GUARANTEE:
    - This recommendation is based on your financial situation
    - Your creditor may recommend a different option
    - This is NOT a promise that the creditor will approve this plan
    - Creditors have final say on which programs they offer

    EDUCATIONAL INFORMATION:
    - This is an estimate based on your data
    - Not legal or financial advice
    - Consult a financial advisor for your specific situation
    """

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

    enhanced_recommendation = {
        **recommendation,
        "disclaimers": {
            "recommendation_type": "EDUCATIONAL RECOMMENDATION ONLY",
            "not_a_promise": "This recommendation is not a guarantee of approval",
            "creditor_discretion": "Your creditor makes the final decision",
        },
        "warning": "Contact your creditor to confirm this recommendation",
        "timestamp": datetime.utcnow().isoformat()
    }

    return enhanced_recommendation


@router.post("/calculate/deferment")
async def calculate_deferment(
        debt_id: int = Query(..., gt=0),
        deferment_months: int = Query(6, ge=3, le=24),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Calculate deferment impact - Temporary pause on payments.

    ⚠️  DEFERMENT INFORMATION:

    WHAT IS DEFERMENT:
    - Temporary PAUSE on payments
    - Interest typically continues to accrue
    - Best for TEMPORARY hardship

    PRIMARY USE:
    - Most common for STUDENT LOANS
    - Less common for credit cards
    - Rarely available for auto loans

    IMPORTANT NOTES:
    - Interest continues to accrue (usually)
    - Loan term extends (you pay longer overall)
    - You'll owe more total (interest adds up)
    """

    debt = db.query(Debt).filter(
        Debt.id == debt_id,
        Debt.user_id == current_user.id
    ).first()

    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    impact = HardshipService.calculate_deferment_impact(debt, deferment_months)

    enhanced_impact = {
        **impact,
        "deferment_info": {
            "what_is_deferment": "Temporary complete pause on payments",
            "duration": f"{deferment_months} months",
            "interest_continues": "Interest typically accrues (ask your creditor)",
        },
        "key_questions": [
            "Is deferment available for my debt type?",
            "Will interest accrue during deferment?",
            "What happens when deferment ends?"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

    return enhanced_impact


@router.post("/calculate/forbearance")
async def calculate_forbearance(
        debt_id: int = Query(..., gt=0),
        reduced_payment: float = Query(..., gt=0),
        forbearance_months: int = Query(12, ge=6, le=36),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Calculate forbearance impact - Temporary payment reduction.

    ⚠️  FORBEARANCE INFORMATION:

    WHAT IS FORBEARANCE:
    - Temporary pause or reduction in payments
    - Your account remains in good standing (usually)
    - Interest typically continues to accrue

    HOW FORBEARANCE WORKS:
    - You pay reduced amount for agreed period
    - After forbearance ends, normal payments resume
    - Interest accrues during forbearance period

    CREDIT IMPACT:
    - May be reported as "deferred" or "forbearance"
    - Usually less damaging than settlement
    - Usually less damaging than delinquency
    """

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

    enhanced_impact = {
        **impact,
        "forbearance_info": {
            "what_is_forbearance": "Temporary pause or reduction in payments",
            "duration": f"{forbearance_months} months",
            "reduced_payment": f"${reduced_payment:,.2f}/month",
            "interest_continues": "Interest typically accrues during forbearance",
        },
        "key_questions": [
            "Will interest accrue during forbearance?",
            "How will you report forbearance to credit bureaus?",
            "What happens when forbearance ends?"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

    return enhanced_impact


@router.post("/calculate/settlement")
async def calculate_settlement(
        debt_id: int = Query(..., gt=0),
        settlement_percentage: float = Query(0.50, ge=0.30, le=0.90),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Calculate settlement impact - WARNING: SEVERE CONSEQUENCES.

    ⚠️  CRITICAL SETTLEMENT WARNINGS:

    CREDIT IMPACT - VERY SEVERE:
    - Settlement will cause a DROP of 100-150+ points IMMEDIATELY
    - "Settled for less than full balance" stays on credit report 7 YEARS
    - Your credit score will be significantly impacted
    - Future borrowing will be more expensive

    TAX IMPLICATIONS - YOU MAY OWE TAXES:
    - Forgiven debt is considered TAXABLE INCOME
    - You will receive a Form 1099-C from creditor
    - This could result in $200-300 tax bill (or more)
    - MUST consult a CPA BEFORE settling

    CREDITOR NOT OBLIGATED:
    - Your creditor does NOT have to settle
    - Settlement is a NEGOTIATION, not a guarantee
    - Creditor can refuse your settlement offer

    ONLY AS ABSOLUTE LAST RESORT:
    - Try ALL other options first
    - Settlement should be LAST option after others fail
    - Only if you understand the 7-year credit impact
    - Only if you've consulted with a tax professional
    """

    debt = db.query(Debt).filter(
        Debt.id == debt_id,
        Debt.user_id == current_user.id
    ).first()

    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    impact = HardshipService.calculate_settlement_impact(debt, settlement_percentage)

    enhanced_impact = {
        **impact,
        "settlement_disclaimers": {
            "information_type": "SETTLEMENT CALCULATION ONLY",
            "does_not_include_taxes": "This calculation does NOT include tax consequences",
            "creditor_not_obligated": "Your creditor is NOT obligated to settle",
            "settlement_not_guaranteed": "You may not get this settlement percentage",
            "tax_professional_required": "You MUST consult a CPA before settling",
            "last_resort_only": "Settlement should be considered only after all other options fail",
        },
        "tax_warning": f"Forgiven debt of ${float(debt.current_principal) * (1 - settlement_percentage):,.2f} may be taxable income.",
        "credit_impact_warning": "Credit score will drop 100-150+ points. Takes 3-5 years to recover.",
        "timestamp": datetime.utcnow().isoformat()
    }

    return enhanced_impact


@router.post("/create")
async def create_hardship_plan(
        request: CreateHardshipPlanRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Create a hardship plan for a debt - Get written confirmation.

    ⚠️  HARDSHIP PLAN CREATION IMPORTANT NOTES:

    BEFORE YOU PROCEED:
    - This creates a hardship plan in our system
    - This does NOT contact your creditor
    - This does NOT bind your creditor to anything
    - You MUST contact your creditor separately

    NEXT STEP (CRITICAL):
    - Contact your creditor directly
    - Ask for written confirmation of terms
    - Do NOT make any payments without written agreement

    WRITTEN AGREEMENT REQUIRED:
    - You MUST get written confirmation from creditor
    - Verbal agreements do NOT protect you
    """

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
        settlement_amount = float(debt.current_principal) * settlement_percentage
        total_cost = settlement_amount

    elif plan_type.lower() == "forbearance":
        reduced_payment_amount = max(_min_payment(debt) * 0.50, 50)
        forbearance_months = 6
        interest_rate = float(debt.interest_rate) / 100 if float(debt.interest_rate) > 1 else float(debt.interest_rate)
        balance = float(debt.current_principal)
        for month in range(forbearance_months):
            monthly_interest = balance * (interest_rate / 12)
            total_cost += monthly_interest
            balance += monthly_interest
            balance -= reduced_payment_amount
        total_cost = round(total_cost, 2)

    elif plan_type.lower() == "deferment":
        deferment_months = 6
        interest_rate = float(debt.interest_rate) / 100 if float(debt.interest_rate) > 1 else float(debt.interest_rate)
        balance = float(debt.current_principal)
        for month in range(deferment_months):
            monthly_interest = balance * (interest_rate / 12)
            total_cost += monthly_interest
            balance += monthly_interest
        total_cost = round(total_cost, 2)

    # HardshipPlan requires a parent HardshipCase (FK is NOT NULL)
    hardship_case = HardshipCase(
        debt_id=debt_id,
        user_id=current_user.id,
        hardship_type=HardshipType.OTHER,
        hardship_description=reason_for_hardship,
        hardship_start_date=datetime.utcnow(),
        case_status=HardshipStatus.OPEN,
    )
    db.add(hardship_case)
    db.flush()

    # Create hardship plan
    hardship_plan = HardshipPlan(
        user_id=current_user.id,
        debt_id=debt_id,
        hardship_case_id=hardship_case.id,
        program_type=_program_type(plan_type),
        description=reason_for_hardship,
        status="created",
        settlement_percentage=settlement_percentage if plan_type.lower() == "settlement" else 0,
        settlement_lump_sum=settlement_amount,
        monthly_payment_during=reduced_payment_amount,
        duration_months=forbearance_months or deferment_months,
        total_cost=total_cost
    )

    db.add(hardship_plan)
    db.commit()
    db.refresh(hardship_plan)

    response = {
        "plan_id": hardship_plan.id,
        "debt_id": hardship_plan.debt_id,
        "plan_type": hardship_plan.program_type.value,
        "status": hardship_plan.status,
        "plan_summary": {
            "debt_name": debt.name,
            "creditor": debt.creditor_name,
            "current_balance": float(float(debt.current_principal)),
        },
        "critical_warnings": [
            "⚠️  This plan is NOT approved by your creditor yet",
            "⚠️  You MUST contact your creditor to confirm",
            "⚠️  Do NOT make any payments without written agreement",
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

    return response


@router.get("/user-plans")
async def get_user_hardship_plans(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all hardship plans for current user.

    ⚠️  PLAN STATUS INFORMATION:

    VERIFY WITH CREDITOR:
    - Your status here is what you've recorded
    - Creditor's system may show different status
    - Always verify current status with creditor

    CHECK YOUR STATEMENTS:
    - Review your monthly bills carefully
    - Verify payments are being credited correctly
    - Confirm plan terms match your agreement
    """

    plans = db.query(HardshipPlan).filter(
        HardshipPlan.user_id == current_user.id
    ).all()

    enhanced_plans = []

    for plan in plans:
        debt = db.query(Debt).filter(Debt.id == plan.debt_id).first()

        enhanced_plan = {
            "plan_id": plan.id,
            "debt_id": plan.debt_id,
            "debt_name": debt.name if debt else "Unknown",
            "creditor": debt.creditor_name if debt else "Unknown",
            "plan_type": plan.program_type.value if plan.program_type else None,
            "status": plan.status,
            "created_at": plan.created_at.isoformat() if hasattr(plan.created_at, 'isoformat') else str(
                plan.created_at),
            "verification_reminders": [
                "Verify payments credited correctly",
                "Confirm no late fees were charged",
                "Check that plan is reported correctly to credit bureaus",
            ]
        }

        enhanced_plans.append(enhanced_plan)

    return enhanced_plans


# ===== HELPER FUNCTIONS =====

def get_recommended_steps(debt: Debt) -> list:
    """Get recommended action steps."""
    return [
        {
            "step": 1,
            "action": "Review the hardship options above",
            "why": "Understand what programs might be available",
        },
        {
            "step": 2,
            "action": f"Contact {debt.creditor_name}'s hardship department",
            "why": "Confirm which programs apply to YOUR account",
        },
        {
            "step": 3,
            "action": "Ask about EACH option specifically",
            "why": "Get detailed information",
        },
        {
            "step": 4,
            "action": "Get everything in WRITING",
            "why": "Protect yourself",
        },
        {
            "step": 5,
            "action": "Understand the FULL impact",
            "why": "Know how this affects your finances",
        },
        {
            "step": 6,
            "action": "Talk to a credit counselor (optional)",
            "where": "Call NFCC at 1-800-388-2227 (FREE)",
        },
        {
            "step": 7,
            "action": "Make your decision",
            "why": "Once you understand everything, move forward",
        }
    ]


def get_creditor_contact(debt: Debt) -> dict:
    """Get creditor contact information and debt-type specific resources."""
    creditor_info = {
        "Chase": {"phone": "1-800-945-9060", "department": "Hardship Program"},
        "Capital One": {"phone": "1-877-383-4802", "department": "Hardship Department"},
        "American Express": {"phone": "1-800-567-1234", "department": "Hardship / Customer Service"},
        "Discover": {"phone": "1-800-347-2683", "department": "Customer Service"},
    }

    known = creditor_info.get(debt.creditor_name)

    base_contact = {
        "creditor_name": debt.creditor_name,
        "phone": known["phone"] if known else "See back of your card",
        "department": known["department"] if known else "Hardship Department",
        "what_to_say": "I'm experiencing financial hardship and would like to discuss payment relief options.",
    }

    # ADD DEBT-TYPE SPECIFIC RESOURCES
    if debt.debt_type == "credit_card":
        base_contact["resources"] = {
            "primary": {
                "organization": "Contact your creditor FIRST",
                "why": "Creditors often have in-house hardship programs better than third-party options"
            },
            "if_creditor_refuses": {
                "organization": "NFCC - National Foundation for Credit Counseling",
                "phone": "1-800-388-2227",
                "website": "www.nfcc.org",
                "services": ["FREE credit counseling", "Debt Management Plan (DMP)"],
                "cost": "FREE counseling, $25-50/month for DMP",
                "critical_warning": "⚠️ IMPORTANT: If you enroll in a DMP, your creditor will CLOSE this credit card account and revoke your card. You won't be able to use it anymore.",
                "dmp_consequences": [
                    "❌ Credit card account will be CLOSED",
                    "❌ Card will be revoked (can't use it)",
                    "❌ Account closure damages your credit score further",
                    "❌ 'In DMP' notation stays on credit report for 3-5 years",
                    "✅ But: Lowers your overall debt and interest payments"
                ],
                "when_to_use_dmp": "Only if creditor won't work with you directly"
            }
        }

    elif debt.debt_type == "personal_loan":
        base_contact["resources"] = {
            "primary": {
                "organization": "Contact your lender FIRST",
                "why": "Most lenders will work directly with you on payment plans"
            },
            "if_lender_refuses": {
                "organization": "NFCC - National Foundation for Credit Counseling",
                "phone": "1-800-388-2227",
                "website": "www.nfcc.org",
                "services": ["FREE credit counseling", "Debt Management Plan (DMP)"],
                "cost": "FREE counseling, $25-50/month for DMP",
                "dmp_consequences": [
                    "⚠️ Account will be marked 'In DMP' on credit report",
                    "⚠️ May impact your credit score (typically 20-50 point hit)",
                    "✅ But: Lender stays at negotiating table",
                    "✅ Account usually remains open (unlike credit cards)",
                    "✅ Lowers overall interest and payments"
                ],
                "when_to_use_dmp": "When lender won't negotiate directly with you"
            }
        }

    elif debt.debt_type == "auto_loan":
        base_contact["resources"] = {
            "primary": {
                "organization": "Contact your lender DIRECTLY",
                "why": "Auto loans are DIFFERENT - your car can be repossessed",
                "critical": "⚠️ WARNING: Do NOT let auto loans go to collections or DMP"
            },
            "recommended_approach": {
                "step_1": "Call your lender immediately",
                "step_2": "Ask about forbearance, deferment, or payment modification",
                "step_3": "Explain your hardship (job loss, medical, etc)",
                "step_4": "Get written agreement BEFORE missing any payments"
            },
            "why_not_dmp": [
                "❌ Auto lenders rarely participate in DMP",
                "❌ Car can be REPOSSESSED even with DMP agreement",
                "❌ Repossession damages credit severely",
                "❌ You lose transportation and way to earn income"
            ],
            "alternatives": {
                "option_1": "Forbearance - Pause or reduce payments temporarily",
                "option_2": "Refinance - If you have decent credit, refinance to lower payment",
                "option_3": "Sell the car - If upside down on loan, consider selling and paying difference"
            },
            "last_resort": {
                "organization": "Bankruptcy attorney",
                "when": "Only if you cannot reach lender AND cannot afford car",
                "why": "Chapter 7 or 13 can protect your car while restructuring debt"
            }
        }

    elif debt.debt_type == "student_loan":
        base_contact["resources"] = {
            "important_note": "Federal vs Private student loans have VERY different options",
            "federal_loans": {
                "what_they_are": "Loans from US Department of Education (Stafford, PLUS, etc)",
                "best_option": "Income-Driven Repayment Plans (government program)",
                "why_better_than_dmp": [
                    "✅ FREE (no DMP fees)",
                    "✅ Official government program",
                    "✅ Better credit protection",
                    "✅ Eligible for Public Service Loan Forgiveness (PSLF) if applicable",
                    "✅ Interest accrual may be waived (depending on plan)"
                ],
                "options": [
                    "Income-Based Repayment (IBR)",
                    "Pay As You Earn (PAYE)",
                    "Revised Pay As You Earn (REPAYE)",
                    "Income-Contingent Repayment (ICR)"
                ],
                "how_to_apply": "Visit studentaid.gov or call 1-800-4-FED-AID (1-800-433-3243)",
                "do_not_use_dmp": "For federal loans, NFCC/DMP is NOT the best path"
            },
            "private_student_loans": {
                "what_they_are": "Loans from banks, credit unions, or private lenders",
                "best_option": "Contact lender directly for forbearance/deferment",
                "if_lender_refuses": {
                    "organization": "NFCC - National Foundation for Credit Counseling",
                    "phone": "1-800-388-2227",
                    "website": "www.nfcc.org",
                    "can_help_with": "Negotiating with private lenders"
                },
                "dmp_for_private": [
                    "⚠️ NFCC can help with private student loans",
                    "⚠️ DMP will mark account 'In DMP' on credit report",
                    "⚠️ Lender may refuse to participate",
                    "✅ But: If they accept, can reduce monthly payments"
                ]
            }
        }

    elif debt.debt_type == "mortgage":
        base_contact["resources"] = {
            "primary": {
                "organization": "Contact your mortgage lender DIRECTLY",
                "why": "Mortgages have special government programs designed for hardship"
            },
            "government_programs": {
                "hamp": {
                    "name": "Home Affordable Modification Program (HAMP)",
                    "what_it_does": "Government-backed loan modification program",
                    "benefits": [
                        "Lower monthly payment",
                        "Extended loan term",
                        "Reduced interest rate",
                        "May forgive some principal"
                    ],
                    "website": "www.makinghomeaffordable.gov",
                    "phone": "1-888-995-HOPE (1-888-995-4673)"
                },
                "hmpa": {
                    "name": "Home Mortgage Protection Act",
                    "what_it_does": "Protects homeowners in hardship",
                    "protections": [
                        "Foreclosure protections",
                        "Right to loan modification",
                        "Right to forbearance"
                    ]
                }
            },
            "do_not_use_dmp": [
                "❌ Standard DMP NOT appropriate for mortgages",
                "❌ Lenders want to work directly with you",
                "❌ Government programs are better",
                "❌ NFCC cannot help modify mortgages"
            ],
            "steps": [
                "Step 1: Contact your lender's loss mitigation department",
                "Step 2: Ask about loan modification programs",
                "Step 3: Ask about HAMP eligibility",
                "Step 4: Get written loan modification agreement",
                "Step 5: If lender refuses, contact HUD: 1-800-569-4287"
            ],
            "last_resort": {
                "organization": "HUD Housing Counselor (FREE)",
                "phone": "1-800-569-4287",
                "website": "www.hud.gov",
                "why": "Independent counselor to advocate for you against lender"
            }
        }

    else:
        # Default for unknown debt types
        base_contact["resources"] = {
            "credit_counseling": {
                "organization": "NFCC - National Foundation for Credit Counseling",
                "phone": "1-800-388-2227",
                "website": "www.nfcc.org",
                "services": "FREE credit counseling and debt management plans"
            }
        }

    return base_contact


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
        warnings.append({"severity": "CRITICAL", "message": "Account likely charged off."})

    if float(debt.interest_rate) and float(debt.interest_rate) > 20:
        warnings.append({"severity": "MEDIUM", "message": f"High interest rate ({float(debt.interest_rate)}%)."})

    if float(debt.current_principal) and float(debt.current_principal) > 5000:
        warnings.append({"severity": "MEDIUM", "message": "Large balance. Better negotiating power."})

    return warnings