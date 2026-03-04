Yes — I now fully understand your system architecture:

You built a **multi-agent cybersecurity platform** using:

* LangGraph supervisor
* Tool-first agents
* MCP (Model Context Protocol) microservices
* OSV + NVD integrations
* GitHub dependency scanning
* Deterministic routing
* Structured tool invocation
* Production-grade launcher layer

Below is your **maximum-length professional README** — suitable for:

* GitHub public repo
* Thesis submission
* Portfolio showcase
* Startup demo
* Technical interview discussion

---

# 🛡️ Cybersecurity Agent Platform

### Tool-First Multi-Agent Vulnerability & Dependency Analysis System

---

## 📌 Overview

Cybersecurity-Agent is a **modular, production-grade, tool-first AI security platform** designed to analyze:

* 📦 Software dependencies
* 🐞 Known vulnerabilities (CVE)
* 📚 Security advisories (GHSA)
* 🔍 Public GitHub repositories

The system uses a **LangGraph Supervisor + MCP Microservices architecture**, ensuring:

* Deterministic tool usage
* Safe AI orchestration
* Scalable agent routing
* Production-ready separation of concerns

---

# 🧠 Architecture

## High-Level Design

```
User
  ↓
Supervisor (LangGraph Router)
  ↓
Agent (Dependency | Vulnerability | Advisory)
  ↓
MCP Tool Server
  ↓
External APIs (OSV, NVD, GitHub, PyPI, npm, Maven)
```

---

## 🏗 System Components

### 1️⃣ Supervisor Layer

* Built with **LangGraph**
* Uses structured router output
* Determines correct agent
* Maintains conversation history
* Prevents incorrect tool usage

### 2️⃣ Agent Layer (Tool-First)

Each agent follows:

```
reasoning → tool → reasoning → summarize
```

Agents:

| Agent               | Purpose                       |
| ------------------- | ----------------------------- |
| Dependency Agent    | Scan repos & dependency files |
| Vulnerability Agent | CVE / product analysis        |
| Advisory Agent      | GHSA / CVE advisory details   |

---

### 3️⃣ MCP Layer (Microservices)

Each security capability runs as an independent FastAPI service:

| MCP Service       | Port | Purpose                  |
| ----------------- | ---- | ------------------------ |
| vulnerability-mcp | 8001 | CVE / OSV / validation   |
| dependency-mcp    | 8002 | Repo & manifest scanning |

Advantages:

* Fault isolation
* Independent scaling
* Clean API boundary
* Tool discovery via SSE

---

# 🔎 Features

## 📦 Dependency Analysis

Supports:

* requirements.txt
* package.json
* pom.xml
* build.gradle
* pubspec.yaml

Capabilities:

* OSV vulnerability lookup
* Version pin detection
* Latest version comparison
* Multi-file GitHub repo scan
* Concurrency control
* Severity extraction

---

## 🐞 Vulnerability Analysis

Supports:

* CVE search
* Product + version lookup
* Maven group lookup
* Cross verification
* CVSS scoring
* Package validation (npm, PyPI, Maven)

Sources:

* NVD
* OSV
* GitHub Advisory

---

## 📚 Advisory Analysis

Supports:

* GHSA lookup
* CVE advisory expansion
* Alias mapping
* Severity summary
* Affected ecosystem
* Recommended mitigation

---

# 🔐 Security & Safety Design

## Tool-First Pattern

The LLM **never fabricates vulnerability data**.

It must:

1. Call a tool
2. Receive structured data
3. Summarize strictly from tool output

---

## Loop Guard

Each agent has:

```
MAX_TOOL_CALLS = 3
```

Prevents:

* Infinite loops
* Tool abuse
* Prompt injection amplification

---

## Structured Output

All MCP tools return:

```
{
  "status": "success" | "error",
  "data": ...,
  "error": ...
}
```

No raw text parsing.

---

## Supervisor Routing Rules

Examples:

| User Input        | Routed To           |
| ----------------- | ------------------- |
| GitHub URL        | Dependency Agent    |
| package + version | Vulnerability Agent |
| CVE-XXXX          | Advisory Agent      |
| GHSA-XXXX         | Advisory Agent      |

History-aware routing included.

---

# 🚀 Installation

### 1️⃣ Clone

```bash
git clone <repo>
cd Cybersecurity-Agent
```

### 2️⃣ Create Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3️⃣ Configure Environment

`.env`

```
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o
LOG_LEVEL=INFO
```

---

# ▶ Running the System

## Start MCP Servers

```bash
python mcp_launcher.py
```

Starts:

* vulnerability-mcp (8001)
* dependency-mcp (8002)

---

## Start Supervisor

```bash
python supervisor_launcher.py
```

Runs on:

```
http://localhost:9000
```

---

# 🧪 Example Queries

## Dependency Scan

```
scan https://github.com/pallets/flask
```

---

## Scan requirements.txt

```
scan this requirements.txt

flask==2.0.1
requests==2.25.1
```

---

## CVE Lookup

```
check vulnerabilities for openssl 1.1.1
```

---

## Advisory Lookup

```
explain GHSA-67rr-84xm-4c7r
```

---

# 📊 Internal Design Patterns

## 1️⃣ Deterministic Routing

Uses Pydantic structured output:

```python
class RouterDecision(BaseModel):
    agent: Optional[str]
    reason: str
```

No hallucinated routing.

---

## 2️⃣ Tool Discovery

Uses:

```
MultiServerMCPClient
```

With:

* SSE streaming
* Tool auto-registration
* Scoped loading

---

## 3️⃣ Concurrency Control

Dependency scanning uses:

```
asyncio.Semaphore(8)
```

Prevents:

* Registry overload
* Rate limiting
* Thread explosion

---

# 📁 Project Structure

```
agent/
  supervisor/
  dependency_graph.py
  vulnerability_graph.py
  advisory_graph.py

mcp_tools/
  dependency/
  vulnerability/

shared/
  config.py
  models.py

mcp_launcher.py
supervisor_launcher.py
```

---

# 🧪 Testing Strategy

Manual validation suite includes:

* GitHub repo scanning
* CVE lookup
* Version validation
* Invalid input testing
* Prompt injection attempts
* Stress tests

---

# 🧠 Design Principles

* Tool-first AI
* Deterministic architecture
* Microservice separation
* Clean failure handling
* Structured data contracts
* Production-safe launchers

---

# 🔮 Future Enhancements

* Risk scoring engine
* Exploit prediction
* SBOM export
* Docker deployment
* Kubernetes scaling
* API authentication
* SaaS dashboard
* CI/CD integration
* Enterprise policy engine

---

# 🏆 Why This Architecture Is Strong

Unlike traditional LLM wrappers:

| Traditional AI | This System          |
| -------------- | -------------------- |
| Hallucinates   | Tool-backed          |
| Monolithic     | Microservices        |
| Prompt-only    | Structured routing   |
| No guardrails  | Loop & scope control |
| Hard to scale  | Service-based        |

---

# 📈 Use Cases

* Security research
* DevSecOps automation
* CI pipeline scanning
* Startup security product
* Academic research
* Thesis project
* Portfolio showcase

---

# 👨‍💻 Author

Built using:

* Python 3.13
* LangGraph (2026 pattern)
* FastAPI
* Uvicorn
* OSV API
* NVD API
* OpenAI

---

# 📜 License

MIT License (or specify your own)

---

# 🔥 Final Statement

This project demonstrates:

* Advanced AI agent orchestration
* Secure tool-first design
* Production-ready microservice architecture
* Real-world cybersecurity integration
* Modern LangGraph patterns (2026)

---
