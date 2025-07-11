#!/usr/bin/env python3
"""
FastAPI Backend Server for Healthcare Database Assistant
Based on the reference implementation from AI-Agent-for-Healthcare
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from src.agents.react_agent import LangGraphReActDatabaseAgent
    from src.agents.db_agent import AzureReActDatabaseAgent
    from src.storage.api_storage import APIStorageManager
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    LangGraphReActDatabaseAgent = None
    AzureReActDatabaseAgent = None
    APIStorageManager = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

agent = None
agent_sessions = {}
api_storage = None

class ChatRequest(BaseModel):
    """Request model for chat interactions"""
    message: str = Field(..., description="User message/query")
    session_id: Optional[str] = Field(None, description="Optional session identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional conversation context")

class ChatResponse(BaseModel):
    """Response model for chat interactions"""
    response: str = Field(..., description="Generated response")
    sql_generated: Optional[str] = Field(None, description="Generated SQL query")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Query results")
    result_count: int = Field(0, description="Number of results")
    success: bool = Field(True, description="Whether the query was successful")
    session_id: Optional[str] = Field(None, description="Session identifier")
    query_understanding: Optional[str] = Field(None, description="AI's understanding of the query")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    table_data: Optional[Dict[str, Any]] = Field(None, description="Structured table data for display")

class HealthResponse(BaseModel):
    """Response model for health checks"""
    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Current timestamp")
    agent_ready: bool = Field(..., description="Whether the agent is ready")
    database_connected: bool = Field(False, description="Database connection status")

class SessionResponse(BaseModel):
    """Response model for session operations"""
    message: str = Field(..., description="Operation result message")
    session_id: Optional[str] = Field(None, description="Session identifier")
    success: bool = Field(True, description="Whether the operation was successful")

async def initialize_agent():
    """Initialize the healthcare database agent"""
    global agent
    try:
        logger.info("Initializing healthcare database agent...")
        
        if AzureReActDatabaseAgent:
            try:
                agent = AzureReActDatabaseAgent(
                    memory_dir="conversation_memory",
                    responses_dir="json_responses"
                )
                logger.info("✅ Enhanced Azure ReAct Database Agent initialized")
                return
            except Exception as e:
                logger.warning(f"Enhanced agent initialization failed: {e}")
        
        if LangGraphReActDatabaseAgent:
            try:
                agent = LangGraphReActDatabaseAgent()
                logger.info("✅ Basic LangGraph ReAct Database Agent initialized")
                return
            except Exception as e:
                logger.error(f"Basic agent initialization failed: {e}")
        
        raise Exception("No agent implementation available")
        
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise

async def initialize_storage():
    """Initialize the API storage manager"""
    global api_storage
    try:
        if APIStorageManager:
            api_storage = APIStorageManager()
            logger.info("✅ API Storage Manager initialized")
        else:
            logger.warning("⚠️  API Storage Manager not available")
    except Exception as e:
        logger.error(f"Failed to initialize API storage: {e}")
        raise

async def cleanup_agent():
    """Cleanup agent resources"""
    global agent
    if agent and hasattr(agent, '_cleanup'):
        try:
            await agent._cleanup()
            logger.info("✅ Agent resources cleaned up")
        except Exception as e:
            logger.warning(f"Error during agent cleanup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    logger.info("🚀 Starting Healthcare Database Assistant API Server...")
    await initialize_agent()
    await initialize_storage()
    yield
    logger.info("🔄 Shutting down Healthcare Database Assistant API Server...")
    await cleanup_agent()

app = FastAPI(
    title="Healthcare Database Assistant API",
    description="AI-powered healthcare database query assistant with natural language processing",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    
    try:
        response = await call_next(request)
        process_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        return response
    except Exception as e:
        process_time = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"{request.method} {request.url.path} - "
            f"Error: {str(e)} - "
            f"Time: {process_time:.4f}s"
        )
        raise

@app.get("/")
async def root():
    """Root endpoint for basic health check"""
    return {
        "message": "Healthcare Database Assistant API is running",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check endpoint"""
    database_connected = False
    
    if agent and hasattr(agent, 'db_connection'):
        try:
            connected, error = await agent.db_connection.test_connection()
            database_connected = connected
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
    
    return HealthResponse(
        status="healthy" if agent else "degraded",
        timestamp=datetime.now().isoformat(),
        agent_ready=agent is not None,
        database_connected=database_connected
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Process chat messages and return structured responses"""
    if not agent:
        raise HTTPException(
            status_code=503,
            detail="Agent not available. Please check server logs."
        )
    
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )
    
    if len(request.message) > 5000:
        raise HTTPException(
            status_code=400,
            detail="Message too long. Maximum length is 5000 characters."
        )
    
    session_id = request.session_id
    if not session_id:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    start_time = time.time()
    request_id = None
    
    try:
        logger.info(f"Processing chat request for session {session_id}: {request.message}")
        
        if api_storage:
            request_data = {
                "session_id": session_id,
                "endpoint": "/chat",
                "method": "POST",
                "user_query": request.message,
                "ip_address": req.client.host if req.client else "",
                "user_agent": req.headers.get("user-agent", ""),
                "headers": dict(req.headers)
            }
            request_id = await api_storage.log_api_request(request_data)
            await api_storage.create_or_update_session(session_id, request_data)
        
        if session_id not in agent_sessions:
            agent_sessions[session_id] = {
                "created_at": datetime.now().isoformat(),
                "messages": []
            }
        
        agent_sessions[session_id]["messages"].append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        })
        
        conversation_context = None
        if len(agent_sessions[session_id]["messages"]) > 1:
            recent_messages = agent_sessions[session_id]["messages"][-5:]
            conversation_context = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in recent_messages[:-1]
            ])
        
        if hasattr(agent, '__aenter__'):
            async with agent as ctx_agent:
                if hasattr(ctx_agent, 'process_query'):
                    response_obj = await ctx_agent.process_query(
                        request.message, 
                        conversation_context=conversation_context
                    )
                else:
                    response_obj = await ctx_agent.answer_question(
                        request.message, 
                        session_id=session_id
                    )
        else:
            if hasattr(agent, 'process_query'):
                response_obj = await agent.process_query(
                    request.message, 
                    conversation_context=conversation_context
                )
            else:
                response_obj = await agent.answer_question(
                    request.message, 
                    session_id=session_id
                )
        
        if hasattr(response_obj, 'dict'):
            response_data = response_obj.dict()
        else:
            response_data = response_obj
        
        if "answer" in response_data:
            response_text = response_data.get("answer", "Query processed successfully")
        else:
            response_text = response_data.get("message", "Query processed successfully")
        
        sql_query = response_data.get("sql_query") or response_data.get("sql_generated")
        data = response_data.get("data", [])
        result_count = response_data.get("result_count", len(data) if data else 0)
        success = response_data.get("success", True)
        query_understanding = response_data.get("query_understanding", "")
        metadata = response_data.get("metadata", {})
        
        table_data = response_data.get("table_data")
        if table_data and hasattr(table_data, 'dict'):
            table_data = table_data.dict()
        
        logger.info(f"Response has table_data: {table_data is not None}")
        
        processing_time = time.time() - start_time
        
        if data and hasattr(data[0], 'data'):
            data = [item.data for item in data]
        
        agent_sessions[session_id]["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat(),
            "sql_query": sql_query,
            "result_count": result_count
        })
        
        metadata.update({
            "session_id": session_id,
            "api_version": "1.0.0",
            "processing_time": processing_time,
            "agent_type": metadata.get("agent_type", "unknown")
        })
        
        chat_response = ChatResponse(
            response=response_text,
            sql_generated=sql_query,
            data=data,
            result_count=result_count,
            success=success,
            session_id=session_id,
            query_understanding=query_understanding,
            metadata=metadata,
            table_data=table_data
        )
        
        if api_storage and request_id:
            response_dict = chat_response.dict()
            await api_storage.log_api_response(request_id, response_dict, processing_time)
            await api_storage.update_session_result(session_id, success, processing_time)
            await api_storage.update_analytics()
        
        return chat_response
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        processing_time = time.time() - start_time
        
        if session_id in agent_sessions:
            agent_sessions[session_id]["messages"].append({
                "role": "assistant",
                "content": f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "error": True
            })
        
        error_response = ChatResponse(
            response=f"I apologize, but I encountered an error while processing your request: {str(e)}",
            sql_generated=None,
            data=[],
            result_count=0,
            success=False,
            session_id=session_id,
            query_understanding=f"Error processing: {request.message}",
            metadata={"error": str(e), "session_id": session_id}
        )
        
        if api_storage and request_id:
            response_dict = error_response.dict()
            await api_storage.log_api_response(request_id, response_dict, processing_time)
            await api_storage.update_session_result(session_id, False, processing_time)
        
        return error_response

@app.post("/end_session", response_model=SessionResponse)
async def end_session(session_id: str):
    """End a chat session and clean up resources"""
    try:
        if session_id in agent_sessions:
            session_data = agent_sessions[session_id]
            
            if agent and hasattr(agent, 'save_session_summary'):
                try:
                    await agent.save_session_summary()
                except Exception as e:
                    logger.warning(f"Error saving session summary: {e}")
            
            del agent_sessions[session_id]
            
            return SessionResponse(
                message=f"Session {session_id} ended successfully",
                session_id=session_id,
                success=True
            )
        else:
            return SessionResponse(
                message=f"Session {session_id} not found",
                session_id=session_id,
                success=False
            )
            
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        return SessionResponse(
            message=f"Error ending session: {str(e)}",
            session_id=session_id,
            success=False
        )

@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    return {
        "active_sessions": list(agent_sessions.keys()),
        "total_sessions": len(agent_sessions),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    if session_id not in agent_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "session_data": agent_sessions[session_id],
        "message_count": len(agent_sessions[session_id]["messages"]),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/analytics")
async def get_analytics(days: int = 7):
    """Get API analytics for the specified number of days"""
    if not api_storage:
        raise HTTPException(status_code=503, detail="API storage not available")
    
    try:
        analytics = await api_storage.get_api_analytics(days)
        return analytics
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/storage/stats")
async def get_storage_stats():
    """Get comprehensive storage statistics"""
    if not api_storage:
        raise HTTPException(status_code=503, detail="API storage not available")
    
    try:
        stats = await api_storage.get_storage_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/storage/cleanup")
async def cleanup_storage(days_to_keep: int = 30):
    """Clean up old API data"""
    if not api_storage:
        raise HTTPException(status_code=503, detail="API storage not available")
    
    try:
        cleanup_stats = await api_storage.cleanup_old_data(days_to_keep)
        return {
            "message": "Storage cleanup completed",
            "cleanup_stats": cleanup_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error during storage cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/{cache_key}")
async def get_cached_response(cache_key: str):
    """Get cached API response"""
    if not api_storage:
        raise HTTPException(status_code=503, detail="API storage not available")
    
    try:
        cached_response = await api_storage.get_cached_response(cache_key)
        if cached_response:
            return {
                "cached": True,
                "response": cached_response,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Cache entry not found or expired")
    except Exception as e:
        logger.error(f"Error getting cached response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cache/{cache_key}")
async def cache_response(cache_key: str, response_data: Dict[str, Any], ttl_minutes: int = 30):
    """Cache API response"""
    if not api_storage:
        raise HTTPException(status_code=503, detail="API storage not available")
    
    try:
        success = await api_storage.cache_response(cache_key, response_data, ttl_minutes)
        return {
            "cached": success,
            "cache_key": cache_key,
            "ttl_minutes": ttl_minutes,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error caching response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rate-limit/{ip_address}")
async def check_rate_limit_status(ip_address: str, endpoint: str = "/chat"):
    """Check rate limit status for an IP address"""
    if not api_storage:
        raise HTTPException(status_code=503, detail="API storage not available")
    
    try:
        is_allowed, limit_info = await api_storage.check_rate_limit(ip_address, endpoint, 60)
        return {
            "ip_address": ip_address,
            "endpoint": endpoint,
            "is_allowed": is_allowed,
            "limit_info": limit_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset_session", response_model=SessionResponse)
async def reset_session(session_id: Optional[str] = None):
    """Reset/clear session conversation history and create a new session"""
    try:
        if session_id and session_id in agent_sessions:
            del agent_sessions[session_id]
            logger.info(f"Cleared existing session: {session_id}")
        
        if agent:
            try:
                if hasattr(agent, 'memory_manager'):
                    if hasattr(agent.memory_manager, 'clear_session_memory'):
                        agent.memory_manager.clear_session_memory()
                        logger.info("Agent memory cleared successfully (JSON memory manager)")
                    elif hasattr(agent.memory_manager, 'reset_session'):
                        agent.memory_manager.reset_session()
                        logger.info("Agent memory reset successfully (conversation memory)")
                    else:
                        logger.warning("Agent has memory_manager but no clear/reset method found")
                elif hasattr(agent, 'clear_session_memory'):
                    agent.clear_session_memory()
                    logger.info("Agent session memory cleared successfully")
                elif hasattr(agent, 'reset_session'):
                    agent.reset_session()
                    logger.info("Agent session reset successfully")
                else:
                    logger.warning("No memory management methods found on agent")
            except Exception as e:
                logger.warning(f"Error resetting agent memory: {e}")
        
        new_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return SessionResponse(
            message="Session reset successfully. New conversation started.",
            session_id=new_session_id,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error resetting session: {e}")
        return SessionResponse(
            message=f"Error resetting session: {str(e)}",
            session_id=session_id,
            success=False
        )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat()
        }
    )

def main():
    """Main entry point for the server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Healthcare Database Assistant API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8002, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", help="Log level")
    
    args = parser.parse_args()
    
    logger.info(f"Starting server on {args.host}:{args.port}")
    
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )

if __name__ == "__main__":
    main()