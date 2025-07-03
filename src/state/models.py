# src/state/models.py
from typing import TypedDict, Dict, Any, Optional, List
from operator import add
from typing_extensions import Annotated

class DatabaseAgentState(TypedDict):
    """Enhanced state model for the database query agent with JSON tracking"""
    
    # Database connection
    db_connected: bool
    connection_error: Optional[str]
    
    # Schema management  
    full_schema: Optional[Dict[str, Any]]
    schema_loaded: bool
    relevant_schema: Optional[Dict[str, Any]]
    
    # User query processing
    user_query: str
    
    # SQL generation and validation
    generated_sql: Optional[str]
    sql_valid: bool
    validation_error: Optional[str]
    
    # Query execution
    query_result: Optional[Any]
    execution_success: bool
    error_code: Optional[int]
    error_message: Optional[str]
    
    # Retry logic
    retry_count: int
    max_retries: int
    
    # Session management
    continue_session: bool
    
    # Current workflow step
    current_step: str
    
    # Enhanced JSON response tracking
    json_response: Dict[str, Any]
    final_json_response: Optional[Dict[str, Any]]
    pydantic_validated_response: Optional[Dict[str, Any]]
    
    # Schema description support
    schema_description: Optional[str]
    
    # Session metadata
    session_summary: Optional[Dict[str, Any]]