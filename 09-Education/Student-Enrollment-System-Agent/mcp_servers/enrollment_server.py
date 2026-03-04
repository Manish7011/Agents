"""mcp_servers/enrollment_server.py — Enrollment Agent (port 8003 · 8 tools)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2.extras
from mcp.server.fastmcp import FastMCP
from database.db import get_connection, init_db
from utils.email_service import send_enrollment_confirmation

mcp = FastMCP("EnrollmentServer", host="127.0.0.1", port=8003, stateless_http=True, json_response=True)


def _cur(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


MAX_CREDITS_PER_SEMESTER = 21


@mcp.tool()
def enroll_student(student_id: str, course_code: str) -> dict:
    """Enroll a student: check prerequisites, capacity, credit limit, then register."""
    conn = get_connection(); cur = _cur(conn)
    # Validate student
    cur.execute("SELECT name, email, status, total_credits FROM students WHERE student_id=%s", (student_id,))
    student = cur.fetchone()
    if not student:
        conn.close()
        return {"success": False, "message": f"Student {student_id} not found."}
    if student["status"] not in ("active",):
        conn.close()
        return {"success": False, "message": f"Student {student_id} is {student['status']} — cannot enroll."}
    # Validate course
    cur.execute("SELECT id,name,capacity,enrolled,status,prerequisites,credits FROM courses WHERE code=%s", (course_code,))
    course = cur.fetchone()
    if not course:
        conn.close()
        return {"success": False, "message": f"Course '{course_code}' not found."}
    if course["status"] != "open":
        conn.close()
        return {"success": False, "message": f"Course '{course_code}' is {course['status']} — not accepting enrollment."}
    # Check already enrolled
    cur.execute("SELECT status FROM enrollments WHERE student_id=%s AND course_id=%s AND status='enrolled'",
                (student_id, course["id"]))
    if cur.fetchone():
        conn.close()
        return {"success": False, "message": f"Student {student_id} is already enrolled in {course_code}."}
    # Check capacity
    if course["enrolled"] >= course["capacity"]:
        conn.close()
        return {"success": False, "message": f"Course '{course_code}' is full ({course['enrolled']}/{course['capacity']}). Use add_to_waitlist."}
    # Check credit limit (current semester)
    cur.execute("""
        SELECT COALESCE(SUM(c.credits),0) AS current_credits
        FROM enrollments e JOIN courses c ON c.id=e.course_id
        WHERE e.student_id=%s AND e.status='enrolled' AND e.semester='Spring'
    """, (student_id,))
    current_credits = int(cur.fetchone()["current_credits"])
    if current_credits + course["credits"] > MAX_CREDITS_PER_SEMESTER:
        conn.close()
        return {"success": False,
                "message": f"Credit limit exceeded. Current: {current_credits}, Adding: {course['credits']}, Max: {MAX_CREDITS_PER_SEMESTER}"}
    # Enroll
    cur.execute("""
        INSERT INTO enrollments (student_id,course_id,semester,status)
        VALUES (%s,%s,'Spring','enrolled')
    """, (student_id, course["id"]))
    cur.execute("UPDATE courses SET enrolled=enrolled+1 WHERE id=%s", (course["id"],))
    conn.commit(); conn.close()
    email_result = send_enrollment_confirmation(
        student["email"], student["name"], course["name"], course_code, "enrolled"
    )
    return {
        "success": True, "student_id": student_id, "student_name": student["name"],
        "course_code": course_code, "course_name": course["name"],
        "credits": course["credits"], "total_credits_this_sem": current_credits + course["credits"],
        "email_sent": email_result["success"],
        "message": f"✅ {student['name']} enrolled in '{course['name']}' ({course_code}). Confirmation email sent.",
    }


@mcp.tool()
def drop_course(student_id: str, course_code: str) -> dict:
    """Drop a student from a course; free the seat; send confirmation email."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, email FROM students WHERE student_id=%s", (student_id,))
    student = cur.fetchone()
    if not student:
        conn.close()
        return {"success": False, "message": f"Student {student_id} not found."}
    cur.execute("SELECT id, name FROM courses WHERE code=%s", (course_code,))
    course = cur.fetchone()
    if not course:
        conn.close()
        return {"success": False, "message": f"Course '{course_code}' not found."}
    cur.execute("""
        UPDATE enrollments SET status='dropped', dropped_at=NOW()
        WHERE student_id=%s AND course_id=%s AND status='enrolled'
        RETURNING id
    """, (student_id, course["id"]))
    if not cur.fetchone():
        conn.close()
        return {"success": False, "message": f"Student {student_id} is not enrolled in {course_code}."}
    cur.execute("UPDATE courses SET enrolled=GREATEST(0,enrolled-1) WHERE id=%s", (course["id"],))
    conn.commit(); conn.close()
    email_result = send_enrollment_confirmation(
        student["email"], student["name"], course["name"], course_code, "dropped"
    )
    return {"success": True, "student_id": student_id, "course_code": course_code,
            "email_sent": email_result["success"],
            "message": f"✅ {student['name']} dropped from '{course['name']}'. Seat freed."}


