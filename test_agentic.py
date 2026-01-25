#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '/app/backend')

from llm_client import LLMClient

async def test():
    client = LLMClient()
    
    messages = [
        {"role": "user", "content": "List all Python files in the /app directory"}
    ]
    
    print("Testing agentic tool calling...")
    print("=" * 60)
    
    result = await client.chat_stream(messages, "test_session")
    
    print(f"\nResponse: {result['response']}")
    print(f"\nTool Calls: {result['tool_calls']}")
    print(f"\nRaw Response:\n{result['raw_response']}")

if __name__ == "__main__":
    asyncio.run(test())
