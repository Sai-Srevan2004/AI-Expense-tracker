
from langgraph.graph import END, START, StateGraph

from app.ai.extractor import extract_intent
from app.ai.state import ExpenseState


def receive_message(state: ExpenseState) -> dict:
    """Validate the incoming message."""

    message = state.get("message", "").strip()

    if not message:
        return {"response": "Please enter a message."}

    return {"message": message}


def extract_request(state: ExpenseState) -> dict:
    """Extract the user's intent and all transaction candidates."""

    intent_data = extract_intent(state["message"])
    return {"intent_data": intent_data}


def route_request(state: ExpenseState) -> str:
    """Route the request according to the extracted intent."""

    intent_data = state.get("intent_data")

    if intent_data is None:
        return "respond"

    if (
        intent_data.clarification_needed
        or intent_data.intent == "unclear"
    ):
        return "clarify"

    if intent_data.intent in {"add_expense", "add_income"}:
        if not intent_data.transactions:
            return "clarify"

        if any(
            transaction.amount is None
            for transaction in intent_data.transactions
        ):
            return "clarify"

    return "respond"


def clarify_request(state: ExpenseState) -> dict:
    """Ask a follow-up question when details are unclear."""

    intent_data = state.get("intent_data")

    if intent_data and intent_data.clarification_question:
        question = intent_data.clarification_question
    else:
        question = "Could you clarify the transaction details?"

    return {"response": question}


def prepare_response(state: ExpenseState) -> dict:
    """Summarize the interpretation without performing transactions."""

    intent_data = state.get("intent_data")

    if intent_data is None:
        return {
            "response": state.get(
                "response",
                "Please try again.",
            )
        }

    intent = intent_data.intent
    transactions = intent_data.transactions
    count = len(transactions)

    if intent == "add_expense":
        response = (
            f"I understood {count} expense transaction(s). "
            "Nothing has been saved yet."
        )

    elif intent == "add_income":
        response = (
            f"I understood {count} income transaction(s). "
            "Nothing has been saved yet."
        )

    elif intent in {
        "query_expenses",
        "query_income",
        "query_balance",
        "query_transactions",
    }:
        response = (
            "I understood your query. Transaction storage and "
            "analytics are not connected yet."
        )

    elif intent == "update_transaction":
        response = (
            "I understood your update request. "
            "No transaction has been changed."
        )

    elif intent == "delete_transaction":
        response = (
            "I understood your deletion request. "
            "No transaction has been deleted."
        )

    else:
        response = (
            "I understood your message, but I need more details "
            "to help."
        )

    return {"response": response}


def after_receive(state: ExpenseState) -> str:
    if state.get("response"):
        return "respond"

    return "extract"


builder = StateGraph(ExpenseState)

builder.add_node("receive", receive_message)
builder.add_node("extract", extract_request)
builder.add_node("clarify", clarify_request)
builder.add_node("respond", prepare_response)

builder.add_edge(START, "receive")

builder.add_conditional_edges(
    "receive",
    after_receive,
    {
        "extract": "extract",
        "respond": "respond",
    },
)

builder.add_conditional_edges(
    "extract",
    route_request,
    {
        "clarify": "clarify",
        "respond": "respond",
    },
)

builder.add_edge("clarify", END)
builder.add_edge("respond", END)

expense_graph = builder.compile()
