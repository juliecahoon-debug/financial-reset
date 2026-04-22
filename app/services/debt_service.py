from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.debt import Debt, DebtStatus
from app.schemas.debt import DebtCreate, DebtUpdate
from typing import Optional, List
from datetime import datetime


class DebtService:
    """Business logic for debt operations"""

    @staticmethod
    def create_debt(db: Session, user_id: int, debt: DebtCreate) -> Debt:
        """Create new debt"""
        db_debt = Debt(
            user_id=user_id,
            name=debt.name,
            debt_type=debt.debt_type,
            balance=debt.balance,
            original_balance=debt.original_balance,
            minimum_payment=debt.minimum_payment,
            interest_rate=debt.interest_rate,
            opened_date=debt.opened_date,
            due_date=debt.due_date,
            creditor=debt.creditor,
            account_number=debt.account_number,
            notes=debt.notes
        )
        db.add(db_debt)
        db.commit()
        db.refresh(db_debt)
        return db_debt

    @staticmethod
    def get_debt_by_id(db: Session, debt_id: int) -> Optional[Debt]:
        """Get debt by ID"""
        return db.query(Debt).filter(Debt.id == debt_id).first()

    @staticmethod
    def get_user_debts(db: Session, user_id: int) -> List[Debt]:
        """Get all debts for a user"""
        return db.query(Debt).filter(Debt.user_id == user_id).all()

    @staticmethod
    def get_active_debts(db: Session, user_id: int) -> List[Debt]:
        """Get active debts for a user"""
        return db.query(Debt).filter(
            Debt.user_id == user_id,
            Debt.status == DebtStatus.ACTIVE
        ).all()

    @staticmethod
    def update_debt(db: Session, debt_id: int, debt_update: DebtUpdate) -> Optional[Debt]:
        """Update debt"""
        db_debt = DebtService.get_debt_by_id(db, debt_id)

        if not db_debt:
            return None

        update_data = debt_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_debt, field, value)

        db.commit()
        db.refresh(db_debt)
        return db_debt

    @staticmethod
    def delete_debt(db: Session, debt_id: int) -> bool:
        """Delete debt"""
        db_debt = DebtService.get_debt_by_id(db, debt_id)

        if not db_debt:
            return False

        db.delete(db_debt)
        db.commit()
        return True

    @staticmethod
    def get_total_debt(debts: List[Debt]) -> float:
        """Calculate total debt balance"""
        return sum(debt.balance for debt in debts)

    @staticmethod
    def get_total_monthly_payment(debts: List[Debt]) -> float:
        """Calculate total minimum monthly payment"""
        return sum(debt.minimum_payment or 0 for debt in debts)

    @staticmethod
    def get_weighted_apr(debts: List[Debt]) -> float:
        """Calculate weighted average APR across all debts"""
        if not debts:
            return 0

        total_balance = DebtService.get_total_debt(debts)
        if total_balance == 0:
            return 0

        weighted_apr = sum(debt.balance * debt.interest_rate for debt in debts) / total_balance
        return round(weighted_apr, 2)
