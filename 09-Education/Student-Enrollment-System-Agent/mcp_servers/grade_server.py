"""mcp_servers/grade_server.py — Grade & Transcript Agent (port 8004 · 8 tools)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import psycopg2.extras
from mcp.server.fastmcp import FastMCP
from database.db import get_connection, init_db
from utils.email_service import send_grade_notification

mcp = FastMCP("GradeServer", host="127.0.0.1", port=8004, stateless_http=True, json_response=True)


def _cur(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


GRADE_POINTS = {
    "A": 4.00, "A-": 3.70, "B+": 3.30, "B": 3.00, "B-": 2.70,
    "C+": 2.30, "C": 2.00, "C-": 1.70, "D": 1.00, "F": 0.00, "I": None
}


def _compute_gpa(student_id: str, cur) -> float:
    cur.execute("""
        SELECT g.grade_points, c.credits
        FROM grades g JOIN courses c ON c.id=g.course_id
        WHERE g.student_id=%s AND g.grade_points IS NOT NULL
    """, (student_id,))
    rows = cur.fetchall()
    if not rows:
        return 0.0
    total_points  = sum(float(r["grade_points"]) * int(r["credits"]) for r in rows)
    total_credits = sum(int(r["credits"]) for r in rows)
    return round(total_points / total_credits, 2) if total_credits else 0.0


@mcp.tool()
def submit_grade(student_id: str, course_code: str, grade: str, submitted_by: str, notes: str = "") -> dict:
    """Faculty submit a grade for a student in a course. Grade must be: A, A-, B+, B, B-, C+, C, C-, D, F, or I."""
    if grade not in GRADE_POINTS:
        return {"success": False, "message": f"Invalid grade '{grade}'. Valid: {', '.join(GRADE_POINTS.keys())}"}
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, email FROM students WHERE student_id=%s", (student_id,))
    student = cur.fetchone()
    cur.execute("SELECT id, name FROM courses WHERE code=%s", (course_code,))
    course = cur.fetchone()
    if not student or not course:
        conn.close()
        return {"success": False, "message": "Student or course not found."}
    grade_points = GRADE_POINTS[grade]
    # Upsert grade
    cur.execute("""
        INSERT INTO grades (student_id,course_id,semester,grade,grade_points,submitted_by,notes)
        VALUES (%s,%s,'Spring',%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """, (student_id, course["id"], grade, grade_points, submitted_by, notes))
    # Update enrollment grade
    cur.execute("UPDATE enrollments SET grade=%s WHERE student_id=%s AND course_id=%s AND status='enrolled'",
                (grade, student_id, course["id"]))
    gpa = _compute_gpa(student_id, cur)
    cur.execute("UPDATE students SET gpa=%s WHERE student_id=%s", (gpa, student_id))
    conn.commit(); conn.close()
    email_result = send_grade_notification(student["email"], student["name"], course["name"], grade, gpa)
    return {
        "success": True, "student_id": student_id, "student_name": student["name"],
        "course_code": course_code, "course_name": course["name"],
        "grade": grade, "grade_points": grade_points, "updated_gpa": gpa,
        "email_sent": email_result["success"],
        "message": f"Grade '{grade}' submitted for {student['name']} in {course_code}. GPA updated to {gpa}.",
    }


@mcp.tool()
def get_student_grades(student_id: str, semester: str = "Spring") -> dict:
    """All grades for a student in a semester with GPA."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, gpa, total_credits FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    if not stu:
        conn.close()
        return {"found": False, "message": f"Student {student_id} not found."}
    cur.execute("""
        SELECT c.code, c.name, c.credits, g.grade, g.grade_points,
               g.submitted_by, g.submitted_at
        FROM grades g JOIN courses c ON c.id=g.course_id
        WHERE g.student_id=%s AND g.semester=%s
        ORDER BY c.code
    """, (student_id, semester))
    rows = cur.fetchall(); conn.close()
    grades = []
    for r in rows:
        d = dict(r)
        d["submitted_at"] = str(d["submitted_at"])[:16]
        grades.append(d)
    sem_credits = sum(g["credits"] for g in grades)
    return {
        "student_id": student_id, "student_name": stu["name"],
        "semester": semester, "cumulative_gpa": float(stu["gpa"]),
        "total_credits_earned": stu["total_credits"],
        "semester_credits": sem_credits, "grades": grades,
    }


@mcp.tool()
def calculate_gpa(student_id: str) -> dict:
    """Calculate current semester and cumulative GPA for a student."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    if not stu:
        conn.close()
        return {"found": False, "message": f"Student {student_id} not found."}
    # Cumulative
    cum_gpa = _compute_gpa(student_id, cur)
    # Semester
    cur.execute("""
        SELECT g.grade_points, c.credits FROM grades g JOIN courses c ON c.id=g.course_id
        WHERE g.student_id=%s AND g.semester='Spring' AND g.grade_points IS NOT NULL
    """, (student_id,))
    sem_rows = cur.fetchall()
    if sem_rows:
        tp = sum(float(r["grade_points"]) * int(r["credits"]) for r in sem_rows)
        tc = sum(int(r["credits"]) for r in sem_rows)
        sem_gpa = round(tp / tc, 2) if tc else 0.0
    else:
        sem_gpa = 0.0
    cur.execute("UPDATE students SET gpa=%s WHERE student_id=%s", (cum_gpa, student_id))
    conn.commit(); conn.close()
    standing = ("Good Standing" if cum_gpa >= 2.0 else
                "Academic Probation" if cum_gpa >= 1.5 else "Academic Suspension")
    return {"student_id": student_id, "student_name": stu["name"],
            "semester_gpa": sem_gpa, "cumulative_gpa": cum_gpa,
            "academic_standing": standing}


@mcp.tool()
def generate_transcript(student_id: str, generated_by: str = "system", is_official: bool = False) -> dict:
    """Generate an official academic transcript for a student."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT * FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    if not stu:
        conn.close()
        return {"found": False, "message": f"Student {student_id} not found."}
    cur.execute("""
        SELECT c.code, c.name, c.credits, c.department, g.grade, g.grade_points,
               g.semester, g.academic_year
        FROM grades g JOIN courses c ON c.id=g.course_id
        WHERE g.student_id=%s ORDER BY g.academic_year, g.semester, c.code
    """, (student_id,))
    grade_rows = cur.fetchall()
    gpa = _compute_gpa(student_id, cur)
    total_credits = sum(int(r["credits"]) for r in grade_rows if r["grade"] and r["grade"] != "I")
    transcript_data = {
        "student_id":    student_id,
        "name":          stu["name"],
        "program":       stu["program"],
        "department":    stu["department"],
        "enrolled_year": stu["enrolled_year"],
        "cumulative_gpa": gpa,
        "total_credits": total_credits,
        "courses": [dict(r) for r in grade_rows],
        "is_official":   is_official,
    }
    cur.execute("""
        INSERT INTO transcripts (student_id,generated_by,content_json,is_official)
        VALUES (%s,%s,%s,%s)
    """, (student_id, generated_by, json.dumps(transcript_data), is_official))
    conn.commit(); conn.close()
    lines = [
        f"OFFICIAL ACADEMIC TRANSCRIPT" if is_official else "UNOFFICIAL TRANSCRIPT",
        f"{'='*50}",
        f"Student: {stu['name']}  |  ID: {student_id}",
        f"Program: {stu['program']}  |  Department: {stu['department']}",
        f"{'='*50}",
    ]
    for g in grade_rows:
        lines.append(f"  {g['code']:<10} {g['name']:<35} {g['credits']}cr  Grade: {g['grade'] or 'pending':>4}")
    lines += [f"{'='*50}", f"Cumulative GPA: {gpa:.2f}  |  Total Credits: {total_credits}"]
    return {**transcript_data, "transcript_text": "\n".join(lines)}


@mcp.tool()
def file_grade_appeal(student_id: str, course_code: str, reason: str) -> dict:
    """Student submits a grade appeal; emails faculty and registrar."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, email FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    cur.execute("SELECT id, name FROM courses WHERE code=%s", (course_code,))
    course = cur.fetchone()
    if not stu or not course:
        conn.close()
        return {"success": False, "message": "Student or course not found."}
    cur.execute("SELECT grade FROM grades WHERE student_id=%s AND course_id=%s ORDER BY submitted_at DESC LIMIT 1",
                (student_id, course["id"]))
    grade_row = cur.fetchone()
    original_grade = grade_row["grade"] if grade_row else "N/A"
    cur.execute("""
        INSERT INTO grade_appeals (student_id,course_id,original_grade,appeal_reason)
        VALUES (%s,%s,%s,%s) RETURNING id
    """, (student_id, course["id"], original_grade, reason))
    appeal_id = cur.fetchone()["id"]; conn.commit(); conn.close()
    return {
        "success": True, "appeal_id": appeal_id, "student_id": student_id,
        "course_code": course_code, "original_grade": original_grade,
        "status": "pending", "reason": reason,
        "message": f"Grade appeal #{appeal_id} filed for {course_code} (original grade: {original_grade}). Status: pending review.",
    }


@mcp.tool()
def get_grade_distribution(course_code: str) -> dict:
    """Faculty view: grade distribution for a course."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT id, name FROM courses WHERE code=%s", (course_code,))
    course = cur.fetchone()
    if not course:
        conn.close()
        return {"found": False, "message": f"Course '{course_code}' not found."}
    cur.execute("""
        SELECT grade, COUNT(*) AS count FROM grades
        WHERE course_id=%s GROUP BY grade ORDER BY grade
    """, (course["id"],))
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS c FROM enrollments WHERE course_id=%s AND status='enrolled'",
                (course["id"],))
    enrolled = cur.fetchone()["c"]; conn.close()
    distribution = {r["grade"]: r["count"] for r in rows if r["grade"]}
    graded = sum(distribution.values())
    return {"course_code": course_code, "course_name": course["name"],
            "total_enrolled": enrolled, "total_graded": graded,
            "pending_grades": enrolled - graded, "distribution": distribution}


