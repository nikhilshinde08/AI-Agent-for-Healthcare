# src/agents/db_agent.py
import os
import sys
from typing import Dict, Any
import structlog
import asyncio
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = structlog.get_logger(__name__)

class AzureReActDatabaseAgent:
    """Database agent using ReAct pattern"""
    
    def __init__(self):
        self.agent = None
        self._initialize_react_agent()
    
    def _initialize_react_agent(self):
        """Initialize the ReAct agent"""
        try:
            from agents.react_agent import LangGraphReActDatabaseAgent
            self.agent = LangGraphReActDatabaseAgent(dialect="PostgreSQL", top_k=10)
            logger.info("ReAct Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ReAct agent: {e}")
            raise e
    
    async def answer_question(self, user_question: str, session_id: str = "default", schema_description: str = None) -> dict:
        """Process user question using ReAct agent"""
        try:
            logger.info(f"Processing question: '{user_question}'")
            
            response_obj = await self.agent.process_query(user_question)
            
            if hasattr(response_obj, 'dict'):
                pydantic_response = response_obj.dict()
            else:
                pydantic_response = {
                    "success": getattr(response_obj, 'success', False),
                    "message": getattr(response_obj, 'message', 'No message'),
                    "query_understanding": getattr(response_obj, 'query_understanding', user_question),
                    "sql_query": getattr(response_obj, 'sql_query', None),
                    "result_count": getattr(response_obj, 'result_count', 0),
                    "results": getattr(response_obj, 'results', []),
                    "metadata": getattr(response_obj, 'metadata', {})
                }
            
            legacy_response = {
                "success": pydantic_response.get("success", False),
                "answer": pydantic_response.get("message", "No response"),
                "query_understanding": pydantic_response.get("query_understanding", user_question),
                "data": self._extract_data_from_results(pydantic_response.get("results", [])),
                "sql_generated": pydantic_response.get("sql_query"),
                "result_count": pydantic_response.get("result_count", 0),
                "metadata": pydantic_response.get("metadata", {}),
                "timestamp": datetime.now().isoformat(),
                "powered_by": "LangGraph ReAct Agent",
                "message": pydantic_response.get("message"),
                "structured_response": pydantic_response
            }
            
            logger.info(f"ReAct agent completed: {legacy_response['success']}")
            return legacy_response
            
        except Exception as e:
            logger.error(f"ReAct agent failed: {str(e)}")
            return {
                "success": False,
                "answer": f"I encountered an error: {str(e)}",
                "query_understanding": user_question,
                "data": None,
                "sql_generated": None,
                "result_count": 0,
                "metadata": {"error_type": type(e).__name__, "error_details": str(e)},
                "timestamp": datetime.now().isoformat(),
                "powered_by": "LangGraph ReAct Agent (Error)",
                "structured_response": None
            }
    
    def _extract_data_from_results(self, results):
        """Extract data from Pydantic QueryResult objects"""
        if not results:
            return []
        
        data = []
        for result in results:
            if isinstance(result, dict):
                if "data" in result:
                    data.append(result["data"])
                else:
                    data.append(result)
            else:
                if hasattr(result, 'data'):
                    data.append(result.data)
                else:
                    data.append({"value": str(result)})
        
        return data

class AzureIntelligentDatabaseAgent(AzureReActDatabaseAgent):
    """Alias for backwards compatibility"""
    pass

class EnhancedReActDatabaseAgent(AzureReActDatabaseAgent):
    """Alias for backwards compatibility"""
    pass

def create_database_agent(approach: str = "react"):
    """Factory function to create database agent"""
    return AzureReActDatabaseAgent()