# Tracker Pro API v1 Documentation

> **Base URL**: `http://127.0.0.1:8000/api/v1/`  
> **Version**: 1.0  
> **Last Updated**: 2025-12-08

## Table of Contents

1. [Authentication](#authentication)
2. [Dashboard Endpoints](#dashboard-endpoints)
3. [Tracker Endpoints](#tracker-endpoints)
4. [Task Endpoints](#task-endpoints)
5. [Goals API](#goals-api)
6. [Analytics & Insights](#analytics--insights)
7. [User Profile & Settings](#user-profile--settings)
8. [Data Management](#data-management)
9. [Utility Endpoints](#utility-endpoints)
10. [Points & Goals System](#points--goals-system)
11. [System Endpoints](#system-endpoints)
12. [Error Handling](#error-handling)
13. [Testing Checklist](#testing-checklist)

---

## Authentication

All endpoints (except auth and health) require authentication via either:

1. **Session Auth** (Browser): Include CSRF token from cookies
2. **JWT Bearer Token** (Mobile/API): `Authorization: Bearer <token>`

### Auth Endpoints

#### POST `/api/v1/auth/login/`

Login with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "remember": true
}
```

**Response (200):**
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

**Response (400):**
```json
{
  "success": false,
  "errors": {
    "email": ["Invalid email or password."]
  }
}
```

**Rate Limit**: 5 attempts per 5 minutes

---

#### POST `/api/v1/auth/signup/`

Create a new account.

**Request:**
```json
{
  "email": "newuser@example.com",
  "password1": "securepassword123",
  "password2": "securepassword123"
}
```

**Response (200):**
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

**Validation Errors:**
- Email already registered
- Passwords don't match
- Password too short (min 8 chars)

**Rate Limit**: 3 signups per hour

---

#### POST `/api/v1/auth/logout/`

Logout current user.

**Response:**
```json
{
  "success": true,
  "redirect": "/accounts/login/"
}
```

---

#### GET `/api/v1/auth/status/`

Check current authentication status.

**Response (Authenticated):**
```json
{
  "authenticated": true,
  "user": {
    "email": "user@example.com",
    "username": "user"
  }
}
```

**Response (Not Authenticated):**
```json
{
  "authenticated": false
}
```

---

#### POST `/api/v1/auth/validate-email/`

Check if email is available for registration.

**Request:**
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

#### POST `/api/v1/auth/google/`

Authenticate with Google ID token (mobile).

**Request:**
```json
{
  "id_token": "<google_id_token>"
}
```

**Response:**
```json
{
  "token": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "name": "John Doe",
    "username": "john"
  }
}
```

---

#### POST `/api/v1/auth/apple/mobile/`

Authenticate with Apple ID token (iOS).

**Request:**
```json
{
  "idToken": "<apple_id_token>",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:**
```json
{
  "success": true,
  "redirect": "/",
  "user": {
    "email": "user@icloud.com",
    "username": "user"
  }
}
```

---

## Dashboard Endpoints

### GET `/api/v1/dashboard/`

Get complete dashboard data in one call.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `date` | string | No | Target date in YYYY-MM-DD format |

**Response:**
```json
{
  "success": true,
  "greeting": "Good morning, John!",
  "date": "2025-12-08",
  "trackers": [...],
  "today_stats": {
    "total": 10,
    "completed": 7,
    "completion_rate": 70.0
  },
  "goals": [...],
  "streaks": {
    "current": 5,
    "longest": 12
  },
  "recent_activity": [...],
  "notifications_count": 3,
  "suggestions": [...]
}
```

---

### GET `/api/v1/dashboard/trackers/`

Get all trackers with their tasks for today.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `date` | string | No | Target date in YYYY-MM-DD format |

**Response:**
```json
{
  "success": true,
  "date": "2025-12-08",
  "trackers": [
    {
      "tracker_id": "uuid",
      "name": "Daily Habits",
      "tasks": [...],
      "completion_rate": 80.0,
      "points_earned": 8,
      "points_total": 10
    }
  ],
  "count": 2
}
```

---

### GET `/api/v1/dashboard/today/`

Get today's aggregated stats only.

**Response:**
```json
{
  "success": true,
  "date": "2025-12-08",
  "total_tasks": 15,
  "completed": 10,
  "in_progress": 2,
  "todo": 2,
  "missed": 1,
  "completion_rate": 66.7,
  "points_earned": 35,
  "points_possible": 50
}
```

---

### GET `/api/v1/dashboard/week/`

Get week overview with day-by-day breakdown.

**Response:**
```json
{
  "success": true,
  "week_start": "2025-12-02",
  "week_end": "2025-12-08",
  "days": [
    {
      "date": "2025-12-02",
      "completed": 8,
      "total": 10,
      "completion_rate": 80.0
    }
  ],
  "week_totals": {
    "completed": 55,
    "total": 70,
    "average_rate": 78.5
  }
}
```

---

### GET `/api/v1/dashboard/goals/`

Get active goals summary for dashboard.

**Response:**
```json
{
  "success": true,
  "goals": [
    {
      "goal_id": "uuid",
      "title": "Lose 5 kg",
      "progress": 45.0,
      "status": "active",
      "target_date": "2025-12-31"
    }
  ],
  "count": 3
}
```

---

### GET `/api/v1/dashboard/streaks/`

Get streak information.

**Response:**
```json
{
  "success": true,
  "current_streak": 5,
  "longest_streak": 12,
  "threshold": 80,
  "days_meeting_threshold": 25
}
```

---

### GET `/api/v1/dashboard/activity/`

Get recent activity feed.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `limit` | integer | No | Number of items (default 10, max 50) |

**Response:**
```json
{
  "success": true,
  "activities": [
    {
      "id": "uuid",
      "type": "task_completed",
      "description": "Completed 'Exercise'",
      "timestamp": "2025-12-08T14:30:00Z",
      "tracker_name": "Daily Habits"
    }
  ]
}
```

---

## Tracker Endpoints

### GET `/api/v1/trackers/`

Get list of all user's trackers.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | No | Filter: 'active', 'paused', 'archived', 'all' |
| `include_deleted` | boolean | No | Include soft-deleted trackers |

**Response:**
```json
{
  "success": true,
  "trackers": [
    {
      "tracker_id": "uuid",
      "name": "Daily Habits",
      "description": "My daily routine",
      "time_mode": "daily",
      "status": "active",
      "target_points": 50,
      "goal_period": "daily",
      "template_count": 5,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-12-08T10:00:00Z"
    }
  ],
  "count": 2
}
```

---

### GET `/api/v1/tracker/<tracker_id>/`

Get detailed information about a specific tracker.

**Response:**
```json
{
  "success": true,
  "tracker": {
    "tracker_id": "uuid",
    "name": "Daily Habits",
    "description": "My daily routine",
    "time_mode": "daily",
    "status": "active",
    "target_points": 50,
    "goal_period": "daily",
    "goal_start_day": 0,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-12-08T10:00:00Z"
  },
  "templates": [
    {
      "template_id": "uuid",
      "description": "Exercise",
      "category": "Health",
      "weight": 5,
      "points": 10,
      "include_in_goal": true,
      "is_recurring": true,
      "time_of_day": "morning"
    }
  ],
  "template_count": 5
}
```

---

### POST `/api/v1/tracker/create/`

Create a new tracker.

**Request:**
```json
{
  "name": "My New Tracker",
  "description": "Optional description",
  "time_mode": "daily",
  "target_points": 50,
  "goal_period": "daily",
  "goal_start_day": 0
}
```

**Validation:**
- `name`: Required, min 3 characters, max 200
- `time_mode`: 'daily', 'weekly', or 'monthly'
- `goal_period`: 'daily', 'weekly', or 'custom'
- `goal_start_day`: 0-6 (Monday-Sunday)

**Response:**
```json
{
  "success": true,
  "tracker_id": "uuid",
  "message": "Tracker created successfully"
}
```

---

### PUT `/api/v1/tracker/<tracker_id>/update/`

Update tracker details.

**Request:**
```json
{
  "name": "Updated Name",
  "description": "New description",
  "status": "active"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Tracker updated successfully"
}
```

---

### DELETE `/api/v1/tracker/<tracker_id>/delete/`

Soft-delete a tracker.

**Response:**
```json
{
  "success": true,
  "message": "Tracker deleted successfully",
  "undo": {
    "action_id": "undo_abc123",
    "expires_in": 30
  }
}
```

---

### POST `/api/v1/tracker/<tracker_id>/task/add/`

Add a new task to a tracker.

**Request:**
```json
{
  "description": "New task",
  "category": "Health",
  "weight": 5,
  "points": 10,
  "include_in_goal": true,
  "is_recurring": true
}
```

**Validation:**
- `description`: Required, min 2 characters, max 500
- `weight`: 1-10

**Response:**
```json
{
  "success": true,
  "template_id": "uuid",
  "message": "Task added successfully"
}
```

---

### POST `/api/v1/tracker/<tracker_id>/reorder/`

Reorder tasks in a tracker.

**Request:**
```json
{
  "order": ["template_id_1", "template_id_2", "template_id_3"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Tasks reordered"
}
```

---

### POST `/api/v1/tracker/<tracker_id>/share/`

Generate a share link for the tracker.

**Request:**
```json
{
  "permission": "view",
  "expires_days": 7,
  "password": "optional_password"
}
```

**Response:**
```json
{
  "success": true,
  "share_url": "https://example.com/share/abc123",
  "token": "abc123",
  "expires_at": "2025-12-15T00:00:00Z"
}
```

---

### GET `/api/v1/tracker/<tracker_id>/export/`

Export tracker data.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `format` | string | No | 'json', 'csv', 'xlsx' (default: json) |
| `start_date` | string | No | Start date YYYY-MM-DD |
| `end_date` | string | No | End date YYYY-MM-DD |

**Response:**
Returns file download or JSON data.

---

### POST `/api/v1/templates/activate/`

Create a tracker from a predefined template.

**Request:**
```json
{
  "template_key": "morning"
}
```

**Available Templates:**
- `morning` - Morning Routine
- `evening` - Evening Routine
- `fitness` - Fitness Tracker
- `mindfulness` - Mindfulness & Wellness
- `productivity` - Productivity Habits
- `learning` - Learning Goals
- `health` - Health & Nutrition
- `finance` - Financial Habits

**Response:**
```json
{
  "success": true,
  "tracker_id": "uuid",
  "message": "Morning Routine tracker created with 5 tasks"
}
```

---

## Task Endpoints

### POST `/api/v1/task/<task_id>/toggle/`

Toggle task completion status.

**Request (optional):**
```json
{
  "status": "DONE"
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "uuid",
  "status": "DONE",
  "completed_at": "2025-12-08T14:30:00Z",
  "feedback": {
    "type": "celebration",
    "message": "Great job! 🎉",
    "streak": 5
  },
  "tracker_progress": {
    "current_points": 35,
    "target_points": 50,
    "progress_percent": 70.0
  }
}
```

---

### POST `/api/v1/task/<task_id>/status/`

Set specific task status with notes.

**Request:**
```json
{
  "status": "IN_PROGRESS",
  "notes": "Working on this now"
}
```

**Status Options:**
- `TODO` - To Do
- `IN_PROGRESS` - In Progress
- `DONE` - Done
- `MISSED` - Missed
- `BLOCKED` - Blocked
- `SKIPPED` - Skipped

**Response:**
```json
{
  "success": true,
  "task_id": "uuid",
  "status": "IN_PROGRESS",
  "notes": "Working on this now"
}
```

---

### PUT `/api/v1/task/<task_id>/edit/`

Edit task details (template level).

**Request:**
```json
{
  "description": "Updated description",
  "category": "Work",
  "weight": 8,
  "points": 15
}
```

**Response:**
```json
{
  "success": true,
  "template_id": "uuid",
  "message": "Task updated"
}
```

---

### DELETE `/api/v1/task/<task_id>/delete/`

Delete a task instance.

**Response:**
```json
{
  "success": true,
  "message": "Task deleted",
  "undo": {
    "action_id": "undo_abc123"
  }
}
```

---

### POST `/api/v1/tasks/bulk/`

Perform bulk actions on multiple tasks.

**Request:**
```json
{
  "action": "mark_done",
  "task_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Actions:**
- `mark_done` - Mark all as done
- `mark_missed` - Mark all as missed
- `delete` - Delete all

**Response:**
```json
{
  "success": true,
  "updated_count": 3,
  "message": "3 tasks marked as done"
}
```

---

### POST `/api/v1/tasks/bulk-update/`

Bulk update task statuses by date range.

**Request:**
```json
{
  "tracker_id": "uuid",
  "start_date": "2025-12-01",
  "end_date": "2025-12-07",
  "status": "MISSED"
}
```

**Response:**
```json
{
  "success": true,
  "updated_count": 15,
  "message": "15 tasks updated to MISSED"
}
```

---

### POST `/api/v1/tracker/<tracker_id>/mark-overdue/`

Mark all overdue TODO tasks as MISSED.

**Response:**
```json
{
  "success": true,
  "marked_count": 5,
  "message": "5 overdue tasks marked as missed"
}
```

---

## Goals API

### GET/POST `/api/v1/goals/`

List or create goals.

**GET Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `per_page` | integer | No | Items per page (default: 20, max: 100) |
| `status` | string | No | Filter: 'active', 'achieved', 'paused', 'abandoned' |
| `sort` | string | No | Sort: 'created', '-created', 'priority', 'progress' |

**GET Response:**
```json
{
  "success": true,
  "goals": [
    {
      "goal_id": "uuid",
      "title": "Lose 5 kg",
      "description": "Weight loss goal",
      "icon": "🎯",
      "goal_type": "habit",
      "target_date": "2025-12-31",
      "target_value": 5.0,
      "current_value": 2.5,
      "unit": "kg",
      "status": "active",
      "priority": "high",
      "progress": 50.0,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 5,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

**POST Request:**
```json
{
  "title": "New Goal",
  "description": "Goal description",
  "target_date": "2025-12-31",
  "status": "active",
  "priority": "high"
}
```

**POST Response:**
```json
{
  "success": true,
  "goal_id": "uuid",
  "message": "Goal created successfully"
}
```

---

## Analytics & Insights

### GET `/api/v1/insights/`

Get behavioral insights for all trackers.

**Response:**
```json
{
  "success": true,
  "insights": [
    {
      "type": "optimal_time",
      "severity": "info",
      "title": "Best Performance Time",
      "description": "You perform best in the morning",
      "action": "Try scheduling important tasks before noon",
      "data": {
        "best_time": "morning",
        "completion_rate": 85.0
      }
    }
  ]
}
```

---

### GET `/api/v1/insights/<tracker_id>/`

Get insights for a specific tracker.

---

### GET `/api/v1/chart-data/`

Get chart data for visualizations.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | 'bar', 'line', 'pie', 'completion' |
| `tracker_id` | string | No | Filter by tracker |
| `days` | integer | No | Number of days (default: 30) |

**Response:**
```json
{
  "success": true,
  "chart_type": "bar",
  "data": {
    "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "datasets": [
      {
        "label": "Completion Rate",
        "data": [80, 75, 90, 85, 70, 60, 95]
      }
    ]
  }
}
```

---

### GET `/api/v1/heatmap/`

Get heatmap data for GitHub-style visualization.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `tracker_id` | string | No | Filter by tracker |
| `weeks` | integer | No | Number of weeks (default: 12) |

**Response:**
```json
{
  "success": true,
  "weeks": 12,
  "data": [
    {
      "date": "2025-12-08",
      "level": 4,
      "count": 10,
      "completion_rate": 100.0
    }
  ]
}
```

**Level Mapping:**
- 0: No data
- 1: 1-25% completion
- 2: 26-50% completion
- 3: 51-75% completion
- 4: 76-100% completion

---

### GET `/api/v1/analytics/data/`

Get comprehensive analytics data.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `days` | integer | No | Days of data (default: 30) |
| `tracker_id` | string | No | Filter by tracker |

**Response:**
```json
{
  "success": true,
  "data": {
    "completion_trend": [...],
    "time_of_day": {
      "morning": 85,
      "afternoon": 70,
      "evening": 75,
      "night": 50
    },
    "heatmap": [...],
    "insights": [...],
    "summary": {
      "average_completion": 75.5,
      "best_day": "Monday",
      "total_completed": 150
    }
  }
}
```

---

### GET `/api/v1/analytics/forecast/`

Get completion rate forecast.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `days` | integer | No | Days to forecast (default: 7, max: 30) |
| `history_days` | integer | No | Historical data to analyze (default: 30) |

**Response:**
```json
{
  "success": true,
  "forecast": [
    {
      "date": "2025-12-09",
      "predicted_rate": 78.5,
      "confidence": 0.85
    }
  ],
  "summary": {
    "message": "Your completion rate is trending upward",
    "recommendation": "Keep up the momentum!",
    "predicted_change": 5.2
  }
}
```

---

## User Profile & Settings

### GET/PUT `/api/v1/user/profile/`

Get or update user profile.

**GET Response:**
```json
{
  "success": true,
  "profile": {
    "id": 1,
    "email": "user@example.com",
    "username": "user",
    "first_name": "John",
    "last_name": "Doe",
    "avatar_url": "/media/avatars/user.jpg",
    "timezone": "Asia/Kolkata",
    "date_format": "DD/MM/YYYY",
    "week_start": 1,
    "date_joined": "2025-01-01T00:00:00Z"
  }
}
```

**PUT Request:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "timezone": "Asia/Kolkata",
  "date_format": "DD/MM/YYYY",
  "week_start": 1
}
```

---

### POST/DELETE `/api/v1/user/avatar/`

Upload or remove user avatar.

**POST** (multipart/form-data):
- `avatar`: Image file (jpg, png, gif, webp)

**Response:**
```json
{
  "success": true,
  "avatar_url": "/media/avatars/user_new.jpg"
}
```

---

### GET/PUT `/api/v1/preferences/`

Get or update user preferences.

**GET Response:**
```json
{
  "success": true,
  "preferences": {
    "daily_reminder_enabled": true,
    "daily_reminder_time": "08:00:00",
    "weekly_review_enabled": true,
    "weekly_review_day": 0,
    "default_view": "week",
    "theme": "dark",
    "show_completed_tasks": true,
    "compact_mode": false,
    "animations": true,
    "sound_complete": true,
    "push_enabled": false,
    "streak_threshold": 80,
    "public_profile": false
  }
}
```

**PUT Request:**
```json
{
  "theme": "dark",
  "daily_reminder_enabled": true,
  "daily_reminder_time": "09:00",
  "push_enabled": true
}
```

---

### DELETE `/api/v1/user/delete/`

Permanently delete user account.

**Request:**
```json
{
  "confirmation": "DELETE MY ACCOUNT",
  "password": "your_password"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Account deleted successfully"
}
```

⚠️ **WARNING**: This is an irreversible operation!

---

## Data Management

### POST `/api/v1/data/export/`

Export all user data.

**Request:**
```json
{
  "format": "json"
}
```

**Format Options:** `json`, `csv`

**Response:**
Returns downloadable file or:
```json
{
  "success": true,
  "download_url": "/exports/user_data_20251208.json"
}
```

---

### POST `/api/v1/data/import/`

Import data from JSON export.

**Request** (multipart/form-data):
- `file`: JSON export file

**Response:**
```json
{
  "success": true,
  "imported": {
    "trackers": 3,
    "tasks": 25,
    "goals": 2
  }
}
```

---

### POST `/api/v1/data/clear/`

Clear all user data.

**Request:**
```json
{
  "confirmation": "DELETE ALL DATA"
}
```

**Response:**
```json
{
  "success": true,
  "deleted": {
    "trackers": 5,
    "tasks": 100,
    "goals": 3
  }
}
```

⚠️ **WARNING**: This is a destructive operation!

---

### POST `/api/v1/export/month/`

Export data for a specific month.

**Request:**
```json
{
  "year": 2024,
  "month": 12,
  "format": "json",
  "tracker_id": "optional-uuid"
}
```

---

## Utility Endpoints

### GET `/api/v1/search/`

Global search with quick commands.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `type` | string | No | Filter: 'all', 'trackers', 'tasks', 'goals', 'notes' |
| `limit` | integer | No | Max results (default: 20) |

**Quick Commands:**
- `/add <task>` - Quick add task
- `/done <task>` - Mark task done
- `/goto <tracker>` - Navigate to tracker

**Response:**
```json
{
  "success": true,
  "results": {
    "trackers": [...],
    "tasks": [...],
    "goals": [...],
    "notes": [...]
  },
  "suggestions": [...],
  "total": 15
}
```

---

### GET/POST `/api/v1/notes/<date_str>/`

Get or create day notes.

**GET Response:**
```json
{
  "success": true,
  "note": {
    "note_id": "uuid",
    "date": "2025-12-08",
    "content": "Today was productive...",
    "sentiment_score": 0.8,
    "keywords": ["productive", "exercise"]
  }
}
```

**POST Request:**
```json
{
  "content": "Today's journal entry..."
}
```

---

### POST `/api/v1/undo/`

Undo a recent action.

**Request:**
```json
{
  "action_id": "undo_abc123",
  "action_type": "delete_task",
  "action_data": {
    "task_id": "uuid"
  }
}
```

---

### POST `/api/v1/validate/`

Real-time field validation.

**Request:**
```json
{
  "field": "tracker_name",
  "value": "My Tracker"
}
```

**Response:**
```json
{
  "valid": true,
  "message": "Name is available"
}
```

---

### GET `/api/v1/notifications/`

Get user notifications.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `unread_only` | boolean | No | Only unread notifications |
| `limit` | integer | No | Max items (default: 20) |

**Response:**
```json
{
  "success": true,
  "notifications": [
    {
      "id": "uuid",
      "type": "achievement",
      "title": "7-Day Streak!",
      "message": "You've completed tasks for 7 days straight!",
      "is_read": false,
      "created_at": "2025-12-08T10:00:00Z"
    }
  ],
  "unread_count": 3
}
```

---

### POST `/api/v1/notifications/`

Mark notifications as read.

**Request:**
```json
{
  "action": "mark_read",
  "notification_ids": ["uuid1", "uuid2"]
}
```

---

## Points & Goals System

### GET `/api/v1/tracker/<tracker_id>/progress/`

Get current progress for tracker's point-based goal.

**Response:**
```json
{
  "success": true,
  "current_points": 35,
  "target_points": 50,
  "progress_percent": 70.0,
  "goal_met": false,
  "period": "daily",
  "period_start": "2025-12-08",
  "period_end": "2025-12-08",
  "task_breakdown": {
    "completed_tasks": 7,
    "total_tasks": 10
  }
}
```

---

### GET/PUT `/api/v1/tracker/<tracker_id>/goal/`

Get or update tracker goal configuration.

**PUT Request:**
```json
{
  "target_points": 50,
  "goal_period": "daily",
  "goal_start_day": 0
}
```

**Response:**
```json
{
  "success": true,
  "tracker_id": "uuid",
  "target_points": 50,
  "goal_period": "daily",
  "progress": {
    "current_points": 35,
    "progress_percent": 70.0
  }
}
```

---

### GET `/api/v1/tracker/<tracker_id>/points-breakdown/`

Get detailed points breakdown per task.

**Response:**
```json
{
  "success": true,
  "tracker_id": "uuid",
  "tasks": [
    {
      "template_id": "uuid",
      "description": "Exercise",
      "points": 10,
      "include_in_goal": true,
      "completed": true,
      "earned_points": 10
    }
  ],
  "summary": {
    "total_possible": 50,
    "total_earned": 35,
    "tasks_included": 5,
    "tasks_excluded": 2
  }
}
```

---

### POST `/api/v1/task/<template_id>/toggle-goal/`

Toggle task's inclusion in goal calculation.

**Request:**
```json
{
  "include": true
}
```

**Response:**
```json
{
  "success": true,
  "template_id": "uuid",
  "include_in_goal": true,
  "tracker_progress": {...}
}
```

---

### POST `/api/v1/task/<template_id>/points/`

Update task points value.

**Request:**
```json
{
  "points": 15
}
```

**Response:**
```json
{
  "success": true,
  "template_id": "uuid",
  "points": 15,
  "tracker_progress": {...}
}
```

---

## System Endpoints

### GET `/api/v1/health/`

Health check endpoint (no auth required).

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-08T10:00:00Z",
  "version": "1.0",
  "database": "ok",
  "cache": "ok"
}
```

**Response (503):**
```json
{
  "status": "unhealthy",
  "error": "Database connection failed"
}
```

---

### GET `/api/v1/feature-flags/<flag_name>/`

Check if a feature flag is enabled.

**Response:**
```json
{
  "success": true,
  "flag": "new_dashboard",
  "enabled": true
}
```

---

### GET `/api/v1/prefetch/`

Prefetch data for SPA navigation.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `panels` | string | Yes | Comma-separated: 'today,dashboard,week' |

---

### GET `/api/v1/tasks/infinite/`

Cursor-based paginated task list.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `cursor` | string | No | ISO datetime cursor |
| `limit` | integer | No | Items per page (default: 20) |
| `tracker_id` | string | No | Filter by tracker |
| `status` | string | No | Filter by status |
| `period` | string | No | 'today', 'week', 'month', 'all' |

---

### GET `/api/v1/suggestions/`

Get smart suggestions based on behavior.

**Response:**
```json
{
  "success": true,
  "suggestions": [
    {
      "type": "optimal_time",
      "message": "You perform best on Mondays",
      "confidence": 0.85
    }
  ]
}
```

---

### POST `/api/v1/sync/`

Bidirectional sync for offline-first apps.

**Request:**
```json
{
  "last_sync": "2025-12-08T00:00:00Z",
  "local_changes": [
    {
      "entity_type": "task",
      "entity_id": "uuid",
      "action": "update",
      "data": {...},
      "timestamp": "2025-12-08T10:00:00Z"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "conflicts": [...],
  "server_changes": {...},
  "new_sync_timestamp": "2025-12-08T10:30:00Z",
  "sync_status": "complete"
}
```

---

## Error Handling

### Standard Error Response

All errors follow this format:

```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (not logged in) |
| 403 | Forbidden (no permission) |
| 404 | Not Found |
| 405 | Method Not Allowed |
| 429 | Too Many Requests (rate limited) |
| 500 | Internal Server Error |

### Validation Error Response

```json
{
  "success": false,
  "errors": {
    "field_name": ["Error message 1", "Error message 2"],
    "non_field_errors": ["General error"]
  }
}
```

### Authentication Error (401)

```json
{
  "detail": "Authentication required",
  "code": "not_authenticated"
}
```

---

## Testing Checklist

### Prerequisites

1. ✅ Django server running at `http://127.0.0.1:8000/`
2. ✅ Test user account created
3. ✅ At least one tracker with tasks

### Test Sequence

#### 1. Authentication Flow
- [ ] Test login with valid credentials
- [ ] Test login with invalid credentials
- [ ] Test rate limiting (6 failed attempts)
- [ ] Test signup with new email
- [ ] Test signup with existing email
- [ ] Test auth status (authenticated)
- [ ] Test auth status (not authenticated)
- [ ] Test logout

#### 2. Dashboard Endpoints
- [ ] GET `/api/v1/dashboard/` (full data)
- [ ] GET `/api/v1/dashboard/trackers/`
- [ ] GET `/api/v1/dashboard/today/`
- [ ] GET `/api/v1/dashboard/week/`
- [ ] GET `/api/v1/dashboard/goals/`
- [ ] GET `/api/v1/dashboard/streaks/`
- [ ] GET `/api/v1/dashboard/activity/`

#### 3. Tracker CRUD
- [ ] GET `/api/v1/trackers/`
- [ ] POST `/api/v1/tracker/create/`
- [ ] GET `/api/v1/tracker/<id>/`
- [ ] PUT `/api/v1/tracker/<id>/update/`
- [ ] DELETE `/api/v1/tracker/<id>/delete/`

#### 4. Task Operations
- [ ] POST `/api/v1/tracker/<id>/task/add/`
- [ ] POST `/api/v1/task/<id>/toggle/`
- [ ] POST `/api/v1/task/<id>/status/`
- [ ] PUT `/api/v1/task/<id>/edit/`
- [ ] DELETE `/api/v1/task/<id>/delete/`
- [ ] POST `/api/v1/tasks/bulk/`

#### 5. Goals & Points
- [ ] GET `/api/v1/goals/`
- [ ] POST `/api/v1/goals/`
- [ ] GET `/api/v1/tracker/<id>/progress/`
- [ ] GET `/api/v1/tracker/<id>/points-breakdown/`
- [ ] PUT `/api/v1/tracker/<id>/goal/`

#### 6. Analytics
- [ ] GET `/api/v1/insights/`
- [ ] GET `/api/v1/chart-data/?type=bar`
- [ ] GET `/api/v1/heatmap/`
- [ ] GET `/api/v1/analytics/data/`
- [ ] GET `/api/v1/analytics/forecast/`

#### 7. User & Settings
- [ ] GET `/api/v1/user/profile/`
- [ ] PUT `/api/v1/user/profile/`
- [ ] GET `/api/v1/preferences/`
- [ ] PUT `/api/v1/preferences/`

#### 8. System
- [ ] GET `/api/v1/health/`
- [ ] GET `/api/v1/search/?q=test`
- [ ] GET `/api/v1/notifications/`

---

## cURL Examples

### Login

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

### Get Dashboard (with session cookie)

```bash
curl -X GET http://127.0.0.1:8000/api/v1/dashboard/ \
  -H "Cookie: sessionid=<your_session_id>"
```

### Get Dashboard (with JWT)

```bash
curl -X GET http://127.0.0.1:8000/api/v1/dashboard/ \
  -H "Authorization: Bearer <your_jwt_token>"
```

### Create Tracker

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tracker/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "My Daily Tracker",
    "description": "Track daily habits",
    "time_mode": "daily"
  }'
```

### Toggle Task

```bash
curl -X POST http://127.0.0.1:8000/api/v1/task/<task_id>/toggle/ \
  -H "Authorization: Bearer <token>"
```

---

*Document generated on 2025-12-08*
