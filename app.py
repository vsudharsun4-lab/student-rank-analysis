from __future__ import annotations

import os
import tempfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from pathlib import Path
from flask import Flask, jsonify, render_template, request, session, redirect, url_for, make_response
import dotenv

# Load configuration from environment variables
dotenv.load_dotenv()
from werkzeug.security import generate_password_hash, check_password_hash
import json
import re
import shutil
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
from xhtml2pdf import pisa

from rank_analysis import (
    build_analysis_payload,
    get_student_profile,
    build_rank_dataframe,
    build_attendance_summary,
)

from agent import generate_student_pdf_remarks, generate_teacher_pdf_cohort_report


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "students.csv"
USERS_PATH = BASE_DIR / "users.json"
ATTENDANCE_COLUMN_NAMES = {
    "attendance",
    "attendance%",
    "attendance_percentage",
    "attendance percentage",
}

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

    attendance_column = None
    for column in raw_df.columns:
        if column != "Name" and str(column).strip().lower() in ATTENDANCE_COLUMN_NAMES:
            attendance_column = column
            break

    if attendance_column and attendance_column != "Attendance":
        raw_df = raw_df.rename(columns={attendance_column: "Attendance"})

    subject_columns = [column for column in raw_df.columns if column != "Name" and column != "Attendance"]
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
        "attendance",
    }
    invalid_subjects = [column for column in subject_columns if column.strip().lower() in reserved_columns]
    if invalid_subjects:
        raise ValueError(
            "Subject names cannot use reserved fields: " + ", ".join(invalid_subjects)
        )

    if len(set(subject_columns)) != len(subject_columns):
        raise ValueError("Duplicate subject column names found. Please keep subject names unique")

    cleaned_columns = ["Name", *subject_columns]
    if "Attendance" in raw_df.columns:
        cleaned_columns.append("Attendance")

    cleaned = raw_df[cleaned_columns].copy()
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

    if "Attendance" in cleaned.columns:
        cleaned["Attendance"] = pd.to_numeric(cleaned["Attendance"], errors="coerce")
        if cleaned["Attendance"].isna().any():
            invalid_students = cleaned.loc[cleaned["Attendance"].isna(), "Name"].head(5).tolist()
            raise ValueError(
                f"Invalid attendance values. Check numeric values for: {', '.join(invalid_students)}"
            )

        out_of_range = (cleaned["Attendance"] < 0) | (cleaned["Attendance"] > 100)
        if out_of_range.any():
            invalid_students = cleaned.loc[out_of_range, "Name"].head(5).tolist()
            raise ValueError(
                f"Attendance must be between 0 and 100. Check: {', '.join(invalid_students)}"
            )

        cleaned["Attendance"] = cleaned["Attendance"].round(2)

    return cleaned, subject_columns


def detect_student_name(question: str, student_names: list[str]) -> str | None:
    """Infer a student name from a free-form prompt when possible."""
    lowered_question = question.lower()
    for name in sorted(student_names, key=len, reverse=True):
        if re.search(re.escape(name.lower()), lowered_question):
            return name
    return None


def detect_student_names(question: str, student_names: list[str]) -> list[str]:
    """Infer all student names mentioned in a free-form prompt."""
    lowered_question = question.lower()
    matched_names = []
    for name in sorted(student_names, key=len, reverse=True):
        if re.search(re.escape(name.lower()), lowered_question):
            matched_names.append(name)
    return matched_names


def stringify_actions(actions: list) -> list[str]:
    """Normalize action payloads into display-ready strings."""
    formatted = []
    for action in actions:
        if isinstance(action, str):
            formatted.append(action)
        elif isinstance(action, dict):
            label = action.get("action", "Action")
            details = action.get("details")
            formatted.append(f"{label}: {details}" if details else label)
    return formatted


def parse_percentage_threshold(question: str) -> float | None:
    """Extract a percentage threshold from a natural-language query when present."""
    match = re.search(r"(?:below|under|less than|above|over|more than)\s+(\d+(?:\.\d+)?)\s*%?", question.lower())
    if match:
        return float(match.group(1))
    return None


def format_student_list_rows(rows: pd.DataFrame, limit: int | None = None) -> list[dict]:
    """Return a compact list of student summary rows for agent responses."""
    if limit is not None:
        rows = rows.head(limit)

    return [
        {
            "name": row["Name"],
            "average": round(float(row["Average"]), 1),
            "rank": int(row["Rank"]),
            "total": int(row["Total"]),
            "grade": row["Grade"],
        }
        for _, row in rows.iterrows()
    ]


