"""mcp_servers/fee_server.py — Fee & Scholarship Agent (port 8006 · 8 tools)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import psycopg2.extras
from mcp.server.fastmcp import FastMCP
from database.db import get_connection, init_db
from utils.email_service import send_fee_reminder, send_payment_receipt, send_scholarship_award

mcp = FastMCP("FeeServer", host="127.0.0.1", port=8006, stateless_http=True, json_response=True)


def _cur(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


@mcp.tool()
def post_tuition_fee(
    student_id: str, fee_type: str, amount: float,
    semester: str = "Spring", due_date: str = "2026-03-31",
    description: str = ""
) -> dict:
    """Post a tuition or other fee charge to a student's account."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    if not stu:
        conn.close()
        return {"success": False, "message": f"Student {student_id} not found."}
    cur.execute("""
        INSERT INTO fees (student_id,fee_type,amount,semester,due_date,status,description)
        VALUES (%s,%s,%s,%s,%s,'unpaid',%s) RETURNING id
    """, (student_id, fee_type, amount, semester, due_date, description or f"{fee_type} fee {semester}"))
    fee_id = cur.fetchone()["id"]; conn.commit(); conn.close()
    return {"success": True, "fee_id": fee_id, "student_id": student_id,
            "student_name": stu["name"], "fee_type": fee_type, "amount": amount,
            "due_date": due_date, "status": "unpaid",
            "message": f"Fee posted: ₹{amount:,.0f} ({fee_type}) for {stu['name']}."}


@mcp.tool()
def record_payment(
    student_id: str, fee_id: int, amount_paid: float,
    payment_method: str = "UPI", processed_by: str = ""
) -> dict:
    """Record a payment; update fee status; send receipt email."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, email FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    cur.execute("SELECT amount, status, fee_type FROM fees WHERE id=%s AND student_id=%s", (fee_id, student_id))
    fee = cur.fetchone()
    if not stu or not fee:
        conn.close()
        return {"success": False, "message": "Student or fee record not found."}
    receipt_no = f"RCP-{uuid.uuid4().hex[:8].upper()}"
    cur.execute("""
        INSERT INTO payments (student_id,fee_id,amount_paid,payment_method,receipt_no,processed_by)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (student_id, fee_id, amount_paid, payment_method, receipt_no, processed_by))
    # Update fee status
    total_paid_q = "SELECT COALESCE(SUM(amount_paid),0) AS total FROM payments WHERE fee_id=%s"
    cur.execute(total_paid_q, (fee_id,))
    total_paid = float(cur.fetchone()["total"])
    fee_amount = float(fee["amount"])
    new_status = "paid" if total_paid >= fee_amount else "partially_paid"
    cur.execute("UPDATE fees SET status=%s WHERE id=%s", (new_status, fee_id))
    conn.commit(); conn.close()
    email_result = send_payment_receipt(stu["email"], stu["name"], amount_paid, receipt_no, fee["fee_type"])
    return {"success": True, "receipt_no": receipt_no, "student_id": student_id,
            "amount_paid": amount_paid, "total_paid_on_fee": total_paid,
            "fee_status": new_status, "email_sent": email_result["success"],
            "message": f"Payment of ₹{amount_paid:,.0f} recorded. Receipt: {receipt_no}. Status: {new_status}."}


@mcp.tool()
def get_financial_statement(student_id: str) -> dict:
    """Full financial statement: charges, payments, outstanding balance."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, email FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    if not stu:
        conn.close()
        return {"found": False, "message": f"Student {student_id} not found."}
    cur.execute("""
        SELECT id, fee_type, amount, semester, due_date, status, description
        FROM fees WHERE student_id=%s ORDER BY due_date
    """, (student_id,))
    fees = [dict(r) for r in cur.fetchall()]
    cur.execute("""
        SELECT amount_paid, payment_date, payment_method, receipt_no
        FROM payments WHERE student_id=%s ORDER BY payment_date DESC
    """, (student_id,))
    payments = [dict(r) for r in cur.fetchall()]; conn.close()
    total_charged  = sum(float(f["amount"]) for f in fees)
    total_paid     = sum(float(p["amount_paid"]) for p in payments)
    outstanding    = total_charged - total_paid
    for f in fees:
        f["amount"] = float(f["amount"])
        f["due_date"] = str(f["due_date"])
    for p in payments:
        p["amount_paid"]   = float(p["amount_paid"])
        p["payment_date"]  = str(p["payment_date"])
    return {
        "student_id": student_id, "student_name": stu["name"],
        "total_charged": round(total_charged, 2),
        "total_paid":    round(total_paid, 2),
        "outstanding":   round(outstanding, 2),
        "fees":          fees,
        "payments":      payments,
    }


@mcp.tool()
def apply_scholarship(student_id: str, scholarship_id: int, applied_by: str = "") -> dict:
    """Award a scholarship; apply discount to tuition; send award email."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, email, gpa, total_credits FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    cur.execute("SELECT * FROM scholarships WHERE id=%s AND is_active=TRUE", (scholarship_id,))
    sch = cur.fetchone()
    if not stu or not sch:
        conn.close()
        return {"success": False, "message": "Student or scholarship not found."}
    # Check eligibility
    if float(stu["gpa"]) < float(sch["criteria_gpa"]):
        conn.close()
        return {"success": False, "message": f"GPA {stu['gpa']:.2f} below required {sch['criteria_gpa']:.2f}."}
    if stu["total_credits"] < sch["criteria_credits"]:
        conn.close()
        return {"success": False, "message": f"Only {stu['total_credits']} credits completed; need {sch['criteria_credits']}."}
    # Apply as negative fee (discount)
    cur.execute("""
        INSERT INTO fees (student_id,fee_type,amount,semester,due_date,status,description)
        VALUES (%s,'scholarship_discount',%s,'Spring','2026-12-31','waived',%s)
    """, (student_id, -float(sch["amount"]), f"Scholarship: {sch['name']}"))
    conn.commit(); conn.close()
    email_result = send_scholarship_award(stu["email"], stu["name"], sch["name"], float(sch["amount"]))
    return {"success": True, "student_id": student_id, "student_name": stu["name"],
            "scholarship": sch["name"], "amount": float(sch["amount"]),
            "email_sent": email_result["success"],
            "message": f"🏆 Scholarship '{sch['name']}' (₹{sch['amount']:,.0f}) awarded to {stu['name']}."}


