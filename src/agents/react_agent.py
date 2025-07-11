"""Healthcare database ReAct agent with Tavily search integration."""

import json
import re
import logging
from typing import Dict, Any, List, Optional
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from langgraph.prebuilt import create_react_agent
from pydantic import Field
from dotenv import load_dotenv
import os
import asyncio
import aiohttp
import ssl
import weakref
from contextlib import asynccontextmanager

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

try:
    from src.models.response_models import DatabaseResponse, QueryResult
    from src.database.connection import DatabaseConnection
except ImportError:
    print("Warning: Could not import response models or database connection")
    DatabaseResponse = None
    QueryResult = None
    DatabaseConnection = None

load_dotenv()

def _validate_azure_env_vars():
    """Validate required Azure OpenAI environment variables."""
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY", 
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "AZURE_OPENAI_MODEL_NAME"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(
            f"Missing required Azure OpenAI environment variables: {', '.join(missing)}"
        )
    return True


class TavilyHealthcareSearchTool(BaseTool):
    """Tool for searching healthcare-related information using Tavily API."""
    
    name: str = Field(default="tavily_healthcare_search")
    description: str = Field(
        default="Search for healthcare-related information, medical conditions, treatments, and clinical data using Tavily search engine. Only use for healthcare/medical queries."
    )
    api_key: str = Field(description="Tavily API key")
    connection_manager: Any = Field(description="Connection manager for HTTP requests")
    
    def __init__(self, api_key: str, connection_manager: Any = None, **kwargs):
        """Initialize the Tavily healthcare search tool.
        
        Args:
            api_key: Tavily API key for authentication
            connection_manager: HTTP connection manager instance
            **kwargs: Additional keyword arguments
        """
        super().__init__(api_key=api_key, connection_manager=connection_manager, **kwargs)
        if connection_manager is None:
            self.connection_manager = ConnectionManager()
    
    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute healthcare search using Tavily API.
        
        Args:
            query: Search query string
            run_manager: Optional callback manager for tool execution
            
        Returns:
            Formatted search results as string
        """
        try:
            healthcare_query = self._enhance_healthcare_query(query)
            
            try:
                loop = asyncio.get_running_loop()
                task = asyncio.create_task(self._search_tavily(healthcare_query))
                result = asyncio.run_coroutine_threadsafe(task, loop).result(timeout=30)
            except RuntimeError:
                result = asyncio.run(self._search_tavily(healthcare_query))
            
            return result
            
        except Exception as e:
            return f"❌ Healthcare search error: {str(e)}\n\nPlease try rephrasing your healthcare query."
    
    async def _arun(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Async version of healthcare search.
        
        Args:
            query: Search query string
            run_manager: Optional callback manager for tool execution
            
        Returns:
            Formatted search results as string
        """
        try:
            healthcare_query = self._enhance_healthcare_query(query)
            return await self._search_tavily(healthcare_query)
        except Exception as e:
            return f"❌ Healthcare search error: {str(e)}"
    
    def _enhance_healthcare_query(self, query: str) -> str:
        """Enhance query with healthcare-specific terms and filters.
        
        Args:
            query: Original search query
            
        Returns:
            Enhanced query with healthcare context and site filters
        """
        healthcare_keywords = [
            'medical', 'health', 'disease', 'condition', 'treatment', 'therapy',
            'diagnosis', 'symptom', 'medication', 'drug', 'clinical', 'patient',
            'hospital', 'doctor', 'physician', 'nurse', 'healthcare', 'medicine'
        ]
        
        query_lower = query.lower()
        has_healthcare_context = any(keyword in query_lower for keyword in healthcare_keywords)
        
        if not has_healthcare_context:
            enhanced_query = f"healthcare medical {query}"
        else:
            enhanced_query = query
        
        trusted_sources = " site:nih.gov OR site:mayoclinic.org OR site:webmd.com OR site:who.int OR site:cdc.gov OR site:pubmed.ncbi.nlm.nih.gov"
        enhanced_query += trusted_sources
        
        return enhanced_query
    
    async def _search_tavily(self, query: str) -> str:
        """Perform the actual Tavily search with proper connection management.
        
        Args:
            query: Enhanced search query
            
        Returns:
            Formatted search results
        """
        url = "https://api.tavily.com/search"
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "include_raw_content": False,
            "max_results": 5,
            "include_domains": [
                "nih.gov", "mayoclinic.org", "webmd.com", "who.int", 
                "cdc.gov", "pubmed.ncbi.nlm.nih.gov", "medlineplus.gov",
                "healthline.com", "clevelandclinic.org", "jhsph.edu"
            ],
            "exclude_domains": [
                "reddit.com", "quora.com", "yahoo.com", "pinterest.com"
            ]
        }
        
        try:
            session = await self.connection_manager.get_session()
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._format_healthcare_search_results(data, query)
                else:
                    error_text = await response.text()
                    return f"❌ Tavily API error (status {response.status}): {error_text}"
        
        except asyncio.TimeoutError:
            return f"❌ Request timeout connecting to Tavily API"
        except aiohttp.ClientError as e:
            return f"❌ Network error connecting to Tavily: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected error during healthcare search: {str(e)}"
    
    def _format_healthcare_search_results(self, data: Dict, original_query: str) -> str:
        """Format Tavily search results for healthcare context.
        
        Args:
            data: Raw API response data
            original_query: Original search query
            
        Returns:
            Formatted search results string
        """
        try:
            results = data.get("results", [])
            answer = data.get("answer", "")
            
            if not results and not answer:
                return f"🔍 No healthcare information found for: {original_query}\n\nTry rephrasing your medical query or being more specific about the condition or treatment."
            
            formatted_result = f"🏥 Healthcare Information Search Results for: {original_query}\n\n"
            
            if answer:
                formatted_result += f"📋 Medical Summary:\n{answer}\n\n"
            
            if results:
                formatted_result += "🔍 Trusted Healthcare Sources:\n"
                for i, result in enumerate(results[:3], 1):
                    title = result.get("title", "No title")
                    url = result.get("url", "No URL")
                    content = result.get("content", "No content available")
                    
                    if len(content) > 200:
                        content = content[:200] + "..."
                    
                    formatted_result += f"{i}. {title}\n"
                    formatted_result += f"   Source: {url}\n"
                    formatted_result += f"   Content: {content}\n\n"
            
            formatted_result += "✅ Please use this healthcare information to help answer the user's medical questions.\n"
            formatted_result += "⚠️  Note: This information is for educational purposes. Always consult healthcare professionals for medical advice."
            
            return formatted_result
            
        except Exception as e:
            return f"❌ Error formatting healthcare search results: {str(e)}"


