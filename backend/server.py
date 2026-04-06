"""
Finance Data Processing and Access Control Backend
Main FastAPI Application

Architecture:
- JWT-based authentication with role-based access control
- Three user roles: Viewer, Analyst, Admin
- Financial records CRUD with filtering
- Dashboard analytics and aggregations
- MongoDB for data persistence
"""
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path
from datetime import datetime, timezone

# Import routes
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.records import router as records_router
from routes.dashboard import router as dashboard_router

# Import auth utilities for admin seeding
from middleware.auth import hash_password, verify_password

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']


async def create_indexes(db):
    """Create MongoDB indexes for optimal performance"""
    try:
        # Users indexes
        await db.users.create_index("email", unique=True)
        
        # Login attempts index
        await db.login_attempts.create_index("identifier")
        
        # Password reset tokens TTL index
        await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
        
        # Financial records indexes
        await db.financial_records.create_index("created_by")
        await db.financial_records.create_index("type")
        await db.financial_records.create_index("category")
        await db.financial_records.create_index("date")
        await db.financial_records.create_index([("date", -1), ("created_at", -1)])
        
        logger.info("MongoDB indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")


async def seed_admin(db):
    """Seed admin user if not exists"""
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    
    try:
        existing = await db.users.find_one({"email": admin_email})
        
        if existing is None:
            hashed = hash_password(admin_password)
            await db.users.insert_one({
                "email": admin_email,
                "password_hash": hashed,
                "name": "System Admin",
                "role": "admin",
                "status": "active",
                "created_at": datetime.now(timezone.utc)
            })
            logger.info(f"Admin user created: {admin_email}")
        elif not verify_password(admin_password, existing["password_hash"]):
            await db.users.update_one(
                {"email": admin_email},
                {"$set": {"password_hash": hash_password(admin_password)}}
            )
            logger.info(f"Admin password updated: {admin_email}")
        
        # Write credentials to test file
        memory_dir = Path("/app/memory")
        memory_dir.mkdir(exist_ok=True)
        
        creds_file = memory_dir / "test_credentials.md"
        with open(creds_file, "w") as f:
            f.write("# Test Credentials\n\n")
            f.write("## Admin Account\n")
            f.write(f"- Email: {admin_email}\n")
            f.write(f"- Password: {admin_password}\n")
            f.write("- Role: admin\n\n")
            f.write("## API Endpoints\n")
            f.write("- POST /api/auth/login\n")
            f.write("- POST /api/auth/register\n")
            f.write("- GET /api/auth/me\n")
            f.write("- POST /api/auth/logout\n")
            f.write("- GET /api/users\n")
            f.write("- GET /api/records\n")
            f.write("- POST /api/records\n")
            f.write("- GET /api/dashboard/summary\n")
        
        logger.info("Test credentials written to /app/memory/test_credentials.md")
    except Exception as e:
        logger.error(f"Error seeding admin: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    app.state.db = db
    app.state.client = client
    
    # Create indexes and seed admin
    await create_indexes(db)
    await seed_admin(db)
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    client.close()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Finance Data Processing API",
    description="""
## Finance Data Processing and Access Control Backend

A comprehensive backend API for managing financial records with role-based access control.

### Features
- **User Management**: Create, update, and manage users with different roles
- **Role-Based Access Control**: Viewer, Analyst, and Admin roles with specific permissions
- **Financial Records**: CRUD operations for income/expense tracking
- **Dashboard Analytics**: Aggregated summaries, category breakdowns, and trends
- **JWT Authentication**: Secure authentication with access and refresh tokens

### User Roles
| Role | Permissions |
|------|-------------|
| **Viewer** | View dashboard data and records |
| **Analyst** | View + Create/Edit/Delete records |
| **Admin** | Full access including user management |

### Authentication
Use the `/api/auth/login` endpoint to obtain JWT tokens. Tokens are set as httpOnly cookies.
You can also use Bearer token in Authorization header.
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# CORS configuration
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
cors_origins = os.environ.get('CORS_ORIGINS', '*').split(',')

# Include frontend URL in allowed origins
allowed_origins = list(set(cors_origins + [frontend_url]))

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/api", tags=["Root"])
async def root():
    """API root - returns basic info"""
    return {
        "message": "Finance Data Processing API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "redoc": "/api/redoc"
    }


# Include routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(records_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


# API info endpoint listing all available endpoints
@app.get("/api/info", tags=["Info"])
async def api_info():
    """Get API information and available endpoints"""
    return {
        "name": "Finance Data Processing API",
        "version": "1.0.0",
        "description": "Backend API for financial data management with role-based access control",
        "endpoints": {
            "authentication": {
                "POST /api/auth/register": "Register new user (becomes Viewer)",
                "POST /api/auth/login": "Login and get tokens",
                "POST /api/auth/logout": "Logout (requires auth)",
                "GET /api/auth/me": "Get current user info",
                "POST /api/auth/refresh": "Refresh access token",
                "POST /api/auth/forgot-password": "Request password reset",
                "POST /api/auth/reset-password": "Reset password with token",
                "POST /api/auth/change-password": "Change password (requires auth)"
            },
            "users": {
                "GET /api/users": "List users (Admin only)",
                "POST /api/users": "Create user with role (Admin only)",
                "GET /api/users/{id}": "Get user by ID (Admin only)",
                "PUT /api/users/{id}": "Update user (Admin or self)",
                "DELETE /api/users/{id}": "Deactivate user (Admin only)"
            },
            "records": {
                "GET /api/records": "List records with filtering (All users)",
                "POST /api/records": "Create record (Analyst/Admin)",
                "GET /api/records/{id}": "Get record (All users)",
                "PUT /api/records/{id}": "Update record (Analyst/Admin, own or admin)",
                "DELETE /api/records/{id}": "Delete record (Analyst/Admin, own or admin)"
            },
            "dashboard": {
                "GET /api/dashboard/summary": "Get full dashboard summary",
                "GET /api/dashboard/categories": "Get category breakdown",
                "GET /api/dashboard/trends": "Get monthly trends",
                "GET /api/dashboard/stats": "Get quick stats"
            }
        },
        "roles": {
            "viewer": "Can view dashboard and records",
            "analyst": "Can view + manage records",
            "admin": "Full access including user management"
        }
    }
