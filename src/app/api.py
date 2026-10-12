
import os
import uuid
from contextlib import asynccontextmanager

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.ai.graph import build_graph

load_dotenv(override=True)


def get_mysql_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ai_expense_tracker"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection = get_mysql_connection()
    try:
        PyMySQLSaver(connection).setup()
    finally:
        connection.close()

    yield


app = FastAPI(
    title="AI Expense Tracker API",
    description="Manage personal finances through an AI assistant.",
    version="0.1.0",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    thread_id: str | None = None


class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    approval_required: bool = False
    approval_request: dict | None = None


def invoke_graph(thread_id: str, graph_input: dict | Command) -> dict:
    """Run the graph using a fresh MySQL connection."""
    connection = get_mysql_connection()

    try:
        checkpointer = PyMySQLSaver(connection)
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        return graph.invoke(graph_input, config=config)
    finally:
        connection.close()


def has_pending_approval(thread_id: str) -> bool:
    """Check whether this conversation is waiting for approval."""
    connection = get_mysql_connection()

    try:
        checkpointer = PyMySQLSaver(connection)
        graph = build_graph(checkpointer)

        config = {"configurable": {"thread_id": thread_id}}
        state = graph.get_state(config)

        return any(
            task.interrupts
            for task in state.tasks
        )
    finally:
        connection.close()



def format_result(result: dict, thread_id: str) -> ChatResponse:
    """Convert a graph result into an API response."""
    interrupts = result.get("__interrupt__", [])

    if interrupts:
        approval_request = interrupts[0].value

        return ChatResponse(
            response="Your approval is required before this operation can proceed.",
            thread_id=thread_id,
            approval_required=True,
            approval_request=approval_request,
        )

    messages = result.get("messages", [])
    content = messages[-1].content if messages else ""

    if not isinstance(content, str):
        content = str(content)

    return ChatResponse(
        response=content,
        thread_id=thread_id,
    )


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}



@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    thread_id = request.thread_id or str(uuid.uuid4())

    try:
        if has_pending_approval(thread_id):
            raise HTTPException(
                status_code=409,
                detail=(
                    "This conversation has a pending approval. "
                    "Please approve or reject it using /approval "
                    "before sending another message."
                ),
            )

        result = invoke_graph(
            thread_id,
            {"messages": [HumanMessage(content=request.message)]},
        )

        return format_result(result, thread_id)

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Chat request failed: "
                f"{type(error).__name__}: {error}"
            ),
        ) from error


@app.post("/approval", response_model=ChatResponse)
def handle_approval(request: ApprovalRequest) -> ChatResponse:
    try:
        result = invoke_graph(
            request.thread_id,
            Command(resume={"approved": request.approved}),
        )
        return format_result(result, request.thread_id)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Approval request failed: {type(error).__name__}: {error}",
        ) from error