class DatabaseQueryTool(BaseTool):
    """Tool for executing SQL queries with proper async handling."""
    
    name: str = Field(default="sql_db_query")
    description: str = Field(
        default="Execute a SQL query against the database. Returns structured data that should be interpreted for the user."
    )
    db_connection: Any = Field(description="Database connection instance")
    agent_instance: Any = Field(default=None, description="Agent instance to store data")
    
    def __init__(self, db_connection: Any, agent_instance: Any = None, **kwargs):
        """Initialize the database query tool.
        
        Args:
            db_connection: Database connection instance
            agent_instance: Agent instance to store structured data
            **kwargs: Additional keyword arguments
        """
        super().__init__(db_connection=db_connection, agent_instance=agent_instance, **kwargs)
    
    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute SQL query with proper async handling.
        
        Args:
            query: SQL query string to execute
            run_manager: Optional callback manager for tool execution
            
        Returns:
            Formatted query results as string
        """
        try:
            mapped_query = query
            if self.agent_instance and hasattr(self.agent_instance, '_map_column_names'):
                mapped_query = self.agent_instance._map_column_names(query)
                
                if '""' in mapped_query:
                    logger.warning(f"Detected double quotes in SQL, attempting to fix: {mapped_query}")
                    mapped_query = mapped_query.replace('""', '"')
            
            try:
                loop = asyncio.get_running_loop()
                task = asyncio.create_task(self.db_connection.execute_query(mapped_query))
                success, data, error, status_code = asyncio.run_coroutine_threadsafe(task, loop).result(timeout=30)
            except RuntimeError:
                success, data, error, status_code = asyncio.run(
                    self.db_connection.execute_query(mapped_query)
                )
            
            if success:
                if data:
                    if self.agent_instance and hasattr(self.agent_instance, 'last_query_data'):
                        self.agent_instance.last_query_data = data
                        self.agent_instance.last_query_sql = mapped_query
                        logger.info(f"Stored {len(data)} rows in last_query_data for table display")
                    
                    result_str = "✅ Query executed successfully."
                    return result_str
                else:
                    return "✅ Query executed successfully but returned no results. Please inform the user that no matching records were found."
            else:
                return f"❌ Error executing query: {error}\n\nPlease check the column names and table structure, then try again with corrected SQL."
                
        except Exception as e:
            error_message = str(e)
            if "zero-length delimited identifier" in error_message:
                logger.error(f"Double quote error in SQL: {mapped_query}")
                return f"❌ SQL syntax error: Invalid column quoting detected in query.\n🔍 Query: {mapped_query}\n\nPlease check the query structure and try again."
            elif "column" in error_message and "does not exist" in error_message:
                return f"❌ Database schema error: {error_message}\n🔍 Query: {mapped_query}\n\nPlease check column names and try again."
            else:
                return f"⚠️ Tool execution error: {error_message}\n🔍 Query: {mapped_query}\n\nPlease revise the query and try again."
    
    async def _arun(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Async version of query execution.
        
        Args:
            query: SQL query string to execute
            run_manager: Optional callback manager for tool execution
            
        Returns:
            Formatted query results as string
        """
        try:
            mapped_query = query
            if self.agent_instance and hasattr(self.agent_instance, '_map_column_names'):
                mapped_query = self.agent_instance._map_column_names(query)
                
                if '""' in mapped_query:
                    logger.warning(f"Detected double quotes in SQL, attempting to fix: {mapped_query}")
                    mapped_query = mapped_query.replace('""', '"')
            
            success, data, error, status_code = await self.db_connection.execute_query(mapped_query)
            
            if success:
                if data:
                    if self.agent_instance and hasattr(self.agent_instance, 'last_query_data'):
                        self.agent_instance.last_query_data = data
                        self.agent_instance.last_query_sql = mapped_query
                        logger.info(f"Stored {len(data)} rows in last_query_data for table display")
                    
                    result_str = "✅ Query executed successfully."
                    return result_str
                else:
                    return "✅ Query executed successfully but returned no results. Please inform the user that no matching records were found."
            else:
                return f"❌ Error executing query: {error}\n\nPlease check the column names and table structure."
                
        except Exception as e:
            error_message = str(e)
            if "zero-length delimited identifier" in error_message:
                logger.error(f"Double quote error in async SQL execution")
                return f"❌ SQL syntax error: Invalid column quoting detected in query.\n\nPlease check the query structure and try again."
            elif "column" in error_message and "does not exist" in error_message:
                return f"❌ Database schema error: {error_message}\n\nPlease check column names and try again."
            else:
                return f"⚠️ Tool execution error: {error_message}"


