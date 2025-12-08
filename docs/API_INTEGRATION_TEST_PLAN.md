# API v1 Integration Testing Plan

> **Version**: 1.0  
> **Total Endpoints**: 55  
> **Test Phases**: 6  
> **Estimated Tests**: 200+

---

## Overview

This plan covers comprehensive integration testing for all Tracker Pro API v1 endpoints, including:
- ✅ Happy path testing
- ✅ Edge cases and error handling
- ✅ Workflow testing (multi-step sequences)
- ✅ Authentication/Authorization testing
- ✅ Data validation testing
- ✅ Performance verification

---

## Test Phases

| Phase | Category | Endpoints | Priority |
|-------|----------|-----------|----------|
| 1 | Authentication & System | 9 | Critical |
| 2 | Tracker CRUD | 10 | Critical |
| 3 | Task CRUD | 9 | Critical |
| 4 | Dashboard & Data | 10 | High |
| 5 | Analytics & Insights | 6 | Medium |
| 6 | User & Data Management | 11 | Medium |

---

## Phase 1: Authentication & System (9 endpoints)

### Endpoints
1. `GET /health/` - Health check
2. `POST /auth/login/` - User login
3. `POST /auth/signup/` - User registration
4. `GET/POST /auth/logout/` - User logout
5. `GET /auth/status/` - Check auth status
6. `POST /auth/validate-email/` - Validate email availability
7. `POST /auth/google/` - Google OAuth
8. `POST /auth/apple/mobile/` - Apple Sign-In
9. `GET /feature-flags/<flag>/` - Feature flag check

### Test Cases

#### 1.1 Health Check
```
GET /api/v1/health/
Expected: 200 OK
{
  "status": "healthy",
  "timestamp": "...",
  "version": "1.0.0",
  "checks": {"database": {...}, "cache": {...}}
}
```

#### 1.2 Login Tests
| Test | Input | Expected |
|------|-------|----------|
| Valid login | `{"email": "test@test.com", "password": "password123"}` | 200, token returned |
| Invalid email format | `{"email": "invalid", ...}` | 400, validation error |
| Wrong password | Valid email, wrong pass | 400, "Invalid email or password" |
| Missing email | `{"password": "..."}` | 400, email required |
| Missing password | `{"email": "..."}` | 400, password required |
| Rate limited | 11+ rapid attempts | 429, rate limit exceeded |

#### 1.3 Signup Tests
| Test | Input | Expected |
|------|-------|----------|
| Valid signup | `{"email": "new@test.com", "password1": "Pass123!", "password2": "Pass123!"}` | 200 |
| Password mismatch | password1 ≠ password2 | 400 |
| Weak password | "123" | 400 |
| Duplicate email | Existing email | 400 |
| Invalid email | "not-an-email" | 400 |

#### 1.4 Auth Status Tests
| Test | Expected |
|------|----------|
| Unauthenticated | 200, `{authenticated: false}` |
| With valid token | 200, `{authenticated: true, user: {...}}` |

#### 1.5 Validate Email Tests
| Test | Input | Expected |
|------|-------|----------|
| Available email | New email | 200, `{available: true}` |
| Taken email | Existing email | 200, `{available: false}` |
| Invalid format | "not-email" | 400 |
| Empty | `{}` | 400 |

---

## Phase 2: Tracker CRUD (10 endpoints)

### Endpoints
1. `GET /trackers/` - List all trackers
2. `GET /tracker/<id>/` - Get tracker detail
3. `POST /tracker/create/` - Create tracker
4. `PUT /tracker/<id>/update/` - Update tracker
5. `DELETE /tracker/<id>/delete/` - Delete tracker
6. `POST /tracker/<id>/reorder/` - Reorder tasks
7. `POST /tracker/<id>/share/` - Generate share link
8. `GET /tracker/<id>/export/` - Export tracker data
9. `POST /templates/activate/` - Activate template
10. `GET /tracker/<id>/progress/` - Points progress

### Test Cases

#### 2.1 List Trackers
| Test | Query Params | Expected |
|------|--------------|----------|
| Default list | None | 200, active trackers |
| Filter by status | `?status=archived` | 200, archived only |
| Include deleted | `?include_deleted=true` | 200, includes soft-deleted |
| Unauthenticated | No auth | 401 |

