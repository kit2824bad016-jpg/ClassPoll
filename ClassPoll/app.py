
import csv
import io
import os
import secrets
import string
from datetime import datetime
from functools import wraps
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from flask import (
    Flask, abort, flash, make_response, redirect, render_template,
    request, session, url_for
)
from mysql.connector import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash


# Load .env from the same folder as app.py
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY", "dev-only-change-me"
)


def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "classpoll_user"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "classpoll"),
        charset="utf8mb4",
        use_unicode=True,
    )


def query_db(sql, params=(), one=False):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchone() if one else cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def execute_db(sql, params=()):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))
            if session.get("role") != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def make_class_code():
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def get_class_for_teacher(class_id):
    return query_db(
        "SELECT * FROM classes WHERE id=%s AND teacher_id=%s",
        (class_id, session["user_id"]),
        one=True,
    )


def get_student_class_membership(class_id):
    return query_db(
        """SELECT c.* FROM classes c
           JOIN class_members cm ON cm.class_id=c.id
           WHERE c.id=%s AND cm.student_id=%s""",
        (class_id, session["user_id"]),
        one=True,
    )


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        if (
            not name
            or not email
            or len(password) < 8
            or role not in ("teacher", "student")
        ):
            flash(
                "Enter all details. Password must be at least 8 characters.",
                "danger",
            )
            return render_template("register.html")

        try:
            execute_db(
                """INSERT INTO users
                   (name, email, password_hash, role)
                   VALUES (%s, %s, %s, %s)""",
                (
                    name,
                    email,
                    generate_password_hash(password),
                    role,
                ),
            )
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except IntegrityError:
            flash("That email is already registered.", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = query_db(
            "SELECT * FROM users WHERE email=%s",
            (email,),
            one=True,
        )

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))

        flash("Email or password is incorrect.", "danger")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have logged out.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    if session["role"] == "teacher":
        classes = query_db(
            """SELECT c.*,
               (SELECT COUNT(*) FROM class_members cm
                WHERE cm.class_id=c.id) AS student_count,
               (SELECT COUNT(*) FROM polls p
                WHERE p.class_id=c.id) AS poll_count
               FROM classes c
               WHERE c.teacher_id=%s
               ORDER BY c.created_at DESC""",
            (session["user_id"],),
        )
        return render_template(
            "teacher_dashboard.html",
            classes=classes,
        )

    classes = query_db(
        """SELECT c.*, u.name AS teacher_name,
           (SELECT COUNT(*) FROM polls p
            WHERE p.class_id=c.id) AS poll_count
           FROM classes c
           JOIN class_members cm ON cm.class_id=c.id
           JOIN users u ON u.id=c.teacher_id
           WHERE cm.student_id=%s
           ORDER BY cm.joined_at DESC""",
        (session["user_id"],),
    )

    polls = query_db(
        """SELECT p.*, c.name AS class_name,
           EXISTS(
               SELECT 1 FROM votes v
               WHERE v.poll_id=p.id AND v.student_id=%s
           ) AS has_voted
           FROM polls p
           JOIN classes c ON c.id=p.class_id
           JOIN class_members cm ON cm.class_id=c.id
           WHERE cm.student_id=%s
           ORDER BY p.created_at DESC""",
        (session["user_id"], session["user_id"]),
    )

    return render_template(
        "student_dashboard.html",
        classes=classes,
        polls=polls,
    )


@app.route("/classes/create", methods=["POST"])
@login_required
@role_required("teacher")
def create_class():
    name = request.form.get("name", "").strip()

    if not name:
        flash("Enter a class name.", "danger")
        return redirect(url_for("dashboard"))

    for _ in range(5):
        code = make_class_code()
        try:
            execute_db(
                """INSERT INTO classes
                   (teacher_id, name, class_code)
                   VALUES (%s, %s, %s)""",
                (session["user_id"], name, code),
            )
            flash(
                f"Class created. Share this join code: {code}",
                "success",
            )
            break
        except IntegrityError:
            continue
    else:
        flash("Could not create a class. Please try again.", "danger")

    return redirect(url_for("dashboard"))


