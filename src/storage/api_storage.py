
"""
API Storage Module for Healthcare Database Assistant
Handles persistent storage of API requests, responses, sessions, and analytics
"""

import json
import os
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import uuid
from contextlib import asynccontextmanager
import hashlib
import time

# Try to import structlog, fallback to standard logging
try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class APIStorageManager:
    """Comprehensive API storage manager with database and file-based storage"""
    
    def __init__(self, base_dir: str = "api_storage", db_file: str = "api_data.sqlite"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        

        self.requests_dir = self.base_dir / "requests"
        self.responses_dir = self.base_dir / "responses"
        self.sessions_dir = self.base_dir / "sessions"
        self.analytics_dir = self.base_dir / "analytics"
        self.cache_dir = self.base_dir / "cache"
        
        for dir_path in [self.requests_dir, self.responses_dir, self.sessions_dir, 
                        self.analytics_dir, self.cache_dir]:
            dir_path.mkdir(exist_ok=True)
        

        self.db_file = self.base_dir / db_file
        self._init_database()
        
        logger.info(f"API Storage Manager initialized at {self.base_dir}")
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT UNIQUE NOT NULL,
                    session_id TEXT,
                    timestamp TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    user_query TEXT,
                    request_size INTEGER,
                    ip_address TEXT,
                    user_agent TEXT,
                    headers TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    response_id TEXT UNIQUE NOT NULL,
                    request_id TEXT NOT NULL,
                    session_id TEXT,
                    timestamp TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    success BOOLEAN NOT NULL,
                    response_size INTEGER,
                    processing_time REAL,
                    sql_generated TEXT,
                    result_count INTEGER,
                    agent_type TEXT,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES api_requests (request_id)
                )
            ''')
            

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    total_requests INTEGER DEFAULT 0,
                    successful_requests INTEGER DEFAULT 0,
                    failed_requests INTEGER DEFAULT 0,
                    total_response_time REAL DEFAULT 0,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    ended_at TEXT
                )
            ''')
            

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    total_requests INTEGER DEFAULT 0,
                    successful_requests INTEGER DEFAULT 0,
                    failed_requests INTEGER DEFAULT 0,
                    unique_sessions INTEGER DEFAULT 0,
                    avg_response_time REAL DEFAULT 0,
                    total_data_transferred INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, hour)
                )
            ''')
            

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    request_count INTEGER DEFAULT 1,
                    window_start TEXT NOT NULL,
                    window_end TEXT NOT NULL,
                    is_blocked BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON api_requests(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_requests_session ON api_requests(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_responses_timestamp ON api_responses(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_responses_request ON api_responses(request_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_activity ON api_sessions(last_activity)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analytics_date ON api_analytics(date, hour)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rate_limits_ip ON api_rate_limits(ip_address, endpoint)')
            
            conn.commit()
            conn.close()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    async def log_api_request(self, request_data: Dict[str, Any]) -> str:
        """Log API request to database and file storage"""
        request_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        try:

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO api_requests 
                (request_id, session_id, timestamp, endpoint, method, user_query, 
                 request_size, ip_address, user_agent, headers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                request_id,
                request_data.get('session_id'),
                timestamp,
                request_data.get('endpoint', ''),
                request_data.get('method', 'POST'),
                request_data.get('user_query', ''),
                len(str(request_data).encode('utf-8')),
                request_data.get('ip_address', ''),
                request_data.get('user_agent', ''),
                json.dumps(request_data.get('headers', {}))
            ))
            
            conn.commit()
            conn.close()
            

            request_file = self.requests_dir / f"request_{request_id}.json"
            request_record = {
                "request_id": request_id,
                "timestamp": timestamp,
                "request_data": request_data,
                "metadata": {
                    "storage_version": "1.0",
                    "created_at": timestamp
                }
            }
            
            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(request_record, f, indent=2, ensure_ascii=False, default=str)
            
            logger.debug(f"API request logged: {request_id}")
            return request_id
            
        except Exception as e:
            logger.error(f"Error logging API request: {e}")
            return request_id
    
    async def log_api_response(self, request_id: str, response_data: Dict[str, Any], 
                               processing_time: float) -> str:
        """Log API response to database and file storage"""
        response_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        try:

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO api_responses 
                (response_id, request_id, session_id, timestamp, status_code, success,
                 response_size, processing_time, sql_generated, result_count, 
                 agent_type, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                response_id,
                request_id,
                response_data.get('session_id'),
                timestamp,
                200 if response_data.get('success', False) else 500,
                response_data.get('success', False),
                len(str(response_data).encode('utf-8')),
                processing_time,
                response_data.get('sql_generated'),
                response_data.get('result_count', 0),
                response_data.get('metadata', {}).get('agent_type', ''),
                response_data.get('metadata', {}).get('error', '') if not response_data.get('success') else None
            ))
            
            conn.commit()
            conn.close()
            

            response_file = self.responses_dir / f"response_{response_id}.json"
            response_record = {
                "response_id": response_id,
                "request_id": request_id,
                "timestamp": timestamp,
                "processing_time": processing_time,
                "response_data": response_data,
                "metadata": {
                    "storage_version": "1.0",
                    "created_at": timestamp
                }
            }
            
            with open(response_file, 'w', encoding='utf-8') as f:
                json.dump(response_record, f, indent=2, ensure_ascii=False, default=str)
            
            logger.debug(f"API response logged: {response_id}")
            return response_id
            
        except Exception as e:
            logger.error(f"Error logging API response: {e}")
            return response_id
    
    async def create_or_update_session(self, session_id: str, request_data: Dict[str, Any]) -> bool:
        """Create or update API session"""
        try:
            timestamp = datetime.now().isoformat()
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            

            cursor.execute('SELECT id FROM api_sessions WHERE session_id = ?', (session_id,))
            exists = cursor.fetchone()
            
            if exists:

                cursor.execute('''
                    UPDATE api_sessions 
                    SET last_activity = ?, total_requests = total_requests + 1
                    WHERE session_id = ?
                ''', (timestamp, session_id))
            else:

                cursor.execute('''
                    INSERT INTO api_sessions 
                    (session_id, created_at, last_activity, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    timestamp,
                    timestamp,
                    request_data.get('ip_address', ''),
                    request_data.get('user_agent', '')
                ))
                

                session_file = self.sessions_dir / f"session_{session_id}.json"
                session_record = {
                    "session_id": session_id,
                    "created_at": timestamp,
                    "requests": [],
                    "metadata": {
                        "storage_version": "1.0",
                        "ip_address": request_data.get('ip_address', ''),
                        "user_agent": request_data.get('user_agent', '')
                    }
                }
                
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_record, f, indent=2, ensure_ascii=False, default=str)
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating/updating session: {e}")
            return False
    
    async def update_session_result(self, session_id: str, success: bool, processing_time: float):
        """Update session with request result"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            if success:
                cursor.execute('''
                    UPDATE api_sessions 
                    SET successful_requests = successful_requests + 1,
                        total_response_time = total_response_time + ?
                    WHERE session_id = ?
                ''', (processing_time, session_id))
            else:
                cursor.execute('''
                    UPDATE api_sessions 
                    SET failed_requests = failed_requests + 1,
                        total_response_time = total_response_time + ?
                    WHERE session_id = ?
                ''', (processing_time, session_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating session result: {e}")
    
    async def end_session(self, session_id: str) -> bool:
        """End an API session"""
        try:
            timestamp = datetime.now().isoformat()
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE api_sessions 
                SET is_active = FALSE, ended_at = ?
                WHERE session_id = ? AND is_active = TRUE
            ''', (timestamp, session_id))
            
            conn.commit()
            conn.close()
            

            session_file = self.sessions_dir / f"session_{session_id}.json"
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                session_data["ended_at"] = timestamp
                session_data["is_active"] = False
                
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Session ended: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return False
    
    async def update_analytics(self, timestamp: str = None):
        """Update hourly analytics"""
        try:
            if timestamp is None:
                timestamp = datetime.now().isoformat()
            
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d')
            hour = dt.hour
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            

            cursor.execute('''
                SELECT COUNT(*) as total_requests,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_requests,
                       SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_requests,
                       AVG(processing_time) as avg_response_time,
                       SUM(response_size) as total_data_transferred
                FROM api_responses 
                WHERE date(timestamp) = ? AND strftime('%H', timestamp) = ?
            ''', (date_str, f"{hour:02d}"))
            
            stats = cursor.fetchone()
            

            cursor.execute('''
                SELECT COUNT(DISTINCT session_id) as unique_sessions
                FROM api_requests 
                WHERE date(timestamp) = ? AND strftime('%H', timestamp) = ?
            ''', (date_str, f"{hour:02d}"))
            
            unique_sessions = cursor.fetchone()[0]
            

            cursor.execute('''
                INSERT OR REPLACE INTO api_analytics 
                (date, hour, total_requests, successful_requests, failed_requests,
                 unique_sessions, avg_response_time, total_data_transferred)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date_str,
                hour,
                stats[0] or 0,
                stats[1] or 0,
                stats[2] or 0,
                unique_sessions or 0,
                stats[3] or 0.0,
                stats[4] or 0
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating analytics: {e}")
    
    async def check_rate_limit(self, ip_address: str, endpoint: str, 
                              requests_per_minute: int = 60) -> Tuple[bool, Dict[str, Any]]:
        """Check if IP address has exceeded rate limit"""
        try:
            now = datetime.now()
            window_start = now - timedelta(minutes=1)
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            

            cursor.execute('''
                DELETE FROM api_rate_limits 
                WHERE window_end < ?
            ''', (window_start.isoformat(),))
            

            cursor.execute('''
                SELECT SUM(request_count) as total_requests
                FROM api_rate_limits 
                WHERE ip_address = ? AND endpoint = ? AND window_start >= ?
            ''', (ip_address, endpoint, window_start.isoformat()))
            
            result = cursor.fetchone()
            current_requests = result[0] if result[0] else 0
            

            is_allowed = current_requests < requests_per_minute
            
            if is_allowed:

                cursor.execute('''
                    INSERT OR REPLACE INTO api_rate_limits 
                    (ip_address, endpoint, request_count, window_start, window_end)
                    VALUES (?, ?, 
                           COALESCE((SELECT request_count FROM api_rate_limits 
                                   WHERE ip_address = ? AND endpoint = ? AND window_start >= ?), 0) + 1,
                           ?, ?)
                ''', (
                    ip_address, endpoint,
                    ip_address, endpoint, window_start.isoformat(),
                    now.isoformat(), (now + timedelta(minutes=1)).isoformat()
                ))
            else:

                cursor.execute('''
                    UPDATE api_rate_limits 
                    SET is_blocked = TRUE 
                    WHERE ip_address = ? AND endpoint = ?
                ''', (ip_address, endpoint))
            
            conn.commit()
            conn.close()
            
            return is_allowed, {
                "current_requests": current_requests + (1 if is_allowed else 0),
                "limit": requests_per_minute,
                "reset_time": (now + timedelta(minutes=1)).isoformat(),
                "blocked": not is_allowed
            }
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True, {}  # Allow request on error
    
    async def cache_response(self, cache_key: str, response_data: Dict[str, Any], 
                            ttl_minutes: int = 30) -> bool:
        """Cache API response"""
        try:
            cache_file = self.cache_dir / f"cache_{hashlib.md5(cache_key.encode()).hexdigest()}.json"
            expires_at = datetime.now() + timedelta(minutes=ttl_minutes)
            
            cache_record = {
                "cache_key": cache_key,
                "response_data": response_data,
                "created_at": datetime.now().isoformat(),
                "expires_at": expires_at.isoformat(),
                "ttl_minutes": ttl_minutes
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_record, f, indent=2, ensure_ascii=False, default=str)
            
            logger.debug(f"Response cached with key: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
            return False
    
    async def get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached API response"""
        try:
            cache_file = self.cache_dir / f"cache_{hashlib.md5(cache_key.encode()).hexdigest()}.json"
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_record = json.load(f)
            

            expires_at = datetime.fromisoformat(cache_record['expires_at'])
            if datetime.now() > expires_at:

                cache_file.unlink()
                return None
            
            logger.debug(f"Cache hit for key: {cache_key}")
            return cache_record['response_data']
            
        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
            return None
    
    async def get_api_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get API analytics for the specified number of days"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            

            cursor.execute('''
                SELECT date,
                       SUM(total_requests) as daily_requests,
                       SUM(successful_requests) as daily_successful,
                       SUM(failed_requests) as daily_failed,
                       SUM(unique_sessions) as daily_sessions,
                       AVG(avg_response_time) as daily_avg_response_time
                FROM api_analytics 
                WHERE date >= ? AND date <= ?
                GROUP BY date
                ORDER BY date
            ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            daily_stats = cursor.fetchall()
            

            cursor.execute('''
                SELECT hour, total_requests, successful_requests, failed_requests
                FROM api_analytics 
                WHERE date = ?
                ORDER BY hour
            ''', (end_date.strftime('%Y-%m-%d'),))
            
            hourly_stats = cursor.fetchall()
            

            cursor.execute('''
                SELECT endpoint, COUNT(*) as request_count
                FROM api_requests 
                WHERE timestamp >= ?
                GROUP BY endpoint
                ORDER BY request_count DESC
                LIMIT 10
            ''', (start_date.isoformat(),))
            
            top_endpoints = cursor.fetchall()
            

            cursor.execute('''
                SELECT COUNT(*) as total_sessions,
                       COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_sessions,
                       AVG(total_requests) as avg_requests_per_session,
                       AVG(total_response_time / NULLIF(total_requests, 0)) as avg_session_response_time
                FROM api_sessions 
                WHERE created_at >= ?
            ''', (start_date.isoformat(),))
            
            session_stats = cursor.fetchone()
            
            conn.close()
            
            return {
                "period": {
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d'),
                    "days": days
                },
                "daily_stats": [
                    {
                        "date": row[0],
                        "total_requests": row[1],
                        "successful_requests": row[2],
                        "failed_requests": row[3],
                        "unique_sessions": row[4],
                        "avg_response_time": row[5]
                    } for row in daily_stats
                ],
                "hourly_stats": [
                    {
                        "hour": row[0],
                        "total_requests": row[1],
                        "successful_requests": row[2],
                        "failed_requests": row[3]
                    } for row in hourly_stats
                ],
                "top_endpoints": [
                    {"endpoint": row[0], "request_count": row[1]} 
                    for row in top_endpoints
                ],
                "session_stats": {
                    "total_sessions": session_stats[0],
                    "active_sessions": session_stats[1],
                    "avg_requests_per_session": session_stats[2],
                    "avg_session_response_time": session_stats[3]
                } if session_stats else {},
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting API analytics: {e}")
            return {"error": str(e)}
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, int]:
        """Clean up old API data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cleanup_stats = {"deleted_records": 0, "deleted_files": 0, "errors": 0}
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            

            cursor.execute('DELETE FROM api_responses WHERE timestamp < ?', (cutoff_date.isoformat(),))
            cleanup_stats["deleted_records"] += cursor.rowcount
            
            cursor.execute('DELETE FROM api_requests WHERE timestamp < ?', (cutoff_date.isoformat(),))
            cleanup_stats["deleted_records"] += cursor.rowcount
            

            cursor.execute('DELETE FROM api_sessions WHERE created_at < ? AND is_active = FALSE', 
                          (cutoff_date.isoformat(),))
            cleanup_stats["deleted_records"] += cursor.rowcount
            

            cursor.execute('DELETE FROM api_rate_limits WHERE window_end < ?', (cutoff_date.isoformat(),))
            cleanup_stats["deleted_records"] += cursor.rowcount
            
            conn.commit()
            conn.close()
            

            for directory in [self.requests_dir, self.responses_dir, self.cache_dir]:
                for file in directory.glob("*.json"):
                    try:
                        file_time = datetime.fromtimestamp(file.stat().st_mtime)
                        if file_time < cutoff_date:
                            file.unlink()
                            cleanup_stats["deleted_files"] += 1
                    except Exception as e:
                        cleanup_stats["errors"] += 1
                        logger.warning(f"Error cleaning up file {file}: {e}")
            
            logger.info(f"API data cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error during API data cleanup: {e}")
            return {"error": str(e)}
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            

            cursor.execute('SELECT COUNT(*) FROM api_requests')
            total_requests = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM api_responses')
            total_responses = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM api_sessions')
            total_sessions = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM api_sessions WHERE is_active = 1')
            active_sessions = cursor.fetchone()[0]
            
            conn.close()
            

            file_stats = {}
            total_size = 0
            
            for name, directory in [
                ("requests", self.requests_dir),
                ("responses", self.responses_dir),
                ("sessions", self.sessions_dir),
                ("cache", self.cache_dir)
            ]:
                files = list(directory.glob("*.json"))
                size = sum(f.stat().st_size for f in files if f.exists())
                file_stats[name] = {
                    "file_count": len(files),
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 2)
                }
                total_size += size
            

            db_size = self.db_file.stat().st_size if self.db_file.exists() else 0
            total_size += db_size
            
            return {
                "database_stats": {
                    "total_requests": total_requests,
                    "total_responses": total_responses,
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "db_size_bytes": db_size,
                    "db_size_mb": round(db_size / (1024 * 1024), 2)
                },
                "file_stats": file_stats,
                "total_storage": {
                    "size_bytes": total_size,
                    "size_mb": round(total_size / (1024 * 1024), 2),
                    "size_gb": round(total_size / (1024 * 1024 * 1024), 3)
                },
                "directories": {
                    "base": str(self.base_dir),
                    "database": str(self.db_file),
                    "requests": str(self.requests_dir),
                    "responses": str(self.responses_dir),
                    "sessions": str(self.sessions_dir),
                    "analytics": str(self.analytics_dir),
                    "cache": str(self.cache_dir)
                },
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {"error": str(e)}