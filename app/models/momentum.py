from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class MomentumCalculation(Base):
    __tablename__ = "momentum_calculations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Current score snapshot
    current_resilience_score = Column(Float, nullable=False)

    # Historical score snapshots (nullable — may not exist yet for new users)
    score_30_days_ago = Column(Float, nullable=True)
    score_90_days_ago = Column(Float, nullable=True)
    score_6_months_ago = Column(Float, nullable=True)

    # Point changes (can be negative)
    momentum_30_days = Column(Float, nullable=True)
    momentum_90_days = Column(Float, nullable=True)
    momentum_6_months = Column(Float, nullable=True)

    # Direction: "improving" | "declining" | "stable" | "unknown"
    direction = Column(String(20), nullable=False)

    # Rate of change in points per month
    velocity_points_per_month = Column(Float, nullable=False)

    # Projection: score in 30 days if current trend continues
    projected_score_30_days = Column(Float, nullable=False)

    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
