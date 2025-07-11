"""Healthcare Database Assistant main module."""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

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

JSON_FEATURES_AVAILABLE = False

try:
    from src.memory.json_memory_manager import JSONMemoryManager
    from src.utils.json_saver import JSONResponseSaver
    JSON_FEATURES_AVAILABLE = True
    print("✅ JSON memory and response saving features available")
except ImportError:
    try:
        from memory.json_memory_manager import JSONMemoryManager
        from utils.json_saver import JSONResponseSaver
        JSON_FEATURES_AVAILABLE = True
        print("✅ JSON memory and response saving features available")
    except ImportError:
        print("⚠️ JSON memory features not available")
        JSON_FEATURES_AVAILABLE = False


async def enhanced_database_cli_with_json_memory():
    """Enhanced CLI with proper JSON memory integration.
    
    Initializes and runs the healthcare database assistant with enhanced
    JSON memory management and response saving capabilities.
    """
    
    print("\n" + "="*80)
    print("🤖 ENHANCED AZURE OPENAI DATABASE ASSISTANT")
    print("⚡ Powered by Azure OpenAI with JSON Memory & Response Saving")
    print("💾 Persistent JSON-based conversation memory")
    print("🔍 Searchable response history")
    print("💬 Ask me anything about your healthcare data!")
    print("="*80)
    
    memory_manager = None
    response_saver = None
    
    if JSON_FEATURES_AVAILABLE:
        try:
            memory_manager = JSONMemoryManager("conversation_memory")
            response_saver = JSONResponseSaver("json_responses")
            print(f"✅ JSON Memory initialized - Session: {memory_manager.current_session_id}")
            print(f"✅ Response Saver initialized - Location: json_responses/")
        except Exception as e:
            print(f"⚠️ Error initializing JSON features: {e}")
            memory_manager = None
            response_saver = None
    
    schema_description = None
    try:
        with open("description.txt", 'r', encoding='utf-8') as f:
            schema_description = f.read().strip()
            print(f"✅ Loaded database description ({len(schema_description)} characters)")
    except FileNotFoundError:
        print("⚠️ description.txt not found - will infer from database structure")
    except Exception as e:
        print(f"⚠️ Error loading description.txt: {e}")
    
    print("\n🔧 Initializing database agent...")
    
    agent = None
    agent_type = "unknown"
    
    try:
        from src.agents.db_agent import AzureReActDatabaseAgent
        agent = AzureReActDatabaseAgent(
            memory_dir="conversation_memory",
            responses_dir="json_responses"
        )
        agent_type = "Enhanced ReAct Agent with JSON Memory"
        print("✅ Enhanced ReAct Agent with JSON Memory initialized!")
    except Exception as e:
        print(f"⚠️ Enhanced Agent failed: {e}")
        
        try:
            from src.agents.react_agent import LangGraphReActDatabaseAgent
            agent = LangGraphReActDatabaseAgent()
            agent_type = "ReAct Agent (no memory)"
            print("✅ Basic ReAct Agent initialized (memory features disabled)")
        except Exception as e2:
            print(f"❌ All agent types failed: {e2}")
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
    print("   • 'Find patients over 65 with high blood pressure'")
    
    if memory_manager and response_saver:
        print("\n💾 JSON Memory Features:")
        print("   ✓ Persistent conversation history")
        print("   ✓ Context-aware follow-up questions")
        print("   ✓ Searchable response database")
        print("   ✓ Session summaries and exports")
        print("   ✓ Daily usage analytics")
        
        try:
            memory_stats = memory_manager.get_memory_stats()
            print(f"   📊 Current session: {memory_stats['current_session']['total_interactions']} interactions")
            print(f"   📁 Storage: {memory_stats['storage_location']}")
            
            integrity_check = memory_manager.validate_memory_integrity()
            if integrity_check['is_healthy']:
                print(f"   ✅ Memory integrity: OK ({integrity_check['conversation_history_count']} conversations)")
            else:
                print(f"   ⚠️ Memory integrity issues: {', '.join(integrity_check['issues'])}")
                
        except Exception as e:
            print(f"   ⚠️ Could not get memory stats: {e}")
    else:
        print("\n⚠️ JSON Memory Features: Disabled")
    
    print("\n" + "-"*80)
    print("💡 Available Commands:")
    print("   • Type your question naturally")
    print("   • 'help' - Show detailed help")
    print("   • 'memory' - Show memory statistics")
    print("   • 'search <term>' - Search conversation history")
    print("   • 'export' - Export session data")
    print("   • 'clear' - Clear session memory")
    print("   • 'stats' - Show storage statistics")
    print("   • 'exit' - End session")
    print("-"*80)
    
    session_count = 0
    
    while True:
        try:
            user_input = input(f"\n💬 [{agent_type}] Your question: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q', 'bye']:
                print(f"\n🔄 Ending session...")
                
                if hasattr(agent, 'save_session_summary'):
                    summary_file = agent.save_session_summary()
                    if summary_file:
                        print(f"💾 Session summary saved to: {os.path.basename(summary_file)}")
                
                if hasattr(agent, 'end_session'):
                    agent.end_session()
                
                print(f"👋 Thank you for using the {agent_type}!")
                
                if hasattr(agent, 'get_memory_stats'):
                    try:
                        final_stats = agent.get_memory_stats()
                        if 'memory_stats' in final_stats:
                            memory_stats = final_stats['memory_stats']
                            print(f"📊 Final session stats: {memory_stats['current_session']['total_interactions']} queries")
                            print(f"✅ Success rate: {memory_stats['current_session']['successful_queries']}/{memory_stats['current_session']['total_interactions']}")
                    except Exception as e:
                        print(f"⚠️ Could not get final stats: {e}")
                
                break
            
            if user_input.lower() in ['help', 'h']:
                print_comprehensive_help()
                continue
            
            if user_input.lower() == 'memory':
                if hasattr(agent, 'get_memory_stats'):
                    try:
                        stats = agent.get_memory_stats()
                        display_memory_stats(stats)
                    except Exception as e:
                        print(f"⚠️ Error getting memory stats: {e}")
                else:
                    print("⚠️ Memory statistics not available")
                continue
            
            if user_input.lower().startswith('search '):
                search_term = user_input[7:].strip()
                if search_term:
                    perform_search(agent, search_term)
                else:
                    print("💭 Please provide a search term: search <term>")
                continue
            
            if user_input.lower() == 'export':
                if hasattr(agent, 'export_session_data'):
                    try:
                        export_file = agent.export_session_data("json")
                        if export_file:
                            print(f"📤 Session data exported to: {export_file}")
                        else:
                            print("⚠️ Export failed or not available")
                    except Exception as e:
                        print(f"⚠️ Export error: {e}")
                else:
                    print("⚠️ Export feature not available")
                continue
            
            if user_input.lower() == 'clear':
                if hasattr(agent, 'clear_session_memory'):
                    try:
                        agent.clear_session_memory()
                        print("🧹 Session memory cleared - starting fresh!")
                    except Exception as e:
                        print(f"⚠️ Clear memory error: {e}")
                else:
                    print("⚠️ Clear memory feature not available")
                continue
            
            if user_input.lower() == 'stats':
                if hasattr(agent, 'get_storage_stats'):
                    try:
                        stats = agent.get_storage_stats()
                        display_storage_stats(stats)
                    except Exception as e:
                        print(f"⚠️ Error getting storage stats: {e}")
                else:
                    print("⚠️ Storage statistics not available")
                continue
            
            if not user_input:
                print("💭 Please ask a question about your healthcare data!")
                continue
            
            session_count += 1
            print(f"\n🧠 Processing your question... (Query #{session_count})")
            
            try:
                start_time = datetime.now()
                
                response = await process_agent_query(agent, user_input, schema_description)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                display_enhanced_results(response, session_count, agent_type, processing_time)
                
            except Exception as e:
                print(f"\n❌ Error processing question: {str(e)}")
                print("💡 Try rephrasing your question or check the logs")
                logger.error(f"Query processing error: {e}")
            
        except KeyboardInterrupt:
            print(f"\n\n👋 Session interrupted! Saving data...")
            
            if hasattr(agent, 'save_session_summary'):
                try:
                    agent.save_session_summary()
                except Exception as e:
                    print(f"⚠️ Error saving session: {e}")
            
            if hasattr(agent, 'end_session'):
                try:
                    agent.end_session()
                except Exception as e:
                    print(f"⚠️ Error ending session: {e}")
            
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            logger.error(f"Unexpected error in main loop: {e}")
            continue
    
    if hasattr(agent, '_cleanup'):
        try:
            await agent._cleanup()
        except Exception as e:
            print(f"⚠️ Error during final cleanup: {e}")


def display_enhanced_results(response: Dict[str, Any], session_count: int, agent_type: str, processing_time: float):
    """Display query results with enhanced formatting.
    
    Args:
        response: The response dictionary from the agent
        session_count: Current session count number
        agent_type: Type of agent being used
        processing_time: Time taken to process the query
    """
    
    print("\n" + "="*80)
    print(f"📊 QUERY #{session_count} - {agent_type.upper()} RESULTS")
    print("="*80)
    
    status_icon = "✅" if response.get("success") else "❌"
    status_text = "SUCCESS" if response.get("success") else "ERROR"
    print(f"\n{status_icon} STATUS: {status_text}")
    print(f"⏱️ PROCESSING TIME: {processing_time:.2f} seconds")
    
    metadata = response.get("metadata", {})
    if metadata.get("session_id"):
        print(f"📋 SESSION: {metadata['session_id']}")
    
    if metadata.get("interaction_id"):
        print(f"🔗 INTERACTION: {metadata['interaction_id']}")
    
    if metadata.get("saved_to_file"):
        print(f"💾 SAVED TO: {os.path.basename(metadata['saved_to_file'])}")
    
    if response.get("query_understanding"):
        print(f"\n🧠 AI UNDERSTANDING:")
        print(f"   {response['query_understanding']}")
    
    if response.get("message") or response.get("answer"):
        answer = response.get("message") or response.get("answer")
        print(f"\n💬 ANSWER:")
        print(f"   {answer}")
    
    if response.get("sql_generated") or response.get("sql_query"):
        sql = response.get("sql_generated") or response.get("sql_query")
        print(f"\n🔧 SQL QUERY:")
        print(f"   {sql}")
    
    data = response.get("data", [])
    if data and response.get("success"):
        result_count = len(data)
        print(f"\n📊 DATA RESULTS ({result_count} records):")
        print("-" * 80)
        
        display_data_table(data)
        
        if result_count > 10:
            print(f"\n   💡 Showing first 10 records. Use 'search' to find specific records")
        elif result_count > 3:
            print(f"\n   💡 Use 'search' to find specific records")
    
    if metadata.get("memory_summary"):
        memory_summary = metadata["memory_summary"]
        print(f"\n🧠 MEMORY CONTEXT:")
        print(f"   Total interactions: {memory_summary.get('total_interactions', 0)}")
        print(f"   Success rate: {memory_summary.get('success_rate', 0):.1f}%")
        if memory_summary.get('current_context', {}).get('last_patient_mentioned'):
            print(f"   Last patient: {memory_summary['current_context']['last_patient_mentioned']}")
    
    print(f"\n⚡ Powered by: {response.get('powered_by', agent_type)}")
    print("="*80)


def display_data_table(data: List[Dict[str, Any]], max_rows: int = 10):
    """Display data in a structured table format.
    
    Args:
        data: List of data dictionaries to display
        max_rows: Maximum number of rows to display
    """
    if not data:
        print("   No data to display")
        return
    
    display_data = data[:max_rows]
    
    if PANDAS_AVAILABLE:
        try:
            df = pd.DataFrame(display_data)
            
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 50)
            pd.set_option('display.expand_frame_repr', False)
            
            table_str = str(df)
            indented_table = '\n'.join('   ' + line for line in table_str.split('\n'))
            print(indented_table)
            
        except Exception as e:
            print(f"   Error creating table with pandas: {e}")
            display_data_simple_table(display_data)
    else:
        display_data_simple_table(display_data)


