"""mcp_servers/timetable_server.py — Timetable & Scheduling Agent (port 8007 · 8 tools)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2.extras
from mcp.server.fastmcp import FastMCP
from database.db import get_connection, init_db
from utils.email_service import send_schedule_update

mcp = FastMCP("TimetableServer", host="127.0.0.1", port=8007, stateless_http=True, json_response=True)


def _cur(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


@mcp.tool()
def create_timetable_slot(
    course_code: str, faculty_email: str, faculty_name: str,
    room: str, day_of_week: str, start_time: str, end_time: str,
    semester: str = "Spring", slot_type: str = "lecture"
) -> dict:
    """Create a class time slot for a course."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT id, name FROM courses WHERE code=%s", (course_code,))
    course = cur.fetchone()
    if not course:
        conn.close()
        return {"success": False, "message": f"Course '{course_code}' not found."}
    cur.execute("""
        INSERT INTO timetable_slots
          (course_id,faculty_email,faculty_name,room,day_of_week,start_time,end_time,semester,slot_type)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (course["id"], faculty_email, faculty_name, room, day_of_week,
          start_time, end_time, semester, slot_type))
    slot_id = cur.fetchone()["id"]; conn.commit(); conn.close()
    return {"success": True, "slot_id": slot_id, "course_code": course_code,
            "course_name": course["name"], "room": room, "day": day_of_week,
            "time": f"{start_time}–{end_time}", "type": slot_type,
            "message": f"Slot created: {course_code} | {day_of_week} {start_time}–{end_time} | Room: {room}"}


@mcp.tool()
def assign_room(slot_id: int, new_room: str) -> dict:
    """Assign a room to a timetable slot; check for double-booking conflicts."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT course_id, day_of_week, start_time, end_time, semester FROM timetable_slots WHERE id=%s", (slot_id,))
    slot = cur.fetchone()
    if not slot:
        conn.close()
        return {"success": False, "message": f"Slot #{slot_id} not found."}
    # Conflict check
    cur.execute("""
        SELECT ts.id, c.code FROM timetable_slots ts JOIN courses c ON c.id=ts.course_id
        WHERE ts.room=%s AND ts.day_of_week=%s AND ts.semester=%s
          AND ts.id!=%s
          AND (ts.start_time < %s AND ts.end_time > %s)
    """, (new_room, slot["day_of_week"], slot["semester"], slot_id,
          slot["end_time"], slot["start_time"]))
    conflicts = cur.fetchall()
    if conflicts:
        conn.close()
        conflict_codes = [c["code"] for c in conflicts]
        return {"success": False, "message": f"Room '{new_room}' is already booked at this time by: {', '.join(conflict_codes)}"}
    cur.execute("UPDATE timetable_slots SET room=%s WHERE id=%s", (new_room, slot_id))
    conn.commit(); conn.close()
    return {"success": True, "slot_id": slot_id, "new_room": new_room,
            "message": f"Room '{new_room}' assigned to slot #{slot_id} — no conflicts."}


@mcp.tool()
def get_faculty_timetable(faculty_email: str, semester: str = "Spring") -> dict:
    """Return a faculty member's full weekly teaching schedule."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("""
        SELECT c.code, c.name, c.credits, ts.room, ts.day_of_week,
               ts.start_time::text, ts.end_time::text, ts.slot_type, c.enrolled
        FROM timetable_slots ts JOIN courses c ON c.id=ts.course_id
        WHERE ts.faculty_email=%s AND ts.semester=%s
        ORDER BY ts.day_of_week, ts.start_time
    """, (faculty_email, semester))
    rows = cur.fetchall(); conn.close()
    schedule = {}
    for r in rows:
        day = r["day_of_week"]
        if day not in schedule:
            schedule[day] = []
        schedule[day].append({
            "course_code": r["code"], "course_name": r["name"],
            "time": f"{r['start_time']}–{r['end_time']}", "room": r["room"],
            "type": r["slot_type"], "enrolled": r["enrolled"]
        })
    return {"faculty_email": faculty_email, "semester": semester,
            "total_slots": len(rows), "schedule": schedule}


@mcp.tool()
def get_student_timetable(student_id: str, semester: str = "Spring") -> dict:
    """Return a student's personalised weekly class timetable."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    if not stu:
        conn.close()
        return {"found": False, "message": f"Student {student_id} not found."}
    cur.execute("""
        SELECT c.code, c.name, c.credits, ts.room, ts.day_of_week,
               ts.start_time::text, ts.end_time::text, ts.slot_type, ts.faculty_name
        FROM enrollments e
        JOIN courses c ON c.id=e.course_id
        JOIN timetable_slots ts ON ts.course_id=c.id AND ts.semester=%s
        WHERE e.student_id=%s AND e.status='enrolled' AND e.semester=%s
        ORDER BY ts.day_of_week, ts.start_time
    """, (semester, student_id, semester))
    rows = cur.fetchall(); conn.close()
    schedule = {}
    for day in DAYS_ORDER:
        slots = [{"course_code": r["code"], "course_name": r["name"],
                  "time": f"{r['start_time']}–{r['end_time']}", "room": r["room"],
                  "type": r["slot_type"], "faculty": r["faculty_name"]}
                 for r in rows if r["day_of_week"] == day]
        if slots:
            schedule[day] = slots
    return {"student_id": student_id, "name": stu["name"], "semester": semester,
            "total_classes": len(rows), "schedule": schedule}


