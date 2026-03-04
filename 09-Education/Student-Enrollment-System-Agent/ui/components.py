# ui/components.py

import streamlit as st
import json
from .styles import QUICK_ACTIONS
from utils.auth import ROLE_AGENTS, ROLE_LABELS, ROLE_COLORS

def sidebar(user: dict, list_sessions_fn, new_thread_id_fn, load_session_fn, history_to_chat_fn):
    role   = user["role"]
    color  = ROLE_COLORS.get(role, "#1d5fa6")
    agents = ROLE_AGENTS.get(role, [])

    with st.sidebar:
        st.markdown(f"""
        <div style='padding:12px;background:#0a0f1e;border-radius:8px;margin-bottom:12px;border:1px solid #1e3a5e;text-align:center'>
          <p style='margin:0;font-weight:700;font-size:15px;color:#e2e8f0'>{user["name"]}</p>
          <p style='margin:2px 0;font-size:11px;color:#94a3b8'>{user["email"]}</p>
          {'<p style="margin:2px 0;font-size:11px;color:#60a5fa">ID: ' + user["student_id"] + '</p>' if user.get("student_id") else ''}
          <span class='role-badge' style='background:{color}20;color:{color};border:1px solid {color}40'>{ROLE_LABELS.get(role, role)}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<p style='color:#94a3b8;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px'>Session Management</p>", unsafe_allow_html=True)

        user_key = f"{user['role']}:{user['email']}"
        sessions, redis_enabled = list_sessions_fn(user_key)
        st.session_state.redis_enabled = redis_enabled

        current_thread = st.session_state.get("thread_id", new_thread_id_fn(user))
        if current_thread not in sessions:
            sessions = [current_thread] + sessions
        sessions = sessions[:50]

        selected = st.selectbox(
            "Saved Sessions",
            options=sessions if sessions else [current_thread],
            key="session_selectbox",
        )
        s1, s2 = st.columns(2)
        with s1:
            if st.button("Load", use_container_width=True):
                target = (selected or "").strip()
                if target:
                    loaded = load_session_fn(target)
                    st.session_state.thread_id = target
                    st.session_state.history = loaded.get("messages", []) or []
                    st.session_state.chat = history_to_chat_fn(st.session_state.history)
                    st.session_state.trace = []
                    st.rerun()
        with s2:
            if st.button("New", use_container_width=True):
                st.session_state.thread_id = new_thread_id_fn(user)
                st.session_state.chat = []
                st.session_state.history = []
                st.session_state.trace = []
                st.rerun()

        session_input = st.text_input("Session ID", value=current_thread, key="session_id_input")
        if st.button("Use ID", use_container_width=True):
            target = (session_input or "").strip()
            if target:
                loaded = load_session_fn(target)
                st.session_state.thread_id = target
                st.session_state.history = loaded.get("messages", []) or []
                st.session_state.chat = history_to_chat_fn(st.session_state.history)
                st.session_state.trace = []
                st.rerun()

        st.caption(f"Current session: `{current_thread}`")
        if not redis_enabled:
            st.caption("Redis unavailable: using in-memory chat only.")

        st.markdown("---")
        st.markdown("<p style='color:#94a3b8;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px'>Quick Actions</p>", unsafe_allow_html=True)
        for label, prompt in QUICK_ACTIONS.get(role, []):
            if st.button(label, key=f"qa_{label}"):
                st.session_state.quick_prompt = prompt

        st.markdown("---")

        st.markdown(f"<p style='color:#94a3b8;font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px'>Your Agents ({len(agents)})</p>", unsafe_allow_html=True)
        agent_icons = {
            "Student Registration": "🎒", "Course Management": "📚",
            "Enrollment": "📝", "Grade & Transcript": "📊",
            "Academic Advising": "🎓", "Fee & Scholarship": "💰",
            "Timetable & Scheduling": "📅", "Direct Answering": "❓",
        }
        for a in agents:
            st.markdown(f'<div class="agent-pill">{agent_icons.get(a,"🤖")} {a}</div>', unsafe_allow_html=True)
        
        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.chat = []
                st.session_state.history = []
                st.session_state.trace = []
                st.rerun()
        with c2:
            if st.button("🚪 Logout", use_container_width=True):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()

def header(user: dict):
    role  = user["role"]
    color = ROLE_COLORS.get(role, "#1d5fa6")
    dept  = user.get("department", "—")
    sid   = f" | Student ID: {user['student_id']}" if user.get("student_id") else ""
    thread_id = st.session_state.get("thread_id", "N/A")
    st.markdown(f"""
    <div class="header-card">
      <h1>🎓 EduManage AI — Student Enrollment & Course Management</h1>
      <p>Logged in as <strong style="color:#fff">{user["name"]}</strong>
         &nbsp;|&nbsp; Role: <strong style="color:{color}">{ROLE_LABELS.get(role, role)}</strong>
         &nbsp;|&nbsp; Dept: {dept}{sid}
         &nbsp;|&nbsp; Access: {len(ROLE_AGENTS.get(role,[]))} agents
         &nbsp;|&nbsp; Session: <strong style="color:#fff">{thread_id}</strong></p>
    </div>
    """, unsafe_allow_html=True)

def render_trace(trace: list):
    if not trace: return
    
    n_routed = sum(1 for s in trace if s.get("type") == "tool_call")
    n_tools = n_routed
    n_results = sum(1 for s in trace if s.get("type") == "tool_result")
    
    with st.expander(f"🔍 Agent Routing Trace ({len(trace)} steps)", expanded=False):
        st.markdown(f"""
            <div class="trace-summary-bar">
                <div class="trace-pill">{n_routed} routed</div>
                <div class="trace-pill">{n_tools} tool calls</div>
                <div class="trace-pill">{n_results} tool results</div>
            </div>
        """, unsafe_allow_html=True)
        
        for i, step in enumerate(trace, 1):
            label = step.get("label", "")
            stype = step.get("type", "")
            
            ui_class = "route"
            ui_type  = "ROUTE"
            icon     = "📦"
            subtext  = "Action processed"
            
            if stype == "tool_call":
                ui_class = "tool"
                ui_type  = "TOOL CALLED"
                icon     = "🛠️"
                subtext  = "Routing to specialized agent"
            elif stype == "tool_result":
                ui_class = "result"
                ui_type  = "MCP RESULT"
                icon     = "✅"
                subtext  = "Response received from agent"
            elif stype == "error":
                ui_class = "error"
                ui_type  = "ERROR"
                icon     = "⚠️"
                subtext  = "Agent encounter error"
            
            st.markdown(f"""
                <div class="trace-card-v2 {ui_class}">
                    <div class="step-header-v2">
                        <span class="step-badge-v2">Step {i}</span>
                        <span class="step-type-v2">{ui_type}</span>
                    </div>
                    <div class="step-title-v2">{label}</div>
                    <div class="step-detail-v2">
                        <span>{icon}</span> {subtext}
                    </div>
                    <details class="step-raw-link-v2">
                        <summary>▶ View raw details</summary>
                        <pre>{json.dumps(step, indent=2)}</pre>
                    </details>
                </div>
            """, unsafe_allow_html=True)
