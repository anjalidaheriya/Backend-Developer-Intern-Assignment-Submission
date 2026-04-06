"""Financial records routes"""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Request, Depends, Query, HTTPException

from models.financial import (
    RecordCreate, RecordUpdate, RecordResponse, RecordListResponse, RecordFilter,
    RecordType, RecordCategory
)
from services.financial_service import FinancialService
from middleware.auth import get_current_user, require_analyst_or_admin, require_admin

router = APIRouter(prefix="/records", tags=["Financial Records"])


@router.get("", response_model=RecordListResponse)
async def list_records(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[RecordType] = None,
    category: Optional[RecordCategory] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List financial records with filtering (All authenticated users)"""
    db = request.app.state.db
    service = FinancialService(db)
    
    filters = RecordFilter(
        type=type,
        category=category,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search
    )
    
    result = await service.list_records(page, page_size, filters, user["id"], user["role"])
    return RecordListResponse(**result)


@router.post("", response_model=RecordResponse)
async def create_record(
    record_data: RecordCreate,
    request: Request,
    user: dict = Depends(require_analyst_or_admin)
):
    """Create a new financial record (Analyst and Admin only)"""
    db = request.app.state.db
    service = FinancialService(db)
    
    return await service.create_record(record_data, user["id"])


@router.get("/{record_id}", response_model=RecordResponse)
async def get_record(
    record_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Get a single record (All authenticated users)"""
    db = request.app.state.db
    service = FinancialService(db)
    
    return await service.get_record(record_id, user["id"], user["role"])


@router.put("/{record_id}", response_model=RecordResponse)
async def update_record(
    record_id: str,
    update_data: RecordUpdate,
    request: Request,
    user: dict = Depends(require_analyst_or_admin)
):
    """Update a financial record (Analyst and Admin only)"""
    db = request.app.state.db
    service = FinancialService(db)
    
    return await service.update_record(record_id, update_data, user["id"], user["role"])


@router.delete("/{record_id}")
async def delete_record(
    record_id: str,
    request: Request,
    user: dict = Depends(require_analyst_or_admin)
):
    """Delete a financial record (Analyst and Admin only)"""
    db = request.app.state.db
    service = FinancialService(db)
    
    await service.delete_record(record_id, user["id"], user["role"])
    return {"message": "Record deleted successfully"}
