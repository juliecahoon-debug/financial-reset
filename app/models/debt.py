from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Date, JSON, \
    Numeric
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
from enum import Enum
from decimal import Decimal


# ============================================================================
# ENUMS - Type-safe domain values
# ============================================================================

class DebtType(str, Enum):
    """Types of debt - all 6 major categories"""
    CREDIT_CARD = "credit_card"
    FEDERAL_STUDENT_LOAN = "federal_student_loan"
    PRIVATE_STUDENT_LOAN = "private_student_loan"
    PERSONAL_LOAN = "personal_loan"
    AUTO_LOAN = "auto_loan"
    MORTGAGE = "mortgage"


class DebtStatus(str, Enum):
    """Current delinquency status"""
    CURRENT = "current"
    DELINQ_30 = "delinq_30"  # 30 days past due
    DELINQ_60 = "delinq_60"  # 60 days past due
    DELINQ_90 = "delinq_90"  # 90 days past due
    DELINQ_120 = "delinq_120"  # 120 days past due
    CHARGE_OFF = "charge_off"  # Charged off (180+ days)
    COLLECTIONS = "collections"  # In collections
    SETTLED = "settled"  # Settled/paid off
    PAID_OFF = "paid_off"  # Completely paid off


class HardshipType(str, Enum):
    """Type of hardship"""
    JOB_LOSS = "job_loss"
    MEDICAL = "medical"
    DIVORCE = "divorce"
    DISASTER = "disaster"
    INCOME_REDUCTION = "income_reduction"
    OTHER = "other"


class HardshipStatus(str, Enum):
    """Status of hardship case"""
    OPEN = "open"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ReliefProgramType(str, Enum):
    """Type of hardship relief program"""
    DEFERMENT = "deferment"
    FORBEARANCE = "forbearance"
    INCOME_DRIVEN_REPAYMENT = "income_driven_repayment"
    RATE_REDUCTION = "rate_reduction"
    PAYMENT_PLAN = "payment_plan"
    SETTLEMENT = "settlement"
    MODIFICATION = "modification"


# ============================================================================
# CORE DEBT TABLE
# ============================================================================

