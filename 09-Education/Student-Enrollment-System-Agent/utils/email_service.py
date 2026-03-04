"""utils/email_service.py — HTML email templates for Student Enrollment System."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()


def _send(to_emails: list[str] | str, subject: str, html: str) -> dict:
    sender   = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_APP_PASSWORD")
    if not sender or not password:
        return {"success": False, "message": "Email not configured in .env — skipping send."}
    if isinstance(to_emails, str):
        to_emails = [e.strip() for e in to_emails.split(",") if e.strip()]
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"EduManage AI <{sender}>"
        msg["To"]      = ", ".join(to_emails)
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(sender, password)
            s.sendmail(sender, to_emails, msg.as_string())
        return {"success": True, "message": f"Email sent to {', '.join(to_emails)}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def _wrap(content: str, badge: str, badge_color: str = "#1d4ed8") -> str:
    return f"""
<div style="font-family:Arial,sans-serif;background:#0f172a;padding:28px;max-width:640px;margin:auto;border-radius:12px">
  <div style="background:linear-gradient(135deg,#1a3c5e,#1d5fa6);padding:22px;border-radius:8px;text-align:center;margin-bottom:16px">
    <h2 style="color:#fff;margin:0;font-size:20px">🎓 EduManage AI — Student Enrollment System</h2>
    <span style="background:{badge_color};color:#fff;padding:4px 18px;border-radius:20px;font-size:12px;margin-top:8px;display:inline-block;font-weight:600">{badge}</span>
  </div>
  <div style="background:#1e293b;padding:22px;border-radius:8px;color:#e2e8f0;line-height:1.8">{content}</div>
  <p style="color:#475569;font-size:11px;text-align:center;margin-top:12px">EduManage AI — Automated University Notification. Contact admin@university.edu for queries.</p>
</div>"""


def _row(label: str, value: str, highlight: bool = False) -> str:
    color = "#fbbf24" if highlight else "#e2e8f0"
    return (f'<tr><td style="padding:8px 10px;color:#94a3b8;border-bottom:1px solid #334155;width:40%">{label}</td>'
            f'<td style="padding:8px 10px;color:{color};font-weight:{"700" if highlight else "400"};border-bottom:1px solid #334155">{value}</td></tr>')


def send_welcome_email(to_email: str, student_name: str, student_id: str, program: str) -> dict:
    content = f"""<p>Dear <b>{student_name}</b>,</p>
<p>Welcome to the university! Your student account has been created successfully.</p>
<table width="100%" style="border-collapse:collapse;margin:12px 0;background:#162032;border-radius:6px">
  {_row("Student ID", student_id, True)}
  {_row("Program", program)}
  {_row("Email", to_email)}
  {_row("Status", "Active")}
</table>
<p>Please log in to the student portal to complete your enrollment and view your timetable.</p>
<p style="color:#94a3b8;font-size:13px">If you have any questions, contact your academic advisor or the registrar's office.</p>"""
    return _send(to_email, f"🎓 Welcome to University — {student_name}", _wrap(content, "WELCOME", "#15803d"))


def send_enrollment_confirmation(to_email: str, student_name: str, course_name: str, course_code: str, action: str = "enrolled") -> dict:
    icon  = "✅" if action == "enrolled" else "❌"
    badge = "ENROLLED" if action == "enrolled" else "DROPPED"
    color = "#15803d" if action == "enrolled" else "#c2410c"
    content = f"""<p>Dear <b>{student_name}</b>,</p>
<p>Your course {action} request has been processed successfully.</p>
<table width="100%" style="border-collapse:collapse;margin:12px 0;background:#162032;border-radius:6px">
  {_row("Action", f"{icon} {action.upper()}")}
  {_row("Course Code", course_code, True)}
  {_row("Course Name", course_name)}
  {_row("Semester", "Spring 2026")}
</table>
<p style="color:#94a3b8;font-size:13px">View your full schedule in the student portal.</p>"""
    return _send(to_email, f"{icon} Course {action.title()} — {course_code}", _wrap(content, badge, color))


def send_grade_notification(to_email: str, student_name: str, course_name: str, grade: str, gpa: float) -> dict:
    content = f"""<p>Dear <b>{student_name}</b>,</p>
<p>Your grade for the following course has been submitted.</p>
<table width="100%" style="border-collapse:collapse;margin:12px 0;background:#162032;border-radius:6px">
  {_row("Course", course_name)}
  {_row("Grade", grade, True)}
  {_row("Updated GPA", f"{gpa:.2f}")}
  {_row("Semester", "Spring 2026")}
</table>
<p style="color:#94a3b8;font-size:13px">Contact your faculty or file a grade appeal if you have concerns.</p>"""
    return _send(to_email, f"📊 Grade Posted — {course_name}", _wrap(content, "GRADE POSTED", "#1d4ed8"))


def send_academic_warning(to_email: str, student_name: str, gpa: float, reason: str, advisor_email: str) -> dict:
    content = f"""<p>Dear <b>{student_name}</b>,</p>
<p>⚠️ This is an important academic notice from your institution.</p>
<table width="100%" style="border-collapse:collapse;margin:12px 0;background:#162032;border-radius:6px">
  {_row("Current GPA", f"{gpa:.2f}", True)}
  {_row("Reason", reason, True)}
  {_row("Required Action", "Contact your academic advisor immediately")}
  {_row("Advisor Email", advisor_email)}
</table>
<p>Please schedule an advising appointment as soon as possible. Failure to address academic standing may result in suspension.</p>"""
    return _send(to_email, "⚠️ Academic Warning Notice", _wrap(content, "ACADEMIC WARNING", "#c2410c"))


