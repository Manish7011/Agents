# ui/pages.py

import streamlit as st
from .styles import UI_CSS
from .components import sidebar, header, render_trace
from utils.auth import authenticate

def login_page(authenticate_fn, new_thread_id_fn):
    st.markdown(UI_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center;padding:28px 0 8px'>
      <h1 style='color:#fff;font-size:34px;margin-bottom:4px'>🎓 EduManage AI</h1>
      <p style='color:#94a3b8;font-size:15px'>Student Enrollment & Course Management System</p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;color:#60a5fa;font-size:18px;font-weight:700;margin-bottom:20px">Sign In to Your Portal</p>', unsafe_allow_html=True)
        with st.form("login"):
            email    = st.text_input("Email Address", placeholder="student@university.edu")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted= st.form_submit_button("Sign In →")
            if submitted:
                if not email or not password:
                    st.error("Please enter email and password.")
                else:
                    user = authenticate_fn(email, password)
                    if user:
                        st.session_state.user    = user
                        st.session_state.chat    = []
                        st.session_state.history = []
                        st.session_state.trace   = []
                        st.session_state.thread_id = new_thread_id_fn(user)
                        st.session_state.redis_enabled = False
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials. Please try again.")
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("🔑 Demo Credentials", expanded=False):
        st.markdown("""
| Role | Email | Password | Access |
|------|-------|----------|--------|
| 🛡️ Admin | `admin@university.edu` | admin123 | All 8 agents |
| 📋 Registrar | `registrar@university.edu` | reg123 | Registration, Courses, Enrollment, Fee, Timetable |
| 👨‍🏫 Faculty | `faculty@university.edu` | fac123 | Grades, Courses, Timetable |
| 🎓 Advisor | `advisor@university.edu` | adv123 | Advising, Registration (view) |
| 🎒 Student | `student@university.edu` | stu123 | Enrollment, Grades, Timetable, Fee |
        """)

def chat_page(user: dict, call_supervisor_fn, sidebar_args: dict):
    st.markdown(UI_CSS, unsafe_allow_html=True)

    for k in ("chat", "history", "trace"):
        if k not in st.session_state:
            st.session_state[k] = []
    
    # Unpack sidebar args
    list_sessions_fn = sidebar_args['list_sessions_fn']
    new_thread_id_fn = sidebar_args['new_thread_id_fn']
    load_session_fn = sidebar_args['load_session_fn']
    history_to_chat_fn = sidebar_args['history_to_chat_fn']

    if "thread_id" not in st.session_state or not st.session_state.thread_id:
        st.session_state.thread_id = new_thread_id_fn(user)

    sidebar(user, list_sessions_fn, new_thread_id_fn, load_session_fn, history_to_chat_fn)
    header(user)

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"]=="user" else "🎓"):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "trace" in msg:
                render_trace(msg["trace"])

    default = st.session_state.pop("quick_prompt", None)
    user_input = st.chat_input("Ask about enrollment, grades, timetable, fees, advising…") or default

    if user_input:
        st.session_state.chat.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        enriched = (
            f"[User: {user['name']} | Role: {user['role']} | Email: {user['email']}"
            + (f" | Student ID: {user['student_id']}" if user.get("student_id") else "")
            + f"]\n\n{user_input}"
        )
        st.session_state.history.append({"role": "human", "content": enriched})

        with st.chat_message("assistant", avatar="🎓"):
            with st.spinner("Processing…"):
                result = call_supervisor_fn(
                    st.session_state.history,
                    st.session_state.thread_id,
                    f"{user['role']}:{user['email']}",
                    user_input,
                )
            reply = result.get("final_reply", "⚠️ No response received.")
            st.markdown(reply)

        st.session_state.chat.append({"role": "assistant", "content": reply, "trace": result.get("trace", [])})
        st.session_state.history.append({"role": "ai", "content": reply})

        if result.get("messages"):
            st.session_state.history = result["messages"]

        st.rerun()
