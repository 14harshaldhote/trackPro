# Points, Toggles, and Goals System - Implementation Plan

> **Created:** 2025-12-08  
> **Status:** ✅ Phase 1-3 COMPLETED  
> **Purpose:** Fix point toggle behavior and implement proper tracker-based goals

---

## ✅ Implementation Status

### Completed Files:

| File | Action | Status |
|------|--------|--------|
| `core/models.py` | Added `target_points`, `goal_period`, `goal_start_day` to TrackerDefinition; Added `points`, `include_in_goal` to TaskTemplate | ✅ Done |
| `core/services/points_service.py` | **NEW** - Central points calculation service with toggle support | ✅ Done |
| `core/views_api.py` | Added 5 new API endpoints for points/goals | ✅ Done |
| `core/urls_api_v1.py` | Registered new endpoints | ✅ Done |
| `core/serializers.py` | Added TrackerGoalSerializer, TaskToggleGoalSerializer, TaskPointsUpdateSerializer; Updated TaskTemplateSerializer | ✅ Done |
| `core/migrations/XXXX_*` | Migration reference file (run `makemigrations` after dependencies installed) | ⏳ Pending |

### New API Endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/tracker/{id}/progress/` | Get tracker points progress |
| GET/PUT | `/api/v1/tracker/{id}/goal/` | Get/set tracker goal configuration |
| GET | `/api/v1/tracker/{id}/points-breakdown/` | Detailed task points breakdown |
| POST | `/api/v1/task/{template_id}/toggle-goal/` | Toggle task goal inclusion |
| POST | `/api/v1/task/{template_id}/points/` | Update task points value |

---

## 📋 Executive Summary

This document analyzes the **gap between the user's specification** (task points, toggles, tracker-linked goals) and the **current codebase implementation**. The current system has a different architecture that needs to be extended/modified to support the specified features.

---

## 🔍 Gap Analysis: Specification vs Current Implementation

### 1. Data Model Comparison

#### SPECIFICATION: Tracker Model
| Field | Specified | Current Status |
|-------|-----------|----------------|
| `target_points` | ✅ Required | ❌ **MISSING** |
| `goal_period` | ✅ Required (daily/weekly/custom) | 🔶 Partial (`time_mode` exists but different purpose) |
| `current_points` | ✅ Required (auto-calculated) | ❌ **MISSING** |

#### SPECIFICATION: Task Model (TaskInstance)
| Field | Specified | Current Status |
|-------|-----------|----------------|
| `points` | ✅ Required | ❌ **MISSING** - Uses `weight` in TaskTemplate (1-10 range) |
| `include_in_goal` | ✅ Required (boolean toggle) | ❌ **MISSING** |
| `is_completed` | ✅ Required | 🔶 Different - Uses `status` enum (DONE/TODO/etc.) |
| `date` | ✅ Required | ✅ Exists via `tracker_instance.period_start/end` |

#### Current Goal Model (Separate from Trackers)
| Field | Description | Issue |
|-------|-------------|-------|
| `Goal.tracker` | Optional FK to TrackerDefinition | ✅ Can link to tracker |
| `Goal.target_value` | Numeric target | ✅ Can be used for target_points |
| `Goal.current_value` | Current progress | ✅ Can be used for current_points |
| `Goal.goal_type` | habit/achievement/project | ✅ Flexible |

### 2. Architecture Differences

#### Specification Architecture (Simple)
```
User → Tracker → Tasks
             └→ Goal (embedded in tracker: target_points, goal_period)
```

#### Current Architecture (More Complex)
```
User → TrackerDefinition → TaskTemplate → TaskInstance
                    └→ TrackerInstance (per date/period)
                    
User → Goal (separate entity) → GoalTaskMapping → TaskTemplate
```

### 3. Key Missing Features

| Feature | Specified | Current | Gap |
|---------|-----------|---------|-----|
| **Point Toggle** | Per-task `include_in_goal` boolean | ❌ Missing | Need to add field + APIs |
| **Points per Task** | `points` integer on Task | ❌ Missing (only `weight` 1-10) | Need to add field or repurpose `weight` |
| **Tracker Goal** | `target_points` + `goal_period` on Tracker | ❌ Missing | Need to add fields to TrackerDefinition |
| **Auto-Calculation** | Recalc `current_points` on toggle/completion | ❌ Missing | Need calculation service |
| **Period Reset** | Daily/weekly reset logic | ❌ Missing | Need timezone-aware reset |
| **Historical Snapshots** | Daily progress history | ❌ Missing | Need new model or field |

---

## 🏗️ Proposed Implementation

### Option A: Extend Current Architecture (Recommended)

**Rationale:** Preserve existing functionality while adding new features.

#### Phase 1: Model Updates

