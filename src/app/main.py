
from langchain_core.messages import HumanMessage

from app.ai.graph import expense_graph


def main() -> None:
    print("AI Expense Tracker")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            message = input("You: ").strip()

            if message.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break

            if not message:
                continue

            result = expense_graph.invoke(
                {"messages": [HumanMessage(content=message)]}
            )

            final_message = result["messages"][-1]
            response = final_message.content

            if isinstance(response, str):
                print(f"\nAssistant: {response}\n")
            else:
                print(f"\nAssistant: {response!r}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as error:
            print(f"\nRequest failed: {error}\n")


if __name__ == "__main__":
    main()
