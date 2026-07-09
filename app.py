from __future__ import annotations

from pathlib import Path
from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import json
import shutil
from datetime import datetime, timedelta
import pandas as pd

from rank_analysis import (
    build_analysis_payload,
    get_student_profile,
    build_rank_dataframe,
)

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "students.csv"
USERS_PATH = BASE_DIR / "users.json"

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "ai-platform-secret-2024-edu"  # Change in production

def default_users() -> dict:
    """Create default seed accounts for first-time setup."""
    return {
        "admin@eduai.com": {
            "password_hash": generate_password_hash("admin123"),
            "user_type": "admin",
            "user_name": "Administrator",
            "student_name": None,
        },
        "teacher@eduai.com": {
            "password_hash": generate_password_hash("teacher123"),
            "user_type": "teacher",
            "user_name": "Educator",
            "student_name": None,
        },
        "student@eduai.com": {
            "password_hash": generate_password_hash("student123"),
            "user_type": "student",
            "user_name": "Arun",
            "student_name": "Arun",
        },
    }


def save_users(users: dict) -> None:
    """Persist user accounts to disk."""
    USERS_PATH.write_text(json.dumps(users, indent=2), encoding="utf-8")


def load_users() -> dict:
    """Load users from disk and seed defaults when needed."""
    if not USERS_PATH.exists():
        users = default_users()
        save_users(users)
        return users

    try:
        users = json.loads(USERS_PATH.read_text(encoding="utf-8"))
        if isinstance(users, dict):
            return users
    except json.JSONDecodeError:
        pass

    users = default_users()
    save_users(users)
    return users


def set_user_session(email: str, account: dict) -> None:
    """Store user identity in the session."""
    session["user_email"] = email
    session["user_type"] = account.get("user_type", "teacher")
    session["user_name"] = account.get("user_name", "User")
    session["student_name"] = account.get("student_name")
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=24)


def get_current_user():
    """Get current logged-in user info from session."""
    if "user_email" not in session:
        return None
    
    user_type = session.get("user_type", "teacher")
    student_name = session.get("student_name")
    
    return {
        "email": session["user_email"],
        "type": user_type,
        "name": session.get("user_name", "User"),
        "student_name": student_name
    }