def build_agent_response(question: str, user: dict, student_name: str | None = None) -> dict:
    """Route a prompt through the existing analytics helpers like a lightweight agent."""
    payload = build_analysis_payload(str(CSV_PATH))
    rank_df = build_rank_dataframe(str(CSV_PATH))
    students = payload.get("students", [])
    available_names = [student["Name"] for student in students if student.get("Name")]
    matched_names = detect_student_names(question, available_names)
    detected_student = student_name or detect_student_name(question, available_names)
    question_lower = question.lower().strip()
    tool_trace = ["build_analysis_payload"]
    attendance_summary = payload.get("attendance_summary") or build_attendance_summary(rank_df)

    if user.get("type") == "student":
        detected_student = user.get("student_name")
        matched_names = [detected_student] if detected_student else []

    if any(keyword in question_lower for keyword in ["topper", "top student", "rank 1", "highest scorer", "who is on top"]):
        topper_row = rank_df.nsmallest(1, "Rank").iloc[0]
        topper_name = topper_row["Name"]
        topper_average = float(topper_row["Average"])
        topper_rank = int(topper_row["Rank"])

        return {
            "intent": "topper_analysis",
            "answer": f"{topper_name} is the topper with an average of {topper_average:.1f} and rank #{topper_rank}.",
            "actions": [
                f"Topper: {topper_name}",
                f"Average: {topper_average:.1f}",
                f"Total marks: {int(topper_row['Total'])}",
            ],
            "highlights": [
                f"Rank #{topper_rank}",
                f"Grade {topper_row['Grade']}",
                f"Pass/Fail: {topper_row['Result']}",
            ],
            "tool_trace": tool_trace + ["build_rank_dataframe"],
            "student_name": topper_name,
        }

    if any(keyword in question_lower for keyword in ["low scorer", "lowest scorer", "weakest student", "bottom scorer", "lowest performer", "last rank", "poorest performer"]):
        low_row = rank_df.nsmallest(1, "Average").iloc[0]
        low_name = low_row["Name"]
        low_average = float(low_row["Average"])
        low_rank = int(low_row["Rank"])

        return {
            "intent": "lowest_scorer_analysis",
            "answer": f"{low_name} is the lowest scorer with an average of {low_average:.1f} and rank #{low_rank}.",
            "actions": [
                f"Lowest scorer: {low_name}",
                f"Average: {low_average:.1f}",
                f"Total marks: {int(low_row['Total'])}",
            ],
            "highlights": [
                f"Rank #{low_rank}",
                f"Grade {low_row['Grade']}",
                f"Pass/Fail: {low_row['Result']}",
            ],
            "tool_trace": tool_trace + ["build_rank_dataframe"],
            "student_name": low_name,
        }

    top_n_match = re.search(r"\btop\s+(\d+)\b", question_lower)
    if top_n_match and any(keyword in question_lower for keyword in ["top", "topper", "show", "list", "students"]):
        top_n = max(1, min(int(top_n_match.group(1)), len(rank_df)))
        top_students = format_student_list_rows(rank_df.nsmallest(top_n, "Rank"), limit=top_n)

        return {
            "intent": "top_students_analysis",
            "answer": f"Here are the top {top_n} students by rank.",
            "actions": [f"#{student['rank']} {student['name']} - average {student['average']:.1f}" for student in top_students],
            "highlights": [f"Top {top_n} based on total marks and rank."],
            "tool_trace": tool_trace + ["build_rank_dataframe"],
            "student_name": None,
        }

    threshold = parse_percentage_threshold(question_lower)
    if threshold is not None and any(keyword in question_lower for keyword in ["below", "under", "less than", "above", "over", "more than"]):
        if any(keyword in question_lower for keyword in ["below", "under", "less than"]):
            filtered = rank_df[rank_df["Average"] < threshold].sort_values(["Average", "Rank"], ascending=[True, True])
            answer = f"There are {len(filtered)} students below {threshold:.0f}% average."
        else:
            filtered = rank_df[rank_df["Average"] > threshold].sort_values(["Average", "Rank"], ascending=[False, True])
            answer = f"There are {len(filtered)} students above {threshold:.0f}% average."

        actions = [
            f"{row['Name']} - average {row['Average']:.1f}, rank #{row['Rank']}"
            for _, row in filtered.head(10).iterrows()
        ]

        return {
            "intent": "threshold_analysis",
            "answer": answer,
            "actions": actions,
            "highlights": [f"Threshold used: {threshold:.0f}%", f"Matching students: {len(filtered)}"],
            "tool_trace": tool_trace + ["build_rank_dataframe"],
            "student_name": None,
        }

    comparison_keywords = ["compare", "better than", "versus", "vs", "between", "difference", "higher than", "lower than"]
    if len(matched_names) >= 2 and any(keyword in question_lower for keyword in comparison_keywords):
        first_name, second_name = matched_names[0], matched_names[1]
        first_profile = get_student_profile(first_name, str(CSV_PATH))
        second_profile = get_student_profile(second_name, str(CSV_PATH))
        tool_trace.extend(["get_student_profile", "get_student_profile"])

        if "error" in first_profile or "error" in second_profile:
            missing_name = first_name if "error" in first_profile else second_name
            missing_profile = first_profile if "error" in first_profile else second_profile
            return {
                "intent": "student_lookup_failed",
                "answer": missing_profile["error"],
                "actions": [],
                "highlights": [],
                "tool_trace": tool_trace,
                "student_name": missing_name,
            }

        first_personal = first_profile["personal"]
        second_personal = second_profile["personal"]
        first_attendance = first_profile.get("attendance")
        second_attendance = second_profile.get("attendance")

        better_academic = first_personal if first_personal["average"] >= second_personal["average"] else second_personal
        lower_academic = second_personal if better_academic is first_personal else first_personal

        answer = (
            f"{better_academic['name']} is performing better academically than {lower_academic['name']}. "
            f"{first_personal['name']} has {first_personal['average']:.1f} average at rank #{first_personal['rank']}, while "
            f"{second_personal['name']} has {second_personal['average']:.1f} average at rank #{second_personal['rank']}."
        )

        actions = [
            f"Academic winner: {better_academic['name']} with average {better_academic['average']:.1f}",
            f"Rank comparison: {first_personal['name']} #{first_personal['rank']} vs {second_personal['name']} #{second_personal['rank']}",
        ]

        highlights = [
            f"{first_personal['name']}: average {first_personal['average']:.1f}, risk {first_personal['risk']}",
            f"{second_personal['name']}: average {second_personal['average']:.1f}, risk {second_personal['risk']}",
        ]

        if first_attendance or second_attendance:
            first_attendance_value = first_attendance["percentage"] if first_attendance else None
            second_attendance_value = second_attendance["percentage"] if second_attendance else None
            if first_attendance_value is not None and second_attendance_value is not None:
                better_attendance = first_attendance if first_attendance_value >= second_attendance_value else second_attendance
                lower_attendance = second_attendance if better_attendance is first_attendance else first_attendance
                answer += (
                    f" Attendance-wise, {better_attendance['percentage']:.1f}% for {better_attendance.get('name', better_academic['name'])} "
                    f"is higher than {lower_attendance['percentage']:.1f}%."
                )
            if first_attendance:
                highlights.append(f"{first_personal['name']} attendance: {first_attendance['percentage']:.1f}% ({first_attendance['status']})")
            if second_attendance:
                highlights.append(f"{second_personal['name']} attendance: {second_attendance['percentage']:.1f}% ({second_attendance['status']})")

        actions.extend(
            [
                f"Support the lower-performing student with peer tutoring and weekly check-ins.",
                f"Use the stronger student's routine as a benchmark for study habits and attendance.",
            ]
        )

        return {
            "intent": "student_comparison",
            "answer": answer,
            "actions": actions,
            "highlights": highlights,
            "tool_trace": tool_trace,
            "student_name": None,
        }

    if any(keyword in question_lower for keyword in ["attendance", "present", "absent", "absentee", "attendance percentage"]) and detected_student:
        profile = get_student_profile(detected_student, str(CSV_PATH))
        tool_trace.append("get_student_profile")

        if "error" in profile:
            return {
                "intent": "student_lookup_failed",
                "answer": profile["error"],
                "actions": [],
                "highlights": [],
                "tool_trace": tool_trace,
                "student_name": detected_student,
            }

        attendance = profile.get("attendance")
        if attendance:
            answer = (
                f"{detected_student} has {attendance['percentage']:.1f}% attendance, which is {attendance['status'].lower()} attendance. "
                f"The class average is {attendance['class_average']:.1f}%."
            )
            precautionary_methods = attendance.get("precautionary_methods", [])
            actions = [
                f"Attendance deviation from class average: {attendance.get('deviation_from_class', 0.0):+.1f}%",
                f"Attendance risk level: {attendance.get('risk_level', 'Medium')}",
                *precautionary_methods,
            ]
            highlights = [
                f"Student attendance: {attendance['percentage']:.1f}%",
                f"Attendance status: {attendance['status']}",
                f"Attendance advice: {attendance['advice']}",
            ]

            return {
                "intent": "student_attendance_analysis",
                "answer": answer,
                "actions": actions,
                "highlights": highlights,
                "tool_trace": tool_trace,
                "student_name": detected_student,
            }

    if any(keyword in question_lower for keyword in ["attendance", "present", "absent", "absentee", "attendance percentage"]):
        attendance_text = (
            f"Average attendance is {attendance_summary.get('average', 0.0):.1f}% with "
            f"{attendance_summary.get('high_count', 0)} high-attendance students and "
            f"{attendance_summary.get('low_count', 0)} low-attendance students."
        )

        return {
            "intent": "attendance_analysis",
            "answer": attendance_text,
            "actions": [
                f"High attendance: {attendance_summary.get('high_percentage', 0.0):.1f}% of the class",
                f"Low attendance: {attendance_summary.get('low_percentage', 0.0):.1f}% of the class",
                f"High threshold: at or above {attendance_summary.get('high_threshold', 90)}%",
                f"Low threshold: below {attendance_summary.get('low_threshold', 75)}%",
            ],
            "highlights": [
                f"Attendance metric is {'available' if attendance_summary.get('present') else 'not available'} in the dataset",
                f"Class average attendance: {attendance_summary.get('average', 0.0):.1f}%" if attendance_summary.get('average') is not None else "Class average attendance: not available",
            ],
            "tool_trace": tool_trace + ["build_attendance_summary"],
            "student_name": None,
        }

    if any(keyword in question_lower for keyword in ["student", "profile", "trajectory", "progress", "recommendation"]) or detected_student:
        if not detected_student:
            return {
                "intent": "student_clarification",
                "answer": "I can analyze an individual student, but I need a student name or selection first.",
                "actions": available_names[:8],
                "highlights": ["Choose a student from the dropdown or mention the name in your question."],
                "tool_trace": tool_trace,
                "student_name": None,
            }

        profile = get_student_profile(detected_student, str(CSV_PATH))
        tool_trace.append("get_student_profile")

        if "error" in profile:
            return {
                "intent": "student_lookup_failed",
                "answer": profile["error"],
                "actions": [],
                "highlights": [],
                "tool_trace": tool_trace,
                "student_name": detected_student,
            }

        personal = profile["personal"]
        trajectory = profile["trajectory"]
        recommendations = profile["recommendations"]
        comparison = profile["comparison"]

        answer = (
            f"{personal['name']} is ranked #{personal['rank']} with an average of {personal['average']:.1f} "
            f"and grade {personal['grade']}. The current trajectory is {trajectory['direction'].replace('📈', '').replace('📉', '').replace('➡️', '').strip() or 'stable'}."
        )

        highlights = [
            f"Risk level: {personal['risk']}",
            f"Vs class average: {comparison['vs_class_avg']:+.1f}",
            f"Percentile rank: {comparison['percentile_rank']:.1f}",
            f"Trajectory horizon: {trajectory['prediction_horizon']}",
        ]

        if profile.get("attendance"):
            highlights.insert(
                1,
                f"Attendance: {profile['attendance']['percentage']:.1f}% ({profile['attendance']['status']} attendance)",
            )
            actions = stringify_actions(recommendations.get("priority_actions", [])) + recommendations.get("personalized_tips", [])
            actions.insert(0, f"Attendance benchmark: class average {profile['attendance']['class_average']:.1f}%")
        else:
            actions = stringify_actions(recommendations.get("priority_actions", [])) + recommendations.get("personalized_tips", [])

        return {
            "intent": "student_analysis",
            "answer": answer,
            "actions": actions,
            "highlights": highlights,
            "tool_trace": tool_trace,
            "student_name": detected_student,
        }

    if any(keyword in question_lower for keyword in ["subject", "weakest", "strongest", "focus"]):
        subject_intelligence = payload.get("subject_intelligence", {})
        ai_brief = payload.get("ai_brief", {})
        weakest_subject = min(subject_intelligence.items(), key=lambda item: item[1]["average"])[0] if subject_intelligence else "the cohort"
        strongest_subject = max(subject_intelligence.items(), key=lambda item: item[1]["average"])[0] if subject_intelligence else "the cohort"

        answer = (
            f"Subject analysis shows {strongest_subject} leading performance, while {weakest_subject} needs the most attention. "
            f"The cohort momentum score is {ai_brief.get('momentum', {}).get('score', 0):.1f}."
        )

        return {
            "intent": "subject_analysis",
            "answer": answer,
            "actions": [item for item in ai_brief.get("actions", [])[:4]],
            "highlights": [item for item in ai_brief.get("insights", [])[:4]],
            "tool_trace": tool_trace,
            "student_name": None,
        }

    if any(keyword in question_lower for keyword in ["risk", "intervention", "support", "failing", "at risk"]):
        ai_brief = payload.get("ai_brief", {})
        risk_breakdown = ai_brief.get("risk_breakdown", {})
        intervention_candidates = ai_brief.get("intervention_candidates", [])

        answer = (
            f"There are {risk_breakdown.get('High', 0)} high-risk students, {risk_breakdown.get('Medium', 0)} medium-risk students, "
            f"and {risk_breakdown.get('Low', 0)} low-risk students."
        )

        return {
            "intent": "risk_analysis",
            "answer": answer,
            "actions": [f"{student['name']} - Avg {student['average']}" for student in intervention_candidates],
            "highlights": [item for item in ai_brief.get("actions", [])[:3]],
            "tool_trace": tool_trace,
            "student_name": None,
        }

    summary = payload.get("summary", {})
    ai_brief = payload.get("ai_brief", {})
    answer = (
        f"The cohort momentum is {ai_brief.get('momentum', {}).get('status', 'stable').lower()} "
        f"with a score of {ai_brief.get('momentum', {}).get('score', 0):.1f}. "
        f"Pass rate is {summary.get('pass_rate', 0):.1f}% and class average is {summary.get('class_average', 0):.1f}."
    )

    attendance_text = ""
    if attendance_summary.get("present"):
        attendance_text = (
            f" Attendance average is {attendance_summary.get('average', 0.0):.1f}% "
            f"with {attendance_summary.get('high_percentage', 0.0):.1f}% high attendance and "
            f"{attendance_summary.get('low_percentage', 0.0):.1f}% low attendance."
        )

    return {
        "intent": "cohort_brief",
        "answer": answer + attendance_text,
        "actions": [item for item in ai_brief.get("actions", [])[:4]],
        "highlights": [
            *[item for item in ai_brief.get("insights", [])[:3]],
            f"Attendance average: {attendance_summary.get('average', 0.0):.1f}%" if attendance_summary.get("average") is not None else "Attendance average: not available",
        ],
        "tool_trace": tool_trace + ["build_attendance_summary"],
        "student_name": None,
    }


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