@mcp.tool()
def get_scholarships(department: str = "", active_only: bool = True) -> list:
    """List all available scholarships with eligibility criteria."""
    conn = get_connection(); cur = _cur(conn)
    q = "SELECT * FROM scholarships WHERE 1=1"
    params = []
    if active_only:
        q += " AND is_active=TRUE"
    if department:
        q += " AND (department=%s OR department='All')"; params.append(department)
    cur.execute(q, params); rows = cur.fetchall(); conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["amount"] = float(d["amount"])
        d["criteria_gpa"] = float(d["criteria_gpa"])
        d["deadline"] = str(d["deadline"])
        result.append(d)
    return result if result else [{"message": "No active scholarships found."}]


@mcp.tool()
def check_scholarship_eligibility(student_id: str) -> list:
    """Check which scholarships a student qualifies for."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT gpa, total_credits, department FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    if not stu:
        conn.close()
        return [{"message": f"Student {student_id} not found."}]
    cur.execute("SELECT * FROM scholarships WHERE is_active=TRUE")
    scholarships = cur.fetchall(); conn.close()
    result = []
    for s in scholarships:
        eligible = (float(stu["gpa"]) >= float(s["criteria_gpa"]) and
                    stu["total_credits"] >= s["criteria_credits"] and
                    (s["department"] == "All" or s["department"] == stu["department"]))
        result.append({
            "scholarship_id": s["id"], "name": s["name"],
            "amount": float(s["amount"]), "eligible": eligible,
            "gpa_required": float(s["criteria_gpa"]), "student_gpa": float(stu["gpa"]),
            "credits_required": s["criteria_credits"], "student_credits": stu["total_credits"],
            "status": "✅ ELIGIBLE" if eligible else "❌ Not eligible",
        })
    return result


@mcp.tool()
def send_fee_reminder_tool(student_id: str) -> dict:
    """Send fee payment reminder for all unpaid/overdue fees."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("SELECT name, email FROM students WHERE student_id=%s", (student_id,))
    stu = cur.fetchone()
    cur.execute("SELECT fee_type, amount, due_date FROM fees WHERE student_id=%s AND status IN ('unpaid','overdue')",
                (student_id,))
    unpaid = cur.fetchall(); conn.close()
    if not stu:
        return {"success": False, "message": f"Student {student_id} not found."}
    if not unpaid:
        return {"success": True, "message": f"No outstanding fees for {stu['name']}."}
    results = []
    for f in unpaid:
        result = send_fee_reminder(stu["email"], stu["name"], f["fee_type"], float(f["amount"]), str(f["due_date"]))
        results.append({"fee_type": f["fee_type"], "amount": float(f["amount"]), "sent": result["success"]})
    return {"success": True, "student_id": student_id, "reminders_sent": len(results), "details": results}


@mcp.tool()
def get_financial_summary() -> dict:
    """Admin/registrar view: total fees collected, outstanding, scholarship disbursements."""
    conn = get_connection(); cur = _cur(conn)
    cur.execute("""
        SELECT
          SUM(CASE WHEN status='paid' THEN amount ELSE 0 END) AS collected,
          SUM(CASE WHEN status IN ('unpaid','overdue') THEN amount ELSE 0 END) AS outstanding,
          SUM(CASE WHEN status='partially_paid' THEN amount ELSE 0 END) AS partial,
          COUNT(*) AS total_fees
        FROM fees WHERE fee_type != 'scholarship_discount'
    """)
    summary = dict(cur.fetchone())
    cur.execute("SELECT SUM(ABS(amount)) AS disbursed FROM fees WHERE fee_type='scholarship_discount'")
    scholarships_disbursed = cur.fetchone()["disbursed"] or 0
    cur.execute("SELECT COUNT(*) AS overdue_count FROM fees WHERE status='overdue'")
    overdue_count = cur.fetchone()["overdue_count"]; conn.close()
    return {
        "total_fees_collected": float(summary["collected"] or 0),
        "total_outstanding": float(summary["outstanding"] or 0),
        "partially_paid": float(summary["partial"] or 0),
        "scholarships_disbursed": float(scholarships_disbursed),
        "overdue_accounts": int(overdue_count),
        "total_fee_records": int(summary["total_fees"]),
    }


def main():
    init_db()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()