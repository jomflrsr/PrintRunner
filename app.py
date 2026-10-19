"""PrintRunner student-project backend: Flask API and SQLite storage."""

from __future__ import annotations

import getpass
import os
import secrets
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
DATA_DIR = Path(os.environ.get("PRINTRUNNER_DATA_DIR", str(INSTANCE_DIR))).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "printrunner.sqlite3"
SECRET_PATH = DATA_DIR / ".session-secret"
MAX_UPLOAD = 15 * 1024 * 1024
ALLOWED_FILES = {"pdf", "doc", "docx", "ppt", "pptx", "jpg", "jpeg", "png"}
ASSETS = {
    "styles.css", "portal.css", "main.py", "join.py", "staff.js", "backend.js",
    "media/printrunner-commercial-fun-v2.mp4",
    "media/printrunner-commercial-fun-poster.jpg",
}
STATUSES = {"New", "In progress", "Completed"}

def load_secret_key() -> str:
    configured_key = os.environ.get("PRINTRUNNER_SECRET_KEY")
    if configured_key:
        return configured_key
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(SECRET_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return SECRET_PATH.read_text(encoding="utf-8").strip()
    secret = secrets.token_hex(32)
    with os.fdopen(descriptor, "w", encoding="utf-8") as secret_file:
        secret_file.write(secret)
    return secret


app = Flask(__name__)
app.config.update(
    SECRET_KEY=load_secret_key(),
    MAX_CONTENT_LENGTH=MAX_UPLOAD + 256 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("PRINTRUNNER_COOKIE_SECURE") == "1",
)


def connect_db() -> sqlite3.Connection:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def database():
    conn = connect_db()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize_db() -> None:
    with database() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                customer TEXT NOT NULL,
                contact TEXT NOT NULL,
                print_type TEXT NOT NULL CHECK (print_type IN ('bw', 'color')),
                pages INTEGER NOT NULL,
                copies INTEGER NOT NULL,
                dropoff TEXT NOT NULL,
                location TEXT NOT NULL,
                total INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'New',
                original_filename TEXT,
                stored_filename TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                availability TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
        """)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def require_csrf() -> None:
    token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if not token or not secrets.compare_digest(token, session.get("csrf_token", "")):
        abort(400, description="Your session expired. Refresh the page and try again.")


def staff_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("staff_id"):
            return jsonify(error="Please sign in to access the service board."), 401
        return fn(*args, **kwargs)
    return wrapper


def clean_text(value: object, limit: int, field: str) -> str:
    result = str(value or "").strip()
    if not result or len(result) > limit:
        raise ValueError(f"Enter a valid {field} (up to {limit} characters).")
    return result


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error="The selected file is too large. Maximum size is 15 MB."), 413


@app.route("/")
@app.route("/index.html")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/join.html")
def join_page():
    return send_from_directory(BASE_DIR, "join.html")


@app.route("/staff.html")
def staff_page():
    return send_from_directory(BASE_DIR, "staff.html")


@app.route("/<path:asset>")
def public_asset(asset: str):
    if asset not in ASSETS:
        abort(404)
    return send_from_directory(BASE_DIR, asset, conditional=True)


@app.get("/api/csrf")
def get_csrf():
    return jsonify(token=csrf_token())


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/api/orders")
def create_order():
    require_csrf()
    try:
        customer = clean_text(request.form.get("customer-name"), 60, "name")
        contact = clean_text(request.form.get("customer-contact"), 20, "contact number")
        location = clean_text(request.form.get("location-detail"), 80, "campus location")
        dropoff = request.form.get("dropoff", "")
        print_type = request.form.get("print-type", "")
        if dropoff not in {"Classroom", "Library", "Campus lobby"}:
            raise ValueError("Choose a valid campus meeting point.")
        if print_type not in {"bw", "color"}:
            raise ValueError("Choose a valid print type.")
        pages = int(request.form.get("page-count", ""))
        copies = int(request.form.get("copy-count", ""))
        if not 1 <= pages <= 500 or not 1 <= copies <= 50:
            raise ValueError("Pages must be 1–500 and copies must be 1–50.")
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400

    upload = request.files.get("file-upload")
    original_name = stored_name = None
    if upload and upload.filename:
        safe_name = secure_filename(upload.filename)
        suffix = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
        if suffix not in ALLOWED_FILES:
            return jsonify(error="Choose a PDF, Office document, or image file."), 400
        payload = upload.read(MAX_UPLOAD + 1)
        if len(payload) > MAX_UPLOAD:
            return jsonify(error="The selected file is too large. Maximum size is 15 MB."), 413
        original_name = safe_name[:180]
        stored_name = f"{uuid.uuid4().hex}.{suffix}"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        (UPLOAD_DIR / stored_name).write_bytes(payload)

    order_id = f"PR-{uuid.uuid4().hex[:8].upper()}"
    total = pages * copies * (5 if print_type == "color" else 2) + 10
    try:
        with database() as db:
            db.execute("""INSERT INTO orders
                (id, customer, contact, print_type, pages, copies, dropoff, location, total,
                 original_filename, stored_filename, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (order_id, customer, contact, print_type, pages, copies, dropoff, location,
                 total, original_name, stored_name, now_iso()))
    except Exception:
        if stored_name:
            (UPLOAD_DIR / stored_name).unlink(missing_ok=True)
        raise
    return jsonify(id=order_id, total=total, message="Your order was sent to the PrintRunner team."), 201


@app.post("/api/applications")
def create_application():
    require_csrf()
    data = request.get_json(silent=True) or {}
    try:
        name = clean_text(data.get("name"), 80, "name")
        email = clean_text(data.get("email"), 120, "email address")
        phone = clean_text(data.get("phone"), 20, "contact number")
        availability = clean_text(data.get("availability"), 40, "availability")
        reason = str(data.get("reason", "")).strip()[:400]
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address.")
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400
    with database() as db:
        cursor = db.execute("""INSERT INTO applications
            (name, email, phone, availability, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)""",
            (name, email, phone, availability, reason, now_iso()))
    return jsonify(message="Thanks for applying. The PrintRunner team will be in touch.", id=cursor.lastrowid), 201


def order_dict(row: sqlite3.Row) -> dict:
    label = "color" if row["print_type"] == "color" else "B&W"
    created = datetime.fromisoformat(row["created_at"]).astimezone().strftime("%b %d, %I:%M %p")
    return {
        "id": row["id"], "customer": row["customer"], "contact": row["contact"],
        "file": row["original_filename"] or "No file attached",
        "print": f"{row['pages']} {label} pages × {row['copies']} {'copy' if row['copies'] == 1 else 'copies'}",
        "dropoff": f"{row['dropoff']} · {row['location']}", "total": row["total"],
        "status": row["status"], "created": created, "has_file": bool(row["stored_filename"]),
    }


@app.post("/api/staff/login")
def staff_login():
    require_csrf()
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    with database() as db:
        staff = db.execute("SELECT * FROM staff WHERE username = ?", (username,)).fetchone()
    if not staff or not check_password_hash(staff["password_hash"], password):
        return jsonify(error="Username or password is incorrect."), 401
    session.clear()
    session["staff_id"] = staff["id"]
    session["staff_username"] = staff["username"]
    token = csrf_token()
    return jsonify(username=staff["username"], csrf=token)


@app.post("/api/staff/logout")
@staff_required
def staff_logout():
    require_csrf()
    session.clear()
    return jsonify(message="Signed out.")


@app.get("/api/staff/session")
def staff_session():
    if not session.get("staff_id"):
        return jsonify(authenticated=False), 200
    return jsonify(authenticated=True, username=session.get("staff_username"))


@app.get("/api/staff/orders")
@staff_required
def staff_orders():
    with database() as db:
        rows = db.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    return jsonify(orders=[order_dict(row) for row in rows])


@app.patch("/api/staff/orders/<order_id>/status")
@staff_required
def update_order_status(order_id: str):
    require_csrf()
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in STATUSES:
        return jsonify(error="Choose a valid order status."), 400
    with database() as db:
        cursor = db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    if not cursor.rowcount:
        return jsonify(error="Order not found."), 404
    return jsonify(message="Order status updated.")


@app.get("/api/staff/orders/<order_id>/file")
@staff_required
def staff_order_file(order_id: str):
    with database() as db:
        row = db.execute("SELECT stored_filename, original_filename FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not row or not row["stored_filename"]:
        abort(404)
    return send_file(UPLOAD_DIR / row["stored_filename"], as_attachment=True,
                     download_name=row["original_filename"], conditional=True)


def create_staff(username: str) -> None:
    password = getpass.getpass("Choose a password for this staff account: ")
    confirm = getpass.getpass("Confirm password: ")
    if len(password) < 12:
        raise SystemExit("Use at least 12 characters for the staff password.")
    if password != confirm:
        raise SystemExit("Passwords did not match.")
    try:
        with database() as db:
            db.execute("INSERT INTO staff (username, password_hash, created_at) VALUES (?, ?, ?)",
                       (username, generate_password_hash(password), now_iso()))
    except sqlite3.IntegrityError:
        raise SystemExit("That staff username already exists.")
    print(f"Staff account '{username}' created.")


initialize_db()

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "create-staff":
        create_staff(sys.argv[2])
    else:
        print("Local project mode: set PRINTRUNNER_DATA_DIR and PRINTRUNNER_SECRET_KEY for deployment.")
        app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8000")), debug=False)
