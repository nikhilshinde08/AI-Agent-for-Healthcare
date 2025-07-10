import asyncio
import requests
import json
from datetime import datetime
import time

async def test_healthcare_queries():
    """Test the FastAPI endpoint with healthcare-specific queries"""
    
    base_url = "http://localhost:8000"
    session_id = f"enhanced_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Test queries that should trigger SQL generation
    test_queries = [
        "How many patients are in the database?",
        "Show me all patients with diabetes",
        "What are the most common medical conditions?",
        "List all medications for hypertension",
        "Show me patients born after 1990",
        "What healthcare providers do we have?"
    ]
    
    print("🧪 Testing Enhanced Healthcare Queries...")
    print("="*60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🏥 Test {i}: {query}")
        print("-" * 40)
        
        try:
            chat_data = {
                "message": query,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
            start_time = time.time()
            response = requests.post(
                f"{base_url}/chat",
                json=chat_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Status: {response.status_code} (took {response_time:.2f}s)")
                print(f"📝 Response: {result.get('response', 'No response')[:200]}...")
                
                if result.get('sql_generated'):
                    print(f"🔧 SQL Generated: {result['sql_generated']}")
                
                if result.get('success'):
                    print(f"📊 Success: {result['success']}")
                    if result.get('result_count'):
                        print(f"📈 Results: {result['result_count']} records")
                else:
                    print("⚠️  No SQL query was generated (this might be expected for some queries)")
                    
            else:
                print(f"❌ Status: {response.status_code}")
                print(f"Error: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"⏱️  Request timed out after 30 seconds")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Small delay between requests
        time.sleep(1)
    
    print("\n" + "="*60)
    print("🎯 Enhanced testing completed!")

async def test_error_handling():
    """Test error handling scenarios"""
    
    base_url = "http://localhost:8000"
    session_id = f"error_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("\n🧪 Testing Error Handling...")
    print("="*40)
    
    # Test with invalid JSON
    try:
        response = requests.post(
            f"{base_url}/chat",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        print(f"Invalid JSON test: {response.status_code}")
    except Exception as e:
        print(f"Invalid JSON test error: {e}")
    
    # Test with missing required fields
    try:
        response = requests.post(
            f"{base_url}/chat",
            json={},
            headers={"Content-Type": "application/json"}
        )
        print(f"Missing fields test: {response.status_code}")
    except Exception as e:
        print(f"Missing fields test error: {e}")

async def test_session_management():
    """Test session management functionality"""
    
    base_url = "http://localhost:8000"
    session_id = f"session_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("\n🧪 Testing Session Management...")
    print("="*40)
    
    # Test session persistence
    queries = [
        "What tables are available?",
        "Can you remember what I just asked?",
        "List patients with heart conditions"
    ]
    
    for query in queries:
        try:
            chat_data = {
                "message": query,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(
                f"{base_url}/chat",
                json=chat_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Query: {query}")
                print(f"📝 Response: {result.get('response', 'No response')[:100]}...")
            else:
                print(f"❌ Query failed: {query}")
        except Exception as e:
            print(f"❌ Session test error: {e}")
        
        time.sleep(0.5)

if __name__ == "__main__":
    print("🚀 Starting Enhanced API Testing...")
    print("Make sure the backend server is running!")
    print("="*60)
    
    try:
        asyncio.run(test_healthcare_queries())
        asyncio.run(test_error_handling())
        asyncio.run(test_session_management())
        print("\n✅ All enhanced tests completed!")
    except KeyboardInterrupt:
        print("\n⏹️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")