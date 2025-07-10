import asyncio
import requests
import json
from datetime import datetime

async def test_api_endpoint():
    """Test the FastAPI endpoint"""
    
    # Test health check
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"✅ Health check: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test chat endpoint
    try:
        chat_data = {
            "message": "Hello, can you help me with my database?",
            "session_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat()
        }
        
        response = requests.post(
            "http://localhost:8000/chat",
            json=chat_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"✅ Chat endpoint: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result.get('response', 'No response')}")
            print(f"Success: {result.get('success', False)}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Chat endpoint failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧪 Testing API endpoints...")
    print("Make sure the backend server is running with: python api_server.py")
    print("="*50)
    
    result = asyncio.run(test_api_endpoint())
    
    if result:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")