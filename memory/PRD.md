# Finance Data Processing and Access Control Backend - PRD

## Original Problem Statement
Build a backend API for a finance dashboard system with role-based access control. Support financial records management, user roles/permissions, and summary-level analytics.

## Architecture

### Backend (FastAPI + MongoDB)
```
/app/backend/
├── server.py              # Main FastAPI app with lifespan management
├── models/                # Pydantic schemas
│   ├── user.py           # User, role, auth models
│   └── financial.py      # Financial record, dashboard models
├── services/              # Business logic
│   ├── user_service.py   # User CRUD operations
│   └── financial_service.py  # Records & analytics
├── routes/                # API endpoints
│   ├── auth.py           # Authentication endpoints
│   ├── users.py          # User management (Admin)
│   ├── records.py        # Financial records CRUD
│   └── dashboard.py      # Analytics endpoints
└── middleware/
    └── auth.py           # JWT auth & RBAC middleware
```

### User Roles & Permissions
| Role | View Dashboard | Manage Records | Manage Users |
|------|---------------|----------------|--------------|
| Viewer | ✅ | ❌ | ❌ |
| Analyst | ✅ | ✅ | ❌ |
| Admin | ✅ | ✅ | ✅ |

## What's Been Implemented (April 6, 2026)

### Authentication System
- JWT-based auth with httpOnly cookies
- Access tokens (15 min) + Refresh tokens (7 days)
- Brute force protection (5 attempts = 15 min lockout)
- Password reset flow with secure tokens
- Admin user auto-seeding on startup

### User Management
- Create/Update/Delete users (Admin only)
- Role assignment (Viewer/Analyst/Admin)
- User status management (active/inactive)
- Self-registration (defaults to Viewer)

### Financial Records
- Full CRUD operations
- Filtering by type, category, date range, amount
- Search by description/notes
- Soft delete functionality
- Categories: salary, investment, freelance, rent, utilities, etc.

### Dashboard Analytics
- Total income/expenses/net balance
- Category-wise breakdowns
- Monthly trends
- Recent activity feed
- Quick stats endpoint

### Frontend (Minimal)
- Login form with pre-filled admin credentials
- Dashboard with stats cards and charts
- Records management (create/list/delete)
- User management (Admin only)
- API documentation viewer
- Role-based UI restrictions

## API Endpoints

### Authentication (`/api/auth`)
- POST `/login` - Login
- POST `/register` - Register (becomes Viewer)
- POST `/logout` - Logout
- GET `/me` - Current user info
- POST `/refresh` - Refresh access token
- POST `/forgot-password` - Request reset
- POST `/reset-password` - Reset with token
- POST `/change-password` - Change password

### Users (`/api/users`) - Admin Only
- GET `/` - List users
- POST `/` - Create user
- GET `/{id}` - Get user
- PUT `/{id}` - Update user
- DELETE `/{id}` - Deactivate user

### Records (`/api/records`)
- GET `/` - List with filters (All users)
- POST `/` - Create (Analyst/Admin)
- GET `/{id}` - Get record (All users)
- PUT `/{id}` - Update (Analyst/Admin)
- DELETE `/{id}` - Delete (Analyst/Admin)

### Dashboard (`/api/dashboard`)
- GET `/summary` - Full dashboard data
- GET `/categories` - Category breakdown
- GET `/trends` - Monthly trends
- GET `/stats` - Quick stats

## Prioritized Backlog

### P0 (Critical) - COMPLETED
- ✅ JWT Authentication
- ✅ Role-based access control
- ✅ Financial records CRUD
- ✅ Dashboard analytics
- ✅ Admin seeding

### P1 (Important) - Future
- Pagination for records listing
- Advanced search/filtering
- Export to CSV/Excel
- Audit logging

### P2 (Nice to Have)
- Email notifications
- Rate limiting
- Unit/Integration tests
- Docker deployment config

## Test Credentials
- **Admin**: admin@example.com / admin123
- **API Docs**: https://[domain]/api/docs
