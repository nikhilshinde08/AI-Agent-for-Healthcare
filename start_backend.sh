#!/bin/bash

echo "🚀 Starting SQL Agent Backend Server..."
echo "📡 API will be available at: http://localhost:8002"
echo "📖 API docs will be available at: http://localhost:8002/docs"
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Kill any existing processes on port 8002
echo "🔧 Checking for existing processes on port 8002..."
PORT_PID=$(lsof -ti:8002)
if [ ! -z "$PORT_PID" ]; then
    echo "🔧 Killing existing process on port 8002 (PID: $PORT_PID)..."
    kill -9 $PORT_PID
    sleep 2
fi

# Install dependencies if needed
echo "🔧 Installing dependencies..."
pip install -r requirements.txt

# Start the FastAPI server
echo "🚀 Starting FastAPI server..."
python api_server.py