#!/bin/bash

# Healthcare Database Assistant - Full Stack Startup Script
# Starts both backend (FastAPI) and frontend (React) servers

set -e

echo "🚀 Starting Healthcare Database Assistant - Full Stack"
echo "=" * 60

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🔄 Shutting down servers..."
    
    # Kill background processes
    jobs -p | xargs -r kill 2>/dev/null || true
    
    # Force kill processes on specific ports
    echo "🔒 Stopping backend (port 8002)..."
    lsof -ti :8002 | xargs kill -9 2>/dev/null || true
    
    echo "🌐 Stopping frontend (port 3000)..."
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
    
    # Additional cleanup for any remaining processes
    pkill -f "uvicorn api_server:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    
    # Wait a moment for cleanup
    sleep 2
    
    echo "👋 Full stack shutdown complete"
    exit 0
}

# Set up signal handlers for graceful shutdown
trap cleanup SIGINT SIGTERM

echo "🔧 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ and try again."
    exit 1
fi
echo "✅ Python: $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ and try again."
    exit 1
fi
echo "✅ Node.js: $(node -v)"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating example configuration..."
    cat > .env << EOF
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=your_endpoint_here
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_here
AZURE_OPENAI_MODEL_NAME=gpt-4

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/healthcare_db

# Optional: Tavily API for healthcare search
TAVILY_API_KEY=your_tavily_key_here
EOF
    echo "📝 Please edit .env file with your configuration and run this script again."
    exit 1
fi

echo "✅ Configuration file found"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p conversation_memory json_responses api_storage logs

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1

echo ""
echo "🔥 Starting Backend Server..."
echo "📖 Backend API docs: http://127.0.0.1:8002/docs"

# Kill any existing process on port 8002
BACKEND_PORT=8002
if lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "🔄 Killing existing process on port $BACKEND_PORT..."
    lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo "🔧 Using backend port: $BACKEND_PORT"

# Start backend in background
python -m uvicorn api_server:app --host 127.0.0.1 --port $BACKEND_PORT --reload &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:$BACKEND_PORT/health > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start within 30 seconds"
        cleanup
        exit 1
    fi
    sleep 1
done

# Navigate to frontend directory and install dependencies
echo ""
echo "🌐 Preparing Frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    if command -v npm &> /dev/null; then
        npm install > /dev/null 2>&1
    elif command -v yarn &> /dev/null; then
        yarn install > /dev/null 2>&1
    else
        echo "❌ No package manager found. Please install npm or yarn."
        cleanup
        exit 1
    fi
fi

# Update browserslist database if needed (prevent startup blocking)
echo "🔄 Checking browserslist database..."
npm update caniuse-lite > /dev/null 2>&1 || echo "⚠️  Browserslist update skipped"

# Kill any existing process on port 3000
FRONTEND_PORT=3000
if lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "🔄 Killing existing process on port $FRONTEND_PORT..."
    lsof -ti :$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo "🚀 Starting Frontend Server..."
echo "📖 Frontend: http://localhost:$FRONTEND_PORT"

# Start frontend in background
if command -v npm &> /dev/null; then
    npm run dev &
elif command -v yarn &> /dev/null; then
    yarn dev &
fi

FRONTEND_PID=$!

# Go back to root directory
cd ..

echo ""
echo "🎉 Full Stack Started Successfully!"
echo "=" * 60
echo "🌐 Frontend:  http://localhost:3000"
echo "🔧 Backend:   http://127.0.0.1:8002"
echo "📖 API Docs:  http://127.0.0.1:8002/docs"
echo "📊 Health:    http://127.0.0.1:8002/health"
echo "=" * 60
echo ""
echo "💡 Tips:"
echo "   • Use the chat interface on the frontend to interact with the assistant"
echo "   • Visit /docs for API documentation"
echo "   • Check /analytics for usage statistics"
echo "   • Press Ctrl+C to stop both servers"
echo ""
echo "🔄 Servers running... Press Ctrl+C to stop"

# Wait for user interrupt
wait