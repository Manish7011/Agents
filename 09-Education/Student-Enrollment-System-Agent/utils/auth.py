"""utils/auth.py — RBAC authentication helpers."""

import psycopg2.extras
from database.db import get_connection, verify_password

ROLE_AGENTS: dict[str, list[str]] = {
    "admin": [
        "Student Registration", "Course Management", "Enrollment",
        "Grade & Transcript", "Academic Advising",
        "Fee & Scholarship", "Timetable & Scheduling", "Direct Answering",
    ],
    "registrar": [
        "Student Registration", "Course Management", "Enrollment",
        "Fee & Scholarship", "Timetable & Scheduling", "Direct Answering",
    ],
    "faculty": [
        "Grade & Transcript", "Course Management",
        "Timetable & Scheduling", "Direct Answering",
    ],
    "advisor": [
        "Academic Advising", "Student Registration", "Direct Answering",
    ],
    "student": [
        "Enrollment", "Grade & Transcript",
        "Timetable & Scheduling", "Fee & Scholarship", "Direct Answering",
    ],
}

ROLE_LABELS = {
    "admin":      "🛡️  Admin",
    "registrar":  "📋  Registrar",
    "faculty":    "👨‍🏫  Faculty",
    "advisor":    "🎓  Advisor",
    "student":    "🎒  Student",
}

ROLE_COLORS = {
    "admin":      "#f59e0b",
    "registrar":  "#1d4ed8",
    "faculty":    "#15803d",
    "advisor":    "#0b7b6b",
    "student":    "#5b21b6",
}


def authenticate(email: str, password: str) -> dict | None:
    try:
        conn = get_connection()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id,name,email,password_hash,role,student_id,staff_id,department "
            "FROM users WHERE email=%s AND is_active=TRUE",
            (email.strip().lower(),),
        )
        user = cur.fetchone(); conn.close()
        if user and verify_password(password, user["password_hash"]):
            return {
                "id":         user["id"],
                "name":       user["name"],
                "email":      user["email"],
                "role":       user["role"],
                "student_id": user["student_id"],
                "staff_id":   user["staff_id"],
                "department": user["department"],
            }
        return None
    except Exception:
        return None
