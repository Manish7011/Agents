# API Reference: MCP Tools & FastAPI Standards

This document provides technical reference for building MCP tools and FastAPI endpoints in the agent ecosystem.

---

## Table of Contents

1. [MCP Tool Development](#mcp-tool-development)
2. [Tool Schema Standards](#tool-schema-standards)
3. [FastAPI Endpoint Patterns](#fastapi-endpoint-patterns)
4. [Request/Response Standards](#requestresponse-standards)
5. [Error Handling](#error-handling)
6. [Authentication & Authorization](#authentication--authorization)
7. [Data Validation](#data-validation)
8. [Async Patterns](#async-patterns)
9. [Testing MCP Tools](#testing-mcp-tools)
10. [Best Practices](#best-practices)

---

## MCP Tool Development

### What are MCP Tools?

MCP (Model Context Protocol) tools are functions that agents can invoke to perform operations. They're standardized, discoverable, and language-agnostic.

### Basic Tool Structure

```python
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional

# Create MCP server
mcp = FastMCP("specialist-name", "1.0.0")

# Define request/response models
class GetUserRequest(BaseModel):
    user_id: int = Field(..., description="Unique user identifier")
    include_details: bool = Field(False, description="Include full details")

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    status: str

# Register tool
@mcp.tool()
async def get_user(user_id: int, include_details: bool = False) -> UserResponse:
    """
    Fetch a user by ID.
    
    Args:
        user_id: The unique user identifier
        include_details: Whether to include full user details
    
    Returns:
        UserResponse containing user information
    """
    # Implementation
    db = get_db_session()
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        status=user.status
    )

# Run server
if __name__ == "__main__":
    mcp.run(host="localhost", port=8001)
```

### Tool Registration in Supervisor

```python
from langgraph.graph import StateGraph

# Define state
class AgentState(TypedDict):
    user_request: str
    tools: List[dict]
    tool_results: dict

# Create graph
graph = StateGraph(AgentState)

# Define node that uses tools
async def specialist_node(state: AgentState) -> dict:
    """Node that calls MCP tools."""
    
    # 1. Get available tools from MCP server
    tools_list = await get_mcp_tools(server_port=8001)
    
    # 2. Call LLM with tools
    llm_response = await llm.ainvoke(
        prompt=state["user_request"],
        tools=tools_list
    )
    
    # 3. Execute tool calls
    for tool_call in llm_response.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        # Call MCP tool
        result = await invoke_mcp_tool(
            server_port=8001,
            tool_name=tool_name,
            args=tool_args
        )
        
        state["tool_results"][tool_name] = result
    
    return {"tool_results": state["tool_results"]}

# Add node to graph
graph.add_node("specialist", specialist_node)
```

---

## Tool Schema Standards

### Auto-Generated Schemas (FastMCP)

FastMCP automatically generates tool schemas from function signatures:

```python
@mcp.tool()
async def create_order(
    customer_id: int,
    items: List[dict],  # List of {product_id, quantity}
    priority: str = "normal"  # Default value
) -> OrderResponse:
    """Create a new customer order."""
    pass
```

Becomes:

```json
{
  "type": "function",
  "function": {
    "name": "create_order",
    "description": "Create a new customer order.",
    "parameters": {
      "type": "object",
      "properties": {
        "customer_id": {
          "type": "integer",
          "description": "Customer identifier"
        },
        "items": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "product_id": {"type": "integer"},
              "quantity": {"type": "integer"}
            },
            "required": ["product_id", "quantity"]
          },
          "description": "List of {product_id, quantity}"
        },
        "priority": {
          "type": "string",
          "enum": ["normal", "express", "standard"],
          "description": "Order priority",
          "default": "normal"
        }
      },
      "required": ["customer_id", "items"]
    }
  }
}
```

### Enum Parameters

```python
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"

@mcp.tool()
async def update_order_status(
    order_id: int,
    status: OrderStatus  # Becomes enum in schema
) -> dict:
    """Update order status."""
    pass
```

### Complex Types

```python
from typing import Optional, List
from datetime import datetime, date

@mcp.tool()
async def search_orders(
    customer_id: Optional[int] = None,  # Optional parameter
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    statuses: List[str] = [],  # Array parameter
) -> List[OrderResponse]:
    """Search orders with filters."""
    pass
```

---

## FastAPI Endpoint Patterns

### Supervisor API Structure

The supervisor exposes a REST API via FastAPI:

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional

# Create app
app = FastAPI(
    title="Supervisor API",
    description="Main agent endpoint",
    version="1.0.0"
)

# Define request/response models
class ProcessRequest(BaseModel):
    request: str = Field(..., description="User request to process")
    user_id: str = Field(..., description="Authenticated user ID")
    context: Optional[dict] = Field(None, description="Additional context")

class ProcessResponse(BaseModel):
    request_id: str
    status: str  # success, error, pending
    result: Optional[dict] = None
    error: Optional[str] = None
    timestamp: str

# Health check endpoint
@app.get("/health", response_model=dict)
async def health_check():
    """Check if supervisor is running."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }

# Main processing endpoint
@app.post("/api/agent/process", response_model=ProcessResponse)
async def process_request(
    request: ProcessRequest,
    user_context: UserContext = Depends(get_user_context)
) -> ProcessResponse:
    """
    Process a request using the supervisor agent.
    
    Args:
        request: ProcessRequest with user query
        user_context: Authenticated user context (auto-injected)
    
    Returns:
        ProcessResponse with result or error
    """
    try:
        # Check permissions
        if not user_context.has_permission("process"):
            raise HTTPException(
                status_code=403,
                detail="User lacks required permission"
            )
        
        # Create request ID for tracking
        request_id = str(uuid.uuid4())
        
        # Log operation
        log_operation(
            operation="process_request",
            resource="agent",
            user_id=user_context.user_id,
            request_id=request_id
        )
        
        # Run LangGraph
        result = await run_agent_graph(
            user_request=request.request,
            user_context=user_context,
            context=request.context
        )
        
        return ProcessResponse(
            request_id=request_id,
            status="success",
            result=result,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except ValidationError as e:
        return ProcessResponse(
            request_id=None,
            status="error",
            error=f"Validation error: {str(e)}",
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        log_error(str(e), user_id=user_context.user_id)
        return ProcessResponse(
            request_id=None,
            status="error",
            error="Internal server error",
            timestamp=datetime.utcnow().isoformat()
        )

# Async endpoint
@app.post("/api/agent/process-async")
async def process_request_async(
    request: ProcessRequest,
    user_context: UserContext = Depends(get_user_context)
) -> dict:
    """Process request asynchronously and return job ID."""
    
    job_id = str(uuid.uuid4())
    
    # Queue the job
    await queue_job(
        job_id=job_id,
        request=request,
        user_context=user_context
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "check_url": f"/api/jobs/{job_id}"
    }

# Check job status
@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Check status of async job."""
    
    job = await get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        "status": job.status,
        "result": job.result if job.status == "completed" else None,
        "error": job.error if job.status == "failed" else None
    }
```

### Pagination Pattern

```python
from fastapi import Query

class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    pages: int

@app.get("/api/items", response_model=PaginatedResponse)
async def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """List items with pagination."""
    
    db = get_db_session()
    query = db.query(Item)
    
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse(
        items=[item.to_dict() for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )
```

---

## Request/Response Standards

### Standard Response Format

All responses follow this format:

```json
{
  "success": true,
  "data": {
    "id": 123,
    "name": "Example"
  },
  "error": null,
  "timestamp": "2024-03-04T10:30:00Z",
  "request_id": "uuid-here"
}
```

### Error Response Format

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  },
  "timestamp": "2024-03-04T10:30:00Z",
  "request_id": "uuid-here"
}
```

### Implementation in FastAPI

```python
class StandardResponse(BaseModel):
    success: bool
    data: Optional[dict]
    error: Optional[dict]
    timestamp: str
    request_id: str

def create_response(
    data: Optional[dict] = None,
    error: Optional[dict] = None,
    request_id: str = None
) -> StandardResponse:
    """Create standard response."""
    
    return StandardResponse(
        success=error is None,
        data=data,
        error=error,
        timestamp=datetime.utcnow().isoformat(),
        request_id=request_id or str(uuid.uuid4())
    )

@app.post("/api/example")
async def example_endpoint(req: ExampleRequest) -> StandardResponse:
    """Example using standard response."""
    
    try:
        result = await process(req.data)
        return create_response(data=result.to_dict())
    except ValidationError as e:
        return create_response(
            error={
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        )
```

---

## Error Handling

### Standard Error Codes

```python
class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMIT = "RATE_LIMIT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
```

### Custom Exception Classes

```python
class AgentException(Exception):
    """Base exception for agent operations."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: dict = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

class ValidationError(AgentException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ErrorCode.VALIDATION_ERROR, details)

class NotFoundError(AgentException):
    def __init__(self, resource: str, identifier: str):
        message = f"{resource} '{identifier}' not found"
        super().__init__(message, ErrorCode.NOT_FOUND)

# Exception handlers
@app.exception_handler(AgentException)
async def agent_exception_handler(request, exc: AgentException):
    return JSONResponse(
        status_code=get_status_code(exc.code),
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )
```

---

## Authentication & Authorization

### Dependency Injection Pattern

```python
from fastapi import Depends, Header, HTTPException

async def get_user_context(
    authorization: str = Header(...)
) -> UserContext:
    """Extract user context from authorization header."""
    
    try:
        # Validate token
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
        user_id = payload.get("user_id")
        email = payload.get("email")
        role = payload.get("role")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return UserContext(
            user_id=user_id,
            email=email,
            role=Role(role)
        )
    
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Use in endpoints
@app.get("/api/protected")
async def protected_endpoint(
    user_context: UserContext = Depends(get_user_context)
):
    """Endpoint requiring authentication."""
    return {"user_id": user_context.user_id}
```

### Permission Checking

```python
async def require_permission(permission: Permission):
    """Dependency that requires specific permission."""
    
    async def check_permission(
        user_context: UserContext = Depends(get_user_context)
    ) -> UserContext:
        
        if not user_context.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )
        
        return user_context
    
    return check_permission

# Use in endpoints
@app.delete("/api/items/{item_id}")
async def delete_item(
    item_id: int,
    user_context: UserContext = Depends(require_permission(Permission.DELETE))
):
    """Delete item (requires DELETE permission)."""
    pass
```

---

## Data Validation

### Pydantic Models

```python
from pydantic import BaseModel, Field, validator
from typing import List

class CreateOrderRequest(BaseModel):
    customer_id: int = Field(..., gt=0, description="Customer ID")
    items: List[dict] = Field(..., min_items=1)
    discount: float = Field(0, ge=0, le=1)
    notes: str = Field("", max_length=500)
    
    @validator("items")
    def validate_items(cls, v):
        """Custom validation for items."""
        for item in v:
            if "product_id" not in item or "quantity" not in item:
                raise ValueError("Items must have product_id and quantity")
            if item["quantity"] <= 0:
                raise ValueError("Quantity must be positive")
        return v

# Usage in endpoint
@app.post("/api/orders")
async def create_order(req: CreateOrderRequest):
    """Create order with validated input."""
    # req is guaranteed to be valid
    pass
```

---

## Async Patterns

### Async MCP Tool

```python
import asyncio

@mcp.tool()
async def fetch_external_data(url: str) -> dict:
    """Fetch data from external API asynchronously."""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        return response.json()
```

### Parallel Tool Execution

```python
async def execute_tools_parallel(tools: List[tuple]) -> dict:
    """Execute multiple tools in parallel."""
    
    # Create tasks
    tasks = [
        invoke_mcp_tool(server_port, tool_name, args)
        for server_port, tool_name, args in tools
    ]
    
    # Execute in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        f"{tool_name}": result
        for (_, tool_name, _), result in zip(tools, results)
    }
```

### Timeout Handling

```python
async def invoke_mcp_tool_with_timeout(
    server_port: int,
    tool_name: str,
    args: dict,
    timeout: int = 30
) -> dict:
    """Invoke MCP tool with timeout."""
    
    try:
        return await asyncio.wait_for(
            invoke_mcp_tool(server_port, tool_name, args),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise AgentException(
            "Tool execution timed out",
            ErrorCode.TIMEOUT
        )
```

---

## Testing MCP Tools

### Unit Test Pattern

```python
import pytest

@pytest.mark.asyncio
async def test_get_user_tool():
    """Test get_user MCP tool."""
    
    # Setup
    user = User(id=1, name="Test User", email="test@example.com")
    db.add(user)
    db.commit()
    
    # Call tool
    result = await get_user(user_id=1)
    
    # Assert
    assert result.id == 1
    assert result.name == "Test User"
    assert result.email == "test@example.com"

@pytest.mark.asyncio
async def test_get_user_not_found():
    """Test get_user when user doesn't exist."""
    
    with pytest.raises(ValueError, match="not found"):
        await get_user(user_id=999)
```

### Integration Test Pattern

```python
import httpx

@pytest.mark.asyncio
async def test_supervisor_api():
    """Test supervisor API endpoint."""
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/agent/process",
            json={
                "request": "Test query",
                "user_id": "user123"
            },
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "result" in data
```

---

## Best Practices

### 1. Tool Naming

```python
# ✓ Good: Clear, action-oriented names
@mcp.tool()
async def create_order(...): pass

@mcp.tool()
async def get_user_by_id(...): pass

# ✗ Bad: Vague, generic names
@mcp.tool()
async def do_something(...): pass

@mcp.tool()
async def process(...): pass
```

### 2. Documentation

```python
@mcp.tool()
async def complex_operation(
    param1: str,
    param2: int
) -> ComplexResult:
    """
    Perform a complex operation.
    
    This operation does X, Y, and Z. It requires:
    - Database access
    - External API call
    
    Args:
        param1: Purpose of param1
        param2: Purpose of param2. Must be positive.
    
    Returns:
        ComplexResult containing:
        - field1: Description
        - field2: Description
    
    Raises:
        ValidationError: If inputs invalid
        ExternalServiceError: If API fails
    
    Example:
        result = await complex_operation("test", 42)
    """
    pass
```

### 3. Error Messages

```python
# ✓ Good: Specific, actionable
raise ValueError("Order ID 123 not found. Check order status at /api/orders")

# ✗ Bad: Generic
raise ValueError("Error")
```

### 4. Type Hints

```python
# ✓ Good: Clear types
async def process(data: dict, timeout: int) -> ProcessResult: pass

# ✗ Bad: Missing types
async def process(data, timeout): pass
```

### 5. Logging

```python
import logging

logger = logging.getLogger(__name__)

@mcp.tool()
async def create_order(customer_id: int, items: List[dict]) -> OrderResponse:
    """Create order."""
    
    logger.info(f"Creating order for customer {customer_id}")
    
    try:
        order = await db.create_order(customer_id, items)
        logger.info(f"Order {order.id} created successfully")
        return order
    
    except Exception as e:
        logger.error(f"Failed to create order: {str(e)}", exc_info=True)
        raise
```

---

## Summary

**MCP Tools:**
- Auto-generate schemas from function signatures
- Register with `@mcp.tool()` decorator
- Available to supervisor via JSON-RPC protocol

**FastAPI Endpoints:**
- Standard request/response formats
- Dependency injection for auth/context
- Comprehensive error handling

**Validation:**
- Use Pydantic for type safety
- Custom validators for complex logic

**Standards:**
- Consistent naming, documentation, error codes
- Async patterns for performance
- Proper logging and testing

For architecture deep dives, see ARCHITECTURE.md. For domain-specific details, see DOMAIN_GUIDE.md.
