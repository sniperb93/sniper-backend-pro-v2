import requests
import sys
import json
from datetime import datetime
import time

class BlaxingAPITester:
    def __init__(self, base_url="https://emergent-control.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if success:
                try:
                    response_data = response.json()
                    details += f", Response: {json.dumps(response_data, indent=2)}"
                    self.log_test(name, True, details)
                    return True, response_data
                except:
                    details += f", Response: {response.text[:200]}"
                    self.log_test(name, True, details)
                    return True, {}
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {json.dumps(error_data, indent=2)}"
                except:
                    details += f", Error: {response.text[:200]}"
                self.log_test(name, False, details)
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_agents_list(self):
        """Test agents list endpoint - should return 4 seeded agents"""
        success, data = self.run_test("Agents List", "GET", "agents/list", 200)
        if success:
            expected_agents = ["sniper", "crystal", "sonia", "corerouter"]
            agent_ids = [agent.get("agent_id") for agent in data]
            
            if len(data) == 4:
                self.log_test("Agents List Count", True, f"Found {len(data)} agents")
            else:
                self.log_test("Agents List Count", False, f"Expected 4 agents, got {len(data)}")
            
            for expected_id in expected_agents:
                if expected_id in agent_ids:
                    self.log_test(f"Agent {expected_id} exists", True)
                else:
                    self.log_test(f"Agent {expected_id} exists", False, f"Missing agent: {expected_id}")
        
        return success, data

    def test_agent_register(self):
        """Test agent registration"""
        test_agent = {
            "agent_id": "test_agent",
            "name": "Test Agent",
            "image": "blaxing/test:latest"
        }
        success, data = self.run_test("Agent Register", "POST", "agents/register", 200, test_agent)
        if success and data:
            if data.get("agent_id") == "test_agent":
                self.log_test("Agent Register Validation", True, "Agent registered correctly")
            else:
                self.log_test("Agent Register Validation", False, "Agent data mismatch")
        return success, data

    def test_agent_activate(self, agent_id="sniper"):
        """Test agent activation"""
        success, data = self.run_test(f"Activate Agent {agent_id}", "POST", f"agents/{agent_id}/activate", 200)
        if success:
            if data.get("state") == "active":
                self.log_test(f"Agent {agent_id} Activation State", True, "State set to active")
            else:
                self.log_test(f"Agent {agent_id} Activation State", False, f"Expected active, got {data.get('state')}")
        return success, data

    def test_agent_status(self, agent_id="sniper"):
        """Test agent status endpoint"""
        success, data = self.run_test(f"Agent {agent_id} Status", "GET", f"agents/{agent_id}/status", 200)
        if success:
            if "uptime" in data and isinstance(data["uptime"], int):
                self.log_test(f"Agent {agent_id} Uptime Check", True, f"Uptime: {data['uptime']} seconds")
            else:
                self.log_test(f"Agent {agent_id} Uptime Check", False, "Uptime not found or invalid")
        return success, data

    def test_agent_deactivate(self, agent_id="sniper"):
        """Test agent deactivation"""
        success, data = self.run_test(f"Deactivate Agent {agent_id}", "POST", f"agents/{agent_id}/deactivate", 200)
        if success:
            if data.get("state") == "sleep":
                self.log_test(f"Agent {agent_id} Deactivation State", True, "State set to sleep")
            else:
                self.log_test(f"Agent {agent_id} Deactivation State", False, f"Expected sleep, got {data.get('state')}")
        return success, data

    def test_agent_status_after_deactivate(self, agent_id="sniper"):
        """Test agent status after deactivation - uptime should be 0"""
        success, data = self.run_test(f"Agent {agent_id} Status After Deactivate", "GET", f"agents/{agent_id}/status", 200)
        if success:
            if data.get("uptime") == 0:
                self.log_test(f"Agent {agent_id} Uptime Reset", True, "Uptime reset to 0")
            else:
                self.log_test(f"Agent {agent_id} Uptime Reset", False, f"Expected uptime 0, got {data.get('uptime')}")
        return success, data

    def test_mock_mode_headers(self):
        """Test mock mode with x-blaxing-source header"""
        headers = {
            'Content-Type': 'application/json',
            'x-blaxing-source': 'mock'
        }
        success, data = self.run_test("Mock Mode - Agents List", "GET", "agents/list", 200, headers=headers)
        if success and len(data) == 4:
            self.log_test("Mock Mode - 4 Seeded Agents", True, "Found expected 4 agents in mock mode")
        elif success:
            self.log_test("Mock Mode - 4 Seeded Agents", False, f"Expected 4 agents, got {len(data)}")
        return success, data

    def test_prod_mode_without_api_key(self):
        """Test prod mode without API key - should fallback to mock for list, fail for mutate"""
        headers = {
            'Content-Type': 'application/json',
            'x-blaxing-source': 'prod'
        }
        
        # List should fallback to mock
        success, data = self.run_test("Prod Mode (No API Key) - List Fallback", "GET", "agents/list", 200, headers=headers)
        if success and len(data) == 4:
            self.log_test("Prod Mode Fallback - List Works", True, "List endpoint falls back to mock successfully")
        
        # Status should fallback to mock
        success, data = self.run_test("Prod Mode (No API Key) - Status Fallback", "GET", "agents/sniper/status", 200, headers=headers)
        if success:
            self.log_test("Prod Mode Fallback - Status Works", True, "Status endpoint falls back to mock successfully")
        
        # Activate should fail with 401
        success, data = self.run_test("Prod Mode (No API Key) - Activate Fails", "POST", "agents/sniper/activate", 401, headers=headers)
        if success:
            self.log_test("Prod Mode - Activate 401", True, "Activate correctly returns 401 without API key")
        
        # Deactivate should fail with 401
        success, data = self.run_test("Prod Mode (No API Key) - Deactivate Fails", "POST", "agents/sniper/deactivate", 401, headers=headers)
        if success:
            self.log_test("Prod Mode - Deactivate 401", True, "Deactivate correctly returns 401 without API key")

    def test_prod_mode_with_invalid_api_key(self):
        """Test prod mode with invalid API key - should fail for all operations"""
        headers = {
            'Content-Type': 'application/json',
            'x-blaxing-source': 'prod',
            'X-API-KEY': 'invalid-key-12345'
        }
        
        # All operations should fail when trying to reach prod with invalid key
        # But list/status will fallback to mock, while mutate operations will fail
        
        # List should fallback to mock
        success, data = self.run_test("Prod Mode (Invalid Key) - List Fallback", "GET", "agents/list", 200, headers=headers)
        
        # Activate should fail
        success, data = self.run_test("Prod Mode (Invalid Key) - Activate Fails", "POST", "agents/sniper/activate", 401, headers=headers)

    def test_default_mock_behavior(self):
        """Test default behavior without headers - should default to mock"""
        # No x-blaxing-source header should default to mock
        success, data = self.run_test("Default Mode - Agents List", "GET", "agents/list", 200)
        if success and len(data) == 4:
            self.log_test("Default Mode - Mock Behavior", True, "Default behavior uses mock mode")
        
        # Activate should work in default mock mode
        success, data = self.run_test("Default Mode - Activate Works", "POST", "agents/sniper/activate", 200)
        if success and data.get("state") == "active":
            self.log_test("Default Mode - Activate Success", True, "Activate works in default mock mode")

    def run_full_test_suite(self):
        """Run complete test suite"""
        print("🚀 Starting Blaxing API Test Suite")
        print(f"   Base URL: {self.base_url}")
        print("=" * 60)

        # Test basic connectivity
        self.test_root_endpoint()
        
        # Test default mock behavior
        print("\n📋 Testing Default Mock Behavior")
        self.test_default_mock_behavior()
        
        # Test explicit mock mode headers
        print("\n📋 Testing Mock Mode Headers")
        self.test_mock_mode_headers()
        
        # Test prod mode without API key
        print("\n📋 Testing Prod Mode Without API Key")
        self.test_prod_mode_without_api_key()
        
        # Test prod mode with invalid API key
        print("\n📋 Testing Prod Mode With Invalid API Key")
        self.test_prod_mode_with_invalid_api_key()
        
        # Test basic CRUD operations in mock mode
        print("\n📋 Testing Basic CRUD Operations")
        self.test_agents_list()
        self.test_agent_register()
        
        # Test activation flow
        print("\n📋 Testing Activation Flow")
        self.test_agent_activate("sniper")
        time.sleep(1)  # Wait for activation to process
        self.test_agent_status("sniper")
        
        # Test deactivation flow
        print("\n📋 Testing Deactivation Flow")
        self.test_agent_deactivate("sniper")
        time.sleep(1)  # Wait for deactivation to process
        self.test_agent_status_after_deactivate("sniper")
        
        # Test with another agent
        print("\n📋 Testing Multiple Agents")
        self.test_agent_activate("crystal")
        time.sleep(1)
        self.test_agent_status("crystal")
        self.test_agent_deactivate("crystal")

        # Print final results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed!")
            return 1

def main():
    tester = BlaxingAPITester()
    return tester.run_full_test_suite()

if __name__ == "__main__":
    sys.exit(main())