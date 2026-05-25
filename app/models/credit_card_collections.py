from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class CreditCardCollectionStatus(Base):
    """Track collection status for a credit card debt"""
    __tablename__ = "credit_card_collection_statuses"

    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, unique=True, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)

    # Current status
    current_stage = Column(String,
                           default="current")  # current, 30_day_late, 60_day_late, 90_day_late, charged_off, in_collections
    days_late = Column(Integer, default=0)
    charge_off_estimated_date = Column(DateTime, nullable=True)

    # Collection info
    collection_agency_name = Column(String, nullable=True)
    collection_agency_phone = Column(String, nullable=True)

    # Tracking
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    alerts = relationship("CollectionAlert", back_populates="status", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CollectionStatus(debt_id={self.debt_id}, stage={self.current_stage}, days_late={self.days_late})>"


class CollectionAlert(Base):
    """Alert for collection events (30 days late, 60 days late, etc)"""
    __tablename__ = "collection_alerts"

    id = Column(Integer, primary_key=True, index=True)
    status_id = Column(Integer, ForeignKey("credit_card_collection_statuses.id"), nullable=False)

    # Alert details
    alert_type = Column(String, nullable=False)  # 30_day_late, 60_day_late, 90_day_late, charged_off, in_collections
    severity = Column(String, nullable=False)  # low, medium, high, critical
    message = Column(String, nullable=False)

    # User interaction
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    status = relationship("CreditCardCollectionStatus", back_populates="alerts")

    def __repr__(self):
        return f"<CollectionAlert(type={self.alert_type}, severity={self.severity}, acknowledged={self.acknowledged})>"
