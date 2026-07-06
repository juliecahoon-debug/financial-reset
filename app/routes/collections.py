from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.debt import Debt
from app.models.credit_card_collections import CreditCardCollectionStatus, CollectionAlert
from app.dependencies import get_current_user
from app.services.credit_card_collections_service import CreditCardCollectionsService
from app.schemas.credit_card_collections import (
    CreditCardCollectionStatusResponse,
    CollectionAlertResponse,
    CollectionStatusDetailResponse,
    AcknowledgeAlertRequest,
    AcknowledgeAlertResponse
)

router = APIRouter(prefix="/collections", tags=["collections"])


# Helper function to get consequences by alert type AND debt type
def get_consequences_for_alert(alert_type: str, debt_type: str) -> list:
    """Return consequences for a given alert type and debt type."""

    # Credit Card specific consequences
    if debt_type == "credit_card":
        consequences_map = {
            "30_day_late": [
                "Late fee charged to your account",
                "Card may be restricted or flagged",
                "Account may be reported as past due to credit bureaus",
                "Interest rate may increase"
            ],
            "60_day_late": [
                "Additional late fees accruing",
                "Card charging privileges may be restricted",
                "Credit score impact significant",
                "Collection agency contact may begin soon",
                "Account closure risk increasing"
            ],
            "90_day_late": [
                "Card suspended - no new charges allowed",
                "Debt collection calls likely beginning",
                "Severe credit score damage",
                "Account likely on creditor's charge-off list",
                "Settlement options still available but limited"
            ],
            "120_day_late": [
                "Card revoked or restricted (creditor-dependent)",
                "Some creditors may offer reinstatement if paid current",
                "Charge-off imminent within 30 days",
                "Collection agency assignment likely",
                "Legal action possible (creditor-dependent)"
            ],
            "charged_off": [
                "Account charged off - creditor may assign to collections",
                "Card permanently revoked or restricted",
                "Reinstatement unlikely but may be possible with settlement",
                "Collection agency may contact you",
                "Legal action possible",
                "Credit damage will persist for 7 years from charge-off date"
            ]
        }

    # Auto Loan specific consequences
    elif debt_type == "auto_loan":
        consequences_map = {
            "30_day_late": [
                "Late fee charged to your account",
                "Negative mark reported to credit bureaus",
                "Interest rate may increase",
                "Creditor may contact you about payment"
            ],
            "60_day_late": [
                "Additional late fees accruing",
                "Repossession notice may be sent",
                "Credit score impact significant",
                "Vehicle at risk - creditor may repossess",
                "Collection agency contact may begin"
            ],
            "90_day_late": [
                "VEHICLE REPOSSESSION IMMINENT",
                "Repossession can occur without notice (varies by state)",
                "Debt collection calls likely beginning",
                "Severe credit score damage",
                "Settlement options very limited"
            ],
            "120_day_late": [
                "Vehicle likely repossessed or repossession imminent",
                "Deficiency balance may be owed after vehicle sale",
                "Collection agency assigned",
                "Legal action possible for deficiency",
                "Credit damage will persist for 7 years"
            ],
            "charged_off": [
                "Account charged off - vehicle repossessed or at imminent risk",
                "Deficiency balance may be substantial",
                "Collection agency will pursue deficiency payment",
                "Wage garnishment possible (creditor-dependent)",
                "Legal action highly likely"
            ]
        }

    # Student Loan specific consequences
    elif debt_type == "student_loan":
        consequences_map = {
            "30_day_late": [
                "Account reported as delinquent",
                "Credit score impact beginning",
                "Loan servicer will contact you",
                "Income-Driven Repayment Plans may be available"
            ],
            "60_day_late": [
                "Significant delinquency recorded",
                "Credit score impact increasing",
                "Wage garnishment process may begin",
                "Rehabilitation or consolidation options available"
            ],
            "90_day_late": [
                "Loan in default status",
                "Wage garnishment possible (federal loans)",
                "Tax refund offset possible (federal loans)",
                "Credit score severely damaged",
                "Default interest may be charged"
            ],
            "120_day_late": [
                "Loan in default - guaranty agency assigned",
                "Wage garnishment likely (federal loans)",
                "Tax refund offset likely (federal loans)",
                "Collection fees may be charged",
                "Professional license suspension possible (some states)"
            ],
            "charged_off": [
                "Loan in default - assigned to debt collector",
                "Wage garnishment active or imminent (federal)",
                "Tax refund offset active or imminent (federal)",
                "Extensive collection efforts ongoing",
                "Credit damage will persist for 7 years from default"
            ]
        }

    # Personal Loan specific consequences
    elif debt_type == "personal_loan":
        consequences_map = {
            "30_day_late": [
                "Late fee charged to account",
                "Account reported to credit bureaus as past due",
                "Interest rate may increase",
                "Creditor will contact you about payment"
            ],
            "60_day_late": [
                "Additional late fees accruing",
                "Credit score impact significant",
                "Collection agency contact may begin",
                "Acceleration clause may be triggered (full amount due)"
            ],
            "90_day_late": [
                "Loan likely accelerated (full balance due immediately)",
                "Debt collection calls likely",
                "Legal action imminent",
                "Wage garnishment possible",
                "Credit score severely damaged"
            ],
            "120_day_late": [
                "Legal action likely filed or filed",
                "Wage garnishment possible or active",
                "Bank account levy possible",
                "Collection attorney may be assigned",
                "Judgment may be entered against you"
            ],
            "charged_off": [
                "Account charged off and assigned to debt collector",
                "Lawsuit likely or already filed",
                "Wage garnishment possible or active",
                "Bank account levy possible",
                "Credit damage will persist for 7 years from charge-off"
            ]
        }

    # Mortgage specific consequences
    elif debt_type == "mortgage":
        consequences_map = {
            "30_day_late": [
                "Late payment reported to credit bureaus",
                "Late fees charged to loan balance",
                "Lender will contact you about payment",
                "Home equity at risk if delinquency continues"
            ],
            "60_day_late": [
                "Serious delinquency status",
                "Additional late fees accruing",
                "Credit score impact significant",
                "Pre-foreclosure notice may be sent"
            ],
            "90_day_late": [
                "Foreclosure process may begin",
                "Formal notice of default or intent to foreclose",
                "Severe credit score damage",
                "Home ownership at serious risk",
                "Legal action imminent"
            ],
            "120_day_late": [
                "Foreclosure proceedings likely initiated",
                "Home may be scheduled for sale at auction",
                "Eviction possible",
                "Home loss imminent",
                "Deficiency balance possible after sale (varies by state)"
            ],
            "charged_off": [
                "Home likely foreclosed or foreclosure in final stages",
                "Eviction proceedings active",
                "Deficiency judgment possible (varies by state)",
                "Homelessness risk",
                "Credit damage will persist for 7 years"
            ]
        }

    else:
        # Default consequences for unknown debt types
        consequences_map = {
            "30_day_late": [
                "Late fee charged",
                "Account reported to credit bureaus",
                "Interest rate may increase"
            ],
            "60_day_late": [
                "Additional fees accruing",
                "Credit score impact significant",
                "Collection contact may begin"
            ],
            "90_day_late": [
                "Account in serious delinquency",
                "Collection agency contact likely",
                "Legal action possible"
            ],
            "120_day_late": [
                "Account charge-off imminent",
                "Collection agency assigned",
                "Legal action likely"
            ],
            "charged_off": [
                "Account charged off",
                "Collection agency active",
                "Legal action possible"
            ]
        }

    return consequences_map.get(alert_type, [])


