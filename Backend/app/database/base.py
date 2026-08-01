# Import all models here so Alembic can discover them via Base.metadata
from app.database.session import Base  # noqa
from app.models.user import User  # noqa
from app.models.transaction import Transaction  # noqa
from app.models.budget import Budget, MonthlyBudget  # noqa
from app.models.ai_insight import AIInsight  # noqa
from app.models.conversation import ConversationHistory  # noqa