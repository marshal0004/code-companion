from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import logging
import json
import asyncio
from pathlib import Path

from database import Database
from llm_client import LLMClient
from tools import ToolExecutor
from config import Config
from context_manager import ContextManager
from verification import CodeVerifier

# Initialize config
Config.init_directories()

# Create FastAPI app
app = FastAPI(title="CodeCompanion API")
api_router = APIRouter(prefix="/api")

# Initialize components
db = Database()
llm_client = LLMClient()
tool_executor = ToolExecutor()
context_manager = ContextManager()
code_verifier = CodeVerifier()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    project_path: str = "/app"

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    message_count: int

@api_router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint with agentic tool execution (Claude Code style)"""
    try:
        # Get or create conversation
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = db.create_conversation(request.project_path)
        
        # Add user message
        user_msg_id = db.add_message(conversation_id, "user", request.message)
        
        # Get conversation history
        history = db.get_conversation_messages(conversation_id)
        
        # Build messages for LLM
        messages = []
        for msg in history:
            messages.append({"role": msg['role'], "content": msg['content']})
        
        # Stream response with agentic loop
        async def generate():
            try:
                max_iterations = 10  # Prevent infinite loops
                iteration = 0
                
                while iteration < max_iterations:
                    iteration += 1
                    
                    # Get LLM response
                    result = await llm_client.chat_stream(messages, conversation_id)
                    response_text = result['response']
                    tool_calls = result['tool_calls']
                    
                    # Stream response text
                    if response_text:
                        words = response_text.split()
                        for i, word in enumerate(words):
                            chunk = word + (" " if i < len(words) - 1 else "")
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                            await asyncio.sleep(0.02)
                    
                    # If no tool calls, we're done
                    if not tool_calls:
                        # Save assistant message
                        db.add_message(conversation_id, "assistant", response_text)
                        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
                        break
                    
                    # Execute tool calls (agentic behavior)
                    tool_results = []
                    for tool_call in tool_calls:
                        tool_name = tool_call['tool']
                        tool_args = tool_call['args']
                        
                        # Notify about tool execution
                        yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_name, 'args': tool_args})}\n\n"
                        
                        # Execute tool
                        result = tool_executor.execute_tool(tool_name, tool_args)
                        tool_results.append(result)
                        
                        # Stream tool result
                        yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_name, 'result': result})}\n\n"
                        
                        # Log tool execution
                        db.add_tool_call(user_msg_id, tool_name, tool_args, json.dumps(result), "completed")
                    
                    # Add tool results to conversation
                    messages.append({"role": "assistant", "content": result['raw_response']})
                    for tool_result in tool_results:
                        messages.append({"role": "tool", "content": json.dumps(tool_result)})
                    
                    # Continue the agentic loop (LLM will see tool results and decide next action)
                    await asyncio.sleep(0.1)
                
                # Save final assistant message if any
                if response_text:
                    db.add_message(conversation_id, "assistant", response_text)
                
                yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
                
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/conversations")
async def list_conversations():
    """List all conversations"""
    try:
        conversations = db.list_conversations()
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"List conversations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation messages"""
    try:
        messages = db.get_conversation_messages(conversation_id)
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "codecompanion"}

@api_router.get("/models/list")
async def list_models():
    """List available models from all providers"""
    try:
        models = llm_client.list_available_models()
        status = llm_client.get_status()
        return {
            "models": models,
            "current_provider": status["active_provider"],
            "current_model": status["active_model"],
            "status": status
        }
    except Exception as e:
        logger.error(f"List models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/models/switch")
async def switch_model(provider: str, model: Optional[str] = None):
    """Switch to a different provider/model"""
    try:
        llm_client.switch_provider(provider, model)
        status = llm_client.get_status()
        return {
            "success": True,
            "active_provider": status["active_provider"],
            "active_model": status["active_model"]
        }
    except Exception as e:
        logger.error(f"Switch model error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/models/status")
async def model_status():
    """Get current model status"""
    try:
        status = llm_client.get_status()
        return status
    except Exception as e:
        logger.error(f"Model status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/index/workspace")
async def index_workspace():
    """Index workspace for semantic search"""
    try:
        result = tool_executor.index_workspace()
        return result
    except Exception as e:
        logger.error(f"Index workspace error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/index/stats")
async def index_stats():
    """Get indexing statistics"""
    try:
        result = tool_executor.index_stats()
        return result
    except Exception as e:
        logger.error(f"Index stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/models/pull")
async def pull_model(model: str):
    """Pull a model from Ollama registry"""
    try:
        if not llm_client.ollama_client:
            raise HTTPException(status_code=400, detail="Ollama client not available")
        result = llm_client.ollama_client.pull_model(model)
        return result
    except Exception as e:
        logger.error(f"Pull model error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Include router
app.include_router(api_router)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
