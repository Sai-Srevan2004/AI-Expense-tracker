
from typing import TypedDict

from app.schemas.intent import TransactionIntent


class ExpenseState(TypedDict, total=False):
    message: str
    intent_data: TransactionIntent
    response: str
    transactions: list[dict]
