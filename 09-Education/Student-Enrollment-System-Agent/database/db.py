"""
database/db.py
══════════════
PostgreSQL schema + seed data for the Student Enrollment & Course Management System.

12 Tables:
  users                  – RBAC logins (5 roles: admin, registrar, faculty, advisor, student)
  students               – Full student profiles
  courses                – Course catalogue with capacity tracking
  enrollments            – Student-course registration records
  grades                 – All grade records with audit trail
  transcripts            – Cached official transcript records
  grade_appeals          – Grade appeal workflow
  advising_appointments  – Advisor meeting bookings
  fees                   – Tuition and fee charges
  payments               – Payment transaction ledger
  scholarships           – Available scholarship programmes
  timetable_slots        – Class schedule and room assignments
"""

import os
import hashlib
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

_SALT = "edu_salt_2026"


def _hash(pw: str) -> str:
    return hashlib.sha256((pw + _SALT).encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    return _hash(plain) == hashed


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "student_enrollment"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )


def _ensure_db():
    try:
        c = get_connection(); c.close()
    except psycopg2.OperationalError:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            dbname="postgres",
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
        )
        conn.autocommit = True
        conn.cursor().execute(f"CREATE DATABASE {os.getenv('DB_NAME','student_enrollment')}")
        conn.close()


