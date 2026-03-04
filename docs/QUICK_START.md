# Quick Start Guide: Setup & Deployment

This guide walks you through setting up and deploying any agent in this ecosystem.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Agent Selection & Installation](#agent-selection--installation)
4. [Database Configuration](#database-configuration)
5. [MCP Server Setup](#mcp-server-setup)
6. [Supervisor API Setup](#supervisor-api-setup)
7. [UI Configuration](#ui-configuration)
8. [Running the Agent](#running-the-agent)
9. [Verification & Testing](#verification--testing)
10. [Troubleshooting](#troubleshooting)
11. [Production Deployment](#production-deployment)

---

## Prerequisites

Before starting, ensure you have:

### System Requirements
- **Python**: 3.9 or higher
- **PostgreSQL**: 12 or higher
- **Redis**: 6 or higher (optional, for session memory)
- **OS**: Linux, macOS, or Windows (with WSL2)
- **Disk Space**: 5GB minimum

### Required API Keys
- **OpenAI**: `OPENAI_API_KEY` for GPT-4o/GPT-4o-mini access
- **Domain-Specific APIs**: Depending on chosen agent (GitHub, AWS, etc.)

### Installation Verification

```bash
# Python version
python --version
# Output: Python 3.9+

# PostgreSQL client
psql --version
# Output: psql (PostgreSQL) 12+

# Redis (optional)
redis-cli --version
# Output: redis-cli 6+
```

---

## Environment Setup

### 1. Clone the Repository

```bash
cd /path/to/agents
git clone <repository-url>
cd Agents
```

### 2. Create a Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Create Environment Configuration File

Create a `.env` file in your agent's root directory:

```bash
# Copy template if exists
cp .env.example .env

# Edit .env with your values
nano .env  # or use your editor
```

### 4. Basic .env Template

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_FALLBACK_MODEL=gpt-4o-mini

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/agent_db
DATABASE_ECHO=False  # Set True for SQL logging

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379/0
REDIS_ENABLED=True

# Server Configuration
SUPERVISOR_PORT=8000
MCP_SERVERS_START_PORT=8001

# API Keys (domain-specific)
GITHUB_TOKEN=ghp_...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# Application Settings
APP_ENV=development  # or production
DEBUG=False
LOG_LEVEL=INFO
```

---

## Agent Selection & Installation

### 1. Choose Your Agent

Browse the domain folders to find your agent:

```
01-Finance/
02-Cybersecurity/
03-ECommerce/
04-DataAnalytics/
05-DevOps/
06-Healthcare/
07-HumanResources/
08-BusinessIntelligence/
09-Education/
```

```bash
# Example: Choose Finance agent
cd 01-Finance/Automated-Financial-Report-Agent
```

### 2. Read Agent README

Every agent has a **README.md** with specific setup instructions. Read it first:

```bash
cat README.md
# Review configuration requirements
# Review specialist descriptions
# Review example usage
```

### 3. Install Dependencies

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Verify installation
pip list | grep langchain  # Check LangChain installed
pip list | grep fastapi    # Check FastAPI installed
pip list | grep streamlit  # Check Streamlit installed
```

### 4. Agent-Specific Dependencies

Some agents have additional requirements. Check the agent README:

```bash
# Example: HR agent with Redis dependency
pip install redis

# Example: Healthcare agent with Stripe
pip install stripe
```

---

## Database Configuration

### 1. Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE agent_db ENCODING 'UTF8';

# Create user (recommended)
CREATE USER agent_user WITH ENCRYPTED PASSWORD 'secure_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE agent_db TO agent_user;

# Exit
\q
```

### 2. Update .env with Database URL

```env
DATABASE_URL=postgresql://agent_user:secure_password@localhost:5432/agent_db
```

### 3. Initialize Database Schema

Run the database initialization script:

```bash
# From agent root directory
python database/init_db.py

# Output should indicate:
# ✓ Database connection successful
# ✓ Created tables: users, sessions, ...
# ✓ Applied migrations: v1_initial_schema
```

### 4. Verify Database

```bash
# Connect to your database
psql DATABASE_URL

# List tables
\dt

# Check specific table
\d tablename

# Exit
\q
```

---

## MCP Server Setup

### Understand MCP Servers

Each agent has one or more MCP servers in the `mcp_servers/` folder. These expose tools to the supervisor agent.

Example structure:
```
mcp_servers/
├── specialist_1_server.py   # Server 1 on port 8001
├── specialist_2_server.py   # Server 2 on port 8002
└── schemas.py               # Shared schemas
```

### 1. Verify MCP Server Configuration

Each server should look like:

```python
# In mcp_servers/specialist_server.py
from fastmcp import FastMCP

mcp = FastMCP("specialist-name", "1.0.0")

@mcp.tool()
async def tool_name(param1: str) -> dict:
    """Tool description."""
    # Implementation
    pass

if __name__ == "__main__":
    mcp.run(host="localhost", port=8001)
```

### 2. Manual MCP Server Testing (Optional)

```bash
# Terminal 1: Start MCP server
cd mcp_servers
python specialist_1_server.py
# Output: MCP Server running on http://localhost:8001

# Terminal 2: Test the server
curl http://localhost:8001/tools

# Output: List of available tools with schemas
```

### 3. MCP Server Port Configuration

Update `start_servers.py` to use correct ports:

```python
MCP_SERVERS = [
    {"name": "specialist_1", "port": 8001},
    {"name": "specialist_2", "port": 8002},
    {"name": "specialist_3", "port": 8003},
]
```

---

## Supervisor API Setup

### 1. Understand the Supervisor

The supervisor is the main agent that:
- Routes requests to appropriate specialists
- Orchestrates workflows
- Exposes a REST API

Located in: `supervisor/supervisor_server.py`

### 2. Test Supervisor API (Before Full Startup)

```bash
# Terminal 1: Ensure MCP servers running

# Terminal 2: Start supervisor manually
python -m uvicorn supervisor.supervisor_server:app \
    --host localhost \
    --port 8000 \
    --reload

# Output:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete
```

### 3. Access API Documentation

Once supervisor is running, visit:

```
http://localhost:8000/docs
```

You'll see:
- All available endpoints
- Request/response schemas
- "Try it out" functionality

### 4. Example API Call

```bash
# Using curl
curl -X POST http://localhost:8000/api/agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "request": "Your query here",
    "user_id": "user123"
  }'

# Using Python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/agent/process",
        json={
            "request": "Your query here",
            "user_id": "user123"
        }
    )
    print(response.json())
```

---

## UI Configuration

### 1. Understand Streamlit UI

The UI is the user-facing interface located in:
`ui/pages.py` and `ui/app.py`

### 2. Streamlit Configuration

Create `~/.streamlit/config.toml` for UI settings:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[client]
showErrorDetails = true

[server]
port = 8501
headless = true
```

### 3. Manual UI Testing

```bash
# Start Streamlit UI
streamlit run app.py

# Output:
# You can now view your Streamlit app in your browser.
# Local URL: http://localhost:8501
# Network URL: http://192.168.x.x:8501
```

### 4. Verify UI Components

Check that UI loads:
- ✓ Title and description display
- ✓ Input form loads
- ✓ Submit button functional
- ✓ API connection working

---

## Running the Agent

### 1. Complete Startup Script

The `start_servers.py` script handles the entire startup:

```bash
# From agent root directory
python start_servers.py
```

This starts:
1. PostgreSQL connection (via SQLAlchemy)
2. MCP servers (ports 8001+)
3. Supervisor API (port 8000)
4. Streamlit UI (port 8501)

### 2. Startup Output

```
Starting MCP Server 1 on port 8001...
✓ MCP Server 1 ready
Starting MCP Server 2 on port 8002...
✓ MCP Server 2 ready
Starting Supervisor API on port 8000...
✓ Supervisor API ready
Starting Streamlit UI...

You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

### 3. Access the Agent

```
Web UI: http://localhost:8501
API Docs: http://localhost:8000/docs
MCP Server 1: http://localhost:8001
MCP Server 2: http://localhost:8002
```

### 4. Graceful Shutdown

```bash
# Press Ctrl+C in terminal running start_servers.py

# Output:
# Shutting down Streamlit...
# Shutting down Supervisor API...
# Shutting down MCP servers...
# ✓ All servers stopped
```

---

## Verification & Testing

### 1. Health Check Endpoints

```bash
# Supervisor health
curl http://localhost:8000/health
# Output: {"status": "ok", "timestamp": "..."}

# MCP servers health
curl http://localhost:8000/mcp/health
# Output: {"servers": {"specialist-1": "ok", ...}}
```

### 2. Test a Simple Request

Via UI:
1. Navigate to http://localhost:8501
2. Enter a test request
3. Click Submit
4. Verify response appears

Via API:
```bash
curl -X POST http://localhost:8000/api/agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "request": "Test request",
    "user_id": "test_user"
  }' | jq .
```

### 3. Check Logs

```bash
# Supervisor logs
tail -f logs/supervisor.log

# MCP logs
tail -f logs/mcp.log

# Application logs
tail -f logs/app.log
```

### 4. Database Verification

```bash
# Connect to database
psql $DATABASE_URL

# Check tables exist
\dt

# Check recent operations
SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 5;

# Exit
\q
```

---

## Troubleshooting

### Issue: Database Connection Error

```
Error: could not connect to server: Connection refused
```

**Solution:**
```bash
# 1. Check PostgreSQL is running
brew services list  # macOS
sudo systemctl status postgresql  # Linux

# 2. Verify DATABASE_URL in .env
echo $DATABASE_URL

# 3. Test connection
psql $DATABASE_URL -c "SELECT 1"

# 4. Check port
lsof -i :5432  # See what's on port 5432
```

### Issue: Port Already in Use

```
Error: Address already in use
```

**Solution:**
```bash
# 1. Find process using port
lsof -i :8000  # For port 8000

# 2. Kill process
kill -9 <PID>

# 3. Or use different port
SUPERVISOR_PORT=8010 python start_servers.py
```

### Issue: OpenAI API Key Invalid

```
Error: Invalid API key provided
```

**Solution:**
```bash
# 1. Check key in .env
echo $OPENAI_API_KEY

# 2. Verify key starts with 'sk-'
# 3. Check key hasn't expired
# 4. Regenerate if needed at platform.openai.com

# 5. Reinstall with new key
export OPENAI_API_KEY=sk-...
python app.py
```

### Issue: MCP Server Not Responding

```
Error: Failed to connect to MCP server on port 8001
```

**Solution:**
```bash
# 1. Check if server is running
curl http://localhost:8001/tools

# 2. Check server logs
tail -f logs/mcp_8001.log

# 3. Verify port in config
grep MCP_SERVERS_START_PORT .env

# 4. Restart server
python mcp_servers/specialist_server.py
```

### Issue: Streamlit Not Loading

```
Error: ConnectionRefusedError: [Errno 111] Connection refused
```

**Solution:**
```bash
# 1. Check UI is running
curl http://localhost:8501

# 2. Check Streamlit logs
streamlit run app.py --logger.level=debug

# 3. Clear Streamlit cache
rm -rf ~/.streamlit

# 4. Restart UI
streamlit run app.py
```

---

## Production Deployment

### 1. Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy code
COPY . .

# Install Python dependencies
RUN pip install -r requirements.txt

# Expose ports
EXPOSE 8000 8001 8002 8501

# Run agent
CMD ["python", "start_servers.py"]
```

Build and run:

```bash
# Build image
docker build -t agent:latest .

# Run container
docker run -p 8000:8000 -p 8501:8501 \
  -e OPENAI_API_KEY=sk-... \
  -e DATABASE_URL=postgresql://... \
  agent:latest
```

### 2. Environment Management

Use environment variables for deployment:

```bash
# Production .env
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING

# Security
ALLOWED_HOSTS=*.example.com
CORS_ORIGINS=https://app.example.com

# Database
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis
REDIS_ENABLED=true
REDIS_URL=redis://redis-cluster:6379/0
```

### 3. Monitoring & Logging

```bash
# Set up centralized logging
LOG_DESTINATION=cloudwatch  # or splunk, datadog, etc.

# Enable health checks
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_PORT=8080

# Metrics collection
METRICS_ENABLED=true
PROMETHEUS_PORT=9090
```

### 4. Scaling Considerations

For production at scale:

- **Load Balancer**: Distribute requests across supervisor instances
- **Database Cluster**: PostgreSQL with read replicas
- **MCP Server Scaling**: Multiple instances per specialist
- **Cache**: Redis cluster for session memory
- **Monitoring**: Prometheus + Grafana or cloud-native tools

---

## Next Steps

1. **Read Agent-Specific README** - Each agent has unique configuration
2. **Explore ARCHITECTURE.md** - Understand the patterns
3. **Review DOMAIN_GUIDE.md** - Domain-specific implementation details
4. **Check API_REFERENCE.md** - API and MCP standards
5. **Deploy to Production** - Use Docker and environment management

For questions, refer to the specific agent's README in its domain folder.
