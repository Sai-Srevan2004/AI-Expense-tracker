# AI Expense Tracker

A conversational expense tracker — manage your finances by chatting instead of filling forms. Built with FastAPI, LangGraph, Groq, React, and MySQL.

## Status
🚧 In active development — building step by step.

## Tech Stack

**Frontend:** React 19, Vite, React Router, Axios, Tailwind CSS, Recharts
**Backend:** FastAPI, LangChain, LangGraph, Groq API, SQLAlchemy, Alembic, JWT Auth
**Database:** MySQL

## Architecture

LLM never writes to the database directly. Every chat message flows through:
