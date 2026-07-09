from __future__ import annotations

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta


def get_subject_columns(data: pd.DataFrame) -> list[str]:
    return [column for column in data.columns if column != "Name"]


def format_student_snapshot(row: pd.Series) -> dict:
    return {
        "name": row["Name"],
        "total": int(row["Total"]),
        "average": round(float(row["Average"]), 2),
        "grade": row["Grade"],
        "rank": int(row["Rank"]),
        "result": row["Result"],
        "risk": row["RiskLevel"],
        "percentile": round(float(row["Percentile"]), 2),
    }


def grade(avg: float) -> str:
    if avg >= 90:
        return "A"
    if avg >= 80:
        return "B"
    if avg >= 70:
        return "C"
    if avg >= 60:
        return "D"
    return "F"


def pass_fail(row: pd.Series, subjects: list[str], pass_mark: int = 35) -> str:
    if all(row[subject] >= pass_mark for subject in subjects):
        return "Pass"
    return "Fail"


def build_rank_dataframe(csv_path: str = "students.csv") -> pd.DataFrame:
    data = pd.read_csv(csv_path)
    subjects = get_subject_columns(data)
    data["Total"] = data[subjects].sum(axis=1)
    data["Average"] = data["Total"] / len(subjects)
    data["Rank"] = data["Total"].rank(ascending=False, method="min").astype(int)
    data["Percentile"] = data["Total"].rank(pct=True).mul(100).round(2)

    # Base consistency from spread: low variance across subjects means stable scores.
    base_consistency = data[subjects].std(axis=1, ddof=0).rsub(100).clip(lower=0)

    # Quality adjustment: consistent low marks should not be treated as strong consistency.
    pass_ratio = data[subjects].ge(35).mean(axis=1)
    quality_factor = (data["Average"] / 100) * 0.6 + pass_ratio * 0.4
    data["Consistency"] = (base_consistency * quality_factor).clip(0, 100).round(2)

    data["Grade"] = data["Average"].apply(grade)
    data["Result"] = data.apply(lambda row: pass_fail(row, subjects), axis=1)
    data["RiskLevel"] = np.where(
        data["Result"] == "Fail",
        "High",
        np.where(data["Average"] < 65, "Medium", "Low"),
    )
    return data.sort_values(["Rank", "Name"]).reset_index(drop=True)


def build_subject_intelligence(data: pd.DataFrame, subjects: list[str]) -> dict:
    subject_intelligence = {}
    for subject in subjects:
        subject_data = data[subject]
        subject_intelligence[subject] = {
            "average": round(float(subject_data.mean()), 2),
            "highest": int(subject_data.max()),
            "lowest": int(subject_data.min()),
            "variance": round(float(subject_data.var(ddof=0)), 2),
        }
    return subject_intelligence


def build_score_bands(data: pd.DataFrame) -> dict:
    return {
        "90_plus": int((data["Average"] >= 90).sum()),
        "80_to_89": int(((data["Average"] >= 80) & (data["Average"] < 90)).sum()),
        "70_to_79": int(((data["Average"] >= 70) & (data["Average"] < 80)).sum()),
        "60_to_69": int(((data["Average"] >= 60) & (data["Average"] < 70)).sum()),
        "below_60": int((data["Average"] < 60).sum()),
    }