@mcp.tool()
def detect_conflicts() -> dict:
    """Check all scheduled slots for room or faculty conflicts."""
    conn = get_connection(); cur = _cur(conn)
    # Room conflicts
    cur.execute("""
        SELECT ts1.id AS slot1, ts2.id AS slot2, ts1.room,
               c1.code AS course1, c2.code AS course2,
               ts1.day_of_week, ts1.start_time::text, ts1.end_time::text
        FROM timetable_slots ts1
        JOIN timetable_slots ts2 ON ts1.id < ts2.id
        JOIN courses c1 ON c1.id=ts1.course_id
        JOIN courses c2 ON c2.id=ts2.course_id
        WHERE ts1.room=ts2.room
          AND ts1.day_of_week=ts2.day_of_week
          AND ts1.semester=ts2.semester
          AND ts1.start_time < ts2.end_time
          AND ts1.end_time > ts2.start_time
    """)
    room_conflicts = [dict(r) for r in cur.fetchall()]
    # Faculty conflicts
    cur.execute("""
        SELECT ts1.id AS slot1, ts2.id AS slot2, ts1.faculty_email,
               c1.code AS course1, c2.code AS course2,
               ts1.day_of_week, ts1.start_time::text
        FROM timetable_slots ts1
        JOIN timetable_slots ts2 ON ts1.id < ts2.id
        JOIN courses c1 ON c1.id=ts1.course_id
        JOIN courses c2 ON c2.id=ts2.course_id
        WHERE ts1.faculty_email=ts2.faculty_email
          AND ts1.day_of_week=ts2.day_of_week
          AND ts1.semester=ts2.semester
          AND ts1.start_time < ts2.end_time
          AND ts1.end_time > ts2.start_time
    """)
    faculty_conflicts = [dict(r) for r in cur.fetchall()]; conn.close()
    total = len(room_conflicts) + len(faculty_conflicts)
    return {
        "total_conflicts": total,
        "room_conflicts": room_conflicts,
        "faculty_conflicts": faculty_conflicts,
        "status": "✅ No conflicts detected!" if total == 0 else f"⚠️ {total} conflict(s) found — requires resolution.",
    }


@mcp.tool()
def update_slot(slot_id: int, field: str, new_value: str) -> dict:
    """Modify a timetable slot — room, time, or day; email affected students."""
    allowed = {"room", "day_of_week", "start_time", "end_time", "slot_type"}
    if field not in allowed:
        return {"success": False, "message": f"Cannot update '{field}'. Allowed: {', '.join(allowed)}"}
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT course_id FROM timetable_slots WHERE id=%s", (slot_id,))
    slot = cur.fetchone()
    if not slot:
        conn.close()
        return {"success": False, "message": f"Slot #{slot_id} not found."}
    cur.execute(f"UPDATE timetable_slots SET {field}=%s WHERE id=%s", (new_value, slot_id))
    # Get enrolled students for notification
    cur.execute("""
        SELECT s.email, s.name, c.name AS course_name FROM enrollments e
        JOIN students s ON s.student_id=e.student_id
        JOIN courses c ON c.id=e.course_id
        WHERE e.course_id=%s AND e.status='enrolled'
    """, (slot["course_id"],))
    students = cur.fetchall()
    conn.commit(); conn.close()
    notified = 0
    for s in students:
        send_schedule_update(s["email"], s["name"], s["course_name"],
                             f"{field.replace('_',' ').title()} changed to: {new_value}")
        notified += 1
    return {"success": True, "slot_id": slot_id, "field": field, "new_value": new_value,
            "students_notified": notified,
            "message": f"Slot #{slot_id} updated ({field}={new_value}). {notified} students emailed."}


@mcp.tool()
def get_room_availability(room: str, day_of_week: str, semester: str = "Spring") -> dict:
    """Show which time slots a room is available or booked on a given day."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("""
        SELECT ts.start_time::text, ts.end_time::text, c.code, c.name, ts.slot_type, ts.faculty_name
        FROM timetable_slots ts JOIN courses c ON c.id=ts.course_id
        WHERE ts.room=%s AND ts.day_of_week=%s AND ts.semester=%s
        ORDER BY ts.start_time
    """, (room, day_of_week, semester))
    bookings = [dict(r) for r in cur.fetchall()]; conn.close()
    # Compute free slots (basic 8am–6pm check)
    all_hours = [f"{h:02d}:00" for h in range(8, 18)]
    booked_ranges = [(b["start_time"], b["end_time"]) for b in bookings]
    return {
        "room": room, "day": day_of_week, "semester": semester,
        "booked_slots": bookings, "booking_count": len(bookings),
        "note": "Booked time windows shown above. Room is free outside these windows (8am–6pm)."
    }


@mcp.tool()
def send_schedule_notification_tool(course_code: str, change_details: str) -> dict:
    """Email updated timetable to all students enrolled in a course."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT id, name FROM courses WHERE code=%s", (course_code,))
    course = cur.fetchone()
    if not course:
        conn.close()
        return {"success": False, "message": f"Course '{course_code}' not found."}
    cur.execute("""
        SELECT s.email, s.name FROM enrollments e
        JOIN students s ON s.student_id=e.student_id
        WHERE e.course_id=%s AND e.status='enrolled'
    """, (course["id"],))
    students = cur.fetchall(); conn.close()
    sent = 0
    for s in students:
        send_schedule_update(s["email"], s["name"], course["name"], change_details)
        sent += 1
    return {"success": True, "course_code": course_code, "students_notified": sent,
            "change_details": change_details,
            "message": f"Schedule notification sent to {sent} students enrolled in {course_code}."}


def main():
    init_db()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()