@mcp.tool()
def update_grade(student_id: str, course_code: str, new_grade: str, updated_by: str, reason: str = "") -> dict:
    """Update an existing grade with audit trail; email student."""
    if new_grade not in GRADE_POINTS:
        return {"success": False, "message": f"Invalid grade '{new_grade}'."}
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT id, name FROM courses WHERE code=%s", (course_code,))
    course = cur.fetchone()
    cur.execute("SELECT name, email FROM students WHERE student_id=%s", (student_id,))
    student = cur.fetchone()
    if not course or not student:
        conn.close()
        return {"success": False, "message": "Student or course not found."}
    cur.execute("""
        UPDATE grades SET grade=%s, grade_points=%s, submitted_by=%s, updated_at=NOW(), notes=%s
        WHERE student_id=%s AND course_id=%s
        RETURNING id
    """, (new_grade, GRADE_POINTS[new_grade], updated_by, reason, student_id, course["id"]))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": "No grade record found to update."}
    gpa = _compute_gpa(student_id, cur)
    cur.execute("UPDATE students SET gpa=%s WHERE student_id=%s", (gpa, student_id))
    conn.commit(); conn.close()
    send_grade_notification(student["email"], student["name"], course["name"], new_grade, gpa)
    return {"success": True, "student_id": student_id, "course_code": course_code,
            "new_grade": new_grade, "updated_gpa": gpa,
            "message": f"Grade updated to '{new_grade}' for {student['name']} in {course_code}."}


@mcp.tool()
def get_academic_standing(student_id: str) -> dict:
    """Determine student academic standing: Good Standing, Probation, or Suspension."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, gpa, total_credits, status FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone(); conn.close()
    if not stu:
        return {"found": False, "message": f"Student {student_id} not found."}
    gpa = float(stu["gpa"])
    standing = ("Good Standing" if gpa >= 2.5 else
                "Academic Probation" if gpa >= 2.0 else
                "Academic Suspension" if gpa >= 1.5 else "Immediate Review Required")
    recommendations = []
    if gpa < 2.5:
        recommendations.append("Meet with your academic advisor immediately")
    if gpa < 2.0:
        recommendations.append("Reduce course load and focus on core subjects")
        recommendations.append("Attend all tutoring and support sessions")
    return {"student_id": student_id, "name": stu["name"], "gpa": gpa,
            "total_credits": stu["total_credits"], "enrollment_status": stu["status"],
            "academic_standing": standing, "recommendations": recommendations}


def main():
    init_db()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()