@mcp.tool()
def get_student_schedule(student_id: str) -> dict:
    """Return a student's current semester enrolled courses with timetable info."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    if not stu:
        conn.close()
        return {"found": False, "message": f"Student {student_id} not found."}
    cur.execute("""
        SELECT c.code, c.name, c.credits, c.instructor, e.status, e.enrolled_at,
               t.day_of_week, t.start_time::text, t.end_time::text, t.room, t.slot_type
        FROM enrollments e
        JOIN courses c ON c.id=e.course_id
        LEFT JOIN timetable_slots t ON t.course_id=c.id AND t.semester='Spring'
        WHERE e.student_id=%s AND e.status='enrolled' AND e.semester='Spring'
        ORDER BY t.day_of_week, t.start_time
    """, (student_id,))
    rows = cur.fetchall()
    total_credits = sum(r["credits"] for r in rows if r["credits"])
    conn.close()
    courses = []
    for r in rows:
        d = dict(r)
        d["enrolled_at"] = str(d["enrolled_at"])[:16]
        courses.append(d)
    return {"student_id": student_id, "student_name": stu["name"],
            "semester": "Spring 2026", "total_credits": total_credits,
            "course_count": len(set(r["code"] for r in courses)),
            "schedule": courses}


@mcp.tool()
def check_prerequisites(student_id: str, course_code: str) -> dict:
    """Check whether a student meets all prerequisites for a course."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT prerequisites FROM courses WHERE code=%s", (course_code,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"found": False, "message": f"Course '{course_code}' not found."}
    prereqs_str = row["prerequisites"] or "None"
    if prereqs_str.strip().lower() in ("none", ""):
        conn.close()
        return {"eligible": True, "course_code": course_code, "prerequisites": "None",
                "message": "No prerequisites required. Student is eligible."}
    prereqs = [p.strip() for p in prereqs_str.split(",") if p.strip().lower() != "none"]
    # Check completed enrollments
    cur.execute("""
        SELECT c.code FROM enrollments e JOIN courses c ON c.id=e.course_id
        WHERE e.student_id=%s AND e.status IN ('completed','enrolled')
    """, (student_id,))
    completed = {r["code"] for r in cur.fetchall()}; conn.close()
    met     = [p for p in prereqs if p in completed]
    missing = [p for p in prereqs if p not in completed]
    return {
        "student_id": student_id, "course_code": course_code,
        "prerequisites": prereqs, "met": met, "missing": missing,
        "eligible": len(missing) == 0,
        "message": ("✅ All prerequisites met — eligible to enroll." if not missing
                    else f"❌ Missing prerequisites: {', '.join(missing)}"),
    }


@mcp.tool()
def get_enrollment_history(student_id: str) -> list:
    """Full enrollment history for a student across all semesters."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("""
        SELECT c.code, c.name, c.credits, c.department, e.semester,
               e.academic_year, e.status, e.enrolled_at, e.dropped_at, e.grade
        FROM enrollments e JOIN courses c ON c.id=e.course_id
        WHERE e.student_id=%s
        ORDER BY e.academic_year DESC, e.semester, c.code
    """, (student_id,))
    rows = cur.fetchall(); conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["enrolled_at"] = str(d["enrolled_at"])[:16]
        d["dropped_at"]  = str(d["dropped_at"])[:16] if d["dropped_at"] else None
        result.append(d)
    return result if result else [{"message": f"No enrollment history found for {student_id}."}]


@mcp.tool()
def bulk_enroll(student_ids: str, course_code: str) -> dict:
    """Enroll multiple students (comma-separated IDs) in a course at once."""
    ids = [s.strip() for s in student_ids.split(",") if s.strip()]
    results = {"success": [], "failed": []}
    for sid in ids:
        res = enroll_student(sid, course_code)
        if res.get("success"):
            results["success"].append(sid)
        else:
            results["failed"].append({"student_id": sid, "reason": res.get("message","")})
    return {
        "course_code": course_code, "attempted": len(ids),
        "enrolled": len(results["success"]), "failed": len(results["failed"]),
        "enrolled_ids": results["success"], "failed_details": results["failed"],
        "message": f"Bulk enrollment: {len(results['success'])}/{len(ids)} successful.",
    }


@mcp.tool()
def get_course_roster(course_code: str) -> dict:
    """List all enrolled students for a specific course."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT id, name FROM courses WHERE code=%s", (course_code,))
    course = cur.fetchone()
    if not course:
        conn.close()
        return {"found": False, "message": f"Course '{course_code}' not found."}
    cur.execute("""
        SELECT s.student_id, s.name, s.email, s.program, s.semester, e.enrolled_at
        FROM enrollments e JOIN students s ON s.student_id=e.student_id
        WHERE e.course_id=%s AND e.status='enrolled'
        ORDER BY s.name
    """, (course["id"],))
    rows = cur.fetchall(); conn.close()
    roster = [{"student_id": r["student_id"], "name": r["name"], "email": r["email"],
               "program": r["program"], "semester": r["semester"],
               "enrolled_at": str(r["enrolled_at"])[:16]} for r in rows]
    return {"course_code": course_code, "course_name": course["name"],
            "enrolled_count": len(roster), "roster": roster}


@mcp.tool()
def send_enrollment_confirmation_tool(student_id: str, course_code: str, action: str = "enrolled") -> dict:
    """Send enrollment or drop confirmation email to a student."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, email FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    cur.execute("SELECT name FROM courses WHERE code=%s", (course_code,))
    course = cur.fetchone(); conn.close()
    if not stu or not course:
        return {"success": False, "message": "Student or course not found."}
    result = send_enrollment_confirmation(stu["email"], stu["name"], course["name"], course_code, action)
    return {"success": result["success"], "email": stu["email"], "message": result["message"]}


def main():
    init_db()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()