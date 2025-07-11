
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
import structlog

logger = structlog.get_logger(__name__)

class JSONMemoryManager:
    """Enhanced JSON-based memory manager for conversation history"""
    
    def __init__(self, base_dir: str = "conversation_memory"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        

        self.sessions_dir = self.base_dir / "sessions"
        self.daily_dir = self.base_dir / "daily"
        self.responses_dir = self.base_dir / "responses"
        
        for dir_path in [self.sessions_dir, self.daily_dir, self.responses_dir]:
            dir_path.mkdir(exist_ok=True)
        

        self.current_session_id = self._find_or_create_session()
        self.session_file = self.sessions_dir / f"{self.current_session_id}.json"
        

        if not self.session_file.exists():
            self._initialize_session()
        else:
            logger.info(f"Recovered existing session: {self.current_session_id}")
        
        logger.info(f"JSON Memory Manager initialized with session: {self.current_session_id}")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"session_{timestamp}_{unique_id}"
    
    def _find_or_create_session(self) -> str:
        """Find existing session from today or create new one"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            

            for session_file in self.sessions_dir.glob(f"session_{today}_*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    

                    created_at = datetime.fromisoformat(session_data.get('created_at', ''))
                    hours_ago = (datetime.now() - created_at).total_seconds() / 3600
                    
                    if hours_ago < 4:
                        session_id = session_data.get('session_id')
                        if session_id:
                            logger.info(f"Found recent session from today: {session_id} ({hours_ago:.1f}h ago)")
                            return session_id
                
                except Exception as e:
                    logger.warning(f"Error reading session file {session_file}: {e}")
            

            logger.info("No recent session found, creating new session")
            return self._generate_session_id()
            
        except Exception as e:
            logger.error(f"Error finding session: {e}")
            return self._generate_session_id()
    
    def _initialize_session(self):
        """Initialize a new session file"""
        session_data = {
            "session_id": self.current_session_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "total_interactions": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "conversation_history": [],
            "session_metadata": {
                "agent_type": "enhanced_react_agent",
                "database_type": "postgresql",
                "memory_version": "2.0"
            },
            "current_context": {
                "last_patient_mentioned": None,
                "last_query_type": None,
                "last_successful_query": None
            }
        }
        
        self._save_session_data(session_data)
    
    def _save_session_data(self, session_data: Dict[str, Any]):
        """Save session data to JSON file with backup and retry"""
        session_data["last_updated"] = datetime.now().isoformat()
        

        backup_file = None
        if self.session_file.exists():
            backup_file = self.session_file.with_suffix('.json.bak')
            try:
                backup_file.write_text(self.session_file.read_text())
            except Exception as e:
                logger.warning(f"Could not create backup: {e}")
        

        for attempt in range(3):
            try:
                with open(self.session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False, default=str)
                logger.debug(f"Session data saved to {self.session_file} (attempt {attempt + 1})")
                

                if backup_file and backup_file.exists():
                    backup_file.unlink()
                return
                
            except Exception as e:
                logger.error(f"Error saving session data (attempt {attempt + 1}): {e}")
                if attempt == 2:
                    if backup_file and backup_file.exists():
                        try:
                            self.session_file.write_text(backup_file.read_text())
                            logger.warning("Restored session from backup after save failure")
                        except Exception as restore_e:
                            logger.error(f"Could not restore backup: {restore_e}")
                    raise e
    
    def _load_session_data(self) -> Dict[str, Any]:
        """Load session data from JSON file with retry mechanism"""
        for attempt in range(3):
            try:
                if self.session_file.exists():
                    with open(self.session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data and 'conversation_history' in data:
                            logger.debug(f"Successfully loaded session data with {len(data['conversation_history'])} interactions")
                            return data
                        else:
                            logger.warning(f"Session file exists but has invalid structure: {self.session_file}")
                            return self._create_empty_session()
                else:
                    logger.warning(f"Session file not found: {self.session_file}")
                    return self._create_empty_session()
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"JSON decode error on attempt {attempt + 1}: {e}")
                if attempt == 2:
                    logger.error("Failed to load session data after 3 attempts, creating new session")
                    return self._create_empty_session()
            except Exception as e:
                logger.error(f"Error loading session data on attempt {attempt + 1}: {e}")
                if attempt == 2:
                    return self._create_empty_session()
        
        return self._create_empty_session()
    
    def _create_empty_session(self) -> Dict[str, Any]:
        """Create empty session structure"""
        return {
            "session_id": self.current_session_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "total_interactions": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "conversation_history": [],
            "session_metadata": {},
            "current_context": {}
        }
    
    def add_interaction(self, user_query: str, agent_response: Dict[str, Any]) -> str:
        """Add a new interaction to memory and return interaction ID"""
        session_data = self._load_session_data()
        
        interaction_id = f"interaction_{len(session_data['conversation_history']) + 1}_{datetime.now().strftime('%H%M%S')}"
        

        success = agent_response.get('success', False)
        result_count = agent_response.get('result_count', 0)
        sql_query = agent_response.get('sql_generated') or agent_response.get('sql_query')
        

        interaction = {
            "interaction_id": interaction_id,
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query,
            "query_type": self._classify_query_type(user_query),
            "agent_response": {
                "success": success,
                "message": agent_response.get('message') or agent_response.get('answer', ''),
                "result_count": result_count,
                "sql_query": sql_query,
                "processing_time": agent_response.get('metadata', {}).get('processing_time_seconds'),
                "agent_type": agent_response.get('metadata', {}).get('agent_type', 'unknown')
            },
            "context": {
                "patient_mentioned": self._extract_patient_context(user_query),
                "medical_focus": self._extract_medical_focus(user_query)
            }
        }
        

        session_data['conversation_history'].append(interaction)
        

        session_data['total_interactions'] += 1
        if success:
            session_data['successful_queries'] += 1
            session_data['current_context']['last_successful_query'] = interaction
        else:
            session_data['failed_queries'] += 1
        

        if interaction['context']['patient_mentioned']:
            session_data['current_context']['last_patient_mentioned'] = interaction['context']['patient_mentioned']
        
        session_data['current_context']['last_query_type'] = interaction['query_type']
        

        self._save_session_data(session_data)
        

        self._save_individual_response(interaction_id, user_query, agent_response)
        
        logger.info(f"Interaction {interaction_id} added to memory")
        return interaction_id
    
    def _save_individual_response(self, interaction_id: str, user_query: str, agent_response: Dict[str, Any]):
        """Save individual response to separate JSON file"""
        try:
            response_file = self.responses_dir / f"{interaction_id}.json"
            response_data = {
                "interaction_id": interaction_id,
                "timestamp": datetime.now().isoformat(),
                "session_id": self.current_session_id,
                "user_query": user_query,
                "agent_response": agent_response,
                "metadata": {
                    "file_type": "individual_response",
                    "memory_version": "2.0"
                }
            }
            
            with open(response_file, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.debug(f"Individual response saved to {response_file}")
        except Exception as e:
            logger.error(f"Error saving individual response: {e}")
    
    def get_conversation_context(self, last_n_interactions: int = 3) -> str:
        """Get conversation context for the agent with enhanced error handling"""
        try:
            session_data = self._load_session_data()
            
            if not session_data or not session_data.get('conversation_history'):
                logger.info("No conversation history found, returning empty context")
                return ""
            
            conversation_history = session_data['conversation_history']
            if not conversation_history:
                logger.info("Conversation history is empty, returning empty context")
                return ""
            
            logger.info(f"Found {len(conversation_history)} interactions in session history")
            recent_interactions = conversation_history[-last_n_interactions:]
            

            context = f"Previous conversation context (Session: {self.current_session_id}):\n"
            

            current_context = session_data.get('current_context', {})
            if current_context.get('last_patient_mentioned'):
                context += f"- Last patient mentioned: {current_context['last_patient_mentioned']}\n"
            
            if current_context.get('last_successful_query'):
                last_query = current_context['last_successful_query']
                context += f"- Last successful query: {last_query['user_query']}\n"
                if last_query.get('agent_response', {}).get('result_count'):
                    context += f"- Last query found: {last_query['agent_response']['result_count']} records\n"
            
            context += f"\nRecent interactions ({len(recent_interactions)} of {len(conversation_history)}):\n"
            
            for i, interaction in enumerate(recent_interactions, 1):
                try:
                    context += f"{i}. User: {interaction.get('user_query', 'Unknown query')}\n"
                    
                    response = interaction.get('agent_response', {})
                    if response.get('success'):
                        if response.get('result_count'):
                            context += f"   AI: Found {response['result_count']} records. {response.get('message', '')[:100]}...\n"
                        else:
                            context += f"   AI: {response.get('message', 'Query successful')[:100]}...\n"
                    else:
                        context += f"   AI: Error - {response.get('message', 'Query failed')[:100]}...\n"
                    
                    if interaction.get('context', {}).get('patient_mentioned'):
                        context += f"   Patient context: {interaction['context']['patient_mentioned']}\n"
                    
                    context += "\n"
                except Exception as e:
                    logger.error(f"Error processing interaction {i}: {e}")
                    context += f"{i}. [Error processing interaction]\n\n"
            
            logger.info(f"Generated context with {len(context)} characters")
            return context
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return ""
    
    def _classify_query_type(self, user_query: str) -> str:
        """Classify the type of user query"""
        query_lower = user_query.lower()
        
        if any(word in query_lower for word in ['count', 'how many', 'total', 'number of']):
            return "count"
        elif any(word in query_lower for word in ['show', 'list', 'find', 'get', 'display']):
            return "list"
        elif any(word in query_lower for word in ['compare', 'difference', 'versus', 'vs']):
            return "comparison"
        elif any(word in query_lower for word in ['update', 'change', 'modify']):
            return "modification"
        elif any(word in query_lower for word in ['delete', 'remove']):
            return "deletion"
        else:
            return "general"
    
    def _extract_patient_context(self, user_query: str) -> Optional[str]:
        """Extract patient context from query"""
        import re
        

        patterns = [
            r'\b([A-Z][a-z]+)\s+(?:patient|records?|data|information)\b',
            r'\bpatient\s+([A-Z][a-z]+)\b',
            r'\b([A-Z][a-z]+)\'s?\s+(?:medical|health|records?)\b',
            r'\bshow\s+(?:me\s+)?([A-Z][a-z]+)(?:\s+[A-Z][a-z]+)?\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_query)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_medical_focus(self, user_query: str) -> Optional[str]:
        """Extract medical focus from query"""
        query_lower = user_query.lower()
        
        medical_categories = {
            'medication': ['medication', 'drug', 'prescription', 'medicine', 'pill'],
            'condition': ['condition', 'diagnosis', 'disease', 'illness', 'disorder'],
            'procedure': ['procedure', 'surgery', 'operation', 'treatment'],
            'visit': ['visit', 'encounter', 'appointment', 'consultation'],
            'test': ['test', 'lab', 'examination', 'screening', 'scan']
        }
        
        for category, keywords in medical_categories.items():
            if any(keyword in query_lower for keyword in keywords):
                return category
        
        return None
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        session_data = self._load_session_data()
        
        return {
            "session_id": self.current_session_id,
            "session_file": str(self.session_file),
            "created_at": session_data.get('created_at'),
            "last_updated": session_data.get('last_updated'),
            "total_interactions": session_data.get('total_interactions', 0),
            "successful_queries": session_data.get('successful_queries', 0),
            "failed_queries": session_data.get('failed_queries', 0),
            "success_rate": (session_data.get('successful_queries', 0) / max(session_data.get('total_interactions', 1), 1)) * 100,
            "current_context": session_data.get('current_context', {}),
            "memory_location": str(self.base_dir)
        }
    
    def search_memory(self, query_term: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search through conversation memory"""
        session_data = self._load_session_data()
        results = []
        
        query_term_lower = query_term.lower()
        
        for interaction in session_data['conversation_history']:

            if query_term_lower in interaction['user_query'].lower():
                results.append({
                    "type": "user_query",
                    "interaction_id": interaction['interaction_id'],
                    "timestamp": interaction['timestamp'],
                    "content": interaction['user_query'],
                    "context": interaction.get('context', {})
                })
            

            response_message = interaction['agent_response'].get('message', '')
            if query_term_lower in response_message.lower():
                results.append({
                    "type": "agent_response",
                    "interaction_id": interaction['interaction_id'],
                    "timestamp": interaction['timestamp'],
                    "content": response_message,
                    "success": interaction['agent_response'].get('success', False)
                })
        

        results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return results[:max_results]
    
    def get_last_successful_query(self) -> Optional[Dict[str, Any]]:
        """Get the last successful query"""
        session_data = self._load_session_data()
        
        for interaction in reversed(session_data['conversation_history']):
            if interaction['agent_response'].get('success'):
                return {
                    "user_query": interaction['user_query'],
                    "agent_response": interaction['agent_response'],
                    "timestamp": interaction['timestamp'],
                    "context": interaction.get('context', {})
                }
        
        return None
    
    def clear_session_memory(self):
        """Clear current session and start new one"""

        if self.session_file.exists():
            archive_name = f"archived_{self.current_session_id}.json"
            archive_path = self.sessions_dir / archive_name
            self.session_file.rename(archive_path)
            logger.info(f"Session archived to {archive_path}")
        

        self.current_session_id = self._generate_session_id()
        self.session_file = self.sessions_dir / f"{self.current_session_id}.json"
        self._initialize_session()
        
        logger.info(f"New session started: {self.current_session_id}")
    
    def save_daily_summary(self):
        """Save daily summary of all sessions"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            daily_file = self.daily_dir / f"daily_summary_{today}.json"
            

            today_sessions = []
            for session_file in self.sessions_dir.glob("session_*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    

                    created_at = session_data.get('created_at', '')
                    if created_at.startswith(today):
                        today_sessions.append({
                            "session_id": session_data['session_id'],
                            "created_at": session_data['created_at'],
                            "total_interactions": session_data['total_interactions'],
                            "successful_queries": session_data['successful_queries'],
                            "failed_queries": session_data['failed_queries']
                        })
                except Exception as e:
                    logger.warning(f"Error reading session file {session_file}: {e}")
            

            daily_summary = {
                "date": today,
                "total_sessions": len(today_sessions),
                "total_interactions": sum(s['total_interactions'] for s in today_sessions),
                "total_successful_queries": sum(s['successful_queries'] for s in today_sessions),
                "total_failed_queries": sum(s['failed_queries'] for s in today_sessions),
                "sessions": today_sessions,
                "created_at": datetime.now().isoformat()
            }
            
            with open(daily_file, 'w', encoding='utf-8') as f:
                json.dump(daily_summary, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Daily summary saved to {daily_file}")
            return str(daily_file)
            
        except Exception as e:
            logger.error(f"Error saving daily summary: {e}")
            return None
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        session_data = self._load_session_data()
        

        session_files = len(list(self.sessions_dir.glob("*.json")))
        response_files = len(list(self.responses_dir.glob("*.json")))
        daily_files = len(list(self.daily_dir.glob("*.json")))
        
        return {
            "current_session": {
                "session_id": self.current_session_id,
                "total_interactions": session_data.get('total_interactions', 0),
                "successful_queries": session_data.get('successful_queries', 0),
                "failed_queries": session_data.get('failed_queries', 0)
            },
            "file_counts": {
                "session_files": session_files,
                "response_files": response_files,
                "daily_files": daily_files
            },
            "storage_location": str(self.base_dir),
            "memory_version": "2.0"
        }
    
    def validate_memory_integrity(self) -> Dict[str, Any]:
        """Validate memory integrity and report issues"""
        issues = []
        stats = {
            "session_file_exists": self.session_file.exists(),
            "session_file_readable": False,
            "session_data_valid": False,
            "conversation_history_count": 0,
            "issues": issues
        }
        
        try:

            if self.session_file.exists():
                session_data = self._load_session_data()
                stats["session_file_readable"] = True
                

                if session_data and 'conversation_history' in session_data:
                    stats["session_data_valid"] = True
                    stats["conversation_history_count"] = len(session_data.get('conversation_history', []))
                else:
                    issues.append("Session data missing or invalid structure")
                    
            else:
                issues.append("Session file does not exist")
                
        except Exception as e:
            issues.append(f"Error validating memory: {e}")
            
        stats["is_healthy"] = len(issues) == 0
        logger.info(f"Memory validation: {stats}")
        
        return stats