@app.route("/classes/join", methods=["POST"])
@login_required
@role_required("student")
def join_class():
    code = request.form.get("class_code", "").strip().upper()

    classroom = query_db(
        "SELECT * FROM classes WHERE class_code=%s",
        (code,),
        one=True,
    )

    if not classroom:
        flash("Class code not found.", "danger")
    else:
        try:
            execute_db(
                """INSERT INTO class_members
                   (class_id, student_id)
                   VALUES (%s, %s)""",
                (classroom["id"], session["user_id"]),
            )
            flash(f"You joined {classroom['name']}.", "success")
        except IntegrityError:
            flash("You are already a member of that class.", "info")

    return redirect(url_for("dashboard"))


@app.route("/classes/<int:class_id>")
@login_required
def class_detail(class_id):
    if session["role"] == "teacher":
        classroom = get_class_for_teacher(class_id)
    else:
        classroom = get_student_class_membership(class_id)

    if not classroom:
        abort(404)

    polls = query_db(
        """SELECT p.*,
           (SELECT COUNT(*) FROM votes v
            WHERE v.poll_id=p.id) AS vote_count
           FROM polls p
           WHERE p.class_id=%s
           ORDER BY p.created_at DESC""",
        (class_id,),
    )

    return render_template(
        "class_detail.html",
        classroom=classroom,
        polls=polls,
    )