def build_ai_brief(data: pd.DataFrame, subject_intelligence: dict) -> dict:
    top_performers = data.nsmallest(3, "Rank")
    support_needed = data.sort_values(["Result", "Average"], ascending=[True, True]).head(3)

    strongest_subject = max(subject_intelligence.items(), key=lambda item: item[1]["average"])[0]
    weakest_subject = min(subject_intelligence.items(), key=lambda item: item[1]["average"])[0]
    sorted_subjects = sorted(
        subject_intelligence.items(), key=lambda item: item[1]["average"], reverse=True
    )

    pass_rate = (data["Result"] == "Pass").mean() * 100
    consistency_average = data["Consistency"].mean()
    momentum_score = float(min(100, round(pass_rate * 0.65 + consistency_average * 0.35, 2)))
    class_average = float(data["Average"].mean())
    median_average = float(data["Average"].median())
    score_spread = int(data["Total"].max() - data["Total"].min())

    risk_counts = data["RiskLevel"].value_counts().to_dict()
    risk_breakdown = {
        "Low": int(risk_counts.get("Low", 0)),
        "Medium": int(risk_counts.get("Medium", 0)),
        "High": int(risk_counts.get("High", 0)),
    }

    near_pass = data[(data["Result"] == "Fail") & (data["Average"] >= 55)].sort_values("Average", ascending=False)

    if momentum_score >= 85:
        momentum_status = "Excellent"
    elif momentum_score >= 70:
        momentum_status = "Stable"
    else:
        momentum_status = "Needs Attention"

    return {
        "momentum": {
            "score": momentum_score,
            "status": momentum_status,
        },
        "class_profile": {
            "pass_rate": round(pass_rate, 2),
            "class_average": round(class_average, 2),
            "median_average": round(median_average, 2),
            "consistency": round(float(consistency_average), 2),
            "score_spread": score_spread,
        },
        "risk_breakdown": risk_breakdown,
        "standout_performers": [format_student_snapshot(row) for _, row in top_performers.iterrows()],
        "intervention_candidates": [format_student_snapshot(row) for _, row in support_needed.iterrows()],
        "near_pass_students": [format_student_snapshot(row) for _, row in near_pass.head(2).iterrows()],
        "subject_focus": [
            {
                "subject": subject,
                "average": round(float(metrics["average"]), 2),
                "priority": "High" if index >= len(sorted_subjects) - 2 else "Watch",
            }
            for index, (subject, metrics) in enumerate(sorted_subjects)
        ],
        "narrative": (
            f"Class momentum is {momentum_status.lower()} with a pass rate of {pass_rate:.1f}%, "
            f"and an overall class average of {class_average:.1f}. "
            f"{strongest_subject} is currently leading performance, while {weakest_subject} "
            "requires immediate reinforcement to improve cohort balance."
        ),
        "insights": [
            f"Median average is {median_average:.1f}, showing the central performance band of the class.",
            f"Score spread is {score_spread} marks, indicating the gap between top and bottom performers.",
            f"High-risk learners: {risk_breakdown['High']} | Medium-risk learners: {risk_breakdown['Medium']}.",
            f"{weakest_subject} has the lowest subject average and should be prioritized in weekly revision blocks.",
        ],
        "actions": [
            f"Run a focused revision sprint in {weakest_subject} for bottom-quartile students.",
            "Pair high-consistency toppers with medium-risk students for peer mentoring cohorts.",
            "Set weekly micro-assessments and track movement in percentile and risk level.",
            "Publish a 14-day intervention tracker for high-risk students and review outcomes every week.",
        ],
    }


def build_analysis_payload(csv_path: str = "students.csv") -> dict:
    data = build_rank_dataframe(csv_path)
    subjects = get_subject_columns(pd.read_csv(csv_path))
    subject_intelligence = build_subject_intelligence(data, subjects)
    score_bands = build_score_bands(data)
    ai_brief = build_ai_brief(data, subject_intelligence)

    subject_toppers = {}
    for subject in subjects:
        topper = data.loc[data[subject].idxmax()]
        subject_toppers[subject] = {
            "name": topper["Name"],
            "marks": int(topper[subject]),
        }

    payload = {
        "students": data.to_dict(orient="records"),
        "top_3": data.head(3)[["Name", "Total", "Rank", "Grade"]].to_dict(orient="records"),
        "summary": {
            "class_average": round(float(data["Average"].mean()), 2),
            "highest_total": int(data["Total"].max()),
            "lowest_total": int(data["Total"].min()),
            "passed": int((data["Result"] == "Pass").sum()),
            "failed": int((data["Result"] == "Fail").sum()),
            "student_count": int(len(data)),
            "pass_rate": round(float((data["Result"] == "Pass").mean() * 100), 2),
            "avg_consistency": round(float(data["Consistency"].mean()), 2),
        },
        "grade_distribution": data["Grade"].value_counts().sort_index().to_dict(),
        "result_distribution": data["Result"].value_counts().to_dict(),
        "subject_toppers": subject_toppers,
        "subject_intelligence": subject_intelligence,
        "score_bands": score_bands,
        "ai_brief": ai_brief,
        "subjects": subjects,
    }
    return payload