def display_data_simple_table(data: List[Dict[str, Any]]):
    """Simple table display without pandas.
    
    Args:
        data: List of data dictionaries to display
    """
    if not data:
        print("   No data to display")
        return
    
    all_keys = set()
    for record in data:
        if isinstance(record, dict):
            all_keys.update(record.keys())
    
    if not all_keys:
        print("   No structured data to display")
        return
    
    headers = sorted(list(all_keys))
    
    col_widths = {}
    for header in headers:
        col_widths[header] = len(header)
        for record in data:
            if isinstance(record, dict):
                value = str(record.get(header, ''))
                if len(value) > 40:
                    value = value[:37] + '...'
                col_widths[header] = max(col_widths[header], len(value))
    
    header_line = "   | " + " | ".join(h.ljust(col_widths[h]) for h in headers) + " |"
    print(header_line)
    
    separator = "   |-" + "-|-".join("-" * col_widths[h] for h in headers) + "-|"
    print(separator)
    
    for record in data:
        if isinstance(record, dict):
            row_values = []
            for header in headers:
                value = str(record.get(header, ''))
                if len(value) > 40:
                    value = value[:37] + '...'
                row_values.append(value.ljust(col_widths[header]))
            
            row_line = "   | " + " | ".join(row_values) + " |"
            print(row_line)


