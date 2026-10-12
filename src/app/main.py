
import os
import uuid

import pymysql
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver
from langgraph.types import Command

from app.ai.graph import build_graph

load_dotenv(override=True)

THREAD_ID = "user-1"


def show_approval_request(request: dict) -> bool:
    """Display a pending change and ask the user to approve it."""
    action = request.get("action")
    transaction = request.get("transaction", {})

    print("\n--- Human Approval Required ---")
    print(f"Action: {action}")
    print(f"Transaction ID: {transaction.get('id')}")
    print(f"Type: {transaction.get('type')}")
    print(f"Amount: {transaction.get('amount')}")
    print(f"Category: {transaction.get('category')}")
    print(f"Description: {transaction.get('description')}")
    print(f"Date: {transaction.get('date')}")

    if action == "update_transaction":
        print(f"Proposed changes: {request.get('proposed_changes')}")

    if action == "delete_transaction":
        print("This transaction will be permanently deleted if approved.")

    print(request.get("message", "Approve this operation?"))

    answer = input("Approve? Type yes or no: ").strip().lower()
    return answer in {"yes", "y"}


def run_chat() -> None:
    """Run the expense assistant with persistent MySQL memory."""
    connection = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ai_expense_tracker"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )

    try:
        checkpointer = PyMySQLSaver(connection)
        checkpointer.setup()
        expense_graph = build_graph(checkpointer)

        print("AI Expense Tracker")
        print("Type 'new' to start a fresh conversation.")
        print("Type 'exit' to quit.\n")

        thread_id = THREAD_ID

        while True:
            try:
                message = input("You: ").strip()

                if message.lower() in {"exit", "quit"}:
                    print("Goodbye!")
                    break

                if message.lower() == "new":
                    thread_id = str(uuid.uuid4())
                    print("Started a new conversation.\n")
                    continue

                if not message:
                    continue

                config = {
                    "configurable": {
                        "thread_id": thread_id,
                    }
                }

                result = expense_graph.invoke(
                    {"messages": [HumanMessage(content=message)]},
                    config=config,
                )

                # Resume paused graph execution after handling each approval.
                while result.get("__interrupt__"):
                    pending = result["__interrupt__"][0]
                    request = pending.value

                    approved = show_approval_request(request)

                    result = expense_graph.invoke(
                        Command(resume={"approved": approved}),
                        config=config,
                    )

                response = result["messages"][-1].content

                if isinstance(response, str):
                    print(f"\nAssistant: {response}\n")
                else:
                    print(f"\nAssistant: {response!r}\n")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break

            except Exception as error:
                print(
                    f"\nRequest failed: "
                    f"{type(error).__name__}: {error}\n"
                )

    finally:
        connection.close()


if __name__ == "__main__":
    run_chat()
