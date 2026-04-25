from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.debt import Transaction
from app.schemas.transaction import (
    TransactionCreate, TransactionUpdate, TransactionResponse,
    TransactionSummary, RecurringTransaction, CSVUploadResponse
)
from app.schemas.spending import SpendingCategory
from app.services.csv_parser_service import CSVParserService
from app.services.spending_service import SpendingService


class TransactionService:
    """Business logic for transaction management"""

    @staticmethod
    def create_transaction(db: Session, user_id: int, transaction: TransactionCreate) -> Transaction:
        """Create new transaction"""

        db_transaction = Transaction(
            user_id=user_id,
            date=transaction.date,
            description=transaction.description,
            amount=transaction.amount,
            merchant=transaction.merchant,
            category=transaction.category or "other",
            source_type=transaction.source_type,
            source_file=transaction.source_file,
            account_type=transaction.account_type,
            account_number=transaction.account_number
        )

        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        return db_transaction

    @staticmethod
    def create_transactions_batch(db: Session, user_id: int, transactions: List[TransactionCreate]) -> int:
        """Create multiple transactions efficiently"""

        count = 0
        for trans in transactions:
            try:
                TransactionService.create_transaction(db, user_id, trans)
                count += 1
            except:
                continue

        return count

    @staticmethod
    def get_user_transactions(
            db: Session,
            user_id: int,
            days: int = 90,
            category: Optional[str] = None
    ) -> List[Transaction]:
        """Get user's transactions (last N days)"""

        start_date = datetime.utcnow().date() - timedelta(days=days)

        query = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date
        )

        if category:
            query = query.filter(Transaction.category == category)

        return query.order_by(Transaction.date.desc()).all()

    @staticmethod
    def get_transaction_by_id(db: Session, transaction_id: int) -> Optional[Transaction]:
        """Get transaction by ID"""
        return db.query(Transaction).filter(Transaction.id == transaction_id).first()

    @staticmethod
    def update_transaction(db: Session, transaction_id: int, update_data: TransactionUpdate) -> Optional[Transaction]:
        """Update transaction (e.g., fix category)"""

        transaction = TransactionService.get_transaction_by_id(db, transaction_id)

        if not transaction:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(transaction, key, value)

        db.commit()
        db.refresh(transaction)
        return transaction

    @staticmethod
    def delete_transaction(db: Session, transaction_id: int) -> bool:
        """Delete transaction"""

        transaction = TransactionService.get_transaction_by_id(db, transaction_id)

        if not transaction:
            return False

        db.delete(transaction)
        db.commit()
        return True

    @staticmethod
    def import_csv(db: Session, user_id: int, csv_content: str, filename: str = "import.csv") -> CSVUploadResponse:
        """Import transactions from CSV"""

        # Parse CSV
        transactions, errors = CSVParserService.parse_csv_file(csv_content, filename)

        if not transactions:
            return CSVUploadResponse(
                file_name=filename,
                total_transactions=0,
                transactions_imported=0,
                transactions_with_errors=len(errors),
                categories_detected=[],
                recurring_detected=0,
                message=f"Failed to import: {errors[0] if errors else 'Unknown error'}"
            )

        # Create transactions
        imported_count = TransactionService.create_transactions_batch(db, user_id, transactions)

        # Detect recurring
        trans_dicts = [t.model_dump() for t in transactions]
        recurring = CSVParserService.detect_recurring_transactions(trans_dicts)

        # Get categories
        categories = list(set(t.category for t in transactions if t.category))

        return CSVUploadResponse(
            file_name=filename,
            total_transactions=len(transactions),
            transactions_imported=imported_count,
            transactions_with_errors=len(errors),
            categories_detected=categories,
            recurring_detected=len(recurring),
            message=f"Successfully imported {imported_count}/{len(transactions)} transactions"
        )

    @staticmethod
    def get_category_summary(db: Session, user_id: int, days: int = 30) -> List[TransactionSummary]:
        """Get spending by category with percentages"""

        transactions = TransactionService.get_user_transactions(db, user_id, days)

        category_totals = {}
        total_spending = sum(t.amount for t in transactions)

        for trans in transactions:
            if trans.category not in category_totals:
                category_totals[trans.category] = {
                    "count": 0,
                    "total": 0,
                    "amounts": []
                }

            category_totals[trans.category]["count"] += 1
            category_totals[trans.category]["total"] += trans.amount
            category_totals[trans.category]["amounts"].append(trans.amount)

        summary = []
        for category, data in category_totals.items():
            percentage_of_total = (data["total"] / total_spending * 100) if total_spending > 0 else 0
            average = data["total"] / data["count"] if data["count"] > 0 else 0

            summary.append(TransactionSummary(
                category=category,
                count=data["count"],
                total_amount=round(data["total"], 2),
                average_amount=round(average, 2),
                percentage_of_total_spending=round(percentage_of_total, 1)
            ))

        return sorted(summary, key=lambda x: x.total_amount, reverse=True)

    @staticmethod
    def get_recurring_transactions(db: Session, user_id: int) -> List[RecurringTransaction]:
        """Get detected recurring transactions"""

        # Get last 90 days of transactions
        transactions = TransactionService.get_user_transactions(db, user_id, days=90)

        # Convert to dicts for analysis
        trans_dicts = [
            {
                "date": t.date,
                "description": t.description,
                "merchant": t.merchant,
                "amount": t.amount,
                "category": t.category
            }
            for t in transactions
        ]

        # Detect patterns
        recurring_data = CSVParserService.detect_recurring_transactions(trans_dicts)

        result = []
        for rec in recurring_data:
            monthly_cost = rec["amount"]
            annual_cost = rec["amount"] * 12

            # Get cancellation tip
            tip = TransactionService._get_cancellation_tip(rec.get("merchant", ""))

            result.append(RecurringTransaction(
                description=rec.get("description", ""),
                merchant=rec.get("merchant"),
                amount=round(rec.get("amount", 0), 2),
                pattern=rec.get("pattern", "unknown"),
                confidence=round(rec.get("confidence", 0), 2),
                occurrences=rec.get("occurrences", 0),
                monthly_cost=round(monthly_cost, 2),
                annual_cost=round(annual_cost, 2),
                cancellation_tip=tip
            ))

        return sorted(result, key=lambda x: x.monthly_cost, reverse=True)

    @staticmethod
    def _get_cancellation_tip(merchant: str) -> str:
        """Get cancellation tip for known services"""

        tips = {
            "netflix": "Go to Settings → Cancel Membership. You can reactivate anytime.",
            "spotify": "Go to Account → Cancel Premium.",
            "gym": "Visit your gym's member services desk or call.",
            "amazon": "Go to Your Memberships & Subscriptions.",
            "apple": "Go to Settings → [Your Name] → Subscriptions.",
            "hulu": "Go to Account → Manage Subscription → Cancel.",
            "disney": "Go to Account → Subscription.",
        }

        for service, tip in tips.items():
            if service.lower() in merchant.lower():
                return tip

        return "Contact the company or visit their website to cancel."

    @staticmethod
    def get_actual_spending_analysis(db: Session, user_id: int, monthly_income: float, days: int = 30) -> dict:
        """Analyze actual spending vs budget"""

        transactions = TransactionService.get_user_transactions(db, user_id, days)
        category_summary = TransactionService.get_category_summary(db, user_id, days)
        recurring = TransactionService.get_recurring_transactions(db, user_id)

        # Get budget recommendation
        budget = SpendingService.get_budget_recommendation(monthly_income)

        total_spending = sum(t.amount for t in transactions)

        # Build comparison
        comparison = {}
        for summary in category_summary:
            budget_cat = next(
                (c for c in budget.categories if c.category.value == summary.category),
                None
            )

            budgeted = budget_cat.recommended_amount if budget_cat else 0
            difference = summary.total_amount - budgeted

            comparison[summary.category] = {
                "actual": round(summary.total_amount, 2),
                "budgeted": round(budgeted, 2),
                "difference": round(difference, 2),
                "status": "over" if difference > 0 else "under",
                "count": summary.count
            }

        return {
            "period_days": days,
            "total_transactions": len(transactions),
            "total_spending": round(total_spending, 2),
            "average_transaction": round(total_spending / len(transactions), 2) if transactions else 0,
            "monthly_income": monthly_income,
            "spending_percentage": round(total_spending / monthly_income * 100, 1) if monthly_income > 0 else 0,
            "category_summary": [
                {
                    "category": s.category,
                    "total": s.total_amount,
                    "count": s.count,
                    "percentage": s.percentage_of_total
                }
                for s in category_summary
            ],
            "recurring_transactions": [
                {
                    "description": r.description,
                    "merchant": r.merchant,
                    "monthly_cost": r.monthly_cost,
                    "annual_cost": r.annual_cost,
                    "pattern": r.pattern,
                    "occurrences": r.occurrences
                }
                for r in recurring
            ],
            "budget_comparison": comparison,
            "recommendation": f"You spent ${total_spending:.2f} in {days} days. At this rate, you'll spend ${(total_spending / days * 30):.2f}/month."
        }
