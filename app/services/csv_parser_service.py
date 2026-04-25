import csv
import re
from datetime import datetime, date
from typing import List, Dict, Tuple
from io import StringIO
import PyPDF2
import pandas as pd
from app.schemas.spending import SpendingCategory
from app.schemas.transaction import TransactionCreate


class CSVParserService:
    """Service for parsing CSV/PDF files and categorizing transactions"""

    # Keywords for auto-categorization
    CATEGORY_KEYWORDS = {
        SpendingCategory.HOUSING: [
            "rent", "mortgage", "landlord", "apartment", "lease", "realtor"
        ],
        SpendingCategory.UTILITIES: [
            "electric", "gas", "water", "internet", "comcast", "verizon", "at&t",
            "power", "utility", "cable", "phone bill", "wifi"
        ],
        SpendingCategory.TRANSPORTATION: [
            "uber", "lyft", "taxi", "gas station", "shell", "chevron", "exxon",
            "parking", "transit", "bus", "train", "car payment", "insurance",
            "maintenance", "oil change", "car wash", "honda", "toyota", "ford"
        ],
        SpendingCategory.GROCERIES: [
            "whole foods", "safeway", "kroger", "trader joe's", "costco",
            "walmart", "target", "grocery", "market", "supermarket", "food",
            "publix", "albertsons"
        ],
        SpendingCategory.DINING: [
            "restaurant", "cafe", "coffee", "starbucks", "chipotle", "doordash",
            "uber eats", "grubhub", "postmates", "pizza", "burger", "sushi",
            "bar", "tavern", "brewery", "dining", "food delivery"
        ],
        SpendingCategory.ENTERTAINMENT: [
            "netflix", "spotify", "hulu", "disney", "movie", "cinema", "theater",
            "concert", "ticketmaster", "games", "steam", "playstation", "xbox",
            "gaming", "amusement", "park", "entertainment"
        ],
        SpendingCategory.SHOPPING: [
            "amazon", "ebay", "mall", "store", "shop", "clothing", "apparel",
            "nike", "adidas", "h&m", "zara", "target", "kohls", "bestbuy",
            "electronics", "department store"
        ],
        SpendingCategory.SUBSCRIPTIONS: [
            "subscription", "membership", "aws", "github", "adobe", "microsoft",
            "apple", "google play", "patreon", "linkedin", "monthly"
        ],
        SpendingCategory.HEALTHCARE: [
            "pharmacy", "cvs", "walgreens", "doctor", "hospital", "medical",
            "clinic", "lab", "urgent care", "health", "dental", "dentist"
        ],
        SpendingCategory.PERSONAL_CARE: [
            "salon", "haircut", "barber", "spa", "massage", "gym", "fitness",
            "trainer", "yoga", "beauty"
        ],
        SpendingCategory.SHOPPING: [
            "amazon", "ebay", "retail", "store"
        ]
    }

    @staticmethod
    def parse_csv_file(file_content: str, source_filename: str = "import.csv") -> Tuple[
        List[TransactionCreate], List[str]]:
        """
        Parse CSV file content and return list of transactions
        """
        transactions = []
        errors = []

        try:
            lines = file_content.strip().split('\n')

            if not lines or len(lines) < 2:
                return [], ["File is empty or too short"]

            # Parse header
            header = [h.strip() for h in lines[0].split(',')]

            print(f"DEBUG CSV Header: {header}")

            # Parse data rows
            for row_num, line in enumerate(lines[1:], start=2):
                try:
                    values = [v.strip() for v in line.split(',')]

                    if not values or all(v == '' for v in values):
                        continue

                    # Create row dict
                    row = {}
                    for i, header_name in enumerate(header):
                        if i < len(values):
                            row[header_name] = values[i]
                        else:
                            row[header_name] = None

                    print(f"DEBUG Row {row_num}: {row}")

                    transaction = CSVParserService._parse_csv_row(row, source_filename)
                    if transaction:
                        print(f"DEBUG Transaction created: {transaction}")
                        transactions.append(transaction)
                except Exception as e:
                    print(f"DEBUG Error on row {row_num}: {str(e)}")
                    errors.append(f"Row {row_num}: {str(e)}")

            return transactions, errors

        except Exception as e:
            print(f"DEBUG CSV parsing error: {str(e)}")
            return [], [f"CSV parsing error: {str(e)}"]

    @staticmethod
    def _parse_csv_row(row: Dict, source_filename: str) -> TransactionCreate:
        """Parse individual CSV row"""

        # Normalize keys
        normalized_row = {k.strip().lower(): v for k, v in row.items()}

        # Find date column
        date_value = None
        date_keys = ["date", "transaction date", "posted date", "post date", "trans date"]
        for key in date_keys:
            if key in normalized_row and normalized_row[key]:
                try:
                    date_value = CSVParserService._parse_date(str(normalized_row[key]))
                    break
                except:
                    continue

        if not date_value:
            raise ValueError("Could not find valid date")

        # Find description/merchant
        description = None
        merchant = None
        desc_keys = ["description", "merchant", "details", "transaction", "description/merchant"]
        for key in desc_keys:
            if key in normalized_row and normalized_row[key]:
                description = str(normalized_row[key])
                merchant = CSVParserService._extract_merchant(description)
                break

        if not description:
            raise ValueError("No description found")

        # Find amount
        amount = None

        # Try simple "amount" column first
        if "amount" in normalized_row and normalized_row["amount"]:
            try:
                amount = float(str(normalized_row["amount"]).replace('$', '').replace(',', '').strip())
            except:
                pass

        # If no amount found, try debit/credit columns
        if amount is None:
            for key in normalized_row:
                val = normalized_row[key]
                if not val:
                    continue

                try:
                    num_val = float(str(val).replace('$', '').replace(',', '').strip())

                    if num_val > 0:  # Only positive amounts
                        if 'debit' in key or 'withdrawal' in key or 'out' in key:
                            amount = abs(num_val)
                            break
                        elif 'credit' in key or 'deposit' in key or 'in' in key:
                            # Skip credits (income)
                            return None
                        elif 'amount' in key:
                            amount = abs(num_val)
                            break
                except:
                    continue

        if amount is None or amount == 0:
            raise ValueError(f"Could not find valid amount in row")

        # Auto-categorize
        category = CSVParserService.auto_categorize(description)

        return TransactionCreate(
            date=date_value,
            description=description.strip(),
            amount=round(amount, 2),
            merchant=merchant,
            category=category,
            source_type="csv",
            source_file=source_filename
        )

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """Parse date from various formats"""

        formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y-%m-%d",
            "%m/%d/%y",
            "%m-%d-%y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d/%m/%Y",
            "%d-%m-%Y"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except:
                continue

        raise ValueError(f"Could not parse date: {date_str}")

    @staticmethod
    def _extract_merchant(description: str) -> str:
        """Extract merchant name from description"""
        # Remove common prefixes
        cleaned = re.sub(r'^(DEBIT|CREDIT|CHECK|ACH|TRANSFER|PAYMENT|PURCHASE)[\s-]*', '', description,
                         flags=re.IGNORECASE)
        # Take first part (before numbers)
        merchant = re.split(r'\d{4}', cleaned)[0].strip()
        return merchant[:50]  # Limit to 50 chars

    @staticmethod
    def auto_categorize(description: str) -> str:
        """Auto-categorize transaction based on keywords"""

        description_lower = description.lower()
        scores = {}

        for category, keywords in CSVParserService.CATEGORY_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in description_lower:
                    score += 1
            if score > 0:
                scores[category] = score

        if scores:
            # Return category with highest score
            return max(scores, key=scores.get).value

        return SpendingCategory.OTHER.value

    @staticmethod
    def detect_recurring_transactions(transactions: List[Dict]) -> List[Dict]:
        """
        Detect recurring transactions
        Look for same merchant within similar amounts on regular intervals
        """

        recurring = []
        merchant_groups = {}

        # Group by merchant
        for trans in transactions:
            merchant = trans.get("merchant", trans.get("description", ""))
            if merchant not in merchant_groups:
                merchant_groups[merchant] = []
            merchant_groups[merchant].append(trans)

        # Detect patterns
        for merchant, trans_list in merchant_groups.items():
            if len(trans_list) < 2:
                continue

            # Sort by date
            trans_list_sorted = sorted(trans_list, key=lambda x: x.get("date", ""))

            # Check if same amount and regular intervals
            amounts = [t.get("amount") for t in trans_list_sorted]
            dates = [t.get("date") for t in trans_list_sorted]

            # If all amounts similar (within 5%)
            if amounts and all(abs(a - amounts[0]) / amounts[0] < 0.05 for a in amounts):
                if len(amounts) >= 2:
                    pattern = CSVParserService._detect_pattern(dates)
                    if pattern:
                        recurring.append({
                            "merchant": merchant,
                            "description": trans_list_sorted[0].get("description"),
                            "amount": amounts[0],
                            "pattern": pattern,
                            "occurrences": len(amounts),
                            "confidence": min(len(amounts) / 3, 1.0)  # More occurrences = more confident
                        })

        return recurring

    @staticmethod
    def _detect_pattern(dates: List[date]) -> str:
        """Detect interval pattern"""

        if len(dates) < 2:
            return None

        intervals = []
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i - 1]).days
            intervals.append(delta)

        # Check if consistent
        if not intervals:
            return None

        avg_interval = sum(intervals) / len(intervals)

        if 28 <= avg_interval <= 32:
            return "monthly"
        elif 6 <= avg_interval <= 8:
            return "weekly"
        elif 13 <= avg_interval <= 15:
            return "bi-weekly"
        elif 88 <= avg_interval <= 95:
            return "quarterly"
        elif 360 <= avg_interval <= 365:
            return "yearly"

        return None

    @staticmethod
    def parse_pdf_file(file_content: bytes, source_filename: str = "statement.pdf") -> Tuple[
        List[TransactionCreate], List[str]]:
        """
        Parse PDF bank statement
        Attempts to extract text and find transaction patterns
        """

        errors = []
        transactions = []

        try:
            # Extract text from PDF
            pdf_text = ""
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))

            for page in pdf_reader.pages:
                pdf_text += page.extract_text()

            # Try to find transaction patterns in text
            # Look for date-amount-description patterns
            lines = pdf_text.split('\n')

            for line in lines:
                try:
                    # Simple pattern: find lines with dates and amounts
                    if any(date_format in line for date_format in ['/', '-']):
                        trans = CSVParserService._parse_pdf_line(line, source_filename)
                        if trans:
                            transactions.append(trans)
                except:
                    continue

            if not transactions:
                errors.append("No transactions found in PDF. Please use a CSV file from your bank.")

            return transactions, errors

        except Exception as e:
            return [], [f"PDF parsing error: {str(e)}. Please export as CSV instead."]

    @staticmethod
    def _parse_pdf_line(line: str, source_filename: str) -> TransactionCreate:
        """Attempt to parse transaction line from PDF text"""

        # This is simplified - PDF formats vary widely
        # Better approach: ask users to export as CSV

        return None
