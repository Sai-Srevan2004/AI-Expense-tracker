
from langchain_core.tools import tool

from app.schemas.intent import TransactionItem

from langgraph.types import interrupt

from app.tools.transaction_store import (
    add_transactions,
    get_balance,
    list_transactions,
    update_transaction as update_transaction_record,
    delete_transaction as delete_transaction_record,
)


def validate_batch(transactions: list[dict]) -> list[TransactionItem]:
    """Validate every transaction before saving any of them."""
    if not transactions:
        raise ValueError("At least one transaction is required.")

    items = [
        TransactionItem.model_validate(transaction)
        for transaction in transactions
    ]

    for item in items:
        if item.amount is None or item.amount <= 0:
            raise ValueError(
                "Every transaction must have a positive amount."
            )

        if not item.category:
            raise ValueError(
                "Every transaction needs a category."
            )

        if not item.description or not item.description.strip():
            raise ValueError(
                "Every transaction needs a description."
            )

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
    """List transactions: all, expense, or income."""
    if transaction_type not in {"all", "expense", "income"}:
        return {
            "success": False,
            "error": "Use all, expense, or income.",
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
    """Calculate recorded income minus recorded expenses."""
    return {
        "success": True,
        "balance": get_balance(),
    }



@tool
def update_transaction_tool(
    transaction_id: str,
    amount: float | None = None,
    category: str | None = None,
    description: str | None = None,
    transaction_date: str | None = None,
) -> dict:
    """Update a transaction only after the user confirms the proposed changes."""

    if all(
        value is None
        for value in (amount, category, description, transaction_date)
    ):
        return {
            "success": False,
            "error": "Provide at least one field to update.",
        }

    transactions = list_transactions()
    existing = next(
        (item for item in transactions if item["id"] == transaction_id),
        None,
    )

    if existing is None:
        return {
            "success": False,
            "error": "Transaction not found. Retrieve transactions first.",
        }

    changes = {
        key: value
        for key, value in {
            "amount": amount,
            "category": category,
            "description": description,
            "date": transaction_date,
        }.items()
        if value is not None
    }

    # Pause the graph and wait for the user's decision.
    decision = interrupt({
        "action": "update_transaction",
        "transaction": existing,
        "proposed_changes": changes,
        "message": "Approve these transaction changes?",
    })

    if not isinstance(decision, dict) or decision.get("approved") is not True:
        return {
            "success": False,
            "cancelled": True,
            "message": "Transaction update cancelled.",
        }

    updated = update_transaction_record(
        transaction_id=transaction_id,
        amount=amount,
        category=category,
        description=description,
        transaction_date=transaction_date,
    )

    if updated is None:
        return {
            "success": False,
            "error": "Transaction no longer exists.",
        }

    return {
        "success": True,
        "message": "Transaction updated successfully.",
        "transaction": updated,
    }


@tool
def delete_transaction_tool(transaction_id: str) -> dict:
    """Delete a transaction only after the user confirms its deletion."""

    transactions = list_transactions()
    existing = next(
        (item for item in transactions if item["id"] == transaction_id),
        None,
    )

    if existing is None:
        return {
            "success": False,
            "error": "Transaction not found. Retrieve transactions first.",
        }

    # Pause the graph before deleting anything.
    decision = interrupt({
        "action": "delete_transaction",
        "transaction": existing,
        "message": "Approve deletion of this transaction?",
    })

    if not isinstance(decision, dict) or decision.get("approved") is not True:
        return {
            "success": False,
            "cancelled": True,
            "message": "Transaction deletion cancelled.",
        }

    deleted = delete_transaction_record(transaction_id)

    if deleted is None:
        return {
            "success": False,
            "error": "Transaction no longer exists.",
        }

    return {
        "success": True,
        "message": "Transaction deleted successfully.",
        "transaction": deleted,
    }
