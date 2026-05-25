from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.debt import Debt
from app.models.credit_card_collections import CreditCardCollectionStatus, CollectionAlert
from typing import Optional, List, Dict

class CreditCardCollectionsService:
    """Service for tracking credit card collection status and alerts"""

    @staticmethod
    def calculate_charge_off_date(days_late: int) -> Optional[datetime]:
        """Calculate estimated charge-off date based on days late.

        Charge-off typically occurs at 120-180 days late.
        We estimate 150 days as average.
        """
        if days_late >= 120:
            # Already charged off or very close
            return datetime.utcnow() - timedelta(days=1)  # Already happened
        elif days_late > 0:
            # Estimate: charge-off will happen at 150 days
            days_until_charge_off = 150 - days_late
            return datetime.utcnow() + timedelta(days=days_until_charge_off)
        else:
            return None

    @staticmethod
    def determine_stage(days_late: int) -> str:
        """Determine collection stage based on days late.

        Stages:
        - current: 0 days late
        - 30_day_late: 30-59 days late
        - 60_day_late: 60-89 days late
        - 90_day_late: 90-119 days late
        - charged_off: 120+ days late
        """
        if days_late == 0:
            return "current"
        elif days_late < 30:
            return "current"
        elif days_late < 60:
            return "30_day_late"
        elif days_late < 90:
            return "60_day_late"
        elif days_late < 120:
            return "90_day_late"
        else:
            return "charged_off"

    @staticmethod
    def create_alert_for_stage(stage: str, days_late: int) -> Dict:
        """Create alert data for a collection stage.

        Returns dict with: alert_type, severity, message
        """
        if stage == "current":
            return None  # No alert for current accounts

        elif stage == "30_day_late":
            return {
                "alert_type": "30_day_late",
                "severity": "HIGH",
                "message": "Your account is 30 days past due. Contact creditor immediately."
            }

        elif stage == "60_day_late":
            return {
                "alert_type": "60_day_late",
                "severity": "CRITICAL",
                "message": "Account is 60 days late. Charge-off window closing. Contact creditor today."
            }

        elif stage == "90_day_late":
            return {
                "alert_type": "90_day_late",
                "severity": "CRITICAL",
                "message": "Charge-off imminent (within 30 days). Settlement negotiations or hardship plan needed NOW."
            }

        elif stage == "charged_off":
            return {
                "alert_type": "charged_off",
                "severity": "CRITICAL",
                "message": "Account charged off. May be sent to collection agency. Settlement still possible but limited."
            }

        return None

    @staticmethod
    def update_collection_status(
            debt_id: int,
            user_id: int,
            days_late: int,
            db: Session
    ) -> CreditCardCollectionStatus:
        """Update or create collection status for a debt.

        Args:
            debt_id: ID of the debt
            user_id: ID of the user
            days_late: Current days late
            db: Database session

        Returns:
            CreditCardCollectionStatus object
        """

        # Find or create status
        status = db.query(CreditCardCollectionStatus).filter(
            CreditCardCollectionStatus.debt_id == debt_id
        ).first()

        if not status:
            # Create new status
            status = CreditCardCollectionStatus(
                debt_id=debt_id,
                user_id=user_id,
                days_late=days_late
            )
            db.add(status)
        else:
            # Update existing status
            status.days_late = days_late

        # Determine current stage
        current_stage = CreditCardCollectionsService.determine_stage(days_late)

        # Check if stage changed
        stage_changed = (status.current_stage != current_stage)

        # Update stage
        status.current_stage = current_stage
        status.charge_off_estimated_date = CreditCardCollectionsService.calculate_charge_off_date(days_late)
        status.last_updated = datetime.utcnow()

        db.commit()
        db.refresh(status)

        # If stage changed, create alert
        if stage_changed and current_stage != "current":
            alert_data = CreditCardCollectionsService.create_alert_for_stage(current_stage, days_late)
            if alert_data:
                new_alert = CollectionAlert(
                    status_id=status.id,
                    alert_type=alert_data["alert_type"],
                    severity=alert_data["severity"],
                    message=alert_data["message"]
                )
                db.add(new_alert)

        return status

    @staticmethod
    def get_collection_status(debt_id: int, db: Session) -> Optional[CreditCardCollectionStatus]:
        """Get collection status for a debt."""
        return db.query(CreditCardCollectionStatus).filter(
            CreditCardCollectionStatus.debt_id == debt_id
        ).first()

    @staticmethod
    def get_alerts_for_user(user_id: int, db: Session, unacknowledged_only: bool = False) -> List[CollectionAlert]:
        """Get all collection alerts for a user.

        Args:
            user_id: User ID
            db: Database session
            unacknowledged_only: If True, only return unacknowledged alerts

        Returns:
            List of CollectionAlert objects
        """
        query = db.query(CollectionAlert).join(
            CreditCardCollectionStatus
        ).filter(
            CreditCardCollectionStatus.user_id == user_id
        )

        if unacknowledged_only:
            query = query.filter(CollectionAlert.acknowledged == False)

        return query.order_by(CollectionAlert.created_at.desc()).all()

    @staticmethod
    def acknowledge_alert(alert_id: int, db: Session) -> CollectionAlert:
        """Mark an alert as acknowledged by user."""
        alert = db.query(CollectionAlert).filter(
            CollectionAlert.id == alert_id
        ).first()

        if alert:
            alert.acknowledged = True
            alert.acknowledged_at = datetime.utcnow()
            db.commit()
            db.refresh(alert)

        return alert