class DatabaseSchemaReaderTool(BaseTool):
    """Tool for reading database schema with exact column names."""
    
    name: str = Field(default="sql_db_schema")
    description: str = Field(
        default="Get the schema and sample rows for specified tables. Shows exact column names and structure."
    )
    db_connection: Any = Field(description="Database connection instance")
    
    def __init__(self, db_connection: Any, **kwargs):
        """Initialize the database schema reader tool.
        
        Args:
            db_connection: Database connection instance
            **kwargs: Additional keyword arguments
        """
        super().__init__(db_connection=db_connection, **kwargs)
    
    def _run(self, table_names: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get database schema information with exact column names.
        
        Args:
            table_names: Comma-separated list of table names to inspect
            run_manager: Optional callback manager for tool execution
            
        Returns:
            Formatted schema information as string
        """
        try:
            if not hasattr(self.db_connection, 'schema_cache') or not self.db_connection.schema_cache:
                return "Schema not loaded. Please ensure database connection is established."
            
            schema = self.db_connection.schema_cache
            
            if not table_names.strip():
                result = "🏥 Healthcare Database Tables:\n\n"
                for table_key, table_info in schema.get("tables", {}).items():
                    table_name = table_info["name"]
                    column_count = len(table_info.get("columns", []))
                    result += f"📋 {table_name} ({column_count} columns)\n"
                
                result += "\n💡 Use sql_db_schema with specific table names to get detailed column information."
                result += "\n⚠️  Always check exact column names before writing queries!"
                return result
            else:
                requested_tables = [name.strip() for name in table_names.split(",")]
                result = "📊 EXACT COLUMN NAMES FOR SQL QUERIES:\n\n"
                
                for table_key, table_info in schema.get("tables", {}).items():
                    table_name = table_info["name"]
                    
                    if table_name.lower() in [t.lower() for t in requested_tables]:
                        result += f"📋 Table: {table_name}\n"
                        result += "📝 Exact Column Names (use these in SQL):\n"
                        
                        for col in table_info.get("columns", []):
                            exact_col_name = col['name']
                            col_info = f"   • {exact_col_name} ({col['type']})"
                            if not col.get('nullable', True):
                                col_info += " NOT NULL"
                            if col.get('primary_key'):
                                col_info += " PRIMARY KEY"
                            result += col_info + "\n"
                        
                        result += "\n"
                
                relationships = schema.get("relationships", [])
                relevant_rels = [
                    rel for rel in relationships 
                    if any(table.lower() in rel.get("from_table", "").lower() or 
                          table.lower() in rel.get("to_table", "").lower() 
                          for table in requested_tables)
                ]
                
                if relevant_rels:
                    result += "🔗 Table Relationships:\n"
                    for rel in relevant_rels:
                        from_col = rel['from_column']
                        to_col = rel['to_column']
                        result += f"   {rel['from_table']}.{from_col} → {rel['to_table']}.{to_col}\n"
                
                result += "\n✅ Copy these exact column names for your SQL queries!"
                return result
                
        except Exception as e:
            return f"❌ Error reading schema: {str(e)}"
    
    async def _arun(self, table_names: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Async version of schema reading.
        
        Args:
            table_names: Comma-separated list of table names to inspect
            run_manager: Optional callback manager for tool execution
            
        Returns:
            Formatted schema information as string
        """
        return self._run(table_names, run_manager)


class DatabaseListTablesTool(BaseTool):
    """Tool for listing all database tables."""
    
    name: str = Field(default="sql_db_list_tables")
    description: str = Field(
        default="List all tables in the healthcare database with descriptions."
    )
    db_connection: Any = Field(description="Database connection instance")
    
    def __init__(self, db_connection: Any, **kwargs):
        """Initialize the database table listing tool.
        
        Args:
            db_connection: Database connection instance
            **kwargs: Additional keyword arguments
        """
        super().__init__(db_connection=db_connection, **kwargs)
    
    def _run(self, query: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """List all database tables.
        
        Args:
            query: Optional query parameter (not used)
            run_manager: Optional callback manager for tool execution
            
        Returns:
            Formatted list of database tables
        """
        try:
            if not hasattr(self.db_connection, 'schema_cache') or not self.db_connection.schema_cache:
                return "Schema not loaded. Please ensure database connection is established."
            
            schema = self.db_connection.schema_cache
            table_names = [table_info["name"] for table_info in schema.get("tables", {}).values()]
            
            result = "🏥 Healthcare Database Tables Overview:\n\n"
            result += f"📊 Available Tables: {', '.join(table_names)}\n\n"
            result += "🔍 Key Healthcare Tables:\n"
            result += "   • patients - Patient demographics and personal information\n"
            result += "   • conditions - Medical diagnoses and health conditions\n" 
            result += "   • medications - Prescribed drugs and treatments\n"
            result += "   • procedures - Medical procedures and surgeries\n"
            result += "   • encounters - Doctor visits and hospital stays\n"
            result += "   • providers - Healthcare professionals and doctors\n"
            result += "   • observations - Patient vitals and measurements\n"
            result += "   • allergies - Patient allergies and reactions\n"
            
            result += "\n💡 Use sql_db_schema with specific table names to get exact column information!"
            return result
            
        except Exception as e:
            return f"❌ Error listing tables: {str(e)}"
    
    async def _arun(self, query: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Async version of table listing.
        
        Args:
            query: Optional query parameter (not used)
            run_manager: Optional callback manager for tool execution
            
        Returns:
            Formatted list of database tables
        """
        return self._run(query, run_manager)


class ConnectionManager:
    """Manages HTTP connections and SSL contexts for the agent."""
    
    def __init__(self):
        """Initialize the connection manager."""
        self._session = None
        self._ssl_context = None
        self._connector = None
        
    def _create_ssl_context(self):
        """Create SSL context for secure connections.
        
        Returns:
            SSL context configured for secure connections
        """
        if self._ssl_context is None:
            self._ssl_context = ssl.create_default_context()
            self._ssl_context.check_hostname = True
            self._ssl_context.verify_mode = ssl.CERT_REQUIRED
        return self._ssl_context
    
    def _create_connector(self):
        """Create HTTP connector with proper SSL and connection pooling.
        
        Returns:
            Configured TCP connector for HTTP requests
        """
        if self._connector is None:
            self._connector = aiohttp.TCPConnector(
                ssl=self._create_ssl_context(),
                limit=10,
                limit_per_host=5,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
        return self._connector
    
    async def get_session(self):
        """Get or create aiohttp session with proper configuration.
        
        Returns:
            Configured aiohttp client session
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(
                connector=self._create_connector(),
                timeout=timeout,
                raise_for_status=False
            )
        return self._session
    
    async def close(self):
        """Close all connections."""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._connector:
            await self._connector.close()
        self._session = None
        self._connector = None


class LangGraphReActDatabaseAgent:
    """Enhanced LangGraph ReAct agent with Tavily healthcare search integration."""
    
    def __init__(self, dialect: str = "PostgreSQL", top_k: int = 10):
        """Initialize the LangGraph ReAct database agent.
        
        Args:
            dialect: Database dialect (default: PostgreSQL)
            top_k: Maximum number of results to return
        """
        try:
            _validate_azure_env_vars()
        except EnvironmentError as e:
            logger.error(f"Environment validation failed: {e}")
            raise
        
        self.dialect = dialect
        self.top_k = top_k
        self._connection_manager = ConnectionManager()
        self._cleanup_tasks = []
        
        self.last_query_data = None
        self.last_query_sql = None
        self.last_table_data = None
        
        self.column_mapping = {
            'first_name': '"FIRST"',
            'last_name': '"LAST"', 
            'birthdate': '"BIRTHDATE"',
            'patient_id': '"PATIENT_ID"',
            'deathdate': '"DEATHDATE"',
            'gender': '"GENDER"',
            'race': '"RACE"',
            'ethnicity': '"ETHINICITY"',  # Note: DB has typo "ETHINICITY"
            'address': '"ADDRESS"',
            'city': '"CITY"',
            'state': '"STATE"',
            'zip': '"ZIP"',
            'ssn': '"SSN"',
            'martial': '"MARTIAL"',
            'healthcare_expenses': '"HEALTHCARE_EXPENSES"',
            'healthcare_coverage': '"HEALTHCARE_COVERAGE"'
        }
        
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            deployment_name=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'),
            model=os.getenv('AZURE_OPENAI_MODEL_NAME'),
            temperature=0.0,  # Reduce for faster, more deterministic responses
            request_timeout=15.0,  # Reduce timeout for faster failure
            max_retries=1,  # Reduce retries for speed
            max_tokens=512  # Limit response length for speed
        )
        
        if DatabaseConnection:
            self.db_connection = DatabaseConnection()
        else:
            raise ImportError("DatabaseConnection not available")
        
        self.tavily_api_key = os.getenv('TAVILY_API_KEY')
        if not self.tavily_api_key:
            logger.warning("TAVILY_API_KEY not found in environment variables")
            
        self.schema_description = self._load_schema_description()
        self.tools = self._setup_tools()
        self.system_prompt = self._create_enhanced_system_prompt()
        
        self.agent = create_react_agent(
            self.llm,
            self.tools,
            prompt=self.system_prompt,
        )
        
        self._register_cleanup()
    
    def _load_schema_description(self) -> str:
        """Load the database description from description.json.
        
        Returns:
            Database schema description or empty string if not found
        """
        try:
            with open("description.json", 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning("description.json not found")
            return ""
        except Exception as e:
            logger.error(f"Error loading description.json: {e}")
            return ""
    
    def _setup_tools(self) -> List[BaseTool]:
        """Setup tools for the ReAct agent including Tavily search.
        
        Returns:
            List of configured tools for the agent
        """
        tools = [
            DatabaseListTablesTool(db_connection=self.db_connection),
            DatabaseSchemaReaderTool(db_connection=self.db_connection),
            DatabaseQueryTool(db_connection=self.db_connection, agent_instance=self)
        ]
        
        if self.tavily_api_key:
            tools.append(TavilyHealthcareSearchTool(
                api_key=self.tavily_api_key,
                connection_manager=self._connection_manager
            ))
            logger.info("Tavily healthcare search tool added")
        else:
            logger.warning("Tavily API key not available - healthcare search disabled")
        
        return tools
    
    def _create_enhanced_system_prompt(self) -> str:
        """Create system prompt for the agent.
        
        Returns:
            Complete system prompt for the agent
        """
        return f"""
You are a healthcare database assistant with access to both patient data and external medical information.

**Database Context:**
{self.schema_description}

**IMPORTANT - Follow-up Question Handling:**
- Pay careful attention to context from previous queries
- When users ask follow-up questions (using words like "also", "more", "what about", "show me their", etc.), refer to the previous context
- Maintain continuity in conversations - remember patients, conditions, and topics from earlier queries
- Do NOT respond with greetings to follow-up questions - continue the conversation naturally

**Query Guidelines:**
- Generate SQL queries that join necessary tables for meaningful results
- Return top {self.top_k} results based on relevance
- Include personal information (name, contact) but exclude sensitive data (ethnicity, SSN, financial)
- Use uppercase column names with double quotes: "COLUMN_NAME"
- Match names with iLIKE 'Name%' for prefix matching
- Follow privacy best practices
- The answer should be always top 5 never add more than 5 results
- Do NOT summarize or re-list query results - the table will display them
- Keep your response extremely brief - just introduce what the table shows
- Never return the ID of the Tables always return readable content.


**Tool Usage Strategy:**
1. **Database Tools** (for patient-specific data):
   - sql_db_list_tables: See available tables
   - sql_db_schema: Get exact column names
   - sql_db_query: Execute SQL queries

2. **Healthcare Search** (for medical information):tavily_healthcare_search

**Response Format:**
- NEVER create markdown tables with | symbols - the frontend handles table display
- NEVER include table data in your response - only provide brief context
- Keep responses extremely brief (1-2 sentences max)
- Do NOT re-list or summarize data that's already in the table
- Do NOT include column headers or data rows in your response
- Only provide minimal context like "Found patients with diabetes." or "Retrieved medication data."
- Combine database results with relevant medical context only when helpful
- Prioritize patient privacy and data security
- Do not add any guideline related line which says always consult a doctor
- For follow-up questions, acknowledge the connection to previous queries when relevant


Remember: Database queries for patient data, Tavily search for medical knowledge and context. 
"""
    
    def _register_cleanup(self):
        """Register cleanup handlers for proper resource management."""
        import weakref
        import atexit
        
        def cleanup_callback():
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.run_until_complete(self._cleanup())
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
        
        atexit.register(cleanup_callback)
        
        weak_self = weakref.ref(self)
        
        def cleanup_finalizer():
            self_ref = weak_self()
            if self_ref:
                try:
                    asyncio.create_task(self_ref._cleanup())
                except Exception:
                    pass
        
        weakref.finalize(self, cleanup_finalizer)
    
    async def _cleanup(self):
        """Clean up resources."""
        try:
            if self._connection_manager:
                await self._connection_manager.close()
            
            if hasattr(self.db_connection, 'close'):
                await self.db_connection.close()
        except Exception as e:
            logger.warning(f"Error during resource cleanup: {e}")
    
    async def __aenter__(self):
        """Async context manager entry.
        
        Returns:
            Self instance for use in async context
        """
        await self._ensure_ready()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit.
        
        Args:
            exc_type: Exception type if any
            exc_val: Exception value if any
            exc_tb: Exception traceback if any
        """
        await self._cleanup()
    
    async def process_query(self, user_question: str, conversation_context: str = None):
        """Process user question with optimized ReAct agent.
        
        Args:
            user_question: User's question or query
            conversation_context: Optional conversation context
            
        Returns:
            Processed response from the agent
        """
        try:
            logger.info(f"Processing query: {user_question}")
            
            await self._ensure_ready()
            
            actual_question = user_question
            if "Current question:" in user_question:
                parts = user_question.split("Current question:")
                if len(parts) > 1:
                    actual_question = parts[1].strip()
                    if "\n\nPlease use" in actual_question:
                        actual_question = actual_question.split("\n\nPlease use")[0].strip()
            
            greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
            question_lower = actual_question.lower().strip()
            
            is_pure_greeting = (
                question_lower in greeting_words or
                (len(question_lower.split()) <= 3 and any(word in question_lower for word in greeting_words) and
                 not any(other in question_lower for other in ['show', 'find', 'get', 'list', 'what', 'who', 'where', 'when']))
            )
            
            is_follow_up = (
                (conversation_context is not None and len(conversation_context) > 0) or
                "Previous conversation context" in user_question or
                any(indicator in question_lower for indicator in [
                    'also', 'more', 'what about', 'show me', 'tell me', 
                    'from', 'previous', 'last', 'that', 'those', 'them',
                    'his', 'her', 'their', 'the same', 'additionally'
                ])
            )
            
            if is_pure_greeting and not is_follow_up:
                return DatabaseResponse(
                    success=True,
                    message="Hello! I'm your Healthcare Database Assistant. I can help you query patient data, medical records, and provide healthcare information. What would you like to know?",
                    result_count=0,
                    metadata={"type": "greeting"}
                )
            
            question_upper = user_question.strip().upper()
            if question_upper.startswith(('SELECT', 'DESCRIBE', 'EXPLAIN')):
                return await self._handle_direct_sql(user_question.strip())
            elif question_upper.startswith('SHOW') and any(keyword in question_upper for keyword in ['TABLES', 'COLUMNS', 'DATABASES', 'INDEXES']):
                return await self._handle_direct_sql(user_question.strip())
            
            if not any(word in user_question.lower() for word in ['over', 'under', 'age', 'years']):
                quick_response = await self._try_quick_patterns(user_question)
                if quick_response:
                    return quick_response
            
            try:
                messages = []
                if conversation_context:
                    messages.append(("system", f"Previous conversation context:\n{conversation_context}"))
                messages.append(("user", self._optimize_query_prompt(user_question)))
                
                result = await asyncio.wait_for(
                    self.agent.ainvoke({
                        "messages": messages
                    }), 
                    timeout=12.0
                )
            except asyncio.TimeoutError:
                logger.warning("Agent timeout, falling back to direct query")
                return await self._handle_timeout_fallback(user_question)
            except Exception as agent_error:
                logger.error(f"Agent execution error: {agent_error}")
                return self._create_error_response(user_question, str(agent_error))
            
            parsed_response = self._parse_agent_response(result, user_question)
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return self._create_error_response(user_question, str(e))
    
    def _optimize_query_prompt(self, user_question: str) -> str:
        """Optimize the query prompt for faster processing."""
        return f"Execute this healthcare database query efficiently: {user_question}"
    
    def _map_column_names(self, sql_query: str) -> str:
        """Map common column names to actual database column names."""
        for common_name, actual_name in self.column_mapping.items():
            pattern = r'(?<!")\b' + re.escape(common_name) + r'\b(?!")'
            sql_query = re.sub(pattern, actual_name, sql_query, flags=re.IGNORECASE)
        return sql_query
    
    async def _try_quick_patterns(self, user_question: str):
        """Try to handle common query patterns quickly without full agent."""
        return None
    
    async def _handle_direct_sql(self, sql_query: str):
        """Handle direct SQL queries without agent overhead."""
        try:
            mapped_sql = self._map_column_names(sql_query)
            
            if '""' in mapped_sql:
                logger.warning(f"Detected double quotes in SQL, attempting to fix: {mapped_sql}")
                mapped_sql = mapped_sql.replace('""', '"')
            
            success, data, error, status_code = await self.db_connection.execute_query(mapped_sql)
            
            if success and data:
                self.last_query_data = data
                self.last_query_sql = mapped_sql
                
                if isinstance(data[0], dict):
                    from src.models.response_models import TableData
                    headers = list(data[0].keys())
                    rows = [[str(row.get(col, '')) for col in headers] for row in data]
                    table_data = TableData(headers=headers, rows=rows, row_count=len(rows))
                else:
                    table_data = None
                
                return DatabaseResponse(
                    success=True,
                    message="Query executed successfully.",
                    result_count=len(data),
                    sql_query=mapped_sql,
                    table_data=table_data,
                    metadata={"type": "direct_sql", "execution_time": "fast"}
                )
            else:
                return DatabaseResponse(
                    success=False,
                    message=f"SQL execution failed: {error}",
                    result_count=0,
                    sql_query=mapped_sql,
                    metadata={"type": "direct_sql_error"}
                )
        except Exception as e:
            error_message = str(e)
            if "zero-length delimited identifier" in error_message:
                logger.error(f"Double quote error in SQL: {mapped_sql}")
                return DatabaseResponse(
                    success=False,
                    message="SQL syntax error: Invalid column quoting detected. Please check the query structure.",
                    result_count=0,
                    sql_query=mapped_sql,
                    metadata={"type": "quote_error", "original_error": error_message}
                )
            elif "column" in error_message and "does not exist" in error_message:
                return DatabaseResponse(
                    success=False,
                    message=f"Database schema error: {error_message}",
                    result_count=0,
                    sql_query=mapped_sql,
                    metadata={"type": "schema_error", "original_error": error_message}
                )
            else:
                return self._create_error_response(sql_query, error_message)
    
    async def _handle_timeout_fallback(self, user_question: str):
        """Handle timeout with simplified response."""
        try:
            if any(word in user_question.lower() for word in ['patients', 'patient']):
                if 'limit' not in user_question.lower():
                    fallback_sql = 'SELECT "FIRST", "LAST", "BIRTHDATE" FROM patients LIMIT 10'
                    return await self._handle_direct_sql(fallback_sql)
            
            return DatabaseResponse(
                success=False,
                message="Query timed out. Please try a simpler query or be more specific.",
                result_count=0,
                metadata={"type": "timeout"}
            )
        except Exception as e:
            return self._create_error_response(user_question, str(e))
    
    def _format_concise_response(self, response, user_question: str):
        """Format response to be concise and table-friendly.
        
        Args:
            response: Raw agent response
            user_question: Original user question
            
        Returns:
            Formatted response optimized for display
        """
        try:
            if hasattr(response, 'dict'):
                response_data = response.dict()
            else:
                response_data = response
            
            existing_message = response_data.get("message", "")
            
            is_greeting_or_conversation = any(word in user_question.lower() for word in ['hello', 'hi', 'thanks', 'thank you', 'goodbye', 'bye'])
            
            if existing_message and len(existing_message) > 30 and not self._is_just_raw_data(existing_message):
                response_data["metadata"] = response_data.get("metadata", {})
                response_data["metadata"]["format"] = "natural_language"
                response_data["metadata"]["formatting_preserved"] = True
                
                if hasattr(response, 'dict'):
                    return type(response)(**response_data)
                else:
                    return response_data
            
            if is_greeting_or_conversation and existing_message and len(existing_message) > 15:
                response_data["metadata"] = response_data.get("metadata", {})
                response_data["metadata"]["format"] = "conversational"
                response_data["metadata"]["formatting_preserved"] = True
                
                if hasattr(response, 'dict'):
                    return type(response)(**response_data)
                else:
                    return response_data
            
            results = response_data.get("results", [])
            result_count = response_data.get("result_count", 0)
            sql_query = response_data.get("sql_query", "")
            
            summary = self._create_summary(results, result_count, user_question)
            
            table_text = self._create_table_text(results, result_count)
            
            insights = self._create_insights(results, user_question)
            
            concise_message = f"**SUMMARY**: {summary}\n\n"
            if table_text:
                concise_message += f"**DATA**:\n{table_text}\n\n"
            if insights:
                concise_message += f"**KEY INSIGHTS**:\n{insights}"
            
            response_data["message"] = concise_message.strip()
            
            response_data["metadata"] = response_data.get("metadata", {})
            response_data["metadata"]["result_count_only"] = len(results) if results else 0
            response_data["metadata"]["sql_executed"] = sql_query
            response_data["metadata"]["format"] = "concise_table"
            
            if hasattr(response, 'dict'):
                return type(response)(**response_data)
            else:
                return response_data
                
        except Exception as e:
            logger.error(f"Error formatting concise response: {e}")
            return response
    
    def _create_summary(self, results, result_count: int, user_question: str) -> str:
        """Create one-sentence summary.
        
        Args:
            results: Query results
            result_count: Number of results
            user_question: Original user question
            
        Returns:
            Summary string
        """
        if result_count == 0:
            return "No results found."
        elif result_count == 1:
            return "Query completed."
        else:
            return "Query completed."
    
    def _create_table_text(self, results, result_count: int) -> str:
        """Create safe table description without exposing actual data.
        
        Args:
            results: Query results (not used for privacy)
            result_count: Number of results
            
        Returns:
            Safe description string
        """
        if result_count == 0:
            return "No data to display"
        
        return f"Data table with {result_count} records available for display"
    
    def _create_insights(self, results, user_question: str) -> str:
        """Create safe insights without exposing actual data.
        
        Args:
            results: Query results (not used for privacy)
            user_question: Original user question
            
        Returns:
            Safe insights string
        """
        if not results:
            return "• No data available for analysis"
        
        insights = []
        
        if "patient" in user_question.lower():
            insights.append("• Patient data retrieved from healthcare database")
        elif "medication" in user_question.lower():
            insights.append("• Medication information available")
        elif "appointment" in user_question.lower():
            insights.append("• Appointment data retrieved")
        else:
            insights.append("• Healthcare data retrieved successfully")
        
        return "\n".join(insights[:1])
    
    async def _ensure_ready(self):
        """Ensure database connection and schema are ready."""
        try:
            connected, error = await self.db_connection.test_connection()
            if not connected:
                raise Exception(f"Database connection failed: {error}")
            
            if not hasattr(self.db_connection, 'schema_cache') or not self.db_connection.schema_cache:
                await self.db_connection.extract_complete_schema()
        except Exception as e:
            logger.error(f"Error ensuring database readiness: {e}")
            raise
    
    def _parse_agent_response(self, agent_result: Dict, user_question: str):
        """Parse LangGraph agent response.
        
        Args:
            agent_result: Raw agent response
            user_question: Original user question
            
        Returns:
            Parsed and structured response
        """
        try:
            messages = agent_result.get("messages", [])
            if not messages:
                return self._create_error_response(user_question, "No messages in response")
            
            final_message = None
            for msg in reversed(messages):
                if hasattr(msg, 'content') and msg.content:
                    final_message = msg.content
                    break
            
            if not final_message:
                return self._create_error_response(user_question, "No content found in response")
            
            logger.info(f"Processing agent output: {final_message[:200]}...")
            
            response_data = {
                "success": True,
                "message": "",
                "results": [],
                "result_count": 0,
                "sql_query": "",
                "table_data": None,
                "metadata": {}
            }
            
            stored_sql = None
            if hasattr(self, 'last_query_sql') and self.last_query_sql:
                stored_sql = self.last_query_sql
            
            if hasattr(self, 'last_query_data') and self.last_query_data:
                try:
                    from src.models.response_models import TableData
                    if isinstance(self.last_query_data, list) and len(self.last_query_data) > 0:
                        if isinstance(self.last_query_data[0], dict):
                            headers = list(self.last_query_data[0].keys())
                            
                            response_data["table_data"] = TableData(
                                headers=headers,
                                data=self.last_query_data,
                                row_count=len(self.last_query_data)
                            )
                            response_data["result_count"] = len(self.last_query_data)
                            logger.info(f"Created table_data with {len(headers)} columns and {len(self.last_query_data)} rows")
                except Exception as e:
                    logger.warning(f"Error creating table data: {e}")
                
                self.last_query_data = None
                self.last_query_sql = None
            
            sql_pattern = r'(?:SELECT|INSERT|UPDATE|DELETE)[^;]+;?'
            sql_matches = re.findall(sql_pattern, final_message, re.IGNORECASE | re.DOTALL)
            if sql_matches:
                response_data["sql_query"] = sql_matches[-1].strip()
                logger.info(f"Extracted SQL from response: {sql_matches[-1].strip()[:100]}...")
            elif stored_sql:
                response_data["sql_query"] = stored_sql
                logger.info(f"Using stored SQL: {stored_sql[:100]}...")
            
            json_pattern = r'\{[^{}]*\}'
            json_matches = re.findall(json_pattern, final_message)
            
            for json_str in json_matches:
                try:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict):
                        for key in ['results', 'result_count', 'message']:
                            if key in parsed:
                                response_data[key] = parsed[key]
                except:
                    continue
            
            lines = final_message.split('\n')
            natural_lines = []
            
            for line in lines:
                if not any(skip in line.lower() for skip in ['sql_db_', 'tavily_', 'thought:', '```', 'action:', 'observation:']):
                    cleaned = line.strip()
                    if cleaned and len(cleaned) > 10 and not cleaned.startswith('{') and '|' not in cleaned and not cleaned.startswith('---'):
                        natural_lines.append(cleaned)
            
            if natural_lines and not response_data["message"]:
                response_data["message"] = ' '.join(natural_lines)
            elif not response_data["message"]:
                response_data["message"] = "Query processed successfully."
            
            if DatabaseResponse:
                return DatabaseResponse(**response_data)
            else:
                return response_data
                
        except Exception as e:
            logger.error(f"Error parsing agent response: {e}")
            return self._create_error_response(user_question, str(e))
    
    def _is_just_raw_data(self, message: str) -> bool:
        """Check if message is just raw data without interpretation.
        
        Args:
            message: Message to check
            
        Returns:
            True if message appears to be raw data
        """
        raw_indicators = [
            message.strip().isdigit(),
            message.count('\n') == 0 and ',' in message and len(message.split(',')) > 2,
            message.startswith('[') and message.endswith(']'),
            len(message.split()) < 5 and any(char.isdigit() for char in message)
        ]
        return any(raw_indicators)
    
    def _enhance_with_natural_language(self, parsed_json: Dict, original_text: str, user_question: str) -> Dict[str, Any]:
        """Enhance JSON response with natural language interpretation.
        
        Args:
            parsed_json: Parsed JSON response
            original_text: Original agent output text
            user_question: Original user question
            
        Returns:
            Enhanced response with natural language
        """
        text_parts = original_text.split('\n')
        natural_language_parts = []
        
        for part in text_parts:
            if not (part.strip().startswith('{') or part.strip().startswith('```') or 
                   'sql_db_' in part.lower() or 'tavily_' in part.lower() or 
                   part.strip().startswith('Thought:')):
                if len(part.strip()) > 10:
                    natural_language_parts.append(part.strip())
        
        if natural_language_parts:
            natural_message = ' '.join(natural_language_parts)
        else:
            natural_message = self._generate_interpretation(parsed_json, user_question)
        
        parsed_json["message"] = natural_message
        return self._validate_and_enhance_json(parsed_json, user_question)
    
    def _generate_interpretation(self, data: Dict, user_question: str) -> str:
        """Generate natural language interpretation of query results.
        
        Args:
            data: Response data dictionary
            user_question: Original user question
            
        Returns:
            Natural language interpretation
        """
        result_count = data.get("result_count", 0)
        results = data.get("results", [])
        
        if "count" in user_question.lower() or "how many" in user_question.lower():
            return f"The answer is {result_count}."
        
        elif result_count == 0:
            return "No matching data found."
        
        else:
            return "Data retrieved successfully."
    
    def _create_response_from_text(self, text: str, user_question: str) -> Dict[str, Any]:
        """Create response structure from natural language text.
        
        Args:
            text: Natural language text
            user_question: Original user question
            
        Returns:
            Structured response dictionary
        """
        numbers = re.findall(r'\b(\d+)\b', text)
        estimated_count = int(numbers[0]) if numbers else 0
        
        sql_match = re.search(r'(SELECT.*?)(?:;|\n|$)', text, re.IGNORECASE | re.DOTALL)
        sql_query = sql_match.group(1).strip() if sql_match else None
        
        success_indicators = ["found", "successfully", "records", "patients", "results"]
        error_indicators = ["error", "failed", "unable", "cannot"]
        
        text_lower = text.lower()
        success_score = sum(1 for indicator in success_indicators if indicator in text_lower)
        error_score = sum(1 for indicator in error_indicators if indicator in text_lower)
        
        is_successful = success_score > error_score
        
        return {
            "success": is_successful,
            "message": text.strip(),
            "query_understanding": f"Processed healthcare query: {user_question}",
            "sql_query": sql_query,
            "result_count": estimated_count,
            "results": [],
            "metadata": {
                "agent_type": "langgraph_react_enhanced_natural_with_tavily",
                "response_type": "natural_language_primary",
                "success_indicators": success_score,
                "error_indicators": error_score,
                "tavily_enabled": bool(self.tavily_api_key)
            }
        }
    
    def _extract_natural_language_response(self, text: str) -> Optional[str]:
        """Extract natural language response from agent output.
        
        Args:
            text: Agent output text
            
        Returns:
            Extracted natural language response or None
        """
        text = text.strip()
        
        final_answer_patterns = [
            r'final answer:\s*(.*?)(?:\n\n|$)',
            r'response:\s*(.*?)(?:\n\n|$)',
            r'answer:\s*(.*?)(?:\n\n|$)'
        ]
        
        for pattern in final_answer_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                if len(content) > 20:
                    return content
        
        lines = text.split('\n')
        natural_lines = []
        skip_keywords = [
            'action:', 'observation:', 'thought:', 'action_input:', 
            'sql_db_', 'tavily_', 'tool:', 'using tool'
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if any(skip.lower() in line.lower() for skip in skip_keywords):
                continue
            if line.startswith('{') or line.startswith('```') or line.startswith('['):
                continue
            if re.match(r'^\s*[\d\.,\-\s|]+\s*$', line):
                continue
            if len(line) > 15:
                natural_lines.append(line)
        
        if natural_lines:
            response = ' '.join(natural_lines)
            response = re.sub(r'\s+', ' ', response)
            response = response.strip()
            
            if len(response) > 30 and not self._is_just_raw_data(response):
                return response
        
        sentences = re.findall(r'[A-Z][^.!?]*[.!?]', text)
        if sentences:
            meaningful_sentences = [s for s in sentences if len(s) > 20 and 'action' not in s.lower()]
            if meaningful_sentences:
                return ' '.join(meaningful_sentences[:3])
        
        return None
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from text using multiple strategies.
        
        Args:
            text: Text containing potential JSON
            
        Returns:
            Extracted JSON dictionary or None
        """
        json_block_match = re.search(r'```json\n?(.*?)\n?```', text, re.DOTALL | re.IGNORECASE)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        json_matches = re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        for match in json_matches:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _validate_and_enhance_json(self, parsed_json: Dict[str, Any], user_question: str) -> Dict[str, Any]:
        """Validate and enhance parsed JSON with required fields.
        
        Args:
            parsed_json: Parsed JSON response
            user_question: Original user question
            
        Returns:
            Enhanced and validated JSON response
        """
        enhanced_json = {
            "success": parsed_json.get("success", True),
            "message": parsed_json.get("message", "Query processed successfully"),
            "query_understanding": parsed_json.get("query_understanding", f"Processed: {user_question}"),
            "sql_query": parsed_json.get("sql_query"),
            "result_count": parsed_json.get("result_count", 0),
            "results": self._format_results(parsed_json.get("results", [])),
            "metadata": parsed_json.get("metadata", {})
        }
        
        if isinstance(enhanced_json["success"], str):
            enhanced_json["success"] = enhanced_json["success"].lower() in ["true", "yes", "success"]
        
        if not isinstance(enhanced_json["result_count"], int):
            try:
                enhanced_json["result_count"] = int(enhanced_json["result_count"])
            except (ValueError, TypeError):
                enhanced_json["result_count"] = len(enhanced_json["results"])
        
        enhanced_json["metadata"]["agent_type"] = "langgraph_react_enhanced_natural_with_tavily"
        enhanced_json["metadata"]["dialect"] = self.dialect
        enhanced_json["metadata"]["top_k_limit"] = self.top_k
        enhanced_json["metadata"]["response_enhanced"] = True
        enhanced_json["metadata"]["tavily_enabled"] = bool(self.tavily_api_key)
        
        return enhanced_json
    
    def _format_results(self, results: List[Any]) -> List[Any]:
        """Format results into QueryResult objects if available.
        
        Args:
            results: Raw results list
            
        Returns:
            Formatted results list
        """
        if not QueryResult:
            return results
            
        formatted_results = []
        for item in results:
            if isinstance(item, dict):
                formatted_results.append(QueryResult(data=item))
            else:
                formatted_results.append(QueryResult(data={"value": str(item)}))
        return formatted_results
    
    def _create_error_response(self, user_question: str, error_msg: str):
        """Create a structured error response.
        
        Args:
            user_question: Original user question
            error_msg: Error message
            
        Returns:
            Structured error response
        """
        response_data = {
            "success": False,
            "message": f"I apologize, but I encountered an issue while processing your question: {error_msg}",
            "query_understanding": f"Attempted to process: {user_question}",
            "sql_query": None,
            "result_count": 0,
            "results": [],
            "metadata": {
                "error_type": "processing_error",
                "agent_type": "langgraph_react_enhanced_natural_with_tavily",
                "original_error": error_msg,
                "tavily_enabled": bool(self.tavily_api_key)
            }
        }
        
        if DatabaseResponse:
            return DatabaseResponse(**response_data)
        else:
            return response_data
    
    def clear_session_memory(self):
        """Clear session memory and cached data"""
        try:
            self.last_query_data = None
            self.last_query_sql = None
            self.last_table_data = None
            
            logger.info("Cleared cached query data from agent")
        except Exception as e:
            logger.warning(f"Error clearing session memory: {e}")


AzureReActDatabaseAgent = LangGraphReActDatabaseAgent


def setup_graceful_shutdown():
    """Setup graceful shutdown for the application."""
    import signal
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        
        try:
            loop = asyncio.get_running_loop()
            for task in asyncio.all_tasks(loop):
                task.cancel()
                
            loop.close()
        except RuntimeError:
            pass
        
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


setup_graceful_shutdown()