import os
import sys
from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime

try:
    from memory.conversation_memory import ConversationMemoryManager
except ImportError:
    try:
        from src.memory.conversation_memory import ConversationMemoryManager
    except ImportError:
        ConversationMemoryManager = None

logger = structlog.get_logger(__name__)

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class AzureReActDatabaseAgent:
    def __init__(self, session_id: str = None, memory_file_path: str = "conversation_memory.json"):
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.memory_manager = None
        if ConversationMemoryManager:
            self.memory_manager = ConversationMemoryManager(self.session_id, memory_file_path)
        self._initialize_react_agent()

    def _initialize_react_agent(self):
        """Initialize the enhanced ReAct agent"""
        try:
            from agents.react_agent import LangGraphReActDatabaseAgent
            self.agent = LangGraphReActDatabaseAgent(dialect="PostgreSQL", top_k=10)
            logger.info("Enhanced ReAct Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ReAct agent: {e}")
            raise e

    async def answer_question(self, user_question: str, session_id: str = None, schema_description: str = None) -> dict:
        """Answer user question with enhanced natural language processing"""
        try:
            # Handle session management
            if session_id and session_id != self.session_id:
                self.session_id = session_id
                if self.memory_manager:
                    self.memory_manager.session_id = session_id
                    self.memory_manager.memory_data = self.memory_manager._load_memory()
            
            logger.info(f"Processing question: '{user_question}' for session: {self.session_id}")
            
            # Get conversation context
            conversation_context = ""
            if self.memory_manager:
                conversation_context = self.memory_manager.get_conversation_context()
                if self._is_follow_up_question(user_question):
                    enhanced_question = self._enhance_question_with_context(user_question, conversation_context)
                    logger.info(f"Enhanced follow-up question: {enhanced_question}")
                    user_question = enhanced_question
            
            # Process the query with the enhanced agent
            response_obj = await self.agent.process_query(user_question, conversation_context)
            
            # Convert to legacy format
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
            
            # Create legacy response format
            legacy_response = {
                "success": pydantic_response.get("success", False),
                "answer": pydantic_response.get("message", "No response"),
                "query_understanding": pydantic_response.get("query_understanding", user_question),
                "data": self._extract_data_from_results(pydantic_response.get("results", [])),
                "sql_generated": pydantic_response.get("sql_query"),
                "result_count": pydantic_response.get("result_count", 0),
                "metadata": pydantic_response.get("metadata", {}),
                "timestamp": datetime.now().isoformat(),
                "powered_by": "Enhanced LangGraph ReAct Agent",
                "message": pydantic_response.get("message"),
                "structured_response": pydantic_response,
                "session_id": self.session_id
            }
            
            # Add memory summary if available
            if self.memory_manager:
                legacy_response["metadata"]["memory_summary"] = self.memory_manager.get_memory_summary()
                self.memory_manager.add_interaction(user_question, legacy_response)
            
            logger.info(f"Enhanced ReAct agent completed: {legacy_response['success']}")
            return legacy_response
            
        except Exception as e:
            logger.error(f"Enhanced ReAct agent failed: {str(e)}")
            error_response = {
                "success": False,
                "answer": f"I apologize, but I encountered an error while processing your question: {str(e)}",
                "query_understanding": user_question,
                "data": None,
                "sql_generated": None,
                "result_count": 0,
                "metadata": {
                    "error_type": type(e).__name__, 
                    "error_details": str(e),
                    "agent_type": "enhanced_react_agent"
                },
                "timestamp": datetime.now().isoformat(),
                "powered_by": "Enhanced LangGraph ReAct Agent (Error)",
                "structured_response": None,
                "session_id": self.session_id
            }
            
            if self.memory_manager:
                self.memory_manager.add_interaction(user_question, error_response)
            
            return error_response

    def _is_follow_up_question(self, user_question: str) -> bool:
        """Check if the question is a follow-up to previous interactions"""
        follow_up_indicators = [
            "from the previous", "from last", "from that", "from those",
            "based on the above", "based on previous", "based on last",
            "show me more", "tell me more", "what about",
            "from earlier", "from before", "that result", "those results",
            "the last query", "previous query", "last search",
            "can you also", "additionally", "furthermore",
            "in addition", "also show", "also tell"
        ]
        question_lower = user_question.lower()
        return any(indicator in question_lower for indicator in follow_up_indicators)

    def _enhance_question_with_context(self, user_question: str, conversation_context: str) -> str:
        """Enhance follow-up questions with conversation context"""
        if not conversation_context:
            return user_question
        
        last_interaction = None
        if self.memory_manager:
            last_interaction = self.memory_manager.get_last_successful_query()
        
        if last_interaction:
            enhanced_question = f"""
Context from previous interaction:
- Previous query: {last_interaction['user_query']}
- SQL used: {last_interaction['agent_response'].get('sql_generated', 'N/A')}
- Results found: {last_interaction['agent_response'].get('result_count', 0)} records

Current follow-up question: {user_question}

Please answer the current question using the context from the previous interaction.
"""
            return enhanced_question
        return user_question

    def _extract_data_from_results(self, results):
        """Extract data from results for legacy format"""
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

    def clear_session_memory(self):
        """Clear session memory"""
        if self.memory_manager:
            self.memory_manager.clear_session_memory()
            logger.info(f"Cleared memory for session: {self.session_id}")
        else:
            logger.warning("Memory manager not available for clearing")

    def get_memory_summary(self) -> Dict[str, Any]:
        """Get memory summary"""
        if self.memory_manager:
            return self.memory_manager.get_memory_summary()
        return {"error": "Memory manager not available"}

    def search_memory(self, query_term: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Search conversation memory"""
        if self.memory_manager:
            return self.memory_manager.search_memory(query_term, max_results)
        return []

    def get_conversation_history(self, last_n_interactions: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history"""
        if self.memory_manager:
            return self.memory_manager.memory_data["conversation_history"][-last_n_interactions:]
        return []

    def start_new_session(self, new_session_id: str = None):
        """Start a new conversation session"""
        if self.memory_manager:
            self.memory_manager.clear_session_memory()
        
        self.session_id = new_session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if self.memory_manager:
            self.memory_manager.session_id = self.session_id
            self.memory_manager.memory_data = self.memory_manager._create_empty_session()
        
        logger.info(f"Started new session: {self.session_id}")

    def end_session(self):
        """End the current session"""
        if self.memory_manager:
            self.memory_manager.clear_session_memory()

# Backward compatibility aliases
class AzureIntelligentDatabaseAgent(AzureReActDatabaseAgent):
    """Alias for backward compatibility"""
    pass

class EnhancedReActDatabaseAgent(AzureReActDatabaseAgent):
    """Alias for backward compatibility"""
    pass

def create_database_agent(approach: str = "react", session_id: str = None, memory_file_path: str = "conversation_memory.json"):
    """Factory function to create database agent"""
    return AzureReActDatabaseAgent(session_id=session_id, memory_file_path=memory_file_path)