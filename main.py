# main.py - Simplified ReAct Only Version
import asyncio
import json
import os
import sys
from datetime import datetime
import uuid

# Add src to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    import structlog
    
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logger = structlog.get_logger(__name__)
except ImportError:
    print("Warning: structlog not available, using basic logging")
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

def save_json_response(response, query, session_id):
    """Simple JSON saver function"""
    try:
        # Create directory
        output_dir = "json_responses"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Create filename
        timestamp = datetime.now()
        date_str = timestamp.strftime("%Y%m%d_%H%M%S")
        clean_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_query = clean_query.replace(' ', '_')[:30]
        
        filename = f"{date_str}_{clean_query}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Enhanced response with metadata
        enhanced_response = {
            "query_metadata": {
                "original_query": query,
                "timestamp": timestamp.isoformat(),
                "session_id": session_id,
                "filename": filename
            },
            "response": response
        }
        
        # Save file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(enhanced_response, f, indent=2, default=str, ensure_ascii=False)
        
        return filepath
    except Exception as e:
        print(f"❌ JSON save failed: {e}")
        return None

async def react_agent_cli():
    """CLI using only ReAct Agent"""
    
    print("\n" + "="*80)
    print("🤖 REACT DATABASE ASSISTANT")
    print("⚡ Using LangGraph ReAct Agent Only")
    print("💾 Healthcare-focused with JSON Output")
    print("🔄 Think → Act → Observe Pattern")
    print("="*80)
    
    # Generate session ID
    session_id = f"react_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"📋 Session ID: {session_id}")
    
    # Check for description.json
    try:
        with open("description.json", 'r', encoding='utf-8') as f:
            schema_description = f.read().strip()
            print(f"✅ Loaded database description ({len(schema_description)} characters)")
    except:
        print("⚠️  description.json not found - will use default healthcare context")
    
    print("\n🔧 Initializing ReAct Agent...")
    
    try:
        from agents.db_agent import AzureReActDatabaseAgent
        
        # Initialize the simplified ReAct agent
        agent = AzureReActDatabaseAgent()
        
        print("✅ ReAct Agent ready!")
        print("🔧 Agent Configuration:")
        print(f"   • Database: PostgreSQL")
        print(f"   • Result Limit: 10 records")
        print(f"   • Agent Type: LangGraph ReAct")
        
    except Exception as e:
        print(f"❌ Failed to initialize ReAct Agent: {e}")
        print("\n💡 Make sure you have:")
        print("   • langgraph installed: pip install langgraph")
        print("   • Azure OpenAI credentials configured")
        print("   • Database connection available")
        return
    
    print("\n🏥 Healthcare Database Capabilities:")
    print("   • Smart table and schema discovery")
    print("   • Automatic query optimization")
    print("   • Healthcare domain expertise")
    print("   • Error detection and retry logic")
    
    print("\n💬 Example Healthcare Questions:")
    print("   • 'How many patients do we have?'")
    print("   • 'Show me patients with diabetes'")
    print("   • 'What are the most common medical conditions?'")
    print("   • 'List medications prescribed for hypertension'")
    print("   • 'Find patients born after 1990'")
    
    print("\n🔄 ReAct Process:")
    print("   1. 🤔 THINK: Understand your question")
    print("   2. 📋 ACT: Explore database tables and schema")  
    print("   3. 🔍 ACT: Generate and execute SQL query")
    print("   4. 📊 OBSERVE: Analyze results and format response")
    
    print("\n" + "-"*80)
    print("Type 'exit', 'help', or ask your healthcare question")
    print("-"*80)
    
    session_responses = []
    session_count = 0
    
    while True:
        try:
            user_input = input(f"\n💬 [ReAct Agent] Ask about your data: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q', 'bye']:
                # Save session summary
                if session_responses:
                    try:
                        session_file = f"json_responses/session_{session_id}_summary.json"
                        os.makedirs("json_responses", exist_ok=True)
                        session_data = {
                            "session_metadata": {
                                "session_id": session_id,
                                "agent_type": "react_only",
                                "total_queries": len(session_responses),
                                "successful_queries": sum(1 for r in session_responses if r.get("response", {}).get("success", False)),
                                "created_at": datetime.now().isoformat()
                            },
                            "responses": session_responses
                        }
                        with open(session_file, 'w', encoding='utf-8') as f:
                            json.dump(session_data, f, indent=2, default=str)
                        print(f"💾 Session saved: {os.path.basename(session_file)}")
                    except Exception as e:
                        print(f"⚠️  Could not save session: {e}")
                
                print(f"\n👋 Thank you! ReAct Agent processed {len(session_responses)} queries")
                break
            
            if user_input.lower() in ['help', 'h']:
                print_react_help()
                continue
            
            if not user_input:
                print("💭 Please ask a question about your healthcare data!")
                continue
            
            session_count += 1
            print(f"\n🧠 ReAct Agent is processing...")
            print("🔄 Following Think → Act → Observe pattern...")
            
            try:
                # Record start time
                start_time = datetime.now()
                
                # Process with ReAct agent
                response = await agent.answer_question(user_input, session_id)
                
                # Record processing time
                processing_time = (datetime.now() - start_time).total_seconds()
                
                # Add processing metadata
                if "metadata" not in response:
                    response["metadata"] = {}
                response["metadata"]["processing_time_seconds"] = processing_time
                response["metadata"]["session_id"] = session_id
                response["metadata"]["query_number"] = session_count
                response["metadata"]["agent_type"] = "react_only"
                
                # Save JSON response
                json_file = save_json_response(response, user_input, session_id)
                
                # Add to session responses
                session_responses.append({
                    "query": user_input,
                    "response": response,
                    "timestamp": start_time.isoformat(),
                    "processing_time": processing_time
                })
                
                # Display results
                display_react_results(response, session_count, json_file, processing_time)
                
            except Exception as e:
                error_response = {
                    "success": False,
                    "answer": f"Error processing question: {str(e)}",
                    "query_understanding": user_input,
                    "sql_generated": None,
                    "result_count": 0,
                    "data": [],
                    "metadata": {
                        "error_type": type(e).__name__,
                        "session_id": session_id,
                        "query_number": session_count,
                        "agent_type": "react_only"
                    }
                }
                
                # Save error response
                json_file = save_json_response(error_response, user_input, session_id)
                session_responses.append({
                    "query": user_input,
                    "response": error_response,
                    "timestamp": datetime.now().isoformat(),
                    "error": True
                })
                
                print(f"\n❌ Error: {str(e)}")
                print("💡 The agent will learn from this error and improve")
                
        except KeyboardInterrupt:
            print("\n👋 ReAct session ended!")
            break

def display_react_results(response: dict, session_count: int, json_file: str = None, processing_time: float = 0):
    """Display ReAct results with enhanced formatting"""
    
    print(f"\n{'='*70}")
    print(f"📊 QUERY {session_count} - REACT AGENT RESULTS")
    print("="*70)
    
    # Status with processing time
    status_icon = "✅" if response.get("success") else "❌"
    status_text = "SUCCESS" if response.get("success") else "ERROR"
    print(f"{status_icon} STATUS: {status_text}")
    print(f"⏱️  PROCESSING TIME: {processing_time:.2f}s")
    
    # JSON file info
    if json_file:
        print(f"💾 JSON SAVED: {os.path.basename(json_file)}")
    
    # Agent understanding
    if response.get("query_understanding"):
        print(f"🧠 AGENT UNDERSTANDING: {response['query_understanding']}")
    
    # Main answer
    if response.get("answer"):
        print(f"💬 ANSWER: {response['answer']}")
    
    # SQL query with formatting
    if response.get("sql_generated"):
        print(f"\n🔧 GENERATED SQL:")
        sql = response['sql_generated']
        # Pretty print SQL
        sql_formatted = sql.replace('SELECT', '\nSELECT').replace('FROM', '\nFROM').replace('WHERE', '\nWHERE').replace('JOIN', '\nJOIN')
        print(f"   {sql_formatted}")
    
    # Results display
    if response.get("success") and response.get("data"):
        results = response["data"]
        result_count = response.get("result_count", len(results))
        
        print(f"\n📊 RESULTS ({result_count} found):")
        print("-" * 50)
        
        # Display results
        for i, result in enumerate(results[:5], 1):  # Show first 5
            print(f"\n   Result {i}:")
            
            if isinstance(result, dict):
                for key, value in result.items():
                    display_value = str(value)
                    if len(display_value) > 50:
                        display_value = display_value[:47] + "..."
                    print(f"      {key}: {display_value}")
            else:
                print(f"      {result}")
        
        if len(results) > 5:
            print(f"\n   ... and {len(results) - 5} more results")
        
        # Show metadata insights
        metadata = response.get("metadata", {})
        if metadata:
            print(f"\n🔍 AGENT INSIGHTS:")
            if "tables_used" in metadata:
                print(f"   Tables accessed: {', '.join(metadata['tables_used'])}")
            if "query_type" in metadata:
                print(f"   Query type: {metadata['query_type']}")
            if "reasoning" in metadata:
                print(f"   Reasoning: {metadata['reasoning']}")
    
    elif not response.get("success"):
        print(f"\n❌ QUERY FAILED")
        if response.get("metadata", {}).get("error_type"):
            print(f"   Error type: {response['metadata']['error_type']}")
    
    # Agent info
    print(f"\n⚡ Powered by: ReAct Agent Only")
    print(f"🤖 Agent Type: Healthcare Database Specialist")
    print("="*70)

def print_react_help():
    """Display help for ReAct agent"""
    print("\n" + "="*60)
    print("📖 REACT AGENT HELP")
    print("="*60)
    
    print("\n🔄 HOW THE REACT AGENT WORKS:")
    print("   1. 🤔 THINK: Agent analyzes your question")
    print("   2. 📋 ACT: Explores database tables (sql_db_list_tables)")
    print("   3. 🔍 ACT: Examines relevant table schemas (sql_db_schema)")
    print("   4. ⚡ ACT: Generates and executes SQL (sql_db_query)")
    print("   5. 📊 OBSERVE: Analyzes results and formats JSON response")
    
    print("\n🏥 HEALTHCARE SPECIALIZATION:")
    print("   • Understands medical terminology and relationships")
    print("   • Knows patient → conditions → medications patterns")
    print("   • Uses proper PostgreSQL syntax with lowercase columns")
    print("   • Automatically limits results for performance")
    print("   • Provides healthcare-focused explanations")
    
    print("\n💬 QUESTION TYPES:")
    print("   • Counting: 'How many patients have diabetes?'")
    print("   • Searching: 'Show me patients with heart conditions'")
    print("   • Analysis: 'What are the most common medications?'")
    print("   • Demographics: 'List patients born after 1990'")
    print("   • Provider info: 'Show me cardiologists'")
    
    print("\n🔧 TECHNICAL FEATURES:")
    print("   • Automatic schema discovery")
    print("   • Query error detection and retry")
    print("   • Result limiting (default: 10 records)")
    print("   • JSON structured responses")
    print("   • Healthcare domain expertise")
    
    print("\n⌨️  COMMANDS:")
    print("   • 'help' - Show this help")
    print("   • 'exit' - End session (saves summary)")
    
    print("\n💡 TIP: The agent will show its thinking process,")
    print("        so you can see how it explores and queries your database!")

if __name__ == "__main__":
    print("🚀 Starting ReAct Database Assistant...")
    asyncio.run(react_agent_cli())