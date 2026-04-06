"""Dashboard and analytics routes"""
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query

from models.financial import DashboardSummary, CategorySummary, MonthlySummary
from services.financial_service import FinancialService
from middleware.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Get dashboard summary with totals, breakdowns, and trends (All authenticated users)"""
    db = request.app.state.db
    service = FinancialService(db)
    
    return await service.get_dashboard_summary(user["id"], user["role"])


@router.get("/categories", response_model=list[CategorySummary])
async def get_category_breakdown(
    request: Request,
    type: Optional[str] = Query(None, description="Filter by 'income' or 'expense'"),
    user: dict = Depends(get_current_user)
):
    """Get category-wise breakdown (All authenticated users)"""
    db = request.app.state.db
    service = FinancialService(db)
    
    return await service.get_category_breakdown(type)


@router.get("/trends", response_model=list[MonthlySummary])
async def get_trends(
    request: Request,
    months: int = Query(12, ge=1, le=24, description="Number of months to include"),
    user: dict = Depends(get_current_user)
):
    """Get monthly income/expense trends (All authenticated users)"""
    db = request.app.state.db
    service = FinancialService(db)
    
    return await service.get_trends(months=months)


@router.get("/stats")
async def get_quick_stats(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Get quick statistics for dashboard cards"""
    db = request.app.state.db
    service = FinancialService(db)
    
    summary = await service.get_dashboard_summary(user["id"], user["role"])
    
    return {
        "total_income": summary.total_income,
        "total_expenses": summary.total_expenses,
        "net_balance": summary.net_balance,
        "record_count": summary.record_count,
        "top_income_category": summary.income_by_category[0].category if summary.income_by_category else None,
        "top_expense_category": summary.expenses_by_category[0].category if summary.expenses_by_category else None
    }
