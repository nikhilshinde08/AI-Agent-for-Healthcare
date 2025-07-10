import os
import sys
from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime

try:
    from memory.conversation_memory import ConversationMemory as ConversationMemoryManager
except ImportError:
    try:
        from src.memory.conversation_memory import ConversationMemory as ConversationMemoryManager
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
        try:
            from agents.react_agent import LangGraphReActDatabaseAgent
            self.agent = LangGraphReActDatabaseAgent(dialect="PostgreSQL", top_k=10)
            logger.info("Enhanced ReAct Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ReAct agent: {e}")
            raise e

    async def answer_question(self, user_question: str, session_id: str = None, schema_description: str = None) -> dict:
        try:
            if session_id and session_id != self.session_id:
                self.session_id = session_id
                if self.memory_manager:
                    # Create a new memory manager instance for the new session
                    self.memory_manager = ConversationMemoryManager(session_id, force_new_session=False)
            
            logger.info(f"Processing question: '{user_question}' for session: {self.session_id}")
            
            conversation_context = ""
            if self.memory_manager:
                conversation_context = self.memory_manager.get_conversation_context()
                if self._is_follow_up_question(user_question):
                    enhanced_question = self._enhance_question_with_context(user_question, conversation_context)
                    logger.info(f"Enhanced follow-up question: {enhanced_question}")
                    user_question = enhanced_question
            
            response_obj = await self.agent.process_query(user_question, conversation_context)
            
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
                "powered_by": "Enhanced LangGraph ReAct Agent",
                "message": pydantic_response.get("message"),
                "structured_response": pydantic_response,
                "session_id": self.session_id
            }
            
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
        if self.memory_manager:
            self.memory_manager.clear_session_memory()
            logger.info(f"Cleared memory for session: {self.session_id}")
        else:
            logger.warning("Memory manager not available for clearing")

    def get_memory_summary(self) -> Dict[str, Any]:
        if self.memory_manager:
            return self.memory_manager.get_memory_summary()
        return {"error": "Memory manager not available"}

    def search_memory(self, query_term: str, max_results: int = 3) -> List[Dict[str, Any]]:
        if self.memory_manager:
            return self.memory_manager.search_memory(query_term, max_results)
        return []

    def get_conversation_history(self, last_n_interactions: int = 10) -> List[Dict[str, Any]]:
        if self.memory_manager:
            memory_data = self.memory_manager.memory_data
            return memory_data.get("conversation_history", [])[-last_n_interactions:]
        return []

    def start_new_session(self, new_session_id: str = None):
        if self.memory_manager:
            self.memory_manager.clear_session_memory()
        
        self.session_id = new_session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if self.memory_manager:
            self.memory_manager = ConversationMemoryManager(self.session_id, force_new_session=True)
        
        logger.info(f"Started new session: {self.session_id}")

    def end_session(self):
        if self.memory_manager:
            # Save the session before ending
            self.memory_manager.save_session_to_file()
            self.memory_manager.clear_session_memory()

# Backward compatibility aliases
class AzureIntelligentDatabaseAgent(AzureReActDatabaseAgent):
    pass

class EnhancedReActDatabaseAgent(AzureReActDatabaseAgent):
    pass

def create_database_agent(approach: str = "react", session_id: str = None, memory_file_path: str = "conversation_memory.json"):
    return AzureReActDatabaseAgent(session_id=session_id, memory_file_path=memory_file_path)