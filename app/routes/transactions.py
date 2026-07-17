from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.debt import Transaction
from app.services.csv_parser_service import CSVParserService
from app.schemas.transaction import TransactionResponse, TransactionUpdate
from datetime import datetime

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.post("/upload/csv")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    content = await file.read()
    transactions, errors = CSVParserService.parse_csv_file(
        content.decode("utf-8", errors="replace"),
        file.filename
    )
    saved = []
    for t in transactions:
        db_t = Transaction(
            user_id=current_user.id,
            date=datetime.combine(t.date, datetime.min.time()),
            description=t.description,
            amount=t.amount,
            merchant=t.merchant,
            category=t.category or "other",
            confidence=0.8,
            is_recurring=False,
            source_type="csv",
            source_file=file.filename,
        )
        db.add(db_t)
        saved.append(db_t)
    db.commit()
    recurring = CSVParserService.detect_recurring_transactions(
        [{"description": t.description, "amount": t.amount, "date": t.date} for t in transactions]
    )
    return {
        "imported": len(saved),
        "errors": errors,
        "recurring_detected": len(recurring),
        "recurring": recurring[:10],
    }

@router.post("/upload/pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    content = await file.read()
    transactions, errors = CSVParserService.parse_pdf_file(content, file.filename)
    saved = []
    for t in transactions:
        db_t = Transaction(
            user_id=current_user.id,
            date=datetime.combine(t.date, datetime.min.time()),
            description=t.description,
            amount=t.amount,
            merchant=t.merchant,
            category=t.category or "other",
            confidence=0.7,
            is_recurring=False,
            source_type="pdf",
            source_file=file.filename,
        )
        db.add(db_t)
        saved.append(db_t)
    db.commit()
    return {"imported": len(saved), "errors": errors}

@router.get("/")
def get_transactions(
    limit: int = 50,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    if category:
        query = query.filter(Transaction.category == category)
    return query.order_by(Transaction.date.desc()).limit(limit).all()

@router.get("/summary")
def get_transaction_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    txns = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    by_category = {}
    for t in txns:
        cat = t.category or "other"
        if cat not in by_category:
            by_category[cat] = {"count": 0, "total": 0.0}
        by_category[cat]["count"] += 1
        by_category[cat]["total"] += t.amount
    total_spending = sum(t.amount for t in txns if t.amount > 0)
    total_income = abs(sum(t.amount for t in txns if t.amount < 0))
    return {
        "total_transactions": len(txns),
        "total_spending": round(total_spending, 2),
        "total_income": round(total_income, 2),
        "by_category": by_category,
    }

@router.patch("/{transaction_id}")
def update_transaction(
    transaction_id: int,
    update: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    t = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(t, field, value)
    db.commit()
    return t
