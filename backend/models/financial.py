"""Financial record models and schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime, date
from enum import Enum


class RecordType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class RecordCategory(str, Enum):
    SALARY = "salary"
    INVESTMENT = "investment"
    FREELANCE = "freelance"
    RENT = "rent"
    UTILITIES = "utilities"
    GROCERIES = "groceries"
    TRANSPORTATION = "transportation"
    ENTERTAINMENT = "entertainment"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    SHOPPING = "shopping"
    TRAVEL = "travel"
    FOOD = "food"
    SUBSCRIPTIONS = "subscriptions"
    OTHER = "other"


# Request schemas
class RecordCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Amount must be positive")
    type: RecordType
    category: RecordCategory
    date: date
    description: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)


class RecordUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    type: Optional[RecordType] = None
    category: Optional[RecordCategory] = None
    date: Optional[date] = None
    description: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)


class RecordFilter(BaseModel):
    type: Optional[RecordType] = None
    category: Optional[RecordCategory] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    search: Optional[str] = None


# Response schemas
class RecordResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str
    amount: float
    type: RecordType
    category: RecordCategory
    date: date
    description: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: bool = False


class RecordListResponse(BaseModel):
    records: list[RecordResponse]
    total: int
    page: int
    page_size: int


# Dashboard/Summary schemas
class CategorySummary(BaseModel):
    category: str
    total: float
    count: int


class MonthlySummary(BaseModel):
    month: str  # Format: YYYY-MM
    income: float
    expenses: float
    net: float


class DashboardSummary(BaseModel):
    total_income: float
    total_expenses: float
    net_balance: float
    income_by_category: list[CategorySummary]
    expenses_by_category: list[CategorySummary]
    recent_records: list[RecordResponse]
    monthly_trends: list[MonthlySummary]
    record_count: int
