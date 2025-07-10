from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio
import os
import sys
from datetime import datetime
import logging

# Add src to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SQL Agent API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    timestamp: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    success: bool
    sql_generated: Optional[str] = None
    data: Optional[list] = None
    result_count: Optional[int] = None

# Global agent instance
agent = None

@app.on_event("startup")
async def startup_event():
    """Initialize the SQL agent on startup"""
    global agent
    try:
        from src.agents.db_agent import create_database_agent
        agent = create_database_agent()
        logger.info("SQL Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize SQL agent: {e}")
        raise e

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "SQL Agent API is running", "status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for SQL agent"""
    try:
        if not agent:
            raise HTTPException(status_code=500, detail="SQL Agent not initialized")
        
        # Generate session ID if not provided
        session_id = request.session_id or f"web_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Processing chat request: {request.message} for session: {session_id}")
        
        # Process the question with the SQL agent
        response = await agent.answer_question(request.message, session_id)
        
        # Format response for the UI - make it concise
        answer = response.get("answer", "I apologize, but I couldn't process your question.")
        
        # Truncate long responses for better UI experience
        if len(answer) > 500:
            answer = answer[:497] + "..."
        
        formatted_response = ChatResponse(
            response=answer,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            success=response.get("success", False),
            sql_generated=response.get("sql_generated"),
            data=response.get("data"),
            result_count=response.get("result_count")
        )
        
        logger.info(f"Chat response generated successfully for session: {session_id}")
        return formatted_response
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_status": "initialized" if agent else "not_initialized"
    }

@app.post("/end_session")
async def end_session(session_id: str):
    """End a chat session and clear memory"""
    try:
        if agent and hasattr(agent, 'end_session'):
            agent.end_session()
            logger.info(f"Session {session_id} ended successfully")
            return {"message": f"Session {session_id} ended successfully"}
        else:
            return {"message": "Session management not available"}
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(status_code=500, detail=f"Error ending session: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Use asyncio loop instead of uvloop to avoid nest_asyncio conflicts
    uvicorn.run(app, host="0.0.0.0", port=8002, loop="asyncio")