#### 2.2 Create Tracker
| Test | Input | Expected |
|------|-------|----------|
| Valid | `{"name": "New Tracker", "time_mode": "daily"}` | 201 |
| Duplicate name | Same name exists | 400 |
| Missing name | `{}` | 400 |
| Invalid time_mode | `{"time_mode": "invalid"}` | 400 |
| Name too long | 500+ chars | 400 |

#### 2.3 Update Tracker
| Test | Input | Expected |
|------|-------|----------|
| Valid update | `{"name": "Updated"}` | 200 |
| Invalid ID | Non-existent UUID | 404 |
| Other user's tracker | Different user | 403 or 404 |
| Invalid status | `{"status": "invalid"}` | 400 |

#### 2.4 Delete Tracker
| Test | Expected |
|------|----------|
| Valid delete | 200, soft deleted |
| Already deleted | 404 |
| Non-existent | 404 |

#### 2.5 Template Activate
| Test | Input | Expected |
|------|-------|----------|
| Valid template | `{"template_key": "morning"}` | 200, tracker created |
| Invalid template | `{"template_key": "invalid"}` | 404, available templates list |
| Missing key | `{}` | 400, available templates list |

---

## Phase 3: Task CRUD (9 endpoints)

### Endpoints
1. `POST /task/<id>/toggle/` - Toggle task status
2. `GET /task/<id>/status/` - Get task status
3. `PUT /task/<id>/edit/` - Edit task
4. `DELETE /task/<id>/delete/` - Delete task
5. `POST /tracker/<id>/task/add/` - Add task to tracker
6. `POST /tasks/bulk/` - Bulk task operations
7. `POST /tasks/bulk-update/` - Bulk status update
8. `POST /tracker/<id>/mark-overdue/` - Mark overdue as missed
9. `GET /tasks/infinite/` - Paginated task list

### Test Cases

#### 3.1 Task Toggle
| Test | Current Status | Expected Result |
|------|----------------|-----------------|
| TODO → DONE | TODO | DONE, points awarded |
| DONE → TODO | DONE | TODO, points reverted |
| IN_PROGRESS → DONE | IN_PROGRESS | DONE |
| Invalid task ID | - | 404 |
| Other user's task | - | 403/404 |

#### 3.2 Add Task
| Test | Input | Expected |
|------|-------|----------|
| Valid task | `{"description": "New task", "category": "work"}` | 201 |
| Empty description | `{"description": ""}` | 400 |
| Invalid tracker | Non-existent ID | 404 |
| Invalid time_of_day | `{"time_of_day": "invalid"}` | 400 |

#### 3.3 Edit Task
| Test | Input | Expected |
|------|-------|----------|
| Update description | `{"description": "Updated"}` | 200 |
| Update category | `{"category": "new-cat"}` | 200 |
| Update weight | `{"weight": 5}` | 200 |
| Invalid weight | `{"weight": -1}` | 400 |

#### 3.4 Task Points
| Test | Input | Expected |
|------|-------|----------|
| Set points | `{"points": 10}` | 200 |
| Invalid points | `{"points": -5}` | 400 |
| Zero points | `{"points": 0}` | 200 |

---

## Phase 4: Dashboard & Data (10 endpoints)

### Endpoints
1. `GET /dashboard/` - Full dashboard
2. `GET /dashboard/trackers/` - Tracker summaries
3. `GET /dashboard/today/` - Today's stats
4. `GET /dashboard/week/` - Week overview
5. `GET /dashboard/goals/` - Goals progress
6. `GET /dashboard/streaks/` - Streak info
7. `GET /dashboard/activity/` - Recent activity
8. `GET /goals/` - Goals list with pagination
9. `GET/PUT /preferences/` - User preferences
10. `GET/POST /notifications/` - Notifications

### Test Cases

#### 4.1 Dashboard
| Test | Query | Expected |
|------|-------|----------|
| Default | None | 200, current day data |
| Specific date | `?date=2025-01-01` | 200, that day's data |
| Invalid date | `?date=invalid` | 400 |
| Future date | `?date=2030-01-01` | 200, empty data |

#### 4.2 Goals Pagination
| Test | Query | Expected |
|------|-------|----------|
| Default | None | 200, page 1, 20 items |
| Page 2 | `?page=2` | 200, page 2 |
| Custom per_page | `?per_page=10` | 200, 10 items max |
| Filter status | `?status=active` | 200, only active |
| Sort order | `?sort=-priority` | 200, sorted |
| Over max per_page | `?per_page=500` | 200, capped at 100 |

