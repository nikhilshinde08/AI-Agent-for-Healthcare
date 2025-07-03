# src/agents/react_agent.py
import json
import re
from typing import Dict, Any, List, Optional
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from langgraph.prebuilt import create_react_agent
from pydantic import Field
import structlog
from dotenv import load_dotenv
import os
import asyncio

try:
    from models.response_models import DatabaseResponse, QueryResult
    from database.connection import DatabaseConnection
except ImportError:
    try:
        from src.models.response_models import DatabaseResponse, QueryResult
        from src.database.connection import DatabaseConnection
    except ImportError:
        print("Warning: Could not import response models or database connection")
        DatabaseResponse = None
        QueryResult = None
        DatabaseConnection = None

load_dotenv()
logger = structlog.get_logger(__name__)

class DatabaseQueryTool(BaseTool):
    """Tool for executing SQL queries with proper async handling"""
    name: str = Field(default="sql_db_query")
    description: str = Field(
        default="Execute a SQL query against the database. Use exact lowercase column names from the schema."
    )
    db_connection: Any = Field(description="Database connection instance")
    
    def __init__(self, db_connection: Any, **kwargs):
        super().__init__(db_connection=db_connection, **kwargs)
    
    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute SQL query with proper async handling"""
        try:
            try:
                loop = asyncio.get_running_loop()
                import nest_asyncio
                nest_asyncio.apply()
                success, data, error, status_code = loop.run_until_complete(
                    self.db_connection.execute_query(query)
                )
            except RuntimeError:
                success, data, error, status_code = asyncio.run(
                    self.db_connection.execute_query(query)
                )
            
            if success:
                if data:
                    result_str = f"Query executed successfully. Found {len(data)} results:\n"
                    
                    if isinstance(data[0], dict):
                        headers = list(data[0].keys())
                        result_str += "Columns: " + ", ".join(headers) + "\n\n"
                        
                        for i, row in enumerate(data[:5], 1):
                            result_str += f"Row {i}: " + ", ".join(f"{k}={v}" for k, v in row.items()) + "\n"
                        
                        if len(data) > 5:
                            result_str += f"... and {len(data) - 5} more rows\n"
                    else:
                        result_str += str(data)
                    
                    return result_str
                else:
                    return "Query executed successfully but returned no results."
            else:
                return f"Error executing query: {error}\n\nHINT: Check that you're using the exact column names from the schema (lowercase)."
                
        except Exception as e:
            return f"Tool execution error: {str(e)}\n\nHINT: Make sure to use exact column names from the database schema."
    
    async def _arun(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Async version"""
        try:
            success, data, error, status_code = await self.db_connection.execute_query(query)
            
            if success:
                if data:
                    result_str = f"Query executed successfully. Found {len(data)} results:\n"
                    
                    if isinstance(data[0], dict):
                        headers = list(data[0].keys())
                        result_str += "Columns: " + ", ".join(headers) + "\n\n"
                        
                        for i, row in enumerate(data[:5], 1):
                            result_str += f"Row {i}: " + ", ".join(f"{k}={v}" for k, v in row.items()) + "\n"
                        
                        if len(data) > 5:
                            result_str += f"... and {len(data) - 5} more rows\n"
                    else:
                        result_str += str(data)
                    
                    return result_str
                else:
                    return "Query executed successfully but returned no results."
            else:
                return f"Error executing query: {error}\n\nHINT: Check that you're using the exact column names from the schema."
                
        except Exception as e:
            return f"Tool execution error: {str(e)}"

