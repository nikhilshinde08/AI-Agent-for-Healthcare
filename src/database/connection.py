# src/database/connection.py - Optimized for ReAct agent
import os
import asyncio
import json
from typing import Dict, Any, Optional, Tuple, List

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlalchemy.engine import URL
import structlog
from dotenv import load_dotenv


load_dotenv()

_required_env_vars = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
_missing = [var for var in _required_env_vars if not os.getenv(var)]
if _missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(_missing)}"
    )

logger = structlog.get_logger(__name__)

class DatabaseConnection:
    """Enhanced PostgreSQL connection optimized for ReAct agent with schema management"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        self.schema_cache: Dict[str, Any] = {}
        self._setup_connection()
    
    def _setup_connection(self):
        """Initialize database connection from .env - works with ANY database"""
   
        db_url = URL.create(
            drivername="postgresql+asyncpg",
            username=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            database=os.getenv("DB_NAME"),
        )
        
        logger.info(
            f"Connecting to database: "
            f"{db_url.host}:{db_url.port}/{db_url.database}"
        )
        
        self.engine = create_async_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False  
        )
        
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test database connection"""
        try:
            async with self.async_session() as session:
                result = await session.execute(text("SELECT 1 as test"))
                test_result = result.fetchone()
                
                if test_result and test_result.test == 1:
                    logger.info("✅ Database connection successful")
                    return True, None
                else:
                    return False, "Connection test failed - unexpected result"
                    
        except Exception as e:
            error_msg = f"Database connection failed: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    async def extract_complete_schema(self) -> Dict[str, Any]:
        """Extract complete database schema optimized for ReAct agent"""
        try:
            logger.info("🔍 Extracting schema for ReAct agent...")
            
            async with self.async_session() as session:
                schema: Dict[str, Any] = {
                    "tables": {},
                    "relationships": []
                }
                
             
                table_query = """
                SELECT 
                    t.table_schema,
                    t.table_name,
                    c.column_name,
                    c.data_type,
                    c.character_maximum_length,
                    c.numeric_precision,
                    c.numeric_scale,
                    c.is_nullable,
                    c.column_default,
                    c.ordinal_position
                FROM information_schema.tables t
                JOIN information_schema.columns c 
                  ON t.table_name = c.table_name 
                  AND t.table_schema = c.table_schema
                WHERE t.table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                  AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_schema, t.table_name, c.ordinal_position
                """
                
                result = await session.execute(text(table_query))
                rows = result.fetchall()
                
                if not rows:
                    logger.warning("⚠️  No tables found in database")
                    return schema
                
              
                for row in rows:
                    key = f"{row.table_schema}.{row.table_name}"
                    if key not in schema["tables"]:
                        schema["tables"][key] = {
                            "schema": row.table_schema,
                            "name": row.table_name,
                            "columns": []
                        }
                    col_info = {
                        "name": row.column_name,
                        "type": row.data_type,
                        "nullable": row.is_nullable == "YES",
                        "default": row.column_default,
                        "position": row.ordinal_position
                    }
                    if row.character_maximum_length is not None:
                        col_info["max_length"] = row.character_maximum_length
                    if row.numeric_precision is not None:
                        col_info["precision"] = row.numeric_precision
                    if row.numeric_scale is not None:
                        col_info["scale"] = row.numeric_scale
                    schema["tables"][key]["columns"].append(col_info)
                
                
                try:
                    fk_query = """
                    SELECT
                        tc.table_schema,
                        tc.table_name,
                        kcu.column_name,
                        ccu.table_schema AS foreign_table_schema,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name,
                        tc.constraint_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                      AND tc.table_schema NOT IN ('information_schema', 'pg_catalog')
                    """
                    fk_result = await session.execute(text(fk_query))
                    fk_rows = fk_result.fetchall()
                    for row in fk_rows:
                        schema["relationships"].append({
                            "from_table": f"{row.table_schema}.{row.table_name}",
                            "from_column": row.column_name,
                            "to_table": f"{row.foreign_table_schema}.{row.foreign_table_name}",
                            "to_column": row.foreign_column_name,
                            "constraint_name": row.constraint_name
                        })
                except Exception as fk_error:
                    logger.warning(f"Could not extract foreign keys: {fk_error}")
                
                # Cache for ReAct agent
                self.schema_cache = schema
                logger.info(
                    f"✅ Schema extracted for ReAct agent: "
                    f"{len(schema['tables'])} tables, {len(schema['relationships'])} relationships"
                )
                return schema
                
        except Exception as e:
            logger.error(f"Schema extraction failed: {e}")
            raise
    
    async def execute_query(self, sql_query: str) -> Tuple[bool, Any, Optional[str], int]:
        """Execute SQL query optimized for ReAct agent responses"""
        try:
            logger.info(f"🔧 Executing ReAct agent query: {sql_query}")
            async with self.async_session() as session:
                await session.execute(text("SET statement_timeout = '30s'"))
                result = await session.execute(text(sql_query))
                rows = result.fetchall()
                cols = result.keys()
                
                # Convert to dict format for JSON serialization
                data = [dict(zip(cols, row)) for row in rows] if rows else []
                
                # Limit results for ReAct agent
                if len(data) > 1000:
                    data = data[:1000]
                    logger.warning("⚠️ Result truncated to 1000 rows for ReAct agent")
                
                logger.info(f"✅ ReAct agent query executed, {len(data)} rows returned")
                return True, data, None, 200
                
        except Exception as e:
            error = str(e)
            status = self._map_db_error_to_status(e)
            logger.error(f"❌ ReAct agent query failed ({status}): {error}")
            return False, None, error, status
    
    def _map_db_error_to_status(self, exception: Exception) -> int:
        """Map database errors to HTTP-like status codes for ReAct agent"""
        err = str(exception).lower()
        if any(k in err for k in ("syntax error", "invalid syntax")):
            return 400
        if any(k in err for k in ("does not exist", "relation", "column", "table")):
            return 404
        if any(k in err for k in ("permission denied", "access denied")):
            return 403
        if any(k in err for k in ("connection", "server closed", "timeout")):
            return 503
        if "timeout" in err:
            return 408
        return 500
    
    async def get_table_sample(self, table_name: str, limit: int = 5) -> Optional[List[Dict]]:
        """Get a sample of data from a table for ReAct agent context"""
        clean_name = table_name.split(".")[-1]
        success, data, error, _ = await self.execute_query(
            f"SELECT * FROM {clean_name} LIMIT {limit}"
        )
        if success:
            return data
        logger.warning(f"Could not get sample from {table_name}: {error}")
        return None
    
    async def close(self):
        """Clean up connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("🔌 Database connections closed")