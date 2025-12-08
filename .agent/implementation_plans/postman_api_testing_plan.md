# TrackerPro Postman API Testing - Implementation Plan

> **Created:** 2025-12-08  
> **Status:** Planning Phase  
> **Author:** Antigravity AI

---

## 📋 Executive Summary

This plan covers the creation of a comprehensive Postman collection for testing **all API endpoints** of the TrackerPro backend. The collection will be organized by functional areas (Authentication, Tasks, Trackers, Analytics, Goals, User Settings, etc.) with proper environment variables, pre-request scripts, and test assertions.

---

## 🔍 Analysis: Current Backend API Structure

### API Routes Overview

Based on analysis of `urls_api_v1.py`, `views_api.py`, and `views_auth.py`:

| Category | Endpoints | Status |
|----------|-----------|--------|
| **Authentication** | 7 endpoints | ✅ Complete |
| **Tasks** | 9 endpoints | ✅ Complete |
| **Trackers** | 7 endpoints | ✅ Complete |
| **Templates** | 1 endpoint | ✅ Complete |
| **Analytics & Insights** | 6 endpoints | ✅ Complete |
| **Goals** | 1 endpoint (GET/POST) | ⚠️ Missing PUT/DELETE |
| **User Settings** | 4 endpoints | ✅ Complete |
| **Data Management** | 3 endpoints | ✅ Complete |
| **User Account** | 2 endpoints | ✅ Complete |
| **Notifications** | 1 endpoint | ✅ Complete |
| **Utility/System** | 8 endpoints | ✅ Complete |

### Identified Gaps

1. **Goals API**: Missing `PUT /api/v1/goals/{goal_id}/` (update) and `DELETE /api/v1/goals/{goal_id}/` (delete)
2. **Goal Details**: Missing `GET /api/v1/goals/{goal_id}/` (single goal fetch)
3. **Goal Progress**: Missing `POST /api/v1/goals/{goal_id}/progress/` (update progress)
4. **Trackers List**: Missing `GET /api/v1/trackers/` (list all trackers for user)
5. **Tracker Details**: Missing `GET /api/v1/tracker/{tracker_id}/` (single tracker fetch)
6. **Task Details**: Missing `GET /api/v1/task/{task_id}/` (single task fetch)
7. **Password Reset**: Missing `POST /api/auth/password-reset/` and `POST /api/auth/password-reset-confirm/`
8. **Day Notes List**: Missing `GET /api/v1/notes/` (list all notes)
9. **Notification Preferences**: Missing granular notification settings

---

## 🗂️ Postman Collection Structure

### 1. **Environment Variables**

```json
{
  "BASE_URL": "http://localhost:8000",
  "API_VERSION": "v1",
  "AUTH_TOKEN": "",
  "REFRESH_TOKEN": "",
  "SESSION_COOKIE": "",
  "USER_EMAIL": "test@example.com",
  "USER_PASSWORD": "TestPass123!",
  "TRACKER_ID": "",
  "TASK_ID": "",
  "GOAL_ID": "",
  "TEMPLATE_ID": ""
}
```

### 2. **Collection Folders**

