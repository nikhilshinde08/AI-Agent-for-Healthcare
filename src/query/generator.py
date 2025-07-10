import os
import re
from typing import Dict, Any, Tuple, Optional, List
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import structlog
from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger(__name__)

class AzureIntelligentQueryGenerator:
    
    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            deployment_name=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'),
            model=os.getenv('AZURE_OPENAI_MODEL_NAME'),
            temperature=0
        )
        self._schema_description = None
    
    async def generate_sql_from_natural_language(self, user_query: str, full_schema: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        try:
            logger.info(f"Analyzing user question with Azure OpenAI: {user_query}")
            
            relevant_data = self._find_relevant_tables_intelligent(user_query, full_schema)
            
            if not relevant_data["tables"]:
                error_msg = "I couldn't find relevant data in the database for your question. Please try asking about different information."
                logger.warning(f"No relevant tables found for: {user_query}")
                return "", error_msg
            
            system_prompt = self._create_enhanced_system_prompt(full_schema, relevant_data)
            user_prompt = self._create_validated_user_prompt(user_query, relevant_data)
            
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            sql_query = self._extract_and_validate_sql_with_schema(response.content, relevant_data)
            
            if sql_query:
                logger.info(f"Generated validated SQL: {sql_query}")
                return sql_query, None
            else:
                error_msg = "I understand your question but couldn't create a proper database query. Please try rephrasing your question."
                logger.error(f"Failed to generate valid SQL for: {user_query}")
                return "", error_msg
                
        except Exception as e:
            error_msg = f"I encountered an error processing your question: {str(e)}"
            logger.error(f"Azure OpenAI error processing query '{user_query}': {str(e)}")
            return "", error_msg
    
    def _find_relevant_tables_intelligent(self, user_query: str, full_schema: Dict[str, Any]) -> Dict[str, Any]:
        query_lower = user_query.lower()
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        
        healthcare_keywords = {
            "patient": ["patients"],
            "condition": ["conditions"], 
            "medication": ["medications"],
            "procedure": ["procedures"],
            "encounter": ["encounters"],
            "provider": ["providers"],
            "allergy": ["allergies"],
            "immunization": ["immunizations"],
            "observation": ["observations"],
            "imaging": ["imaging_studies"],
            "device": ["devices"],
            "careplan": ["careplans"],
            "organization": ["organizations"],
            "payer": ["payers", "payer_transitions"]
        }
        
        relevant_tables = {}
        
        for keyword, table_names in healthcare_keywords.items():
            if keyword in query_words or any(word in query_words for word in [keyword + "s", keyword[:-1]]):
                for table_name in table_names:
                    for table_key, table_info in full_schema.get("tables", {}).items():
                        if table_name.lower() in table_info["name"].lower():
                            relevant_tables[table_key] = table_info
        
        if not relevant_tables:
            table_scores = {}
            
            for table_key, table_info in full_schema.get("tables", {}).items():
                score = 0
                table_name = table_info["name"].lower()
                
                table_words = set(re.findall(r'\b\w+\b', table_name))
                common_words = query_words & table_words
                score += len(common_words) * 5
                
                for column in table_info.get("columns", []):
                    col_name = column["name"].lower()
                    col_words = set(re.findall(r'\b\w+\b', col_name))
                    common_col_words = query_words & col_words
                    score += len(common_col_words) * 2
                
                if score > 0:
                    table_scores[table_key] = {"score": score, "table_info": table_info}
            
            sorted_tables = sorted(table_scores.items(), key=lambda x: x[1]["score"], reverse=True)
            for table_key, data in sorted_tables[:3]:
                relevant_tables[table_key] = data["table_info"]
        
        relevant_relationships = []
        for rel in full_schema.get("relationships", []):
            if any(table_info["name"] in rel["from_table"] or table_info["name"] in rel["to_table"] 
                   for table_info in relevant_tables.values()):
                relevant_relationships.append(rel)
        
        return {
            "tables": relevant_tables,
            "relationships": relevant_relationships
        }
    
    def _create_enhanced_system_prompt(self, full_schema: Dict[str, Any], relevant_data: Dict[str, Any]) -> str:
        
        schema_context = ""
        if self._schema_description:
            schema_context = f"""
HEALTHCARE DATABASE DESCRIPTION:
{self._schema_description}

"""
        
        schema_details = self._format_schema_for_prompt(relevant_data)
        
        return f"""You are an expert SQL assistant specialized in healthcare databases that converts natural language questions into PostgreSQL queries.

{schema_context}AVAILABLE DATABASE SCHEMA:
{schema_details}

CRITICAL POSTGRESQL RULES:
1. **Column names MUST be lowercase** - PostgreSQL is case-sensitive (id, first, last, birthdate, etc.)
2. **Use EXACT table names** from the schema but in lowercase
3. **Use ILIKE for case-insensitive text searches**: WHERE description ILIKE '%heart%'
4. **JOIN syntax**: patients.id = conditions.patient (lowercase column names)
5. **Always use lowercase identifiers** in all SQL statements
6. **LIMIT results to 1000** unless specifically asking for counts
7. **Use COUNT(*) for counting questions**
8. **Use COUNT(DISTINCT column_name) for distinct counts**

HEALTHCARE QUERY PATTERNS:
- Patient queries: SELECT * FROM patients WHERE condition
- Condition searches: JOIN patients with conditions table
- Medication queries: JOIN with medications and conditions
- Provider searches: Query providers table with specialty filters
- Encounter analysis: JOIN encounters with patients
- Demographics: Use patients table with date/location filters

RESPONSE FORMAT:
Generate ONLY a valid PostgreSQL SELECT statement using lowercase column names.
If the query cannot be answered with available tables/columns, return "NO_VALID_QUERY".

EXAMPLES:
- "patients with diabetes" → SELECT p.id, p.first, p.last FROM patients p JOIN conditions c ON p.id = c.patient WHERE c.description ILIKE '%diabetes%' LIMIT 1000;
- "count of patients" → SELECT COUNT(*) as count FROM patients;
- "medications for heart conditions" → SELECT m.description, m.code FROM medications m JOIN conditions c ON m.reasoncode = c.code WHERE c.description ILIKE '%heart%' LIMIT 1000;
"""

    def _format_schema_for_prompt(self, relevant_data: Dict[str, Any]) -> str:
        schema_text = []
        
        for table_key, table_info in relevant_data["tables"].items():
            table_name = table_info["name"]
            schema_text.append(f"\nTable: {table_name}")
            schema_text.append("Columns (use these LOWERCASE names in PostgreSQL):")
            
            for column in table_info.get("columns", []):
                column_name_lower = column['name'].lower()
                column_info = f"  - {column_name_lower} ({column['type']})"
                if not column.get('nullable', True):
                    column_info += " NOT NULL"
                schema_text.append(column_info)
        
        relationships = relevant_data.get("relationships", [])
        if relationships:
            schema_text.append("\nRelationships (use lowercase column names):")
            for relationship in relationships:
                from_table = relationship["from_table"].split(".")[-1]
                to_table = relationship["to_table"].split(".")[-1]
                from_column = relationship['from_column'].lower()
                to_column = relationship['to_column'].lower()
                schema_text.append(f"  - {from_table}.{from_column} → {to_table}.{to_column}")
        
        return "\n".join(schema_text)
    
    def _create_validated_user_prompt(self, user_query: str, relevant_data: Dict[str, Any]) -> str:
        
        available_tables = list(relevant_data["tables"].keys())
        available_columns = []
        
        for table_info in relevant_data["tables"].values():
            table_name = table_info["name"]
            for col in table_info.get("columns", []):
                available_columns.append(f"{table_name}.{col['name'].lower()}")
        
        return f"""User Question: "{user_query}"

Available Tables: {', '.join([info['name'] for info in relevant_data['tables'].values()])}
Available Columns: {', '.join(available_columns[:10])}{'...' if len(available_columns) > 10 else ''}

Task: Convert this healthcare question into a PostgreSQL query using ONLY the tables and columns listed above.
Use lowercase column names and proper PostgreSQL syntax.

If the question cannot be answered with the available schema, respond with "NO_VALID_QUERY".
Otherwise, generate a valid PostgreSQL SELECT statement."""
    
    def _extract_and_validate_sql_with_schema(self, response: str, relevant_data: Dict[str, Any]) -> Optional[str]:
        response = response.strip()
        
        if "NO_VALID_QUERY" in response:
            return None
        
        sql_query = self._extract_sql_from_response(response)
        
        if not sql_query:
            return None
        
        if not self._validate_sql_basics(sql_query):
            return None
        
        if not self._validate_sql_against_schema(sql_query, relevant_data):
            return None
        
        return sql_query
    
    def _extract_sql_from_response(self, response: str) -> Optional[str]:
        
        if "```sql" in response:
            start = response.find("```sql") + 6
            end = response.find("```", start)
            sql_query = response[start:end].strip() if end != -1 else response[start:].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            sql_query = response[start:end].strip() if end != -1 else response[start:].strip()
        else:
            lines = response.split('\n')
            sql_query = None
            for line in lines:
                line = line.strip()
                if line.upper().startswith('SELECT'):
                    sql_query = line
                    break
        
        if sql_query:
            sql_query = sql_query.strip()
            if not sql_query.endswith(';'):
                sql_query += ';'
        
        return sql_query if sql_query else None
    
    def _validate_sql_basics(self, sql_query: str) -> bool:
        if not sql_query:
            return False
        
        sql_upper = sql_query.upper().strip()
        
        if not sql_upper.startswith('SELECT'):
            return False
        
        if 'FROM' not in sql_upper:
            return False
        
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        if any(keyword in sql_upper for keyword in dangerous):
            return False
        
        return True
    
    def _validate_sql_against_schema(self, sql_query: str, relevant_data: Dict[str, Any]) -> bool:
        
        available_tables = {}
        for table_key, table_info in relevant_data["tables"].items():
            table_name = table_info["name"]
            column_names = set(column['name'].lower() for column in table_info.get("columns", []))
            available_tables[table_name.lower()] = column_names
        
        sql_upper = sql_query.upper()
        table_pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        used_tables = re.findall(table_pattern, sql_upper, re.IGNORECASE)
        
        for used_table in used_tables:
            if used_table.lower() not in available_tables:
                return False
        
        qualified_column_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)'
        column_refs = re.findall(qualified_column_pattern, sql_query)
        
        for table_name, column_name in column_refs:
            table_lower = table_name.lower()
            column_lower = column_name.lower()
            
            if table_lower in available_tables:
                if column_lower not in available_tables[table_lower]:
                    return False
            else:
                return False
        
        return True
    
    def validate_query_syntax(self, sql_query: str) -> Tuple[bool, Optional[str]]:
        try:
            if not sql_query:
                return False, "Empty query"
            
            if not self._validate_sql_basics(sql_query):
                return False, "Invalid SQL structure - must be a SELECT statement"
            
            sql_lower = sql_query.lower()
            
            if re.search(r'\b[A-Z][a-zA-Z]*\.[A-Z]', sql_query):
                return False, "Column names should be lowercase for PostgreSQL"
            
            if 'count(' not in sql_lower and 'limit' not in sql_lower:
                logger.warning("Query missing LIMIT clause - performance concern")
            
            return True, None
            
        except Exception as e:
            return False, str(e)