def send_advising_appointment(student_email: str, advisor_email: str, student_name: str, advisor_name: str, scheduled_at: str, notes: str) -> dict:
    content = f"""<p>Dear <b>{student_name}</b>,</p>
<p>Your advising appointment has been confirmed.</p>
<table width="100%" style="border-collapse:collapse;margin:12px 0;background:#162032;border-radius:6px">
  {_row("Advisor", advisor_name)}
  {_row("Date & Time", scheduled_at, True)}
  {_row("Notes", notes or "General advising session")}
</table>
<p style="color:#94a3b8;font-size:13px">Please arrive 5 minutes early. Contact {advisor_email} if you need to reschedule.</p>"""
    result1 = _send(student_email, "📅 Advising Appointment Confirmed", _wrap(content, "APPOINTMENT", "#0b7b6b"))
    # Also notify advisor
    adv_content = f"""<p>Dear <b>{advisor_name}</b>,</p>
<p>A new advising appointment has been booked by <b>{student_name}</b>.</p>
<table width="100%" style="border-collapse:collapse;margin:12px 0;background:#162032;border-radius:6px">
  {_row("Student", student_name)}
  {_row("Student Email", student_email)}
  {_row("Date & Time", scheduled_at, True)}
  {_row("Notes", notes or "General advising session")}
</table>"""
    _send(advisor_email, f"📅 New Advising Appointment — {student_name}", _wrap(adv_content, "NEW APPOINTMENT", "#0b7b6b"))
    return result1


def send_fee_reminder(to_email: str, student_name: str, fee_type: str, amount: float, due_date: str) -> dict:
    content = f"""<p>Dear <b>{student_name}</b>,</p>
<p>This is a reminder that you have an outstanding fee balance.</p>
<table width="100%" style="border-collapse:collapse;margin:12px 0;background:#162032;border-radius:6px">
  {_row("Fee Type", fee_type)}
  {_row("Amount Due", f"₹{amount:,.0f}", True)}
  {_row("Due Date", due_date, True)}
  {_row("Payment Status", "⚠️ UNPAID")}
</table>
<p>Please make payment through the student portal before the due date to avoid late fees.</p>"""
    return _send(to_email, f"💰 Fee Payment Reminder — ₹{amount:,.0f} Due", _wrap(content, "FEE REMINDER", "#b45309"))


def send_payment_receipt(to_email: str, student_name: str, amount: float, receipt_no: str, fee_type: str) -> dict:
    content = f"""<p>Dear <b>{student_name}</b>,</p>
<p>Your payment has been received and processed successfully.</p>
<table width="100%" style="border-collapse:collapse;margin:12px 0;background:#162032;border-radius:6px">
  {_row("Receipt Number", receipt_no, True)}
  {_row("Fee Type", fee_type)}
  {_row("Amount Paid", f"₹{amount:,.0f}", True)}
  {_row("Status", "✅ PAYMENT SUCCESSFUL")}
</table>
<p style="color:#94a3b8;font-size:13px">Please retain this receipt for your records.</p>"""
    return _send(to_email, f"✅ Payment Receipt — {receipt_no}", _wrap(content, "PAYMENT RECEIVED", "#15803d"))


def send_scholarship_award(to_email: str, student_name: str, scholarship_name: str, amount: float) -> dict:
    content = f"""<p>Dear <b>{student_name}</b>,</p>
<p>🎉 Congratulations! You have been awarded a scholarship.</p>
<table width="100%" style="border-collapse:collapse;margin:12px 0;background:#162032;border-radius:6px">
  {_row("Scholarship", scholarship_name, True)}
  {_row("Award Amount", f"₹{amount:,.0f}", True)}
  {_row("Applied To", "Current Semester Tuition")}
  {_row("Status", "✅ AWARDED")}
</table>
<p>This amount has been applied to your tuition account. Keep up the excellent work!</p>"""
    return _send(to_email, f"🏆 Scholarship Awarded — {scholarship_name}", _wrap(content, "SCHOLARSHIP AWARD", "#15803d"))


def send_schedule_update(to_email: str, student_name: str, course_name: str, change_details: str) -> dict:
    content = f"""<p>Dear <b>{student_name}</b>,</p>
<p>📅 Your class timetable has been updated.</p>
<table width="100%" style="border-collapse:collapse;margin:12px 0;background:#162032;border-radius:6px">
  {_row("Course", course_name)}
  {_row("Change", change_details, True)}
</table>
<p style="color:#94a3b8;font-size:13px">Please update your personal calendar. Contact the registrar for queries.</p>"""
    return _send(to_email, f"📅 Timetable Update — {course_name}", _wrap(content, "SCHEDULE UPDATE", "#1d4ed8"))


def send_course_status_notification(to_email: str, student_name: str, course_name: str, new_status: str, reason: str = "") -> dict:
    content = f"""<p>Dear <b>{student_name}</b>,</p>
<p>There has been an update to the status of a course you are associated with.</p>
<table width="100%" style="border-collapse:collapse;margin:12px 0;background:#162032;border-radius:6px">
  {_row("Course", course_name)}
  {_row("New Status", new_status.upper(), True)}
  {_row("Reason", reason or "Administrative update")}
</table>"""
    return _send(to_email, f"📢 Course Status Update — {course_name}", _wrap(content, "COURSE UPDATE", "#5b21b6"))