@app.route("/dashboard/chat")
def chat_dashboard():
    """Dedicated AI chat interface for asking questions about student data."""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("chat.html", user=user)


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


def generate_student_chart(student_name, profile):
    # Set standard plot defaults
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    
    # 1. Subject marks vs Class Avg
    subjects = list(profile["subjects"].keys())
    student_marks = [profile["subjects"][sub]["marks"] for sub in subjects]
    class_avgs = [profile["subjects"][sub]["class_avg"] for sub in subjects]
    
    x = np.arange(len(subjects))
    width = 0.35
    
    ax1.bar(x - width/2, student_marks, width, label='Student', color='#0f9d7a')
    ax1.bar(x + width/2, class_avgs, width, label='Class Avg', color='#cbd5e0')
    ax1.set_title('Subject Performance Comparison', fontsize=10, fontweight='bold', color='#1a365d')
    ax1.set_ylabel('Marks (%)', fontsize=9)
    ax1.set_xticks(x)
    ax1.set_xticklabels(subjects, rotation=15, fontsize=8)
    ax1.set_ylim(0, 105)
    ax1.legend(fontsize=8)
    
    # 2. Performance Trajectory
    weeks = [point["week"] for point in profile["trajectory"]["trajectory"]]
    scores = [point["predicted_score"] for point in profile["trajectory"]["trajectory"]]
    
    # Prepend current average as Week 0
    current_avg = profile["personal"]["average"]
    weeks = [0] + weeks
    scores = [current_avg] + scores
    
    ax2.plot(weeks, scores, marker='o', linewidth=2, color='#2b6cb0', label='Predicted Trend')
    ax2.set_title('4-Week Predicted Trajectory', fontsize=10, fontweight='bold', color='#1a365d')
    ax2.set_xlabel('Weeks', fontsize=9)
    ax2.set_ylabel('Score (%)', fontsize=9)
    ax2.set_xticks(weeks)
    ax2.set_xticklabels([f"Current\n({current_avg}%)"] + [f"W{w}" for w in weeks[1:]], fontsize=8)
    ax2.set_ylim(max(0, min(scores)-10), min(100, max(scores)+10))
    ax2.legend(fontsize=8)
    
    plt.tight_layout()
    
    # Save to temp file
    temp_dir = tempfile.gettempdir()
    chart_path = os.path.join(temp_dir, f"chart_{student_name.replace(' ', '_')}_{int(datetime.now().timestamp())}.png")
    plt.savefig(chart_path, dpi=200)
    plt.close(fig)
    return chart_path