@app.route(
    "/classes/<int:class_id>/polls/create",
    methods=["GET", "POST"],
)
@login_required
@role_required("teacher")
def create_poll(class_id):
    classroom = get_class_for_teacher(class_id)

    if not classroom:
        abort(404)

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        options = [
            option.strip()
            for option in request.form.getlist("options")
            if option.strip()
        ]
        closes_raw = request.form.get("closes_at", "").strip()
        visible = request.form.get("results_visible") == "on"

        if not question or len(options) < 2:
            flash(
                "Enter a question and at least two options.",
                "danger",
            )
            return render_template(
                "create_poll.html",
                classroom=classroom,
            )

        closes_at = None

        if closes_raw:
            try:
                closes_at = datetime.strptime(
                    closes_raw,
                    "%Y-%m-%dT%H:%M",
                )
                if closes_at <= datetime.now():
                    flash(
                        "Closing time must be in the future.",
                        "danger",
                    )
                    return render_template(
                        "create_poll.html",
                        classroom=classroom,
                    )
            except ValueError:
                flash("Invalid closing date/time.", "danger")
                return render_template(
                    "create_poll.html",
                    classroom=classroom,
                )

        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute(
                """INSERT INTO polls
                   (class_id, created_by, question,
                    closes_at, results_visible)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    class_id,
                    session["user_id"],
                    question,
                    closes_at,
                    visible,
                ),
            )

            poll_id = cur.lastrowid

            cur.executemany(
                """INSERT INTO poll_options
                   (poll_id, option_text)
                   VALUES (%s, %s)""",
                [(poll_id, option) for option in options],
            )

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

        flash("Poll created successfully.", "success")
        return redirect(url_for("poll_detail", poll_id=poll_id))

    return render_template(
        "create_poll.html",
        classroom=classroom,
    )


def get_poll_and_check_access(poll_id):
    poll = query_db(
        """SELECT p.*, c.name AS class_name,
                  c.teacher_id
           FROM polls p
           JOIN classes c ON c.id=p.class_id
           WHERE p.id=%s""",
        (poll_id,),
        one=True,
    )

    if not poll:
        abort(404)

    if session["role"] == "teacher":
        if poll["teacher_id"] != session["user_id"]:
            abort(403)
    elif not get_student_class_membership(poll["class_id"]):
        abort(403)

    return poll


def poll_is_open(poll):
    if poll["is_closed"]:
        return False

    if poll["closes_at"] and poll["closes_at"] <= datetime.now():
        return False

    return True


@app.route("/polls/<int:poll_id>")
@login_required
def poll_detail(poll_id):
    poll = get_poll_and_check_access(poll_id)

    options = query_db(
        """SELECT * FROM poll_options
           WHERE poll_id=%s ORDER BY id""",
        (poll_id,),
    )

    has_voted = False
    selected_option = None

    if session["role"] == "student":
        vote = query_db(
            """SELECT option_id FROM votes
               WHERE poll_id=%s AND student_id=%s""",
            (poll_id, session["user_id"]),
            one=True,
        )
        has_voted = bool(vote)
        selected_option = vote["option_id"] if vote else None

    show_results = (
        session["role"] == "teacher"
        or poll["results_visible"]
        or has_voted
        or not poll_is_open(poll)
    )

    results = []
    total_votes = 0

    if show_results:
        results = query_db(
            """SELECT o.id, o.option_text,
                      COUNT(v.id) AS vote_count
               FROM poll_options o
               LEFT JOIN votes v ON v.option_id=o.id
               WHERE o.poll_id=%s
               GROUP BY o.id, o.option_text
               ORDER BY o.id""",
            (poll_id,),
        )

        total_votes = sum(row["vote_count"] for row in results)

        for row in results:
            row["percentage"] = (
                round(row["vote_count"] * 100 / total_votes, 1)
                if total_votes
                else 0
            )

    return render_template(
        "poll_detail.html",
        poll=poll,
        options=options,
        has_voted=has_voted,
        selected_option=selected_option,
        show_results=show_results,
        results=results,
        total_votes=total_votes,
        is_open=poll_is_open(poll),
    )


@app.route("/polls/<int:poll_id>/vote", methods=["POST"])
@login_required
@role_required("student")
def cast_vote(poll_id):
    poll = get_poll_and_check_access(poll_id)

    if not poll_is_open(poll):
        flash("This poll is closed.", "warning")
        return redirect(url_for("poll_detail", poll_id=poll_id))

    option_id = request.form.get("option_id", type=int)

    valid_option = query_db(
        """SELECT id FROM poll_options
           WHERE id=%s AND poll_id=%s""",
        (option_id, poll_id),
        one=True,
    )

    if not valid_option:
        flash("Please select a valid option.", "danger")
        return redirect(url_for("poll_detail", poll_id=poll_id))

    try:
        execute_db(
            """INSERT INTO votes
               (poll_id, option_id, student_id)
               VALUES (%s, %s, %s)""",
            (poll_id, option_id, session["user_id"]),
        )
        flash("Your vote has been recorded.", "success")
    except IntegrityError:
        flash("You have already voted in this poll.", "info")

    return redirect(url_for("poll_detail", poll_id=poll_id))


@app.route("/polls/<int:poll_id>/close", methods=["POST"])
@login_required
@role_required("teacher")
def close_poll(poll_id):
    get_poll_and_check_access(poll_id)

    execute_db(
        "UPDATE polls SET is_closed=TRUE WHERE id=%s",
        (poll_id,),
    )

    flash("Poll closed.", "success")
    return redirect(url_for("poll_detail", poll_id=poll_id))


@app.route("/polls/<int:poll_id>/participation")
@login_required
@role_required("teacher")
def participation(poll_id):
    poll = get_poll_and_check_access(poll_id)

    rows = query_db(
        """SELECT u.id, u.name, u.email,
           CASE WHEN v.id IS NULL
                THEN 'Pending' ELSE 'Voted'
           END AS status
           FROM class_members cm
           JOIN users u ON u.id=cm.student_id
           LEFT JOIN votes v
             ON v.student_id=u.id AND v.poll_id=%s
           WHERE cm.class_id=%s
           ORDER BY u.name""",
        (poll_id, poll["class_id"]),
    )

    voted_count = sum(
        1 for row in rows if row["status"] == "Voted"
    )

    return render_template(
        "participation.html",
        poll=poll,
        rows=rows,
        voted_count=voted_count,
        total=len(rows),
    )


@app.route("/polls/<int:poll_id>/participation.csv")
@login_required
@role_required("teacher")
def participation_csv(poll_id):
    poll = get_poll_and_check_access(poll_id)

    rows = query_db(
        """SELECT u.name, u.email,
           CASE WHEN v.id IS NULL
                THEN 'Pending' ELSE 'Voted'
           END AS status
           FROM class_members cm
           JOIN users u ON u.id=cm.student_id
           LEFT JOIN votes v
             ON v.student_id=u.id AND v.poll_id=%s
           WHERE cm.class_id=%s
           ORDER BY u.name""",
        (poll_id, poll["class_id"]),
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Student Name",
        "Email",
        "Participation Status",
    ])

    for row in rows:
        writer.writerow([
            row["name"],
            row["email"],
            row["status"],
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="poll_{poll_id}_participation.csv"'
    )

    return response


@app.errorhandler(403)
def forbidden(_error):
    return render_template(
        "error.html",
        code=403,
        message="You do not have permission to access this page.",
    ), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "error.html",
        code=404,
        message="The page or item could not be found.",
    ), 404


if __name__ == "__main__":
    app.run(debug=True)
