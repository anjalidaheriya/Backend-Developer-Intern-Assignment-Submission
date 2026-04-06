"""Financial service - business logic for financial records"""
from datetime import datetime, timezone, date
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException

from models.financial import (
    RecordCreate, RecordUpdate, RecordResponse, RecordFilter,
    CategorySummary, MonthlySummary, DashboardSummary
)


class FinancialService:
    def __init__(self, db):
        self.db = db
        self.collection = db.financial_records
    
    async def create_record(self, record_data: RecordCreate, user_id: str) -> RecordResponse:
        """Create a new financial record"""
        record_doc = {
            "amount": record_data.amount,
            "type": record_data.type.value,
            "category": record_data.category.value,
            "date": record_data.date.isoformat(),
            "description": record_data.description,
            "notes": record_data.notes,
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
            "is_deleted": False
        }
        
        result = await self.collection.insert_one(record_doc)
        record_doc["id"] = str(result.inserted_id)
        
        return self._doc_to_response(record_doc)
    
    async def get_record(self, record_id: str, user_id: str = None, 
                         user_role: str = None) -> RecordResponse:
        """Get a single financial record"""
        try:
            query = {"_id": ObjectId(record_id), "is_deleted": False}
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid record ID")
        
        record = await self.collection.find_one(query)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        return self._doc_to_response(record)
    
    async def list_records(self, page: int = 1, page_size: int = 20,
                          filters: Optional[RecordFilter] = None,
                          user_id: str = None, user_role: str = None) -> dict:
        """List financial records with filtering and pagination"""
        query = {"is_deleted": False}
        
        # Apply filters
        if filters:
            if filters.type:
                query["type"] = filters.type.value
            if filters.category:
                query["category"] = filters.category.value
            if filters.start_date:
                query["date"] = query.get("date", {})
                query["date"]["$gte"] = filters.start_date.isoformat()
            if filters.end_date:
                query.setdefault("date", {})
                query["date"]["$lte"] = filters.end_date.isoformat()
            if filters.min_amount:
                query["amount"] = query.get("amount", {})
                query["amount"]["$gte"] = filters.min_amount
            if filters.max_amount:
                query.setdefault("amount", {})
                query["amount"]["$lte"] = filters.max_amount
            if filters.search:
                query["$or"] = [
                    {"description": {"$regex": filters.search, "$options": "i"}},
                    {"notes": {"$regex": filters.search, "$options": "i"}}
                ]
        
        # Get total count
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        skip = (page - 1) * page_size
        cursor = self.collection.find(query).skip(skip).limit(page_size).sort("date", -1)
        records = await cursor.to_list(length=page_size)
        
        return {
            "records": [self._doc_to_response(r) for r in records],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    
    async def update_record(self, record_id: str, update_data: RecordUpdate,
                           user_id: str, user_role: str) -> RecordResponse:
        """Update a financial record"""
        try:
            query = {"_id": ObjectId(record_id), "is_deleted": False}
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid record ID")
        
        record = await self.collection.find_one(query)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Only admin or record creator can update
        if user_role != "admin" and record["created_by"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this record")
        
        # Build update document
        update_doc = {"updated_at": datetime.now(timezone.utc)}
        
        if update_data.amount is not None:
            update_doc["amount"] = update_data.amount
        if update_data.type is not None:
            update_doc["type"] = update_data.type.value
        if update_data.category is not None:
            update_doc["category"] = update_data.category.value
        if update_data.date is not None:
            update_doc["date"] = update_data.date.isoformat()
        if update_data.description is not None:
            update_doc["description"] = update_data.description
        if update_data.notes is not None:
            update_doc["notes"] = update_data.notes
        
        await self.collection.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": update_doc}
        )
        
        return await self.get_record(record_id, user_id, user_role)
    
    async def delete_record(self, record_id: str, user_id: str, 
                           user_role: str) -> bool:
        """Soft delete a financial record"""
        try:
            query = {"_id": ObjectId(record_id), "is_deleted": False}
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid record ID")
        
        record = await self.collection.find_one(query)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Only admin or record creator can delete
        if user_role != "admin" and record["created_by"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this record")
        
        await self.collection.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": {"is_deleted": True, "updated_at": datetime.now(timezone.utc)}}
        )
        
        return True
    
    async def get_dashboard_summary(self, user_id: str = None, 
                                   user_role: str = None) -> DashboardSummary:
        """Get dashboard summary with aggregated data"""
        base_query = {"is_deleted": False}
        
        # Total income
        income_pipeline = [
            {"$match": {**base_query, "type": "income"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        income_result = await self.collection.aggregate(income_pipeline).to_list(1)
        total_income = income_result[0]["total"] if income_result else 0
        
        # Total expenses
        expense_pipeline = [
            {"$match": {**base_query, "type": "expense"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        expense_result = await self.collection.aggregate(expense_pipeline).to_list(1)
        total_expenses = expense_result[0]["total"] if expense_result else 0
        
        # Income by category
        income_by_cat_pipeline = [
            {"$match": {**base_query, "type": "income"}},
            {"$group": {"_id": "$category", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
        ]
        income_by_cat = await self.collection.aggregate(income_by_cat_pipeline).to_list(100)
        income_categories = [
            CategorySummary(category=item["_id"], total=item["total"], count=item["count"])
            for item in income_by_cat
        ]
        
        # Expenses by category
        expense_by_cat_pipeline = [
            {"$match": {**base_query, "type": "expense"}},
            {"$group": {"_id": "$category", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
        ]
        expense_by_cat = await self.collection.aggregate(expense_by_cat_pipeline).to_list(100)
        expense_categories = [
            CategorySummary(category=item["_id"], total=item["total"], count=item["count"])
            for item in expense_by_cat
        ]
        
        # Monthly trends (last 12 months)
        monthly_pipeline = [
            {"$match": base_query},
            {"$addFields": {"month": {"$substr": ["$date", 0, 7]}}},
            {"$group": {
                "_id": {"month": "$month", "type": "$type"},
                "total": {"$sum": "$amount"}
            }},
            {"$sort": {"_id.month": -1}},
            {"$limit": 24}  # Last 12 months * 2 (income + expense)
        ]
        monthly_data = await self.collection.aggregate(monthly_pipeline).to_list(24)
        
        # Process monthly trends
        monthly_dict = {}
        for item in monthly_data:
            month = item["_id"]["month"]
            record_type = item["_id"]["type"]
            if month not in monthly_dict:
                monthly_dict[month] = {"income": 0, "expenses": 0}
            if record_type == "income":
                monthly_dict[month]["income"] = item["total"]
            else:
                monthly_dict[month]["expenses"] = item["total"]
        
        monthly_trends = [
            MonthlySummary(
                month=month,
                income=data["income"],
                expenses=data["expenses"],
                net=data["income"] - data["expenses"]
            )
            for month, data in sorted(monthly_dict.items(), reverse=True)[:12]
        ]
        
        # Recent records
        recent_cursor = self.collection.find(base_query).sort("created_at", -1).limit(10)
        recent_records = await recent_cursor.to_list(10)
        recent_responses = [self._doc_to_response(r) for r in recent_records]
        
        # Total record count
        record_count = await self.collection.count_documents(base_query)
        
        return DashboardSummary(
            total_income=total_income,
            total_expenses=total_expenses,
            net_balance=total_income - total_expenses,
            income_by_category=income_categories,
            expenses_by_category=expense_categories,
            recent_records=recent_responses,
            monthly_trends=monthly_trends,
            record_count=record_count
        )
    
    async def get_category_breakdown(self, record_type: str = None) -> list[CategorySummary]:
        """Get category-wise breakdown"""
        query = {"is_deleted": False}
        if record_type:
            query["type"] = record_type
        
        pipeline = [
            {"$match": query},
            {"$group": {"_id": "$category", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
            {"$sort": {"total": -1}}
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(100)
        return [
            CategorySummary(category=item["_id"], total=item["total"], count=item["count"])
            for item in results
        ]
    
    async def get_trends(self, period: str = "monthly", months: int = 12) -> list[MonthlySummary]:
        """Get income/expense trends"""
        base_query = {"is_deleted": False}
        
        pipeline = [
            {"$match": base_query},
            {"$addFields": {"month": {"$substr": ["$date", 0, 7]}}},
            {"$group": {
                "_id": {"month": "$month", "type": "$type"},
                "total": {"$sum": "$amount"}
            }},
            {"$sort": {"_id.month": -1}},
            {"$limit": months * 2}
        ]
        
        monthly_data = await self.collection.aggregate(pipeline).to_list(months * 2)
        
        monthly_dict = {}
        for item in monthly_data:
            month = item["_id"]["month"]
            record_type = item["_id"]["type"]
            if month not in monthly_dict:
                monthly_dict[month] = {"income": 0, "expenses": 0}
            if record_type == "income":
                monthly_dict[month]["income"] = item["total"]
            else:
                monthly_dict[month]["expenses"] = item["total"]
        
        return [
            MonthlySummary(
                month=month,
                income=data["income"],
                expenses=data["expenses"],
                net=data["income"] - data["expenses"]
            )
            for month, data in sorted(monthly_dict.items(), reverse=True)[:months]
        ]
    
    def _doc_to_response(self, doc: dict) -> RecordResponse:
        """Convert MongoDB document to response model"""
        return RecordResponse(
            id=str(doc.get("_id", doc.get("id"))),
            amount=doc["amount"],
            type=doc["type"],
            category=doc["category"],
            date=date.fromisoformat(doc["date"]) if isinstance(doc["date"], str) else doc["date"],
            description=doc.get("description"),
            notes=doc.get("notes"),
            created_by=doc["created_by"],
            created_at=doc["created_at"],
            updated_at=doc.get("updated_at"),
            is_deleted=doc.get("is_deleted", False)
        )