def generate_teacher_chart(payload):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    
    # 1. Subject Averages
    subjects = payload["subjects"]
    sub_intelligence = payload["subject_intelligence"]
    averages = [sub_intelligence[sub]["average"] for sub in subjects]
    
    ax1.bar(subjects, averages, color='#3182ce')
    ax1.set_title('Cohort Subject Averages', fontsize=10, fontweight='bold', color='#1a365d')
    ax1.set_ylabel('Average Marks (%)', fontsize=9)
    ax1.set_ylim(0, 105)
    for i, v in enumerate(averages):
        ax1.text(i, v + 2, f"{v}%", ha='center', fontsize=8, fontweight='bold')
    
    # 2. Risk Level Breakdown
    risk_data = payload["ai_brief"]["risk_breakdown"]
    categories = list(risk_data.keys())
    counts = list(risk_data.values())
    
    color_map = {'Low': '#48bb78', 'Medium': '#ecc94b', 'High': '#f56565'}
    bar_colors = [color_map.get(cat, '#cbd5e0') for cat in categories]
    
    ax2.bar(categories, counts, color=bar_colors, width=0.5)
    ax2.set_title('Cohort Risk Breakdown', fontsize=10, fontweight='bold', color='#1a365d')
    ax2.set_ylabel('Number of Students', fontsize=9)
    ax2.set_yticks(range(0, max(counts) + 2))
    for i, v in enumerate(counts):
        ax2.text(i, v + 0.1, str(v), ha='center', fontsize=9, fontweight='bold')
        
    plt.tight_layout()
    
    # Save to temp file
    temp_dir = tempfile.gettempdir()
    chart_path = os.path.join(temp_dir, f"cohort_chart_{int(datetime.now().timestamp())}.png")
    plt.savefig(chart_path, dpi=200)
    plt.close(fig)
    return chart_path


