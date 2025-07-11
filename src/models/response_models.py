from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json

class QueryResult(BaseModel):
    data: Dict[str, Any] = Field(..., description="Individual record data")
    
    @validator('data', pre=True)
    def validate_data(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {"raw_data": v}
        return v if isinstance(v, dict) else {"value": v}

class TableData(BaseModel):
    headers: List[str] = Field(default_factory=list, description="Table column headers")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Table data as JSON objects")
    row_count: int = Field(0, description="Number of rows in the table")
    
class DatabaseResponse(BaseModel):
    success: bool = Field(..., description="Whether the query was successful")
    message: str = Field(..., description="Human-readable response message")
    query_understanding: str = Field(default="", description="How the AI interpreted the user's question")
    sql_query: Optional[str] = Field(None, description="Generated SQL query")
    result_count: int = Field(0, description="Number of results returned")
    results: List[QueryResult] = Field(default_factory=list, description="Query results")
    table_data: Optional[TableData] = Field(None, description="Structured table data for UI display")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    powered_by: str = Field(default="LangGraph ReAct Agent", description="AI system used")
    
    @validator('results', pre=True)
    def validate_results(cls, v):
        if not v:
            return []
        validated_results = []
        for item in v:
            if isinstance(item, dict):
                validated_results.append(QueryResult(data=item))
            elif hasattr(item, 'data'):
                validated_results.append(item)
            else:
                validated_results.append(QueryResult(data={"value": str(item)}))
        return validated_results
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ReActStep(BaseModel):
    thought: str = Field(..., description="Agent's reasoning")
    action: str = Field(..., description="Action to take")
    action_input: str = Field(..., description="Input for the action")
    observation: str = Field(..., description="Result of the action")

class ReActResponse(BaseModel):
    steps: List[ReActStep] = Field(default_factory=list, description="ReAct reasoning steps")
    final_answer: DatabaseResponse = Field(..., description="Final structured response")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
