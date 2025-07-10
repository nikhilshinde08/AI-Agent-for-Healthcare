#!/bin/bash

echo "🚀 Starting Medicare Pro UI Frontend..."
echo "🌐 Frontend will be available at: http://localhost:5173"
echo ""

# Kill any existing processes on port 5173
echo "🔧 Checking for existing processes on port 5173..."
PORT_PID=$(lsof -ti:5173)
if [ ! -z "$PORT_PID" ]; then
    echo "🔧 Killing existing process on port 5173 (PID: $PORT_PID)..."
    kill -9 $PORT_PID
    sleep 2
fi

# Navigate to UI directory
cd ui

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "🔧 Installing npm dependencies..."
    npm install
fi

# Start the development server
echo "🚀 Starting Vite development server..."
npm run dev