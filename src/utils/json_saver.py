
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
import structlog

logger = structlog.get_logger(__name__)

class JSONResponseSaver:
    """Enhanced JSON response saver with organized storage"""
    
    def __init__(self, base_dir: str = "json_responses"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        

        self.responses_dir = self.base_dir / "responses"
        self.sessions_dir = self.base_dir / "sessions"
        self.daily_dir = self.base_dir / "daily"
        self.exports_dir = self.base_dir / "exports"
        
        for dir_path in [self.responses_dir, self.sessions_dir, self.daily_dir, self.exports_dir]:
            dir_path.mkdir(exist_ok=True)
        
        logger.info(f"JSON Response Saver initialized at {self.base_dir}")
    
    def save_response(self, response: Dict[str, Any], user_query: str, session_id: str) -> Optional[str]:
        """Save individual response to JSON file"""
        try:

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            filename = f"response_{timestamp}_{unique_id}.json"
            filepath = self.responses_dir / filename
            

            enhanced_response = {
                "metadata": {
                    "filename": filename,
                    "saved_at": datetime.now().isoformat(),
                    "session_id": session_id,
                    "user_query": user_query,
                    "response_type": "individual_query_response",
                    "saver_version": "2.0"
                },
                "query_info": {
                    "original_query": user_query,
                    "query_length": len(user_query),
                    "query_type": self._classify_query_type(user_query),
                    "timestamp": datetime.now().isoformat()
                },
                "response_data": response,
                "analysis": {
                    "success": response.get('success', False),
                    "has_data": bool(response.get('data') or response.get('results')),
                    "result_count": response.get('result_count', 0),
                    "has_sql": bool(response.get('sql_generated') or response.get('sql_query')),
                    "processing_time": response.get('metadata', {}).get('processing_time_seconds'),
                    "agent_type": response.get('metadata', {}).get('agent_type', 'unknown')
                }
            }
            

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(enhanced_response, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Response saved to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving response: {e}")
            return None
    
    def save_session_responses(self, session_responses: List[Dict[str, Any]], session_id: str) -> Optional[str]:
        """Save complete session responses to JSON file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"session_{session_id}_{timestamp}.json"
            filepath = self.sessions_dir / filename
            

            total_queries = len(session_responses)
            successful_queries = sum(1 for r in session_responses if r.get('response', {}).get('success', False))
            failed_queries = total_queries - successful_queries
            total_results = sum(r.get('response', {}).get('result_count', 0) for r in session_responses)
            

            session_summary = {
                "session_metadata": {
                    "session_id": session_id,
                    "filename": filename,
                    "saved_at": datetime.now().isoformat(),
                    "session_type": "complete_session_export",
                    "saver_version": "2.0"
                },
                "session_statistics": {
                    "total_queries": total_queries,
                    "successful_queries": successful_queries,
                    "failed_queries": failed_queries,
                    "success_rate": (successful_queries / max(total_queries, 1)) * 100,
                    "total_results_returned": total_results,
                    "session_duration": self._calculate_session_duration(session_responses)
                },
                "query_analysis": {
                    "query_types": self._analyze_query_types(session_responses),
                    "most_common_agent": self._find_most_common_agent(session_responses),
                    "average_processing_time": self._calculate_average_processing_time(session_responses)
                },
                "responses": session_responses
            }
            

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_summary, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Session responses saved to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving session responses: {e}")
            return None
    
    def save_daily_summary(self, date: str = None) -> Optional[str]:
        """Save daily summary of all responses"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            filename = f"daily_summary_{date}.json"
            filepath = self.daily_dir / filename
            

            daily_responses = []
            for response_file in self.responses_dir.glob("*.json"):
                try:
                    with open(response_file, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                    

                    saved_at = response_data.get('metadata', {}).get('saved_at', '')
                    if saved_at.startswith(date):
                        daily_responses.append(response_data)
                except Exception as e:
                    logger.warning(f"Error reading response file {response_file}: {e}")
            

            daily_summary = {
                "summary_metadata": {
                    "date": date,
                    "filename": filename,
                    "created_at": datetime.now().isoformat(),
                    "summary_type": "daily_responses_summary",
                    "saver_version": "2.0"
                },
                "daily_statistics": {
                    "total_responses": len(daily_responses),
                    "successful_queries": sum(1 for r in daily_responses if r.get('analysis', {}).get('success', False)),
                    "failed_queries": sum(1 for r in daily_responses if not r.get('analysis', {}).get('success', False)),
                    "total_results": sum(r.get('analysis', {}).get('result_count', 0) for r in daily_responses),
                    "unique_sessions": len(set(r.get('metadata', {}).get('session_id') for r in daily_responses if r.get('metadata', {}).get('session_id')))
                },
                "query_analysis": {
                    "query_types": self._analyze_daily_query_types(daily_responses),
                    "most_active_hour": self._find_most_active_hour(daily_responses),
                    "average_query_length": self._calculate_average_query_length(daily_responses)
                },
                "responses": daily_responses
            }
            

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(daily_summary, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Daily summary saved to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving daily summary: {e}")
            return None
    
    def export_session_data(self, session_id: str, export_format: str = "json") -> Optional[str]:
        """Export session data in specified format"""
        try:

            session_file = None
            for file in self.sessions_dir.glob(f"session_{session_id}_*.json"):
                session_file = file
                break
            
            if not session_file:
                logger.warning(f"Session file not found for session_id: {session_id}")
                return None
            

            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            

            if export_format.lower() == "json":
                return str(session_file)
            elif export_format.lower() == "csv":
                return self._export_to_csv(session_data, session_id)
            elif export_format.lower() == "txt":
                return self._export_to_txt(session_data, session_id)
            else:
                logger.error(f"Unsupported export format: {export_format}")
                return None
                
        except Exception as e:
            logger.error(f"Error exporting session data: {e}")
            return None
    
    def _export_to_csv(self, session_data: Dict[str, Any], session_id: str) -> Optional[str]:
        """Export session data to CSV format"""
        try:
            import csv
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"session_{session_id}_{timestamp}.csv"
            filepath = self.exports_dir / filename
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'user_query', 'success', 'result_count', 'sql_query', 'response_message']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for response in session_data.get('responses', []):
                    query_metadata = response.get('query_metadata', {})
                    response_data = response.get('response', {})
                    
                    writer.writerow({
                        'timestamp': query_metadata.get('timestamp', ''),
                        'user_query': query_metadata.get('original_query', ''),
                        'success': response_data.get('success', False),
                        'result_count': response_data.get('result_count', 0),
                        'sql_query': response_data.get('sql_generated', ''),
                        'response_message': response_data.get('message', '')
                    })
            
            logger.info(f"Session exported to CSV: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return None
    
    def _export_to_txt(self, session_data: Dict[str, Any], session_id: str) -> Optional[str]:
        """Export session data to readable text format"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"session_{session_id}_{timestamp}.txt"
            filepath = self.exports_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as txtfile:

                txtfile.write(f"SESSION REPORT: {session_id}\n")
                txtfile.write("=" * 80 + "\n\n")
                

                stats = session_data.get('session_statistics', {})
                txtfile.write("SESSION STATISTICS:\n")
                txtfile.write(f"Total Queries: {stats.get('total_queries', 0)}\n")
                txtfile.write(f"Successful Queries: {stats.get('successful_queries', 0)}\n")
                txtfile.write(f"Failed Queries: {stats.get('failed_queries', 0)}\n")
                txtfile.write(f"Success Rate: {stats.get('success_rate', 0):.1f}%\n")
                txtfile.write(f"Total Results: {stats.get('total_results_returned', 0)}\n\n")
                

                txtfile.write("CONVERSATION HISTORY:\n")
                txtfile.write("-" * 80 + "\n\n")
                
                for i, response in enumerate(session_data.get('responses', []), 1):
                    query_metadata = response.get('query_metadata', {})
                    response_data = response.get('response', {})
                    
                    txtfile.write(f"QUERY {i}:\n")
                    txtfile.write(f"Time: {query_metadata.get('timestamp', '')}\n")
                    txtfile.write(f"Question: {query_metadata.get('original_query', '')}\n")
                    txtfile.write(f"Success: {response_data.get('success', False)}\n")
                    txtfile.write(f"Answer: {response_data.get('message', '')}\n")
                    
                    if response_data.get('sql_generated'):
                        txtfile.write(f"SQL: {response_data.get('sql_generated')}\n")
                    
                    if response_data.get('result_count'):
                        txtfile.write(f"Results: {response_data.get('result_count')} records\n")
                    
                    txtfile.write("\n" + "-" * 40 + "\n\n")
            
            logger.info(f"Session exported to TXT: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error exporting to TXT: {e}")
            return None
    
    def _classify_query_type(self, query: str) -> str:
        """Classify query type for analysis"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['count', 'how many', 'total', 'number']):
            return "count"
        elif any(word in query_lower for word in ['show', 'list', 'find', 'get', 'display']):
            return "retrieval"
        elif any(word in query_lower for word in ['compare', 'difference', 'versus']):
            return "comparison"
        elif any(word in query_lower for word in ['update', 'change', 'modify']):
            return "modification"
        else:
            return "general"
    
    def _analyze_query_types(self, session_responses: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze query types in session"""
        query_types = {}
        
        for response in session_responses:
            query_metadata = response.get('query_metadata', {})
            original_query = query_metadata.get('original_query', '')
            query_type = self._classify_query_type(original_query)
            
            query_types[query_type] = query_types.get(query_type, 0) + 1
        
        return query_types
    
    def _analyze_daily_query_types(self, daily_responses: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze query types for daily summary"""
        query_types = {}
        
        for response in daily_responses:
            query_type = response.get('query_info', {}).get('query_type', 'unknown')
            query_types[query_type] = query_types.get(query_type, 0) + 1
        
        return query_types
    
    def _find_most_common_agent(self, session_responses: List[Dict[str, Any]]) -> str:
        """Find most commonly used agent type"""
        agent_counts = {}
        
        for response in session_responses:
            agent_type = response.get('response', {}).get('metadata', {}).get('agent_type', 'unknown')
            agent_counts[agent_type] = agent_counts.get(agent_type, 0) + 1
        
        if agent_counts:
            return max(agent_counts, key=agent_counts.get)
        return "unknown"
    
    def _calculate_average_processing_time(self, session_responses: List[Dict[str, Any]]) -> float:
        """Calculate average processing time"""
        processing_times = []
        
        for response in session_responses:
            processing_time = response.get('query_metadata', {}).get('processing_time_seconds')
            if processing_time and isinstance(processing_time, (int, float)):
                processing_times.append(processing_time)
        
        if processing_times:
            return sum(processing_times) / len(processing_times)
        return 0.0
    
    def _calculate_session_duration(self, session_responses: List[Dict[str, Any]]) -> str:
        """Calculate total session duration"""
        if not session_responses:
            return "0 minutes"
        
        try:
            first_timestamp = session_responses[0].get('query_metadata', {}).get('timestamp', '')
            last_timestamp = session_responses[-1].get('query_metadata', {}).get('timestamp', '')
            
            if first_timestamp and last_timestamp:
                from datetime import datetime
                first_time = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00'))
                last_time = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
                
                duration = last_time - first_time
                minutes = int(duration.total_seconds() / 60)
                return f"{minutes} minutes"
        except Exception:
            pass
        
        return "unknown"
    
    def _find_most_active_hour(self, daily_responses: List[Dict[str, Any]]) -> str:
        """Find most active hour of the day"""
        hour_counts = {}
        
        for response in daily_responses:
            saved_at = response.get('metadata', {}).get('saved_at', '')
            if saved_at:
                try:
                    hour = datetime.fromisoformat(saved_at.replace('Z', '+00:00')).hour
                    hour_counts[hour] = hour_counts.get(hour, 0) + 1
                except Exception:
                    continue
        
        if hour_counts:
            most_active_hour = max(hour_counts, key=hour_counts.get)
            return f"{most_active_hour:02d}:00"
        return "unknown"
    
    def _calculate_average_query_length(self, daily_responses: List[Dict[str, Any]]) -> float:
        """Calculate average query length"""
        query_lengths = []
        
        for response in daily_responses:
            query_length = response.get('query_info', {}).get('query_length', 0)
            if query_length > 0:
                query_lengths.append(query_length)
        
        if query_lengths:
            return sum(query_lengths) / len(query_lengths)
        return 0.0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            response_files = list(self.responses_dir.glob("*.json"))
            session_files = list(self.sessions_dir.glob("*.json"))
            daily_files = list(self.daily_dir.glob("*.json"))
            export_files = list(self.exports_dir.glob("*"))
            

            total_size = 0
            for file_list in [response_files, session_files, daily_files, export_files]:
                for file in file_list:
                    try:
                        total_size += file.stat().st_size
                    except Exception:
                        pass
            
            return {
                "storage_location": str(self.base_dir),
                "file_counts": {
                    "response_files": len(response_files),
                    "session_files": len(session_files),
                    "daily_files": len(daily_files),
                    "export_files": len(export_files),
                    "total_files": len(response_files) + len(session_files) + len(daily_files) + len(export_files)
                },
                "storage_size": {
                    "total_bytes": total_size,
                    "total_mb": round(total_size / (1024 * 1024), 2)
                },
                "directories": {
                    "responses": str(self.responses_dir),
                    "sessions": str(self.sessions_dir),
                    "daily": str(self.daily_dir),
                    "exports": str(self.exports_dir)
                }
            }
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {"error": str(e)}
    
    def cleanup_old_files(self, days_to_keep: int = 30) -> Dict[str, int]:
        """Clean up old files beyond retention period"""
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cleanup_stats = {"deleted_files": 0, "kept_files": 0, "errors": 0}
            

            for file in self.responses_dir.glob("*.json"):
                try:
                    file_time = datetime.fromtimestamp(file.stat().st_mtime)
                    if file_time < cutoff_date:
                        file.unlink()
                        cleanup_stats["deleted_files"] += 1
                        logger.debug(f"Deleted old response file: {file}")
                    else:
                        cleanup_stats["kept_files"] += 1
                except Exception as e:
                    cleanup_stats["errors"] += 1
                    logger.warning(f"Error cleaning up file {file}: {e}")
            

            session_cutoff = datetime.now() - timedelta(days=days_to_keep * 2)
            for file in self.sessions_dir.glob("*.json"):
                try:
                    file_time = datetime.fromtimestamp(file.stat().st_mtime)
                    if file_time < session_cutoff:
                        file.unlink()
                        cleanup_stats["deleted_files"] += 1
                        logger.debug(f"Deleted old session file: {file}")
                    else:
                        cleanup_stats["kept_files"] += 1
                except Exception as e:
                    cleanup_stats["errors"] += 1
                    logger.warning(f"Error cleaning up file {file}: {e}")
            
            logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {"error": str(e)}
    
    def search_responses(self, search_term: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search through saved responses"""
        try:
            search_results = []
            search_term_lower = search_term.lower()
            
            for response_file in self.responses_dir.glob("*.json"):
                try:
                    with open(response_file, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                    

                    user_query = response_data.get('query_info', {}).get('original_query', '')
                    response_message = response_data.get('response_data', {}).get('message', '')
                    
                    if (search_term_lower in user_query.lower() or 
                        search_term_lower in response_message.lower()):
                        
                        search_results.append({
                            "file": str(response_file),
                            "timestamp": response_data.get('metadata', {}).get('saved_at', ''),
                            "user_query": user_query,
                            "response_message": response_message[:200] + "..." if len(response_message) > 200 else response_message,
                            "success": response_data.get('response_data', {}).get('success', False),
                            "session_id": response_data.get('metadata', {}).get('session_id', '')
                        })
                        
                        if len(search_results) >= max_results:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error reading response file {response_file}: {e}")
            

            search_results.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching responses: {e}")
            return []