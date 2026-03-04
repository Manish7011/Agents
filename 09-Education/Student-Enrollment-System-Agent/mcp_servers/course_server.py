"""mcp_servers/course_server.py — Course Management Agent (port 8002 · 8 tools)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2.extras
from mcp.server.fastmcp import FastMCP
from database.db import get_connection, init_db
from utils.email_service import send_course_status_notification

mcp = FastMCP("CourseServer", host="127.0.0.1", port=8002, stateless_http=True, json_response=True)


def _cur(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


@mcp.tool()
def create_course(
    code: str, name: str, department: str, credits: int = 3,
    capacity: int = 30, semester: str = "Spring",
    level: str = "undergraduate", instructor: str = "",
    prerequisites: str = "None", description: str = ""
) -> dict:
    """Create a new course in the catalogue."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT id FROM courses WHERE code=%s", (code,))
    if cur.fetchone():
        conn.close()
        return {"success": False, "message": f"Course code '{code}' already exists."}
    cur.execute("""
        INSERT INTO courses
          (code,name,department,credits,capacity,enrolled,semester,level,
           prerequisites,instructor,description,status)
        VALUES (%s,%s,%s,%s,%s,0,%s,%s,%s,%s,%s,'open') RETURNING id
    """, (code, name, department, credits, capacity, semester, level, prerequisites, instructor, description))
    cid = cur.fetchone()["id"]; conn.commit(); conn.close()
    return {"success": True, "course_id": cid, "code": code, "name": name,
            "department": department, "credits": credits, "capacity": capacity,
            "status": "open", "message": f"Course '{name}' ({code}) created successfully."}


@mcp.tool()
def update_course(
    course_code: str, field: str, new_value: str
) -> dict:
    """Update a course field. Allowed: name, description, capacity, instructor, semester, prerequisites, level."""
    allowed = {"name", "description", "capacity", "instructor", "semester", "prerequisites", "level"}
    if field not in allowed:
        return {"success": False, "message": f"Cannot update '{field}'. Allowed: {', '.join(allowed)}"}
    conn = get_connection(); cur = _cur(conn)
    val = int(new_value) if field == "capacity" else new_value
    cur.execute(f"UPDATE courses SET {field}=%s WHERE code=%s RETURNING id, name",
                (val, course_code))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": f"Course '{course_code}' not found."}
    conn.commit(); conn.close()
    return {"success": True, "course_code": course_code, "course_name": row["name"],
            "field": field, "new_value": new_value,
            "message": f"Updated {field} for course {course_code}."}


@mcp.tool()
def get_course_details(course_code: str) -> dict:
    """Get full course details including current enrollment vs capacity."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT * FROM courses WHERE code=%s", (course_code,))
    row = cur.fetchone(); conn.close()
    if not row:
        return {"found": False, "message": f"Course '{course_code}' not found."}
    d = dict(row)
    d["found"] = True
    d["seats_available"] = max(0, d["capacity"] - d["enrolled"])
    d["fill_pct"] = round(d["enrolled"] / d["capacity"] * 100, 1) if d["capacity"] else 0
    d["created_at"] = str(d["created_at"])[:19]
    return d


@mcp.tool()
def list_courses(
    department: str = "", semester: str = "", status: str = "",
    level: str = "", limit: int = 20
) -> list:
    """List courses with optional filters."""
    conn = get_connection(); cur = _cur(conn)
    q = """SELECT id,code,name,department,credits,capacity,enrolled,semester,level,
                  instructor,status,prerequisites
           FROM courses WHERE 1=1"""
    params = []
    if department:
        q += " AND department ILIKE %s"; params.append(f"%{department}%")
    if semester:
        q += " AND semester=%s"; params.append(semester)
    if status:
        q += " AND status=%s"; params.append(status)
    if level:
        q += " AND level=%s"; params.append(level)
    q += f" ORDER BY code LIMIT {limit}"
    cur.execute(q, params); rows = cur.fetchall(); conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["seats_available"] = max(0, d["capacity"] - d["enrolled"])
        result.append(d)
    return result if result else [{"message": "No courses found matching criteria."}]


@mcp.tool()
def set_course_status(course_code: str, new_status: str, notify_waitlisted: bool = True) -> dict:
    """Open or close a course; optionally email waitlisted students."""
    valid = {"open", "closed", "cancelled", "completed"}
    if new_status not in valid:
        return {"success": False, "message": f"Invalid status. Choose: {', '.join(valid)}"}
    conn = get_connection(); cur = _cur(conn)
    cur.execute("UPDATE courses SET status=%s WHERE code=%s RETURNING id, name",
                (new_status, course_code))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": f"Course '{course_code}' not found."}
    notified = 0
    if notify_waitlisted and new_status == "open":
        cur.execute("""
            SELECT s.email, s.name FROM enrollments e
            JOIN students s ON s.student_id=e.student_id
            WHERE e.course_id=%s AND e.status='waitlisted'
        """, (row["id"],))
        waitlisted = cur.fetchall()
        for w in waitlisted:
            send_course_status_notification(w["email"], w["name"], row["name"], new_status,
                                            "A seat is now available — enroll immediately!")
            notified += 1
    conn.commit(); conn.close()
    return {"success": True, "course_code": course_code, "course_name": row["name"],
            "new_status": new_status, "waitlisted_notified": notified,
            "message": f"Course '{course_code}' status set to '{new_status}'. {notified} waitlisted students notified."}


@mcp.tool()
def get_waitlist(course_code: str) -> dict:
    """Return the current waitlist for a course."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT id, name FROM courses WHERE code=%s", (course_code,))
    course = cur.fetchone()
    if not course:
        conn.close()
        return {"found": False, "message": f"Course '{course_code}' not found."}
    cur.execute("""
        SELECT s.student_id, s.name, s.email, e.enrolled_at
        FROM enrollments e JOIN students s ON s.student_id=e.student_id
        WHERE e.course_id=%s AND e.status='waitlisted'
        ORDER BY e.enrolled_at ASC
    """, (course["id"],))
    rows = cur.fetchall(); conn.close()
    waitlist = [{"position": i+1, "student_id": r["student_id"], "name": r["name"],
                 "email": r["email"], "waitlisted_since": str(r["enrolled_at"])[:16]}
                for i, r in enumerate(rows)]
    return {"course_code": course_code, "course_name": course["name"],
            "waitlist_count": len(waitlist), "waitlist": waitlist}


