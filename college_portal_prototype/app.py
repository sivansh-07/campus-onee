from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, math, os
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "college_portal.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "prototype-secret-change-me"

CAMPUS_LAT = 26.8467
CAMPUS_LON = 80.9462
GEOFENCE_RADIUS = 1000  # Prototype: 1 km around demo campus center


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        department_id INTEGER,
        verified INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        code TEXT NOT NULL,
        semester TEXT,
        department_id INTEGER,
        syllabus TEXT
    );

    CREATE TABLE IF NOT EXISTS enrollments (
        user_id INTEGER,
        course_id INTEGER,
        PRIMARY KEY(user_id, course_id)
    );

    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        teacher_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        due_date TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        filename TEXT,
        submitted_at TEXT NOT NULL,
        grade TEXT,
        feedback TEXT
    );

    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        attendance_date TEXT NOT NULL,
        status TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        UNIQUE(student_id, course_id, attendance_date)
    );

    CREATE TABLE IF NOT EXISTS vivas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        teacher_id INTEGER NOT NULL,
        scheduled_at TEXT NOT NULL,
        status TEXT DEFAULT 'Scheduled'
    );

    CREATE TABLE IF NOT EXISTS leaves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        from_date TEXT NOT NULL,
        to_date TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'Pending'
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS labs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        building TEXT,
        room TEXT,
        equipment TEXT,
        department_id INTEGER
    );
    """)
    conn.commit()

    # Seed data only when empty.
    if conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO departments(name, code) VALUES (?, ?)",
            [("Information Technology", "IT"), ("Computer Science", "CSE"), ("Electronics", "ECE")]
        )

    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        it_id = conn.execute("SELECT id FROM departments WHERE code='IT'").fetchone()["id"]
        cse_id = conn.execute("SELECT id FROM departments WHERE code='CSE'").fetchone()["id"]
        users = [
            ("Student Demo", "student@college.test", "student123", "student", it_id, 1),
            ("Teacher Demo", "teacher@college.test", "teacher123", "teacher", it_id, 1),
            ("Admin Demo", "admin@college.test", "admin123", "admin", None, 1),
            ("Placement Officer", "placement@college.test", "placement123", "placement", None, 1),
            ("Pending Teacher", "pending@college.test", "teacher123", "teacher", cse_id, 0),
        ]
        for name, email, pwd, role, dept, verified in users:
            conn.execute(
                "INSERT INTO users(name,email,password,role,department_id,verified) VALUES(?,?,?,?,?,?)",
                (name, email, generate_password_hash(pwd), role, dept, verified)
            )

    if conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
        it_id = conn.execute("SELECT id FROM departments WHERE code='IT'").fetchone()["id"]
        cse_id = conn.execute("SELECT id FROM departments WHERE code='CSE'").fetchone()["id"]
        courses = [
            ("Data Structures & Algorithms", "IT301", "5", it_id, "Syllabus: Algorithms, sorting, searching, graphs, dynamic programming."),
            ("Database Management Systems", "IT302", "5", it_id, "Syllabus: SQL, normalization, transactions, indexing."),
            ("Web Technology", "IT303", "5", it_id, "Syllabus: HTML, CSS, JavaScript, Flask/REST APIs."),
            ("Operating Systems", "CSE301", "5", cse_id, "Syllabus: Processes, threads, memory, filesystems."),
        ]
        conn.executemany(
            "INSERT INTO courses(title,code,semester,department_id,syllabus) VALUES(?,?,?,?,?)",
            courses
        )

    if conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0] == 0:
        student_id = conn.execute("SELECT id FROM users WHERE email='student@college.test'").fetchone()["id"]
        course_ids = [r["id"] for r in conn.execute("SELECT id FROM courses WHERE code LIKE 'IT%'").fetchall()]
        conn.executemany("INSERT INTO enrollments(user_id,course_id) VALUES(?,?)",
                         [(student_id, cid) for cid in course_ids])

    if conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0] == 0:
        teacher_id = conn.execute("SELECT id FROM users WHERE email='teacher@college.test'").fetchone()["id"]
        course_id = conn.execute("SELECT id FROM courses WHERE code='IT301'").fetchone()["id"]
        conn.execute(
            "INSERT INTO assignments(course_id,teacher_id,title,description,due_date) VALUES(?,?,?,?,?)",
            (course_id, teacher_id, "Sorting Algorithms Assignment",
             "Implement and compare merge sort, quick sort and counting sort.",
             "2026-09-15")
        )

    if conn.execute("SELECT COUNT(*) FROM labs").fetchone()[0] == 0:
        it_id = conn.execute("SELECT id FROM departments WHERE code='IT'").fetchone()["id"]
        conn.executemany(
            "INSERT INTO labs(name,building,room,equipment,department_id) VALUES(?,?,?,?,?)",
            [
                ("Programming Lab", "IT Block", "Lab 201", "50 PCs, LAN, Projector", it_id),
                ("Database Lab", "IT Block", "Lab 202", "SQL Servers, PCs", it_id),
            ]
        )
    conn.commit()
    conn.close()


def login_required():
    return "user_id" in session


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


@app.context_processor
def inject_user():
    if "user_id" not in session:
        return {"current_user": None}
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return {"current_user": user}


@app.route("/")
def index():
    if login_required():
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"].strip().lower()
    password = request.form["password"]
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    if user and check_password_hash(user["password"], password):
        if user["role"] == "teacher" and not user["verified"]:
            flash("Teacher account is waiting for admin verification.", "warning")
            return redirect(url_for("index"))
        session["user_id"] = user["id"]
        return redirect(url_for("dashboard"))
    flash("Invalid email or password.", "danger")
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect(url_for("index"))
    conn = db()
    role = session.get("role")
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not role:
        role = user["role"]
        session["role"] = role

    stats = {}
    if role == "student":
        courses = conn.execute("""
            SELECT c.* FROM courses c JOIN enrollments e ON c.id=e.course_id
            WHERE e.user_id=?
        """, (user["id"],)).fetchall()
        assignments = conn.execute("""
            SELECT a.*, c.code FROM assignments a JOIN courses c ON c.id=a.course_id
            JOIN enrollments e ON e.course_id=c.id
            WHERE e.user_id=? ORDER BY a.due_date
        """, (user["id"],)).fetchall()
        att = conn.execute("""
            SELECT COUNT(*) total,
                   SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) present
            FROM attendance WHERE student_id=?
        """, (user["id"],)).fetchone()
        stats["courses"] = len(courses)
        stats["assignments"] = len(assignments)
        stats["attendance"] = round((att["present"] or 0) * 100 / att["total"], 1) if att["total"] else 0
    elif role == "teacher":
        stats["courses"] = conn.execute(
            "SELECT COUNT(*) n FROM courses WHERE department_id=?", (user["department_id"],)
        ).fetchone()["n"]
        stats["assignments"] = conn.execute(
            "SELECT COUNT(*) n FROM assignments WHERE teacher_id=?", (user["id"],)
        ).fetchone()["n"]
        stats["pending_submissions"] = conn.execute("""
            SELECT COUNT(*) n FROM submissions s
            JOIN assignments a ON a.id=s.assignment_id
            WHERE a.teacher_id=? AND (s.grade IS NULL OR s.grade='')
        """, (user["id"],)).fetchone()["n"]
    elif role == "admin":
        stats["students"] = conn.execute("SELECT COUNT(*) n FROM users WHERE role='student'").fetchone()["n"]
        stats["teachers"] = conn.execute("SELECT COUNT(*) n FROM users WHERE role='teacher'").fetchone()["n"]
        stats["pending_teachers"] = conn.execute(
            "SELECT COUNT(*) n FROM users WHERE role='teacher' AND verified=0"
        ).fetchone()["n"]
        stats["courses"] = conn.execute("SELECT COUNT(*) n FROM courses").fetchone()["n"]
    else:
        stats["students"] = conn.execute("SELECT COUNT(*) n FROM users WHERE role='student'").fetchone()["n"]
        stats["drives"] = 3
    conn.close()
    return render_template("dashboard.html", stats=stats)


@app.route("/courses")
def courses():
    if not login_required():
        return redirect(url_for("index"))
    conn = db()
    rows = conn.execute("""
        SELECT c.*, d.name department FROM courses c
        LEFT JOIN departments d ON d.id=c.department_id ORDER BY d.name, c.code
    """).fetchall()
    conn.close()
    return render_template("courses.html", courses=rows)


@app.route("/assignments")
def assignments():
    if not login_required():
        return redirect(url_for("index"))
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if user["role"] == "student":
        rows = conn.execute("""
            SELECT a.*, c.code, c.title course_title,
                   s.id submission_id, s.grade, s.feedback, s.submitted_at
            FROM assignments a JOIN courses c ON c.id=a.course_id
            JOIN enrollments e ON e.course_id=c.id
            LEFT JOIN submissions s ON s.assignment_id=a.id AND s.student_id=?
            WHERE e.user_id=? ORDER BY a.due_date
        """, (user["id"], user["id"])).fetchall()
    else:
        rows = conn.execute("""
            SELECT a.*, c.code, c.title course_title,
                   COUNT(s.id) submissions
            FROM assignments a JOIN courses c ON c.id=a.course_id
            LEFT JOIN submissions s ON s.assignment_id=a.id
            WHERE a.teacher_id=? GROUP BY a.id ORDER BY a.due_date
        """, (user["id"],)).fetchall()
    conn.close()
    return render_template("assignments.html", assignments=rows, user=user)


@app.route("/assignments/<int:assignment_id>/submit", methods=["POST"])
def submit_assignment(assignment_id):
    if not login_required():
        return redirect(url_for("index"))
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Please select a file.", "warning")
        return redirect(url_for("assignments"))
    conn = db()
    assignment = conn.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
    if not assignment:
        conn.close()
        flash("Assignment not found.", "danger")
        return redirect(url_for("assignments"))
    if datetime.now().date() > datetime.strptime(assignment["due_date"], "%Y-%m-%d").date():
        conn.close()
        flash("Deadline passed.", "danger")
        return redirect(url_for("assignments"))
    safe = os.path.basename(file.filename)
    save_dir = os.path.join(UPLOAD_DIR, str(assignment_id), str(session["user_id"]))
    os.makedirs(save_dir, exist_ok=True)
    file.save(os.path.join(save_dir, safe))
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("""
        INSERT INTO submissions(assignment_id,student_id,filename,submitted_at)
        VALUES(?,?,?,?)
    """, (assignment_id, session["user_id"], safe, now))
    teacher = conn.execute("SELECT teacher_id FROM assignments WHERE id=?", (assignment_id,)).fetchone()
    conn.execute("INSERT INTO notifications(user_id,message,created_at) VALUES(?,?,?)",
                 (teacher["teacher_id"], f"New submission received: {safe}", now))
    conn.commit()
    conn.close()
    flash("Assignment submitted successfully.", "success")
    return redirect(url_for("assignments"))


@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if not login_required():
        return redirect(url_for("index"))
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    courses = conn.execute("""
        SELECT c.* FROM courses c JOIN enrollments e ON e.course_id=c.id
        WHERE e.user_id=?
    """, (user["id"],)).fetchall()
    records = conn.execute("""
        SELECT a.*, c.code FROM attendance a JOIN courses c ON c.id=a.course_id
        WHERE a.student_id=? ORDER BY a.attendance_date DESC
    """, (user["id"],)).fetchall()
    conn.close()
    return render_template("attendance.html", courses=courses, records=records)


@app.route("/api/attendance/checkin", methods=["POST"])
def api_checkin():
    if not login_required():
        return jsonify(success=False, message="Login required"), 401
    data = request.get_json(silent=True) or {}
    try:
        lat = float(data["latitude"])
        lon = float(data["longitude"])
        course_id = int(data["courseId"])
    except (KeyError, ValueError, TypeError):
        return jsonify(success=False, message="Latitude, longitude and course are required."), 400

    distance = haversine(lat, lon, CAMPUS_LAT, CAMPUS_LON)
    if distance > GEOFENCE_RADIUS:
        return jsonify(success=False, message=f"Outside campus geofence ({distance:.0f} m away)."), 403

    conn = db()
    today = date.today().isoformat()
    try:
        conn.execute("""
            INSERT INTO attendance(student_id,course_id,attendance_date,status,latitude,longitude)
            VALUES(?,?,?,?,?,?)
        """, (session["user_id"], course_id, today, "Present", lat, lon))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify(success=False, message="Attendance already marked today."), 409
    conn.close()
    return jsonify(success=True, message=f"Attendance recorded. Distance: {distance:.0f} m")


@app.route("/leave", methods=["GET", "POST"])
def leave():
    if not login_required():
        return redirect(url_for("index"))
    conn = db()
    if request.method == "POST":
        conn.execute("""
            INSERT INTO leaves(user_id,from_date,to_date,reason)
            VALUES(?,?,?,?)
        """, (session["user_id"], request.form["from_date"], request.form["to_date"], request.form["reason"]))
        conn.commit()
        flash("Leave request submitted.", "success")
    rows = conn.execute("SELECT * FROM leaves WHERE user_id=? ORDER BY id DESC",
                        (session["user_id"],)).fetchall()
    conn.close()
    return render_template("leave.html", leaves=rows)

git init
@app.route("/vivas")
def vivas():
    if not login_required():
        return redirect(url_for("index"))
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if user["role"] == "student":
        rows = conn.execute("""
            SELECT v.*, c.code, c.title, u.name teacher
            FROM vivas v JOIN courses c ON c.id=v.course_id JOIN users u ON u.id=v.teacher_id
            WHERE v.student_id=? ORDER BY v.scheduled_at
        """, (user["id"],)).fetchall()
    else:
        rows = conn.execute("""
            SELECT v.*, c.code, c.title, u.name student
            FROM vivas v JOIN courses c ON c.id=v.course_id JOIN users u ON u.id=v.student_id
            WHERE v.teacher_id=? ORDER BY v.scheduled_at
        """, (user["id"],)).fetchall()
    conn.close()
    return render_template("vivas.html", vivas=rows, user=user)


@app.route("/labs")
def labs():
    if not login_required():
        return redirect(url_for("index"))
    conn = db()
    rows = conn.execute("""
        SELECT l.*, d.name department FROM labs l
        LEFT JOIN departments d ON d.id=l.department_id
    """).fetchall()
    conn.close()
    return render_template("labs.html", labs=rows)


@app.route("/admin/teachers", methods=["GET", "POST"])
def admin_teachers():
    if not login_required():
        return redirect(url_for("index"))
    conn = db()
    me = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if me["role"] != "admin":
        conn.close()
        return "Forbidden", 403
    if request.method == "POST":
        teacher_id = int(request.form["teacher_id"])
        approved = 1 if request.form["action"] == "approve" else 0
        conn.execute("UPDATE users SET verified=? WHERE id=? AND role='teacher'", (approved, teacher_id))
        conn.execute("INSERT INTO notifications(user_id,message,created_at) VALUES(?,?,?)",
                     (teacher_id, f"Teacher account {'verified' if approved else 'rejected'} by admin.",
                      datetime.now().isoformat(timespec="seconds")))
        conn.commit()
    teachers = conn.execute("""
        SELECT u.*, d.name department FROM users u
        LEFT JOIN departments d ON d.id=u.department_id
        WHERE u.role='teacher'
    """).fetchall()
    conn.close()
    return render_template("teachers.html", teachers=teachers)


@app.route("/notifications")
def notifications():
    if not login_required():
        return redirect(url_for("index"))
    conn = db()
    rows = conn.execute("""
        SELECT * FROM notifications
        WHERE user_id IS NULL OR user_id=?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("notifications.html", notifications=rows)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