##### 1.1 Add fields to `TrackerDefinition`
```python
# New fields for TrackerDefinition
target_points = models.IntegerField(default=0, help_text="Target points for goal")
goal_period = models.CharField(max_length=20, choices=[
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('custom', 'Custom'),
], default='daily')
goal_start_day = models.IntegerField(default=0)  # 0=Monday for weekly
```

##### 1.2 Add fields to `TaskTemplate` 
```python
# New fields for TaskTemplate (affects all instances)
points = models.IntegerField(default=1, validators=[MinValueValidator(0)])
include_in_goal = models.BooleanField(default=True)
```

##### 1.3 Add fields to `TaskInstance` (for per-instance overrides)
```python
# Optional: Allow per-instance override of template defaults
include_in_goal_override = models.BooleanField(null=True, blank=True)
# If null, use template default; if set, use this value
```

##### 1.4 Create new `DailyProgress` model for historical tracking
```python
class DailyProgress(models.Model):
    """Snapshot of daily progress for analytics and history."""
    
    progress_id = models.CharField(max_length=36, primary_key=True)
    tracker = models.ForeignKey(TrackerDefinition, on_delete=models.CASCADE)
    date = models.DateField()
    
    # Points
    total_points_possible = models.IntegerField(default=0)
    points_earned = models.IntegerField(default=0)
    target_points = models.IntegerField(default=0)  # Snapshot of goal
    
    # Task counts
    total_tasks = models.IntegerField(default=0)
    completed_tasks = models.IntegerField(default=0)
    included_tasks = models.IntegerField(default=0)  # Tasks with include_in_goal=True
    
    # Status
    goal_met = models.BooleanField(default=False)
    completion_percentage = models.FloatField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['tracker', 'date']]
```

#### Phase 2: Service Layer Updates

##### 2.1 Create `PointsCalculationService`
```python
# core/services/points_service.py

class PointsCalculationService:
    """
    Central service for all points calculations.
    Single source of truth for progress calculation logic.
    """
    
    def __init__(self, tracker_id: str, user, target_date=None):
        self.tracker_id = tracker_id
        self.user = user
        self.target_date = target_date or date.today()
    
    def calculate_current_points(self, period: str = None) -> Dict:
        """
        Calculate current points for tracker.
        
        Returns:
            {
                'current_points': int,
                'target_points': int,
                'progress_percentage': float,
                'goal_met': bool,
                'tasks_included': int,
                'tasks_excluded': int
            }
        """
        # Implementation details...
    
    def get_applicable_tasks(self, period: str) -> QuerySet:
        """Get tasks that count towards the goal."""
        # Filter by:
        # 1. Tracker
        # 2. Date range (based on period: daily/weekly)
        # 3. include_in_goal = True
        # 4. status = DONE
    
    def refresh_tracker_progress(self):
        """Recalculate and save tracker progress."""
        # Called after task completion, toggle change, etc.
    
    def create_daily_snapshot(self):
        """Create end-of-day progress snapshot."""
```

##### 2.2 Update `TaskService` for toggle handling
```python
# Add to task_service.py

def toggle_goal_inclusion(self, task_id: str, include: bool) -> Dict:
    """
    Toggle whether a task's points count towards the goal.
    
    Args:
        task_id: TaskInstance ID (or TaskTemplate ID)
        include: True = count towards goal, False = exclude
    
    Returns:
        {
            'task_id': str,
            'include_in_goal': bool,
            'tracker_points_updated': int
        }
    """
    # 1. Update task/template include_in_goal field
    # 2. Recalculate tracker progress
    # 3. Return updated state
```

#### Phase 3: API Endpoints

##### 3.1 New Endpoints Needed

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/task/{id}/toggle-goal/` | Toggle task goal inclusion |
| GET | `/api/v1/tracker/{id}/progress/` | Get tracker points progress |
| PUT | `/api/v1/tracker/{id}/goal/` | Set/update tracker goal |
| GET | `/api/v1/tracker/{id}/history/` | Get historical progress |
| POST | `/api/v1/tracker/{id}/recalculate/` | Force recalculate progress |

##### 3.2 Update Existing Endpoints
- **`/api/v1/task/{id}/toggle/`**: Also trigger points recalculation
- **`/api/v1/task/{id}/status/`**: Also trigger points recalculation
- **`/api/v1/tracker/create/`**: Accept `target_points` and `goal_period`
- **`/api/v1/tracker/{id}/update/`**: Allow updating goal settings

#### Phase 4: Frontend/iOS Integration

##### 4.1 API Response Updates
```json
// Task object should include:
{
  "task_id": "uuid",
  "description": "Exercise 30 min",
  "status": "TODO",
  "points": 10,
  "include_in_goal": true,
  // ... other fields
}

