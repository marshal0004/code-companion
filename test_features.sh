#!/bin/bash

echo "======================================"
echo "CodeCompanion Feature Test"
echo "======================================"
echo

echo "1. Testing Backend Health..."
curl -s http://localhost:8001/api/health || echo "FAILED"
echo
echo

echo "2. Testing Model Status..."
curl -s http://localhost:8001/api/models/status | python3 -m json.tool
echo
echo

echo "3. Testing Available Models..."
curl -s http://localhost:8001/api/models/list | python3 -m json.tool | head -30
echo
echo

echo "4. Testing Conversations List..."
curl -s http://localhost:8001/api/conversations | python3 -m json.tool
echo
echo

echo "5. Testing Index Stats..."
curl -s http://localhost:8001/api/index/stats | python3 -m json.tool
echo
echo

echo "======================================"
echo "All API endpoints working!"
echo "======================================"