```
📁 TrackerPro API v1
│
├── 📂 1. Authentication
│   ├── 🔷 POST Login (Email/Password)
│   ├── 🔷 POST Signup
│   ├── 🔷 POST Logout
│   ├── 🔷 GET Check Auth Status
│   ├── 🔷 POST Validate Email Availability
│   ├── 🔷 POST Google Sign-In (Mobile)
│   └── 🔷 POST Apple Sign-In (Mobile)
│
├── 📂 2. Tasks
│   ├── 🔷 POST Toggle Task Status
│   ├── 🔷 POST Set Task Status
│   ├── 🔷 POST Edit Task Details
│   ├── 🔷 POST Delete Task
│   ├── 🔷 POST Bulk Task Actions
│   ├── 🔷 POST Add Task to Tracker (Quick Add)
│   ├── 🔷 GET Infinite Scroll Tasks
│   └── 🔷 POST Bulk Status Update by Filter
│
├── 📂 3. Trackers
│   ├── 🔷 POST Create Tracker
│   ├── 🔷 POST Update Tracker
│   ├── 🔷 POST Delete Tracker
│   ├── 🔷 POST Reorder Tasks
│   ├── 🔷 POST Generate Share Link
│   ├── 🔷 GET Export Tracker Data
│   └── 🔷 POST Mark Overdue as Missed
│
├── 📂 4. Templates
│   └── 🔷 POST Activate Template
│
├── 📂 5. Analytics & Insights
│   ├── 🔷 GET Analytics Dashboard Data
│   ├── 🔷 GET Completion Forecast
│   ├── 🔷 GET Behavioral Insights
│   ├── 🔷 GET Tracker-Specific Insights
│   ├── 🔷 GET Chart Data
│   ├── 🔷 GET Heatmap Data
│   └── 🔷 GET Smart Suggestions
│
├── 📂 6. Goals
│   ├── 🔷 GET List Goals (Paginated)
│   ├── 🔷 POST Create Goal
│   ├── 🔶 PUT Update Goal (MISSING)
│   └── 🔶 DELETE Delete Goal (MISSING)
│
├── 📂 7. User Profile & Settings
│   ├── 🔷 GET User Profile
│   ├── 🔷 PUT Update User Profile
│   ├── 🔷 POST Upload Avatar
│   ├── 🔷 DELETE Remove Avatar
│   ├── 🔷 GET User Preferences
│   └── 🔷 PUT Update User Preferences
│
├── 📂 8. Notifications
│   ├── 🔷 GET List Notifications
│   ├── 🔷 POST Mark Notifications Read
│   └── 🔷 POST Mark All Notifications Read
│
├── 📂 9. Data Management
│   ├── 🔷 POST Export All Data (JSON)
│   ├── 🔷 POST Export All Data (CSV)
│   ├── 🔷 POST Import Data
│   ├── 🔷 POST Clear All Data
│   └── 🔷 DELETE Delete Account
│
├── 📂 10. Utility & System
│   ├── 🔷 GET Global Search
│   ├── 🔷 POST Save Day Note
│   ├── 🔷 POST Undo Action
│   ├── 🔷 POST Validate Field
│   ├── 🔷 GET Prefetch Panel Data
│   ├── 🔷 POST Sync (Offline Actions)
│   ├── 🔷 GET Health Check
│   ├── 🔷 GET Feature Flag
│   └── 🔷 POST Export Month Data
│
└── 📂 11. Workflow Tests
    ├── 🔗 Complete Onboarding Flow
    ├── 🔗 Daily Task Workflow
    ├── 🔗 Create & Complete Tracker
    ├── 🔗 Goal Progress Tracking
    └── 🔗 Data Export & Import
```

---

## 📝 Detailed API Documentation for Postman

### Phase 1: Authentication APIs (7 endpoints)

| # | Method | Endpoint | Description | Auth Required |
|---|--------|----------|-------------|---------------|
| 1 | POST | `/api/v1/auth/login/` | Email/password login | No |
| 2 | POST | `/api/v1/auth/signup/` | New user registration | No |
| 3 | GET/POST | `/api/v1/auth/logout/` | Logout user | Session |
| 4 | GET | `/api/v1/auth/status/` | Check auth status | Any |
| 5 | POST | `/api/v1/auth/validate-email/` | Check email availability | No |
| 6 | POST | `/api/v1/auth/google/` | Google OAuth mobile | No |
| 7 | POST | `/api/v1/auth/apple/mobile/` | Apple Sign-In mobile | No |

### Phase 2: Task APIs (9 endpoints)

| # | Method | Endpoint | Description | Auth Required |
|---|--------|----------|-------------|---------------|
| 1 | POST | `/api/v1/task/{id}/toggle/` | Toggle task status | Yes |
| 2 | POST | `/api/v1/task/{id}/status/` | Set specific status | Yes |
| 3 | POST | `/api/v1/task/{id}/edit/` | Edit task details | Yes |
| 4 | POST | `/api/v1/task/{id}/delete/` | Soft-delete task | Yes |
| 5 | POST | `/api/v1/tasks/bulk/` | Bulk task actions | Yes |
| 6 | POST | `/api/v1/tracker/{id}/task/add/` | Quick add task | Yes |
| 7 | GET | `/api/v1/tasks/infinite/` | Paginated task list | Yes |
| 8 | POST | `/api/v1/tasks/bulk-update/` | Update by filter | Yes |
| 9 | POST | `/api/v1/tracker/{id}/mark-overdue/` | Mark overdue missed | Yes |

