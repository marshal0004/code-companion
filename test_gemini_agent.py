#!/usr/bin/env python3
"""
Quick test of CodeCompanion agent with Gemini (FREE)
Tests basic coding task with tool execution
"""
import requests
import json
import time

API_URL = "http://localhost:8001"

def test_coding_task():
    """Test agent's ability to create a simple Python script"""
    
    print("🧪 Testing CodeCompanion Agent with Gemini (FREE)")
    print("=" * 60)
    
    # Check status first
    print("\n📊 Checking model status...")
    response = requests.get(f"{API_URL}/api/models/status")
    status = response.json()
    print(f"   Provider: {status['active_provider']}")
    print(f"   Model: {status['active_model']}")
    print(f"   Gemini: {'✓' if status['gemini_available'] else '✗'}")
    print(f"   Ollama: {'✓' if status['ollama_available'] else '✗'}")
    emergent_status = "✓ (but not used)" if status['emergent_available'] else "✗"
    print(f"   Emergent: {emergent_status}")
    
    if status['active_provider'] != 'gemini':
        print("\n❌ ERROR: Not using Gemini! Current provider:", status['active_provider'])
        return False
    
    # Test simple coding task
    print("\n🎯 Task: Create a simple calculator Python script")
    print("-" * 60)
    
    task = """Create a Python file called 'calculator.py' that has:
1. A Calculator class with methods: add, subtract, multiply, divide
2. Basic error handling for division by zero
3. A main section that demonstrates usage

Keep it simple and clean."""
    
    response = requests.post(
        f"{API_URL}/api/chat/stream",
        json={
            "message": task,
            "project_path": "/tmp/test_agent"
        },
        stream=True,
        timeout=60
    )
    
    print("\n🤖 Agent Response:")
    print("-" * 60)
    
    content = ""
    tools_used = []
    success = False
    
    for line in response.iter_lines():
        if not line:
            continue
        
        line = line.decode('utf-8')
        if not line.startswith('data: '):
            continue
        
        try:
            data = json.loads(line[6:])
            
            if data['type'] == 'content':
                content += data['content']
                print(data['content'], end='', flush=True)
            
            elif data['type'] == 'tool_call':
                tool_name = data['name']
                tools_used.append(tool_name)
                print(f"\n\n🔧 Tool: {tool_name}", flush=True)
            
            elif data['type'] == 'tool_result':
                if data.get('success', False):
                    print(" ✓", flush=True)
                else:
                    print(f" ✗ ({data['result'].get('error', 'failed')})", flush=True)
            
            elif data['type'] == 'done':
                success = True
                print("\n" + "-" * 60)
                break
            
            elif data['type'] == 'error':
                print(f"\n\n❌ Error: {data['message']}")
                break
        
        except json.JSONDecodeError:
            continue
    
    # Summary
    print("\n\n📊 Test Results:")
    print("=" * 60)
    print(f"✓ Task completed: {success}")
    print(f"✓ Provider used: Gemini (FREE)")
    print(f"✓ Tools executed: {len(tools_used)}")
    for tool in set(tools_used):
        print(f"  - {tool}")
    print(f"✓ No Emergent credits used: ✓")
    
    # Check if file was created
    print("\n🔍 Verifying file creation...")
    import os
    if os.path.exists('/tmp/test_agent/calculator.py'):
        print("✓ calculator.py created successfully!")
        # Show first 10 lines
        with open('/tmp/test_agent/calculator.py', 'r') as f:
            lines = f.readlines()[:10]
        print("\n📄 First 10 lines:")
        print("-" * 60)
        for i, line in enumerate(lines, 1):
            print(f"{i:2}| {line.rstrip()}")
    else:
        print("✗ File not found - agent may have used different path")
    
    return success

if __name__ == "__main__":
    try:
        success = test_coding_task()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
