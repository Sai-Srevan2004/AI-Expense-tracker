
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, func, select

from app.database import SessionLocal
from app.models.transaction import Transaction
from app.schemas.intent import TransactionItem


def parse_transaction_date(value: str | None) -> date:
    """Convert a supported date string into a Python date."""

    if not value:
        return date.today()

    normalized = value.strip().lower()

    relative_dates = {
        "today": date.today(),
        "yesterday": date.today() - timedelta(days=1),
        "tomorrow": date.today() + timedelta(days=1),
    }

    if normalized in relative_dates:
        return relative_dates[normalized]

    try:
        return date.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(
            "Unsupported date. Use YYYY-MM-DD, today, yesterday, "
            "or tomorrow."
        ) from error


def transaction_to_dict(transaction: Transaction) -> dict:
    """Convert a database transaction into a dictionary."""

    return {
        "id": transaction.id,
        "type": transaction.type,
        "amount": float(transaction.amount),
        "category": transaction.category,
        "description": transaction.description,
        "date": transaction.transaction_date.isoformat(),
    }


def add_transactions(
    items: list[TransactionItem],
    transaction_type: str,
) -> list[dict]:
    """Save multiple transactions to MySQL."""

    if transaction_type not in {"expense", "income"}:
        raise ValueError("Invalid transaction type.")

    if not items:
        raise ValueError("At least one transaction is required.")

    new_transactions = []

    # Validate and prepare the complete batch before saving.
    for item in items:
        if item.amount is None or item.amount <= 0:
            raise ValueError(
                "Every transaction needs a positive amount."
            )

        if not item.category:
            raise ValueError(
                "Every transaction needs a category."
            )

        if not item.description or not item.description.strip():
            raise ValueError(
                "Every transaction needs a description."
            )

        transaction = Transaction(
            id=str(uuid4()),
            type=transaction_type,
            amount=Decimal(str(item.amount)),
            category=item.category,
            description=item.description.strip(),
            transaction_date=parse_transaction_date(
                item.transaction_date
            ),
        )

        new_transactions.append(transaction)

    # Save the complete batch in one database transaction.
    with SessionLocal() as session:
        try:
            session.add_all(new_transactions)
            session.commit()

            return [
                transaction_to_dict(transaction)
                for transaction in new_transactions
            ]

        except Exception:
            session.rollback()
            raise


def list_transactions(
    transaction_type: str | None = None,
) -> list[dict]:
    """Retrieve transactions from MySQL, optionally by type."""

    if transaction_type not in {None, "expense", "income"}:
        raise ValueError("Invalid transaction type.")

    statement = select(Transaction).order_by(
        Transaction.created_at.desc()
    )

    if transaction_type is not None:
        statement = statement.where(
            Transaction.type == transaction_type
        )

    with SessionLocal() as session:
        transactions = session.scalars(statement).all()

        return [
            transaction_to_dict(transaction)
            for transaction in transactions
        ]


def get_balance() -> float:
    """Calculate total income minus total expenses from MySQL."""

    with SessionLocal() as session:
        income = session.scalar(
            select(
                func.coalesce(func.sum(Transaction.amount), 0)
            ).where(Transaction.type == "income")
        )

        expenses = session.scalar(
            select(
                func.coalesce(func.sum(Transaction.amount), 0)
            ).where(Transaction.type == "expense")
        )

        balance = Decimal(str(income)) - Decimal(str(expenses))

        return float(balance)


def clear_transactions() -> None:
    """Delete all transactions. Use only when intentionally resetting data."""

    with SessionLocal() as session:
        try:
            session.execute(delete(Transaction))
            session.commit()
        except Exception:
            session.rollback()
            raise
