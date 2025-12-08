#!/usr/bin/env python3
"""
API v1 Test Runner for Tracker Pro

This script tests all API endpoints and generates a report of gaps/issues found.
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Any

BASE_URL = "http://127.0.0.1:8000/api/v1"

class APITestRunner:
    def __init__(self):
        self.session = requests.Session()
        self.results: List[Dict] = []
        self.gaps: List[Dict] = []
        self.errors: List[Dict] = []
        self.auth_token = None
        self.session_cookie = None
        
    def log_result(self, endpoint: str, method: str, status_code: int, 
                   success: bool, response_data: Any, notes: str = ""):
        result = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "success": success,
            "notes": notes,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {method} {endpoint} -> {status_code} {notes}")
        
        if not success:
            self.errors.append({
                **result,
                "response": str(response_data)[:500]
            })
            
    def log_gap(self, category: str, description: str, severity: str, endpoint: str = ""):
        gap = {
            "category": category,
            "description": description,
            "severity": severity,  # "critical", "major", "minor"
            "endpoint": endpoint
        }
        self.gaps.append(gap)
        print(f"⚠️  GAP [{severity.upper()}]: {description}")
        
    def test_health(self):
        """Test health endpoint (no auth required)"""
        print("\n" + "="*60)
        print("1. HEALTH CHECK")
        print("="*60)
        
        r = self.session.get(f"{BASE_URL}/health/")
        data = r.json()
        self.log_result("/health/", "GET", r.status_code, 
                       r.status_code == 200 and data.get("status") == "healthy",
                       data, "Health check")
        return r.status_code == 200
        
    def test_auth_status_unauthenticated(self):
        """Test auth status when not logged in"""
        print("\n" + "="*60)
        print("2. AUTH STATUS (Unauthenticated)")
        print("="*60)
        
        r = self.session.get(f"{BASE_URL}/auth/status/")
        data = r.json()
        expected = data.get("authenticated") == False
        self.log_result("/auth/status/", "GET", r.status_code, 
                       r.status_code == 200 and expected,
                       data, "Should show not authenticated")
        
    def test_protected_endpoint_unauthorized(self):
        """Test that protected endpoints return 401"""
        print("\n" + "="*60)
        print("3. PROTECTED ENDPOINTS (Unauthorized)")
        print("="*60)
        
        endpoints = [
            "/dashboard/",
            "/trackers/",
            "/goals/",
            "/preferences/",
            "/notifications/",
            "/insights/",
            "/user/profile/",
        ]
        
        for endpoint in endpoints:
            r = self.session.get(f"{BASE_URL}{endpoint}")
            # Should return 401
            is_401 = r.status_code == 401
            self.log_result(endpoint, "GET", r.status_code, 
                           is_401, r.text[:200],
                           "Should return 401")
            
            if not is_401:
                self.log_gap("Auth", f"{endpoint} does not return 401 for unauthenticated requests", 
                            "critical", endpoint)
                            
    def test_login(self, email: str, password: str) -> bool:
        """Test login endpoint"""
        print("\n" + "="*60)
        print("4. LOGIN")
        print("="*60)
        
        # Test with valid credentials
        r = self.session.post(f"{BASE_URL}/auth/login/", 
                             json={"email": email, "password": password})
        data = r.json()
        success = r.status_code == 200 and data.get("success") == True
        
        self.log_result("/auth/login/", "POST", r.status_code, 
                       success, data, f"Login with {email}")
        
        if success:
            # Check if we got session cookie
            if 'sessionid' in self.session.cookies:
                print("   ✓ Session cookie received")
            else:
                print("   ⚠ No session cookie received")
                
        return success
        
    def test_login_validation(self):
        """Test login validation errors"""
        print("\n" + "="*60)
        print("5. LOGIN VALIDATION")
        print("="*60)
        
        # Test empty payload
        r = self.session.post(f"{BASE_URL}/auth/login/", json={})
        self.log_result("/auth/login/", "POST", r.status_code, 
                       r.status_code == 400, r.text[:200],
                       "Empty payload should fail")
        
        # Test invalid email format
        r = self.session.post(f"{BASE_URL}/auth/login/", 
                             json={"email": "invalid", "password": "test1234"})
        self.log_result("/auth/login/", "POST", r.status_code, 
                       r.status_code == 400, r.text[:200],
                       "Invalid email should fail")
        
        # Test short password
        r = self.session.post(f"{BASE_URL}/auth/login/", 
                             json={"email": "test@test.com", "password": "short"})
        self.log_result("/auth/login/", "POST", r.status_code, 
                       r.status_code == 400, r.text[:200],
                       "Short password should fail")
                       
    def test_dashboard_endpoints(self):
        """Test all dashboard endpoints (requires auth)"""
        print("\n" + "="*60)
        print("6. DASHBOARD ENDPOINTS")
        print("="*60)
        
        endpoints = [
            ("/dashboard/", "Full dashboard"),
            ("/dashboard/trackers/", "Trackers with tasks"),
            ("/dashboard/today/", "Today's stats"),
            ("/dashboard/week/", "Week overview"),
            ("/dashboard/goals/", "Goals summary"),
            ("/dashboard/streaks/", "Streak info"),
            ("/dashboard/activity/", "Activity feed"),
        ]
        
        for endpoint, desc in endpoints:
            r = self.session.get(f"{BASE_URL}{endpoint}")
            try:
                data = r.json()
                success = data.get("success", False)
            except:
                data = r.text
                success = False
                
            self.log_result(endpoint, "GET", r.status_code, 
                           success, data if isinstance(data, dict) else data[:200],
                           desc)
                           
            if r.status_code == 500:
                self.log_gap("Backend Error", f"{endpoint} returns 500 error", "critical", endpoint)
            elif r.status_code == 401:
                self.log_gap("Auth", f"{endpoint} returns 401 even with session", "critical", endpoint)
                
    def test_tracker_endpoints(self):
        """Test tracker CRUD endpoints"""
        print("\n" + "="*60)
        print("7. TRACKER ENDPOINTS")
        print("="*60)
        
        # GET trackers list
        r = self.session.get(f"{BASE_URL}/trackers/")
        try:
            data = r.json()
            success = data.get("success", False)
            trackers = data.get("trackers", [])
        except:
            success = False
            trackers = []
            
        self.log_result("/trackers/", "GET", r.status_code, success, 
                       f"Found {len(trackers)} trackers", "List trackers")
                       
        if trackers:
            tracker_id = trackers[0]["tracker_id"]
            
            # GET single tracker
            r = self.session.get(f"{BASE_URL}/tracker/{tracker_id}/")
            try:
                data = r.json()
                success = data.get("success", False)
            except:
                success = False
                
            self.log_result(f"/tracker/{tracker_id[:8]}../", "GET", r.status_code, 
                           success, data if isinstance(data, dict) else "Parse error",
                           "Get tracker detail")
                           
            # GET tracker progress
            r = self.session.get(f"{BASE_URL}/tracker/{tracker_id}/progress/")
            try:
                data = r.json()
                success = data.get("success", False)
            except:
                success = False
                
            self.log_result(f"/tracker/{tracker_id[:8]}../progress/", "GET", r.status_code, 
                           success, "Progress endpoint", "Tracker progress")
                           
            # GET tracker goal
            r = self.session.get(f"{BASE_URL}/tracker/{tracker_id}/goal/")
            try:
                data = r.json()
                success = data.get("success", False)
            except:
                success = False
                
            self.log_result(f"/tracker/{tracker_id[:8]}../goal/", "GET", r.status_code, 
                           success, "Goal endpoint", "Tracker goal")
                           
            # GET points breakdown
            r = self.session.get(f"{BASE_URL}/tracker/{tracker_id}/points-breakdown/")
            try:
                data = r.json()
                success = data.get("success", False)
            except:
                success = False
                
            self.log_result(f"/tracker/{tracker_id[:8]}../points-breakdown/", "GET", r.status_code, 
                           success, "Points breakdown", "Task points breakdown")
        else:
            self.log_gap("Data", "No trackers found for testing", "major")
            
    def test_goals_endpoints(self):
        """Test goals API"""
        print("\n" + "="*60)
        print("8. GOALS ENDPOINTS")
        print("="*60)
        
        # GET goals
        r = self.session.get(f"{BASE_URL}/goals/")
        try:
            data = r.json()
            success = data.get("success", False)
        except:
            success = False
            data = r.text
            
        self.log_result("/goals/", "GET", r.status_code, success, 
                       data if isinstance(data, dict) else data[:200],
                       "List goals")
        
        if r.status_code == 500:
            self.log_gap("Backend Error", "/goals/ returns 500", "critical", "/goals/")
                       
    def test_analytics_endpoints(self):
        """Test analytics endpoints"""
        print("\n" + "="*60)
        print("9. ANALYTICS ENDPOINTS")
        print("="*60)
        
        endpoints = [
            ("/insights/", "Behavioral insights"),
            ("/chart-data/?type=bar", "Chart data"),
            ("/heatmap/", "Heatmap data"),
            ("/analytics/data/", "Analytics data"),
            ("/analytics/forecast/", "Completion forecast"),
        ]
        
        for endpoint, desc in endpoints:
            r = self.session.get(f"{BASE_URL}{endpoint}")
            try:
                data = r.json()
                success = data.get("success", False)
            except:
                success = False
                data = r.text
                
            self.log_result(endpoint, "GET", r.status_code, success, 
                           data if isinstance(data, dict) else data[:200],
                           desc)
                           
            if r.status_code == 500:
                self.log_gap("Backend Error", f"{endpoint} returns 500", "critical", endpoint)
                
    def test_user_endpoints(self):
        """Test user profile and settings"""
        print("\n" + "="*60)
        print("10. USER ENDPOINTS")
        print("="*60)
        
        # GET profile
        r = self.session.get(f"{BASE_URL}/user/profile/")
        try:
            data = r.json()
            success = data.get("success", False)
        except:
            success = False
            data = r.text
            
        self.log_result("/user/profile/", "GET", r.status_code, success, 
                       "Profile endpoint", "Get user profile")
                       
        # GET preferences
        r = self.session.get(f"{BASE_URL}/preferences/")
        try:
            data = r.json()
            success = data.get("success", False)
        except:
            success = False
            data = r.text
            
        self.log_result("/preferences/", "GET", r.status_code, success, 
                       "Preferences endpoint", "Get user preferences")
                       
        # GET notifications
        r = self.session.get(f"{BASE_URL}/notifications/")
        try:
            data = r.json()
            success = data.get("success", False)
        except:
            success = False
            data = r.text
            
        self.log_result("/notifications/", "GET", r.status_code, success, 
                       "Notifications endpoint", "Get notifications")
                       
    def test_utility_endpoints(self):
        """Test utility endpoints"""
        print("\n" + "="*60)
        print("11. UTILITY ENDPOINTS")
        print("="*60)
        
        # Search
        r = self.session.get(f"{BASE_URL}/search/?q=test")
        try:
            data = r.json()
            success = data.get("success", False) or "results" in data
        except:
            success = False
            data = r.text
            
        self.log_result("/search/?q=test", "GET", r.status_code, success, 
                       "Search endpoint", "Global search")
                       
        # Suggestions
        r = self.session.get(f"{BASE_URL}/suggestions/")
        try:
            data = r.json()
            success = data.get("success", False)
        except:
            success = False
            data = r.text
            
        self.log_result("/suggestions/", "GET", r.status_code, success, 
                       "Suggestions endpoint", "Smart suggestions")
                       
        # Feature flag  
        r = self.session.get(f"{BASE_URL}/feature-flags/test_flag/")
        try:
            data = r.json()
            # Feature flags should return 200 even if flag doesn't exist
            success = r.status_code == 200
        except:
            success = False
            data = r.text
            
        self.log_result("/feature-flags/test_flag/", "GET", r.status_code, success, 
                       "Feature flags endpoint", "Check feature flag")
                       
        # Infinite scroll
        r = self.session.get(f"{BASE_URL}/tasks/infinite/")
        try:
            data = r.json()
            success = data.get("success", False)
        except:
            success = False
            data = r.text
            
        self.log_result("/tasks/infinite/", "GET", r.status_code, success, 
                       "Infinite scroll endpoint", "Paginated tasks")
                       
    def test_csrf_issues(self):
        """Test endpoints that might have CSRF issues"""
        print("\n" + "="*60)
        print("12. CSRF VERIFICATION")
        print("="*60)
        
        # Test validate-email (should work without CSRF for mobile)
        r = self.session.post(f"{BASE_URL}/auth/validate-email/",
                             json={"email": "test@test.com"})
        
        is_csrf_error = r.status_code == 403 and "CSRF" in r.text
        if is_csrf_error:
            self.log_gap("CSRF", "/auth/validate-email/ requires CSRF but shouldn't for API", 
                        "major", "/auth/validate-email/")
            self.log_result("/auth/validate-email/", "POST", r.status_code, False, 
                           "CSRF error", "Should be CSRF exempt")
        else:
            self.log_result("/auth/validate-email/", "POST", r.status_code, True, 
                           r.text[:100], "CSRF exempt check")
                           
    def test_logout(self):
        """Test logout"""
        print("\n" + "="*60)
        print("13. LOGOUT")
        print("="*60)
        
        r = self.session.post(f"{BASE_URL}/auth/logout/")
        try:
            data = r.json()
            success = data.get("success", False)
        except:
            success = False
            data = r.text
            
        self.log_result("/auth/logout/", "POST", r.status_code, success, 
                       data if isinstance(data, dict) else data[:200],
                       "Logout")
                       
    def generate_report(self):
        """Generate final test report"""
        print("\n" + "="*60)
        print("TEST REPORT SUMMARY")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Gaps Found: {len(self.gaps)}")
        
        if self.gaps:
            print("\n" + "-"*60)
            print("GAPS & ISSUES FOUND:")
            print("-"*60)
            for gap in self.gaps:
                severity_icon = {"critical": "🔴", "major": "🟠", "minor": "🟡"}.get(gap["severity"], "⚪")
                print(f"\n{severity_icon} [{gap['severity'].upper()}] {gap['category']}")
                print(f"   Description: {gap['description']}")
                if gap["endpoint"]:
                    print(f"   Endpoint: {gap['endpoint']}")
                    
        if self.errors:
            print("\n" + "-"*60)
            print("FAILED TESTS:")
            print("-"*60)
            for err in self.errors[:10]:  # Show first 10
                print(f"\n❌ {err['method']} {err['endpoint']}")
                print(f"   Status: {err['status_code']}")
                print(f"   Notes: {err['notes']}")
                
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "gaps": self.gaps,
            "errors": self.errors
        }
        
    def run_all_tests(self, email: str, password: str):
        """Run all tests in sequence"""
        print("\n" + "="*60)
        print("TRACKER PRO API v1 - TEST SUITE")
        print(f"Base URL: {BASE_URL}")
        print(f"Time: {datetime.now().isoformat()}")
        print("="*60)
        
        # Public endpoints
        self.test_health()
        self.test_auth_status_unauthenticated()
        self.test_protected_endpoint_unauthorized()
        self.test_login_validation()
        self.test_csrf_issues()
        
        # Login
        if self.test_login(email, password):
            # Authenticated endpoints
            self.test_dashboard_endpoints()
            self.test_tracker_endpoints()
            self.test_goals_endpoints()
            self.test_analytics_endpoints()
            self.test_user_endpoints()
            self.test_utility_endpoints()
            self.test_logout()
        else:
            print("\n⚠️  Login failed - skipping authenticated tests")
            self.log_gap("Auth", "Could not login - check test user credentials", "critical")
            
        # Generate report
        return self.generate_report()


if __name__ == "__main__":
    import sys
    
    # Default test credentials - modify as needed
    email = sys.argv[1] if len(sys.argv) > 1 else "dhoteh020@gmail.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "test1234"
    
    runner = APITestRunner()
    report = runner.run_all_tests(email, password)
    
    # Exit with error code if there are failures
    if report["failed"] > 0 or len(report["gaps"]) > 0:
        sys.exit(1)
    sys.exit(0)
