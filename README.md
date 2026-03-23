# AgentSandbox

Enterprise simulation layer for previewing Claude agent actions in a sandboxed environment.

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 to use the app. The frontend proxies API requests to the backend on port 8000.

## Architecture

- **Backend**: FastAPI + SQLite + Anthropic SDK
- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **Mock Tools**: read_file, write_file, send_email, http_request, query_database
- **Streaming**: WebSocket for live action timeline during runs
