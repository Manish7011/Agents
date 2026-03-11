# ⚖️ Contract Intelligence Platform

AI-powered multi-agent contract lifecycle management system.

## Architecture

- **7 Specialist Agents** — each with their own MCP server (ports 8001–8007)
- **Supervisor Agent** — FastAPI orchestrator with LangGraph (port 8000)
- **Streamlit UI** — role-based web interface (port 9001)

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env .env.local
# Edit .env — set OPENAI_API_KEY and DATABASE_URL
```

### 3. Start MCP agent servers (Terminal 1)
```bash
python start_servers.py
```
This starts: 7 MCP agent servers + auto-initialises database

### 4. Start Supervisor API (Terminal 2)
```bash
python start_supervisor.py
```

### 5. Start the UI (Terminal 3)
```bash
streamlit run app.py --server.port 9001
```

Open **http://localhost:9001**

## Demo Login Accounts

| Email | Password | Role |
|-------|----------|------|
| admin@contract.ai | Admin@123 | Admin |
| legal@contract.ai | Legal@123 | Legal Counsel |
| manager@contract.ai | Manager@123 | Contract Manager |
| procure@contract.ai | Procure@123 | Procurement |
| finance@contract.ai | Finance@123 | Finance |
| viewer@contract.ai | Viewer@123 | Viewer |

## Agent Ports

| Agent | Port |
|-------|------|
| Supervisor API | 8000 |
| Draft Agent | 8001 |
| Review & Risk Agent | 8002 |
| Approval Agent | 8003 |
| Execution Agent | 8004 |
| Obligation Agent | 8005 |
| Compliance Agent | 8006 |
| Analytics Agent | 8007 |
| Streamlit UI | 9001 |
