#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for CodeCompanion
Tests all backend endpoints including streaming, agentic loop, and tool execution
"""

import requests
import json
import time
import sys
from typing import Dict, Any
import os

# Get backend URL from frontend env
BACKEND_URL = "https://codehelper-33.preview.emergentagent.com/api"

class CodeCompanionTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
    
    def test_health_endpoint(self):
        """Test GET /api/health"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy" and data.get("service") == "codecompanion":
                    self.log_test("Health Check", True, f"Status: {data}")
                    return True
                else:
                    self.log_test("Health Check", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")
            return False
    
    def test_model_status(self):
        """Test GET /api/models/status"""
        try:
            response = self.session.get(f"{self.base_url}/models/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["active_provider", "active_model"]
                
                if all(field in data for field in required_fields):
                    self.log_test("Model Status", True, f"Provider: {data.get('active_provider')}, Model: {data.get('active_model')}")
                    return True, data
                else:
                    self.log_test("Model Status", False, f"Missing required fields: {data}")
                    return False, None
            else:
                self.log_test("Model Status", False, f"HTTP {response.status_code}: {response.text}")
                return False, None
                
        except Exception as e:
            self.log_test("Model Status", False, f"Exception: {str(e)}")
            return False, None
    
    def test_model_list(self):
        """Test GET /api/models/list"""
        try:
            response = self.session.get(f"{self.base_url}/models/list", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["models", "current_provider", "current_model", "status"]
                
                if all(field in data for field in required_fields):
                    models_count = len(data.get("models", {}))
                    self.log_test("Model List", True, f"Found {models_count} models, Current: {data.get('current_provider')}/{data.get('current_model')}")
                    return True, data
                else:
                    self.log_test("Model List", False, f"Missing required fields: {data}")
                    return False, None
            else:
                self.log_test("Model List", False, f"HTTP {response.status_code}: {response.text}")
                return False, None
                
        except Exception as e:
            self.log_test("Model List", False, f"Exception: {str(e)}")
            return False, None
    
    def test_conversations_list(self):
        """Test GET /api/conversations"""
        try:
            response = self.session.get(f"{self.base_url}/conversations", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "conversations" in data:
                    conv_count = len(data["conversations"])
                    self.log_test("Conversations List", True, f"Found {conv_count} conversations")
                    return True, data
                else:
                    self.log_test("Conversations List", False, f"Missing 'conversations' field: {data}")
                    return False, None
            else:
                self.log_test("Conversations List", False, f"HTTP {response.status_code}: {response.text}")
                return False, None
                
        except Exception as e:
            self.log_test("Conversations List", False, f"Exception: {str(e)}")
            return False, None
    
    def test_indexing_stats(self):
        """Test GET /api/index/stats"""
        try:
            response = self.session.get(f"{self.base_url}/index/stats", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Index Stats", True, f"Stats: {data}")
                return True, data
            else:
                self.log_test("Index Stats", False, f"HTTP {response.status_code}: {response.text}")
                return False, None
                
        except Exception as e:
            self.log_test("Index Stats", False, f"Exception: {str(e)}")
            return False, None
    
    def test_workspace_indexing(self):
        """Test POST /api/index/workspace"""
        try:
            response = self.session.post(f"{self.base_url}/index/workspace", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Workspace Indexing", True, f"Result: {data}")
                return True, data
            else:
                self.log_test("Workspace Indexing", False, f"HTTP {response.status_code}: {response.text}")
                return False, None
                
        except Exception as e:
            self.log_test("Workspace Indexing", False, f"Exception: {str(e)}")
            return False, None
    
    def test_chat_streaming(self):
        """Test POST /api/chat/stream with agentic tool execution"""
        try:
            # Test with a simple query that should trigger tool execution
            payload = {
                "message": "List all Python files in the backend directory",
                "project_path": "/app"
            }
            
            print(f"\n🔄 Testing Chat Stream with query: '{payload['message']}'")
            
            response = self.session.post(
                f"{self.base_url}/chat/stream",
                json=payload,
                stream=True,
                timeout=60
            )
            
            if response.status_code != 200:
                self.log_test("Chat Streaming", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            # Parse streaming response
            events = []
            tool_calls = []
            tool_results = []
            content_chunks = []
            conversation_id = None
            
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    try:
                        event_data = json.loads(line[6:])  # Remove "data: " prefix
                        events.append(event_data)
                        
                        event_type = event_data.get("type")
                        
                        if event_type == "content":
                            content_chunks.append(event_data.get("content", ""))
                        elif event_type == "tool_call":
                            tool_calls.append(event_data)
                            print(f"   🔧 Tool Call: {event_data.get('name')} with args: {event_data.get('args')}")
                        elif event_type == "tool_result":
                            tool_results.append(event_data)
                            print(f"   📋 Tool Result: {event_data.get('name')} -> {str(event_data.get('result', ''))[:100]}...")
                        elif event_type == "done":
                            conversation_id = event_data.get("conversation_id")
                            print(f"   ✅ Stream Complete. Conversation ID: {conversation_id}")
                            break
                        elif event_type == "error":
                            self.log_test("Chat Streaming", False, f"Stream error: {event_data.get('message')}")
                            return False
                            
                    except json.JSONDecodeError as e:
                        print(f"   ⚠️  JSON decode error: {e} for line: {line}")
                        continue
            
            # Validate streaming results
            full_content = "".join(content_chunks)
            
            success_criteria = [
                len(events) > 0,  # Got some events
                len(tool_calls) > 0,  # Tool was called
                len(tool_results) > 0,  # Tool returned results
                conversation_id is not None,  # Got conversation ID
            ]
            
            if all(success_criteria):
                details = f"Events: {len(events)}, Tools: {len(tool_calls)}, Results: {len(tool_results)}, Content length: {len(full_content)}"
                self.log_test("Chat Streaming", True, details)
                
                # Test if the tool actually found Python files
                if tool_results:
                    first_result = tool_results[0].get("result", {})
                    if isinstance(first_result, dict) and "files" in first_result:
                        python_files = [f for f in first_result["files"] if f.endswith(".py")]
                        if python_files:
                            self.log_test("Tool Execution (List Directory)", True, f"Found {len(python_files)} Python files")
                        else:
                            self.log_test("Tool Execution (List Directory)", False, "No Python files found in backend directory")
                    else:
                        self.log_test("Tool Execution (List Directory)", False, f"Unexpected tool result format: {first_result}")
                
                return True, conversation_id
            else:
                failed_criteria = []
                if len(events) == 0: failed_criteria.append("No events")
                if len(tool_calls) == 0: failed_criteria.append("No tool calls")
                if len(tool_results) == 0: failed_criteria.append("No tool results")
                if conversation_id is None: failed_criteria.append("No conversation ID")
                
                self.log_test("Chat Streaming", False, f"Failed criteria: {', '.join(failed_criteria)}")
                return False, None
                
        except Exception as e:
            self.log_test("Chat Streaming", False, f"Exception: {str(e)}")
            return False, None
    
    def test_conversation_retrieval(self, conversation_id: str):
        """Test GET /api/conversations/{conversation_id}"""
        try:
            response = self.session.get(f"{self.base_url}/conversations/{conversation_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "messages" in data:
                    message_count = len(data["messages"])
                    self.log_test("Conversation Retrieval", True, f"Retrieved {message_count} messages")
                    return True, data
                else:
                    self.log_test("Conversation Retrieval", False, f"Missing 'messages' field: {data}")
                    return False, None
            else:
                self.log_test("Conversation Retrieval", False, f"HTTP {response.status_code}: {response.text}")
                return False, None
                
        except Exception as e:
            self.log_test("Conversation Retrieval", False, f"Exception: {str(e)}")
            return False, None
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting CodeCompanion Backend API Tests")
        print(f"🌐 Backend URL: {self.base_url}")
        print("=" * 60)
        
        # 1. Health & Status Tests
        print("\n📊 HEALTH & STATUS TESTS")
        print("-" * 30)
        health_ok = self.test_health_endpoint()
        status_ok, status_data = self.test_model_status()
        list_ok, list_data = self.test_model_list()
        
        # 2. Conversation Tests
        print("\n💬 CONVERSATION TESTS")
        print("-" * 30)
        conv_list_ok, conv_data = self.test_conversations_list()
        
        # 3. Chat & Agentic Loop Tests
        print("\n🤖 CHAT & AGENTIC LOOP TESTS")
        print("-" * 30)
        chat_ok, conversation_id = self.test_chat_streaming()
        
        # 4. Test conversation retrieval if we got a conversation ID
        if chat_ok and conversation_id:
            conv_retrieve_ok, conv_messages = self.test_conversation_retrieval(conversation_id)
        
        # 5. Indexing Tests
        print("\n🔍 INDEXING TESTS")
        print("-" * 30)
        index_stats_ok, stats_data = self.test_indexing_stats()
        index_workspace_ok, workspace_data = self.test_workspace_indexing()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}")
            if not result["success"] and result["details"]:
                print(f"   Error: {result['details']}")
        
        print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        # Critical issues
        critical_failures = []
        for result in self.test_results:
            if not result["success"]:
                if "Health Check" in result["test"]:
                    critical_failures.append("Backend health check failed")
                elif "Chat Streaming" in result["test"]:
                    critical_failures.append("Agentic chat loop not working")
                elif "Tool Execution" in result["test"]:
                    critical_failures.append("Tool execution failed")
        
        if critical_failures:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in critical_failures:
                print(f"   - {issue}")
        
        return passed == total

if __name__ == "__main__":
    tester = CodeCompanionTester()
    success = tester.run_all_tests()
    
    if success:
        print(f"\n🎉 All tests passed! CodeCompanion backend is working correctly.")
        sys.exit(0)
    else:
        print(f"\n💥 Some tests failed. Check the details above.")
        sys.exit(1)