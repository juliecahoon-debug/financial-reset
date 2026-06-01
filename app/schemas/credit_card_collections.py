from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class CollectionAlertResponse(BaseModel):
    """Response model for a collection alert"""
    id: int
    alert_type: str
    severity: str
    message: str
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CreditCardCollectionStatusResponse(BaseModel):
    """Response model for collection status"""
    id: int
    debt_id: int
    user_id: int
    current_stage: str
    days_late: int
    charge_off_estimated_date: Optional[datetime] = None
    collection_agency_name: Optional[str] = None
    collection_agency_phone: Optional[str] = None
    last_updated: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class CollectionStatusDetailResponse(BaseModel):
    """Detailed collection status with alerts and next steps"""
    debt_id: int
    debt_name: str
    creditor: str
    current_balance: float

    collection_status: dict
    active_alerts: List[dict]
    action_items: List[str]
    disclaimers: dict
    next_steps: List[dict]
    timestamp: datetime


class AcknowledgeAlertRequest(BaseModel):
    """Request to acknowledge an alert"""
    acknowledged: bool = True


class AcknowledgeAlertResponse(BaseModel):
    """Response when alert is acknowledged"""
    alert_id: int
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    message: str
    next_alert_if_worsens: str
