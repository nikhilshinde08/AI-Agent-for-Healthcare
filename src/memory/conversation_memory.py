import json
import os
import uuid
from datetime import datetime
from pathlib import Path
import threading
import atexit
import re

class ConversationMemory:
    
    _current_session = None
    _lock = threading.Lock()
    _auto_save_registered = False
    
    def __init__(self, session_id=None, memory_file_path="conversation_memory.json", force_new_session=False):
        self.memory_file_path = memory_file_path
        self.sessions_folder = Path("sessions")
        self.sessions_folder.mkdir(exist_ok=True)
        
        # Try to load existing session first
        if session_id and not force_new_session:
            self.session_id = session_id
            existing_data = self._load_existing_session(session_id)
            if existing_data:
                with ConversationMemory._lock:
                    ConversationMemory._current_session = {
                        "session_id": self.session_id,
                        "data": existing_data
                    }
                print(f"Loaded existing session: {self.session_id}")
            else:
                with ConversationMemory._lock:
                    ConversationMemory._current_session = {
                        "session_id": self.session_id,
                        "data": self._create_empty_session()
                    }
                print(f"Created new session: {self.session_id}")
        else:
            # Create new session
            self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            with ConversationMemory._lock:
                ConversationMemory._current_session = {
                    "session_id": self.session_id,
                    "data": self._create_empty_session()
                }
            print(f"Created fresh session: {self.session_id}")
            
        # Register auto-save
        if not ConversationMemory._auto_save_registered:
            atexit.register(ConversationMemory._cleanup_on_exit)
            ConversationMemory._auto_save_registered = True
    
    def _create_empty_session(self):
        return {
            "conversation_history": [],
            "session_start": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "total_interactions": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "natural_language_responses": 0,
            "session_active": True,
            "session_closed": None,
            "current_context": {},
            "last_patient_query": None,
            "session_type": "fresh_ephemeral"
        }
    
    def _load_existing_session(self, session_id):
        """Load existing session from file if it exists"""
        file_path = self.sessions_folder / f"{session_id}.json"
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    return session_data.get("data", self._create_empty_session())
            except Exception as e:
                print(f"Error loading session {session_id}: {e}")
        return None
    
    def _load_memory(self):
        """Load memory from file for backward compatibility"""
        return self._load_existing_session(self.session_id)
    
    def save_session_to_file(self):
        """Save current session to file"""
        with ConversationMemory._lock:
            session_data = ConversationMemory._current_session
            if session_data:
                file_path = self.sessions_folder / f"{self.session_id}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, default=str)
                print(f"Session saved to {file_path}")
    
    def auto_save(self):
        """Auto-save session after each interaction"""
        self.save_session_to_file()
    
    @classmethod
    def _cleanup_on_exit(cls):
        with cls._lock:
            session_data = cls._current_session
            if session_data:
                instance = cls()
                instance.session_id = session_data["session_id"]
                instance.save_session_to_file()
                print(f"Cleaning up and saving session: {session_data['session_id']}")
                cls._current_session = None
    
    @property
    def memory_data(self):
        with ConversationMemory._lock:
            if ConversationMemory._current_session:
                return ConversationMemory._current_session["data"]
            else:
                return self._create_empty_session()
    
    def _update_memory_data(self, update_func):
        with ConversationMemory._lock:
            if ConversationMemory._current_session:
                update_func(ConversationMemory._current_session["data"])
            else:
                ConversationMemory._current_session = {
                    "session_id": self.session_id,
                    "data": self._create_empty_session()
                }
                update_func(ConversationMemory._current_session["data"])
    
    def add_interaction(self, user_query, agent_response):
        has_natural_language = self._has_natural_language_response(agent_response)
        
        patient_context = self._extract_patient_context(user_query)
        
        def update_session(session_data):
            interaction = {
                "timestamp": datetime.now().isoformat(),
                "user_query": user_query,
                "agent_response": {
                    "success": agent_response.get('success', False),
                    "answer": agent_response.get('answer', ''),
                    "message": agent_response.get('message', agent_response.get('answer', '')),
                    "result_count": agent_response.get('result_count', 0),
                    "data_sample": self._extract_data_sample(agent_response.get('data')),
                    "has_natural_language": has_natural_language,
                    "sql_generated": agent_response.get('sql_generated'),
                },
                "interaction_id": len(session_data["conversation_history"]) + 1,
                "query_type": self._classify_query_type(user_query),
                "patient_context": patient_context
            }
            
            session_data["conversation_history"].append(interaction)
            
            if patient_context:
                session_data["current_context"].update(patient_context)
                session_data["last_patient_query"] = user_query
            
            session_data["last_updated"] = datetime.now().isoformat()
            session_data["total_interactions"] += 1
            
            if agent_response.get('success'):
                session_data["successful_queries"] += 1
            else:
                session_data["failed_queries"] += 1
                
            if has_natural_language:
                session_data["natural_language_responses"] += 1
            
            print(f"Added interaction {interaction['interaction_id']} to session")
        
        self._update_memory_data(update_session)
        # Auto-save after each interaction
        self.auto_save()
    
    def _extract_patient_context(self, user_query):
        context = {}
        query_lower = user_query.lower()
        
        name_patterns = [
            r'\b([A-Z][a-z]+)\s+(?:patient|records?|data|information)\b',
            r'\bpatient\s+([A-Z][a-z]+)\b',
            r'\b([A-Z][a-z]+)\'s?\s+(?:medical|health|records?)\b',
            r'\bshow\s+(?:me\s+)?([A-Z][a-z]+)(?:\s+[A-Z][a-z]+)?\b',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, user_query)
            if match:
                context["mentioned_patient"] = match.group(1)
                break
        
        if any(word in query_lower for word in ['medication', 'drug', 'prescription']):
            context["query_focus"] = "medication"
        elif any(word in query_lower for word in ['condition', 'diagnosis', 'disease']):
            context["query_focus"] = "condition"
        
        return context
    
    def get_conversation_context(self, last_n_interactions=3):
        memory_data = self.memory_data
        
        if not memory_data["conversation_history"]:
            return ""
        
        recent_interactions = memory_data["conversation_history"][-last_n_interactions:]
        
        context = "## Current Session Context:\n"
        context += f"Session ID: {self.session_id}\n"
        context += f"Total interactions: {memory_data['total_interactions']}\n"
        
        current_context = memory_data.get("current_context", {})
        if current_context.get("mentioned_patient"):
            context += f"**Current Patient Focus:** {current_context['mentioned_patient']}\n"
        
        context += "\n### Recent Interactions:\n"
        
        for interaction in recent_interactions:
            context += f"**Q{interaction['interaction_id']}:** {interaction['user_query']}\n"
            
            response = interaction['agent_response']
            if response.get('success'):
                context += f"**A{interaction['interaction_id']}:** {response.get('message', response.get('answer', 'No answer'))}\n"
                
                if interaction.get('patient_context', {}).get('mentioned_patient'):
                    context += f"**Patient Mentioned:** {interaction['patient_context']['mentioned_patient']}\n"
            else:
                context += f"**Error:** {response.get('message', 'Unknown error')}\n"
            
            context += "\n"
        
        return context
    
    def reset_session(self):
        self.__init__(force_new_session=True)
        print(f"Reset to fresh session: {self.session_id}")
    
    def _has_natural_language_response(self, agent_response):
        answer = agent_response.get('answer', '') or agent_response.get('message', '')
        
        if not answer or len(answer.strip()) < 10:
            return False
            
        natural_indicators = [
            "there are", "found", "shows", "indicates", "based on", 
            "according to", "the data shows", "results show"
        ]
        
        answer_lower = answer.lower()
        has_natural_words = any(indicator in answer_lower for indicator in natural_indicators)
        
        return has_natural_words
    
    def _classify_query_type(self, user_query):
        query_lower = user_query.lower()
        
        if any(word in query_lower for word in ['count', 'how many', 'total']):
            return "count"
        elif any(word in query_lower for word in ['show', 'list', 'find', 'get']):
            return "list"
        elif any(word in query_lower for word in ['compare', 'difference']):
            return "comparison"
        else:
            return "general"
    
    def _extract_data_sample(self, data, max_records=3):
        if not data:
            return []
        if isinstance(data, list):
            return data[:max_records]
        elif isinstance(data, dict):
            return [data]
        else:
            return [{"value": str(data)}]
    
    def get_last_successful_query(self):
        """Get the last successful query from conversation history"""
        memory_data = self.memory_data
        history = memory_data.get("conversation_history", [])
        
        # Find the last successful interaction
        for interaction in reversed(history):
            if interaction.get("agent_response", {}).get("success", False):
                return interaction
        return None
    
    def get_memory_summary(self):
        """Get a summary of current memory state"""
        memory_data = self.memory_data
        return {
            "session_id": self.session_id,
            "total_interactions": memory_data.get("total_interactions", 0),
            "successful_queries": memory_data.get("successful_queries", 0),
            "failed_queries": memory_data.get("failed_queries", 0),
            "last_updated": memory_data.get("last_updated"),
            "current_context": memory_data.get("current_context", {}),
            "session_active": memory_data.get("session_active", True)
        }
    
    def search_memory(self, query_term, max_results=3):
        """Search through conversation history for relevant interactions"""
        memory_data = self.memory_data
        history = memory_data.get("conversation_history", [])
        
        results = []
        query_lower = query_term.lower()
        
        for interaction in reversed(history):
            user_query = interaction.get("user_query", "").lower()
            agent_response = interaction.get("agent_response", {}).get("answer", "").lower()
            
            if (query_lower in user_query or query_lower in agent_response) and len(results) < max_results:
                results.append(interaction)
        
        return results
    
    def clear_session_memory(self):
        """Clear current session memory"""
        with ConversationMemory._lock:
            ConversationMemory._current_session = {
                "session_id": self.session_id,
                "data": self._create_empty_session()
            }
        print(f"Cleared memory for session: {self.session_id}")
    
    def get_session_status(self):
        memory_data = self.memory_data
        return {
            "session_id": self.session_id,
            "session_type": "persistent",
            "session_active": memory_data.get("session_active", True),
            "total_interactions": memory_data["total_interactions"],
            "last_updated": memory_data["last_updated"],
            "session_start": memory_data["session_start"],
            "current_patient": memory_data.get("current_context", {}).get("mentioned_patient"),
            "memory_location": "persistent_file_storage"
        }

# Create an alias for backward compatibility
ConversationMemoryManager = ConversationMemory

if __name__ == "__main__":
    memory = ConversationMemory()
    
    memory.add_interaction(
        "Show me John's medical records",
        {
            "success": True,
            "answer": "Found 3 records for patient John.",
            "result_count": 3,
            "data": [
                {"date": "2024-06-01", "type": "visit", "notes": "Regular checkup"},
                {"date": "2024-04-15", "type": "test", "notes": "Blood work"},
                {"date": "2024-02-10", "type": "prescription", "notes": "Antibiotic"}
            ]
        }
    )
    
    context = memory.get_conversation_context()
    print(context)
    
    memory.save_session_to_file()
    
    status = memory.get_session_status()
    print(f"Session status: {status}")