### Phase 3: Tracker APIs (7 endpoints)

| # | Method | Endpoint | Description | Auth Required |
|---|--------|----------|-------------|---------------|
| 1 | POST | `/api/v1/tracker/create/` | Create new tracker | Yes |
| 2 | POST | `/api/v1/tracker/{id}/update/` | Update tracker | Yes |
| 3 | POST | `/api/v1/tracker/{id}/delete/` | Delete tracker | Yes |
| 4 | POST | `/api/v1/tracker/{id}/reorder/` | Reorder tasks | Yes |
| 5 | POST | `/api/v1/tracker/{id}/share/` | Generate share link | Yes |
| 6 | GET | `/api/v1/tracker/{id}/export/` | Export tracker data | Yes |
| 7 | POST | `/api/v1/templates/activate/` | Create from template | Yes |

### Phase 4: Analytics & Insights (6 endpoints)

| # | Method | Endpoint | Description | Auth Required |
|---|--------|----------|-------------|---------------|
| 1 | GET | `/api/v1/analytics/data/` | Dashboard analytics | Yes |
| 2 | GET | `/api/v1/analytics/forecast/` | Completion forecast | Yes |
| 3 | GET | `/api/v1/insights/` | All insights | Yes |
| 4 | GET | `/api/v1/insights/{tracker_id}/` | Tracker insights | Yes |
| 5 | GET | `/api/v1/chart-data/` | Chart-ready data | Yes |
| 6 | GET | `/api/v1/heatmap/` | Heatmap data | Yes |

### Phase 5: Goals API (1 endpoint, multiple methods)

| # | Method | Endpoint | Description | Auth Required |
|---|--------|----------|-------------|---------------|
| 1 | GET | `/api/v1/goals/` | List goals (paginated) | Yes |
| 2 | POST | `/api/v1/goals/` | Create goal | Yes |

### Phase 6: User & Settings APIs (4 endpoints)

| # | Method | Endpoint | Description | Auth Required |
|---|--------|----------|-------------|---------------|
| 1 | GET/PUT | `/api/v1/user/profile/` | User profile CRUD | Yes |
| 2 | POST/DELETE | `/api/v1/user/avatar/` | Avatar management | Yes |
| 3 | GET/PUT | `/api/v1/preferences/` | User preferences | Yes |
| 4 | DELETE | `/api/v1/user/delete/` | Delete account | Yes |

### Phase 7: Notifications API (1 endpoint)

| # | Method | Endpoint | Description | Auth Required |
|---|--------|----------|-------------|---------------|
| 1 | GET/POST | `/api/v1/notifications/` | List/manage notifications | Yes |

### Phase 8: Data Management APIs (3 endpoints)

| # | Method | Endpoint | Description | Auth Required |
|---|--------|----------|-------------|---------------|
| 1 | POST | `/api/v1/data/export/` | Export all data | Yes |
| 2 | POST | `/api/v1/data/import/` | Import data | Yes |
| 3 | POST | `/api/v1/data/clear/` | Clear all data | Yes |

### Phase 9: Utility APIs (8 endpoints)

| # | Method | Endpoint | Description | Auth Required |
|---|--------|----------|-------------|---------------|
| 1 | GET | `/api/v1/search/` | Global search | No |
| 2 | POST | `/api/v1/notes/{date}/` | Save day note | Yes |
| 3 | POST | `/api/v1/undo/` | Undo action | Yes |
| 4 | POST | `/api/v1/validate/` | Field validation | Yes |
| 5 | GET | `/api/v1/prefetch/` | Prefetch data | Yes |
| 6 | GET | `/api/v1/suggestions/` | Smart suggestions | Yes |
| 7 | POST | `/api/v1/sync/` | Offline sync | Yes |
| 8 | GET | `/api/v1/health/` | Health check | No |
| 9 | GET | `/api/v1/feature-flags/{flag}/` | Feature flag | Yes |
| 10 | POST | `/api/v1/export/month/` | Export month data | Yes |

---

## ⚠️ Identified Gaps & Recommendations

### Critical Missing Endpoints

