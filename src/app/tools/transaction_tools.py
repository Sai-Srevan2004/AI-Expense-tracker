
from langchain_core.tools import tool

from app.schemas.intent import TransactionItem
from app.tools.transaction_store import (
    add_transactions,
    get_balance,
    list_transactions,
)


def validate_batch(transactions: list[dict]) -> list[TransactionItem]:
    """Validate every item before saving any transaction."""

    if not transactions:
        raise ValueError("At least one transaction is required.")

    items = [
        TransactionItem.model_validate(item)
        for item in transactions
    ]

    if any(item.amount is None for item in items):
        raise ValueError("Every transaction must have an amount.")

    return items


@tool
def record_expenses(transactions: list[dict]) -> dict:
    """Record one or more personal expenses."""

    items = validate_batch(transactions)
    created = add_transactions(items, "expense")

    return {
        "success": True,
        "count": len(created),
        "transactions": created,
    }


@tool
def record_income(transactions: list[dict]) -> dict:
    """Record one or more personal income transactions."""

    items = validate_batch(transactions)
    created = add_transactions(items, "income")

    return {
        "success": True,
        "count": len(created),
        "transactions": created,
    }


@tool
def get_transactions(transaction_type: str = "all") -> dict:
    """List stored transactions by type: all, expense, or income."""

    if transaction_type not in {"all", "expense", "income"}:
        return {
            "success": False,
            "error": "Transaction type must be all, expense, or income.",
        }

    selected_type = (
        None if transaction_type == "all" else transaction_type
    )

    transactions = list_transactions(selected_type)

    return {
        "success": True,
        "count": len(transactions),
        "transactions": transactions,
    }


@tool
def calculate_balance() -> dict:
    """Calculate total recorded income minus total recorded expenses."""

    return {
        "success": True,
        "balance": get_balance(),
    }
