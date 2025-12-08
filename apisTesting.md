# TrackerPro API Testing Guide

> **Last Updated:** 2025-12-08  
> **API Version:** v1  
> **Base URL:** `https://your-domain.com/api/v1/`

---

## Table of Contents
1. [Authentication APIs](#authentication-apis)
2. [Task APIs](#task-apis)
3. [Tracker APIs](#tracker-apis)
4. [Analytics & Insights APIs](#analytics--insights-apis)
5. [User Settings APIs](#user-settings-apis)
6. [Data Management APIs](#data-management-apis)
7. [Utility APIs](#utility-apis)
8. [Product Review & Recommendations](#product-review--recommendations)

---

## 🔐 Authentication APIs

### POST `/auth/login/`
**Purpose:** Log in user with email/password

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "remember": true
}
```

**Response:**
```json
{
  "success": true,
  "redirect": "/",
  "user": {
    "email": "user@example.com",
    "username": "user"
  }
}
```

**Rate Limit:** 5 attempts per 5 minutes

**✅ Product Review:** Good implementation with rate limiting. Consider adding:
- Account lockout after N failed attempts
- Remember device option for 2FA
- Password strength indicator on signup

---

### POST `/auth/signup/`
**Purpose:** Register new user

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password1": "securePass123!",
  "password2": "securePass123!"
}
```

**Response:**
```json
{
  "success": true,
  "redirect": "/",
  "user": {
    "email": "newuser@example.com",
    "username": "newuser"
  }
}
```

**Rate Limit:** 3 signups per hour

**✅ Product Review:** Good validation. Missing:
- Email verification flow
- Terms of service acceptance checkbox
- Optional referral code field

---

### POST `/auth/logout/`
**Purpose:** Log out current user

**Headers Required:** Session/Cookie authentication

**Response:**
```json
{
  "success": true,
  "redirect": "/accounts/login/"
}
```

---

### GET `/auth/status/`
**Purpose:** Check authentication status

**Response (authenticated):**
```json
{
  "authenticated": true,
  "user": {
    "email": "user@example.com",
    "username": "user"
  }
}
```

**Response (unauthenticated):**
```json
{
  "authenticated": false
}
```

---

### POST `/auth/validate-email/`
**Purpose:** Real-time email availability check

**Request Body:**
```json
{
  "email": "test@example.com"
}
```

**Response:**
```json
{
  "available": true,
  "message": "Email available."
}
```

---

### POST `/auth/google/mobile/`
**Purpose:** Google Sign-In for iOS/mobile apps

**Request Body:**
```json
{
  "idToken": "eyJhbGciOiJSUzI1..."
}
```

**✅ Product Review:** Properly validates Google token. Consider adding:
- Token refresh handling
- Profile picture sync from Google

---

### POST `/auth/apple/mobile/`
**Purpose:** Apple Sign-In for iOS apps

**Request Body:**
```json
{
  "idToken": "eyJhbGciOiJSUzI1...",
  "first_name": "John",
  "last_name": "Doe"
}
```

**⚠️ Note:** Apple only sends name on first authorization. Store it immediately.

---

## ✅ Task APIs

### POST `/task/{task_id}/toggle/`
**Purpose:** Toggle task status (TODO → DONE → SKIPPED)

**Response:**
```json
{
  "success": true,
  "message": "Task done",
  "data": {
    "task_id": "uuid",
    "old_status": "TODO",
    "new_status": "DONE",
    "undo": {...}
  },
  "feedback": {
    "type": "success",
    "message": "Great job! ✓",
    "haptic": "success",
    "animation": "checkmark",
    "toast": true
  },
  "stats_delta": {
    "remaining_tasks": 4,
    "all_complete": false,
    "tracker_id": "uuid"
  }
}
```

**✅ Product Review:** Excellent UX feedback with:
- Haptic feedback types for iOS
- Celebration animation when all tasks complete
- Undo support

---

### POST `/task/{task_id}/status/`
**Purpose:** Set specific status with optional notes

**Request Body:**
```json
{
  "status": "DONE",
  "notes": "Completed early today"
}
```

**Valid statuses:** `TODO`, `IN_PROGRESS`, `DONE`, `SKIPPED`, `MISSED`, `BLOCKED`

---

### POST `/task/{task_id}/edit/`
**Purpose:** Full task editing

**Request Body:**
```json
{
  "description": "Updated task description",
  "category": "work",
  "weight": 3,
  "time_of_day": "morning"
}
```

---

### POST `/task/{task_id}/delete/`
**Purpose:** Soft-delete a task

**Response includes undo_data for restoration**

---

### POST `/tasks/bulk/`
**Purpose:** Bulk actions on multiple tasks

**Request Body:**
```json
{
  "action": "complete",
  "task_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Valid actions:** `complete`, `skip`, `pending`, `delete`

**✅ Product Review:** Good for batch operations. Consider adding:
- Progress indicator for large batches
- Partial success handling

---

### GET `/tasks/infinite/`
**Purpose:** Cursor-based paginated task list for infinite scroll

**Query Params:**
- `cursor`: ISO datetime cursor
- `limit`: Items per page (default: 20, max: 100)
- `tracker_id`: Filter by tracker
- `status`: Filter by status
- `period`: `today`, `week`, `month`, `all`

**Response:**
```json
{
  "success": true,
  "items": [...],
  "pagination": {
    "has_more": true,
    "next_cursor": "2024-12-07T10:30:00Z"
  },
  "meta": {
    "period": "today",
    "limit": 20
  }
}
```

**✅ Product Review:** Modern cursor pagination is excellent for mobile apps. Better than offset pagination for realtime data.

---

## 📊 Tracker APIs

### POST `/tracker/create/`
**Purpose:** Create new tracker

**Request Body:**
```json
{
  "name": "Morning Routine",
  "description": "Daily morning habits",
  "time_mode": "daily",
  "tasks": [
    {
      "description": "Wake up at 6AM",
      "category": "routine",
      "weight": 2,
      "time_of_day": "morning"
    }
  ]
}
```

**time_mode options:** `daily`, `weekly`, `monthly`

---

### POST `/tracker/{tracker_id}/update/`
**Purpose:** Update tracker details

**Request Body:**
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "status": "active"
}
```

---

### POST `/tracker/{tracker_id}/delete/`
**Purpose:** Soft-delete a tracker

---

### POST `/tracker/{tracker_id}/task/add/`
**Purpose:** Quick add task to tracker

**Request Body:**
```json
{
  "description": "New task",
  "category": "work",
  "weight": 1,
  "time_of_day": "afternoon"
}
```

---

### POST `/tracker/{tracker_id}/reorder/`
**Purpose:** Reorder tasks via drag-and-drop

**Request Body:**
```json
{
  "order": ["task_uuid_1", "task_uuid_3", "task_uuid_2"]
}
```

---

### POST `/tracker/{tracker_id}/share/`
**Purpose:** Generate share link for tracker

**Response:**
```json
{
  "success": true,
  "data": {
    "share_url": "https://app.com/shared/abc123/",
    "token": "abc123"
  }
}
```

---

### GET `/tracker/{tracker_id}/export/`
**Purpose:** Export tracker data

**Query Params:**
- `format`: `csv` or `json` (default: csv)
- `start`: ISO date
- `end`: ISO date

---

### POST `/templates/activate/`
**Purpose:** Create tracker from predefined template

**Request Body:**
```json
{
  "template_key": "morning"
}
```

**Available templates:**
- `morning` - Morning Routine (8 tasks)
- `fitness` - Fitness Tracker (6 tasks)
- `study` - Study Plan (5 tasks)
- `work` - Work Productivity (7 tasks)
- `mindfulness` - Mindfulness (4 tasks)
- `evening` - Evening Wind Down (5 tasks)
- `weekly-review` - Weekly Review (6 tasks)
- `language` - Language Learning (5 tasks)

**Response:**
```json
{
  "success": true,
  "message": "Created \"Morning Routine\" tracker",
  "data": {
    "tracker_id": "uuid",
    "tracker_name": "Morning Routine",
    "task_count": 8
  }
}
```

**✅ Product Review:** Great for onboarding! Consider adding:
- Template preview before activation
- Customization options (e.g., skip certain tasks)
- "Most Popular" badge on templates

---

## 📈 Analytics & Insights APIs

### GET `/analytics/data/`
**Purpose:** Comprehensive analytics dashboard data

**Query Params:**
- `days`: Number of days (1-365, default: 30)
- `tracker_id`: Optional tracker filter

**Response:**
```json
{
  "success": true,
  "data": {
    "completion_trend": {
      "labels": ["Dec 1", "Dec 2", ...],
      "data": [85.5, 90.0, ...],
      "dates": ["2024-12-01", ...]
    },
    "category_distribution": {
      "labels": ["Work", "Health", ...],
      "data": [35.5, 25.0, ...],
      "counts": [150, 100, ...]
    },
    "time_of_day": {
      "labels": ["Morning", "Afternoon", "Evening", "Night"],
      "data": [45, 65, 40, 15]
    },
    "heatmap": [...],
    "insights": [
      {
        "type": "pattern",
        "icon": "📅",
        "title": "Best Day",
        "message": "You're most productive on Tuesdays"
      }
    ],
    "summary": {...}
  }
}
```

**✅ Product Review:** Excellent Chart.js-ready data format. Consider:
- Caching for heavy analytics queries
- Background precomputation (already implemented)

---

### GET `/analytics/forecast/`
**Purpose:** Completion rate predictions

**Query Params:**
- `days`: Days to forecast (1-30, default: 7)
- `history_days`: Historical window (7-365, default: 30)
- `tracker_id`: Optional filter

**Response:**
```json
{
  "success": true,
  "forecast": {
    "predictions": [85.2, 86.1, ...],
    "upper_bound": [90.5, 91.2, ...],
    "lower_bound": [79.9, 81.0, ...],
    "confidence": 0.85,
    "trend": "increasing",
    "dates": ["2024-12-08", ...],
    "labels": ["Dec 8", ...]
  },
  "summary": {
    "message": "Your completion rate is trending increasing...",
    "recommendation": "Keep up the momentum!",
    "predicted_change": 5.2
  }
}
```

**✅ Product Review:** Behavioral insights integrated! Uses numpy-only (no scipy) for serverless compatibility.

---

### GET `/insights/`
### GET `/insights/{tracker_id}/`
**Purpose:** Behavioral insights

**Response:**
```json
{
  "success": true,
  "insights": [
    {
      "type": "weekend_dip",
      "severity": "medium",
      "title": "Weekend Completion Dip",
      "message": "Your completion drops 25% on weekends",
      "suggestion": "Consider lighter weekend goals",
      "tracker_name": "Morning Routine",
      "tracker_id": "uuid"
    }
  ],
  "count": 5
}
```

---

### GET `/chart-data/`
**Purpose:** Chart-specific data

**Query Params:**
- `type`: `bar`, `line`, `pie`, `completion`
- `tracker_id`: Optional filter
- `days`: Timeframe (default: 30)

---

### GET `/heatmap/`
**Purpose:** GitHub-style contribution heatmap

**Query Params:**
- `tracker_id`: Optional filter
- `weeks`: Number of weeks (default: 12)

**Response:**
```json
{
  "success": true,
  "heatmap": [
    [
      {"date": "2024-10-01", "level": 3, "count": 8, "total": 10, "rate": 80},
      ...
    ],
    ...
  ]
}
```

**Level scale:** 0 (no activity) → 4 (high activity)

---

### GET `/suggestions/`
**Purpose:** Smart suggestions based on behavior patterns

**Response:**
```json
{
  "success": true,
  "suggestions": [
    {
      "type": "best_day",
      "icon": "📅",
      "message": "You're most productive on Mondays",
      "detail": "85 tasks completed",
      "action": null
    },
    {
      "type": "streak",
      "icon": "🔥",
      "message": "You're on a 7-day streak!",
      "detail": "Keep it going",
      "action": {"label": "View Stats", "url": "/analytics/"}
    }
  ]
}
```

---

## ⚙️ User Settings APIs

### GET/PUT `/preferences/`
**Purpose:** User preferences management

**GET Response:**
```json
{
  "success": true,
  "preferences": {
    "theme": "dark",
    "default_view": "today",
    "timezone": "Asia/Kolkata",
    "date_format": "DD/MM/YYYY",
    "week_start": 1,
    "daily_reminder_enabled": true,
    "sound_complete": true,
    "sound_notify": false,
    "sound_volume": 80,
    "compact_mode": false,
    "animations": true,
    "keyboard_enabled": true,
    "push_enabled": true
  }
}
```

**PUT Request Body (partial update):**
```json
{
  "theme": "light",
  "animations": false
}
```

---

### GET/PUT `/user/profile/`
**Purpose:** User profile management

**GET Response:**
```json
{
  "success": true,
  "profile": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "username": "johndoe",
    "timezone": "Asia/Kolkata",
    "date_format": "DD/MM/YYYY",
    "week_start": 1
  }
}
```

**PUT Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Smith",
  "email": "john.smith@example.com"
}
```

---

### POST/DELETE `/user/avatar/`
**Purpose:** Avatar upload/removal

**POST:** Multipart form with `avatar` file (JPEG, PNG, GIF, WebP; max 5MB)

**Response:**
```json
{
  "success": true,
  "avatar_url": "/media/avatars/user_123.jpg"
}
```

---

### GET/POST `/notifications/`
**Purpose:** Notification management

**GET Response:**
```json
{
  "success": true,
  "notifications": [
    {
      "notification_id": "uuid",
      "type": "achievement",
      "title": "7-Day Streak!",
      "message": "You've completed tasks 7 days in a row!",
      "link": "/analytics/",
      "is_read": false,
      "created_at": "2024-12-08T10:00:00Z"
    }
  ],
  "unread_count": 3
}
```

**POST (mark as read):**
```json
{
  "action": "mark_read",
  "ids": ["uuid1", "uuid2"]
}
```

```json
{
  "action": "mark_all_read"
}
```

---

### GET/POST `/goals/`
**Purpose:** Goals management with pagination

**Query Params (GET):**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `status`: `active`, `completed`, `archived`, `all`
- `sort`: `created_at`, `-created_at`, `priority`, `progress`, `target_date`

**POST Request Body:**
```json
{
  "title": "Run a marathon",
  "description": "Complete a full 42km marathon",
  "goal_type": "achievement",
  "target_date": "2025-06-01",
  "target_value": 42,
  "unit": "km",
  "icon": "🏃"
}
```

---

## 💾 Data Management APIs

### POST `/data/export/`
**Purpose:** Export all user data

**Request Body:**
```json
{
  "format": "json"
}
```

**Valid formats:** `json`, `csv`

**Response:** File download

---

### POST `/data/import/`
**Purpose:** Import data from JSON file

**Request:** Multipart form with JSON file

**Response:**
```json
{
  "success": true,
  "message": "Imported 5 trackers with 32 tasks",
  "imported_trackers": 5,
  "imported_tasks": 32
}
```

---

### POST `/data/clear/`
**Purpose:** Clear all user data (DESTRUCTIVE)

**Request Body:**
```json
{
  "confirmation": "DELETE ALL DATA"
}
```

**⚠️ Warning:** This soft-deletes all trackers and goals.

---

### DELETE `/user/delete/`
**Purpose:** Permanently delete account (IRREVERSIBLE)

**Request Body:**
```json
{
  "confirmation": "DELETE MY ACCOUNT",
  "password": "user_current_password"
}
```

---

## 🛠 Utility APIs

### POST `/sync/`
**Purpose:** Bidirectional sync for offline-first mobile apps

**Request Body:**
```json
{
  "last_sync": "2024-12-07T10:00:00Z",
  "device_id": "iOS-ABC123",
  "pending_actions": [
    {
      "action_type": "toggle_task",
      "entity_id": "task_uuid",
      "timestamp": "2024-12-07T09:55:00Z",
      "data": {"new_status": "DONE"}
    }
  ]
}
```

**Response:**
```json
{
  "sync_status": "complete",
  "action_results": [...],
  "server_changes": {...},
  "new_sync_timestamp": "2024-12-08T10:00:00Z"
}
```

---

### GET `/prefetch/`
**Purpose:** Prefetch data for SPA navigation

**Query Params:**
- `panels`: Comma-separated (default: `today,dashboard`)

**Response:**
```json
{
  "success": true,
  "data": {
    "today": {
      "total_count": 12,
      "done_count": 5,
      "pending_count": 7
    },
    "dashboard": {
      "tracker_count": 4,
      "has_tasks_today": true
    }
  }
}
```

---

### POST `/validate/`
**Purpose:** Real-time field validation

**Request Body:**
```json
{
  "field": "tracker_name",
  "value": "Morning Routine"
}
```

**Response:**
```json
{
  "valid": true,
  "errors": []
}
```

**Supported fields:** `tracker_name`, `task_description`

---

### POST `/undo/`
**Purpose:** Undo last action

**Request Body:**
```json
{
  "type": "task_toggle",
  "data": {
    "task_id": "uuid",
    "old_status": "TODO"
  }
}
```

---

### GET `/search/`
**Purpose:** Global search

**Query Params:**
- `q`: Search query
- `save`: `true`/`false` (save to history)

**Response:**
```json
{
  "trackers": [...],
  "tasks": [...],
  "commands": [
    {"shortcut": "Ctrl+N", "label": "New Tracker", "action": "modal", "url": "/modals/add-tracker/"}
  ]
}
```

---

### GET `/health/`
**Purpose:** Health check for load balancers

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-08T10:00:00Z",
  "version": "1.0.0",
  "checks": {
    "database": {"status": "ok", "latency_ms": 2.5},
    "cache": {"status": "ok", "latency_ms": 0.8}
  }
}
```

---

### GET `/feature-flags/{flag_name}/`
**Purpose:** Check feature flag status

**Response:**
```json
{
  "enabled": true,
  "flag": "behavioral_insights"
}
```

**Available flags:**
- `behavioral_insights`
- `export`
- `undo`
- `pagination`
- `offline`

---

## 📋 Product Review & Recommendations

### ✅ What's Good

1. **Authentication**
   - Proper rate limiting on sensitive endpoints
   - Social login support (Google, Apple)
   - CSRF exemption for mobile clients

2. **API Design**
   - RESTful conventions followed
   - Consistent response format with `success` boolean
   - UXResponse wrapper with haptic/animation feedback

3. **Performance**
   - Cursor-based pagination for infinite scroll
   - Prefetch endpoint for SPA optimization
   - ETag support for conditional requests
   - Background analytics precomputation

4. **Data Safety**
   - Soft-delete pattern (recoverable data)
   - Confirmation strings for destructive actions
   - Transaction wrapping for multi-step operations

5. **Mobile/Offline Support**
   - Sync endpoint for offline-first apps
   - Device ID tracking
   - Conflict detection

### ⚠️ Issues Found & Fixed

1. **❌ `/api/v1/analytics/forecast/` → 500 Error**
   - **Cause:** `scipy` dependency not installed on serverless
   - **Fix:** Rewrote `forecast_service.py` to use numpy-only

2. **❌ `/api/v1/templates/activate/` → 500 Error**
   - **Cause:** Missing CSRF exemption for mobile clients
   - **Fix:** Added `@csrf_exempt` decorator and improved error logging

3. **❌ `analytics.py` visualization functions → Crash**
   - **Cause:** Referenced undefined `sns`, `plt` variables
   - **Fix:** Replaced matplotlib functions with data-only returns for frontend rendering

### ❓ Missing Features to Consider

1. **Push Notifications API**
   - Register/unregister device tokens
   - Notification preferences per type

2. **Batch/Bulk APIs**
   - `POST /trackers/bulk-delete/`
   - `POST /tasks/batch-create/`

3. **Webhook/Integration APIs**
   - Zapier/Make.com integration
   - Calendar sync (Google Calendar, Apple Calendar)

4. **Analytics Enhancements**
   - Export analytics to PDF
   - Email weekly reports
   - Compare time periods (this week vs last week)

5. **Social Features**
   - Share tracker as template
   - Leaderboards (opt-in)
   - Accountability partners

### 📱 iOS/React/Vue App Recommendations

1. **Optimistic Updates**
   - Toggle task immediately, sync in background
   - Show undo toast for 5 seconds

2. **Caching Strategy**
   - Cache `/prefetch/` response locally
   - Use ETag for conditional updates
   - Implement 5-minute stale-while-revalidate

3. **Offline Queue**
   - Store actions in local storage
   - Retry with exponential backoff
   - Handle conflicts gracefully (server wins)

4. **Error Handling**
   - Show inline errors for validation (400)
   - Show toast for server errors (500)
   - Retry mechanism for network failures

5. **Performance**
   - Use infinite scroll, not pagination
   - Preload adjacent panels
   - Debounce validation requests

---

## 🧪 Postman Collection Setup

### Environment Variables
```
BASE_URL: https://your-domain.com
API_VERSION: v1
SESSION_COOKIE: (auto-populated after login)
```

### Auth Flow
1. Call `POST /api/v1/auth/login/` with credentials
2. Copy session cookie from response headers
3. All subsequent requests automatically authenticated

### Testing Tips
- Use `{{BASE_URL}}/api/{{API_VERSION}}/` in request URLs
- Set `Content-Type: application/json` header
- For file uploads, use `multipart/form-data`

---

*Document generated: 2025-12-08*
