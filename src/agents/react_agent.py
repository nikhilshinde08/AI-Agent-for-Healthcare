import json
import re
from typing import Dict, Any, List, Optional
from langchain_cerebras import ChatCerebras
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
    name: str = Field(default="tavily_healthcare_search")
    description: str = Field(
        default="Search for healthcare-related information, medical conditions, treatments, and clinical data using Tavily search engine. Only use for healthcare/medical queries."
    )
    api_key: str = Field(description="Tavily API key")
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
    
    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            healthcare_query = self._enhance_healthcare_query(query)
            
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
        try:
            healthcare_query = self._enhance_healthcare_query(query)
            return await self._search_tavily(healthcare_query)
        except Exception as e:
            return f"❌ Healthcare search error: {str(e)}"
    
    def _enhance_healthcare_query(self, query: str) -> str:
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
        
        enhanced_query += " site:nih.gov OR site:mayoclinic.org OR site:webmd.com OR site:who.int OR site:cdc.gov OR site:pubmed.ncbi.nlm.nih.gov"
        
        return enhanced_query
    
    async def _search_tavily(self, query: str) -> str:
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
                        search_results = await response.json()
                        return self._format_healthcare_search_results(search_results, query)
                    else:
                        error_text = await response.text()
                        return f"❌ Tavily API error (status {response.status}): {error_text}"
        
        except aiohttp.ClientError as network_error:
            return f"❌ Network error connecting to Tavily: {str(network_error)}"
        except Exception as unexpected_error:
            return f"❌ Unexpected error during healthcare search: {str(unexpected_error)}"
    
    def _format_healthcare_search_results(self, search_results: Dict, original_query: str) -> str:
        try:
            results = search_results.get("results", [])
            answer = search_results.get("answer", "")
            
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
    name: str = Field(default="sql_db_query")
    description: str = Field(
        default="Execute a SQL query against the database. Returns structured data that should be interpreted for the user."
    )
    db_connection: Any = Field(description="Database connection instance")
    
    def __init__(self, db_connection: Any, **kwargs):
        super().__init__(db_connection=db_connection, **kwargs)
    
    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        try:
            try:
                loop = asyncio.get_running_loop()
                import nest_asyncio
                nest_asyncio.apply()
                success, query_results, error, status_code = loop.run_until_complete(
                    self.db_connection.execute_query(query)
                )
            except RuntimeError:
                success, query_results, error, status_code = asyncio.run(
                    self.db_connection.execute_query(query)
                )
            
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
                return f"❌ Error executing query: {error}\n\nPlease check the column names and table structure, then try again with corrected SQL."
                
        except Exception as e:
            return f"⚠️ Tool execution error: {str(e)}\n\nPlease revise the query and try again."
    
    async def _arun(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
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
    name: str = Field(default="sql_db_schema")
    description: str = Field(
        default="Get the schema and sample rows for specified tables. Shows exact column names and structure."
    )
    db_connection: Any = Field(description="Database connection instance")
    
    def __init__(self, db_connection: Any, **kwargs):
        super().__init__(db_connection=db_connection, **kwargs)
    
    def _run(self, table_names: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
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
        return self._run(table_names, run_manager)

class DatabaseListTablesTool(BaseTool):
    name: str = Field(default="sql_db_list_tables")
    description: str = Field(
        default="List all tables in the healthcare database with descriptions."
    )
    db_connection: Any = Field(description="Database connection instance")
    
    def __init__(self, db_connection: Any, **kwargs):
        super().__init__(db_connection=db_connection, **kwargs)
    
    def _run(self, query: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
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
    
    def __init__(self, dialect: str = "PostgreSQL", top_k: int = 10):
        self.dialect = dialect
        self.top_k = top_k
        
        try:
            import nest_asyncio
            import asyncio
            
            # Check if we're using uvloop (which doesn't support nest_asyncio)
            try:
                current_loop = asyncio.get_running_loop()
                loop_type = type(current_loop).__name__
                if 'uvloop' in loop_type.lower():
                    logger.info("Using uvloop, skipping nest_asyncio.apply()")
                else:
                    nest_asyncio.apply()
            except RuntimeError:
                # No event loop running, safe to apply nest_asyncio
                nest_asyncio.apply()
        except ImportError:
            logger.warning("nest_asyncio not available - may have event loop issues")
        except Exception as e:
            logger.warning(f"Could not apply nest_asyncio: {e}")
        
        self.llm = ChatCerebras(
        api_key=os.getenv('CEREBRAS_API_KEY'),
        model="llama-4-scout-17b-16e-instruct",
        temperature=0)

        
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
    
    def _load_schema_description(self) -> str:
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
        tools = [
            DatabaseListTablesTool(db_connection=self.db_connection),
            DatabaseSchemaReaderTool(db_connection=self.db_connection),
            DatabaseQueryTool(db_connection=self.db_connection)
        ]
        
        if self.tavily_api_key:
            tools.append(TavilyHealthcareSearchTool(api_key=self.tavily_api_key))
            logger.info("Tavily healthcare search tool added")
        else:
            logger.warning("Tavily API key not available - healthcare search disabled")
        
        return tools
    
    def _create_enhanced_system_prompt(self) -> str:
        tavily_guidance = ""
        if self.tavily_api_key:
            tavily_guidance = """

🔍 **Healthcare Information Search Tool:**
- WHEN TO USE: External medical information, treatment guidelines, clinical knowledge, or disease explanations
- TRUSTED SOURCES: NIH, Mayo Clinic, WebMD, WHO, CDC, PubMed
- PURPOSE: Supplement database queries with medical context and provide evidence-based healthcare information
- PRIORITY: Always query database first for patient-specific data, then use Tavily for general medical knowledge
- OUTPUT: Provide concise, factual medical information without disclaimers
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
- The ouput should be in 1 line  not more than that in json format
- Always provide natural language interpretations 
- Explain results in everyday language
- Combine database results with relevant medical context when helpful
- Prioritize patient privacy and data security
- Do not add any guideline related line which says always consult a doctor


Remember: Database queries for patient data, Tavily search for medical knowledge and context. 
"""


    
    async def process_query(self, user_question: str, conversation_context: str = None):
        try:
            logger.info(f"Processing query with enhanced ReAct agent: {user_question}")
            
            await self._ensure_ready()
            
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
        connected, error = await self.db_connection.test_connection()
        if not connected:
            raise Exception(f"Database connection failed: {error}")
        
        if not hasattr(self.db_connection, 'schema_cache') or not self.db_connection.schema_cache:
            await self.db_connection.extract_complete_schema()
    
    def _parse_agent_response(self, agent_result: Dict, user_question: str):
        try:
            messages = agent_result.get("messages", [])
            if not messages:
                raise ValueError("No messages in agent result")
            
            final_message = None
            for msg in reversed(messages):
                if hasattr(msg, 'content') and msg.content and hasattr(msg, 'type') and msg.type == 'ai':
                    final_message = msg.content
                    break
            
            if not final_message:
                for msg in reversed(messages):
                    if hasattr(msg, 'content') and msg.content:
                        final_message = msg.content
                        break
            
            if not final_message:
                raise ValueError("No final message content found")
            
            logger.info(f"Processing agent output: {final_message[:200]}...")
            
            parsed_json = self._extract_json_from_text(final_message)
            
            if parsed_json:
                if parsed_json.get("message") and not self._is_just_raw_data(parsed_json["message"]):
                    response_data = self._validate_and_enhance_json(parsed_json, user_question)
                else:
                    response_data = self._enhance_with_natural_language(parsed_json, final_message, user_question)
            else:
                response_data = self._create_response_from_text(final_message, user_question)
            
            if DatabaseResponse:
                return DatabaseResponse(**response_data)
            else:
                return response_data
                
        except Exception as e:
            logger.error(f"Error parsing agent response: {e}")
            return self._create_error_response(user_question, f"Response parsing failed: {str(e)}")
    
    def _is_just_raw_data(self, message: str) -> bool:
        raw_indicators = [
            message.strip().isdigit(),
            message.count('\n') == 0 and ',' in message and len(message.split(',')) > 2,
            message.startswith('[') and message.endswith(']'),
            len(message.split()) < 5 and any(char.isdigit() for char in message)
        ]
        return any(raw_indicators)
    
    def _enhance_with_natural_language(self, parsed_json: Dict, original_text: str, user_question: str) -> Dict[str, Any]:
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
        result_count = data.get("result_count", 0)
        results = data.get("results", [])
        
        if "count" in user_question.lower() or "how many" in user_question.lower():
            if result_count == 1 and results:
                count_value = str(results[0]).strip('{}[](),')
                return f"Found {count_value} records."
            else:
                return f"Found {result_count} records."
        
        elif result_count == 0:
            return "No records found."
        
        elif result_count == 1:
            return f"Found 1 record: {results[0] if results else 'Details unavailable'}"
        
        else:
            return f"Found {result_count} records. Top results: {', '.join(str(r) for r in results[:2])}{'...' if len(results) > 2 else ''}"
    
    def _create_response_from_text(self, text: str, user_question: str) -> Dict[str, Any]:
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
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
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

AzureReActDatabaseAgent = LangGraphReActDatabaseAgent