# Medicare Pro UI + SQL Agent Integration

This document explains how to run the integrated Medicare Pro UI with the SQL Agent backend.

## Overview

The integration consists of:
- **Backend**: FastAPI server (`api_server.py`) that exposes the SQL Agent functionality
- **Frontend**: Medicare Pro UI with an integrated chat component that communicates with the SQL Agent

## Prerequisites

1. **Python Environment**: Make sure you have Python 3.8+ installed
2. **Node.js**: Make sure you have Node.js 16+ installed
3. **Database**: Ensure your PostgreSQL database is running and accessible
4. **Environment Variables**: Set up your Azure OpenAI or OpenAI API credentials

## Quick Start

### Option 1: Using the Startup Scripts (Recommended)

1. **Start the Backend Server**:
   ```bash
   ./start_backend.sh
   ```
   This will:
   - Activate the virtual environment
   - Install Python dependencies
   - Start the FastAPI server at `http://localhost:8000`

2. **Start the Frontend** (in a new terminal):
   ```bash
   ./start_frontend.sh
   ```
   This will:
   - Install npm dependencies
   - Start the Vite development server at `http://localhost:5173`

### Option 2: Manual Setup

1. **Backend Setup**:
   ```bash
   # Activate virtual environment
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Start the API server
   python api_server.py
   ```

2. **Frontend Setup**:
   ```bash
   # Navigate to UI directory
   cd ui
   
   # Install dependencies
   npm install
   
   # Start development server
   npm run dev
   ```

## API Endpoints

The FastAPI server provides the following endpoints:

- `GET /` - Health check
- `POST /chat` - Main chat endpoint for SQL queries
- `GET /health` - Detailed health check
- `POST /end_session` - End a chat session
- `GET /docs` - FastAPI auto-generated documentation

## Chat Component Features

The integrated chat component includes:

### 🔧 **Settings Panel**
- Configurable API endpoint (defaults to `http://localhost:8000/chat`)
- Connection status indicator
- Real-time endpoint validation

### 💬 **Chat Interface**
- Session-based conversations
- Loading indicators
- Error handling with helpful messages
- SQL query display in responses
- Result count information

### 🏥 **Healthcare Focus**
- Healthcare-specific welcome message
- Database-oriented placeholder text
- Medical terminology awareness

## Usage Examples

Once both servers are running, you can ask questions like:

- "How many patients do we have?"
- "Show me patients with diabetes"
- "What are the most common medical conditions?"
- "List medications prescribed for hypertension"
- "Find patients born after 1990"

## API Request/Response Format

### Request Format
```json
{
  "message": "How many patients do we have?",
  "session_id": "web_1234567890",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Response Format
```json
{
  "response": "Based on your database, you have 1,234 patients.",
  "session_id": "web_1234567890",
  "timestamp": "2024-01-01T12:00:00Z",
  "success": true,
  "sql_generated": "SELECT COUNT(*) FROM patients;",
  "data": [{"count": 1234}],
  "result_count": 1
}
```

## Configuration

### Environment Variables
Make sure to set up your API credentials in `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
DATABASE_URL=your_database_connection_string
```

### Database Configuration
The SQL Agent is configured to work with PostgreSQL. Make sure your database is accessible and the connection string is properly configured.

## Troubleshooting

### Common Issues

1. **CORS Errors**: Make sure the FastAPI server is running on `http://localhost:8000`
2. **Database Connection**: Verify your database is running and accessible
3. **API Credentials**: Check that your OpenAI/Azure OpenAI credentials are correctly set
4. **Port Conflicts**: Ensure ports 8000 (backend) and 5173 (frontend) are available

### Debug Steps

1. Check if the backend is running: `curl http://localhost:8000/health`
2. Check the browser console for any JavaScript errors
3. Verify the API endpoint in the chat settings panel
4. Check the FastAPI logs for any server errors

## Development

### File Structure
```
agent_ai/
├── api_server.py              # FastAPI backend server
├── start_backend.sh           # Backend startup script
├── start_frontend.sh          # Frontend startup script
├── ui/                        # Medicare Pro UI
│   ├── src/
│   │   ├── components/
│   │   │   └── ChatButton.tsx # Enhanced chat component
│   │   └── pages/
│   │       └── Index.tsx      # Main page with chat
│   └── package.json
├── src/                       # SQL Agent source code
│   ├── agents/
│   ├── database/
│   └── ...
└── requirements.txt
```

### Making Changes

- **Backend Changes**: Modify `api_server.py` or the SQL Agent code in `src/`
- **Frontend Changes**: Modify the React components in `ui/src/`
- **Chat Component**: Main chat logic is in `ui/src/components/ChatButton.tsx`

## Production Deployment

For production deployment:

1. **Backend**: Use a production WSGI server like Gunicorn
2. **Frontend**: Build the React app with `npm run build`
3. **Environment**: Set proper environment variables
4. **CORS**: Configure CORS properly for your domain
5. **Database**: Use connection pooling and proper security

## Support

If you encounter issues:
1. Check the console logs (both frontend and backend)
2. Verify all dependencies are installed
3. Ensure the database is accessible
4. Check API credentials and permissions


## Screenshot for the Same 
https://ibb.co/ZptQnjvp
https://ibb.co/GQ1ZDSvC
