# ui/styles.py

UI_CSS = """
<style>
.stApp,[data-testid="stAppViewContainer"]{background:#0a0f1e!important}
.stApp *{color:#e2e8f0!important}
[data-testid="stSidebar"]{background:#111827!important;border-right:1px solid #1e3a5e}
[data-testid="stSidebar"] .stButton>button{
  background:#0f2444!important;color:#e2e8f0!important;border:1px solid #1e3a5e!important;
  border-radius:8px!important;width:100%!important;margin-bottom:5px!important;
  padding:9px 14px!important;font-size:12px!important;text-align:left!important}
[data-testid="stSidebar"] .stButton>button:hover{background:#1d5fa6!important;border-color:#1d5fa6!important}
[data-testid="stChatMessage"]{
  background:#111827!important;border:1px solid #1e3a5e!important;
  border-radius:12px!important;padding:14px 18px!important;margin-bottom:10px!important}
[data-testid="stChatInput"] textarea{
  background:#111827!important;color:#e2e8f0!important;
  border:1px solid #1e3a5e!important;border-radius:10px!important}
[data-testid="stChatInput"]{background:#0a0f1e!important;border-top:1px solid #1e3a5e!important}
.header-card{
  background:linear-gradient(135deg,#0f2444,#1d5fa6);
  padding:18px 24px;border-radius:12px;margin-bottom:16px;border:1px solid #1e3a5e}
.header-card h1{margin:0;font-size:20px;color:#fff!important}
.header-card p{margin:4px 0 0;font-size:12px;color:#93c5fd!important}
.role-badge{display:inline-block;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;margin-bottom:10px}
.agent-pill{
  padding:6px 10px;background:#0a0f1e;border-radius:6px;margin-bottom:4px;
  border:1px solid #1e3a5e;font-size:12px}
.trace-summary-bar {
  display: flex; gap: 8px; background: rgba(15, 23, 42, 0.4);
  padding: 10px 14px; border-radius: 12px; margin-bottom: 12px;
  border: 1px solid rgba(30, 58, 94, 0.5);
}
.trace-pill {
  background: rgba(30, 58, 94, 0.3); border: 1px solid rgba(29, 95, 166, 0.4);
  color: #e2e8f0; padding: 3px 12px; border-radius: 20px;
  font-size: 11px; font-weight: 600;
}
.trace-card-v2 {
  background: rgba(17, 24, 39, 0.7); border-radius: 10px;
  padding: 16px; margin-bottom: 12px; border: 1px solid rgba(30, 58, 94, 0.5);
  border-left: 4px solid #3b82f6; transition: transform 0.2s;
}
.trace-card-v2:hover { transform: translateX(2px); background: rgba(17, 24, 39, 0.9); }
.trace-card-v2.route { border-left-color: #3b82f6; }
.trace-card-v2.tool { border-left-color: #60a5fa; }
.trace-card-v2.result { border-left-color: #10b981; }
.trace-card-v2.error { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.05); }

.step-header-v2 { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.step-badge-v2 {
  background: #0f172a; color: #fff; padding: 2px 8px; border-radius: 6px;
  font-size: 10px; font-weight: 700; border: 1px solid rgba(30, 58, 94, 0.8);
}
.step-type-v2 {
  font-size: 10px; font-weight: 800; color: #60a5fa;
  letter-spacing: 1px; text-transform: uppercase;
}
.step-title-v2 { font-size: 14px; font-weight: 700; color: #f8fafc; margin-bottom: 6px; }
.step-detail-v2 { font-size: 12px; color: #94a3b8; display: flex; align-items: center; gap: 6px; }
.step-raw-link-v2 {
  font-size: 11px; color: #60a5fa; margin-top: 14px;
  cursor: pointer; outline: none;
}
.step-raw-link-v2 summary {
  list-style: none; display: flex; align-items: center; gap: 4px; opacity: 0.8;
}
.step-raw-link-v2 summary::-webkit-details-marker { display: none; }
.step-raw-link-v2 pre {
  background: rgba(15, 23, 42, 0.9); padding: 10px; border-radius: 6px;
  border: 1px solid rgba(30, 58, 94, 0.5); margin-top: 8px;
  font-family: 'JetBrains Mono', monospace; font-size: 10px;
  color: #94a3b8; overflow-x: auto; white-space: pre-wrap;
}
.login-box{
  background:#111827;border:1px solid #1e3a5e;border-radius:14px;
  padding:36px;max-width:440px;margin:50px auto 0}
.stTextInput>div>div>input{
  background:#0a0f1e!important;color:#e2e8f0!important;
  border:1px solid #1e3a5e!important;border-radius:8px!important}
.stTextInput label{color:#94a3b8!important;font-size:13px!important}
div[data-testid="stForm"] .stButton>button{
  background:linear-gradient(135deg,#1d5fa6,#0f2444)!important;
  color:#fff!important;border:none!important;border-radius:8px!important;
  width:100%!important;padding:12px!important;font-size:15px!important;font-weight:700!important}
div[data-testid="stForm"] .stButton>button:hover{background:#1d5fa6!important}
.stExpander{background:#111827!important;border:1px solid #1e3a5e!important;border-radius:8px!important}
</style>
"""