def show_visualizations(data: pd.DataFrame, subjects: list[str]) -> None:
    plt.figure(figsize=(10, 6))
    plt.bar(data["Name"], data["Total"], color="skyblue")
    plt.title("Student Total Marks Analysis")
    plt.xlabel("Students")
    plt.ylabel("Total Marks")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    grade_counts = data["Grade"].value_counts()
    plt.figure(figsize=(6, 6))
    plt.pie(
        grade_counts,
        labels=grade_counts.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=["#2a9d8f", "#457b9d", "#e9c46a", "#f4a261", "#e76f51"],
    )
    plt.title("Grade Distribution")
    plt.show()

    result_counts = data["Result"].value_counts()
    plt.figure(figsize=(6, 6))
    plt.pie(
        result_counts,
        labels=result_counts.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=["#3a86ff", "#ef476f"],
    )
    plt.title("Pass/Fail Analysis")
    plt.show()

    data.plot(x="Name", y=subjects, kind="bar", figsize=(10, 6))
    plt.title("Marks in Each Subject")
    plt.xlabel("Students")
    plt.ylabel("Marks")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def generate_performance_trajectory(avg_score: float, consistency: float, risk_level: str) -> dict:
    """Predict future performance trend using ML-inspired logic."""
    # Create a simple performance trajectory model
    weeks_ahead = 4
    trajectory_points = []
    
    current_score = avg_score
    for week in range(1, weeks_ahead + 1):
        # Trajectory influenced by consistency and risk
        stability_factor = consistency / 100  # 0 to 1
        trend_direction = 1 if risk_level == "Low" else (-0.5 if risk_level == "High" else 0.2)

        # Confidence should reflect both stability and performance quality.
        avg_factor = avg_score / 100
        risk_penalty = 0.12 if risk_level == "High" else (0.06 if risk_level == "Medium" else 0.0)
        confidence_raw = (stability_factor * 0.55) + (avg_factor * 0.45) - risk_penalty
        confidence_score = float(np.clip(35 + confidence_raw * 65, 35, 95))
        
        # Predict small week-over-week changes
        weekly_change = trend_direction * (1 - stability_factor) 
        predicted_score = current_score + (weekly_change * week * 0.5)
        predicted_score = max(0, min(100, predicted_score))  # Clamp to 0-100
        
        trajectory_points.append({
            "week": week,
            "predicted_score": round(float(predicted_score), 1),
            "confidence": round(float(confidence_score), 1)
        })
    
    # Determine trajectory direction
    if trajectory_points[-1]["predicted_score"] > avg_score + 2:
        direction = "📈 Improving"
    elif trajectory_points[-1]["predicted_score"] < avg_score - 2:
        direction = "📉 Declining"
    else:
        direction = "➡️ Stable"
    
    return {
        "current_score": round(avg_score, 1),
        "direction": direction,
        "trajectory": trajectory_points,
        "prediction_horizon": "Next 4 weeks"
    }