| Priority | Missing Endpoint | Purpose | Action Required |
|----------|------------------|---------|-----------------|
| **HIGH** | `PUT /api/v1/goals/{id}/` | Update goal | Add to views_api.py |
| **HIGH** | `DELETE /api/v1/goals/{id}/` | Delete goal | Add to views_api.py |
| **HIGH** | `GET /api/v1/goals/{id}/` | Get single goal | Add to views_api.py |
| **MEDIUM** | `GET /api/v1/trackers/` | List trackers | Add to views_api.py |
| **MEDIUM** | `GET /api/v1/tracker/{id}/` | Get tracker details | Add to views_api.py |
| **MEDIUM** | `GET /api/v1/task/{id}/` | Get task details | Add to views_api.py |
| **LOW** | `POST /api/auth/password-reset/` | Password reset | Add to views_auth.py |
| **LOW** | `GET /api/v1/notes/` | List day notes | Add to views_api.py |
| **LOW** | `POST /api/v1/goals/{id}/progress/` | Update goal progress | Add to views_api.py |

### Workflow Gaps per Page

#### 1. Dashboard Page
- ✅ `/api/v1/suggestions/` - Smart suggestions  
- ✅ `/api/v1/prefetch/` - Prefetch panel data
- ⚠️ Missing: `GET /api/v1/trackers/` - List all trackers

#### 2. Today View
- ✅ `/api/v1/tasks/infinite/` - Task list
- ✅ `/api/v1/task/{id}/toggle/` - Toggle tasks
- ✅ `/api/v1/notes/{date}/` - Day notes
- ✅ Complete

#### 3. Tracker Detail Page
- ✅ Task operations complete
- ⚠️ Missing: `GET /api/v1/tracker/{id}/` - Get tracker details
- ⚠️ Missing: `GET /api/v1/tracker/{id}/stats/` - Tracker statistics

#### 4. Analytics Page
- ✅ `/api/v1/analytics/data/` - Full analytics
- ✅ `/api/v1/analytics/forecast/` - Predictions
- ✅ `/api/v1/heatmap/` - Heatmap data
- ✅ Complete

#### 5. Goals Page
- ✅ `GET /api/v1/goals/` - List goals
- ⚠️ Missing: `GET/PUT/DELETE /api/v1/goals/{id}/` - Goal CRUD

#### 6. Settings Page
- ✅ `/api/v1/user/profile/` - Profile
- ✅ `/api/v1/preferences/` - Preferences
- ✅ `/api/v1/user/avatar/` - Avatar
- ✅ Complete

---

## 📁 Deliverables

### Files to Create

1. **`/TrackerPro_Postman_Collection.json`** - Complete Postman collection
2. **`/TrackerPro_Postman_Environment.json`** - Environment variables
3. **`/apisTesting.md`** (UPDATE) - Add missing API documentation
4. **Missing API Endpoints** (if opted to implement)

### Postman Collection Features

- ✅ Pre-request scripts for authentication
- ✅ Test assertions for all responses
- ✅ Environment variable extraction
- ✅ Workflow request chaining
- ✅ Example request/response pairs
- ✅ Descriptive endpoint documentation

---

## 🔧 Implementation Steps

### Step 1: Create Postman Environment File
- Define all environment variables
- Include local, staging, and production URLs

### Step 2: Create Authentication Folder
- Login request with token extraction
- Auto-set AUTH_TOKEN for subsequent requests

### Step 3: Create CRUD Folders
- Tasks, Trackers, Goals, Settings
- Include all request variations

### Step 4: Create Analytics Folder
- All analytics endpoints with query params

### Step 5: Create Workflow Tests
- End-to-end test sequences
- Request chaining with variable passing

### Step 6: Add Missing Endpoints (Optional)
- Implement missing Goal endpoints
- Implement missing Tracker listing endpoint

---

## ✅ Approval Checklist

Before proceeding to file creation:

- [ ] Review collection structure
- [ ] Confirm which gaps to fill (implement missing endpoints?)
- [ ] Confirm environment variable naming
- [ ] Confirm test assertion depth (basic vs comprehensive)

---

## Next Steps

**Option A:** Create Postman Collection files only (use existing endpoints)

**Option B:** Create Postman Collection + Implement missing API endpoints

**Please confirm which option you prefer, and I'll proceed with file creation.**
