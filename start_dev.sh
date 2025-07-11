#!/bin/bash

# Healthcare Database Assistant - Development Mode Startup Script
# Starts both the original CLI and the new FastAPI server

set -e

echo "🚀 Starting Healthcare Database Assistant in Development Mode..."

# Function to start the original CLI
start_cli() {
    echo "📱 Starting Original CLI Interface..."
    python main.py
}

# Function to start the FastAPI server
start_api() {
    echo "🌐 Starting FastAPI Server..."
    ./start_backend.sh
}

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

echo ""
echo "🎯 Choose interface:"
echo "1. Original CLI Interface (main.py)"
echo "2. FastAPI Server (api_server.py)"
echo "3. Both (CLI first, then API server)"
echo ""

read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        start_cli
        ;;
    2)
        start_api
        ;;
    3)
        echo "📱 Starting CLI first. When done, the API server will start."
        start_cli
        echo "🌐 Now starting FastAPI server..."
        start_api
        ;;
    *)
        echo "Invalid choice. Starting CLI interface..."
        start_cli
        ;;
esac

echo "👋 Development session ended."