def generate_recommendations(student_row: pd.Series, subjects: list[str], subject_intelligence: dict, all_students_avg: float) -> dict:
    """Generate personalized AI recommendations for a student."""
    name = student_row["Name"]
    avg = student_row["Average"]
    risk = student_row["RiskLevel"]
    result = student_row["Result"]
    
    recommendations = []
    priority_actions = []
    
    # Subject-level recommendations
    student_subject_scores = {subject: student_row[subject] for subject in subjects}
    sorted_subjects = sorted(student_subject_scores.items(), key=lambda x: x[1])
    
    weakest = sorted_subjects[0][0]
    weakest_score = sorted_subjects[0][1]
    strongest = sorted_subjects[-1][0]
    strongest_score = sorted_subjects[-1][1]
    
    # Generate context-specific recommendations
    if result == "Fail":
        priority_actions.append({
            "action": "🚨 Critical: Immediate intervention needed",
            "details": f"Focus on passing mark (35+) in all subjects. Start with {weakest} (current: {weakest_score})"
        })
        recommendations.append(f"Complete all practice tests for {weakest} to build confidence")
        recommendations.append(f"Attend after-school sessions focusing on key topics in failed subjects")
    
    if avg < 50:
        priority_actions.append({
            "action": "⚠️ High Priority: Comprehensive support",
            "details": "Requires personalized tutoring and structured study plan"
        })
        recommendations.append("Create a daily study schedule with 2-hour focused sessions")
        recommendations.append(f"Use {strongest} as a foundation to build momentum in other subjects")
    elif avg < 65:
        priority_actions.append({
            "action": "📌 Medium Priority: Targeted improvement",
            "details": f"Close gaps in {weakest}. Current: {weakest_score}, Target: 65+"
        })
        recommendations.append(f"Consolidate concepts in {weakest} using practice problems")
    else:
        if avg >= 85:
            priority_actions.append({
                "action": "⭐ Excellence Track: Maintain & Enhance",
                "details": f"Strong performance in {strongest}. Share knowledge with peers"
            })
            recommendations.append(f"Consider peer tutoring in {strongest} to reinforce mastery")
        else:
            priority_actions.append({
                "action": "✅ On Track: Focus on consistency",
                "details": f"Reduce subject variance. Gap between {strongest} ({strongest_score}) and {weakest} ({weakest_score})"
            })
        recommendations.append(f"Reduce variance by strengthening {weakest}")
    
    # Consistency-based recommendations
    consistency = student_row.get("Consistency", 50)
    if consistency < 40:
        recommendations.append("Study habits are inconsistent. Try the Pomodoro technique (25-min focused sessions)")
    
    # Performance vs class average
    if avg < all_students_avg - 10:
        recommendations.append("You're below average. Join peer study groups or seek additional tutoring")
    elif avg > all_students_avg + 15:
        recommendations.append("Exceptional performance! Consider advanced topics to challenge yourself")
    
    return {
        "student_name": name,
        "current_average": round(avg, 1),
        "risk_level": risk,
        "weakest_subject": weakest,
        "strongest_subject": strongest,
        "priority_actions": priority_actions,
        "personalized_tips": recommendations[:4],  # Top 4 recommendations
        "next_review_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    }


def generate_intervention_plan(student_row: pd.Series, subjects: list[str], subject_intelligence: dict) -> dict:
    """Create a detailed intervention plan for at-risk students."""
    name = student_row["Name"]
    result = student_row["Result"]
    risk = student_row["RiskLevel"]
    avg = student_row["Average"]
    
    if result == "Pass" and risk == "Low":
        return {"status": "not_needed", "message": "Student performing well, no intervention required"}
    
    # Determine intervention level
    if result == "Fail":
        intervention_level = "Critical"
        target_score = 40
    elif risk == "High":
        intervention_level = "High"
        target_score = 60
    else:
        intervention_level = "Medium"
        target_score = 70
    
    # Subject-level focus
    student_scores = {s: student_row[s] for s in subjects}
    failed_subjects = [s for s in subjects if student_row[s] < 35]
    weak_subjects = [s for s in subjects if student_row[s] < 50]
    
    # Create 4-week plan
    weeks = []
    for week in range(1, 5):
        focus_subjects = failed_subjects if failed_subjects else weak_subjects[:2]
        weeks.append({
            "week": week,
            "focus": f"Week {week}: {', '.join(focus_subjects[:2])} deep dive",
            "activities": [
                f"Daily 1.5h focused sessions in {focus_subjects[0] if focus_subjects else 'weak subjects'}",
                "2x weekly assessment tests",
                "Peer review of concepts with peer mentor"
            ],
            "checkpoint": f"Mini-test in {focus_subjects[0] if focus_subjects else 'all subjects'}"
        })
    
    return {
        "student_name": name,
        "intervention_level": intervention_level,
        "current_average": round(avg, 1),
        "target_score": target_score,
        "failed_subjects": failed_subjects,
        "weak_subjects": weak_subjects,
        "4week_plan": weeks,
        "mentor_assigned": True,
        "weekly_review": True,
        "escalation_threshold": 45  # Score below this triggers escalation
    }


def get_student_profile(student_name: str, csv_path: str = "students.csv") -> dict:
    """Generate a comprehensive profile for a specific student."""
    data = build_rank_dataframe(csv_path)
    subjects = get_subject_columns(pd.read_csv(csv_path))
    subject_intelligence = build_subject_intelligence(data, subjects)
    
    student = data[data["Name"] == student_name]
    if student.empty:
        return {"error": "Student not found"}
    
    student_row = student.iloc[0]
    all_students_avg = data["Average"].mean()
    
    # Compile profile
    profile = {
        "personal": format_student_snapshot(student_row),
        "subjects": {subject: {
            "marks": int(student_row[subject]),
            "status": "Pass" if student_row[subject] >= 35 else "Fail",
            "percentile": round((data[subject] <= student_row[subject]).sum() / len(data) * 100, 1),
            "class_avg": round(subject_intelligence[subject]["average"], 1)
        } for subject in subjects},
        "trajectory": generate_performance_trajectory(student_row["Average"], student_row["Consistency"], student_row["RiskLevel"]),
        "recommendations": generate_recommendations(student_row, subjects, subject_intelligence, all_students_avg),
        "intervention": generate_intervention_plan(student_row, subjects, subject_intelligence),
        "comparison": {
            "vs_class_avg": round(student_row["Average"] - all_students_avg, 1),
            "above_median": student_row["Average"] > data["Average"].median(),
            "percentile_rank": round((data["Average"] <= student_row["Average"]).sum() / len(data) * 100, 1)
        }
    }
    
    return profile


if __name__ == "__main__":
    ranked = build_rank_dataframe("students.csv")
    payload = build_analysis_payload("students.csv")
    subjects = payload["subjects"]

    print("\nStudent Rank List\n")
    print(ranked[["Name", *subjects, "Total", "Average", "Grade", "Result", "Rank"]])

    print("\nTop 3 Students\n")
    print(ranked.head(3)[["Name", "Total", "Rank", "Grade"]])

    print("\nClass Statistics")
    print("Class Average Marks:", payload["summary"]["class_average"])
    print("Highest Marks:", payload["summary"]["highest_total"])
    print("Lowest Marks:", payload["summary"]["lowest_total"])
    print("Total Passed Students:", payload["summary"]["passed"])
    print("Total Failed Students:", payload["summary"]["failed"])

    print("\nSubject Toppers")
    for subject, topper in payload["subject_toppers"].items():
        print(subject, "Topper:", topper["name"], "-", topper["marks"])

    show_visualizations(ranked, subjects)