def display_memory_stats(stats: Dict[str, Any]):
    """Display memory statistics.
    
    Args:
        stats: Dictionary containing memory statistics
    """
    print("\n" + "="*60)
    print("🧠 MEMORY STATISTICS")
    print("="*60)
    
    if 'memory_stats' in stats:
        memory_stats = stats['memory_stats']
        current_session = memory_stats.get('current_session', {})
        
        print(f"\n📋 CURRENT SESSION:")
        print(f"   Session ID: {current_session.get('session_id', 'Unknown')}")
        print(f"   Total interactions: {current_session.get('total_interactions', 0)}")
        print(f"   Successful queries: {current_session.get('successful_queries', 0)}")
        print(f"   Failed queries: {current_session.get('failed_queries', 0)}")
        
        if current_session.get('total_interactions', 0) > 0:
            success_rate = (current_session.get('successful_queries', 0) / current_session.get('total_interactions', 1)) * 100
            print(f"   Success rate: {success_rate:.1f}%")
        
        file_counts = memory_stats.get('file_counts', {})
        print(f"\n📁 FILE STORAGE:")
        print(f"   Session files: {file_counts.get('session_files', 0)}")
        print(f"   Response files: {file_counts.get('response_files', 0)}")
        print(f"   Daily summaries: {file_counts.get('daily_files', 0)}")
        
        print(f"\n💾 STORAGE LOCATION: {memory_stats.get('storage_location', 'Unknown')}")
    
    if 'response_stats' in stats:
        response_stats = stats['response_stats']
        print(f"\n📊 RESPONSE STORAGE:")
        if 'storage_size' in response_stats:
            storage_size = response_stats['storage_size']
            print(f"   Total size: {storage_size.get('total_mb', 0):.2f} MB")
        
        if 'file_counts' in response_stats:
            file_counts = response_stats['file_counts']
            print(f"   Total files: {file_counts.get('total_files', 0)}")
    
    print("="*60)


