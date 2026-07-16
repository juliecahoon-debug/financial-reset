from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class ResilienceScore(Base):
    __tablename__ = "resilience_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Overall Score
    total_score = Column(Float, nullable=False)          # 0-100
    financial_state = Column(String(20), nullable=False) # thriving / stable / strained / stressed / in_crisis

    # Individual Dimension Scores (0-100 each)
    emergency_buffer_score = Column(Float)
    debt_service_ratio_score = Column(Float)
    income_stability_score = Column(Float)
    insurance_coverage_score = Column(Float)
    concentration_risk_score = Column(Float)
    credit_access_score = Column(Float)
    recovery_velocity_score = Column(Float)

    # Raw Data (for trend analysis and display)
    emergency_buffer_months = Column(Float)        # Actual months of expenses covered
    debt_service_ratio_percent = Column(Float)     # % of income going to debt
    income_stability_percent = Column(Float)       # Coefficient of variation %
    insurance_coverage_percent = Column(Float)     # % of needs covered
    concentration_risk_ratio = Column(Float)       # 1.0 = single source, 2.0+ = diversified
    credit_utilization_percent = Column(Float)     # % of credit used
    recovery_months = Column(Float)               # Months to recover from $1K shock

    # Metadata
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    calculation_version = Column(String(10), default="v1.0")
