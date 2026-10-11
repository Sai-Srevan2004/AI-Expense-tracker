
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from app.schemas.intent import TransactionIntent

load_dotenv()

model = ChatGroq(
    model=os.getenv("LLM_NAME", "llama-3.3-70b-versatile"),
    temperature=0,
)

extractor = model.with_structured_output(TransactionIntent)

SYSTEM_PROMPT = """
You interpret messages for a personal expense and income tracker.

Return one intent and a list of all transaction items mentioned.

Rules:
- Extract every distinct transaction, not just the first one.
- Never invent amounts, dates, categories, or descriptions.
- Each transaction must be represented by a separate list item.
- For expenses, use categories such as Food, Transport, Shopping,
  Bills, Entertainment, Health, Education, Travel, Accommodation,
  Groceries, and Other.
- For income, use Salary, Freelancing, Business, Investment, Gift,
  or Other.
- Hotel or lodging expenses should normally use Accommodation.
- Preserve the meaning of each amount and its associated description.
- Do not assume two identical amounts refer to the same transaction.
- If the wording could mean either one transaction or multiple
  transactions, ask a clarification question.
- If a transaction is missing an essential amount, ask for it.
- Questions about spending, income, balance, or history are queries,
  not new transactions.
- Requests to change or delete existing transactions are not new
  transactions.
- Never claim that transactions have been saved, changed, or deleted.
- Never calculate authoritative financial totals.
- Use the allowed schema categories only.
- For dates, preserve the date expression mentioned by the user.
"""


def extract_intent(message: str) -> TransactionIntent:
    """Convert a message into a validated structured interpretation."""

    if not message.strip():
        raise ValueError("Message cannot be empty.")

    return extractor.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", message),
        ]
    )