@router.get("/{debt_id}/status", response_model=CollectionStatusDetailResponse)
async def get_collection_status(
        debt_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get collection status for a debt.

    Shows:
    - Current delinquency stage (current, 30 days late, 60 days late, etc)
    - Days late
    - Estimated charge-off date
    - Active alerts
    - Recommended action items
    - Compliance disclaimers

    ⚠️ IMPORTANT DISCLAIMERS:

    EDUCATIONAL USE ONLY:
    - This information is based on your reported data
    - Actual delinquency status depends on creditor records
    - Contact your creditor for official status

    TIMELINES ARE ESTIMATES (Vary by Debt Type):
    - Credit Cards: Charge-off typically occurs at 150+ days late
    - Auto Loans: Repossession typically occurs at 90-120+ days late
    - Mortgages: Foreclosure typically begins at 90-120+ days late
    - Student Loans: Default typically occurs at 90-120+ days late
    - Personal Loans: Charge-off typically occurs at 120-150+ days late
    - These are estimates only - actual timelines vary by creditor

    IMMEDIATE ACTION NEEDED:
    - If status shows 30+ days late, contact creditor immediately
    - Do not wait to take action
    - Earlier intervention = better outcomes
    - For auto loans, contact creditor immediately to prevent repossession
    """


    # Get debt
    debt = db.query(Debt).filter(
        Debt.id == debt_id,
        Debt.user_id == current_user.id
    ).first()

    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")

    # Get or create collection status
    status = CreditCardCollectionsService.get_collection_status(debt_id, db)

    if not status:
        # If no status exists, create one with current days_late
        # (For now, assume 0 days late if not tracked)
        status = CreditCardCollectionsService.update_collection_status(
            debt_id=debt_id,
            user_id=current_user.id,
            days_late=0,
            db=db
        )

    # Get alerts for this debt
    alerts = db.query(CollectionAlert).filter(
        CollectionAlert.status_id == status.id
    ).all()

    # Build response
    days_until_charge_off = None
    if status.charge_off_estimated_date:
        days_until_charge_off = (status.charge_off_estimated_date - datetime.utcnow()).days

    action_items = []
    if status.current_stage == "current":
        action_items = ["Monitor account regularly", "Keep making on-time payments"]
    elif status.current_stage == "30_day_late":
        action_items = ["Contact creditor immediately", "Discuss hardship program or payment plan"]
    elif status.current_stage == "60_day_late":
        action_items = ["Contact creditor TODAY", "Propose settlement or hardship plan"]
    elif status.current_stage == "90_day_late":
        action_items = ["Settlement negotiations or hardship plan needed NOW", "Charge-off imminent"]
    elif status.current_stage == "120_day_late":
        action_items = ["Settlement negotiations needed", "Charge-off imminent within 30 days"]
    elif status.current_stage == "charged_off":
        action_items = ["Expect collection agency contact", "Settlement still possible but limited"]

    next_steps = [
        {
            "action": f"Call {debt.creditor_name}",
            "timeline": "TODAY" if status.current_stage != "current" else "This month",
            "why": "Confirm delinquency status and discuss options"
        },
        {
            "action": "Get written agreement",
            "timeline": "Before making payments",
            "why": "Protects you and documents terms"
        }
    ]

    active_alerts = [
        {
            "alert_id": alert.id,
            "type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "consequences": get_consequences_for_alert(alert.alert_type, debt.debt_type),
            "created_at": alert.created_at,
            "acknowledged": alert.acknowledged
        }
        for alert in alerts
    ]

    response = CollectionStatusDetailResponse(
        debt_id=debt_id,
        debt_name=debt.name,
        creditor=debt.creditor_name,
        current_balance=float(debt.current_principal),
        collection_status={
            "stage": status.current_stage,
            "severity": {
                "current": "LOW",
                "30_day_late": "MEDIUM",
                "60_day_late": "MEDIUM HIGH",
                "90_day_late": "HIGH",
                "120_day_late": "SEVERE",
                "charged_off": "CRITICAL"
            }.get(status.current_stage, "CRITICAL"),
            "days_until_charge_off": days_until_charge_off,
            "charge_off_estimated_date": status.charge_off_estimated_date
        },
        active_alerts=active_alerts,
        action_items=action_items,
        disclaimers={
            "information_type": "EDUCATIONAL",
            "charge_off_timeline": (
                "Charge-off typically occurs at 150+ days late" if debt.debt_type == "credit_card"
                else "Repossession typically occurs at 90-120+ days late" if debt.debt_type == "auto_loan"
                else "Foreclosure typically begins at 90-120+ days late" if debt.debt_type == "mortgage"
                else "Default status typically occurs at 90-120+ days late" if debt.debt_type == "student_loan"
                else "Charge-off typically occurs at 120-150+ days late"
            ),
            "collection_likely": (
                "Account may be sent to collections after charge-off" if debt.debt_type == "credit_card"
                else "Vehicle may be repossessed and sold; deficiency balance may be owed" if debt.debt_type == "auto_loan"
                else "Home will be foreclosed and sold; deficiency may be owed (varies by state)" if debt.debt_type == "mortgage"
                else "Account will be assigned to debt collector; wage garnishment possible (federal loans)" if debt.debt_type == "student_loan"
                else "Account may be sent to collections"
            ),
            "contact_creditor": "Contact your creditor for official delinquency status and available options"
        },
        next_steps=next_steps,
        timestamp=datetime.utcnow()
    )

    return response


@router.get("/alerts", response_model=dict)
async def get_collection_alerts(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all collection alerts for the user.

    Shows:
    - All unacknowledged alerts
    - Alert type, severity, and message
    - Action items for each alert
    - Links to hardship options

    ⚠️ DISCLAIMERS:

    TIMELY ALERTS:
    - Alerts are created when account reaches new delinquency stage
    - Check this regularly for updates

    EDUCATION ONLY:
    - This is educational information
    - Not official notice from creditor
    - Contact creditor for official communication

    ACTION REQUIRED:
    - Do not ignore critical alerts
    - Take action immediately when status worsens
    """

    # Get all alerts for user
    alerts = CreditCardCollectionsService.get_alerts_for_user(current_user.id, db)

    # Build response
    alert_list = []
    for alert in alerts:
        # Get debt name from the status
        status = alert.status
        debt = db.query(Debt).filter(Debt.id == status.debt_id).first()

        alert_list.append({
            "alert_id": alert.id,
            "debt_id": status.debt_id,
            "debt_name": debt.name if debt else "Unknown",
            "type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "consequences": get_consequences_for_alert(alert.alert_type, debt.debt_type),
            "created_at": alert.created_at,
            "days_since_alert": (datetime.utcnow() - alert.created_at).days,
            "recommended_action": "Contact creditor immediately" if alert.severity == "CRITICAL" else "Review your hardship options",
            "action_url": f"/hardship/options/{status.debt_id}",
            "acknowledged": alert.acknowledged
        })

    return {
        "total_alerts": len(alerts),
        "critical_alerts": sum(1 for a in alerts if a.severity == "CRITICAL"),
        "alerts": alert_list,
        "disclaimers": {
            "information_type": "EDUCATIONAL ALERTS",
            "not_legal_advice": "These are estimates based on your data. Contact creditor for official information.",
            "timing_estimates": "Actual timelines may vary. Contact creditor immediately for accurate information."
        }
    }


@router.post("/alerts/{alert_id}/acknowledge", response_model=AcknowledgeAlertResponse)
async def acknowledge_alert(
        alert_id: int,
        request: AcknowledgeAlertRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Mark an alert as acknowledged by user.

    This indicates the user has seen and understands the alert.

    ⚠️ ACKNOWLEDGEMENT NOTE:
    - Acknowledging does NOT resolve the issue
    - You still need to take action with your creditor
    - Use this to track which alerts you've reviewed
    """

    # Get alert
    alert = db.query(CollectionAlert).filter(
        CollectionAlert.id == alert_id
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Verify ownership (alert belongs to current user's debt)
    status = alert.status
    if status.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Acknowledge it
    updated_alert = CreditCardCollectionsService.acknowledge_alert(alert_id, db)

    response = AcknowledgeAlertResponse(
        alert_id=updated_alert.id,
        acknowledged=updated_alert.acknowledged,
        acknowledged_at=updated_alert.acknowledged_at,
        message="Alert marked as acknowledged. Remember to take action immediately.",
        next_alert_if_worsens="If account reaches next delinquency stage, new critical alert will be created"
    )

    return response

