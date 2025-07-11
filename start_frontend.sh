#!/bin/bash

# Healthcare Database Assistant - Frontend Startup Script
# React + Vite frontend for the Healthcare Assistant

set -e

echo "🌐 Starting Healthcare Database Assistant Frontend..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ and try again."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    echo "❌ Node.js version 16+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js version: $(node -v)"

# Navigate to frontend directory
cd frontend

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "❌ package.json not found. Make sure you're in the correct directory."
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    if command -v npm &> /dev/null; then
        npm install
    elif command -v yarn &> /dev/null; then
        yarn install
    else
        echo "❌ No package manager found. Please install npm or yarn."
        exit 1
    fi
else
    echo "📦 Dependencies already installed"
fi

# Check if backend is running
echo "🔍 Checking backend availability..."
if curl -s http://127.0.0.1:8002/health > /dev/null; then
    echo "✅ Backend is running at http://127.0.0.1:8002"
else
    echo "⚠️  Backend not detected at http://127.0.0.1:8002"
    echo "   Please start the backend first with: ./start_backend.sh"
    echo "   Or start both with: ./start_full_stack.sh"
    echo ""
    echo "   Continuing with frontend startup..."
fi

# Kill any existing process on port 3000
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "🔄 Killing existing process on port 3000..."
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
    sleep 2
    echo "✅ Port 3000 is now available"
fi

echo ""
echo "🚀 Starting Frontend Development Server..."
echo "📖 Frontend will be available at: http://localhost:3000"
echo "🔗 Backend API endpoint: http://127.0.0.1:8002"
echo "🔄 Press Ctrl+C to stop the frontend server"
echo ""

# Start the development server
if command -v npm &> /dev/null; then
    npm run dev
elif command -v yarn &> /dev/null; then
    yarn dev
else
    echo "❌ No package manager found to start the dev server."
    exit 1
fi