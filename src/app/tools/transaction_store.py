
from datetime import date
from uuid import uuid4

from app.schemas.intent import TransactionItem


_transactions: list[dict] = []


def add_transactions(
    items: list[TransactionItem],
    transaction_type: str,
) -> list[dict]:
    """Store multiple validated transactions in memory."""

    if transaction_type not in {"expense", "income"}:
        raise ValueError("Invalid transaction type.")

    created = []

    for item in items:
        if item.amount is None:
            raise ValueError("Every transaction needs an amount.")

        transaction = {
            "id": str(uuid4()),
            "type": transaction_type,
            "amount": item.amount,
            "category": item.category or "Other",
            "description": item.description or "",
            "date": item.transaction_date or date.today().isoformat(),
        }

        _transactions.append(transaction)
        created.append(transaction.copy())

    return created


def list_transactions(
    transaction_type: str | None = None,
) -> list[dict]:
    """Return stored transactions, optionally filtered by type."""

    if transaction_type not in {None, "expense", "income"}:
        raise ValueError("Invalid transaction type.")

    return [
        transaction.copy()
        for transaction in _transactions
        if transaction_type is None
        or transaction["type"] == transaction_type
    ]


def get_balance() -> float:
    """Calculate income minus expenses using Python."""

    income = sum(
        transaction["amount"]
        for transaction in _transactions
        if transaction["type"] == "income"
    )

    expenses = sum(
        transaction["amount"]
        for transaction in _transactions
        if transaction["type"] == "expense"
    )

    return income - expenses