@app.route("/student/<student_name>/pdf")
def student_pdf(student_name):
    """Generate and download a PDF report for a single student."""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    
    # Access control
    if user["type"] == "student" and user["student_name"] != student_name:
        return render_template("error.html", message="Access denied"), 403
        
    profile = get_student_profile(student_name, str(CSV_PATH))
    if "error" in profile:
        return render_template("error.html", message=profile["error"]), 404
        
    # Get general class summary metrics
    payload = build_analysis_payload(str(CSV_PATH))
    class_average = payload["summary"]["class_average"]
    total_students = payload["summary"]["student_count"]
    
    # Try generating AI remarks
    ai_content = generate_student_pdf_remarks(student_name, profile)
    
    # Fallback to rule-based generation if LLM is unavailable
    if not ai_content:
        subjects = list(profile["subjects"].keys())
        sorted_subs = sorted(subjects, key=lambda s: profile["subjects"][s]["marks"])
        
        strengths = []
        improvements = []
        
        # Strengths
        for sub in reversed(sorted_subs):
            marks = profile["subjects"][sub]["marks"]
            if marks >= 75:
                strengths.append(f"Exhibits strong comprehension and performance in {sub} ({marks}%).")
            if len(strengths) >= 2:
                break
        if not strengths:
            highest_sub = sorted_subs[-1]
            strengths.append(f"Shows the highest relative performance in {highest_sub} ({profile['subjects'][highest_sub]['marks']}%).")
        
        # Improvements
        for sub in sorted_subs:
            marks = profile["subjects"][sub]["marks"]
            if marks < 50:
                improvements.append(f"Requires additional reinforcement and practice in {sub} ({marks}%).")
            if len(improvements) >= 2:
                break
        if not improvements:
            lowest_sub = sorted_subs[0]
            improvements.append(f"Opportunity to enhance scores in {lowest_sub} ({profile['subjects'][lowest_sub]['marks']}%).")
            
        if profile.get("attendance") and profile["attendance"]["percentage"] >= 90:
            strengths.append("Demonstrates excellent attendance habits, supporting learning continuity.")
        elif profile.get("attendance") and profile["attendance"]["percentage"] < 75:
            improvements.append("Regular attendance support is recommended to prevent gaps in core concepts.")
            
        risk_level = profile["personal"]["risk"]
        if risk_level == "High":
            risk_assessment = f"{student_name} is marked as high academic risk due to scores falling below passing thresholds in key subjects. Active engagement with the recommended 4-week study plan is crucial."
        elif risk_level == "Medium":
            risk_assessment = f"{student_name} is performing at moderate academic risk. Consistent practice in weaker subject areas will help stabilize performance and build confidence."
        else:
            risk_assessment = f"{student_name} maintains a low risk profile with stable academic performance across subjects. Continuous engagement with enrichment exercises is recommended."
            
        avg = profile["personal"]["average"]
        if avg >= 85:
            remarks = f"Excellent academic performance! {student_name} shows fantastic discipline, intellectual curiosity, and consistent effort. Keep up the outstanding work!"
        elif avg >= 70:
            remarks = "Good academic standing. Consistent work on areas of improvement, especially during the daily review sessions, will help reach the next tier of performance."
        else:
            remarks = "Requires focused academic support. With structured practice, regular attendance, and close adherence to the weekly study checklist, we expect significant improvement."
            
        ai_content = {
            "strengths": strengths[:3],
            "improvements": improvements[:3],
            "risk_assessment": risk_assessment,
            "teacher_remarks": remarks
        }
        
    chart_path = None
    try:
        chart_path = generate_student_chart(student_name, profile)
    except Exception as e:
        app.logger.error(f"Error generating chart: {e}")
        
    try:
        current_date = datetime.now().strftime("%B %d, %Y")
        html = render_template(
            "pdf_student_report.html",
            profile=profile,
            total_students=total_students,
            class_average=class_average,
            ai_content=ai_content,
            chart_path=chart_path,
            current_date=current_date
        )
        
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
        
        if not pdf.err:
            response = make_response(result.getvalue())
            response.headers['Content-Type'] = 'application/pdf'
            filename = f"{student_name.replace(' ', '_')}_performance_report.pdf"
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        else:
            return render_template("error.html", message="Failed to generate PDF document"), 500
    finally:
        if chart_path and os.path.exists(chart_path):
            try:
                os.remove(chart_path)
            except OSError:
                pass


