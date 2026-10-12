
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


def resolve_date_range(
    date_filter: str | None,
) -> tuple[date | None, date | None]:
    """Convert common date filters into a start and end date."""
    if not date_filter:
        return None, None

    today = date.today()
    value = date_filter.strip().lower()

    if value == "today":
        return today, today

    if value == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday

    if value == "this month":
        start = today.replace(day=1)
        return start, today

    if value == "last month":
        end = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
        return start, end

    if value == "this week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end

    if value == "last week":
        this_week_start = today - timedelta(days=today.weekday())
        end = this_week_start - timedelta(days=1)
        start = end - timedelta(days=6)
        return start, end


    raise ValueError(
        "Unsupported date filter. Use today, yesterday, this week, "
        "last week, this month, or last month."
    )



def list_transactions(
    transaction_type: str | None = None,
    category: str | None = None,
    date_filter: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Retrieve transactions using optional filters."""
    filter_start, filter_end = resolve_date_range(date_filter)

    if start_date:
        filter_start = date.fromisoformat(start_date)

    if end_date:
        filter_end = date.fromisoformat(end_date)

    with SessionLocal() as session:
        statement = select(Transaction)

        if transaction_type:
            statement = statement.where(
                Transaction.type == transaction_type
            )

        if category:
            statement = statement.where(
                func.lower(Transaction.category) == category.strip().lower()
            )

        if filter_start:
            statement = statement.where(
                Transaction.transaction_date >= filter_start
            )

        if filter_end:
            statement = statement.where(
                Transaction.transaction_date <= filter_end
            )

        statement = statement.order_by(Transaction.created_at.desc())
        transactions = session.scalars(statement).all()

        return [transaction_to_dict(item) for item in transactions]


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


def update_transaction(
    transaction_id: str,
    amount: float | None = None,
    category: str | None = None,
    description: str | None = None,
    transaction_date: str | None = None,
) -> dict | None:
    """Update an existing transaction by its ID."""

    with SessionLocal() as session:
        try:
            transaction = session.get(Transaction, transaction_id)

            if transaction is None:
                return None

            if amount is not None:
                if amount <= 0:
                    raise ValueError("Amount must be positive.")

                transaction.amount = Decimal(str(amount))

            if category is not None:
                if not category.strip():
                    raise ValueError("Category cannot be empty.")

                transaction.category = category

            if description is not None:
                if not description.strip():
                    raise ValueError("Description cannot be empty.")

                transaction.description = description.strip()

            if transaction_date is not None:
                transaction.transaction_date = parse_transaction_date(
                    transaction_date
                )

            session.commit()
            session.refresh(transaction)

            return transaction_to_dict(transaction)

        except Exception:
            session.rollback()
            raise


def delete_transaction(transaction_id: str) -> dict | None:
    """Delete an existing transaction by its ID."""

    with SessionLocal() as session:
        try:
            transaction = session.get(Transaction, transaction_id)

            if transaction is None:
                return None

            deleted_transaction = transaction_to_dict(transaction)

            session.delete(transaction)
            session.commit()

            return deleted_transaction

        except Exception:
            session.rollback()
            raise



def clear_transactions() -> None:
    """Delete all transactions. Use only when intentionally resetting data."""

    with SessionLocal() as session:
        try:
            session.execute(delete(Transaction))
            session.commit()
        except Exception:
            session.rollback()
            raise



def get_transaction_summary(
    transaction_type: str = "expense",
    date_filter: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Calculate transaction totals and counts for a date range."""
    filter_start, filter_end = resolve_date_range(date_filter)

    if start_date:
        filter_start = date.fromisoformat(start_date)

    if end_date:
        filter_end = date.fromisoformat(end_date)

    with SessionLocal() as session:
        statement = select(
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
        ).where(Transaction.type == transaction_type)

        if filter_start:
            statement = statement.where(
                Transaction.transaction_date >= filter_start
            )

        if filter_end:
            statement = statement.where(
                Transaction.transaction_date <= filter_end
            )

        total, count = session.execute(statement).one()

        return {
            "type": transaction_type,
            "total": float(total),
            "count": count,
            "start_date": (
                filter_start.isoformat() if filter_start else None
            ),
            "end_date": filter_end.isoformat() if filter_end else None,
        }



def get_category_summary(
    date_filter: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Calculate expense totals grouped by category."""
    filter_start, filter_end = resolve_date_range(date_filter)

    if start_date:
        filter_start = date.fromisoformat(start_date)

    if end_date:
        filter_end = date.fromisoformat(end_date)

    with SessionLocal() as session:
        statement = (
            select(
                Transaction.category,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .where(Transaction.type == "expense")
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
        )

        if filter_start:
            statement = statement.where(
                Transaction.transaction_date >= filter_start
            )

        if filter_end:
            statement = statement.where(
                Transaction.transaction_date <= filter_end
            )

        rows = session.execute(statement).all()

        return [
            {
                "category": category,
                "total": float(total),
                "count": count,
            }
            for category, total, count in rows
        ]


def compare_monthly_transactions(
    transaction_type: str = "expense",
) -> dict:
    """Compare this month's total with last month's total."""
    today = date.today()

    this_month_start = today.replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    with SessionLocal() as session:
        statement = (
            select(
                func.sum(Transaction.amount),
                func.count(Transaction.id),
            )
            .where(Transaction.type == transaction_type)
        )

        current_total, current_count = session.execute(
            statement.where(
                Transaction.transaction_date >= this_month_start,
                Transaction.transaction_date <= today,
            )
        ).one()

        previous_total, previous_count = session.execute(
            statement.where(
                Transaction.transaction_date >= last_month_start,
                Transaction.transaction_date <= last_month_end,
            )
        ).one()

        current_total = float(current_total or 0)
        previous_total = float(previous_total or 0)

        difference = current_total - previous_total

        percentage_change = (
            (difference / previous_total) * 100
            if previous_total
            else None
        )

        return {
            "type": transaction_type,
            "this_month": {
                "start_date": this_month_start.isoformat(),
                "end_date": today.isoformat(),
                "total": current_total,
                "count": current_count,
            },
            "last_month": {
                "start_date": last_month_start.isoformat(),
                "end_date": last_month_end.isoformat(),
                "total": previous_total,
                "count": previous_count,
            },
            "difference": difference,
            "percentage_change": percentage_change,
        }
