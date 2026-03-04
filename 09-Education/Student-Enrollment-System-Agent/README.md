# EduManage AI - System Architecture & Documentation

Welcome to the comprehensive documentation for the **EduManage AI - Student Enrollment & Course Management System**. This document provides a step-by-step explanation of the codebase, how the Model Context Protocol (MCP) servers function, the inner workings of the system, and instructions on how to run both the backend servers and the frontend Streamlit UI.

## EduManage AI - Demo

![alt text](<./assets/EduManageAI.gif>)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [What is MCP (Model Context Protocol)?](#2-what-is-mcp)
3. [Architecture deep-dive](#3-architecture-deep-dive)
   - [Specialist MCP Servers](#specialist-mcp-servers)
   - [The LangGraph Supervisor](#the-langgraph-supervisor)
   - [The Streamlit Frontend UI](#the-streamlit-frontend-ui)
4. [Step-by-Step Flow: How a Request is Processed](#4-step-by-step-flow)
5. [How to Run the Application](#5-how-to-run-the-application)

---

## 1. System Overview

EduManage AI is a multi-agent, role-based application designed to simulate a university's enrollment and management system.

It features:

- **Role-Based Access Control (RBAC)**: Users log in with specific roles (Admin, Registrar, Faculty, Advisor, Student), restricting access to certain agents and data.
- **Micro-Agent Architecture**: Instead of one monolithic AI, the system utilizes **7 specialized agents**, each running as an independent MCP Server with its own isolated set of tools (e.g., database queries, email simulation).
- **Intelligent Supervisor**: A central "Supervisor" agent built with LangGraph that receives user queries, determines the intent, and routes the query to the correct specialist agent.
- **Rich Streamlit UI**: A modern interface that features dark mode, session management (backed by Redis), and detailed routing trace visualizations.

---

## 2. What is MCP (Model Context Protocol)?

**MCP (Model Context Protocol)** is an emerging open standard that standardizes how AI models connect to data sources, external APIs, and tools.

In a traditional setup, you have to build custom integrations for every tool an LLM uses. MCP solves this by acting as a universal, standard protocol.

### How it works in EduManage:

1. **MCP Servers**: We define specialized Python scripts (like `registration_server.py`) using the `FastMCP` library. These servers expose local Python functions as "Tools" over a standard HTTP interface.
2. **MCP Client**: The central LangGraph Supervisor acts as the MCP Client. Instead of holding the tool code locally, it asks the MCP Servers at startup: _"What tools do you have?"_.
3. **Execution**: When the LLM decides to use a tool, the Supervisor sends an execution request over HTTP to the specific MCP server, which runs the code against the database and returns the JSON result.

**Why is this powerful?**
It creates absolute separation of concerns. If the Admissions department needs to update how "Registration" works, they only modify the `registration_server.py`. The Supervisor doesn't need to be rewritten or recompiled.

---

### 3. Architecture Deep-Dive

The system follows a modular, three-tier architecture orchestrated by the **Model Context Protocol (MCP)**. Below is the complete workflow of how a user request traverses the system:

![alt text](<./assets/Chart1.png>)

---

### 4. Communication Sequence

The following sequence diagram illustrates the step-by-step lifecycle of a single user request:

![alt text](<./assets/Chart2.png>)

---


### A. Specialist MCP Servers (`mcp_servers/`)

Located in the `mcp_servers/` directory, these are 7 independent FastAPI/MCP servers running on ports 8001 through 8007.

1. **Registration (Port 8001)**: Handles new student creation, profile updates, and sending welcome emails.
2. **Course (Port 8002)**: Handles creating/updating courses, capacities, and waitlists.
3. **Enrollment (Port 8003)**: Manages assigning existing students to courses, dropping courses, checking prerequisites.
4. **Grade (Port 8004)**: Submits grades, calculates CGPAs, and generates transcripts.
5. **Advising (Port 8005)**: Performs degree audits, detects at-risk students, and schedules advising appointments.
6. **Fee (Port 8006)**: Handles tuition posting, payments, and scholarships.
7. **Timetable (Port 8007)**: Manages class schedules, room assignments, and conflict detection.

All of these servers connect directly to the underlying PostgreSQL database via `database/db.py`.

### B. The LangGraph Supervisor (`supervisor/`)

This is the "Brain" of the application, running on Port 9001.

- **`graph.py`**: This file defines the LangGraph architecture.
  - It uses a router node (`supervisor_agent`) powered by an LLM with structured output (`RouteDecision`) to decide which specialist should handle the user's message.
  - It creates agent nodes (using LangChain's `create_agent` or `create_react_agent`) for each specialist. Each agent only has access to the tools dynamically loaded from its respective MCP server.
  - It includes a `direct_answering_agent` as a fallback for general questions that don't require database tools.
- **`supervisor_server.py`**: This wraps the LangGraph into its own FastMCP server so the Streamlit UI can talk to it cleanly over HTTP format. It also manages conversational memory (backing it up to Redis so sessions persist across UI reloads).

### C. The Streamlit Frontend UI (`app.py`)

This is the user interface. It is completely decoupled from the AI logic.

- It handles user logins and role definitions.
- It displays the chat interface.
- It intercepts user messages and POSTs them to the Supervisor MCP server at `http://127.0.0.1:9001/mcp`.
- It parses the response to display the AI's reply and renders a detailed **"Agent Routing Trace"** UI card so the user can see exactly how the Supervisor routed the request.

---

## 4. Step-by-Step Flow: How a Request is Processed

Let's trace what happens when a user types: _"Register a new student named John Doe"_

1. **User Input (`app.py`)**:
   The user types the message in the Streamlit UI. Streamlit wraps it in a JSON payload alongside conversation history and the user's role/session data.
2. **API Call**:
   Streamlit makes a POST request to `http://127.0.0.1:9001/mcp` looking for the `chat` tool.
3. **Supervisor Graph (`supervisor_server.py` -> `graph.py`)**:
   - The Supervisor node receives the message.
   - It reads its system prompt and looks at the available routes.
   - The LLM decides: _"This is a new student registration, I must route to `reg_agent`."_
4. **Specialist Agent Execution**:
   - The flow shifts to the `reg_agent` node.
   - The `reg_agent` knows it has tools available from the Port 8001 MCP Server.
   - The LLM decides it needs to use the `register_student` tool.
5. **MCP Tool Invocation**:
   - The Langchain framework makes an HTTP request to `http://127.0.0.1:8001/mcp`, commanding it to execute `register_student(name="John Doe", ...)`.
6. **Database & Logic (`mcp_servers/registration_server.py`)**:
   - The registration server receives the command, runs the SQL query via `psycopg2`, inserts John Doe, and returns a JSON success dictionary.
7. **Final Reply**:
   - The `reg_agent` receives the JSON dictionary, formulates a natural language response (e.g., _"John Doe has been successfully registered!"_), and the graph concludes.
8. **UI Render (`app.py`)**:
   - The response goes back to Streamlit, which prints the message and generates the Trace UI cards visually showing that `reg_agent` was called and `register_student` was executed.

---

## 5. How to Run the Application

To run the full stack locally, you need three components actively running: Redis, the backend servers, and the frontend UI.

### Prerequisites:

- Python 3.10+
- PostgreSQL database (configured in your `.env` file)
- Redis server running locally (or configured in `.env`)
- OpenAI API Key (configured in your `.env` file)

### Dependencies (`requirements.txt`):

- **langgraph** `>= 0.2.0`
- **langchain** `>= 0.2.0`
- **langchain-openai** `>= 0.1.0`
- **langchain-core** `>= 0.2.0`
- **langchain-mcp-adapters** `>= 0.1.0`
- **mcp** `>= 1.0.0`
- **python-dotenv** `>= 1.0.0`
- **psycopg2-binary** `>= 2.9.0`
- **streamlit** `>= 1.35.0`
- **nest-asyncio** `>= 1.6.0`
- **uvicorn** `>= 0.30.0`
- **httpx** `>= 0.27.0`
- **psutil** `>= 5.9.0`
- **redis** `>= 5.0.0`

### Step 1: Start Redis (If not already running)

If you are on Windows, you can use WSL to run redis-server, or use a Docker container:

```bash
# Example using Docker
docker run -p 6379:6379 -d redis
```

### Step 2: Start the Backend Servers

We have provided a unified script that automatically starts all 7 specialist MCP servers plus the Supervisor server using multiprocessing.

Open a terminal in the project root and run:

```bash
python start_servers.py
```

_Wait until you see messages indicating that ports 8001 through 8007 and port 9001 are actively listening._

### Step 3: Start the Streamlit UI

Open a **new** terminal window (leave `start_servers.py` running in the first one), ensure your virtual environment is activated, and run:

```bash
streamlit run app.py
```

Streamlit will automatically open a browser window to `http://localhost:8501`. You can then log in using one of the demo credentials provided on the login page.
