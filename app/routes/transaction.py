from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.transaction_service import TransactionService
from app.services.spending_service import SpendingService
from app.schemas.transaction import (
    TransactionResponse, TransactionUpdate, CSVUploadResponse,
    TransactionSummary, RecurringTransaction
)


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/upload-csv", response_model=CSVUploadResponse)
async def upload_csv(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Upload CSV file with bank transactions"""

    try:
        # Read file content
        contents = await file.read()
        csv_content = contents.decode('utf-8')

        # Import transactions
        result = TransactionService.import_csv(db, current_user.id, csv_content, file.filename)

        return result

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a valid CSV file."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get("/list", response_model=list[TransactionResponse])
async def get_transactions(
        days: int = Query(90, ge=1, le=730, description="Number of days to retrieve"),
        category: str = Query(None, description="Filter by category"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get user's transactions"""

    transactions = TransactionService.get_user_transactions(db, current_user.id, days, category)
    return transactions


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
        transaction_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get specific transaction"""

    transaction = TransactionService.get_transaction_by_id(db, transaction_id)

    if not transaction or transaction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    return transaction


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
        transaction_id: int,
        update_data: TransactionUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update transaction (e.g., fix category)"""

    transaction = TransactionService.get_transaction_by_id(db, transaction_id)

    if not transaction or transaction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    updated = TransactionService.update_transaction(db, transaction_id, update_data)
    return updated


@router.delete("/{transaction_id}")
async def delete_transaction(
        transaction_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete transaction"""

    transaction = TransactionService.get_transaction_by_id(db, transaction_id)

    if not transaction or transaction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    success = TransactionService.delete_transaction(db, transaction_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not delete transaction"
        )

    return {"message": "Transaction deleted"}


@router.get("/summary/by-category", response_model=list[dict])
async def get_category_summary(
        days: int = Query(30, ge=1, le=730),
        monthly_income: float = Query(None, gt=0, description="Monthly income (optional, for budget comparison)"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get spending breakdown by category with percentages of total spending and budget"""

    summary = TransactionService.get_category_summary(db, current_user.id, days)

    # Get budget if income provided
    budget = None
    if monthly_income:
        budget = SpendingService.get_budget_recommendation(monthly_income)

    # Build response with both percentages
    result = []
    for item in summary:
        percentage_of_budget = None

        if budget:
            budgeted = next(
                (c.recommended_amount for c in budget.categories if c.category.value == item.category),
                None
            )
            if budgeted:
                percentage_of_budget = round(item.total_amount / budgeted * 100, 1)

        result.append({
            "category": item.category,
            "count": item.count,
            "total_amount": item.total_amount,
            "average_amount": item.average_amount,
            "percentage_of_total_spending": item.percentage_of_total_spending,
            "percentage_of_budget": percentage_of_budget,
            "status": "over" if percentage_of_budget and percentage_of_budget > 100 else "under" if percentage_of_budget else None
        })

    return result


@router.get("/recurring/detect", response_model=list[RecurringTransaction])
async def detect_recurring(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Detect recurring transactions"""

    recurring = TransactionService.get_recurring_transactions(db, current_user.id)
    return recurring


@router.get("/analysis/actual-vs-budget", response_model=dict)
async def analyze_actual_spending(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        days: int = Query(30, ge=1, le=730, description="Period to analyze"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get actual spending analysis vs budget"""

    analysis = TransactionService.get_actual_spending_analysis(db, current_user.id, monthly_income, days)
    return analysis
