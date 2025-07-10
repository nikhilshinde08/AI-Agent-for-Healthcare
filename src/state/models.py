from typing import TypedDict, Dict, Any, Optional, List
from operator import add
from typing_extensions import Annotated

class DatabaseAgentState(TypedDict):
    
    db_connected: bool
    connection_error: Optional[str]
    
    full_schema: Optional[Dict[str, Any]]
    schema_loaded: bool
    relevant_schema: Optional[Dict[str, Any]]
    
    user_query: str
    
    generated_sql: Optional[str]
    sql_valid: bool
    validation_error: Optional[str]
    
    query_result: Optional[Any]
    execution_success: bool
    error_code: Optional[int]
    error_message: Optional[str]
    
    retry_count: int
    max_retries: int
    
    continue_session: bool
    
    current_step: str
    
    json_response: Dict[str, Any]
    final_json_response: Optional[Dict[str, Any]]
    pydantic_validated_response: Optional[Dict[str, Any]]
    
    schema_description: Optional[str]
    
    session_summary: Optional[Dict[str, Any]]