def display_storage_stats(stats: Dict[str, Any]):
    """Display storage statistics.
    
    Args:
        stats: Dictionary containing storage statistics
    """
    print("\n" + "="*60)
    print("💾 STORAGE STATISTICS")
    print("="*60)
    
    if 'response_stats' in stats:
        response_stats = stats['response_stats']
        
        if 'file_counts' in response_stats:
            file_counts = response_stats['file_counts']
            print(f"\n📁 FILE COUNTS:")
            print(f"   Individual responses: {file_counts.get('response_files', 0)}")
            print(f"   Session summaries: {file_counts.get('session_files', 0)}")
            print(f"   Daily summaries: {file_counts.get('daily_files', 0)}")
            print(f"   Export files: {file_counts.get('export_files', 0)}")
            print(f"   Total files: {file_counts.get('total_files', 0)}")
        
        if 'storage_size' in response_stats:
            storage_size = response_stats['storage_size']
            print(f"\n💾 STORAGE SIZE:")
            print(f"   Total: {storage_size.get('total_mb', 0):.2f} MB")
            print(f"   ({storage_size.get('total_bytes', 0):,} bytes)")
        
        if 'directories' in response_stats:
            directories = response_stats['directories']
            print(f"\n📂 DIRECTORIES:")
            for dir_type, path in directories.items():
                print(f"   {dir_type}: {path}")
    
    print("="*60)


