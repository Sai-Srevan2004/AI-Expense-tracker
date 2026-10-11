
import os
import uuid

import pymysql
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver

from app.ai.graph import build_graph

load_dotenv(override=True)

THREAD_ID = "personal-expense-tracker"


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
