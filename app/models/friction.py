from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from datetime import datetime
from app.database import Base


class FrictionPoint(Base):
    __tablename__ = "friction_points"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Friction classification
    friction_type = Column(String(50), nullable=False)   # e.g. "high_debt_load"
    severity = Column(String(20), nullable=False)         # "critical" | "high" | "medium" | "low"
    description = Column(String(500), nullable=False)     # Human-readable explanation
    impact_on_resilience = Column(Float, nullable=False)  # Points lost due to this friction

    # Threshold data
    current_value = Column(Float, nullable=True)   # e.g. 55.0 (55% DTI)
    threshold = Column(Float, nullable=True)        # e.g. 50.0 (50% threshold)

    # Action guidance
    recommended_action = Column(String(500), nullable=False)
    estimated_improvement = Column(Float, nullable=False)  # Points gained if resolved

    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
