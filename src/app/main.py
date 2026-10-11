
import json

from app.ai.graph import expense_graph


def main() -> None:
    message = input("You: ").strip()

    try:
        result = expense_graph.invoke({"message": message})

        print("\nAI response:")
        print(result.get("response", "No response generated."))

        intent_data = result.get("intent_data")

        if intent_data:
            print("\nExtracted intent:")
            print(
                json.dumps(
                    intent_data.model_dump(),
                    indent=2,
                    ensure_ascii=False,
                )
            )

            if intent_data.transactions:
                print("\nTransactions identified:")

                for index, transaction in enumerate(
                    intent_data.transactions,
                    start=1,
                ):
                    print(
                        f"{index}. "
                        f"Amount: {transaction.amount} | "
                        f"Category: {transaction.category} | "
                        f"Description: {transaction.description}"
                    )

    except Exception as error:
        print(f"Workflow failed: {error}")


if __name__ == "__main__":
    main()