QUICK_ACTIONS: dict[str, list[tuple]] = {
    "admin": [
        ("🎒 Register Student",       "Register a new student: Aditya Kumar, aditya@university.edu, B.Tech Computer Science"),
        ("📊 All Student Statistics", "Show me student enrollment statistics by department"),
        ("📚 List All Courses",       "List all courses available this semester with seat availability"),
        ("⚠️  At-Risk Students",      "Show all students at academic risk and send them warnings"),
        ("💰 Financial Summary",      "Show the overall financial summary of fees collected and outstanding"),
        ("🔍 Detect Conflicts",       "Check all timetable slots for room or faculty conflicts"),
    ],
    "registrar": [
        ("🎒 Register New Student",  "Register a new student: Kavya Reddy, kavya@university.edu, MBA Business Analytics, Management"),
        ("📚 Create Course",         "Create a new course: CS601 Deep Learning, Computer Science, 3 credits, capacity 25, Spring"),
        ("📋 Enrollment Stats",      "Show course enrollment statistics — most popular courses"),
        ("💰 Fee Reminders",         "Send fee reminders to student STU-2026-001"),
        ("📅 Show Timetable",        "Show the complete timetable for Spring semester"),
        ("👥 CS Department Roster",  "Show all active students in the Computer Science department"),
    ],
    "faculty": [
        ("📝 Submit Grade",          "Submit grade A for student STU-2026-002 in course CS101"),
        ("📊 Grade Distribution",    "Show grade distribution for course CS101"),
        ("📅 My Timetable",          "Show my teaching timetable for faculty@university.edu this semester"),
        ("📚 My Course Details",     "Show details for course CS101 including enrolled students"),
        ("🎓 Course Roster",         "Show all students enrolled in CS201"),
        ("✏️  Update Grade",          "Update grade for STU-2026-004 in CS101 to B+"),
    ],
    "advisor": [
        ("🔍 Degree Audit",          "Run a degree audit for student STU-2026-001"),
        ("⚠️  At-Risk Students",     "Show all students at academic risk with GPA below 2.0"),
        ("📅 Book Appointment",      "Book an advising appointment for STU-2026-005 tomorrow at 10am"),
        ("🎓 Graduation Check",      "Check graduation eligibility for student STU-2026-007"),
        ("📋 Study Plan",            "Generate a study plan for student STU-2026-001"),
        ("📢 Academic Warnings",     "Send academic warnings to all at-risk students"),
    ],
    "student": [
        ("📚 Enroll in Course",      "I want to enroll in CS301 Advanced Algorithms"),
        ("📅 My Timetable",          "Show my personal timetable for this semester"),
        ("📊 My Grades",             "Show all my grades for this semester"),
        ("💰 My Fee Balance",        "Show my financial statement and outstanding fees"),
        ("🎓 Scholarship Check",     "Am I eligible for any scholarships?"),
        ("❓ How to Drop a Course",  "How do I drop a course and what is the deadline?"),
    ],
}
