import os
import sys
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from src.memory.json_memory_manager import JSONMemoryManager
    JSON_MEMORY_AVAILABLE = True
except ImportError:
    try:
        from memory.json_memory_manager import JSONMemoryManager
        JSON_MEMORY_AVAILABLE = True
    except ImportError:
        print("Warning: JSONMemoryManager not available")
        JSON_MEMORY_AVAILABLE = False

try:
    from src.utils.json_saver import JSONResponseSaver
    JSON_SAVER_AVAILABLE = True
except ImportError:
    try:
        from utils.json_saver import JSONResponseSaver
        JSON_SAVER_AVAILABLE = True
    except ImportError:
        print("Warning: JSONResponseSaver not available")
        JSON_SAVER_AVAILABLE = False

class AzureReActDatabaseAgent:
    """Enhanced database agent with JSON memory and response saving"""
    
    def __init__(self, session_id: str = None, memory_dir: str = "conversation_memory", responses_dir: str = "json_responses"):
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.memory_manager = None
        if JSON_MEMORY_AVAILABLE:
            self.memory_manager = JSONMemoryManager(memory_dir)
            logger.info(f"JSON Memory Manager initialized for session: {self.memory_manager.current_session_id}")
        else:
            logger.warning("JSON Memory Manager not available - memory features disabled")
        
        self.response_saver = None
        if JSON_SAVER_AVAILABLE:
            self.response_saver = JSONResponseSaver(responses_dir)
            logger.info(f"JSON Response Saver initialized at: {responses_dir}")
        else:
            logger.warning("JSON Response Saver not available - response saving disabled")
        
        self._initialize_react_agent()
    
    def _initialize_react_agent(self):
        """Initialize the enhanced ReAct agent"""
        try:
            from src.agents.react_agent import LangGraphReActDatabaseAgent
            self.agent = LangGraphReActDatabaseAgent(dialect="PostgreSQL", top_k=10)
            logger.info("Enhanced ReAct Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ReAct agent: {e}")
            raise e
    
    async def process_query(self, user_question: str, conversation_context: str = None, session_id: str = None) -> dict:
        """Process query - alias for answer_question for API compatibility"""
        return await self.answer_question(user_question, session_id=session_id)

    async def answer_question(self, user_question: str, session_id: str = None, schema_description: str = None) -> dict:
        """Answer user question with enhanced JSON memory and response saving"""
        try:
            if self.memory_manager:
                actual_session_id = self.memory_manager.current_session_id
                self.session_id = actual_session_id
                logger.info(f"Using memory manager session ID: {actual_session_id}")
            else:
                if session_id and session_id != self.session_id:
                    self.session_id = session_id
                    logger.info(f"Session ID updated to: {session_id}")
                actual_session_id = self.session_id
            
            logger.info(f"Processing question: '{user_question}' for session: {actual_session_id}")
            
            conversation_context = ""
            if self.memory_manager:
                try:
                    conversation_context = self.memory_manager.get_conversation_context()
                    logger.info(f"Retrieved conversation context: {len(conversation_context)} characters")
                    if self._is_follow_up_question(user_question):
                        enhanced_question = self._enhance_question_with_context(user_question, conversation_context)
                        logger.info(f"Enhanced follow-up question: {enhanced_question}")
                        user_question = enhanced_question
                except Exception as e:
                    logger.error(f"Error retrieving conversation context: {e}")
                    conversation_context = ""
            
            start_time = datetime.now()
            response_obj = await self.agent.process_query(user_question, conversation_context)
            processing_time = (datetime.now() - start_time).total_seconds()
            
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
                    "table_data": getattr(response_obj, 'table_data', None),
                    "metadata": getattr(response_obj, 'metadata', {})
                }
            
            enhanced_response = {
                "success": pydantic_response.get("success", False),
                "answer": pydantic_response.get("message", "No response"),
                "message": pydantic_response.get("message", "No response"),
                "query_understanding": pydantic_response.get("query_understanding", user_question),
                "data": self._extract_data_from_results(pydantic_response.get("results", [])),
                "sql_generated": pydantic_response.get("sql_query"),
                "sql_query": pydantic_response.get("sql_query"),
                "result_count": pydantic_response.get("result_count", 0),
                "table_data": pydantic_response.get("table_data"),
                "metadata": {
                    **pydantic_response.get("metadata", {}),
                    "processing_time_seconds": processing_time,
                    "session_id": actual_session_id,
                    "timestamp": datetime.now().isoformat(),
                    "agent_type": "enhanced_react_agent_with_json_memory",
                    "memory_enabled": JSON_MEMORY_AVAILABLE,
                    "response_saving_enabled": JSON_SAVER_AVAILABLE
                },
                "timestamp": datetime.now().isoformat(),
                "powered_by": "Enhanced LangGraph ReAct Agent with JSON Memory",
                "structured_response": pydantic_response,
                "session_id": actual_session_id
            }
            
            if self.memory_manager:
                try:
                    memory_summary = self.memory_manager.get_session_summary()
                    enhanced_response["metadata"]["memory_summary"] = memory_summary
                    
                    interaction_id = self.memory_manager.add_interaction(user_question, enhanced_response)
                    enhanced_response["metadata"]["interaction_id"] = interaction_id
                except Exception as e:
                    logger.error(f"Error adding interaction to memory: {e}")
                    enhanced_response["metadata"]["memory_error"] = str(e)
            
            if self.response_saver:
                try:
                    saved_file = self.response_saver.save_response(enhanced_response, user_question, actual_session_id)
                    if saved_file:
                        enhanced_response["metadata"]["saved_to_file"] = saved_file
                        logger.info(f"Response saved to: {saved_file}")
                except Exception as e:
                    logger.error(f"Error saving response to file: {e}")
                    enhanced_response["metadata"]["save_error"] = str(e)
            
            logger.info(f"Enhanced ReAct agent completed: {enhanced_response['success']}")
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Enhanced ReAct agent failed: {str(e)}")
            
            error_response = {
                "success": False,
                "answer": f"I apologize, but I encountered an error while processing your question: {str(e)}",
                "message": f"I apologize, but I encountered an error while processing your question: {str(e)}",
                "query_understanding": user_question,
                "data": None,
                "sql_generated": None,
                "sql_query": None,
                "result_count": 0,
                "metadata": {
                    "error_type": type(e).__name__, 
                    "error_details": str(e),
                    "agent_type": "enhanced_react_agent_with_json_memory",
                    "session_id": actual_session_id if 'actual_session_id' in locals() else self.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "memory_enabled": JSON_MEMORY_AVAILABLE,
                    "response_saving_enabled": JSON_SAVER_AVAILABLE
                },
                "timestamp": datetime.now().isoformat(),
                "powered_by": "Enhanced LangGraph ReAct Agent with JSON Memory (Error)",
                "structured_response": None,
                "session_id": actual_session_id if 'actual_session_id' in locals() else self.session_id
            }
            
            if self.memory_manager:
                try:
                    interaction_id = self.memory_manager.add_interaction(user_question, error_response)
                    error_response["metadata"]["interaction_id"] = interaction_id
                except Exception as e:
                    logger.error(f"Error adding error interaction to memory: {e}")
            
            if self.response_saver:
                try:
                    saved_file = self.response_saver.save_response(error_response, user_question, actual_session_id if 'actual_session_id' in locals() else self.session_id)
                    if saved_file:
                        error_response["metadata"]["saved_to_file"] = saved_file
                except Exception as e:
                    logger.error(f"Error saving error response to file: {e}")
            
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
            "in addition", "also show", "also tell", "and also",
            "continue", "expand on", "more details about",
            "for them", "for him", "for her", "for this patient",
            "their", "his", "her", "same patient", "that patient",
            "also find", "now show", "now tell", "what else",
            "any other", "more about", "details on"
        ]
        question_lower = user_question.lower()
        
        has_follow_up_indicator = any(indicator in question_lower for indicator in follow_up_indicators)
        
        has_pronoun_reference = any(pronoun in question_lower for pronoun in ["them", "him", "her", "they", "their", "his", "her"]) and not any(question_lower.count(name) > 0 for name in ["john", "jane", "smith", "doe", "patient"])
        
        return has_follow_up_indicator or has_pronoun_reference
    
    def _enhance_question_with_context(self, user_question: str, conversation_context: str) -> str:
        """Enhance follow-up questions with conversation context"""
        if not conversation_context:
            return user_question
        
        enhanced_question = f"""
{conversation_context}

Current question: {user_question}

Please use the previous conversation context to properly understand and answer the current question. Pay attention to any patients, conditions, or topics mentioned in the previous interactions.
"""
        return enhanced_question
    
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
            logger.info(f"Cleared memory for session: {self.memory_manager.current_session_id}")
        else:
            logger.warning("Memory manager not available for clearing")
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get memory summary"""
        if self.memory_manager:
            return self.memory_manager.get_session_summary()
        return {"error": "Memory manager not available"}
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        if self.memory_manager:
            return self.memory_manager.get_memory_stats()
        return {"error": "Memory manager not available"}
    
    def search_memory(self, query_term: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Search conversation memory"""
        if self.memory_manager:
            return self.memory_manager.search_memory(query_term, max_results)
        return []
    
    def search_responses(self, search_term: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search saved responses"""
        if self.response_saver:
            return self.response_saver.search_responses(search_term, max_results)
        return []
    
    def get_conversation_history(self, last_n_interactions: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history"""
        if self.memory_manager:
            session_data = self.memory_manager._load_session_data()
            return session_data.get("conversation_history", [])[-last_n_interactions:]
        return []
    
    def start_new_session(self, new_session_id: str = None):
        """Start a new conversation session"""
        if self.memory_manager:
            self.save_session_summary()
            
            self.memory_manager.clear_session_memory()
            
            self.session_id = new_session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            logger.info(f"Started new session: {self.memory_manager.current_session_id}")
        else:
            self.session_id = new_session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"Started new session: {self.session_id}")
    
    def end_session(self):
        """End the current session"""
        if self.memory_manager:
            self.save_session_summary()
            logger.info(f"Session ended: {self.memory_manager.current_session_id}")
        
        if self.response_saver:
            self.response_saver.save_daily_summary()
            logger.info("Daily summary saved")
    
    def save_session_summary(self):
        """Save session summary to JSON"""
        if self.memory_manager and self.response_saver:
            try:
                session_data = self.memory_manager._load_session_data()
                
                session_responses = []
                for interaction in session_data.get("conversation_history", []):
                    session_responses.append({
                        "query_metadata": {
                            "original_query": interaction["user_query"],
                            "timestamp": interaction["timestamp"],
                            "session_id": self.memory_manager.current_session_id,
                            "interaction_id": interaction["interaction_id"]
                        },
                        "response": interaction["agent_response"]
                    })
                
                if session_responses:
                    saved_file = self.response_saver.save_session_responses(session_responses, self.memory_manager.current_session_id)
                    if saved_file:
                        logger.info(f"Session summary saved to: {saved_file}")
                        return saved_file
                
            except Exception as e:
                logger.error(f"Error saving session summary: {e}")
        
        return None
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        stats = {"memory_stats": {}, "response_stats": {}}
        
        if self.memory_manager:
            stats["memory_stats"] = self.memory_manager.get_memory_stats()
        
        if self.response_saver:
            stats["response_stats"] = self.response_saver.get_storage_stats()
        
        return stats
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """Clean up old data files"""
        cleanup_results = {}
        
        if self.response_saver:
            cleanup_results["response_cleanup"] = self.response_saver.cleanup_old_files(days_to_keep)
        
        return cleanup_results
    
    def export_session_data(self, export_format: str = "json") -> Optional[str]:
        """Export current session data"""
        if self.response_saver and self.memory_manager:
            return self.response_saver.export_session_data(self.memory_manager.current_session_id, export_format)
        return None


class AzureIntelligentDatabaseAgent(AzureReActDatabaseAgent):
    """Alias for backward compatibility"""
    pass

class EnhancedReActDatabaseAgent(AzureReActDatabaseAgent):
    """Alias for backward compatibility"""
    pass

def create_database_agent(approach: str = "react", session_id: str = None, memory_dir: str = "conversation_memory", responses_dir: str = "json_responses"):
    """Factory function to create database agent with JSON memory"""
    return AzureReActDatabaseAgent(session_id=session_id, memory_dir=memory_dir, responses_dir=responses_dir)