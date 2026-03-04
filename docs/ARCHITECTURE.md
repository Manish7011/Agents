# Architecture Guide: Multi-Agent Ecosystem Patterns

This document provides a deep dive into the architectural patterns, design decisions, and principles that govern the entire agent ecosystem.

---

## Table of Contents

1. [Core Pattern: Supervisor + Specialist](#core-pattern-supervisor--specialist)
2. [Technical Stack Overview](#technical-stack-overview)
3. [Component Architecture](#component-architecture)
4. [Agent Lifecycle](#agent-lifecycle)
5. [State Management with LangGraph](#state-management-with-langgraph)
6. [MCP: Tool Protocol & Integration](#mcp-tool-protocol--integration)
7. [Data Persistence Patterns](#data-persistence-patterns)
8. [Security & Access Control](#security--access-control)
9. [Deployment & Scalability](#deployment--scalability)
10. [Common Design Patterns](#common-design-patterns)

---

## Core Pattern: Supervisor + Specialist

### Overview

Every agent in this ecosystem follows the **Supervisor + Specialist Multi-Agent Pattern**:

```
User Request
     ↓
┌─────────────────┐
│   SUPERVISOR    │  ← Routes requests to specialists
│   AGENT         │  ← Orchestrates workflow
└────────┬────────┘
         │
    ┌────┴─────────────┐
    ↓                  ↓
┌───────────┐   ┌───────────┐
│Specialist1│   │Specialist2│
│  (Finance)│   │(Reporting)│
└────┬──────┘   └────┬──────┘
     │               │
     └───────┬───────┘
             ↓
        ┌─────────────┐
        │ MCP Tools   │
        │ (Database,  │
        │  APIs, etc) │
        └─────────────┘
             ↓
        Response
```

### Why This Pattern?

**1. Modularity**
- Each specialist handles a specific domain/responsibility
- Changes to one specialist don't affect others
- Easy to reason about and test in isolation

**2. Scalability**
- Add new specialists without redesigning the supervisor
- Remove or update specialists independently
- Handle growing request complexity

**3. Resilience**
- If one specialist fails, others continue
- Load can be distributed across specialists
- Retry logic can be specialist-specific

**4. Maintainability**
- Clear separation of concerns
- Each specialist has a focused purpose
- Easier onboarding for new engineers

**5. Extensibility**
- Tools are exposed via MCP (Model Context Protocol)
- Specialists can access tools without tight coupling
- New tools can be added without agent code changes

### Key Components

**Supervisor:**
- Receives user requests
- Understands user intent via LLM
- Routes to appropriate specialists
- Orchestrates multi-step workflows
- Aggregates specialist responses
- Error handling and retries

**Specialists:**
- Domain-specific agents
- Handle specific workflows/operations
- Call MCP tools for execution
- Return structured results
- May invoke other specialists

**MCP Tools:**
- Database queries
- API calls
- External service integrations
- Custom business logic
- Data transformation

---

## Technical Stack Overview

### LLM Backbone
- **OpenAI GPT-4o** (for complex reasoning)
- **OpenAI GPT-4o-mini** (for simpler tasks, cost optimization)
- Function calling / tool calling capabilities

### Agent Orchestration
- **LangGraph**: State management, graph-based routing, execution
- **LangChain**: Foundation for building chains and tools
- **Pydantic**: Structured output schemas

### Tool Protocol
- **MCP (Model Context Protocol)**: Standardized tool exposure
- **FastMCP**: HTTP-based MCP server implementation
- JSON-RPC communication between agents and tools

### Backend Services
- **FastAPI**: REST API framework for supervisor agents
- **Uvicorn**: ASGI server for async request handling
- **Pydantic**: Request/response validation

### Data Layer
- **PostgreSQL**: Primary persistent data store
- **Redis**: Session memory, caching, distributed state
- **SQLAlchemy**: ORM for database operations

### User Interface
- **Streamlit**: Interactive web UI for agent interactions
- **Python native**: No separate frontend required

### Supporting Libraries
- **httpx**: Async HTTP client for MCP communication
- **logging**: Structured logging and audit trails
- **pytest**: Testing framework

---

## Component Architecture

### Standard Agent Structure

Each agent follows a consistent folder structure:

```
agent-name/
├── supervisor/
│   ├── supervisor_server.py     (FastAPI app with supervisor logic)
│   └── graph.py                 (LangGraph graph definition)
│
├── mcp_servers/
│   ├── __init__.py
│   ├── server_1.py              (MCP server implementation)
│   ├── server_2.py              (Additional servers)
│   └── schemas.py               (Shared tool schemas)
│
├── database/
│   ├── __init__.py
│   ├── db.py                    (SQLAlchemy models)
│   └── init_db.py               (Database initialization)
│
├── ui/
│   ├── __init__.py
│   ├── pages.py                 (Streamlit pages)
│   ├── components.py            (Reusable UI widgets)
│   ├── services.py              (UI business logic)
│   ├── config.py                (UI configuration)
│   └── styles.py                (CSS/styling)
│
├── utils/
│   ├── __init__.py
│   ├── auth.py                  (RBAC, permissions)
│   ├── logger.py                (Audit logging)
│   ├── config.py                (Shared configuration)
│   └── constants.py             (Shared constants)
│
├── app.py                       (Main UI entrypoint)
├── start_servers.py             (Start all servers)
├── requirements.txt             (Python dependencies)
└── README.md                    (Agent documentation)
```

### Component Responsibilities

**supervisor_server.py**
- FastAPI application
- Endpoint for supervisor requests
- Server lifecycle management
- Health checks

**graph.py**
- LangGraph StateGraph definition
- Node definitions (supervisor, specialists)
- Edge/routing logic
- Tool calling configuration

**mcp_servers/\*.py**
- FastMCP server implementations
- Tool function definitions
- Request validation
- Error handling
- Database interactions

**database/db.py**
- SQLAlchemy ORM models
- Database schema
- Relationships and constraints

**ui/pages.py**
- Streamlit page definitions
- State management
- Event handlers
- API calls to supervisor

**utils/auth.py**
- RBAC implementation
- Permission checking
- User context management

**utils/logger.py**
- Structured logging
- Audit trail recording
- Event tracking

---

## Agent Lifecycle

### 1. Startup Phase

```
1. Load configuration
2. Initialize database connection
3. Create SQLAlchemy session factory
4. Start MCP servers (FastMCP)
5. Initialize LangGraph graph
6. Start supervisor FastAPI server
7. Start Streamlit UI (if configured)
```

**Implementation in start_servers.py:**
```python
# Pseudo-code showing lifecycle
if __name__ == "__main__":
    # 1. Config & DB
    init_db()  # Create tables, migrations
    
    # 2. MCP Servers (background processes)
    mcp_process_1 = start_mcp_server(specialist_1_server, port=8001)
    mcp_process_2 = start_mcp_server(specialist_2_server, port=8002)
    
    # 3. Supervisor API (background)
    api_process = start_supervisor_server(port=8000)
    
    # 4. Streamlit UI (foreground)
    start_streamlit_ui()
```

### 2. Request Handling

```
1. User submits request via Streamlit UI
2. UI calls supervisor API endpoint
3. Supervisor LangGraph invokes:
   a. Intent classification node
   b. Specialist selection node
   c. Tool calling node (via MCP)
   d. Response aggregation node
4. Specialist executes:
   a. Validation
   b. MCP tool calls
   c. Data processing
   d. Result formatting
5. MCP tool executes:
   a. Database queries
   b. External API calls
   c. Business logic
6. Results bubble back up
7. UI displays response
```

### 3. Shutdown Phase

```
1. Stop accepting new requests
2. Wait for in-flight requests to complete
3. Close database connections
4. Shutdown MCP servers
5. Shutdown FastAPI server
6. Clean up resources
```

---

## State Management with LangGraph

### Graph Structure

LangGraph represents agent logic as a graph with nodes and edges:

```python
from langgraph.graph import StateGraph
from typing import TypedDict, Annotated

# 1. Define State
class AgentState(TypedDict):
    user_request: str
    intent: str  # Classified intent
    specialist: str  # Selected specialist
    tool_calls: list  # Tools to invoke
    results: dict  # Tool execution results
    final_response: str

# 2. Create Graph
graph = StateGraph(AgentState)

# 3. Add Nodes
graph.add_node("classify_intent", classify_intent_node)
graph.add_node("select_specialist", select_specialist_node)
graph.add_node("specialist_1", specialist_1_node)
graph.add_node("specialist_2", specialist_2_node)
graph.add_node("aggregate_results", aggregate_results_node)

# 4. Add Edges with Routing
graph.add_edge("classify_intent", "select_specialist")
graph.add_conditional_edges(
    "select_specialist",
    route_to_specialist,  # Decision function
    {
        "specialist_1": "specialist_1",
        "specialist_2": "specialist_2",
    }
)
graph.add_edge("specialist_1", "aggregate_results")
graph.add_edge("specialist_2", "aggregate_results")

# 5. Set Entry & Exit
graph.set_entry_point("classify_intent")
graph.set_finish_point("aggregate_results")

# 6. Compile
runnable = graph.compile()
```

### Node Implementation Pattern

```python
async def specialist_node(state: AgentState) -> dict:
    """Specialist node executing business logic."""
    
    # 1. Extract relevant state
    request = state["user_request"]
    
    # 2. Prepare tool calls
    tools_schema = [
        {
            "name": "tool_1",
            "description": "...",
            "input_schema": {...}
        }
    ]
    
    # 3. Invoke LLM with tools
    response = await llm.ainvoke(
        prompt,
        tools=tools_schema
    )
    
    # 4. Extract and execute tools
    tool_calls = response.tool_calls
    tool_results = []
    
    for tool_call in tool_calls:
        result = await execute_mcp_tool(
            tool_call["name"],
            tool_call["args"]
        )
        tool_results.append(result)
    
    # 5. Return state updates
    return {
        "tool_calls": tool_calls,
        "results": {
            "specialist": "specialist_1",
            "data": tool_results
        }
    }
```

### State Mutation & Immutability

- State updates are merged with existing state
- Each node returns a dict of updates
- Previous state values are preserved
- Enables error recovery and debugging

---

## MCP: Tool Protocol & Integration

### Model Context Protocol (MCP)

MCP is a standardized protocol for exposing tools to LLMs:

**Benefits:**
- Decouples tools from agents (tools can be versioned independently)
- Standardized tool discovery and invocation
- Easy to compose multiple tool servers
- Language-agnostic communication

### MCP Server Implementation (FastMCP)

```python
from fastmcp import FastMCP

# 1. Create server
mcp = FastMCP("specialist-server", "1.0.0")

# 2. Register tools
@mcp.tool()
async def get_user_data(user_id: int) -> dict:
    """Fetch user data from database."""
    db = get_db_session()
    user = db.query(User).filter(User.id == user_id).first()
    return user.to_dict()

@mcp.tool()
async def update_user(user_id: int, **updates) -> dict:
    """Update user in database."""
    db = get_db_session()
    user = db.query(User).filter(User.id == user_id).first()
    for key, value in updates.items():
        setattr(user, key, value)
    db.commit()
    return {"success": True, "user": user.to_dict()}

# 3. Tool schema is auto-generated from function signatures
# 4. Server handles HTTP requests (JSON-RPC)
if __name__ == "__main__":
    mcp.run(host="localhost", port=8001)
```

### Tool Schema Generation

FastMCP automatically generates OpenAPI/JSON-Schema from function signatures:

```python
@mcp.tool()
async def process_order(
    order_id: int,
    action: str  # Enum: "approve", "reject", "review"
) -> OrderResult:
    """
    Process a customer order.
    
    Args:
        order_id: Unique order identifier
        action: Action to take on the order
    
    Returns:
        OrderResult with status and details
    """
    ...
```

Becomes:

```json
{
  "name": "process_order",
  "description": "Process a customer order.",
  "input_schema": {
    "type": "object",
    "properties": {
      "order_id": {
        "type": "integer",
        "description": "Unique order identifier"
      },
      "action": {
        "type": "string",
        "enum": ["approve", "reject", "review"],
        "description": "Action to take on the order"
      }
    },
    "required": ["order_id", "action"]
  }
}
```

### Tool Invocation Pattern

```python
async def invoke_mcp_tool(tool_name: str, args: dict) -> any:
    """Generic MCP tool invoker."""
    
    # 1. Discover available tools from MCP server
    tools_response = await client.request("tools/list", {})
    
    # 2. Find matching tool
    tool = next(
        (t for t in tools_response["tools"] if t["name"] == tool_name),
        None
    )
    if not tool:
        raise ValueError(f"Tool {tool_name} not found")
    
    # 3. Validate arguments
    validate_arguments(args, tool["input_schema"])
    
    # 4. Invoke tool
    result = await client.request("tools/call", {
        "name": tool_name,
        "arguments": args
    })
    
    return result["content"][0]["text"]
```

---

## Data Persistence Patterns

### PostgreSQL with SQLAlchemy

All agents use SQLAlchemy for database abstraction:

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

### Session Management

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 1. Create engine (connection pool)
engine = create_engine(
    "postgresql://user:pass@localhost/db",
    pool_size=10,
    max_overflow=20
)

# 2. Create session factory
SessionLocal = sessionmaker(bind=engine)

# 3. Use in context manager
with SessionLocal() as session:
    user = session.query(User).filter(User.id == 1).first()
    user.name = "Updated"
    session.commit()
```

### Redis Session Memory

For agents that maintain conversation memory:

```python
import redis
import json

redis_client = redis.Redis(host="localhost", port=6379)

# Store session
session_state = {
    "user_context": {...},
    "conversation_history": [...]
}
redis_client.set(
    f"session:{session_id}",
    json.dumps(session_state),
    ex=3600  # 1 hour expiry
)

# Retrieve session
state = json.loads(redis_client.get(f"session:{session_id}"))
```

---

## Security & Access Control

### Role-Based Access Control (RBAC)

Standard RBAC pattern using roles and permissions:

```python
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"

class Permission(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

# Define role-permission mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.DELETE],
    Role.ANALYST: [Permission.CREATE, Permission.READ, Permission.UPDATE],
    Role.VIEWER: [Permission.READ],
}

def check_permission(user_role: Role, required_permission: Permission) -> bool:
    """Check if user role has required permission."""
    return required_permission in ROLE_PERMISSIONS.get(user_role, [])
```

### Authentication Context

```python
class UserContext:
    """Represents authenticated user context."""
    
    def __init__(self, user_id: str, email: str, role: Role):
        self.user_id = user_id
        self.email = email
        self.role = role
    
    def has_permission(self, permission: Permission) -> bool:
        return check_permission(self.role, permission)

# Obtain context in node
async def specialist_node(state: AgentState, user_context: UserContext) -> dict:
    """Node with user context."""
    
    # Check permission
    if not user_context.has_permission(Permission.UPDATE):
        raise PermissionError("User lacks UPDATE permission")
    
    # Proceed with operation
    ...
```

### Audit Logging

All operations logged with user context:

```python
def log_operation(
    operation: str,
    resource: str,
    user_id: str,
    result: str,
    details: dict = None
) -> None:
    """Log operation for audit trail."""
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "operation": operation,
        "resource": resource,
        "user_id": user_id,
        "result": result,  # success, failure, denied
        "details": details or {}
    }
    
    # Log to database, file, or external service
    logger.info(json.dumps(log_entry))
```

---

## Deployment & Scalability

### Docker Deployment

Each agent can be containerized:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Start all servers
CMD ["python", "start_servers.py"]
```

### Multi-Process Architecture

`start_servers.py` launches multiple processes:

```python
import subprocess
import time

def start_servers():
    """Start MCP servers and UI concurrently."""
    
    processes = []
    
    # Start MCP servers (background)
    for port in [8001, 8002, 8003]:
        proc = subprocess.Popen(
            [sys.executable, "mcp_servers/server.py", str(port)]
        )
        processes.append(proc)
        time.sleep(0.5)  # Stagger startup
    
    # Start supervisor API (background)
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "supervisor.supervisor_server:app", "--port", "8000"]
    )
    processes.append(api_proc)
    
    # Start Streamlit UI (foreground)
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "app.py"]
        )
    finally:
        # Cleanup on exit
        for proc in processes:
            proc.terminate()
```

### Horizontal Scaling

For production deployments:

1. **Database**: PostgreSQL cluster with replication
2. **MCP Servers**: Multiple instances behind load balancer
3. **Supervisor API**: FastAPI with uvicorn workers, load balanced
4. **UI**: Streamlit server with session affinity (sticky sessions)
5. **Cache**: Redis cluster for distributed session memory

---

## Common Design Patterns

### Error Handling & Retries

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_mcp_tool_with_retry(tool_name: str, args: dict) -> any:
    """Call MCP tool with automatic retries on failure."""
    return await invoke_mcp_tool(tool_name, args)
```

### Tool Result Handling

```python
from typing import Union

class ToolSuccess:
    def __init__(self, data: any):
        self.data = data
        self.success = True

class ToolError:
    def __init__(self, error: str, code: str = None):
        self.error = error
        self.code = code
        self.success = False

# In specialist node
try:
    result = await invoke_mcp_tool(tool_name, args)
    tool_result = ToolSuccess(result)
except Exception as e:
    tool_result = ToolError(str(e), "TOOL_FAILED")

return {"tool_result": tool_result}
```

### Conditional Routing

```python
def route_to_specialist(state: AgentState) -> str:
    """Route request to appropriate specialist based on intent."""
    
    intent = state.get("intent", "").lower()
    
    if "financial" in intent:
        return "specialist_finance"
    elif "reporting" in intent:
        return "specialist_reporting"
    else:
        return "specialist_default"
```

### Parallel Tool Execution

```python
import asyncio

async def call_multiple_tools_parallel(tools: list) -> dict:
    """Execute multiple MCP tool calls in parallel."""
    
    tasks = [
        invoke_mcp_tool(tool["name"], tool["args"])
        for tool in tools
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {tool["name"]: result for tool, result in zip(tools, results)}
```

---

## Summary

The architecture enables:

✅ **Modularity** - Specialists operate independently  
✅ **Extensibility** - Tools via MCP, new specialists easily added  
✅ **Scalability** - Horizontal scaling at each layer  
✅ **Maintainability** - Clear patterns applied consistently  
✅ **Reliability** - Error handling, retries, audit logging  
✅ **Security** - RBAC, credential management, audit trails  
✅ **Testability** - Components tested in isolation  

For implementation examples, refer to specific agent READMEs in their domain folders.