def perform_search(agent, search_term: str):
    """Perform search in conversation history.
    
    Args:
        agent: The database agent instance
        search_term: Term to search for
    """
    print(f"\n🔍 Searching for: '{search_term}'")
    
    if hasattr(agent, 'search_memory'):
        try:
            memory_results = agent.search_memory(search_term, max_results=3)
            if memory_results:
                print(f"\n🧠 MEMORY SEARCH RESULTS:")
                for i, result in enumerate(memory_results, 1):
                    print(f"\n   {i}. {result['type'].upper()}")
                    print(f"      Time: {result['timestamp'][:19]}")
                    print(f"      Content: {result['content'][:100]}...")
                    if 'context' in result:
                        context = result['context']
                        if context.get('patient_mentioned'):
                            print(f"      Patient: {context['patient_mentioned']}")
        except Exception as e:
            print(f"⚠️ Memory search error: {e}")
    
    if hasattr(agent, 'search_responses'):
        try:
            response_results = agent.search_responses(search_term, max_results=3)
            if response_results:
                print(f"\n📄 RESPONSE SEARCH RESULTS:")
                for i, result in enumerate(response_results, 1):
                    print(f"\n   {i}. Query: {result['user_query'][:60]}...")
                    print(f"      Time: {result['timestamp'][:19]}")
                    print(f"      Success: {'✅' if result['success'] else '❌'}")
                    print(f"      Response: {result['response_message'][:80]}...")
        except Exception as e:
            print(f"⚠️ Response search error: {e}")
    
    if not (hasattr(agent, 'search_memory') or hasattr(agent, 'search_responses')):
        print("⚠️ Search feature not available")


async def process_agent_query(agent, user_input: str, schema_description: str = None):
    """Process query through the agent with proper error handling"""
    if hasattr(agent, '__aenter__'):
        async with agent as ctx_agent:
            if hasattr(ctx_agent, 'answer_question'):
                return await ctx_agent.answer_question(user_input, schema_description=schema_description)
            elif hasattr(ctx_agent, 'process_query'):
                response_obj = await ctx_agent.process_query(user_input)
                if hasattr(response_obj, 'dict'):
                    return {
                        "success": response_obj.success,
                        "answer": response_obj.message,
                        "message": response_obj.message,
                        "query_understanding": response_obj.query_understanding,
                        "data": [r.data for r in response_obj.results] if response_obj.results else [],
                        "sql_generated": response_obj.sql_query,
                        "result_count": response_obj.result_count,
                        "metadata": response_obj.metadata
                    }
                else:
                    return response_obj
            else:
                raise ValueError("Agent method not found")
    else:
        if hasattr(agent, 'answer_question'):
            return await agent.answer_question(user_input, schema_description=schema_description)
        elif hasattr(agent, 'process_query'):
            response_obj = await agent.process_query(user_input)
            if hasattr(response_obj, 'dict'):
                return {
                    "success": response_obj.success,
                    "answer": response_obj.message,
                    "message": response_obj.message,
                    "query_understanding": response_obj.query_understanding,
                    "data": [r.data for r in response_obj.results] if response_obj.results else [],
                    "sql_generated": response_obj.sql_query,
                    "result_count": response_obj.result_count,
                    "metadata": response_obj.metadata
                }
            else:
                return response_obj
        else:
            raise ValueError("Agent method not found")


