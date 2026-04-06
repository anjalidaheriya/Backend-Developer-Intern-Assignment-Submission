#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Finance Data Processing System
Tests authentication, role-based access control, CRUD operations, and dashboard analytics
"""

import requests
import sys
import json
from datetime import datetime, date
from typing import Dict, Any, Optional

class FinanceAPITester:
    def __init__(self, base_url: str = "https://role-based-finance-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.admin_token = None
        self.viewer_token = None
        self.analyst_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test credentials from /app/memory/test_credentials.md
        self.admin_creds = {"email": "admin@example.com", "password": "admin123"}
        
    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED - {details}")
            
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "response_data": response_data
        })
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, 
                    expected_status: int = 200, token: str = None) -> tuple[bool, Dict]:
        """Make HTTP request and validate response"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
            
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=headers)
            else:
                return False, {"error": f"Unsupported method: {method}"}
            
            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}
                
            return success, response_data
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def test_health_check(self):
        """Test health endpoint"""
        success, data = self.make_request('GET', 'health')
        self.log_test("Health Check", success, 
                     "" if success else f"Health check failed: {data}")
        return success
    
    def test_api_info(self):
        """Test API info endpoint"""
        success, data = self.make_request('GET', 'info')
        self.log_test("API Info", success,
                     "" if success else f"API info failed: {data}")
        return success
    
    def test_admin_login(self):
        """Test admin login and store token"""
        success, data = self.make_request('POST', 'auth/login', self.admin_creds)
        
        if success and 'user' in data:
            # Check if cookies are set (session should handle this)
            self.admin_token = None  # Will use session cookies
            user = data['user']
            if user['role'] == 'admin' and user['email'] == self.admin_creds['email']:
                self.log_test("Admin Login", True)
                return True
        
        self.log_test("Admin Login", False, f"Login failed: {data}")
        return False
    
    def test_get_current_user(self):
        """Test getting current user info"""
        success, data = self.make_request('GET', 'auth/me')
        
        if success and 'email' in data:
            self.log_test("Get Current User", True)
            return True
        
        self.log_test("Get Current User", False, f"Failed to get user: {data}")
        return False
    
    def test_register_viewer(self):
        """Test registering a new viewer user"""
        viewer_data = {
            "email": f"viewer_{datetime.now().strftime('%H%M%S')}@test.com",
            "password": "TestPass123!",
            "name": "Test Viewer"
        }
        
        success, data = self.make_request('POST', 'auth/register', viewer_data, 200)
        
        if success and 'user' in data and data['user']['role'] == 'viewer':
            self.log_test("Register Viewer", True)
            return True, viewer_data
        
        self.log_test("Register Viewer", False, f"Registration failed: {data}")
        return False, None
    
    def test_create_analyst_user(self):
        """Test admin creating an analyst user"""
        analyst_data = {
            "email": f"analyst_{datetime.now().strftime('%H%M%S')}@test.com",
            "password": "TestPass123!",
            "name": "Test Analyst",
            "role": "analyst"
        }
        
        success, data = self.make_request('POST', 'users', analyst_data, 200)
        
        if success and 'role' in data and data['role'] == 'analyst':
            self.log_test("Create Analyst User", True)
            return True, analyst_data
        
        self.log_test("Create Analyst User", False, f"User creation failed: {data}")
        return False, None
    
    def test_list_users(self):
        """Test listing users (admin only)"""
        success, data = self.make_request('GET', 'users')
        
        if success and 'users' in data:
            users = data['users']
            admin_found = any(user['role'] == 'admin' for user in users)
            if admin_found:
                self.log_test("List Users", True)
                return True
        
        self.log_test("List Users", False, f"Failed to list users: {data}")
        return False
    
    def test_create_financial_record(self):
        """Test creating a financial record (analyst/admin only)"""
        record_data = {
            "type": "income",
            "category": "salary",
            "amount": 5000.00,
            "description": "Monthly salary",
            "date": date.today().isoformat()
        }
        
        success, data = self.make_request('POST', 'records', record_data, 200)
        
        if success and 'id' in data:
            self.log_test("Create Financial Record", True)
            return True, data['id']
        
        self.log_test("Create Financial Record", False, f"Record creation failed: {data}")
        return False, None
    
    def test_list_financial_records(self):
        """Test listing financial records"""
        success, data = self.make_request('GET', 'records')
        
        if success and 'records' in data:
            self.log_test("List Financial Records", True)
            return True
        
        self.log_test("List Financial Records", False, f"Failed to list records: {data}")
        return False
    
    def test_dashboard_summary(self):
        """Test dashboard summary endpoint"""
        success, data = self.make_request('GET', 'dashboard/summary')
        
        if success and 'total_income' in data:
            self.log_test("Dashboard Summary", True)
            return True
        
        self.log_test("Dashboard Summary", False, f"Dashboard summary failed: {data}")
        return False
    
    def test_dashboard_stats(self):
        """Test dashboard quick stats"""
        success, data = self.make_request('GET', 'dashboard/stats')
        
        if success and 'total_income' in data:
            self.log_test("Dashboard Stats", True)
            return True
        
        self.log_test("Dashboard Stats", False, f"Dashboard stats failed: {data}")
        return False
    
    def test_role_based_access_control(self):
        """Test role-based access control by trying viewer access to restricted endpoints"""
        # First, register a viewer
        viewer_success, viewer_data = self.test_register_viewer()
        if not viewer_success:
            self.log_test("RBAC Test Setup", False, "Could not create viewer for RBAC test")
            return False
        
        # Login as viewer
        viewer_login_success, login_data = self.make_request('POST', 'auth/login', {
            "email": viewer_data['email'],
            "password": viewer_data['password']
        })
        
        if not viewer_login_success:
            self.log_test("RBAC Viewer Login", False, "Could not login as viewer")
            return False
        
        # Try to create a record (should fail - 403)
        record_data = {
            "type": "expense",
            "category": "food",
            "amount": 50.00,
            "description": "Lunch",
            "date": date.today().isoformat()
        }
        
        success, data = self.make_request('POST', 'records', record_data, 403)
        
        if success:  # Success means we got the expected 403
            self.log_test("RBAC - Viewer Cannot Create Records", True)
            return True
        
        self.log_test("RBAC - Viewer Cannot Create Records", False, 
                     f"Expected 403, but got different response: {data}")
        return False
    
    def test_logout(self):
        """Test logout functionality"""
        success, data = self.make_request('POST', 'auth/logout')
        
        if success:
            self.log_test("Logout", True)
            return True
        
        self.log_test("Logout", False, f"Logout failed: {data}")
        return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Finance API Backend Tests")
        print(f"📍 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Basic connectivity tests
        if not self.test_health_check():
            print("❌ Health check failed - stopping tests")
            return False
        
        self.test_api_info()
        
        # Authentication tests
        if not self.test_admin_login():
            print("❌ Admin login failed - stopping tests")
            return False
        
        self.test_get_current_user()
        
        # User management tests
        self.test_list_users()
        self.test_create_analyst_user()
        
        # Financial records tests
        record_created, record_id = self.test_create_financial_record()
        self.test_list_financial_records()
        
        # Dashboard tests
        self.test_dashboard_summary()
        self.test_dashboard_stats()
        
        # Role-based access control tests
        self.test_role_based_access_control()
        
        # Cleanup
        self.test_logout()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed. Check details above.")
            failed_tests = [r for r in self.test_results if not r['success']]
            print("\nFailed tests:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
            return False

def main():
    """Main test runner"""
    tester = FinanceAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            'summary': {
                'total_tests': tester.tests_run,
                'passed_tests': tester.tests_passed,
                'success_rate': f"{(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "0%",
                'timestamp': datetime.now().isoformat()
            },
            'detailed_results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())