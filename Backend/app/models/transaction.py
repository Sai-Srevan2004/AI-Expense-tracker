from sqlalchemy import String, Float, Date, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
import enum
from app.database.session import Base


class TransactionType(str, enum.Enum):
    expense = "expense"
    income = "income"


class Category(str, enum.Enum):
    food = "Food"
    grocery = "Grocery"
    transport = "Transport"
    fuel = "Fuel"
    rent = "Rent"
    shopping = "Shopping"
    entertainment = "Entertainment"
    bills = "Bills"
    emi = "EMI"
    education = "Education"
    medical = "Medical"
    travel = "Travel"
    salary = "Salary"
    investment = "Investment"
    others = "Others"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    category: Mapped[Category] = mapped_column(Enum(Category), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    merchant: Mapped[str | None] = mapped_column(String(150), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="transactions")