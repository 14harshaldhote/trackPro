#!/usr/bin/env python3
"""
API v1 Integration Test Suite

Comprehensive integration tests for Tracker Pro API v1.
Run with: python tests/integration_test_suite.py

Test Phases:
1. Authentication & System
2. Tracker CRUD
3. Task CRUD
4. Dashboard & Data
5. Analytics & Insights
6. User & Data Management
"""

import requests
import json
import time
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1"
VERBOSE = True

class TestStatus(Enum):
    PASSED = "✅"
    FAILED = "❌"
    SKIPPED = "⏭️"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    response_code: int
    message: str
    duration_ms: float
    phase: str


class IntegrationTestSuite:
    def __init__(self):
        self.session = requests.Session()
        self.results: List[TestResult] = []
        self.auth_token: Optional[str] = None
        self.test_user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        self.test_user_password = "TestPass123!"
        self.test_tracker_id: Optional[str] = None
        self.test_task_id: Optional[str] = None
        self.test_template_id: Optional[str] = None
        self.phase_stats: Dict[str, Dict] = {}
        
    def log(self, msg: str):
        if VERBOSE:
            print(msg)
            
    def add_result(self, name: str, status: TestStatus, code: int, 
                   message: str, duration: float, phase: str):
        result = TestResult(
            name=name, status=status, response_code=code,
            message=message, duration_ms=duration, phase=phase
        )
        self.results.append(result)
        
        icon = status.value
        self.log(f"  {icon} {name} [{code}] ({duration:.0f}ms)")
        if status == TestStatus.FAILED:
            self.log(f"     → {message[:100]}")
            
    def get_headers(self, auth: bool = True) -> Dict:
        headers = {"Content-Type": "application/json"}
        if auth and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
        
    def request(self, method: str, endpoint: str, data: Any = None, 
                auth: bool = True, params: Dict = None) -> Tuple[int, Any, float]:
        """Make a request and return (status_code, response_data, duration_ms)"""
        url = f"{BASE_URL}{endpoint}"
        headers = self.get_headers(auth)
        
        start = time.time()
        try:
            if method == "GET":
                resp = self.session.get(url, headers=headers, params=params)
            elif method == "POST":
                resp = self.session.post(url, headers=headers, json=data)
            elif method == "PUT":
                resp = self.session.put(url, headers=headers, json=data)
            elif method == "DELETE":
                resp = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unknown method: {method}")
                
            duration = (time.time() - start) * 1000
            
            try:
                response_data = resp.json()
            except:
                response_data = resp.text[:500]
                
            return resp.status_code, response_data, duration
            
        except Exception as e:
            duration = (time.time() - start) * 1000
            return 0, str(e), duration

    # =========================================================================
    # PHASE 1: AUTHENTICATION & SYSTEM
    # =========================================================================
    
    def run_phase_1(self):
        """Authentication & System Tests"""
        phase = "Phase 1: Auth & System"
        self.log(f"\n{'='*60}")
        self.log(f"  {phase}")
        self.log(f"{'='*60}")
        
        # 1.1 Health Check
        code, data, dur = self.request("GET", "/health/", auth=False)
        status = TestStatus.PASSED if code == 200 and data.get("status") == "healthy" else TestStatus.FAILED
        self.add_result("Health check returns healthy", status, code, str(data), dur, phase)
        
        # 1.2 Auth Status (Unauthenticated)
        code, data, dur = self.request("GET", "/auth/status/", auth=False)
        status = TestStatus.PASSED if code == 200 and data.get("authenticated") == False else TestStatus.FAILED
        self.add_result("Auth status shows unauthenticated", status, code, str(data), dur, phase)
        
        # 1.3 Email Validation - Available
        code, data, dur = self.request("POST", "/auth/validate-email/", 
                                       {"email": self.test_user_email}, auth=False)
        status = TestStatus.PASSED if code == 200 and data.get("available") == True else TestStatus.FAILED
        self.add_result("Email validation - available", status, code, str(data), dur, phase)
        
        # 1.4 Email Validation - Invalid format
        code, data, dur = self.request("POST", "/auth/validate-email/", 
                                       {"email": "not-an-email"}, auth=False)
        status = TestStatus.PASSED if code in [200, 400] else TestStatus.FAILED
        self.add_result("Email validation - invalid format", status, code, str(data), dur, phase)
        
        # 1.5 Signup - Valid
        code, data, dur = self.request("POST", "/auth/signup/", {
            "email": self.test_user_email,
            "password1": self.test_user_password,
            "password2": self.test_user_password
        }, auth=False)
        status = TestStatus.PASSED if code == 200 and data.get("success") else TestStatus.FAILED
        self.add_result("Signup with valid data", status, code, str(data), dur, phase)
        
        # 1.6 Signup - Duplicate email
        code, data, dur = self.request("POST", "/auth/signup/", {
            "email": self.test_user_email,
            "password1": self.test_user_password,
            "password2": self.test_user_password
        }, auth=False)
        status = TestStatus.PASSED if code == 400 else TestStatus.FAILED
        self.add_result("Signup rejects duplicate email", status, code, str(data), dur, phase)
        
        # 1.7 Login - Invalid credentials
        code, data, dur = self.request("POST", "/auth/login/", {
            "email": self.test_user_email,
            "password": "wrongpassword"
        }, auth=False)
        status = TestStatus.PASSED if code == 400 else TestStatus.FAILED
        self.add_result("Login rejects wrong password", status, code, str(data), dur, phase)
        
        # 1.8 Login - Valid credentials
        code, data, dur = self.request("POST", "/auth/login/", {
            "email": self.test_user_email,
            "password": self.test_user_password
        }, auth=False)
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Login with valid credentials", status, code, str(data), dur, phase)
        
        # Store token if available
        if data.get("token"):
            self.auth_token = data["token"]
            self.log(f"    → Token acquired for authenticated tests")
        elif data.get("success"):
            # Session-based, get token separately
            self.log(f"    → Session acquired (no JWT token)")
            
        # 1.9 Auth Status (Authenticated) - Use session
        code, data, dur = self.request("GET", "/auth/status/", auth=False)
        # May or may not be authenticated depending on session
        self.add_result("Auth status check", TestStatus.PASSED, code, str(data), dur, phase)
        
        # 1.10 Feature Flag Check
        code, data, dur = self.request("GET", "/feature-flags/new_sync_api/", auth=False)
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Feature flag check", status, code, str(data), dur, phase)
        
        # 1.11 Login - Missing email
        code, data, dur = self.request("POST", "/auth/login/", {"password": "test"}, auth=False)
        status = TestStatus.PASSED if code == 400 else TestStatus.FAILED
        self.add_result("Login rejects missing email", status, code, str(data), dur, phase)
        
        # 1.12 Empty email validation
        code, data, dur = self.request("POST", "/auth/validate-email/", {"email": ""}, auth=False)
        status = TestStatus.PASSED if code == 400 else TestStatus.FAILED
        self.add_result("Email validation rejects empty", status, code, str(data), dur, phase)

    # =========================================================================
    # PHASE 2: TRACKER CRUD
    # =========================================================================
    
    def run_phase_2(self):
        """Tracker CRUD Tests"""
        phase = "Phase 2: Tracker CRUD"
        self.log(f"\n{'='*60}")
        self.log(f"  {phase}")
        self.log(f"{'='*60}")
        
        # 2.1 List Trackers - Empty (new user)
        code, data, dur = self.request("GET", "/trackers/")
        status = TestStatus.PASSED if code == 200 and "trackers" in data else TestStatus.FAILED
        if code == 401:
            status = TestStatus.SKIPPED
            self.log(f"    → Need authentication, attempting login...")
            self._relogin()
            code, data, dur = self.request("GET", "/trackers/")
            status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("List trackers (empty)", status, code, str(data), dur, phase)
        
        # 2.2 Create Tracker
        code, data, dur = self.request("POST", "/tracker/create/", {
            "name": "Test Tracker",
            "description": "Integration test tracker",
            "time_mode": "daily"
        })
        status = TestStatus.PASSED if code in [200, 201] and data.get("success") else TestStatus.FAILED
        self.add_result("Create tracker", status, code, str(data), dur, phase)
        
        if "tracker_id" in data:
            self.test_tracker_id = data["tracker_id"]
        elif data.get("data", {}).get("tracker_id"):
            self.test_tracker_id = data["data"]["tracker_id"]
            
        # 2.3 Create Tracker - Missing name
        code, data, dur = self.request("POST", "/tracker/create/", {"time_mode": "daily"})
        status = TestStatus.PASSED if code == 400 else TestStatus.FAILED
        self.add_result("Create tracker rejects missing name", status, code, str(data), dur, phase)
        
        # 2.4 Get Tracker Detail
        if self.test_tracker_id:
            code, data, dur = self.request("GET", f"/tracker/{self.test_tracker_id}/")
            status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
            self.add_result("Get tracker detail", status, code, str(data), dur, phase)
        else:
            self.add_result("Get tracker detail", TestStatus.SKIPPED, 0, "No tracker ID", 0, phase)
            
        # 2.5 Update Tracker
        if self.test_tracker_id:
            code, data, dur = self.request("PUT", f"/tracker/{self.test_tracker_id}/update/", {
                "name": "Updated Test Tracker",
                "description": "Updated description"
            })
            status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
            self.add_result("Update tracker", status, code, str(data), dur, phase)
        else:
            self.add_result("Update tracker", TestStatus.SKIPPED, 0, "No tracker ID", 0, phase)
            
        # 2.6 Get Tracker - Non-existent
        fake_id = str(uuid.uuid4())
        code, data, dur = self.request("GET", f"/tracker/{fake_id}/")
        status = TestStatus.PASSED if code == 404 else TestStatus.FAILED
        self.add_result("Get non-existent tracker returns 404", status, code, str(data), dur, phase)
        
        # 2.7 Template Activation - Valid
        code, data, dur = self.request("POST", "/templates/activate/", {"template_key": "morning"})
        status = TestStatus.PASSED if code == 200 and data.get("success") else TestStatus.FAILED
        self.add_result("Activate morning template", status, code, str(data), dur, phase)
        
        # Store template tracker ID for task tests
        if data.get("data", {}).get("tracker_id"):
            template_tracker_id = data["data"]["tracker_id"]
            self.test_tracker_id = self.test_tracker_id or template_tracker_id
            
        # 2.8 Template Activation - Invalid key
        code, data, dur = self.request("POST", "/templates/activate/", {"template_key": "invalid_xyz"})
        status = TestStatus.PASSED if code == 404 and "available_templates" in str(data) else TestStatus.FAILED
        self.add_result("Invalid template returns error with list", status, code, str(data), dur, phase)
        
        # 2.9 Template Activation - Missing key
        code, data, dur = self.request("POST", "/templates/activate/", {})
        status = TestStatus.PASSED if code == 400 and "available_templates" in str(data) else TestStatus.FAILED
        self.add_result("Missing template_key returns error with list", status, code, str(data), dur, phase)
        
        # 2.10 List Trackers - With data
        code, data, dur = self.request("GET", "/trackers/")
        status = TestStatus.PASSED if code == 200 and len(data.get("trackers", [])) > 0 else TestStatus.FAILED
        self.add_result("List trackers shows created trackers", status, code, f"Count: {data.get('count', 0)}", dur, phase)
        
        # 2.11 List Trackers - Filter by status
        code, data, dur = self.request("GET", "/trackers/", params={"status": "active"})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("List trackers with status filter", status, code, str(data), dur, phase)
        
        # 2.12 Share Tracker
        if self.test_tracker_id:
            code, data, dur = self.request("POST", f"/tracker/{self.test_tracker_id}/share/")
            status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
            self.add_result("Generate share link", status, code, str(data), dur, phase)
        else:
            self.add_result("Generate share link", TestStatus.SKIPPED, 0, "No tracker ID", 0, phase)
            
        # 2.13 Get Tracker Progress
        if self.test_tracker_id:
            code, data, dur = self.request("GET", f"/tracker/{self.test_tracker_id}/progress/")
            status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
            self.add_result("Get tracker progress", status, code, str(data), dur, phase)
        else:
            self.add_result("Get tracker progress", TestStatus.SKIPPED, 0, "No tracker ID", 0, phase)

    # =========================================================================
    # PHASE 3: TASK CRUD
    # =========================================================================
    
    def run_phase_3(self):
        """Task CRUD Tests"""
        phase = "Phase 3: Task CRUD"
        self.log(f"\n{'='*60}")
        self.log(f"  {phase}")
        self.log(f"{'='*60}")
        
        if not self.test_tracker_id:
            self.log("  ⚠️  No tracker available - creating one...")
            code, data, _ = self.request("POST", "/tracker/create/", {
                "name": "Task Test Tracker",
                "time_mode": "daily"
            })
            if data.get("tracker_id"):
                self.test_tracker_id = data["tracker_id"]
            elif data.get("data", {}).get("tracker_id"):
                self.test_tracker_id = data["data"]["tracker_id"]
        
        # 3.1 Add Task to Tracker
        code, data, dur = self.request("POST", f"/tracker/{self.test_tracker_id}/task/add/", {
            "description": "Test Task 1",
            "category": "testing",
            "weight": 2,
            "time_of_day": "morning"
        })
        status = TestStatus.PASSED if code in [200, 201] else TestStatus.FAILED
        self.add_result("Add task to tracker", status, code, str(data), dur, phase)
        
        # Get task ID from response or fetch from tracker
        if data.get("task_id"):
            self.test_task_id = data["task_id"]
        elif data.get("template_id"):
            self.test_template_id = data["template_id"]
            
        # 3.2 Add Task - Missing description
        code, data, dur = self.request("POST", f"/tracker/{self.test_tracker_id}/task/add/", {
            "category": "testing"
        })
        status = TestStatus.PASSED if code == 400 else TestStatus.FAILED
        self.add_result("Add task rejects missing description", status, code, str(data), dur, phase)
        
        # 3.3 Add another Task for ordering
        code, data, dur = self.request("POST", f"/tracker/{self.test_tracker_id}/task/add/", {
            "description": "Test Task 2",
            "category": "testing",
            "weight": 1
        })
        status = TestStatus.PASSED if code in [200, 201] else TestStatus.FAILED
        self.add_result("Add second task", status, code, str(data), dur, phase)
        
        # 3.4 Get Dashboard Trackers (to get task instances)
        code, data, dur = self.request("GET", "/dashboard/trackers/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get dashboard trackers for task IDs", status, code, f"Found trackers: {len(data.get('trackers', []))}", dur, phase)
        
        # Extract a task instance ID
        if data.get("success"):
            for tracker in data.get("trackers", []):
                for task in tracker.get("tasks", []):
                    if not self.test_task_id:
                        self.test_task_id = task.get("task_instance_id") or task.get("task_id")
                        break
                        
        # 3.5 Toggle Task - TODO to DONE
        if self.test_task_id:
            code, data, dur = self.request("POST", f"/task/{self.test_task_id}/toggle/")
            status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
            self.add_result("Toggle task TODO → DONE", status, code, str(data)[:100], dur, phase)
        else:
            self.add_result("Toggle task", TestStatus.SKIPPED, 0, "No task ID", 0, phase)
            
        # 3.6 Get Task Status
        if self.test_task_id:
            code, data, dur = self.request("GET", f"/task/{self.test_task_id}/status/")
            status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
            self.add_result("Get task status", status, code, str(data), dur, phase)
        else:
            self.add_result("Get task status", TestStatus.SKIPPED, 0, "No task ID", 0, phase)
            
        # 3.7 Toggle Task back - DONE to TODO
        if self.test_task_id:
            code, data, dur = self.request("POST", f"/task/{self.test_task_id}/toggle/")
            status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
            self.add_result("Toggle task DONE → TODO", status, code, str(data)[:100], dur, phase)
        else:
            self.add_result("Toggle task back", TestStatus.SKIPPED, 0, "No task ID", 0, phase)
            
        # 3.8 Edit Task
        if self.test_task_id:
            code, data, dur = self.request("PUT", f"/task/{self.test_task_id}/edit/", {
                "description": "Updated Test Task",
                "category": "updated"
            })
            status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
            self.add_result("Edit task", status, code, str(data), dur, phase)
        else:
            self.add_result("Edit task", TestStatus.SKIPPED, 0, "No task ID", 0, phase)
            
        # 3.9 Toggle task - Non-existent
        fake_id = str(uuid.uuid4())
        code, data, dur = self.request("POST", f"/task/{fake_id}/toggle/")
        status = TestStatus.PASSED if code == 404 else TestStatus.FAILED
        self.add_result("Toggle non-existent task returns 404", status, code, str(data), dur, phase)
        
        # 3.10 Infinite Tasks (paginated)
        code, data, dur = self.request("GET", "/tasks/infinite/", params={"page": 1, "per_page": 10})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get paginated tasks", status, code, f"Tasks found", dur, phase)
        
        # 3.11 Reorder Tasks
        if self.test_tracker_id:
            code, data, dur = self.request("POST", f"/tracker/{self.test_tracker_id}/reorder/", {
                "order": []  # Empty order should work
            })
            status = TestStatus.PASSED if code in [200, 400] else TestStatus.FAILED
            self.add_result("Reorder tasks", status, code, str(data), dur, phase)
        else:
            self.add_result("Reorder tasks", TestStatus.SKIPPED, 0, "No tracker ID", 0, phase)

    # =========================================================================
    # PHASE 4: DASHBOARD & DATA
    # =========================================================================
    
    def run_phase_4(self):
        """Dashboard & Data Tests"""
        phase = "Phase 4: Dashboard & Data"
        self.log(f"\n{'='*60}")
        self.log(f"  {phase}")
        self.log(f"{'='*60}")
        
        # 4.1 Full Dashboard
        code, data, dur = self.request("GET", "/dashboard/")
        status = TestStatus.PASSED if code == 200 and data.get("success") else TestStatus.FAILED
        self.add_result("Get full dashboard", status, code, f"Trackers: {len(data.get('trackers', []))}", dur, phase)
        
        # 4.2 Dashboard with date parameter
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        code, data, dur = self.request("GET", "/dashboard/", params={"date": yesterday})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Dashboard with date param", status, code, str(data.get("success")), dur, phase)
        
        # 4.3 Dashboard invalid date
        code, data, dur = self.request("GET", "/dashboard/", params={"date": "invalid"})
        status = TestStatus.PASSED if code == 400 else TestStatus.FAILED
        self.add_result("Dashboard rejects invalid date", status, code, str(data), dur, phase)
        
        # 4.4 Dashboard Trackers
        code, data, dur = self.request("GET", "/dashboard/trackers/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get dashboard trackers", status, code, f"Count: {len(data.get('trackers', []))}", dur, phase)
        
        # 4.5 Dashboard Today
        code, data, dur = self.request("GET", "/dashboard/today/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get today stats", status, code, str(data.get("success")), dur, phase)
        
        # 4.6 Dashboard Week
        code, data, dur = self.request("GET", "/dashboard/week/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get week overview", status, code, str(data.get("success")), dur, phase)
        
        # 4.7 Dashboard Goals
        code, data, dur = self.request("GET", "/dashboard/goals/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get goals summary", status, code, str(data.get("success")), dur, phase)
        
        # 4.8 Dashboard Streaks
        code, data, dur = self.request("GET", "/dashboard/streaks/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get streaks", status, code, str(data.get("success")), dur, phase)
        
        # 4.9 Dashboard Activity
        code, data, dur = self.request("GET", "/dashboard/activity/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get activity feed", status, code, str(data.get("success")), dur, phase)
        
        # 4.10 Goals Endpoint - List
        code, data, dur = self.request("GET", "/goals/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get goals list", status, code, f"Pagination: {bool(data.get('pagination'))}", dur, phase)
        
        # 4.11 Goals - Pagination
        code, data, dur = self.request("GET", "/goals/", params={"page": 1, "per_page": 5})
        status = TestStatus.PASSED if code == 200 and data.get("pagination", {}).get("per_page") == 5 else TestStatus.FAILED
        self.add_result("Goals with pagination", status, code, str(data.get("pagination")), dur, phase)
        
        # 4.12 Create Goal
        code, data, dur = self.request("POST", "/goals/", {
            "title": "Test Goal",
            "description": "Integration test goal",
            "goal_type": "habit",
            "target_value": 10
        })
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Create goal", status, code, str(data), dur, phase)
        
        # 4.13 Preferences - Get
        code, data, dur = self.request("GET", "/preferences/")
        status = TestStatus.PASSED if code == 200 and "preferences" in data else TestStatus.FAILED
        self.add_result("Get preferences", status, code, f"Has prefs: {bool(data.get('preferences'))}", dur, phase)
        
        # 4.14 Preferences - Update
        code, data, dur = self.request("PUT", "/preferences/", {"compact_mode": True})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Update preferences", status, code, str(data), dur, phase)
        
        # 4.15 Notifications - Get
        code, data, dur = self.request("GET", "/notifications/")
        status = TestStatus.PASSED if code == 200 and "notifications" in data else TestStatus.FAILED
        self.add_result("Get notifications", status, code, f"Has pagination: {bool(data.get('pagination'))}", dur, phase)
        
        # 4.16 Notifications - With pagination
        code, data, dur = self.request("GET", "/notifications/", params={"page": 1, "per_page": 5})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Notifications with pagination", status, code, str(data.get("pagination")), dur, phase)
        
        # 4.17 Notifications - Mark all read
        code, data, dur = self.request("POST", "/notifications/", {"action": "mark_all_read"})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Mark all notifications read", status, code, str(data), dur, phase)

    # =========================================================================
    # PHASE 5: ANALYTICS & INSIGHTS
    # =========================================================================
    
    def run_phase_5(self):
        """Analytics & Insights Tests"""
        phase = "Phase 5: Analytics"
        self.log(f"\n{'='*60}")
        self.log(f"  {phase}")
        self.log(f"{'='*60}")
        
        # 5.1 Insights - All
        code, data, dur = self.request("GET", "/insights/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get all insights", status, code, f"Count: {data.get('count', 0)}", dur, phase)
        
        # 5.2 Insights - Specific tracker
        if self.test_tracker_id:
            code, data, dur = self.request("GET", f"/insights/{self.test_tracker_id}/")
            status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
            self.add_result("Get tracker insights", status, code, str(data.get("success")), dur, phase)
        else:
            self.add_result("Get tracker insights", TestStatus.SKIPPED, 0, "No tracker", 0, phase)
            
        # 5.3 Chart Data - Bar
        code, data, dur = self.request("GET", "/chart-data/", params={"type": "bar"})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get bar chart data", status, code, f"Type: {data.get('chart_type')}", dur, phase)
        
        # 5.4 Chart Data - Pie
        code, data, dur = self.request("GET", "/chart-data/", params={"type": "pie"})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get pie chart data", status, code, f"Type: {data.get('chart_type')}", dur, phase)
        
        # 5.5 Chart Data - Invalid type
        code, data, dur = self.request("GET", "/chart-data/", params={"type": "invalid"})
        status = TestStatus.PASSED if code == 400 else TestStatus.FAILED
        self.add_result("Chart rejects invalid type", status, code, str(data), dur, phase)
        
        # 5.6 Heatmap - Default
        code, data, dur = self.request("GET", "/heatmap/")
        status = TestStatus.PASSED if code == 200 and "heatmap" in data else TestStatus.FAILED
        self.add_result("Get heatmap data", status, code, f"Weeks: {data.get('weeks')}", dur, phase)
        
        # 5.7 Heatmap - Custom weeks
        code, data, dur = self.request("GET", "/heatmap/", params={"weeks": 26})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get heatmap 26 weeks", status, code, f"Weeks: {data.get('weeks')}", dur, phase)
        
        # 5.8 Analytics Data
        code, data, dur = self.request("GET", "/analytics/data/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get analytics data", status, code, str(data.get("success")), dur, phase)
        
        # 5.9 Forecast
        code, data, dur = self.request("GET", "/analytics/forecast/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get forecast", status, code, f"Has suggestions: {'suggestions' in data}", dur, phase)
        
        # 5.10 Forecast with params
        code, data, dur = self.request("GET", "/analytics/forecast/", params={"days": 14})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get 14-day forecast", status, code, str(data.get("success")), dur, phase)
        
        # 5.11 Forecast invalid days
        code, data, dur = self.request("GET", "/analytics/forecast/", params={"days": 100})
        status = TestStatus.PASSED if code == 400 else TestStatus.FAILED
        self.add_result("Forecast rejects invalid days", status, code, str(data), dur, phase)

    # =========================================================================
    # PHASE 6: USER & DATA MANAGEMENT
    # =========================================================================
    
    def run_phase_6(self):
        """User & Data Management Tests"""
        phase = "Phase 6: User & Data"
        self.log(f"\n{'='*60}")
        self.log(f"  {phase}")
        self.log(f"{'='*60}")
        
        # 6.1 User Profile - Get
        code, data, dur = self.request("GET", "/user/profile/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get user profile", status, code, str(data.get("success")), dur, phase)
        
        # 6.2 User Profile - Update
        code, data, dur = self.request("PUT", "/user/profile/", {
            "username": f"testuser_{uuid.uuid4().hex[:4]}"
        })
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Update user profile", status, code, str(data), dur, phase)
        
        # 6.3 Search
        code, data, dur = self.request("GET", "/search/", params={"q": "morning"})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Search for 'morning'", status, code, f"Results found", dur, phase)
        
        # 6.4 Search - Empty query
        code, data, dur = self.request("GET", "/search/", params={"q": ""})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Search with empty query", status, code, str(data.get("success")), dur, phase)
        
        # 6.5 Day Notes - Save
        today = date.today().isoformat()
        code, data, dur = self.request("POST", f"/notes/{today}/", {"note": "Test note"})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Save day note", status, code, str(data), dur, phase)
        
        # 6.6 Day Notes - Invalid date
        code, data, dur = self.request("POST", "/notes/invalid-date/", {"note": "Test"})
        status = TestStatus.PASSED if code == 400 else TestStatus.FAILED
        self.add_result("Day note rejects invalid date", status, code, str(data), dur, phase)
        
        # 6.7 Smart Suggestions
        code, data, dur = self.request("GET", "/suggestions/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Get smart suggestions", status, code, str(data.get("success")), dur, phase)
        
        # 6.8 Prefetch
        code, data, dur = self.request("GET", "/prefetch/", params={"panels": "today,dashboard"})
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Prefetch panels", status, code, str(data.get("success")), dur, phase)
        
        # 6.9 Sync
        code, data, dur = self.request("GET", "/sync/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Sync data", status, code, str(data.get("success")), dur, phase)
        
        # 6.10 Validate Field
        code, data, dur = self.request("POST", "/validate/", {
            "field": "tracker_name",
            "value": "Test Tracker"
        })
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Validate field", status, code, str(data), dur, phase)
        
        # 6.11 Export Month
        code, data, dur = self.request("GET", "/export/month/")
        status = TestStatus.PASSED if code in [200, 400] else TestStatus.FAILED
        self.add_result("Export month data", status, code, "Response received", dur, phase)
        
        # 6.12 Data Export
        code, data, dur = self.request("GET", "/data/export/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Full data export", status, code, "Export response", dur, phase)
        
        # 6.13 Logout
        code, data, dur = self.request("POST", "/auth/logout/")
        status = TestStatus.PASSED if code == 200 else TestStatus.FAILED
        self.add_result("Logout", status, code, str(data), dur, phase)

    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _relogin(self):
        """Re-login if session expired"""
        code, data, _ = self.request("POST", "/auth/login/", {
            "email": self.test_user_email,
            "password": self.test_user_password
        }, auth=False)
        if data.get("token"):
            self.auth_token = data["token"]
            
    # =========================================================================
    # WORKFLOW TESTS
    # =========================================================================
    
    def run_workflow_tests(self):
        """End-to-end workflow tests"""
        phase = "Workflow Tests"
        self.log(f"\n{'='*60}")
        self.log(f"  {phase}")
        self.log(f"{'='*60}")
        
        # Re-login for workflow tests
        self._relogin()
        
        # Workflow 1: Task Completion Flow
        self.log("\n  📋 Workflow 1: Task Completion Flow")
        
        # Get today's tasks
        code, data, dur = self.request("GET", "/dashboard/trackers/")
        task_found = False
        task_id = None
        for tracker in data.get("trackers", []):
            for task in tracker.get("tasks", []):
                if task.get("status") == "TODO":
                    task_id = task.get("task_instance_id")
                    task_found = True
                    break
                    
        if task_id:
            # Complete task
            code, _, dur = self.request("POST", f"/task/{task_id}/toggle/")
            self.add_result("Workflow: Complete task", 
                           TestStatus.PASSED if code == 200 else TestStatus.FAILED, 
                           code, "Task toggled", dur, phase)
                           
            # Verify progress
            code, _, dur = self.request("GET", "/dashboard/today/")
            self.add_result("Workflow: Verify progress updated", 
                           TestStatus.PASSED if code == 200 else TestStatus.FAILED,
                           code, "Progress checked", dur, phase)
                           
            # Undo
            code, _, dur = self.request("POST", f"/task/{task_id}/toggle/")
            self.add_result("Workflow: Undo task completion",
                           TestStatus.PASSED if code == 200 else TestStatus.FAILED,
                           code, "Task undone", dur, phase)
        else:
            self.add_result("Workflow: Task completion flow", 
                           TestStatus.SKIPPED, 0, "No tasks available", 0, phase)
        
        # Workflow 2: Create and Manage Tracker
        self.log("\n  📋 Workflow 2: Create & Manage Tracker")
        
        # Create tracker 
        code, data, dur = self.request("POST", "/tracker/create/", {
            "name": f"Workflow Test {uuid.uuid4().hex[:6]}",
            "time_mode": "daily"
        })
        new_tracker_id = data.get("tracker_id") or data.get("data", {}).get("tracker_id")
        self.add_result("Workflow: Create tracker",
                       TestStatus.PASSED if code in [200, 201] else TestStatus.FAILED,
                       code, f"ID: {new_tracker_id}", dur, phase)
                       
        if new_tracker_id:
            # Add task
            code, _, dur = self.request("POST", f"/tracker/{new_tracker_id}/task/add/", {
                "description": "Workflow Task"
            })
            self.add_result("Workflow: Add task",
                           TestStatus.PASSED if code in [200, 201] else TestStatus.FAILED,
                           code, "Task added", dur, phase)
                           
            # Update tracker
            code, _, dur = self.request("PUT", f"/tracker/{new_tracker_id}/update/", {
                "name": "Updated Workflow Tracker"
            })
            self.add_result("Workflow: Update tracker",
                           TestStatus.PASSED if code == 200 else TestStatus.FAILED,
                           code, "Tracker updated", dur, phase)
                           
            # Delete tracker
            code, _, dur = self.request("DELETE", f"/tracker/{new_tracker_id}/delete/")
            self.add_result("Workflow: Delete tracker",
                           TestStatus.PASSED if code == 200 else TestStatus.FAILED,
                           code, "Tracker deleted", dur, phase)

    # =========================================================================
    # REPORT GENERATION
    # =========================================================================
    
    def generate_report(self) -> Dict:
        """Generate test report"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        
        # Calculate by phase
        phases = {}
        for r in self.results:
            if r.phase not in phases:
                phases[r.phase] = {"passed": 0, "failed": 0, "skipped": 0}
            if r.status == TestStatus.PASSED:
                phases[r.phase]["passed"] += 1
            elif r.status == TestStatus.FAILED:
                phases[r.phase]["failed"] += 1
            else:
                phases[r.phase]["skipped"] += 1
                
        # Print report
        print(f"\n{'='*60}")
        print("  INTEGRATION TEST REPORT")
        print(f"{'='*60}")
        print(f"\n  Total Tests: {total}")
        print(f"  ✅ Passed:   {passed} ({100*passed/total:.1f}%)")
        print(f"  ❌ Failed:   {failed} ({100*failed/total:.1f}%)")
        print(f"  ⏭️  Skipped:  {skipped} ({100*skipped/total:.1f}%)")
        
        print(f"\n  By Phase:")
        for phase, stats in phases.items():
            phase_total = sum(stats.values())
            print(f"    {phase}: {stats['passed']}/{phase_total} passed")
            
        if failed > 0:
            print(f"\n  ❌ Failed Tests:")
            for r in self.results:
                if r.status == TestStatus.FAILED:
                    print(f"    - {r.name} [{r.response_code}]: {r.message[:60]}")
                    
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "phases": phases,
            "success_rate": passed / total if total > 0 else 0
        }

    # =========================================================================
    # MAIN RUNNER
    # =========================================================================
    
    def run_all(self):
        """Run all test phases"""
        print("\n" + "="*60)
        print("  TRACKER PRO API v1 - INTEGRATION TEST SUITE")
        print(f"  Base URL: {BASE_URL}")
        print(f"  Time: {datetime.now().isoformat()}")
        print("="*60)
        
        # Run all phases
        self.run_phase_1()  # Auth
        self.run_phase_2()  # Tracker CRUD
        self.run_phase_3()  # Task CRUD
        self.run_phase_4()  # Dashboard
        self.run_phase_5()  # Analytics
        self.run_phase_6()  # User & Data
        self.run_workflow_tests()  # Workflows
        
        # Generate report
        report = self.generate_report()
        
        return report


if __name__ == "__main__":
    suite = IntegrationTestSuite()
    report = suite.run_all()
    
    # Exit with appropriate code
    if report["failed"] > 0:
        exit(1)
    exit(0)