@app.route("/dashboard/teacher/cohort-pdf")
def cohort_pdf():
    """Generate and download a PDF class performance report (Teachers/Admins only)."""
    user = get_current_user()
    if not user or user["type"] not in ["teacher", "admin"]:
        return render_template("error.html", message="Access denied"), 403
        
    payload = build_analysis_payload(str(CSV_PATH))
    ai_content = generate_teacher_pdf_cohort_report(payload)
    
    if not ai_content:
        class_average = payload["summary"]["class_average"]
        pass_rate = payload["summary"]["pass_rate"]
        passed = payload["summary"]["passed"]
        failed = payload["summary"]["failed"]
        risk = payload["ai_brief"]["risk_breakdown"]
        
        subject_intelligence = payload["subject_intelligence"]
        weakest_subject = min(subject_intelligence.items(), key=lambda item: item[1]["average"])[0]
        strongest_subject = max(subject_intelligence.items(), key=lambda item: item[1]["average"])[0]
        
        class_performance_report = (
            f"The cohort's overall academic average is {class_average}%, demonstrating a stable learning curve. "
            f"Subject-wise, student averages peak in {strongest_subject} and exhibit the lowest levels in {weakest_subject}. "
            f"Focusing instructional interventions on {weakest_subject} concepts will help raise the class average and "
            f"stabilize performance differences across subjects."
        )
        
        at_risk_report = (
            f"Analysis of student risk indicators shows that {risk.get('High', 0)} students are at high academic risk, "
            f"and {risk.get('Medium', 0)} are at medium academic risk. Common risk factors include subject averages below 50% "
            f"and low attendance rates (below 75%). Remediation plans should include after-school revision clubs, peer study cohorts, "
            f"and parent follow-up meetings to address attendance issues."
        )
        
        semester_summary = (
            f"This semester, a pass rate of {pass_rate}% was achieved, with {passed} students successfully passing all subjects "
            f"and {failed} students failing one or more subjects. The overall momentum is {payload['ai_brief']['momentum']['status']}, "
            f"scoring {payload['ai_brief']['momentum']['score']} out of 100. High-consistency performers maintain strong results, "
            f"and target interventions are slowly closing gaps in low-performing quartiles."
        )
        
        parent_meeting_report = (
            f"Key discussion guide for parent meetings:\n"
            f"1. Celebrate milestones for low-risk students, encouraging enrichment activities.\n"
            f"2. Present 4-week structured learning plans for high/medium-risk students, clarifying daily revision tasks.\n"
            f"3. Highlight attendance metrics, stressing its impact on concepts and scores.\n"
            f"4. Coordinate target goals for weak subjects, establishing check-in schedules."
        )
        
        ai_content = {
            "class_performance_report": class_performance_report,
            "at_risk_report": at_risk_report,
            "semester_summary": semester_summary,
            "parent_meeting_report": parent_meeting_report
        }
        
    chart_path = None
    try:
        chart_path = generate_teacher_chart(payload)
    except Exception as e:
        app.logger.error(f"Error generating teacher chart: {e}")
        
    try:
        current_date = datetime.now().strftime("%B %d, %Y")
        html = render_template(
            "pdf_teacher_report.html",
            payload=payload,
            ai_content=ai_content,
            chart_path=chart_path,
            current_date=current_date
        )
        
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
        
        if not pdf.err:
            response = make_response(result.getvalue())
            response.headers['Content-Type'] = 'application/pdf'
            filename = "class_cohort_performance_report.pdf"
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        else:
            return render_template("error.html", message="Failed to generate PDF document"), 500
    finally:
        if chart_path and os.path.exists(chart_path):
            try:
                os.remove(chart_path)
            except OSError:
                pass


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


