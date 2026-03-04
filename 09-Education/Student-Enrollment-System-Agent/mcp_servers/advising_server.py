"""mcp_servers/advising_server.py — Academic Advising Agent (port 8005 · 8 tools)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2.extras
from mcp.server.fastmcp import FastMCP
from database.db import get_connection, init_db
from utils.email_service import send_academic_warning, send_advising_appointment

mcp = FastMCP("AdvisingServer", host="127.0.0.1", port=8005, stateless_http=True, json_response=True)


def _cur(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


@mcp.tool()
def run_degree_audit(student_id: str) -> dict:
    """Check credits completed vs required for student's program. Required: 160 credits for B.Tech, 80 for M.Tech/MBA."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, program, total_credits, gpa, semester FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    if not stu:
        conn.close()
        return {"found": False, "message": f"Student {student_id} not found."}
    program_requirements = {
        "B.Tech": 160, "M.Tech": 80, "MBA": 80, "default": 120
    }
    prog = stu["program"]
    required = next((v for k, v in program_requirements.items() if k in prog), 120)
    completed = stu["total_credits"]
    # Enrolled credits
    cur.execute("""
        SELECT COALESCE(SUM(c.credits),0) AS in_progress
        FROM enrollments e JOIN courses c ON c.id=e.course_id
        WHERE e.student_id=%s AND e.status='enrolled'
    """, (student_id,))
    in_progress = int(cur.fetchone()["in_progress"]); conn.close()
    remaining = max(0, required - completed - in_progress)
    pct = round((completed + in_progress) / required * 100, 1) if required else 0
    return {
        "student_id": student_id, "name": stu["name"], "program": prog,
        "credits_required": required, "credits_completed": completed,
        "credits_in_progress": in_progress, "credits_remaining": remaining,
        "completion_pct": pct, "current_gpa": float(stu["gpa"]),
        "on_track": remaining <= (8 - stu["semester"]) * 20,
        "message": f"{stu['name']} has completed {pct}% of degree requirements ({completed}/{required} credits).",
    }


@mcp.tool()
def get_at_risk_students(gpa_threshold: float = 2.0, department: str = "") -> list:
    """List students at academic risk: low GPA, probation, or suspended status."""
    conn = get_connection(); cur = _cur(conn)
    q = """
        SELECT student_id, name, email, program, department, semester, gpa, status
        FROM students WHERE (gpa < %s OR status IN ('suspended','deferred')) AND status!='graduated'
    """
    params = [gpa_threshold]
    if department:
        q += " AND department ILIKE %s"; params.append(f"%{department}%")
    q += " ORDER BY gpa ASC"
    cur.execute(q, params); rows = cur.fetchall(); conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["risk_level"] = ("🔴 Critical" if d["gpa"] < 1.5 else "🟠 High" if d["gpa"] < 2.0 else "🟡 Moderate")
        result.append(d)
    return result if result else [{"message": f"No at-risk students found (threshold GPA: {gpa_threshold})."}]


