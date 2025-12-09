# TrackPro Backend - Comprehensive Integration Testing Plan

**Version:** 1.0  
**Date:** 2025-12-09  
**Coverage:** V1.0 + V1.5 + V2.0 APIs and Services

---

## Table of Contents

1. [Testing Overview](#1-testing-overview)
2. [Test Environment Setup](#2-test-environment-setup)
3. [Authentication Tests](#3-authentication-tests)
4. [Tracker CRUD Tests](#4-tracker-crud-tests)
5. [Task & Template Tests](#5-task--template-tests)
6. [Instance Management Tests](#6-instance-management-tests)
7. [Goal & Progress Tests](#7-goal--progress-tests)
8. [Streak Tests](#8-streak-tests)
9. [Analytics Tests](#9-analytics-tests)
10. [Tag System Tests (V1.5)](#10-tag-system-tests-v15)
11. [Search System Tests (V1.5)](#11-search-system-tests-v15)
12. [Entity Relations Tests (V1.5)](#12-entity-relations-tests-v15)
13. [Share Link Tests](#13-share-link-tests)
14. [Knowledge Graph Tests (V2.0)](#14-knowledge-graph-tests-v20)
15. [Habit Intelligence Tests (V2.0)](#15-habit-intelligence-tests-v20)
16. [Activity Replay Tests (V2.0)](#16-activity-replay-tests-v20)
17. [Collaboration Tests (V2.0)](#17-collaboration-tests-v20)
18. [Edge Case Tests](#18-edge-case-tests)
19. [Performance Tests](#19-performance-tests)
20. [Test Execution Script](#20-test-execution-script)

---

## 1. Testing Overview

### Testing Goals
- Verify all 100 API endpoints function correctly
- Validate all 19 services work as expected
- Test all documented edge cases
- Ensure proper error handling and validation
- Confirm authentication and authorization work

### Testing Approach
1. **Unit Tests**: Test individual service methods
2. **Integration Tests**: Test API endpoints with real database
3. **Edge Case Tests**: Test boundary conditions and error paths
4. **Workflow Tests**: Test multi-step user journeys
5. **Performance Tests**: Test response times and load handling

### Test Data Strategy
- Create fresh test database for each test run
- Use Django's TestCase with transaction rollback
- Factory pattern for test data generation
- Fixtures for common scenarios

---

## 2. Test Environment Setup

### Directory Structure
```
core/tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── factories.py             # Test data factories
├── base.py                  # Base test class
├── test_auth.py             # Authentication tests
├── test_tracker.py          # Tracker CRUD
├── test_task.py             # Task operations
├── test_instance.py         # Instance management
├── test_goal.py             # Goal system
├── test_streak.py           # Streak calculations
├── test_analytics.py        # Analytics endpoints
├── test_tag.py              # V1.5 Tags
├── test_search.py           # V1.5 Search
├── test_relations.py        # V1.5 Dependencies
├── test_share.py            # Share links
├── test_knowledge_graph.py  # V2.0 Graph
├── test_habit_intel.py      # V2.0 Intelligence
├── test_activity_replay.py  # V2.0 Replay
├── test_collaboration.py    # V2.0 Collaboration
├── test_edge_cases.py       # Edge case suite
└── test_performance.py      # Performance suite
```

### Base Test Class
```python
# core/tests/base.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
import json

User = get_user_model()

class BaseAPITestCase(TestCase):
    """Base class for all API tests."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Get JWT token
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        self.token = response.json().get('access')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def assertSuccess(self, response):
        """Assert response indicates success."""
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', False))
        return data
    
    def assertError(self, response, status_code=400):
        """Assert response indicates error."""
        self.assertEqual(response.status_code, status_code)
        data = response.json()
        self.assertFalse(data.get('success', True))
        return data
```

### Test Factories
```python
# core/tests/factories.py
import uuid
from datetime import date, timedelta
from core.models import *

class TrackerFactory:
    @staticmethod
    def create(user, **kwargs):
        defaults = {
            'tracker_id': str(uuid.uuid4()),
            'name': 'Test Tracker',
            'time_mode': 'daily',
            'status': 'active'
        }
        defaults.update(kwargs)
        return TrackerDefinition.objects.create(user=user, **defaults)

class TemplateFactory:
    @staticmethod
    def create(tracker, **kwargs):
        defaults = {
            'template_id': str(uuid.uuid4()),
            'description': 'Test Task',
            'category': 'general',
            'points': 1,
            'weight': 1.0,
            'is_recurring': True
        }
        defaults.update(kwargs)
        return TaskTemplate.objects.create(tracker=tracker, **defaults)

class InstanceFactory:
    @staticmethod
    def create(tracker, target_date=None, **kwargs):
        if target_date is None:
            target_date = date.today()
        defaults = {
            'instance_id': str(uuid.uuid4()),
            'tracking_date': target_date,
            'period_start': target_date,
            'period_end': target_date,
            'status': 'active'
        }
        defaults.update(kwargs)
        return TrackerInstance.objects.create(tracker=tracker, **defaults)

class TaskInstanceFactory:
    @staticmethod
    def create(instance, template, **kwargs):
        defaults = {
            'task_instance_id': str(uuid.uuid4()),
            'status': 'TODO'
        }
        defaults.update(kwargs)
        return TaskInstance.objects.create(
            tracker_instance=instance,
            template=template,
            **defaults
        )
```

---

## 3. Authentication Tests

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| AUTH-001 | Login with valid credentials | POST /api/v1/auth/login/ with valid email/password | 200, returns access token |
| AUTH-002 | Login with invalid password | POST /api/v1/auth/login/ with wrong password | 401, "Invalid credentials" |
| AUTH-003 | Login with unknown email | POST /api/v1/auth/login/ with non-existent email | 401, "Invalid credentials" |
| AUTH-004 | Signup new user | POST /api/v1/auth/signup/ with valid data | 201, user created |
| AUTH-005 | Signup duplicate email | POST /api/v1/auth/signup/ with existing email | 400, "Email already exists" |
| AUTH-006 | Access protected endpoint without token | GET /api/v1/dashboard/ without Authorization header | 401, "Authentication required" |
| AUTH-007 | Access with invalid token | GET /api/v1/dashboard/ with malformed token | 401, "Invalid token" |
| AUTH-008 | Access with expired token | GET /api/v1/dashboard/ with expired token | 401, "Token expired" |
| AUTH-009 | Logout | POST /api/v1/auth/logout/ | 200, token invalidated |
| AUTH-010 | Check auth status | GET /api/v1/auth/status/ with valid token | 200, returns user info |
| AUTH-011 | Google OAuth flow | POST /api/v1/auth/google/ with valid Google token | 200, returns access token |
| AUTH-012 | Apple OAuth flow | POST /api/v1/auth/apple/mobile/ with valid Apple token | 200, returns access token |

### Edge Cases
- Empty email/password fields
- SQL injection attempts in login
- Rate limiting after multiple failed attempts
- Case sensitivity in email

---

## 4. Tracker CRUD Tests

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| TRACK-001 | Create tracker | POST /api/v1/tracker/create/ | 201, tracker created |
| TRACK-002 | Create with missing name | POST /api/v1/tracker/create/ without name | 400, validation error |
| TRACK-003 | Get tracker list | GET /api/v1/trackers/ | 200, returns array |
| TRACK-004 | Get tracker detail | GET /api/v1/tracker/{id}/ | 200, returns tracker |
| TRACK-005 | Get non-existent tracker | GET /api/v1/tracker/invalid-id/ | 404, not found |
| TRACK-006 | Update tracker | PUT /api/v1/tracker/{id}/update/ | 200, updated |
| TRACK-007 | Delete tracker (soft) | DELETE /api/v1/tracker/{id}/delete/ | 200, soft deleted |
| TRACK-008 | Get deleted tracker | GET /api/v1/tracker/{id}/ (after delete) | 404, not found |
| TRACK-009 | Restore tracker | POST /api/v1/tracker/{id}/restore/ | 200, restored |
| TRACK-010 | Clone tracker | POST /api/v1/tracker/{id}/clone/ | 201, clone created |
| TRACK-011 | Clone with custom name | POST /api/v1/tracker/{id}/clone/ with name | 201, uses custom name |
| TRACK-012 | Change time mode | POST /api/v1/tracker/{id}/change-mode/ | 200, mode changed |
| TRACK-013 | Change to invalid mode | POST /api/v1/tracker/{id}/change-mode/ with "yearly" | 400, invalid mode |
| TRACK-014 | Access other user's tracker | GET /api/v1/tracker/{other-user-id}/ | 404, not found |

### Edge Cases
- Restore with name conflict (should append "(Restored)")
- Clone tracker with no templates
- Change mode with existing future instances
- Very long tracker names/descriptions

---

## 5. Task & Template Tests

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| TASK-001 | Add task to tracker | POST /api/v1/tracker/{id}/task/add/ | 201, template created |
| TASK-002 | Toggle task status | POST /api/v1/task/{id}/toggle/ | 200, status toggled |
| TASK-003 | Set specific status | PUT /api/v1/task/{id}/status/ | 200, status set |
| TASK-004 | Edit task | PUT /api/v1/task/{id}/edit/ | 200, task updated |
| TASK-005 | Delete task | DELETE /api/v1/task/{id}/delete/ | 200, soft deleted |
| TASK-006 | Bulk task update | POST /api/v1/tasks/bulk/ | 200, all updated |
| TASK-007 | Reorder tasks | POST /api/v1/tracker/{id}/reorder/ | 200, weights updated |
| TASK-008 | Update task points | PUT /api/v1/task/{id}/points/ | 200, points updated |
| TASK-009 | Toggle task goal inclusion | POST /api/v1/task/{id}/toggle-goal/ | 200, toggled |
| TASK-010 | Get task points breakdown | GET /api/v1/tracker/{id}/points-breakdown/ | 200, breakdown returned |

### Edge Cases
- Toggle completed task (first_completed_at shouldn't change)
- Status oscillation (DONE -> TODO -> DONE)
- Negative points attempt
- Delete template with active task instances
- Bulk update with invalid task IDs

---

## 6. Instance Management Tests

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| INST-001 | Get/create today's instance | GET /dashboard/today/ | 200, instance created if needed |
| INST-002 | Generate instances for range | POST /api/v1/tracker/{id}/instances/generate/ | 200, instances created |
| INST-003 | Get week aggregation | GET /api/v1/tracker/{id}/week/ | 200, weekly data |
| INST-004 | Fill missing instances | POST with mark_missed=true | 200, missed tasks marked |
| INST-005 | Get trackers for date | GET /dashboard/trackers/?date=2025-12-01 | 200, trackers for date |

### Edge Cases
- Generate overlapping date ranges
- Instance for weekly tracker
- Instance for monthly tracker
- Future date instances
- Past date instances (backdating)
- More than 365 days range (should fail)

---

## 7. Goal & Progress Tests

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| GOAL-001 | Create goal | POST /api/v1/goals/ | 201, goal created |
| GOAL-002 | List goals | GET /api/v1/goals/ | 200, goals with progress |
| GOAL-003 | Goal auto-update on task | Complete task linked to goal | Goal progress increases |
| GOAL-004 | Goal with deleted template | Delete template linked to goal | Progress recalculates |
| GOAL-005 | Change target mid-way | Update goal target_value | Status recalculated |
| GOAL-006 | Achieved goal status | Complete all linked tasks | Status becomes 'achieved' |
| GOAL-007 | Goal insights | GET /api/v1/goals/ | Returns velocity, on_track |

### Edge Cases
- Goal with target_date in past
- Goal with target_value of 0
- Multiple goals sharing same template
- Weight contribution calculation
- Goal attached to deleted tracker

---

## 8. Streak Tests

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| STRK-001 | Calculate current streak | GET /dashboard/streaks/ | Returns current_streak |
| STRK-002 | Streak with threshold | User with 80% threshold | 75% day breaks streak |
| STRK-003 | Streak broken by gap | No instance for yesterday | Streak is 0 or 1 |
| STRK-004 | Longest streak tracking | Check longest_streak field | Correct historical max |
| STRK-005 | Weekly tracker streak | Weekly mode streak calc | Counts weeks, not days |
| STRK-006 | Streak milestone notification | Reach 7-day streak | Notification created |

### Edge Cases
- Streak across timezone changes
- Multiple trackers with different thresholds
- Partial completion (50% of tasks)
- First day of tracking (streak = 1)

---

## 9. Analytics Tests

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| ANAL-001 | Get analytics data | GET /api/v1/analytics/data/ | Returns summary |
| ANAL-002 | Get heatmap data | GET /api/v1/heatmap/ | Year of activity levels |
| ANAL-003 | Get tracker analytics | GET /api/v1/analytics/data/?tracker_id=X | Tracker-specific |
| ANAL-004 | Compare trackers | GET /api/v1/analytics/compare/?trackers=X,Y | Comparison data |
| ANAL-005 | Get insights | GET /api/v1/insights/ | Best day, missed tasks |
| ANAL-006 | Chart data | GET /api/v1/chart-data/ | Chart-ready data |

### Edge Cases
- Analytics with no data
- Analytics with 1 day of data
- Analytics with gaps in data
- Very old date ranges
- Deleted tracker in comparison

---

## 10. Tag System Tests (V1.5)

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| TAG-001 | Create tag | POST /api/v1/tags/ | 201, tag created |
| TAG-002 | List tags with counts | GET /api/v1/tags/ | Tags with usage_count |
| TAG-003 | Update tag | PUT /api/v1/tags/{id}/ | 200, tag updated |
| TAG-004 | Delete tag | DELETE /api/v1/tags/{id}/ | 200, tag deleted |
| TAG-005 | Add tag to template | POST /api/v1/template/{id}/tag/{tag_id}/ | 200, association created |
| TAG-006 | Remove tag from template | POST with action=remove | 200, association removed |
| TAG-007 | Get tasks by tag | GET /api/v1/tasks/by-tag/?tags=X,Y | Filtered tasks |
| TAG-008 | Get tag analytics | GET /api/v1/tags/analytics/ | Tag-wise completion |

### Edge Cases
- Duplicate tag name
- Delete tag with associations
- Tag with special characters
- Very long tag name
- Tag color validation

---

## 11. Search System Tests (V1.5)

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| SRCH-001 | Basic search | GET /api/v1/search/?q=gym | Matching results |
| SRCH-002 | Empty search | GET /api/v1/search/?q= | Recent/popular items |
| SRCH-003 | Get suggestions | GET /api/v1/search/suggestions/?q=gy | Auto-complete results |
| SRCH-004 | Get search history | GET /api/v1/search/history/ | Recent searches |
| SRCH-005 | Get popular searches | GET /api/v1/search/history/?type=popular | Popular searches |
| SRCH-006 | Clear search history | POST /api/v1/search/history/clear/ | History cleared |
| SRCH-007 | Clear old history only | POST with older_than_days=30 | Old entries cleared |
| SRCH-008 | Search includes tags | Search for tag name | Tag in results |

### Edge Cases
- SQL injection in search query
- Very long search query
- Special characters in query
- Search with no results

---

## 12. Entity Relations Tests (V1.5)

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| REL-001 | Create dependency | POST /api/v1/template/{id}/dependencies/ | Dependency created |
| REL-002 | Get dependencies | GET /api/v1/template/{id}/dependencies/ | Dependencies listed |
| REL-003 | Remove dependency | POST /{id}/dependencies/{target}/remove/ | Dependency removed |
| REL-004 | Check task blocked | GET /api/v1/task/{id}/blocked/ | Blocked status |
| REL-005 | Get dependency graph | GET /api/v1/tracker/{id}/dependency-graph/ | Graph data |
| REL-006 | Circular dependency prevention | Create A->B->A | 400, cycle detected |

### Edge Cases
- Self-dependency (A depends on A)
- Long dependency chain
- Dependency on deleted template
- Multiple relation types

---

## 13. Share Link Tests

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| SHR-001 | Create share link | POST /api/v1/tracker/{id}/share/create/ | Link created |
| SHR-002 | Create with password | POST with password | Password hash stored |
| SHR-003 | Create with expiration | POST with expires_in_days=7 | Expiration set |
| SHR-004 | Create with max uses | POST with max_uses=10 | Limit set |
| SHR-005 | List share links | GET /api/v1/shares/ | User's links |
| SHR-006 | Deactivate link | POST /api/v1/share/{token}/deactivate/ | Link deactivated |
| SHR-007 | Access expired link | Access after expiration | 403, expired |
| SHR-008 | Access with wrong password | Wrong password | 403, invalid password |
| SHR-009 | Exceed max uses | Access after limit | 403, limit reached |

### Edge Cases
- Concurrent access at max_uses limit
- Token regeneration
- Access deactivated link
- Very long password

---

## 14. Knowledge Graph Tests (V2.0)

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| GRAPH-001 | Get full graph | GET /api/v1/v2/knowledge-graph/ | Nodes and edges |
| GRAPH-002 | Include notes | GET with include_notes=true | Notes included |
| GRAPH-003 | Get entity connections | GET /api/v1/v2/graph/tracker/{id}/ | Connected entities |
| GRAPH-004 | Explore depth | GET with depth=3 | 3 levels explored |
| GRAPH-005 | Find path | GET /api/v1/v2/graph/path/?source...target | Path found |
| GRAPH-006 | No path exists | Find path between unconnected | path_found: false |

### Edge Cases
- Graph with no data
- Very large graph (performance)
- Circular relationships in graph
- Path to deleted entity

---

## 15. Habit Intelligence Tests (V2.0)

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| HABIT-001 | Get all insights | GET /api/v1/v2/insights/habits/ | Insights array |
| HABIT-002 | Day of week analysis | GET /api/v1/v2/insights/day-analysis/ | Best/worst days |
| HABIT-003 | Task difficulty | GET /api/v1/v2/insights/difficulty/ | Difficulty rankings |
| HABIT-004 | Schedule suggestions | GET /api/v1/v2/insights/schedule/ | Suggestions array |
| HABIT-005 | With custom days | GET with days=30 | 30-day analysis |

### Edge Cases
- Analysis with < 14 days of data
- All tasks at 100% completion
- All tasks at 0% completion
- Missing days in data

---

## 16. Activity Replay Tests (V2.0)

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| REPLAY-001 | Get timeline | GET /api/v1/v2/timeline/ | Activity events |
| REPLAY-002 | Timeline with date range | GET with start_date, end_date | Filtered events |
| REPLAY-003 | Day snapshot | GET /api/v1/v2/snapshot/2025-12-09/ | Full day state |
| REPLAY-004 | Compare periods | GET /api/v1/v2/compare/?p1_start... | Comparison data |
| REPLAY-005 | Weekly comparison | GET /api/v1/v2/compare/weekly/ | Week-over-week |
| REPLAY-006 | Entity history | GET /api/v1/v2/history/tracker/{id}/ | Change history |

### Edge Cases
- Snapshot for day with no data
- Compare non-overlapping periods
- Very long timeline (limit)
- History for deleted entity

---

## 17. Collaboration Tests (V2.0)

### Test Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| COLLAB-001 | View shared tracker | GET /api/v1/v2/shared/{token}/ | Tracker data (public) |
| COLLAB-002 | View with password | GET with password param | Access granted |
| COLLAB-003 | Get shared instances | GET /api/v1/v2/shared/{token}/instances/ | Instance list |
| COLLAB-004 | Update shared task | POST /{token}/task/{id}/ with edit permission | Task updated |
| COLLAB-005 | Update without edit | POST with view-only token | 403, permission denied |
| COLLAB-006 | Add note | POST /{token}/instance/{id}/note/ | Note added |
| COLLAB-007 | Create invite | POST /api/v1/v2/tracker/{id}/invite/ | Invite created |
| COLLAB-008 | Invite with permissions | POST with permission=edit | Edit permission set |

### Edge Cases
- Update task in expired share
- Multiple collaborators editing
- Note from anonymous user
- Very long note content

---

## 18. Edge Case Tests

### Time & Timezone Edge Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| EDGE-001 | Timezone boundary | Task completed at 11:59pm local | Correct day assignment |
| EDGE-002 | User changes timezone | Change from UTC to PST | "Today" shifts correctly |
| EDGE-003 | DST transition | Task during DST change | No duplicate/missing days |

### Data Integrity Edge Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| EDGE-010 | Concurrent instance creation | Two requests for same date | Only one instance created |
| EDGE-011 | Cascade soft delete | Delete tracker | All children soft deleted |
| EDGE-012 | Restore with children | Restore tracker | Children restored |
| EDGE-013 | Goal with all deleted mappings | All templates deleted | Progress goes to 0 |

### Security Edge Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| EDGE-020 | CSRF protection | POST without CSRF token | 403 or exempt |
| EDGE-021 | SQL injection | Search with SQL payload | Sanitized, no error |
| EDGE-022 | XSS in notes | Script tags in note content | Stored as plain text |
| EDGE-023 | Path traversal | ../ in file paths | Rejected |

### Validation Edge Cases

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| EDGE-030 | Negative points | Set points=-5 | Validation error |
| EDGE-031 | Future goal target date | target_date = today + 365 | Accepted |
| EDGE-032 | Past goal target date | target_date = yesterday | Warning or rejected |
| EDGE-033 | Empty tracker name | name="" | Validation error |

---

## 19. Performance Tests

### Load Tests

| Test ID | Test Name | Target | Threshold |
|---------|-----------|--------|-----------|
| PERF-001 | Dashboard load | 100 concurrent users | < 500ms p95 |
| PERF-002 | Task toggle | 1000 req/sec | < 100ms p95 |
| PERF-003 | Analytics query | 365 days of data | < 1s |
| PERF-004 | Knowledge graph | 100 trackers, 500 templates | < 2s |
| PERF-005 | Search | 10,000 items | < 200ms |

### Stress Tests

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| STRESS-001 | Bulk instance creation | Generate 365 instances at once |
| STRESS-002 | Large graph traversal | Graph with 10,000 nodes |
| STRESS-003 | Concurrent share access | 100 users hitting same link |

---

## 20. Test Execution Script

### Run All Tests
```bash
# Full test suite
python manage.py test core.tests --verbosity=2

# Specific test module
python manage.py test core.tests.test_auth
python manage.py test core.tests.test_tracker
python manage.py test core.tests.test_edge_cases

# With coverage
pip install coverage
coverage run manage.py test core.tests
coverage report -m
coverage html  # Generate HTML report

# Parallel execution
python manage.py test core.tests --parallel 4
```

### CI/CD Integration
```yaml
# .github/workflows/test.yml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:latest
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install coverage pytest-django
      
      - name: Run tests
        run: |
          coverage run manage.py test core.tests
          coverage report -m --fail-under=80
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

### Test Data Reset Script
```python
# scripts/reset_test_data.py
from django.core.management import call_command

def reset_test_database():
    """Reset database to clean state for testing."""
    call_command('flush', '--no-input')
    call_command('migrate', '--run-syncdb')
    # Add seed data if needed
```

---

## Summary

### Total Test Cases by Category

| Category | Test Count |
|----------|------------|
| Authentication | 12 |
| Tracker CRUD | 14 |
| Task & Template | 10 |
| Instance Management | 5 |
| Goals | 7 |
| Streaks | 6 |
| Analytics | 6 |
| Tags (V1.5) | 8 |
| Search (V1.5) | 8 |
| Entity Relations (V1.5) | 6 |
| Share Links | 9 |
| Knowledge Graph (V2.0) | 6 |
| Habit Intelligence (V2.0) | 5 |
| Activity Replay (V2.0) | 6 |
| Collaboration (V2.0) | 8 |
| Edge Cases | 15 |
| Performance | 8 |
| **Total** | **139** |

### Coverage Goals
- **Line Coverage**: > 80%
- **Branch Coverage**: > 70%
- **Endpoint Coverage**: 100%
- **Edge Case Coverage**: 100%

---

**Document Version:** 1.0  
**Author:** TrackPro Team  
**Last Updated:** 2025-12-09