def normalize_marks_dataframe(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Validate and normalize uploaded marks CSV before saving."""
    if raw_df is None or raw_df.empty:
        raise ValueError("Uploaded file is empty")

    raw_df.columns = [str(column).strip() for column in raw_df.columns]
    lowered_map = {column.lower(): column for column in raw_df.columns}
    candidate_name = lowered_map.get("name") or lowered_map.get("student") or lowered_map.get("student_name")
    if not candidate_name:
        raise ValueError("CSV must include a Name column (accepted: Name, student, or student_name)")

    if candidate_name != "Name":
        raw_df = raw_df.rename(columns={candidate_name: "Name"})

    subject_columns = [column for column in raw_df.columns if column != "Name"]
    if not subject_columns:
        raise ValueError("CSV must include at least one subject column")

    reserved_columns = {
        "total",
        "average",
        "rank",
        "percentile",
        "consistency",
        "grade",
        "result",
        "risklevel",
    }
    invalid_subjects = [column for column in subject_columns if column.strip().lower() in reserved_columns]
    if invalid_subjects:
        raise ValueError(
            "Subject names cannot use reserved fields: " + ", ".join(invalid_subjects)
        )

    if len(set(subject_columns)) != len(subject_columns):
        raise ValueError("Duplicate subject column names found. Please keep subject names unique")

    cleaned = raw_df[["Name", *subject_columns]].copy()
    cleaned["Name"] = cleaned["Name"].astype(str).str.strip()

    if cleaned["Name"].eq("").any() or cleaned["Name"].str.lower().eq("nan").any():
        raise ValueError("Each row must have a valid student name")

    duplicate_mask = cleaned["Name"].duplicated()
    if duplicate_mask.any():
        duplicate_names = cleaned.loc[duplicate_mask, "Name"].unique().tolist()
        duplicates = ", ".join(duplicate_names[:5])
        raise ValueError(f"Duplicate student names found: {duplicates}")

    for subject in subject_columns:
        cleaned[subject] = pd.to_numeric(cleaned[subject], errors="coerce")
        if cleaned[subject].isna().any():
            invalid_students = cleaned.loc[cleaned[subject].isna(), "Name"].head(5).tolist()
            raise ValueError(
                f"Invalid marks for {subject}. Check numeric values for: {', '.join(invalid_students)}"
            )

        out_of_range = (cleaned[subject] < 0) | (cleaned[subject] > 100)
        if out_of_range.any():
            invalid_students = cleaned.loc[out_of_range, "Name"].head(5).tolist()
            raise ValueError(
                f"Marks for {subject} must be between 0 and 100. Check: {', '.join(invalid_students)}"
            )

        cleaned[subject] = cleaned[subject].round(2)

    return cleaned, subject_columns


# ==================== Auth Routes ====================

@app.route("/")
def index():
    """Home page - redirect to dashboard if logged in."""
    user = get_current_user()
    if user:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page and authentication."""
    if request.method == "GET":
        signup_success = request.args.get("created") == "1"
        reset_success = request.args.get("reset") == "1"
        return render_template(
            "login.html",
            signup_success=signup_success,
            reset_success=reset_success,
        )
    
    # Handle login POST
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    if not email or not password:
        return render_template("login.html", error="Please enter email and password"), 400

    email = email.lower()
    users = load_users()
    account = users.get(email)

    if not account:
        return render_template("login.html", error="Invalid credentials"), 401

    if not check_password_hash(account.get("password_hash", ""), password):
        return render_template("login.html", error="Invalid credentials"), 401

    set_user_session(email, account)

    if account.get("user_type") == "student" and account.get("student_name"):
        return redirect(url_for("student_dashboard", student_name=account["student_name"]))

    return redirect(url_for("dashboard"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Allow users to reset password using their registered login email."""
    if request.method == "GET":
        return render_template("forgot_password.html")

    email = request.form.get("email", "").strip().lower()
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not email or not new_password or not confirm_password:
        return render_template(
            "forgot_password.html",
            error="Please fill in all fields",
        ), 400

    users = load_users()
    account = users.get(email)

    if not account:
        return render_template(
            "forgot_password.html",
            error="No account found for this email",
        ), 404

    if len(new_password) < 6:
        return render_template(
            "forgot_password.html",
            error="Password must be at least 6 characters",
        ), 400

    if new_password != confirm_password:
        return render_template(
            "forgot_password.html",
            error="Passwords do not match",
        ), 400

    account["password_hash"] = generate_password_hash(new_password)
    users[email] = account
    save_users(users)

    return redirect(url_for("login", reset="1"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Create a new account with a unique login ID."""
    students_data = build_rank_dataframe(str(CSV_PATH))
    student_names = students_data["Name"].tolist()

    if request.method == "GET":
        return render_template("signup.html", student_names=student_names)

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    user_type = request.form.get("user_type", "teacher")
    student_name = request.form.get("student_select", "").strip()

    if not full_name or not email or not password or not confirm_password:
        return render_template(
            "signup.html",
            error="Please fill in all required fields",
            student_names=student_names,
        ), 400

    if "@" not in email:
        return render_template(
            "signup.html",
            error="Please enter a valid email address",
            student_names=student_names,
        ), 400

    if password != confirm_password:
        return render_template(
            "signup.html",
            error="Passwords do not match",
            student_names=student_names,
        ), 400

    if len(password) < 6:
        return render_template(
            "signup.html",
            error="Password must be at least 6 characters",
            student_names=student_names,
        ), 400

    if user_type not in {"teacher", "admin", "student"}:
        return render_template(
            "signup.html",
            error="Invalid account type",
            student_names=student_names,
        ), 400

    if user_type == "student" and student_name not in student_names:
        return render_template(
            "signup.html",
            error="Please select a valid student profile",
            student_names=student_names,
        ), 400

    users = load_users()
    if email in users:
        return render_template(
            "signup.html",
            error="An account with this email already exists",
            student_names=student_names,
        ), 409

    users[email] = {
        "password_hash": generate_password_hash(password),
        "user_type": user_type,
        "user_name": full_name,
        "student_name": student_name if user_type == "student" else None,
    }
    save_users(users)

    return redirect(url_for("login", created="1"))


@app.route("/logout")
def logout():
    """Logout user."""
    session.clear()
    return redirect(url_for("login"))


@app.route("/auth/check")
def check_auth():
    """Check if user is authenticated."""
    user = get_current_user()
    return jsonify({
        "authenticated": user is not None,
        "user": user
    })


# ==================== Dashboard Routes ====================

@app.route("/dashboard")
def dashboard():
    """Main hub dashboard for teachers/admins."""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    
    if user["type"] == "student":
        return redirect(url_for("student_dashboard", student_name=user["student_name"]))
    
    return render_template("hub.html", user=user)


@app.route("/dashboard/briefing")
def briefing():
    """AI Briefing page."""
    user = get_current_user()
    if not user or user["type"] == "student":
        return redirect(url_for("login"))
    
    return render_template("briefing.html", user=user)


@app.route("/dashboard/performance")
def performance():
    """Performance & Risk page."""
    user = get_current_user()
    if not user or user["type"] == "student":
        return redirect(url_for("login"))
    
    return render_template("performance.html", user=user)


@app.route("/dashboard/subject-focus")
def subject_focus():
    """Subject Focus & Recommendations page."""
    user = get_current_user()
    if not user or user["type"] == "student":
        return redirect(url_for("login"))
    # Provide an initial server-side analysis payload so the page is populated
    # even if the client-side API fetch is blocked or slow.
    payload = build_analysis_payload(str(CSV_PATH))
    # The AI brief contains subject_focus, narrative, and recommendation data.
    summary = payload.get("ai_brief", {})
    subject_intelligence = payload.get("subject_intelligence", {})
    subjects = payload.get("subjects", [])
    class_profile = payload.get("summary", {})

    return render_template(
        "subject_focus.html",
        user=user,
        summary=summary,
        class_profile=class_profile,
        subject_intelligence=subject_intelligence,
        subjects=subjects,
    )


@app.route("/dashboard/metrics")
def metrics():
    """Performance Metrics page."""
    user = get_current_user()
    if not user or user["type"] == "student":
        return redirect(url_for("login"))
    
    return render_template("metrics.html", user=user)


@app.route("/dashboard/students")
def students_overview():
    """Students Overview & Interventions page."""
    user = get_current_user()
    if not user or user["type"] == "student":
        return redirect(url_for("login"))
    
    return render_template("students_overview.html", user=user)


@app.route("/dashboard/teacher")
def teacher_dashboard():
    """Teacher dashboard to upload and manage marks CSV."""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if user["type"] not in {"teacher", "admin"}:
        return render_template("error.html", message="Access denied"), 403

    return render_template("teacher_dashboard.html", user=user)


@app.route("/student/<student_name>")
def student_dashboard(student_name):
    """Individual student profile page."""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    
    # Verify access - student can only view their own profile
    if user["type"] == "student" and user["student_name"] != student_name:
        return render_template("error.html", message="Access denied"), 403
    
    profile = get_student_profile(student_name, str(CSV_PATH))
    if "error" in profile:
        return render_template("error.html", message=profile["error"]), 404
    
    return render_template("student_profile.html", profile=profile, user=user)


# ==================== API Routes ====================

@app.route("/api/analysis")
def analysis():
    """Get full analysis payload."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    payload = build_analysis_payload(str(CSV_PATH))

    # Backwards compatibility for templates: many templates expect a
    # `summary` object with ai briefing fields (momentum, class_profile,
    # risk_breakdown, standout_performers, etc.). The analysis payload
    # contains `ai_brief` and other top-level keys — expose a `summary`
    # that includes the ai brief plus commonly used aggregates so
    # client-side templates work without additional changes.
    summary = payload.get("ai_brief", {})
    # Include a few extra useful top-level keys if present
    if "score_bands" in payload:
        summary.setdefault("score_bands", payload["score_bands"])
    if "subject_intelligence" in payload:
        summary.setdefault("subject_intelligence", payload["subject_intelligence"])
    if "summary" in payload:
        # preserve original small summary keys as well
        summary.setdefault("class_profile", payload["summary"]) 

    payload["summary"] = summary

    return jsonify(payload)


@app.route("/api/student/<student_name>")
def api_student_profile(student_name):
    """API endpoint for student profile."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Verify access
    if user["type"] == "student" and user["student_name"] != student_name:
        return jsonify({"error": "Access denied"}), 403
    
    profile = get_student_profile(student_name, str(CSV_PATH))
    return jsonify(profile)


@app.route("/api/students")
def api_students():
    """Get all students list."""
    user = get_current_user()
    if not user or user["type"] not in ["teacher", "admin"]:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = build_rank_dataframe(str(CSV_PATH))
    students_list = data[["Name", "Total", "Rank", "Grade", "Result", "RiskLevel", "Average"]].to_dict(orient="records")
    return jsonify({"students": students_list})


@app.route("/api/recommendations")
def api_recommendations():
    """Get recommendations for all students (teachers only)."""
    user = get_current_user()
    if not user or user["type"] not in ["teacher", "admin"]:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = build_rank_dataframe(str(CSV_PATH))
    
    # Generate quick recommendations for dashboard
    recommendations = []
    for idx, row in data.iterrows():
        if row["Result"] == "Fail" or row["RiskLevel"] in ["High", "Medium"]:
            recommendations.append({
                "name": row["Name"],
                "risk": row["RiskLevel"],
                "result": row["Result"],
                "avg": round(row["Average"], 1),
                "action": "Schedule intervention" if row["Result"] == "Fail" else "Monitor progress"
            })
    
    return jsonify({"recommendations": sorted(recommendations, key=lambda x: (x["result"] == "Fail", x["risk"]), reverse=True)})


@app.route("/api/summary")
def api_summary():
    """Get dashboard summary."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    payload = build_analysis_payload(str(CSV_PATH))
    return jsonify(payload["summary"])


@app.route("/api/teacher/marks-schema")
def teacher_marks_schema():
    """Return current marks schema for teacher upload guidance."""
    user = get_current_user()
    if not user or user["type"] not in ["teacher", "admin"]:
        return jsonify({"error": "Unauthorized"}), 401

    current_df = pd.read_csv(CSV_PATH)
    columns = [str(column).strip() for column in current_df.columns.tolist()]
    subjects = [column for column in columns if column != "Name"]

    return jsonify(
        {
            "columns": columns,
            "subjects": subjects,
            "student_count": int(len(current_df)),
        }
    )


@app.route("/api/teacher/template")
def teacher_template():
    """Download a flexible CSV template with teacher-selected subject count."""
    user = get_current_user()
    if not user or user["type"] not in ["teacher", "admin"]:
        return jsonify({"error": "Unauthorized"}), 401

    count_param = request.args.get("subject_count", "6")
    try:
        subject_count = int(count_param)
    except ValueError:
        subject_count = 6

    subject_count = max(1, min(20, subject_count))
    columns = ["Name", *[f"Subject_{index}" for index in range(1, subject_count + 1)]]
    csv_template = ",".join(columns) + "\n"

    response = app.response_class(csv_template, mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=marks_template.csv"
    return response


@app.route("/api/teacher/upload-marks", methods=["POST"])
def teacher_upload_marks():
    """Replace marks dataset from teacher uploaded CSV."""
    user = get_current_user()
    if not user or user["type"] not in ["teacher", "admin"]:
        return jsonify({"error": "Unauthorized"}), 401

    if "marks_file" not in request.files:
        return jsonify({"error": "Please choose a CSV file to upload"}), 400

    uploaded_file = request.files["marks_file"]
    if not uploaded_file or uploaded_file.filename.strip() == "":
        return jsonify({"error": "Please choose a CSV file to upload"}), 400

    if not uploaded_file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only CSV files are supported"}), 400

    try:
        uploaded_df = pd.read_csv(uploaded_file)
        cleaned_df, subject_columns = normalize_marks_dataframe(uploaded_df)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Could not read the uploaded CSV file"}), 400

    backup_path = BASE_DIR / "students_backup.csv"
    if CSV_PATH.exists():
        shutil.copy2(CSV_PATH, backup_path)

    cleaned_df.to_csv(CSV_PATH, index=False)

    return jsonify(
        {
            "message": "Marks uploaded successfully",
            "student_count": int(len(cleaned_df)),
            "subjects": subject_columns,
            "preview": cleaned_df.head(8).to_dict(orient="records"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    )


@app.route("/api/interventions")
def api_interventions():
    """Get intervention data."""
    user = get_current_user()
    if not user or user["type"] not in ["teacher", "admin"]:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = build_rank_dataframe(str(CSV_PATH))
    
    interventions = []
    for idx, row in data.iterrows():
        if row["Result"] == "Fail":
            interventions.append({
                "name": row["Name"],
                "status": "Critical",
                "average": round(row["Average"], 1),
                "reason": f"Failing in multiple subjects",
                "assigned_date": datetime.now().strftime("%Y-%m-%d")
            })
        elif row["RiskLevel"] == "High":
            interventions.append({
                "name": row["Name"],
                "status": "High Risk",
                "average": round(row["Average"], 1),
                "reason": f"Below passing threshold",
                "assigned_date": datetime.now().strftime("%Y-%m-%d")
            })
    
    return jsonify({"interventions": interventions})


# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template("error.html", message="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template("error.html", message="Internal server error"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
