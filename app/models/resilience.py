from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class ResilienceScore(Base):
    __tablename__ = "resilience_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Overall Score
    total_score = Column(Float, nullable=False)
    financial_state = Column(String(20), nullable=False)

    # Individual Dimension Scores (0-100 each)
    emergency_buffer_score = Column(Float)
    debt_service_ratio_score = Column(Float)
    income_stability_score = Column(Float)
    insurance_coverage_score = Column(Float)
    concentration_risk_score = Column(Float)
    credit_access_score = Column(Float)
    recovery_velocity_score = Column(Float)

    # Raw Data (for trend analysis and display)
    emergency_buffer_months = Column(Float)
    debt_service_ratio_percent = Column(Float)
    income_stability_percent = Column(Float)
    insurance_coverage_percent = Column(Float)
    concentration_risk_ratio = Column(Float)
    credit_utilization_percent = Column(Float)
    recovery_months = Column(Float)

    # Calculation metadata
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    calculation_version = Column(String(10), default="1.0")
