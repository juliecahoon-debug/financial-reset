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

    TIMELINES ARE ESTIMATES:
    - Charge-off typically occurs at 120-180 days late
    - Collection agency involvement timing varies by creditor
    - These are estimates only

    IMMEDIATE ACTION NEEDED:
    - If status shows 30+ days late, contact creditor immediately
    - Do not wait to take action
    - Earlier intervention = better outcomes
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
    elif status.current_stage == "charged_off":
        action_items = ["Expect collection agency contact", "Settlement still possible but limited"]

    next_steps = [
        {
            "action": f"Call {debt.creditor}",
            "timeline": "TODAY" if status.current_stage != "current" else "This month",
            "why": "Confirm delinquency status and discuss options"
        },
        {
            "action": "Get written agreement",
            "timeline": "Before making payments",
            "why": "Protects you and documents terms"
        }
    ]

    response = CollectionStatusDetailResponse(
        debt_id=debt_id,
        debt_name=debt.name,
        creditor=debt.creditor,
        current_balance=float(debt.balance),
        collection_status={
            "stage": status.current_stage,
            "severity": "LOW" if status.current_stage == "current" else "CRITICAL",
            "days_until_charge_off": days_until_charge_off,
            "charge_off_estimated_date": status.charge_off_estimated_date
        },
        active_alerts=[
            {
                "alert_id": alert.id,
                "type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "created_at": alert.created_at,
                "acknowledged": alert.acknowledged
            }
            for alert in alerts
        ],
        action_items=action_items,
        disclaimers={
            "information_type": "EDUCATIONAL",
            "charge_off_timeline": "Charge-off typically occurs at 120-180 days late",
            "collection_likely": "Account may be sent to collections after charge-off",
            "contact_creditor": "Contact your creditor for official delinquency status"
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
