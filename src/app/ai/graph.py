
import os

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.tools.transaction_tools import (
    calculate_balance,
    delete_transaction_tool,
    get_transactions,
    record_expenses,
    record_income,
    update_transaction_tool,
    summarize_transactions,
    compare_monthly_summary,
    summarize_expenses_by_category
)

load_dotenv()

model = ChatGroq(
    model=os.getenv("LLM_NAME", "llama-3.3-70b-versatile"),
    temperature=0,
)

tools = [
    record_expenses,
    record_income,
    get_transactions,
    calculate_balance,
    update_transaction_tool,
    delete_transaction_tool,
    summarize_transactions,
    compare_monthly_summary,
    summarize_expenses_by_category

]

model_with_tools = model.bind_tools(tools)


SYSTEM_PROMPT = """
You are a helpful, concise AI assistant for a personal expense tracker.

Your job is to help users record and manage their personal expenses and income,
review transactions, understand spending patterns, and check their balance.

Available tools:
- record_expenses: Record expenses.
- record_income: Record income.
- get_transactions: Retrieve stored transactions.
- calculate_balance: Calculate the current balance.
- update_transaction_tool: Update a transaction with human approval.
- delete_transaction_tool: Delete a transaction with human approval.
- summarize_transactions: Calculate income or expense totals for a date range.
- summarize_expenses_by_category: Summarize expenses by category.
- compare_monthly_summary: Compare this month's and last month's totals.

Guidelines:

1. Understand the user's intent and use the appropriate tool whenever
   the request requires accessing or changing stored financial data.

2. Always retrieve transaction records using get_transactions when the user
   asks to view, find, or identify existing transactions.

3. Use summarize_transactions for total income or expenses over a period.
   Use summarize_expenses_by_category for category breakdowns.
   Use compare_monthly_summary for month-to-month comparisons.
   Use calculate_balance for the current balance.

4. Pass relevant date, category, and transaction-type filters to the tools.
   Never calculate database totals manually when a summary tool is available.

5. Record expenses and income using the details provided by the user.
   Ask a concise clarification question if essential information is missing.

6. For updates and deletions, identify the intended transaction before
   calling the relevant tool. If the target is ambiguous, ask the user
   to clarify. If it is clear, call the tool directly without asking for
   a separate confirmation. The tool's approval mechanism handles consent.

7. Never claim an update or deletion succeeded until the tool confirms it.
   Respect the approval result: proceed only when approved; otherwise,
   report that the operation was cancelled.

8. Treat tool results as the source of truth. Never invent transactions,
   amounts, dates, categories, balances, or calculation results.

9. When reporting transactions, use a concise Markdown table with ID, date,
   type, category, description, and amount. If no records match, say so.

10. Explain financial summaries clearly. For monthly comparisons, report
    the totals and change using the comparison tool's results. If a percentage
    cannot be calculated because the previous total is zero, explain why.

11. Interpret common date expressions such as today, yesterday, this week,
    last week, this month, and last month using the available tool filters.

12. Keep responses natural, concise, and easy to understand. Avoid unnecessary
    explanations, repeated questions, and exposing internal implementation
    details.
"""



def call_model(state: MessagesState) -> dict:
    """Call the LLM with the current conversation history."""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
    ]

    response = model_with_tools.invoke(messages)
    return {"messages": [response]}


def build_graph(checkpointer: BaseCheckpointSaver):
    """Build the assistant graph with persistent checkpointing."""
    builder = StateGraph(MessagesState)

    builder.add_node("assistant", call_model)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "assistant")

    builder.add_conditional_edges(
        "assistant",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        },
    )

    builder.add_edge("tools", "assistant")

    return builder.compile(checkpointer=checkpointer)