@mcp.tool()
def book_advising_appointment(
    student_id: str, advisor_email: str, advisor_name: str,
    scheduled_at: str, notes: str = "", meeting_type: str = "in_person"
) -> dict:
    """Book a student-advisor meeting; send confirmation emails to both parties."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, email FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    if not stu:
        conn.close()
        return {"success": False, "message": f"Student {student_id} not found."}
    cur.execute("""
        INSERT INTO advising_appointments
          (student_id,advisor_email,advisor_name,scheduled_at,notes,meeting_type)
        VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
    """, (student_id, advisor_email, advisor_name, scheduled_at, notes, meeting_type))
    appt_id = cur.fetchone()["id"]; conn.commit(); conn.close()
    email_result = send_advising_appointment(
        stu["email"], advisor_email, stu["name"], advisor_name, scheduled_at, notes
    )
    return {
        "success": True, "appointment_id": appt_id, "student_id": student_id,
        "student_name": stu["name"], "advisor": advisor_name,
        "scheduled_at": scheduled_at, "meeting_type": meeting_type,
        "email_sent": email_result["success"],
        "message": f"Appointment #{appt_id} booked: {stu['name']} with {advisor_name} at {scheduled_at}.",
    }


@mcp.tool()
def get_advising_appointments(advisor_email: str = "", student_id: str = "", status: str = "scheduled") -> list:
    """List advising appointments for an advisor or student."""
    conn = get_connection(); cur = _cur(conn)
    q = "SELECT * FROM advising_appointments WHERE status=%s"
    params = [status]
    if advisor_email:
        q += " AND advisor_email=%s"; params.append(advisor_email)
    if student_id:
        q += " AND student_id=%s"; params.append(student_id)
    q += " ORDER BY scheduled_at ASC"
    cur.execute(q, params); rows = cur.fetchall(); conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["scheduled_at"] = str(d["scheduled_at"])[:16]
        d["created_at"]   = str(d["created_at"])[:16]
        result.append(d)
    return result if result else [{"message": f"No {status} appointments found."}]


@mcp.tool()
def get_credit_summary(student_id: str) -> dict:
    """Credits earned, in-progress, and still needed for graduation."""
    return run_degree_audit(student_id)


@mcp.tool()
def send_academic_warning_tool(student_id: str, advisor_email: str = "advisor@university.edu") -> dict:
    """Email an academic warning to a student with recommended actions."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, email, gpa, status FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone(); conn.close()
    if not stu:
        return {"success": False, "message": f"Student {student_id} not found."}
    gpa = float(stu["gpa"])
    reason = ("GPA below 2.0 — Academic Probation" if gpa < 2.0 else
              "GPA below 2.5 — At-risk student" if gpa < 2.5 else
              f"Enrollment status: {stu['status']}")
    result = send_academic_warning(stu["email"], stu["name"], gpa, reason, advisor_email)
    return {"success": result["success"], "student_id": student_id, "student_name": stu["name"],
            "gpa": gpa, "reason": reason, "email": stu["email"], "message": result["message"]}


@mcp.tool()
def get_graduation_eligibility(student_id: str) -> dict:
    """Check whether a student meets all requirements for graduation."""
    audit = run_degree_audit(student_id)
    if not audit.get("student_id"):
        return audit
    gpa      = audit["current_gpa"]
    remaining = audit["credits_remaining"]
    eligible = remaining == 0 and gpa >= 2.0
    return {
        "student_id": student_id, "name": audit["name"], "program": audit["program"],
        "graduation_eligible": eligible,
        "credits_remaining": remaining, "current_gpa": gpa,
        "gpa_requirement": 2.0, "gpa_met": gpa >= 2.0,
        "credits_met": remaining == 0,
        "message": ("✅ Eligible for graduation this semester!" if eligible
                    else f"❌ Not yet eligible. {remaining} credits remaining; GPA: {gpa:.2f} (need 2.0+)."),
    }


@mcp.tool()
def generate_study_plan(student_id: str) -> dict:
    """Create a semester-by-semester plan for remaining graduation requirements."""
    audit = run_degree_audit(student_id)
    if not audit.get("student_id"):
        return audit
    remaining = audit["credits_remaining"]
    current_sem = 0
    semesters = []
    credits_left = remaining
    sem_names = ["Spring 2026","Fall 2026","Spring 2027","Fall 2027","Spring 2028","Fall 2028"]
    for sem in sem_names:
        if credits_left <= 0:
            break
        load = min(18, credits_left)
        semesters.append({"semester": sem, "planned_credits": load, "cumulative_after": remaining - credits_left + load})
        credits_left -= load
        current_sem += 1
    return {
        "student_id": student_id, "name": audit["name"], "program": audit["program"],
        "credits_remaining": remaining, "semesters_to_graduation": current_sem,
        "study_plan": semesters,
        "message": f"Study plan generated. Estimated graduation in {current_sem} semester(s).",
    }


def main():
    init_db()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()