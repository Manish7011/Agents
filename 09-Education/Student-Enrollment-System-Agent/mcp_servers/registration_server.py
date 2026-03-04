"""mcp_servers/registration_server.py — Student Registration Agent (port 8001 · 8 tools)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2.extras
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from database.db import get_connection, init_db
from utils.email_service import send_welcome_email

mcp = FastMCP("RegistrationServer", host="127.0.0.1", port=8001, stateless_http=True, json_response=True)


def _cur(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def _gen_student_id() -> str:
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT COUNT(*) AS c FROM students")
    n = cur.fetchone()["c"] + 1
    conn.close()
    return f"STU-{datetime.now().year}-{n:04d}"


@mcp.tool()
def register_student(
    name: str, email: str, program: str, department: str,
    dob: str = "", gender: str = "", semester: int = 1,
    guardian_name: str = "", guardian_email: str = ""
) -> dict:
    """Register a new student: create profile, assign student ID, send welcome email."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT id FROM students WHERE email=%s", (email,))
    if cur.fetchone():
        conn.close()
        return {"success": False, "message": f"Student with email '{email}' already exists."}
    student_id = _gen_student_id()
    cur.execute("""
        INSERT INTO students
          (student_id,name,email,dob,gender,program,department,semester,enrolled_year,
           guardian_name,guardian_email)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (student_id, name, email, dob or None, gender, program, department,
          semester, datetime.now().year, guardian_name, guardian_email))
    # Create user account for student
    import hashlib
    default_pw = hashlib.sha256(("pass123" + "edu_salt_2026").encode()).hexdigest()
    cur.execute("""
        INSERT INTO users (name,email,password_hash,role,student_id,department)
        VALUES (%s,%s,%s,'student',%s,%s)
        ON CONFLICT (email) DO NOTHING
    """, (name, email, default_pw, student_id, department))
    conn.commit(); conn.close()
    email_result = send_welcome_email(email, name, student_id, program)
    return {
        "success": True, "student_id": student_id, "name": name, "email": email,
        "program": program, "department": department, "semester": semester,
        "enrolled_year": datetime.now().year, "status": "active",
        "email_sent": email_result["success"],
        "message": f"Student {name} registered successfully with ID {student_id}. Welcome email sent.",
    }


@mcp.tool()
def get_student_profile(student_id: str = "", email: str = "") -> dict:
    """Retrieve full student profile by student ID or email."""
    if not student_id and not email:
        return {"found": False, "message": "Provide either student_id or email."}
    conn = get_connection(); cur = _cur(conn)
    if student_id:
        cur.execute("SELECT * FROM students WHERE student_id=%s", (student_id,))
    else:
        cur.execute("SELECT * FROM students WHERE email=%s", (email,))
    row = cur.fetchone(); conn.close()
    if not row:
        return {"found": False, "message": f"No student found."}
    d = dict(row)
    d["dob"] = str(d["dob"]) if d["dob"] else None
    d["created_at"] = str(d["created_at"])[:19]
    d["found"] = True
    return d


@mcp.tool()
def update_student_profile(
    student_id: str, field: str, new_value: str
) -> dict:
    """Update a student profile field. Allowed fields: program, department, address, guardian_email."""
    allowed = {"program", "department", "address", "guardian_name", "guardian_email", "phone"}
    if field not in allowed:
        return {"success": False, "message": f"Cannot update field '{field}'. Allowed: {', '.join(allowed)}"}
    conn = get_connection(); cur = _cur(conn)
    cur.execute(f"UPDATE students SET {field}=%s WHERE student_id=%s RETURNING name", (new_value, student_id))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": f"Student {student_id} not found."}
    conn.commit(); conn.close()
    return {"success": True, "student_id": student_id, "field": field, "new_value": new_value,
            "message": f"Updated {field} for {row['name']} (ID: {student_id})"}


@mcp.tool()
def search_students(
    name: str = "", department: str = "", program: str = "",
    status: str = "", limit: int = 20
) -> list:
    """Search students by name, department, program, or status."""
    conn = get_connection(); cur = _cur(conn)
    q = "SELECT student_id,name,email,program,department,semester,status,gpa,total_credits FROM students WHERE 1=1"
    params = []
    if name:
        q += " AND name ILIKE %s"; params.append(f"%{name}%")
    if department:
        q += " AND department ILIKE %s"; params.append(f"%{department}%")
    if program:
        q += " AND program ILIKE %s"; params.append(f"%{program}%")
    if status:
        q += " AND status=%s"; params.append(status)
    q += f" ORDER BY name LIMIT {limit}"
    cur.execute(q, params); rows = cur.fetchall(); conn.close()
    return [dict(r) for r in rows] if rows else [{"message": "No students found matching search criteria."}]


@mcp.tool()
def change_enrollment_status(student_id: str, new_status: str, reason: str = "") -> dict:
    """Change student enrollment status: active, suspended, graduated, withdrawn, deferred."""
    valid = {"active", "suspended", "graduated", "withdrawn", "deferred"}
    if new_status not in valid:
        return {"success": False, "message": f"Invalid status. Choose from: {', '.join(valid)}"}
    conn = get_connection(); cur = _cur(conn)
    cur.execute("UPDATE students SET status=%s WHERE student_id=%s RETURNING name, email",
                (new_status, student_id))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": f"Student {student_id} not found."}
    conn.commit(); conn.close()
    return {"success": True, "student_id": student_id, "name": row["name"],
            "new_status": new_status, "reason": reason,
            "message": f"Status of {row['name']} changed to '{new_status}'."}


@mcp.tool()
def get_department_roster(department: str, status: str = "active") -> dict:
    """List all students in a department with enrollment counts."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("""
        SELECT student_id,name,email,program,semester,gpa,total_credits,status
        FROM students WHERE department ILIKE %s AND status=%s
        ORDER BY name
    """, (f"%{department}%", status))
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS c FROM students WHERE department ILIKE %s AND status=%s",
                (f"%{department}%", status))
    count = cur.fetchone()["c"]; conn.close()
    return {
        "department": department, "status": status, "count": count,
        "students": [dict(r) for r in rows],
        "message": f"{count} {status} students in {department} department.",
    }


@mcp.tool()
def send_welcome_email_tool(student_id: str) -> dict:
    """Send or resend a welcome email to a registered student."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name,email,program FROM students WHERE student_id=%s", (student_id,))
    row = cur.fetchone(); conn.close()
    if not row:
        return {"success": False, "message": f"Student {student_id} not found."}
    result = send_welcome_email(row["email"], row["name"], student_id, row["program"])
    return {"success": result["success"], "student_id": student_id, "email": row["email"],
            "message": result["message"]}


@mcp.tool()
def get_student_statistics() -> dict:
    """Return admission statistics by department, program, gender, and year."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT department, COUNT(*) AS count FROM students WHERE status='active' GROUP BY department ORDER BY count DESC")
    by_dept = [{"department": r["department"], "count": r["count"]} for r in cur.fetchall()]
    cur.execute("SELECT status, COUNT(*) AS count FROM students GROUP BY status ORDER BY count DESC")
    by_status = [{"status": r["status"], "count": r["count"]} for r in cur.fetchall()]
    cur.execute("SELECT gender, COUNT(*) AS count FROM students WHERE gender IS NOT NULL GROUP BY gender")
    by_gender = [{"gender": r["gender"], "count": r["count"]} for r in cur.fetchall()]
    cur.execute("SELECT COUNT(*) AS total FROM students")
    total = cur.fetchone()["total"]; conn.close()
    return {
        "total_students": total,
        "by_department": by_dept,
        "by_status": by_status,
        "by_gender": by_gender,
    }


def main():
    init_db()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()