@app.route("/api/agent", methods=["POST"])
def api_agent():
    """Answer a free-form analytics prompt by orchestrating existing helpers."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    student_name = str(payload.get("student_name", "")).strip() or None

    if not question:
        return jsonify({"error": "Please enter a question"}), 400

    if user["type"] == "student":
        student_name = user.get("student_name")
    elif student_name:
        student_name = student_name.strip()

    if user["type"] == "student" and student_name != user.get("student_name"):
        return jsonify({"error": "Access denied"}), 403

    from agent import get_agent_response
    return jsonify(get_agent_response(question, user, student_name, csv_path=str(CSV_PATH)))


@app.route("/api/teacher/marks-schema")
def teacher_marks_schema():
    """Return current marks schema for teacher upload guidance."""
    user = get_current_user()
    if not user or user["type"] not in ["teacher", "admin"]:
        return jsonify({"error": "Unauthorized"}), 401

    current_df = pd.read_csv(CSV_PATH)
    columns = [str(column).strip() for column in current_df.columns.tolist()]
    subjects = [column for column in columns if column != "Name" and column.lower() not in ATTENDANCE_COLUMN_NAMES]
    attendance_column = next((column for column in columns if column.lower() in ATTENDANCE_COLUMN_NAMES), None)

    return jsonify(
        {
            "columns": columns,
            "subjects": subjects,
            "attendance_present": attendance_column is not None,
            "attendance_column": attendance_column,
            "attendance_thresholds": {
                "high": 90,
                "low": 75,
            },
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
    columns = ["Name", *[f"Subject_{index}" for index in range(1, subject_count + 1)], "Attendance"]
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
            "attendance_summary": {
                "present": "Attendance" in cleaned_df.columns,
                "average": round(float(cleaned_df["Attendance"].mean()), 2) if "Attendance" in cleaned_df.columns else None,
                "high_count": int((cleaned_df["Attendance"] >= 90).sum()) if "Attendance" in cleaned_df.columns else 0,
                "low_count": int((cleaned_df["Attendance"] < 75).sum()) if "Attendance" in cleaned_df.columns else 0,
                "high_percentage": round(float((cleaned_df["Attendance"] >= 90).mean() * 100), 2) if "Attendance" in cleaned_df.columns else 0.0,
                "low_percentage": round(float((cleaned_df["Attendance"] < 75).mean() * 100), 2) if "Attendance" in cleaned_df.columns else 0.0,
                "high_threshold": 90,
                "low_threshold": 75,
            },
            "preview": cleaned_df.head(20).to_dict(orient="records"),
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
