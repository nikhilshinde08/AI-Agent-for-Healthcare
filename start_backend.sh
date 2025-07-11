#!/bin/bash

# Healthcare Database Assistant - Backend Startup Script
# Based on reference implementation

set -e

echo "🚀 Starting Healthcare Database Assistant Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "🔧 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for environment variables
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Please create one with your configuration."
    echo "Example .env file:"
    echo "AZURE_OPENAI_ENDPOINT=your_endpoint"
    echo "AZURE_OPENAI_API_KEY=your_key"
    echo "AZURE_OPENAI_API_VERSION=2024-02-15-preview"
    echo "AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment"
    echo "AZURE_OPENAI_MODEL_NAME=gpt-4"
    echo "DATABASE_URL=postgresql://user:password@localhost/dbname"
    echo "TAVILY_API_KEY=your_tavily_key"
    echo ""
    echo "Create .env file and run this script again."
    exit 1
fi

# Load environment variables
echo "🔐 Loading environment variables..."
export $(cat .env | xargs)

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p conversation_memory
mkdir -p json_responses
mkdir -p logs

# Check Python version
echo "🐍 Python version:"
python --version

# Check if database connection is available
echo "🔍 Checking database connection..."
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
db_url = os.getenv('DATABASE_URL')
if db_url:
    print(f'✅ Database URL configured: {db_url[:20]}...')
else:
    print('⚠️  DATABASE_URL not configured')
"

# Kill any existing process on port 8002
if lsof -Pi :8002 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "🔄 Killing existing process on port 8002..."
    lsof -ti :8002 | xargs kill -9 2>/dev/null || true
    sleep 2
    echo "✅ Port 8002 is now available"
fi

# Start the FastAPI server
echo "🌐 Starting FastAPI server on http://127.0.0.1:8002"
echo "📖 API documentation will be available at http://127.0.0.1:8002/docs"
echo "🔄 Press Ctrl+C to stop the server"
echo ""

# Run with auto-reload for development
python -m uvicorn api_server:app --host 127.0.0.1 --port 8002 --reload --log-level info

echo "👋 Backend server stopped."