@mcp.tool()
def add_to_waitlist(student_id: str, course_code: str) -> dict:
    """Add a student to the waitlist when a course is at capacity."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT id, name, capacity, enrolled, status FROM courses WHERE code=%s", (course_code,))
    course = cur.fetchone()
    if not course:
        conn.close()
        return {"success": False, "message": f"Course '{course_code}' not found."}
    # Check if already enrolled or waitlisted
    cur.execute("SELECT status FROM enrollments WHERE student_id=%s AND course_id=%s",
                (student_id, course["id"]))
    existing = cur.fetchone()
    if existing:
        conn.close()
        return {"success": False, "message": f"Student {student_id} is already {existing['status']} for {course_code}."}
    cur.execute("""
        INSERT INTO enrollments (student_id,course_id,semester,status)
        VALUES (%s,%s,'Spring','waitlisted')
    """, (student_id, course["id"]))
    # Get waitlist position
    cur.execute("SELECT COUNT(*) AS pos FROM enrollments WHERE course_id=%s AND status='waitlisted'",
                (course["id"],))
    position = cur.fetchone()["pos"]
    conn.commit(); conn.close()
    return {"success": True, "student_id": student_id, "course_code": course_code,
            "course_name": course["name"], "waitlist_position": position,
            "message": f"Added to waitlist for '{course_code}'. Position: #{position}"}


@mcp.tool()
def get_enrollment_stats() -> dict:
    """Return enrollment statistics across all courses."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("""
        SELECT
          COUNT(*) AS total_courses,
          SUM(enrolled) AS total_enrolled,
          SUM(capacity) AS total_capacity,
          AVG(CASE WHEN capacity>0 THEN enrolled::float/capacity*100 ELSE 0 END) AS avg_fill_pct
        FROM courses WHERE status='open'
    """)
    summary = dict(cur.fetchone())
    cur.execute("""
        SELECT code, name, enrolled, capacity,
               ROUND(enrolled::numeric/NULLIF(capacity,0)*100,1) AS fill_pct
        FROM courses WHERE status='open'
        ORDER BY fill_pct DESC NULLS LAST LIMIT 5
    """)
    top_courses = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT COUNT(*) AS c FROM enrollments WHERE status='waitlisted'")
    waitlist_total = cur.fetchone()["c"]; conn.close()
    return {
        "summary": {k: float(v) if isinstance(v, float) else int(v or 0) for k, v in summary.items()},
        "total_waitlisted": waitlist_total,
        "most_popular_courses": top_courses,
    }


def main():
    init_db()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()