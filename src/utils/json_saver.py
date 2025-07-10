import asyncio
import json
import os
import sys
from datetime import datetime
import uuid

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    import structlog
    
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

try:
    from utils.json_saver import JSONResponseSaver
    JSON_SAVING_AVAILABLE = True
except ImportError:
    print("Warning: JSON saver not available")
    JSON_SAVING_AVAILABLE = False

async def enhanced_database_cli_with_json():
    
    print("\n" + "="*80)
    print("🤖 ENHANCED AZURE OPENAI DATABASE ASSISTANT")
    print("⚡ Powered by Azure OpenAI with JSON Output & Saving")
    print("💾 All responses automatically saved as JSON files")
    print("💬 Ask me anything about your healthcare data!")
    print("="*80)
    
    json_saver = None
    if JSON_SAVING_AVAILABLE:
        json_saver = JSONResponseSaver("json_responses")
        print("✅ JSON saving enabled - responses will be saved to 'json_responses/' folder")
    else:
        print("⚠️  JSON saving not available - responses will only be displayed")
    
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    print(f"📋 Session ID: {session_id}")
    
    session_responses = []
    
    schema_description = None
    try:
        with open("/home/afour/Desktop/SQL_Agent/generic_sql_agent/description.txt", 'r', encoding='utf-8') as f:
            schema_description = f.read().strip()
            print(f"✅ Loaded database description ({len(schema_description)} characters)")
    except FileNotFoundError:
        print("⚠️  description.txt not found - will infer from database structure")
    except Exception as e:
        print(f"⚠️  Error loading description.txt: {e}")
    
    print("\n🔧 Initializing database agent...")
    
    agent = None
    agent_type = "unknown"
    
    try:
        from agents.react_agent import AzureReActDatabaseAgent
        agent = AzureReActDatabaseAgent()
        agent_type = "ReAct Agent"
        print("✅ ReAct Agent initialized successfully!")
    except Exception as e:
        print(f"⚠️  ReAct Agent failed: {e}")
        
        try:
            from agents.db_agent import AzureIntelligentDatabaseAgent
            agent = AzureIntelligentDatabaseAgent()
            agent_type = "Enhanced Node Workflow"
            print("✅ Enhanced Node Workflow initialized successfully!")
        except Exception as e:
            print(f"⚠️  Enhanced Node Workflow failed: {e}")
            
            try:
                from agents.db_agent import EnhancedReActDatabaseAgent
                agent = EnhancedReActDatabaseAgent()
                agent_type = "Fallback Agent"
                print("✅ Fallback Agent initialized successfully!")
            except Exception as e:
                print(f"❌ All agent types failed: {e}")
                print("\n💡 Check your configuration:")
                print("   • Azure OpenAI credentials in .env")
                print("   • Database connection settings")
                print("   • Required dependencies installed")
                return
    
    if not agent:
        print("❌ No agent could be initialized")
        return
    
    print(f"\n🎯 {agent_type} is ready!")
    print("\n🏥 Healthcare Database Capabilities:")
    print("   • Patient demographics and medical records")
    print("   • Medical conditions and diagnoses")
    print("   • Medications and prescriptions")
    print("   • Medical procedures and treatments")
    print("   • Healthcare providers and organizations")
    
    print("\n💬 Example Questions:")
    print("   • 'How many patients do we have?'")
    print("   • 'Show me patients with diabetes'")
    print("   • 'What medications are prescribed for heart conditions?'")
    print("   • 'List recent emergency room visits'")
    
    print("\n💾 JSON Saving Features:")
    if json_saver:
        print("   ✓ Individual response files for each query")
        print("   ✓ Session summary file at the end")
        print("   ✓ Daily summary files")
        print("   ✓ Searchable JSON format with metadata")
    else:
        print("   ⚠️  JSON saving not available in this session")
    
    print("\n" + "-"*80)
    print("Type 'exit', 'help', 'save-session', or ask your question")
    print("-"*80)
    
    session_count = 0
    
    while True:
        try:
            user_input = input(f"\n💬 [{agent_type}] Ask about your data: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q', 'bye']:
                if json_saver and session_responses:
                    session_file = json_saver.save_session_responses(session_responses, session_id)
                    if session_file:
                        print(f"💾 Session summary saved to: {session_file}")
                
                print(f"\n👋 Thank you for using the {agent_type}!")
                print(f"📊 Session Summary: {len(session_responses)} queries processed")
                break
            
            if user_input.lower() in ['help', 'h']:
                print_help_with_json()
                continue
            
            if user_input.lower() == 'save-session':
                if json_saver and session_responses:
                    session_file = json_saver.save_session_responses(session_responses, session_id)
                    if session_file:
                        print(f"💾 Session manually saved to: {session_file}")
                else:
                    print("⚠️  No responses to save or JSON saver not available")
                continue
            
            if user_input.lower() == 'show-files':
                show_saved_files()
                continue
            
            if not user_input:
                print("💭 Please ask a question about your healthcare data!")
                continue
            
            session_count += 1
            print(f"\n🧠 {agent_type} is processing your question...")
            
            try:
                start_time = datetime.now()
                
                if agent_type == "ReAct Agent":
                    response_obj = await agent.process_query(user_input)
                    if hasattr(response_obj, 'dict'):
                        response = {
                            "success": response_obj.success,
                            "answer": response_obj.message,
                            "query_understanding": response_obj.query_understanding,
                            "data": [r.data for r in response_obj.results] if response_obj.results else [],
                            "sql_generated": response_obj.sql_query,
                            "result_count": response_obj.result_count,
                            "metadata": response_obj.metadata,
                            "powered_by": response_obj.powered_by,
                            "structured_response": response_obj.dict()
                        }
                    else:
                        response = response_obj
                else:
                    if schema_description:
                        response = await agent.answer_question(user_input, f"session_{session_count}", schema_description)
                    else:
                        response = await agent.answer_question(user_input, f"session_{session_count}")
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                if "metadata" not in response:
                    response["metadata"] = {}
                response["metadata"]["processing_time_seconds"] = processing_time
                response["metadata"]["session_id"] = session_id
                response["metadata"]["query_number"] = session_count
                
                if json_saver:
                    saved_file = json_saver.save_response(response, user_input, session_id)
                    if saved_file:
                        print(f"💾 Response saved to: {os.path.basename(saved_file)}")
                
                session_responses.append({
                    "query_metadata": {
                        "original_query": user_input,
                        "timestamp": start_time.isoformat(),
                        "session_id": session_id,
                        "query_number": session_count,
                        "processing_time_seconds": processing_time
                    },
                    "response": response
                })
                
                display_results_with_json_info(response, session_count, agent_type, saved_file if json_saver else None)
                
            except Exception as e:
                error_response = {
                    "success": False,
                    "answer": f"Error processing question: {str(e)}",
                    "query_understanding": user_input,
                    "data": None,
                    "sql_generated": None,
                    "metadata": {
                        "error_type": type(e).__name__,
                        "session_id": session_id,
                        "query_number": session_count
                    }
                }
                
                if json_saver:
                    saved_file = json_saver.save_response(error_response, user_input, session_id)
                    if saved_file:
                        print(f"💾 Error response saved to: {os.path.basename(saved_file)}")
                
                session_responses.append({
                    "query_metadata": {
                        "original_query": user_input,
                        "timestamp": datetime.now().isoformat(),
                        "session_id": session_id,
                        "query_number": session_count,
                        "error": True
                    },
                    "response": error_response
                })
                
                print(f"\n❌ Error processing question: {str(e)}")
                print("💡 Try rephrasing your question or check your configuration")
                logger.error(f"Query processing error: {e}")
            
        except KeyboardInterrupt:
            print(f"\n\n👋 {agent_type} session ended!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            continue

def display_results_with_json_info(response: dict, session_count: int, agent_type: str, saved_file: str = None):
    
    print("\n" + "="*70)
    print(f"📊 SESSION {session_count} - {agent_type.upper()} RESULTS")
    print("="*70)
    
    status_icon = "✅" if response.get("success") else "❌"
    status_text = "SUCCESS" if response.get("success") else "ERROR"
    print(f"\n{status_icon} STATUS: {status_text}")
    
    if saved_file:
        print(f"💾 JSON SAVED: {os.path.basename(saved_file)}")
    
    if response.get("query_understanding"):
        print(f"🧠 UNDERSTANDING: {response['query_understanding']}")
    
    if response.get("answer"):
        print(f"💬 ANSWER: {response['answer']}")
    
    if response.get("sql_generated"):
        print(f"\n🔧 SQL QUERY:")
        print(f"   {response['sql_generated']}")
    
    data = response.get("data", [])
    if data and response.get("success"):
        result_count = len(data)
        print(f"\n📊 DATA RESULTS ({result_count} records):")
        print("-" * 50)
        
        for i, record in enumerate(data[:3], 1):
            print(f"\n   Record {i}:")
            if isinstance(record, dict):
                for key, value in record.items():
                    display_value = str(value)
                    if len(display_value) > 50:
                        display_value = display_value[:47] + "..."
                    print(f"      {key}: {display_value}")
            else:
                print(f"      {record}")
        
        if result_count > 3:
            print(f"\n   ... and {result_count - 3} more records")
    
    metadata = response.get("metadata", {})
    if metadata:
        print(f"\n🔍 METADATA:")
        for key, value in metadata.items():
            if key in ["processing_time_seconds", "query_type", "tables_used"]:
                print(f"   {key}: {value}")
    
    if response.get("structured_response"):
        print(f"\n📋 STRUCTURED RESPONSE: Available in JSON file")
    
    print(f"\n⚡ Powered by: {response.get('powered_by', agent_type)}")
    print("="*70)

def print_help_with_json():
    print("\n" + "="*60)
    print("📖 HELP - HEALTHCARE DATABASE ASSISTANT WITH JSON SAVING")
    print("="*60)
    
    print("\n💬 HOW TO ASK QUESTIONS:")
    print("   • Use natural language - no need to know SQL!")
    print("   • Ask about patients, conditions, medications, procedures")
    print("   • Be specific about what you want to know")
    
    print("\n🏥 HEALTHCARE DATA AVAILABLE:")
    print("   • PATIENTS: Demographics, personal information")
    print("   • CONDITIONS: Medical diagnoses and diseases")
    print("   • MEDICATIONS: Prescriptions and treatments")
    print("   • PROCEDURES: Medical procedures and surgeries")
    print("   • ENCOUNTERS: Doctor visits and hospital stays")
    print("   • PROVIDERS: Doctors and healthcare professionals")
    
    print("\n💾 JSON SAVING FEATURES:")
    print("   • Each query response saved as individual JSON file")
    print("   • Session summary saved when you exit")
    print("   • Files saved in 'json_responses/' folder")
    print("   • Includes metadata: timestamps, processing time, session info")
    print("   • Searchable and machine-readable format")
    
    print("\n⌨️  COMMANDS:")
    print("   • 'help' - Show this help")
    print("   • 'save-session' - Manually save session summary")
    print("   • 'show-files' - Show saved JSON files")
    print("   • 'exit' or 'quit' - End session (auto-saves summary)")

def show_saved_files():
    json_dir = "json_responses"
    
    if not os.path.exists(json_dir):
        print("📁 No JSON files saved yet")
        return
    
    files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    
    if not files:
        print("📁 No JSON files found")
        return
    
    print(f"\n📁 SAVED JSON FILES ({len(files)} files):")
    print("-" * 50)
    
    files_with_time = [(f, os.path.getmtime(os.path.join(json_dir, f))) for f in files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    for i, (filename, mtime) in enumerate(files_with_time[:10], 1):
        file_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        file_size = os.path.getsize(os.path.join(json_dir, filename))
        print(f"   {i:2d}. {filename}")
        print(f"       Created: {file_time} | Size: {file_size} bytes")
    
    if len(files) > 10:
        print(f"   ... and {len(files) - 10} more files")
    
    print(f"\n📂 Location: {os.path.abspath(json_dir)}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("🧪 Testing connections...")
        asyncio.run(enhanced_database_cli_with_json())
    else:
        asyncio.run(enhanced_database_cli_with_json())