#### 4.3 Notifications
| Test | Method | Expected |
|------|--------|----------|
| List notifications | GET | 200, paginated list |
| Filter unread | GET `?unread_only=true` | 200, unread only |
| Mark read | POST `{action: "mark_read", ids: [...]}` | 200 |
| Mark all read | POST `{action: "mark_all_read"}` | 200 |

#### 4.4 Preferences
| Test | Method | Input | Expected |
|------|--------|-------|----------|
| Get preferences | GET | - | 200, all prefs |
| Update theme | PUT | `{"theme": "dark"}` | 200 |
| Invalid theme | PUT | `{"theme": "invalid"}` | 400 |
| Multiple updates | PUT | `{"theme": "dark", "compact_mode": true}` | 200 |

---

## Phase 5: Analytics & Insights (6 endpoints)

### Endpoints
1. `GET /insights/` - All insights
2. `GET /insights/<tracker_id>/` - Tracker insights
3. `GET /chart-data/` - Chart data
4. `GET /heatmap/` - Heatmap data
5. `GET /analytics/data/` - Analytics data
6. `GET /analytics/forecast/` - Completion forecast

### Test Cases

#### 5.1 Chart Data
| Test | Query | Expected |
|------|-------|----------|
| Bar chart | `?type=bar` | 200, weekly data |
| Pie chart | `?type=pie` | 200, category distribution |
| Line chart | `?type=completion` | 200, completion trend |
| Invalid type | `?type=invalid` | 400 |
| With tracker | `?tracker_id=xxx&type=bar` | 200 |

#### 5.2 Heatmap
| Test | Query | Expected |
|------|-------|----------|
| Default | None | 200, 12 weeks |
| Custom weeks | `?weeks=26` | 200, 26 weeks |
| Specific tracker | `?tracker_id=xxx` | 200 |

#### 5.3 Forecast
| Test | Query | Expected |
|------|-------|----------|
| Default | None | 200, 7 day forecast |
| Custom days | `?days=14` | 200, 14 days |
| New user | No history | 200, suggestions returned |
| Invalid days | `?days=100` | 400 |

---

## Phase 6: User & Data Management (11 endpoints)

### Endpoints
1. `GET/PUT /user/profile/` - User profile
2. `POST /user/avatar/` - Upload avatar
3. `DELETE /user/delete/` - Delete account
4. `GET /data/export/` - Export all data
5. `POST /data/import/` - Import data
6. `DELETE /data/clear/` - Clear all data
7. `GET /export/month/` - Monthly export
8. `GET /search/` - Global search
9. `POST /notes/<date>/` - Day notes
10. `POST /undo/` - Undo action
11. `GET /sync/` - Sync data

### Test Cases

#### 6.1 User Profile
| Test | Method | Input | Expected |
|------|--------|-------|----------|
| Get profile | GET | - | 200, user data |
| Update name | PUT | `{"username": "newname"}` | 200 |
| Invalid username | PUT | `{"username": ""}` | 400 |

#### 6.2 Search
| Test | Query | Expected |
|------|-------|----------|
| Basic search | `?q=morning` | 200, results |
| Empty query | `?q=` | 200, empty or suggestions |
| No results | `?q=zzzznotfound` | 200, empty results |
| Special chars | `?q=<script>` | 200, sanitized |

#### 6.3 Day Notes
| Test | Date | Input | Expected |
|------|------|-------|----------|
| Save note | 2025-12-08 | `{"note": "My note"}` | 200 |
| Invalid date | invalid | - | 400 |
| Empty note | - | `{"note": ""}` | 200, clears note |

#### 6.4 Data Export
| Test | Query | Expected |
|------|-------|----------|
| JSON export | `?format=json` | 200, JSON file |
| CSV export | `?format=csv` | 200, CSV file |

---

## Workflow Tests

### Workflow 1: New User Onboarding
```
1. POST /auth/signup/ → Create account
2. GET /auth/status/ → Verify logged in
3. POST /templates/activate/ {template_key: "morning"} → Create first tracker
4. GET /dashboard/ → Verify tracker appears
5. GET /trackers/ → Verify tracker in list
6. POST /task/<id>/toggle/ → Complete first task
7. GET /dashboard/today/ → Verify progress
```

