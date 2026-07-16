from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from app.models.user import User
from app.dependencies import get_current_user
from app.services.csv_parser_service import CSVParserService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/import")
async def import_transactions(
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user)
):
    """Import and auto-categorize transactions from a CSV file."""
    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        content = raw.decode("latin-1")

    transactions, errors = CSVParserService.parse_csv_file(content, file.filename or "import.csv")

    parsed = [t.model_dump(mode="json") for t in transactions]
    recurring = CSVParserService.detect_recurring_transactions(parsed)
    categories = sorted({t.get("category") for t in parsed if t.get("category")})

    return {
        "file_name": file.filename,
        "total_transactions": len(transactions) + len(errors),
        "transactions_imported": len(transactions),
        "transactions_with_errors": len(errors),
        "categories_detected": categories,
        "recurring_detected": len(recurring),
        "transactions": parsed,
        "recurring_transactions": recurring,
        "errors": errors,
        "message": f"Imported {len(transactions)} transactions from {file.filename}",
    }


@router.get("/categorize")
async def categorize_transaction(
        description: str = Query(..., min_length=1),
        current_user: User = Depends(get_current_user)
):
    """Auto-categorize a transaction description."""
    return {
        "description": description,
        "category": CSVParserService.auto_categorize(description),
    }
