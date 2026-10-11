
from typing import Literal

from pydantic import BaseModel, Field


IntentType = Literal[
    "add_expense",
    "add_income",
    "query_expenses",
    "query_income",
    "query_balance",
    "query_transactions",
    "update_transaction",
    "delete_transaction",
    "general_question",
    "unclear",
]

Category = Literal[
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Entertainment",
    "Health",
    "Education",
    "Travel",
    "Accommodation",
    "Groceries",
    "Salary",
    "Freelancing",
    "Business",
    "Investment",
    "Gift",
    "Other",
]


class TransactionItem(BaseModel):
    """One transaction mentioned in a user's message."""

    amount: float | None = Field(default=None, gt=0)
    category: Category | None = None
    description: str | None = None
    transaction_date: str | None = None


class TransactionIntent(BaseModel):
    """Structured interpretation of a user's complete message."""

    intent: IntentType

    transactions: list[TransactionItem] = Field(
        default_factory=list,
        description="All transactions mentioned in the message.",
    )

    clarification_needed: bool = False

    clarification_question: str | None = None