class DatabaseSchemaReaderTool(BaseTool):
    """Tool for reading database schema with exact column names"""
    name: str = Field(default="sql_db_schema")
    description: str = Field(
        default="Get the schema and sample rows for specified tables. Shows EXACT column names (lowercase)."
    )
    db_connection: Any = Field(description="Database connection instance")
    
    def __init__(self, db_connection: Any, **kwargs):
        super().__init__(db_connection=db_connection, **kwargs)
    
    def _run(self, table_names: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get database schema information with exact column names"""
        try:
            if not hasattr(self.db_connection, 'schema_cache') or not self.db_connection.schema_cache:
                return "Schema not loaded. Please ensure database connection is established."
            
            schema = self.db_connection.schema_cache
            
            if not table_names.strip():
                result = "Available tables in the healthcare database:\n\n"
                for table_key, table_info in schema.get("tables", {}).items():
                    table_name = table_info["name"]
                    column_count = len(table_info.get("columns", []))
                    result += f"- {table_name} ({column_count} columns)\n"
                
                result += "\nCRITICAL: PostgreSQL column names are case-sensitive!"
                result += "\nAlways use the EXACT lowercase column names shown in the detailed schema."
                result += "\nUse sql_db_schema with specific table names to get EXACT column names."
                return result
            else:
                requested_tables = [name.strip() for name in table_names.split(",")]
                result = "EXACT COLUMN NAMES (use these EXACTLY in your SQL):\n\n"
                
                for table_key, table_info in schema.get("tables", {}).items():
                    table_name = table_info["name"]
                    
                    if table_name.lower() in [t.lower() for t in requested_tables]:
                        result += f"Table: {table_name}\n"
                        result += "EXACT Column Names (copy these exactly):\n"
                        
                        for col in table_info.get("columns", []):
                            exact_col_name = col['name']
                            col_info = f"  {exact_col_name} ({col['type']})"
                            if not col.get('nullable', True):
                                col_info += " NOT NULL"
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
                    result += "Relationships (use EXACT column names):\n"
                    for rel in relevant_rels:
                        from_col = rel['from_column']
                        to_col = rel['to_column']
                        result += f"  {rel['from_table']}.{from_col} → {rel['to_table']}.{to_col}\n"
                
                result += "\nREMINDER: Copy column names EXACTLY as shown above!"
                return result
                
        except Exception as e:
            return f"Error reading schema: {str(e)}"
    
    async def _arun(self, table_names: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        return self._run(table_names, run_manager)

class DatabaseListTablesTool(BaseTool):
    """Tool for listing all database tables"""
    name: str = Field(default="sql_db_list_tables")
    description: str = Field(
        default="List all tables in the healthcare database with descriptions."
    )
    db_connection: Any = Field(description="Database connection instance")
    
    def __init__(self, db_connection: Any, **kwargs):
        super().__init__(db_connection=db_connection, **kwargs)
    
    def _run(self, query: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """List all database tables"""
        try:
            if not hasattr(self.db_connection, 'schema_cache') or not self.db_connection.schema_cache:
                return "Schema not loaded. Please ensure database connection is established."
            
            schema = self.db_connection.schema_cache
            table_names = [table_info["name"] for table_info in schema.get("tables", {}).values()]
            
            result = "Healthcare Database Tables: " + ", ".join(table_names)
            result += "\n\nKey Healthcare Tables:"
            result += "\n• patients - Patient demographics and personal information"
            result += "\n• conditions - Medical diagnoses and health conditions" 
            result += "\n• medications - Prescribed drugs and treatments"
            result += "\n• procedures - Medical procedures and surgeries"
            result += "\n• encounters - Doctor visits and hospital stays"
            result += "\n• providers - Healthcare professionals and doctors"
            result += "\n• observations - Patient vitals and measurements"
            result += "\n• allergies - Patient allergies and reactions"
            
            result += "\n\nIMPORTANT: Use sql_db_schema to get EXACT column names before writing queries!"
            return result
            
        except Exception as e:
            return f"Error listing tables: {str(e)}"
    
    async def _arun(self, query: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        return self._run(query, run_manager)

class LangGraphReActDatabaseAgent:
    """LangGraph ReAct agent with enhanced prompt and proper async handling"""
    
    def __init__(self, dialect: str = "PostgreSQL", top_k: int = 10):
        self.dialect = dialect
        self.top_k = top_k
        
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            logger.warning("nest_asyncio not available - may have event loop issues")
        
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            deployment_name=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'),
            model=os.getenv('AZURE_OPENAI_MODEL_NAME'),
            temperature=0.0
        )
        
        if DatabaseConnection:
            self.db_connection = DatabaseConnection()
        else:
            raise ImportError("DatabaseConnection not available")
            
        self.schema_description = self._load_schema_description()
        self.tools = self._setup_tools()
        self.system_prompt = self._create_enhanced_system_prompt()
        
        self.agent = create_react_agent(
            self.llm,
            self.tools,
            prompt=self.system_prompt,
        )
    
    def _load_schema_description(self) -> str:
        """Load the database description from description.json"""
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
        """Setup tools for the ReAct agent"""
        return [
            DatabaseListTablesTool(db_connection=self.db_connection),
            DatabaseSchemaReaderTool(db_connection=self.db_connection),
            DatabaseQueryTool(db_connection=self.db_connection)
        ]
    
    def _create_enhanced_system_prompt(self) -> str:
        """Create enhanced system prompt with strict column name requirements"""
        return f"""
# Expert Healthcare Database Analyst – STRICT COLUMN NAME COMPLIANCE

You are a healthcare database analyst using PostgreSQL. Follow these critical rules:

## MANDATORY COLUMN NAME RULES

1. **ALWAYS use `sql_db_schema` FIRST** before any query
2. **COLUMN NAMES MUST BE IN QUOTES AND UPPERCASE**: Use "COLUMN_NAME" format ONLY
3. **NEVER guess column names** - always check schema first
4. **Copy exact names from schema** but convert to UPPERCASE and wrap in quotes

## TOOLS
- `sql_db_list_tables`: List all tables
- `sql_db_schema(<table>)`: Get exact column names (convert to "UPPERCASE")  
- `sql_db_query(<SQL>)`: Execute queries with "COLUMN_NAME" format

## SQL REQUIREMENTS
- **Column format**: Always use "COLUMN_NAME" (uppercase, quoted)
- **Text search**: Use ILIKE for case-insensitive
- **Limit**: Use `LIMIT {self.top_k}` for lists
- **No DML**: SELECT only

{self.schema_description}

## WORKFLOW (ReAct):
1. **THINK**: Understand request
2. **ACT**: `sql_db_list_tables` → `sql_db_schema(table)` → copy names
3. **THINK**: Plan query with "UPPERCASE_COLUMN_NAMES"  
4. **ACT**: Execute SQL with quoted uppercase columns
5. **OBSERVE**: If error, re-check schema

## RESPONSE FORMAT (JSON):
```json
{{
  "success": true|false,
  "message": "Clear explanation",
  "query_understanding": "Request interpretation", 
  "sql_query": "SQL with \\"COLUMN_NAME\\" format",
  "result_count": <number>,
  "results": [...],
  "metadata": {{
    "tables_used": [...],
    "query_type": "type",
    "reasoning": "approach"
  }}
}}
```

## CRITICAL EXAMPLES
- ❌ Wrong: `SELECT condition_name FROM conditions`
- ✅ Correct: `SELECT "CONDITION_NAME" FROM conditions`
- ❌ Wrong: `SELECT "condition_name" FROM conditions`  
- ✅ Correct: `SELECT "CONDITION_NAME" FROM conditions`

## ABSOLUTE REQUIREMENTS
- **NEVER use unquoted column names**
- **NEVER use lowercase in quotes**
- **ALWAYS convert schema names to "UPPERCASE" format**
- **ALWAYS check schema before every query**

You MUST use "UPPERCASE_COLUMN_NAME" format for ALL columns. No exceptions.
"""
    
    async def process_query(self, user_question: str):
        """Process user question with proper async handling"""
        try:
            logger.info(f"Processing query with enhanced ReAct agent: {user_question}")
            
            await self._ensure_ready()
            
            try:
                result = await self.agent.ainvoke({
                    "messages": [("user", user_question)]
                })
            except Exception as agent_error:
                logger.error(f"Agent execution error: {agent_error}")
                return self._create_error_response(user_question, str(agent_error))
            
            return self._parse_agent_response(result, user_question)
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return self._create_error_response(user_question, str(e))
    
    def _create_error_response(self, user_question: str, error_msg: str):
        """Create a structured error response"""
        response_data = {
            "success": False,
            "message": f"I encountered an error while processing your question: {error_msg}",
            "query_understanding": f"Attempted to process: {user_question}",
            "sql_query": None,
            "result_count": 0,
            "results": [],
            "metadata": {
                "error_type": "processing_error",
                "agent_type": "langgraph_react_enhanced"
            }
        }
        
        if DatabaseResponse:
            return DatabaseResponse(**response_data)
        else:
            return response_data
    
    async def _ensure_ready(self):
        """Ensure database connection and schema are ready"""
        connected, error = await self.db_connection.test_connection()
        if not connected:
            raise Exception(f"Database connection failed: {error}")
        
        if not hasattr(self.db_connection, 'schema_cache') or not self.db_connection.schema_cache:
            await self.db_connection.extract_complete_schema()
    
    def _parse_agent_response(self, agent_result: Dict, user_question: str):
        """Parse LangGraph agent response and extract JSON"""
        try:
            messages = agent_result.get("messages", [])
            if not messages:
                raise ValueError("No messages in agent result")
            
            final_message = None
            for msg in reversed(messages):
                if hasattr(msg, 'content') and msg.content:
                    final_message = msg.content
                    break
            
            if not final_message:
                raise ValueError("No final message content found")
            
            logger.info(f"Parsing agent output: {final_message[:200]}...")
            
            parsed_json = self._extract_json_from_text(final_message)
            
            if parsed_json:
                response_data = self._validate_and_enhance_json(parsed_json, user_question)
                if DatabaseResponse:
                    return DatabaseResponse(**response_data)
                else:
                    return response_data
            else:
                return self._create_fallback_response(final_message, user_question)
                
        except Exception as e:
            logger.error(f"Error parsing agent response: {e}")
            return self._create_error_response(user_question, f"Response parsing failed: {str(e)}")
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from text using multiple strategies"""
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
        """Validate and enhance parsed JSON with required fields"""
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
        
        enhanced_json["metadata"]["agent_type"] = "langgraph_react_enhanced"
        enhanced_json["metadata"]["dialect"] = self.dialect
        enhanced_json["metadata"]["top_k_limit"] = self.top_k
        
        return enhanced_json
    
    def _format_results(self, results: List[Any]) -> List[Any]:
        """Format results into QueryResult objects if available"""
        if not QueryResult:
            return results
            
        formatted_results = []
        for item in results:
            if isinstance(item, dict):
                formatted_results.append(QueryResult(data=item))
            else:
                formatted_results.append(QueryResult(data={"value": str(item)}))
        return formatted_results
    
    def _create_fallback_response(self, text: str, user_question: str):
        """Create fallback response when JSON parsing fails"""
        text_lower = text.lower()
        
        success_indicators = ["found", "result", "successful", "query executed", "rows"]
        error_indicators = ["error", "failed", "unable", "cannot", "not found"]
        
        success_score = sum(1 for indicator in success_indicators if indicator in text_lower)
        error_score = sum(1 for indicator in error_indicators if indicator in text_lower)
        
        is_successful = success_score > error_score
        
        sql_match = re.search(r'(SELECT.*?)(?:;|\n|$)', text, re.IGNORECASE | re.DOTALL)
        sql_query = sql_match.group(1).strip() if sql_match else None
        
        numbers = re.findall(r'\b(\d+)\b', text)
        estimated_count = int(numbers[0]) if numbers else 0
        
        response_data = {
            "success": is_successful,
            "message": text[:300] + "..." if len(text) > 300 else text,
            "query_understanding": f"Processed healthcare query: {user_question}",
            "sql_query": sql_query,
            "result_count": estimated_count,
            "metadata": {
                "agent_type": "langgraph_react_enhanced_fallback",
                "success_score": success_score,
                "error_score": error_score,
                "response_type": "text_analysis"
            }
        }
        
        if DatabaseResponse:
            return DatabaseResponse(**response_data)
        else:
            return response_data

AzureReActDatabaseAgent = LangGraphReActDatabaseAgent