class Debt(Base):
    """Core debt tracking - foundation for all debt types"""
    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # DEBT IDENTIFICATION
    name = Column(String(255), nullable=False)  # e.g., "Chase Credit Card", "Navient Student Loan"
    debt_type = Column(SQLEnum(DebtType), nullable=False, index=True)
    creditor_name = Column(String(255), nullable=False)  # Who you owe money to
    account_number = Column(String(50))  # Last 4 digits

    # FINANCIAL DATA (use Decimal for precision)
    original_balance = Column(Numeric(18, 2), nullable=False)  # Original amount borrowed
    current_principal = Column(Numeric(18, 2), nullable=False)  # Principal still owed
    interest_rate = Column(Numeric(6, 4), nullable=False)  # APR (e.g., 7.5000)
    monthly_payment = Column(Numeric(12, 2))  # Current required payment
    minimum_payment = Column(Numeric(12, 2))  # Minimum payment required

    # DATES (all timezone-aware)
    originated_date = Column(DateTime(timezone=True))  # When loan originated
    opened_date = Column(DateTime(timezone=True))  # When account opened
    first_delinquency_date = Column(DateTime(timezone=True))  # When first delinquent
    charge_off_date = Column(DateTime(timezone=True))  # When charged off
    paid_off_date = Column(DateTime(timezone=True))  # When fully paid
    due_date_day = Column(Integer)  # Day of month payment due (1-31)

    # STATUS TRACKING
    status = Column(SQLEnum(DebtStatus), default=DebtStatus.CURRENT, index=True)
    days_past_due = Column(Integer, default=0)  # Current DPD
    months_to_charge_off = Column(Integer)  # Estimated months until charge-off

    # COLLECTIONS DATA
    in_collections = Column(Boolean, default=False)
    collector_name = Column(String(255))  # Name of collection agency
    collection_agency_phone = Column(String(20))
    collection_agency_address = Column(String(500))

    # STATE-SPECIFIC RULES (soft delete, is_active flag)
    is_active = Column(Boolean, default=True)  # Soft delete

    # METADATA
    notes = Column(String(1000))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # RELATIONSHIPS
    user = relationship("User", back_populates="debts")
    loan_status = relationship("LoanStatus", uselist=False, back_populates="debt", cascade="all, delete-orphan")
    hardship_cases = relationship("HardshipCase", back_populates="debt", cascade="all, delete-orphan")
    hardship_plans = relationship("HardshipPlan", back_populates="debt", cascade="all, delete-orphan")
    loan_events = relationship("LoanEvent", back_populates="debt", cascade="all, delete-orphan")
    settlement_negotiations = relationship("SettlementNegotiation", back_populates="debt", cascade="all, delete-orphan")
    cost_benefit_analyses = relationship("CostBenefitAnalysis", back_populates="debt", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Debt(id={self.id}, user_id={self.user_id}, name={self.name}, balance={self.current_principal}, status={self.status})>"


# ============================================================================
# DEBT STATUS TRACKING (Separate from Debt for clean separation)
# ============================================================================

class LoanStatus(Base):
    """Current status snapshot - separate from Debt for normalization"""
    __tablename__ = "loan_statuses"

    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"), nullable=False, unique=True)

    # STATUS
    status = Column(SQLEnum(DebtStatus), nullable=False)
    days_past_due = Column(Integer, default=0)

    # PAYMENT TRACKING
    scheduled_payment = Column(Numeric(12, 2))  # What they should pay
    amount_past_due = Column(Numeric(12, 2), default=0)  # Amount overdue
    last_payment_date = Column(DateTime(timezone=True))  # When last payment made
    next_due_date = Column(DateTime(timezone=True))  # When next payment due

    # DELINQUENCY TIMELINE
    status_changed_date = Column(DateTime(timezone=True))  # When status last changed

    # CHARGE-OFF TRACKING
    estimated_charge_off_date = Column(DateTime(timezone=True))  # Predicted charge-off
    days_to_charge_off = Column(Integer)  # Days remaining until charge-off

    # METADATA
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # RELATIONSHIPS
    debt = relationship("Debt", back_populates="loan_status")

    def __repr__(self):
        return f"<LoanStatus(debt_id={self.debt_id}, status={self.status}, dpp={self.days_past_due})>"


# ============================================================================
# HARDSHIP CASE TRACKING
# ============================================================================

class HardshipCase(Base):
    """Hardship case - when user applies for hardship relief"""
    __tablename__ = "hardship_cases"

    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # HARDSHIP DETAILS
    hardship_type = Column(SQLEnum(HardshipType), nullable=False)
    hardship_description = Column(String(1000))  # User's explanation
    hardship_start_date = Column(DateTime(timezone=True), nullable=False)
    expected_duration_months = Column(Integer)  # How long hardship will last

    # FINANCIAL SITUATION
    income_before_hardship = Column(Numeric(12, 2))  # Monthly income before hardship
    income_during_hardship = Column(Numeric(12, 2))  # Current monthly income
    monthly_expenses = Column(Numeric(12, 2))  # Essential expenses

    # WHAT THEY CAN PAY
    can_pay_monthly = Column(Numeric(12, 2))  # Amount they can realistically pay
    hardship_monthly_payment = Column(Numeric(12, 2))  # Proposed payment during hardship

    # STATUS
    case_status = Column(SQLEnum(HardshipStatus), default=HardshipStatus.OPEN)
    approved_programs = Column(JSON, default=list)  # Array of approved program IDs

    # DOCUMENTATION
    documents_submitted = Column(JSON, default=list)  # ["termination_letter", "bank_statement", ...]
    documents_required = Column(JSON, default=list)  # What still needs to be submitted

    # METADATA
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_date = Column(DateTime(timezone=True))

    # RELATIONSHIPS
    debt = relationship("Debt", back_populates="hardship_cases")
    user = relationship("User", back_populates="hardship_cases")
    hardship_plans = relationship("HardshipPlan", back_populates="hardship_case")

    def __repr__(self):
        return f"<HardshipCase(id={self.id}, debt_id={self.debt_id}, type={self.hardship_type}, status={self.case_status})>"


# ============================================================================
# LOSS MITIGATION OPTIONS / RELIEF PROGRAMS
# ============================================================================

class HardshipPlan(Base):
    """Specific relief program (deferment, forbearance, settlement, etc.)"""
    __tablename__ = "hardship_plans"

    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"), nullable=False)
    hardship_case_id = Column(Integer, ForeignKey("hardship_cases.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # PROGRAM TYPE
    program_type = Column(SQLEnum(ReliefProgramType), nullable=False)
    program_name = Column(String(255))  # "3-Month Payment Pause", "Settlement Offer", etc.

    # PROGRAM DETAILS (flexible for different types)
    description = Column(String(1000))  # What the program offers
    eligibility_criteria = Column(String(500))  # What you need to qualify

    # FINANCIAL TERMS
    monthly_payment_during = Column(Numeric(12, 2))  # New payment (may be 0 for deferment)
    duration_months = Column(Integer)  # How long the program lasts

    # Settlement-specific
    settlement_percentage = Column(Numeric(5, 4))  # 0.50 = 50% settlement
    settlement_lump_sum = Column(Numeric(12, 2))  # Total settlement amount
    settlement_deadline = Column(DateTime(timezone=True))  # By when to pay

    # Deferment/Forbearance-specific
    interest_accrues = Column(Boolean, default=True)  # Does interest continue to accrue?

    # IMPACT
    credit_reporting_treatment = Column(String(100))  # "Paused", "Normal", "Settled"
    credit_impact_score = Column(Integer)  # Estimated credit score change (-50 to +50)
    total_cost = Column(Numeric(12, 2))  # Total you'll pay under this plan

    # STATUS
    status = Column(String(50), default="available")  # available, applied, approved, rejected, active, completed
    approval_date = Column(DateTime(timezone=True))
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))

    # SUCCESS RATE (proprietary data - your moat!)
    success_rate_percent = Column(Integer)  # % of users this works for (from your data)
    typical_approval_days = Column(Integer)  # How many days to approve typically

    # METADATA
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # RELATIONSHIPS
    debt = relationship("Debt", back_populates="hardship_plans")
    hardship_case = relationship("HardshipCase", back_populates="hardship_plans")
    user = relationship("User", back_populates="hardship_plans")

    def __repr__(self):
        return f"<HardshipPlan(id={self.id}, type={self.program_type}, status={self.status})>"


# ============================================================================
# SETTLEMENT NEGOTIATION TRACKING (Your proprietary tracking!)
# ============================================================================

class SettlementNegotiation(Base):
    """Track settlement negotiations and outcomes"""
    __tablename__ = "settlement_negotiations"

    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # NEGOTIATION DETAILS
    settlement_requested_date = Column(DateTime(timezone=True), nullable=False)
    settlement_requested_amount = Column(Numeric(12, 2))  # What you offered
    settlement_accepted_amount = Column(Numeric(12, 2))  # What they accepted
    settlement_percentage = Column(Numeric(5, 4))  # 0.50 = 50% settlement

    # TIMELINE
    settlement_deadline = Column(DateTime(timezone=True))  # By when to pay
    settlement_paid_date = Column(DateTime(timezone=True))  # When you paid

    # STATUS
    status = Column(String(50), default="pending")  # pending, counter_offered, accepted, rejected, paid

    # OUTCOME DATA (YOUR MOAT - track what actually works!)
    successful = Column(Boolean)  # Did this settlement go through?
    reason_rejected = Column(String(500))  # If rejected, why?
    lessons_learned = Column(String(1000))  # What did you learn?

    # METADATA
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # RELATIONSHIPS
    debt = relationship("Debt", back_populates="settlement_negotiations")
    user = relationship("User", back_populates="settlement_negotiations")

    def __repr__(self):
        return f"<SettlementNegotiation(id={self.id}, status={self.status}, amount={self.settlement_accepted_amount})>"


# ============================================================================
# LOAN EVENTS (Immutable audit trail)
# ============================================================================

class LoanEvent(Base):
    """Immutable event log for every change to a loan"""
    __tablename__ = "loan_events"

    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"), nullable=False, index=True)

    # EVENT DETAILS
    event_type = Column(String(50),
                        nullable=False)  # "payment_posted", "delinq_status_changed", "hardship_approved", etc.
    event_date = Column(DateTime(timezone=True), nullable=False, index=True)
    description = Column(String(500))  # Human-readable description

    # EVENT DATA (flexible JSON)
    event_data = Column(
        JSON)  # {"payment_amount": 500, "method": "ACH", "status_changed_from": "current", "status_changed_to": "delinq_30"}

    # SOURCE
    source = Column(String(50))  # "user_submitted", "api_sync", "servicer_notification", "system"
    source_details = Column(String(255))  # Additional source info

    # METADATA
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # RELATIONSHIPS
    debt = relationship("Debt", back_populates="loan_events")

    def __repr__(self):
        return f"<LoanEvent(id={self.id}, type={self.event_type}, date={self.event_date})>"


# ============================================================================
# COST-BENEFIT ANALYSIS RESULTS
# ============================================================================

class CostBenefitAnalysis(Base):
    """Results from cost-benefit analyzer engine"""
    __tablename__ = "cost_benefit_analyses"

    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # OPTIONS COMPARED
    options_compared = Column(JSON, default=list)  # Array of option IDs compared

    # RESULTS (ranked options)
    ranked_options = Column(JSON, default=list)  # [{rank: 1, option_id: 123, total_cost: 5000, months: 24, ...}, ...]
    recommended_option_id = Column(Integer)  # Which option we recommend

    # ASSUMPTIONS USED
    assumptions = Column(JSON)  # {"user_income": 4000, "market_apr": 7.5, "inflation": 0.03, ...}

    # METADATA
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # RELATIONSHIPS
    debt = relationship("Debt", back_populates="cost_benefit_analyses")
    user = relationship("User", back_populates="cost_benefit_analyses")

    def __repr__(self):
        return f"<CostBenefitAnalysis(id={self.id}, debt_id={self.debt_id}, recommended_option={self.recommended_option_id})>"


# ============================================================================
# STATE OVERLAY - State-specific rules (collections law, SOL, etc.)
# ============================================================================

class StateOverlay(Base):
    """State-specific collections and hardship rules"""
    __tablename__ = "state_overlays"

    id = Column(Integer, primary_key=True, index=True)
    state_code = Column(String(2), nullable=False, unique=True, index=True)  # "UT", "CA", "NY", etc.

    # COLLECTIONS LAW
    statute_of_limitations_credit_card = Column(Integer)  # Years (e.g., 6 years in Utah)
    statute_of_limitations_personal_loan = Column(Integer)
    statute_of_limitations_student_loan = Column(Integer, default=999)  # No SOL for student loans
    statute_of_limitations_mortgage = Column(Integer)

    # WAGE GARNISHMENT
    wage_garnishment_allowed = Column(Boolean, default=True)
    wage_garnishment_max_percent = Column(Numeric(5, 2))  # 25% is federal limit
    wage_garnishment_exemptions = Column(String(500))  # Special exemptions by state

    # COLLECTOR LICENSING
    collector_licensing_required = Column(Boolean, default=False)
    collector_licensing_agency = Column(String(255))
    collector_licensing_url = Column(String(500))

    # DISCLOSURE REQUIREMENTS
    mandatory_disclosures = Column(JSON)  # State-specific disclosures

    # FORECLOSURE TIMELINES (for mortgages)
    foreclosure_process_type = Column(String(50))  # "judicial", "non-judicial", "hybrid"
    foreclosure_timeline_months = Column(Integer)  # How many months typical

    # HARDSHIP PROGRAM AVAILABILITY
    hardship_programs_available = Column(JSON, default=list)  # ["forbearance", "settlement", ...]

    # METADATA
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<StateOverlay(state_code={self.state_code})>"


# ============================================================================
# BALANCE TRANSFER / GOALS / TRANSACTIONS
# ============================================================================

class BalanceTransfer(Base):
    __tablename__ = "balance_transfers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    card_name = Column(String, nullable=False)
    intro_apr = Column(Float, default=0.0)
    regular_apr = Column(Float, nullable=False)
    promo_months = Column(Integer, nullable=False)
    balance_transfer_fee = Column(Float, default=0.03)
    credit_limit = Column(Float, nullable=False)
    transfer_amount = Column(Float, nullable=True)
    estimated_monthly_payment = Column(Float, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    target_amount = Column(Float, nullable=False)
    current_savings = Column(Float, default=0.0)
    target_date = Column(DateTime, nullable=False)
    priority = Column(Integer, default=1)
    annual_return_rate = Column(Float, default=0.02)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    merchant = Column(String, nullable=True)
    category = Column(String, default="other")
    confidence = Column(Float, default=0.8)
    is_recurring = Column(Boolean, default=False)
    recurring_pattern = Column(String, nullable=True)
    source_type = Column(String, default="csv")
    source_file = Column(String, nullable=True)
    account_type = Column(String, nullable=True)
    account_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Non-table helper type: goal_service imports `Scenario` from this module as a
# return annotation for what-if scenario dicts. The concrete shape lives in
# app.schemas.goal.Scenario; this placeholder keeps the import resolvable.
class Scenario:
    pass