def print_comprehensive_help():
    """Display comprehensive help information."""
    print("\n" + "="*80)
    print("📖 COMPREHENSIVE HELP - HEALTHCARE DATABASE ASSISTANT")
    print("="*80)
    
    print("\n💬 HOW TO ASK QUESTIONS:")
    print("   • Use natural language - no SQL knowledge required!")
    print("   • Be specific about what you want to know")
    print("   • Ask follow-up questions - the AI remembers context")
    print("   • Use patient names if known")
    
    print("\n🏥 HEALTHCARE DATA CATEGORIES:")
    print("   • PATIENTS: Demographics, contact info, basic details")
    print("   • CONDITIONS: Medical diagnoses, diseases, health issues")
    print("   • MEDICATIONS: Prescriptions, drugs, dosages")
    print("   • PROCEDURES: Surgeries, treatments, medical procedures")
    print("   • ENCOUNTERS: Doctor visits, hospital stays, appointments")
    print("   • PROVIDERS: Doctors, nurses, healthcare professionals")
    print("   • OBSERVATIONS: Test results, vitals, measurements")
    print("   • ALLERGIES: Patient allergies and reactions")
    
    print("\n💡 EXAMPLE QUESTIONS:")
    print("   📊 Counting: 'How many patients have diabetes?'")
    print("   📋 Listing: 'Show me all patients over 65'")
    print("   🔍 Searching: 'Find John Smith's medical records'")
    print("   🏥 Medical: 'What medications treat high blood pressure?'")
    print("   📅 Recent: 'Show recent emergency room visits'")
    print("   🔗 Related: 'Who are the cardiologists in our system?'")
    
    print("\n🧠 MEMORY FEATURES:")
    print("   • Conversation history is automatically saved")
    print("   • Context is maintained across questions")
    print("   • Follow-up questions use previous context")
    print("   • Search through past conversations")
    print("   • Export conversation summaries")
    
    print("\n⌨️ AVAILABLE COMMANDS:")
    print("   • 'help' - Show this help information")
    print("   • 'memory' - Display memory statistics")
    print("   • 'search <term>' - Search conversation history")
    print("   • 'export' - Export session data")
    print("   • 'clear' - Clear session memory")
    print("   • 'stats' - Show storage statistics")
    print("   • 'exit' - End session and save data")
    
    print("\n💾 JSON STORAGE:")
    print("   • All interactions saved as JSON files")
    print("   • Session summaries created automatically")
    print("   • Daily usage summaries")
    print("   • Searchable and exportable data")
    
    print("\n🔧 TECHNICAL FEATURES:")
    print("   • Azure OpenAI powered natural language processing")
    print("   • PostgreSQL database integration")
    print("   • Intelligent SQL query generation")
    print("   • Context-aware response generation")
    print("   • Persistent JSON-based memory system")
    
    print("="*80)


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "test":
            print("🧪 Running in test mode...")
            asyncio.run(enhanced_database_cli_with_json_memory())
        else:
            asyncio.run(enhanced_database_cli_with_json_memory())
    except KeyboardInterrupt:
        print("\n👋 Application interrupted by user")
    except Exception as e:
        print(f"\n❌ Application error: {e}")
        logger.error(f"Application error: {e}")
    finally:
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception as e:
            print(f"⚠️ Error during final cleanup: {e}")
        
        print("\n🔄 Application shutdown complete")