### Workflow 2: Daily Task Completion
```
1. GET /dashboard/trackers/ → Get today's tasks
2. POST /task/<id>/toggle/ → Mark task DONE
3. GET /tracker/<id>/progress/ → Check points
4. POST /task/<id>/toggle/ → Undo (mark TODO)
5. POST /undo/ → Restore previous state
6. GET /dashboard/streaks/ → Verify streak
```

### Workflow 3: Tracker Management
```
1. POST /tracker/create/ → Create tracker
2. POST /tracker/<id>/task/add/ → Add task 1
3. POST /tracker/<id>/task/add/ → Add task 2
4. POST /tracker/<id>/reorder/ → Reorder tasks
5. PUT /tracker/<id>/update/ → Update tracker
6. POST /tracker/<id>/share/ → Get share link
7. GET /tracker/<id>/export/ → Export data
8. DELETE /tracker/<id>/delete/ → Delete tracker
```

### Workflow 4: Analytics Review
```
1. GET /analytics/data/ → Get stats
2. GET /chart-data/?type=bar → Weekly chart
3. GET /heatmap/?weeks=12 → Activity heatmap
4. GET /insights/ → Get insights
5. GET /analytics/forecast/ → Get predictions
```

### Workflow 5: Goal Management
```
1. POST /goals/ → Create goal
2. GET /goals/ → List goals
3. PUT /tracker/<id>/goal/ → Set tracker goal
4. GET /tracker/<id>/progress/ → Check progress
5. POST /task/<template_id>/toggle-goal/ → Toggle include_in_goal
6. PUT /task/<template_id>/points/ → Update task points
```

---

## Edge Cases

### Authentication Edge Cases
- Token expiry
- Invalid token format
- Revoked token
- Concurrent sessions

### Data Edge Cases
- Empty trackers (no tasks)
- Trackers with 100+ tasks
- Tasks with very long descriptions
- Unicode/emoji in text fields
- Null vs empty string handling

### Date Edge Cases
- Leap year dates
- Timezone boundaries
- DST transitions
- Future dates
- Very old dates

### Concurrency Edge Cases
- Same task toggled twice rapidly
- Bulk operations during active use
- Race conditions on points calculation

---

## Test Execution Order

### Phase 1 Tests (Run First - No Data Required)
- Health check
- Auth status (unauthenticated)
- Signup flow
- Login flow
- Email validation

### Phase 2-6 Tests (Require Test User)
1. Create test user via signup
2. Get auth token
3. Run remaining tests with token

---

## Success Criteria

| Category | Criteria |
|----------|----------|
| Coverage | 100% of endpoints tested |
| Passing | 95%+ tests pass |
| Performance | All responses < 2s |
| Edge Cases | All edge cases handled |
| Workflows | All workflows complete |

---

## Test Tracking Checklist

### Phase 1: Authentication ☐
- [ ] Health check
- [ ] Login (all cases)
- [ ] Signup (all cases)
- [ ] Logout
- [ ] Auth status
- [ ] Email validation
- [ ] Feature flags

### Phase 2: Tracker CRUD ☐
- [ ] List trackers
- [ ] Get tracker detail
- [ ] Create tracker
- [ ] Update tracker
- [ ] Delete tracker
- [ ] Reorder tasks
- [ ] Share tracker
- [ ] Export tracker
- [ ] Template activation
- [ ] Points progress

### Phase 3: Task CRUD ☐
- [ ] Toggle task
- [ ] Get task status
- [ ] Edit task
- [ ] Delete task
- [ ] Add task
- [ ] Bulk operations
- [ ] Mark overdue

### Phase 4: Dashboard ☐
- [ ] Full dashboard
- [ ] Dashboard trackers
- [ ] Today stats
- [ ] Week overview
- [ ] Goals summary
- [ ] Streaks
- [ ] Activity
- [ ] Goals pagination
- [ ] Notifications
- [ ] Preferences

### Phase 5: Analytics ☐
- [ ] Insights
- [ ] Chart data
- [ ] Heatmap
- [ ] Analytics data
- [ ] Forecast

### Phase 6: User/Data ☐
- [ ] User profile
- [ ] Avatar upload
- [ ] Search
- [ ] Day notes
- [ ] Data export
- [ ] Sync

### Workflows ☐
- [ ] Onboarding flow
- [ ] Daily completion flow
- [ ] Tracker management flow
- [ ] Analytics flow
- [ ] Goal management flow
