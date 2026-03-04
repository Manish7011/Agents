"""
app.py
══════
EduManage AI — Student Enrollment & Course Management System
Streamlit UI with Role-Based Access Control (RBAC)
"""

import sys
import os
import json
import uuid
import httpx
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import init_db
from utils.auth import authenticate, ROLE_AGENTS, ROLE_LABELS, ROLE_COLORS
from ui import login_page, chat_page

SUPERVISOR_URL = "http://127.0.0.1:9001/mcp"
HTTP_TIMEOUT   = 120


def _new_thread_id(user: dict) -> str:
    role = user.get("role", "user")
    return f"{role}-{uuid.uuid4().hex[:10]}"


def _display_user_content(content: str) -> str:
    # Hide enriched audit prefix in UI when loading from stored history.
    if content.startswith("[User:") and "]\n\n" in content:
        return content.split("]\n\n", 1)[1]
    return content

# ── Page config ───────────────────────────────────────────────────────────────
def _page_config():
    st.set_page_config(
        page_title="EduManage AI",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )

# ── Supervisor calls ───────────────────────────────────────────────────────────
def _mcp_call(name: str, arguments: dict) -> dict:
    payload = {
        "jsonrpc": "2.0", "id": 1,
        "method": "tools/call", "params": {"name": name, "arguments": arguments},
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        resp = httpx.post(SUPERVISOR_URL, json=payload, headers=headers, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        raw  = data.get("result", {})
        if isinstance(raw, str):
            raw = json.loads(raw)
        content = raw.get("content", [])
        if isinstance(content, list) and content:
            inner = content[0].get("text", "{}")
            return json.loads(inner) if isinstance(inner, str) else inner
        if isinstance(raw, dict):
            return raw
        return {"error": f"Unexpected response: {raw}"}
    except Exception as exc:
        return {"error": str(exc)}


def _call_supervisor(history: list, thread_id: str, user_key: str, latest_user_input: str) -> dict:
    out = _mcp_call(
        "chat",
        {
            "messages_json": json.dumps(history),
            "thread_id": thread_id,
            "user_key": user_key,
            "latest_user_input": latest_user_input,
        },
    )
    if "error" in out and "final_reply" not in out:
        err = out.get("error", "unknown")
        return {
            "final_reply": (
                f"⚠️ **Connection Error** — Could not reach the EduManage supervisor.\n\n"
                f"Make sure all servers are running:\n```\npython start_servers.py\n```\n\nError: `{err}`"
            ),
            "trace": [{"type": "error", "label": f"Error: {err[:120]}"}],
            "messages": [],
        }
    return out


def _list_sessions(user_key: str) -> tuple[list[str], bool]:
    out = _mcp_call("list_sessions", {"user_key": user_key, "limit": 50})
    return out.get("sessions", []) or [], bool(out.get("redis_enabled", False))


def _load_session(thread_id: str) -> dict:
    return _mcp_call("get_session", {"thread_id": thread_id})


def _history_to_chat(history: list[dict]) -> list[dict]:
    chat: list[dict] = []
    for msg in history:
        role = msg.get("role")
        if role == "human":
            chat.append({"role": "user", "content": _display_user_content(str(msg.get("content", "")))})
        elif role == "ai":
            chat.append({"role": "assistant", "content": str(msg.get("content", "")), "trace": []})
    return chat

# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    _page_config()
    init_db()
    
    if "user" not in st.session_state or not st.session_state.user:
        login_page(authenticate, _new_thread_id)
    else:
        sidebar_args = {
            'list_sessions_fn': _list_sessions,
            'new_thread_id_fn': _new_thread_id,
            'load_session_fn': _load_session,
            'history_to_chat_fn': _history_to_chat
        }
        chat_page(st.session_state.user, _call_supervisor, sidebar_args)


if __name__ == "__main__":
    main()
