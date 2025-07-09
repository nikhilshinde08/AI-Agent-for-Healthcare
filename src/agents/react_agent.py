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
import aiohttp

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

class TavilyHealthcareSearchTool(BaseTool):
    """Tool for searching healthcare-related information using Tavily API"""
    name: str = Field(default="tavily_healthcare_search")
    description: str = Field(
        default="Search for healthcare-related information, medical conditions, treatments, and clinical data using Tavily search engine. Only use for healthcare/medical queries."
    )
    api_key: str = Field(description="Tavily API key")
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
    
    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute healthcare search using Tavily API"""
        try:
            # Enhance query with healthcare context
            healthcare_query = self._enhance_healthcare_query(query)
            
            # Use asyncio to run the async search
            try:
                loop = asyncio.get_running_loop()
                import nest_asyncio
                nest_asyncio.apply()
                result = loop.run_until_complete(self._search_tavily(healthcare_query))
            except RuntimeError:
                result = asyncio.run(self._search_tavily(healthcare_query))
            
            return result
            
        except Exception as e:
            return f"❌ Healthcare search error: {str(e)}\n\nPlease try rephrasing your healthcare query."
    
    async def _arun(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Async version of healthcare search"""
        try:
            healthcare_query = self._enhance_healthcare_query(query)
            return await self._search_tavily(healthcare_query)
        except Exception as e:
            return f"❌ Healthcare search error: {str(e)}"
    
    def _enhance_healthcare_query(self, query: str) -> str:
        """Enhance query with healthcare-specific terms and filters"""
        # Add healthcare context if not already present
        healthcare_keywords = [
            'medical', 'health', 'disease', 'condition', 'treatment', 'therapy',
            'diagnosis', 'symptom', 'medication', 'drug', 'clinical', 'patient',
            'hospital', 'doctor', 'physician', 'nurse', 'healthcare', 'medicine'
        ]
        
        query_lower = query.lower()
        has_healthcare_context = any(keyword in query_lower for keyword in healthcare_keywords)
        
        if not has_healthcare_context:
            # Add healthcare context to the query
            enhanced_query = f"healthcare medical {query}"
        else:
            enhanced_query = query
        
        # Add filters for healthcare-specific sources
        enhanced_query += " site:nih.gov OR site:mayoclinic.org OR site:webmd.com OR site:who.int OR site:cdc.gov OR site:pubmed.ncbi.nlm.nih.gov"
        
        return enhanced_query
    
    async def _search_tavily(self, query: str) -> str:
        """Perform the actual Tavily search"""
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
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_healthcare_search_results(data, query)
                    else:
                        error_text = await response.text()
                        return f"❌ Tavily API error (status {response.status}): {error_text}"
        
        except aiohttp.ClientError as e:
            return f"❌ Network error connecting to Tavily: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected error during healthcare search: {str(e)}"
    
    def _format_healthcare_search_results(self, data: Dict, original_query: str) -> str:
        """Format Tavily search results for healthcare context"""
        try:
            results = data.get("results", [])
            answer = data.get("answer", "")
            
            if not results and not answer:
                return f"🔍 No healthcare information found for: {original_query}\n\nTry rephrasing your medical query or being more specific about the condition or treatment."
            
            formatted_result = f"🏥 Healthcare Information Search Results for: {original_query}\n\n"
            
            # Include AI-generated answer if available
            if answer:
                formatted_result += f"📋 Medical Summary:\n{answer}\n\n"
            
            # Include top search results
            if results:
                formatted_result += "🔍 Trusted Healthcare Sources:\n"
                for i, result in enumerate(results[:3], 1):
                    title = result.get("title", "No title")
                    url = result.get("url", "No URL")
                    content = result.get("content", "No content available")
                    
                    # Truncate content for readability
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
    """Tool for executing SQL queries with proper async handling"""
    name: str = Field(default="sql_db_query")
    description: str = Field(
        default="Execute a SQL query against the database. Returns structured data that should be interpreted for the user."
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
                    # Format the results in a structured way for the LLM to interpret
                    result_str = f"✅ Query executed successfully!\n"
                    result_str += f"📊 Found {len(data)} record(s)\n"
                    result_str += f"🔍 Query: {query}\n\n"
                    
                    if isinstance(data[0], dict):
                        headers = list(data[0].keys())
                        result_str += f"📋 Columns: {', '.join(headers)}\n\n"
                        
                        # Show sample data
                        result_str += "📄 Sample Results:\n"
                        for i, row in enumerate(data[:5], 1):
                            result_str += f"  Row {i}: {', '.join(f'{k}={v}' for k, v in row.items())}\n"
                        
                        if len(data) > 5:
                            result_str += f"  ... and {len(data) - 5} more rows\n"
                    else:
                        result_str += f"📄 Results: {data}\n"
                    
                    result_str += f"\n✨ Please provide a natural language interpretation of these results to answer the user's question."
                    return result_str
                else:
                    return "✅ Query executed successfully but returned no results. Please inform the user that no matching records were found."
            else:
                return f"❌ Error executing query: {error}\n\nPlease check the column names and table structure, then try again with corrected SQL."
                
        except Exception as e:
            return f"⚠️ Tool execution error: {str(e)}\n\nPlease revise the query and try again."
    
    async def _arun(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Async version"""
        try:
            success, data, error, status_code = await self.db_connection.execute_query(query)
            
            if success:
                if data:
                    result_str = f"✅ Query executed successfully!\n"
                    result_str += f"📊 Found {len(data)} record(s)\n"
                    result_str += f"🔍 Query: {query}\n\n"
                    
                    if isinstance(data[0], dict):
                        headers = list(data[0].keys())
                        result_str += f"📋 Columns: {', '.join(headers)}\n\n"
                        
                        result_str += "📄 Sample Results:\n"
                        for i, row in enumerate(data[:5], 1):
                            result_str += f"  Row {i}: {', '.join(f'{k}={v}' for k, v in row.items())}\n"
                        
                        if len(data) > 5:
                            result_str += f"  ... and {len(data) - 5} more rows\n"
                    else:
                        result_str += f"📄 Results: {data}\n"
                    
                    result_str += f"\n✨ Please provide a natural language interpretation of these results to answer the user's question."
                    return result_str
                else:
                    return "✅ Query executed successfully but returned no results. Please inform the user that no matching records were found."
            else:
                return f"❌ Error executing query: {error}\n\nPlease check the column names and table structure."
                
        except Exception as e:
            return f"⚠️ Tool execution error: {str(e)}"

class DatabaseSchemaReaderTool(BaseTool):
    """Tool for reading database schema with exact column names"""
    name: str = Field(default="sql_db_schema")
    description: str = Field(
        default="Get the schema and sample rows for specified tables. Shows exact column names and structure."
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
                
                # Add relationships if any
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
        return self._run(query, run_manager)

class LangGraphReActDatabaseAgent:
    """Enhanced LangGraph ReAct agent with Tavily healthcare search integration"""
    
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
            temperature=0.1  # Slightly higher for more natural responses
        )
        
        if DatabaseConnection:
            self.db_connection = DatabaseConnection()
        else:
            raise ImportError("DatabaseConnection not available")
        
        # Get Tavily API key from environment
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
        """Setup tools for the ReAct agent including Tavily search"""
        tools = [
            DatabaseListTablesTool(db_connection=self.db_connection),
            DatabaseSchemaReaderTool(db_connection=self.db_connection),
            DatabaseQueryTool(db_connection=self.db_connection)
        ]
        
        # Add Tavily search tool if API key is available
        if self.tavily_api_key:
            tools.append(TavilyHealthcareSearchTool(api_key=self.tavily_api_key))
            logger.info("Tavily healthcare search tool added")
        else:
            logger.warning("Tavily API key not available - healthcare search disabled")
        
        return tools
    
    def _create_enhanced_system_prompt(self) -> str:
        """Create enhanced system prompt that includes Tavily search guidance"""
        tavily_guidance = ""
        if self.tavily_api_key:
            tavily_guidance = """
            
🔍 **Healthcare Information Search:**
- Use tavily_healthcare_search when you need external medical information, treatment guidelines, or clinical knowledge
- This tool searches trusted healthcare sources like NIH, Mayo Clinic, WebMD, WHO, and CDC
- Use it to supplement database queries with medical context, explain conditions, or provide treatment information
- Always prioritize database queries for patient-specific data, then use Tavily for general healthcare information
- Always ensure you give consised answers 1 line.
"""
        
        return f"""You are a healthcare database assistant with access to both patient data and external medical information.

**Database Context:**
{self.schema_description}

**Query Guidelines:**
- Generate SQL queries that join necessary tables for meaningful results
- Return top {self.top_k} results based on relevance
- Include personal information (name, contact) but exclude sensitive data (ethnicity, SSN, financial)
- Use uppercase column names with double quotes: "COLUMN_NAME"
- Match names with iLIKE 'Name%' for prefix matching
- Follow privacy best practices

**Tool Usage Strategy:**
1. **Database Tools** (for patient-specific data):
   - sql_db_list_tables: See available tables
   - sql_db_schema: Get exact column names
   - sql_db_query: Execute SQL queries

2. **Healthcare Search** (for medical information):{tavily_guidance}

**Response Format:**
- Always provide natural language interpretations
- Explain results in everyday language
- Combine database results with relevant medical context when helpful
- Prioritize patient privacy and data security
-Do not add any guideline related line which says always consult a doctor


Remember: Database queries for patient data, Tavily search for medical knowledge and context. 
"""
    
    async def process_query(self, user_question: str, conversation_context: str = None):
        """Process user question with enhanced natural language response generation"""
        try:
            logger.info(f"Processing query with enhanced ReAct agent: {user_question}")
            
            await self._ensure_ready()
            
            # Enhanced prompt to encourage natural language responses
            enhanced_question = f"""
User Question: {user_question}

Please help the user by:
1. Understanding what they're asking for
2. Using the appropriate tools (database for patient data, Tavily for medical information)
3. **MOST IMPORTANTLY**: Providing a clear, natural language explanation of the results

When appropriate, combine patient data from the database with relevant medical context from healthcare sources.

Remember to always interpret the data and explain what it means in everyday language, not just raw numbers or query results.

{f"Previous conversation context: {conversation_context}" if conversation_context else ""}
"""
            
            try:
                result = await self.agent.ainvoke({
                    "messages": [("user", enhanced_question)]
                })
            except Exception as agent_error:
                logger.error(f"Agent execution error: {agent_error}")
                return self._create_error_response(user_question, str(agent_error))
            
            return self._parse_agent_response(result, user_question)
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return self._create_error_response(user_question, str(e))
    
    async def _ensure_ready(self):
        """Ensure database connection and schema are ready"""
        connected, error = await self.db_connection.test_connection()
        if not connected:
            raise Exception(f"Database connection failed: {error}")
        
        if not hasattr(self.db_connection, 'schema_cache') or not self.db_connection.schema_cache:
            await self.db_connection.extract_complete_schema()
    
    def _parse_agent_response(self, agent_result: Dict, user_question: str):
        """Parse LangGraph agent response and ensure natural language output"""
        try:
            messages = agent_result.get("messages", [])
            if not messages:
                raise ValueError("No messages in agent result")
            
            # Get the final AI message
            final_message = None
            for msg in reversed(messages):
                if hasattr(msg, 'content') and msg.content and hasattr(msg, 'type') and msg.type == 'ai':
                    final_message = msg.content
                    break
            
            if not final_message:
                # Fallback to any contentG
                for msg in reversed(messages):
                    if hasattr(msg, 'content') and msg.content:
                        final_message = msg.content
                        break
            
            if not final_message:
                raise ValueError("No final message content found")
            
            logger.info(f"Processing agent output: {final_message[:200]}...")
            
            # Try to extract JSON, but prioritize natural language response
            parsed_json = self._extract_json_from_text(final_message)
            
            if parsed_json:
                # Ensure the message contains natural language interpretation
                if parsed_json.get("message") and not self._is_just_raw_data(parsed_json["message"]):
                    response_data = self._validate_and_enhance_json(parsed_json, user_question)
                else:
                    # Generate natural language interpretation if missing
                    response_data = self._enhance_with_natural_language(parsed_json, final_message, user_question)
            else:
                # If no JSON found, create response from the natural language text
                response_data = self._create_response_from_text(final_message, user_question)
            
            if DatabaseResponse:
                return DatabaseResponse(**response_data)
            else:
                return response_data
                
        except Exception as e:
            logger.error(f"Error parsing agent response: {e}")
            return self._create_error_response(user_question, f"Response parsing failed: {str(e)}")
    
    def _is_just_raw_data(self, message: str) -> bool:
        """Check if message is just raw data without interpretation"""
        raw_indicators = [
            message.strip().isdigit(),  # Just a number
            message.count('\n') == 0 and ',' in message and len(message.split(',')) > 2,  # CSV-like
            message.startswith('[') and message.endswith(']'),  # Array format
            len(message.split()) < 5 and any(char.isdigit() for char in message)  # Very short with numbers
        ]
        return any(raw_indicators)
    
    def _enhance_with_natural_language(self, parsed_json: Dict, original_text: str, user_question: str) -> Dict[str, Any]:
        """Enhance JSON response with natural language interpretation"""
        # Extract meaningful parts from the original text
        text_parts = original_text.split('\n')
        natural_language_parts = []
        
        for part in text_parts:
            # Skip JSON blocks and tool calls
            if not (part.strip().startswith('{') or part.strip().startswith('```') or 
                   'sql_db_' in part.lower() or 'tavily_' in part.lower() or 
                   part.strip().startswith('Thought:')):
                if len(part.strip()) > 10:  # Only meaningful text
                    natural_language_parts.append(part.strip())
        
        # Create natural language interpretation
        if natural_language_parts:
            natural_message = ' '.join(natural_language_parts)
        else:
            # Generate interpretation based on results
            natural_message = self._generate_interpretation(parsed_json, user_question)
        
        parsed_json["message"] = natural_message
        return self._validate_and_enhance_json(parsed_json, user_question)
    
    def _generate_interpretation(self, data: Dict, user_question: str) -> str:
        """Generate natural language interpretation of query results"""
        result_count = data.get("result_count", 0)
        results = data.get("results", [])
        
        # Generate context-appropriate response
        if "count" in user_question.lower() or "how many" in user_question.lower():
            if result_count == 1 and results:
                # Likely a count query
                count_value = str(results[0]).strip('{}[](),')
                return f"Based on the current data, there are {count_value} records that match your query."
            else:
                return f"I found {result_count} records in response to your question."
        
        elif result_count == 0:
            return "I didn't find any records matching your criteria in the database."
        
        elif result_count == 1:
            return f"I found 1 record that matches your query. Here are the details: {results[0] if results else 'No details available'}"
        
        else:
            return f"I found {result_count} records that match your query. Here are the results: {', '.join(str(r) for r in results[:3])}{'...' if len(results) > 3 else ''}"
    
    def _create_response_from_text(self, text: str, user_question: str) -> Dict[str, Any]:
        """Create response structure from natural language text"""
        # Extract any numbers that might indicate results
        numbers = re.findall(r'\b(\d+)\b', text)
        estimated_count = int(numbers[0]) if numbers else 0
        
        # Extract SQL if present
        sql_match = re.search(r'(SELECT.*?)(?:;|\n|$)', text, re.IGNORECASE | re.DOTALL)
        sql_query = sql_match.group(1).strip() if sql_match else None
        
        # Determine success
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
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from text using multiple strategies"""
        # Try JSON code blocks first
        json_block_match = re.search(r'```json\n?(.*?)\n?```', text, re.DOTALL | re.IGNORECASE)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # Try finding JSON objects
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
        
        # Ensure success is boolean
        if isinstance(enhanced_json["success"], str):
            enhanced_json["success"] = enhanced_json["success"].lower() in ["true", "yes", "success"]
        
        # Ensure result_count is integer
        if not isinstance(enhanced_json["result_count"], int):
            try:
                enhanced_json["result_count"] = int(enhanced_json["result_count"])
            except (ValueError, TypeError):
                enhanced_json["result_count"] = len(enhanced_json["results"])
        
        # Enhance metadata
        enhanced_json["metadata"]["agent_type"] = "langgraph_react_enhanced_natural_with_tavily"
        enhanced_json["metadata"]["dialect"] = self.dialect
        enhanced_json["metadata"]["top_k_limit"] = self.top_k
        enhanced_json["metadata"]["response_enhanced"] = True
        enhanced_json["metadata"]["tavily_enabled"] = bool(self.tavily_api_key)
        
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
    
    def _create_error_response(self, user_question: str, error_msg: str):
        """Create a structured error response"""
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

# Backward compatibility alias
AzureReActDatabaseAgent = LangGraphReActDatabaseAgent