// Tracker progress endpoint:
{
  "success": true,
  "tracker_id": "uuid",
  "goal": {
    "target_points": 50,
    "current_points": 35,
    "goal_period": "daily",
    "progress_percentage": 70.0,
    "goal_met": false
  },
  "breakdown": {
    "total_tasks": 8,
    "completed_tasks": 5,
    "included_tasks": 6,
    "excluded_tasks": 2
  }
}
```

---

## 📝 Decision Matrix

Before implementing, you need to decide:

### Decision 1: Points vs Weight
| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Repurpose existing `weight` field as `points` | No migration, simple | Breaks existing weight semantics |
| B | Add new `points` field, keep `weight` | Clean separation | More fields, migration needed |
| **Recommended**: B (add new field) | Allows weight for ordering AND points for goals |

### Decision 2: Toggle Scope
| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Toggle on `TaskTemplate` (affects all instances) | Simple, consistent | Less granular control |
| B | Toggle on `TaskInstance` (per-occurrence) | Granular control | Complex UI, many toggles |
| C | Toggle on Template with per-instance override | Best of both | More complex logic |
| **Recommended**: A (Template level) | Simpler UX, meets stated requirement |

### Decision 3: Goal Location
| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Goal embedded in TrackerDefinition | Simple, 1:1 relationship | Only one goal per tracker |
| B | Keep separate Goal model, link to Tracker | Multiple goals possible | More complex |
| **Recommended**: A for MVP, then extend to B | Start simple, expand later |

### Decision 4: Period Reset Timing
| Option | Description |
|--------|-------------|
| `timezone_local` | Reset at midnight user's local time |
| `timezone_utc` | Reset at midnight UTC |
| `custom` | User configures reset time |
| **Recommended**: `timezone_local` using UserPreferences.timezone |

---

## 🔧 Implementation Steps

### Step 1: Database Migrations
1. Add `target_points`, `goal_period` to `TrackerDefinition`
2. Add `points`, `include_in_goal` to `TaskTemplate`
3. Create `DailyProgress` model
4. Run migrations

### Step 2: Service Layer
1. Create `PointsCalculationService`
2. Update `TaskService.update_task_status()` to trigger recalculation
3. Add toggle handling methods
4. Add scheduled job for daily snapshots

### Step 3: API Layer
1. Create new endpoints for points/goal management
2. Update existing task/tracker endpoints
3. Add goal fields to serializers
4. Update response formats

### Step 4: iOS Integration
1. Update models to include new fields
2. Add toggle UI in task rows
3. Add goal progress UI in tracker detail
4. Connect to new API endpoints

### Step 5: Testing
1. Unit tests for calculation logic
2. API tests for new endpoints
3. Edge case tests (zero points, all excluded, etc.)

---

## ⚠️ Edge Cases to Handle

| Case | Expected Behavior |
|------|-------------------|
| `target_points = 0` | Treat as "no goal set", hide progress bar or show neutral |
| All tasks excluded | `current_points = 0`, show warning |
| Task completed then excluded | Remove points from total |
| Goal period changes | Recalculate with new window |
| Past task completed | Only count if within current period |
| User changes timezone | Recalculate based on new timezone |
| Points edited after completion | Recalculate immediately |

---

## 📦 Deliverables

### Files to Create/Modify

| File | Action | Priority |
|------|--------|----------|
| `core/models.py` | Add new fields to TrackerDefinition, TaskTemplate; Add DailyProgress model | HIGH |
| `core/services/points_service.py` | **NEW** - Points calculation service | HIGH |
| `core/services/task_service.py` | Update to trigger recalculation | HIGH |
| `core/services/tracker_service.py` | Update for goal settings | MEDIUM |
| `core/views_api.py` | Add new endpoints | HIGH |
| `core/urls_api_v1.py` | Register new endpoints | HIGH |
| `core/serializers.py` | Add new serializers | MEDIUM |
| `core/management/commands/daily_snapshot.py` | **NEW** - Daily progress job | LOW |
| iOS: Task models | Update with new fields | HIGH |
| iOS: Tracker views | Add goal progress UI | MEDIUM |

---

## ✅ Approval Checklist

Before proceeding to implementation:

- [ ] Confirm Decision 1: Points vs Weight approach
- [ ] Confirm Decision 2: Toggle scope (Template vs Instance)
- [ ] Confirm Decision 3: Goal location (embedded vs separate)
- [ ] Confirm Decision 4: Timezone handling
- [ ] Confirm priority order for implementation phases
- [ ] Review edge cases

---

## 🚀 Next Steps

**Please confirm:**

1. Which decisions do you want for each option above?
2. Should I start with Option A (extend current architecture) or redesign?
3. Do you want me to create the migration files first, or the service layer?
4. Should I include iOS model updates in Phase 1?

Once confirmed, I'll proceed with generating the actual code files.