def init_db():
    """Create all tables and seed data. Safe to call multiple times."""
    _ensure_db()
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id            SERIAL PRIMARY KEY,
        name          VARCHAR(120) NOT NULL,
        email         VARCHAR(120) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role          VARCHAR(20)  NOT NULL
                        CHECK (role IN ('admin','registrar','faculty','advisor','student')),
        student_id    VARCHAR(20),
        staff_id      VARCHAR(20),
        department    VARCHAR(80),
        is_active     BOOLEAN DEFAULT TRUE,
        created_at    TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS students (
        id            SERIAL PRIMARY KEY,
        student_id    VARCHAR(20) UNIQUE NOT NULL,
        name          VARCHAR(120) NOT NULL,
        email         VARCHAR(120) UNIQUE NOT NULL,
        phone         VARCHAR(20),
        dob           DATE,
        gender        VARCHAR(10),
        program       VARCHAR(80),
        department    VARCHAR(80),
        semester      INTEGER DEFAULT 1,
        enrolled_year INTEGER,
        status        VARCHAR(20) DEFAULT 'active'
                        CHECK (status IN ('active','suspended','graduated','withdrawn','deferred')),
        gpa           NUMERIC(3,2) DEFAULT 0.00,
        total_credits INTEGER DEFAULT 0,
        address       TEXT,
        guardian_name VARCHAR(120),
        guardian_email VARCHAR(120),
        created_at    TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS courses (
        id            SERIAL PRIMARY KEY,
        code          VARCHAR(20) UNIQUE NOT NULL,
        name          VARCHAR(150) NOT NULL,
        department    VARCHAR(80),
        credits       INTEGER DEFAULT 3,
        capacity      INTEGER DEFAULT 30,
        enrolled      INTEGER DEFAULT 0,
        semester      VARCHAR(20),
        academic_year INTEGER DEFAULT 2026,
        level         VARCHAR(20) DEFAULT 'undergraduate',
        prerequisites TEXT,
        instructor    VARCHAR(120),
        description   TEXT,
        status        VARCHAR(20) DEFAULT 'open'
                        CHECK (status IN ('open','closed','cancelled','completed')),
        created_at    TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS enrollments (
        id            SERIAL PRIMARY KEY,
        student_id    VARCHAR(20) NOT NULL,
        course_id     INTEGER REFERENCES courses(id),
        semester      VARCHAR(20),
        academic_year INTEGER DEFAULT 2026,
        status        VARCHAR(20) DEFAULT 'enrolled'
                        CHECK (status IN ('enrolled','dropped','waitlisted','completed')),
        enrolled_at   TIMESTAMP DEFAULT NOW(),
        dropped_at    TIMESTAMP,
        grade         VARCHAR(5)
    );

    CREATE TABLE IF NOT EXISTS grades (
        id            SERIAL PRIMARY KEY,
        student_id    VARCHAR(20) NOT NULL,
        course_id     INTEGER REFERENCES courses(id),
        semester      VARCHAR(20),
        academic_year INTEGER DEFAULT 2026,
        grade         VARCHAR(5),
        grade_points  NUMERIC(3,2),
        submitted_by  VARCHAR(120),
        submitted_at  TIMESTAMP DEFAULT NOW(),
        updated_at    TIMESTAMP,
        notes         TEXT
    );

    CREATE TABLE IF NOT EXISTS transcripts (
        id            SERIAL PRIMARY KEY,
        student_id    VARCHAR(20) NOT NULL,
        generated_at  TIMESTAMP DEFAULT NOW(),
        generated_by  VARCHAR(120),
        content_json  TEXT,
        is_official   BOOLEAN DEFAULT FALSE
    );

    CREATE TABLE IF NOT EXISTS grade_appeals (
        id             SERIAL PRIMARY KEY,
        student_id     VARCHAR(20) NOT NULL,
        course_id      INTEGER REFERENCES courses(id),
        original_grade VARCHAR(5),
        appeal_reason  TEXT,
        status         VARCHAR(20) DEFAULT 'pending'
                          CHECK (status IN ('pending','under_review','approved','rejected')),
        reviewed_by    VARCHAR(120),
        resolution     TEXT,
        created_at     TIMESTAMP DEFAULT NOW(),
        resolved_at    TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS advising_appointments (
        id            SERIAL PRIMARY KEY,
        student_id    VARCHAR(20) NOT NULL,
        advisor_email VARCHAR(120),
        advisor_name  VARCHAR(120),
        scheduled_at  TIMESTAMP,
        duration_mins INTEGER DEFAULT 30,
        notes         TEXT,
        status        VARCHAR(20) DEFAULT 'scheduled'
                        CHECK (status IN ('scheduled','completed','cancelled','no_show')),
        meeting_type  VARCHAR(20) DEFAULT 'in_person',
        created_at    TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS fees (
        id            SERIAL PRIMARY KEY,
        student_id    VARCHAR(20) NOT NULL,
        fee_type      VARCHAR(60),
        amount        NUMERIC(10,2) NOT NULL,
        semester      VARCHAR(20),
        academic_year INTEGER DEFAULT 2026,
        due_date      DATE,
        status        VARCHAR(20) DEFAULT 'unpaid'
                        CHECK (status IN ('unpaid','paid','partially_paid','waived','overdue')),
        description   TEXT,
        created_at    TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS payments (
        id            SERIAL PRIMARY KEY,
        student_id    VARCHAR(20) NOT NULL,
        fee_id        INTEGER REFERENCES fees(id),
        amount_paid   NUMERIC(10,2),
        payment_date  DATE DEFAULT CURRENT_DATE,
        payment_method VARCHAR(40),
        receipt_no    VARCHAR(40),
        processed_by  VARCHAR(120),
        created_at    TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS scholarships (
        id              SERIAL PRIMARY KEY,
        name            VARCHAR(120) NOT NULL,
        description     TEXT,
        amount          NUMERIC(10,2),
        criteria_gpa    NUMERIC(3,2) DEFAULT 0.00,
        criteria_credits INTEGER DEFAULT 0,
        deadline        DATE,
        is_active       BOOLEAN DEFAULT TRUE,
        department      VARCHAR(80),
        created_at      TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS timetable_slots (
        id            SERIAL PRIMARY KEY,
        course_id     INTEGER REFERENCES courses(id),
        faculty_email VARCHAR(120),
        faculty_name  VARCHAR(120),
        room          VARCHAR(40),
        day_of_week   VARCHAR(15),
        start_time    TIME,
        end_time      TIME,
        semester      VARCHAR(20),
        academic_year INTEGER DEFAULT 2026,
        slot_type     VARCHAR(20) DEFAULT 'lecture',
        created_at    TIMESTAMP DEFAULT NOW()
    );
    """)
    conn.commit()

    # ── Seed only once ──────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    # ── Users (5 roles) ─────────────────────────────────────────────────────
    cur.execute("""
    INSERT INTO users (name, email, password_hash, role, department, student_id, staff_id) VALUES
      ('System Admin',       'admin@university.edu',      %s, 'admin',      'Administration',         NULL,         'ADM-001'),
      ('Priya Registrar',    'registrar@university.edu',  %s, 'registrar',  'Registrar Office',       NULL,         'REG-001'),
      ('Dr. Arjun Mehta',    'faculty@university.edu',    %s, 'faculty',    'Computer Science',       NULL,         'FAC-001'),
      ('Dr. Sunita Advisor', 'advisor@university.edu',    %s, 'advisor',    'Academic Affairs',       NULL,         'ADV-001'),
      ('Rohit Student',      'student@university.edu',    %s, 'student',    'Computer Science', 'STU-2026-001',     NULL)
    """, (_hash("admin123"), _hash("reg123"), _hash("fac123"), _hash("adv123"), _hash("stu123")))

    # ── Students (8 demo students) ───────────────────────────────────────────
    cur.execute("""
    INSERT INTO students
      (student_id,name,email,phone,dob,gender,program,department,semester,enrolled_year,status,gpa,total_credits)
    VALUES
      ('STU-2026-001','Rohit Sharma','rohit@university.edu','9876543210','2003-05-15','Male','B.Tech Computer Science','Computer Science',3,2024,'active',3.45,45),
      ('STU-2026-002','Priya Patel','priya@university.edu','9876543211','2003-08-22','Female','B.Tech Computer Science','Computer Science',3,2024,'active',3.80,48),
      ('STU-2026-003','Ankit Verma','ankit@university.edu','9876543212','2002-12-10','Male','M.Tech Data Science','Computer Science',2,2025,'active',3.20,18),
      ('STU-2026-004','Sneha Iyer','sneha@university.edu','9876543213','2003-03-28','Female','B.Tech Electronics','Electronics',3,2024,'active',2.90,42),
      ('STU-2026-005','Karan Joshi','karan@university.edu','9876543214','2003-07-01','Male','B.Tech Computer Science','Computer Science',2,2024,'suspended',1.85,24),
      ('STU-2026-006','Meera Nair','meera@university.edu','9876543215','2002-11-15','Female','MBA Business Analytics','Management',2,2025,'active',3.65,22),
      ('STU-2026-007','Vijay Kumar','vijay@university.edu','9876543216','2001-09-20','Male','B.Tech Mechanical','Mechanical',6,2022,'active',2.50,96),
      ('STU-2026-008','Aisha Khan','aisha@university.edu','9876543217','2003-01-12','Female','B.Tech Computer Science','Computer Science',1,2026,'active',0.00,0)
    """)

    # ── Courses ──────────────────────────────────────────────────────────────
    cur.execute("""
    INSERT INTO courses
      (code,name,department,credits,capacity,enrolled,semester,level,prerequisites,instructor,description,status)
    VALUES
      ('CS101','Introduction to Programming','Computer Science',4,40,38,'Spring','undergraduate','None','Dr. Arjun Mehta','Fundamentals of programming using Python','open'),
      ('CS201','Data Structures & Algorithms','Computer Science',4,35,32,'Spring','undergraduate','CS101','Dr. Arjun Mehta','Trees, graphs, sorting, searching algorithms','open'),
      ('CS301','Advanced Algorithms','Computer Science',3,30,28,'Spring','undergraduate','CS201','Dr. Arjun Mehta','Advanced algorithm design and complexity analysis','open'),
      ('CS401','Machine Learning','Computer Science',3,25,20,'Spring','postgraduate','CS201,MATH201','Dr. Priya Singh','Supervised, unsupervised, reinforcement learning','open'),
      ('MATH101','Calculus I','Mathematics',4,50,45,'Spring','undergraduate','None','Dr. Ramesh Kumar','Limits, derivatives, integrals','open'),
      ('MATH201','Linear Algebra','Mathematics',3,40,38,'Spring','undergraduate','MATH101','Dr. Ramesh Kumar','Vectors, matrices, eigenvalues','open'),
      ('PHY101','Engineering Physics','Physics',3,40,36,'Spring','undergraduate','None','Dr. Sunita Rao','Mechanics, optics, electromagnetism','open'),
      ('CS501','Cloud Computing','Computer Science',3,20,15,'Spring','postgraduate','CS301','Dr. Arjun Mehta','AWS, GCP, containerisation, microservices','open'),
      ('MBA101','Management Principles','Management',3,45,40,'Spring','postgraduate','None','Dr. Meena Shah','Strategic management, organisational behaviour','open'),
      ('EC101','Basic Electronics','Electronics',4,40,35,'Spring','undergraduate','None','Dr. Vijay Rao','Circuits, diodes, transistors, op-amps','open')
    """)

    # ── Enrollments ──────────────────────────────────────────────────────────
    cur.execute("""
    INSERT INTO enrollments (student_id,course_id,semester,status) VALUES
      ('STU-2026-001',1,'Spring','enrolled'),('STU-2026-001',2,'Spring','enrolled'),
      ('STU-2026-001',5,'Spring','enrolled'),('STU-2026-002',1,'Spring','enrolled'),
      ('STU-2026-002',2,'Spring','enrolled'),('STU-2026-002',3,'Spring','enrolled'),
      ('STU-2026-003',4,'Spring','enrolled'),('STU-2026-003',8,'Spring','enrolled'),
      ('STU-2026-004',5,'Spring','enrolled'),('STU-2026-004',7,'Spring','enrolled'),
      ('STU-2026-004',10,'Spring','enrolled'),('STU-2026-005',1,'Spring','enrolled'),
      ('STU-2026-006',9,'Spring','enrolled'),('STU-2026-007',3,'Spring','enrolled')
    """)

    # ── Grades ───────────────────────────────────────────────────────────────
    cur.execute("""
    INSERT INTO grades (student_id,course_id,semester,grade,grade_points,submitted_by) VALUES
      ('STU-2026-001',1,'Spring',NULL,NULL,'faculty@university.edu'),
      ('STU-2026-002',1,'Spring','A',4.00,'faculty@university.edu'),
      ('STU-2026-002',2,'Spring','A-',3.70,'faculty@university.edu'),
      ('STU-2026-004',5,'Spring','B+',3.30,'Dr. Ramesh Kumar'),
      ('STU-2026-005',1,'Spring','D',1.00,'faculty@university.edu'),
      ('STU-2026-007',3,'Spring','B',3.00,'faculty@university.edu')
    """)

    # ── Fees ─────────────────────────────────────────────────────────────────
    cur.execute("""
    INSERT INTO fees (student_id,fee_type,amount,semester,due_date,status,description) VALUES
      ('STU-2026-001','tuition',85000,'Spring','2026-03-15','unpaid','Spring 2026 Tuition Fee'),
      ('STU-2026-001','hostel',25000,'Spring','2026-03-15','paid','Spring 2026 Hostel Fee'),
      ('STU-2026-002','tuition',85000,'Spring','2026-03-15','paid','Spring 2026 Tuition Fee'),
      ('STU-2026-003','tuition',95000,'Spring','2026-03-15','unpaid','Spring 2026 PG Tuition Fee'),
      ('STU-2026-004','tuition',85000,'Spring','2026-03-15','partially_paid','Spring 2026 Tuition Fee'),
      ('STU-2026-005','tuition',85000,'Spring','2026-03-01','overdue','Spring 2026 Tuition Fee'),
      ('STU-2026-006','tuition',95000,'Spring','2026-03-15','unpaid','Spring 2026 MBA Tuition Fee'),
      ('STU-2026-007','tuition',85000,'Spring','2026-03-15','paid','Spring 2026 Tuition Fee')
    """)

    # ── Payments ─────────────────────────────────────────────────────────────
    cur.execute("""
    INSERT INTO payments (student_id,fee_id,amount_paid,payment_method,receipt_no,processed_by) VALUES
      ('STU-2026-001',2,25000,'UPI','RCP-2026-0001','registrar@university.edu'),
      ('STU-2026-002',3,85000,'Bank Transfer','RCP-2026-0002','registrar@university.edu'),
      ('STU-2026-004',5,42500,'UPI','RCP-2026-0003','registrar@university.edu'),
      ('STU-2026-007',8,85000,'Cash','RCP-2026-0004','registrar@university.edu')
    """)

    # ── Scholarships ─────────────────────────────────────────────────────────
    cur.execute("""
    INSERT INTO scholarships (name,description,amount,criteria_gpa,criteria_credits,deadline,department) VALUES
      ('Merit Excellence Award','Top performing students with GPA above 3.7',50000,3.70,30,'2026-04-30','All'),
      ('CS Innovation Scholarship','Computer Science students with outstanding projects',35000,3.50,24,'2026-03-31','Computer Science'),
      ('Need-Based Support Grant','Financial assistance for deserving students',25000,2.50,0,'2026-03-31','All'),
      ('Research Excellence Award','Students engaged in active research',40000,3.60,20,'2026-05-15','All')
    """)

    # ── Timetable Slots ──────────────────────────────────────────────────────
    cur.execute("""
    INSERT INTO timetable_slots
      (course_id,faculty_email,faculty_name,room,day_of_week,start_time,end_time,semester,slot_type)
    VALUES
      (1,'faculty@university.edu','Dr. Arjun Mehta','Room 101','Monday','09:00','11:00','Spring','lecture'),
      (1,'faculty@university.edu','Dr. Arjun Mehta','Lab A','Wednesday','14:00','16:00','Spring','lab'),
      (2,'faculty@university.edu','Dr. Arjun Mehta','Room 102','Tuesday','09:00','11:00','Spring','lecture'),
      (2,'faculty@university.edu','Dr. Arjun Mehta','Room 102','Thursday','11:00','12:00','Spring','tutorial'),
      (3,'faculty@university.edu','Dr. Arjun Mehta','Room 201','Monday','14:00','16:00','Spring','lecture'),
      (4,'faculty@university.edu','Dr. Arjun Mehta','PG Room 1','Wednesday','09:00','11:00','Spring','lecture'),
      (5,'dr.ramesh@university.edu','Dr. Ramesh Kumar','Room 103','Tuesday','11:00','13:00','Spring','lecture'),
      (6,'dr.ramesh@university.edu','Dr. Ramesh Kumar','Room 103','Friday','09:00','11:00','Spring','lecture'),
      (9,'dr.meena@university.edu','Dr. Meena Shah','MBA Hall','Monday','11:00','13:00','Spring','lecture'),
      (10,'dr.vijay@university.edu','Dr. Vijay Rao','EC Lab','Thursday','14:00','17:00','Spring','lab')
    """)

    # ── Advising Appointments ────────────────────────────────────────────────
    cur.execute("""
    INSERT INTO advising_appointments
      (student_id,advisor_email,advisor_name,scheduled_at,notes,status,meeting_type)
    VALUES
      ('STU-2026-005','advisor@university.edu','Dr. Sunita Advisor','2026-03-05 10:00:00',
       'Academic intervention — GPA below 2.0','scheduled','in_person'),
      ('STU-2026-004','advisor@university.edu','Dr. Sunita Advisor','2026-03-07 11:00:00',
       'Course selection for next semester','scheduled','online')
    """)

    conn.commit()
    conn.close()
    print("✅  Student Enrollment DB initialised with seed data.")