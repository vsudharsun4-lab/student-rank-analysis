from __future__ import annotations

import os
import json
import re
import requests
import pandas as pd
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

# Load configuration from environment variables
load_dotenv()

openai_key = os.environ.get("OPENAI_API_KEY")
openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

gemini_key = os.environ.get("GEMINI_API_KEY")
gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

client = None
if openai_key:
    client = OpenAI(api_key=openai_key)


def sanitize_for_json(obj):
    """Recursively convert numpy types and NaNs to standard JSON serializable python types."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(x) for x in obj]
    elif isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif pd.isna(obj):
        return None
    return obj


def build_academic_context(user_type: str, student_name: str | None, csv_path: str) -> str:
    """Build a text context of the student dataset for the LLM prompt."""
    from rank_analysis import build_analysis_payload, build_rank_dataframe
    
    try:
        df = build_rank_dataframe(csv_path)
        payload = build_analysis_payload(csv_path)
        
        context = []
        context.append("--- ACADEMIC DATASET CONTEXT ---")
        
        if user_type == "student":
            # Access control: only include this student's details
            if not student_name:
                return "Student name not provided. Access denied."
            student_row = df[df["Name"].str.lower() == student_name.lower()]
            if not student_row.empty:
                row = student_row.iloc[0]
                context.append(f"You are talking to student: {row['Name']}")
                context.append(f"Student Profile:")
                context.append(f"- Name: {row['Name']}")
                context.append(f"- Rank: #{row['Rank']}")
                context.append(f"- Average: {row['Average']:.1f}%")
                context.append(f"- Grade: {row['Grade']}")
                context.append(f"- Result: {row['Result']}")
                context.append(f"- Risk Level: {row['RiskLevel']}")
                if "Attendance" in row and not pd.isna(row["Attendance"]):
                    context.append(f"- Attendance: {row['Attendance']:.1f}%")
                
                # Subject scores
                subjects = [c for c in df.columns if c not in ["Name", "Total", "Average", "Rank", "Percentile", "Consistency", "Grade", "Result", "RiskLevel", "Attendance", "AttendanceStatus"]]
                context.append("Subject Marks:")
                for sub in subjects:
                    context.append(f"  * {sub}: {row[sub]}% (Class Avg: {payload['subject_intelligence'][sub]['average']:.1f}%)")
            else:
                context.append(f"Student user '{student_name}' details not found in database.")
        else:
            # Teacher / Admin: include full cohort context
            context.append("User Role: Educator/Administrator (Full Access)")
            context.append("Cohort Summary:")
            context.append(f"- Total Students: {payload['summary']['student_count']}")
            context.append(f"- Class Average: {payload['summary']['class_average']:.1f}%")
            context.append(f"- Pass Rate: {payload['summary']['pass_rate']:.1f}%")
            context.append(f"- Passed: {payload['summary']['passed']} | Failed: {payload['summary']['failed']}")
            
            risk = payload["ai_brief"]["risk_breakdown"]
            context.append(f"- Risk Breakdown: High Risk: {risk.get('High', 0)}, Medium Risk: {risk.get('Medium', 0)}, Low Risk: {risk.get('Low', 0)}")
            
            context.append("\nSubject Averages & Toppers:")
            for sub in payload["subjects"]:
                intel = payload["subject_intelligence"][sub]
                topper = payload["subject_toppers"][sub]
                context.append(f"- {sub}: Avg {intel['average']:.1f}% | Highest: {intel['highest']}% | Lowest: {intel['lowest']}% | Topper: {topper['name']} ({topper['marks']}%)")
                
            context.append("\nFull Student Roster:")
            context.append("Rank | Name | Average | Grade | Result | Risk | Attendance")
            for _, row in df.iterrows():
                att = f"{row['Attendance']:.1f}%" if "Attendance" in row and not pd.isna(row["Attendance"]) else "N/A"
                context.append(f"#{row['Rank']} | {row['Name']} | {row['Average']:.1f}% | {row['Grade']} | {row['Result']} | {row['RiskLevel']} Risk | {att}")
                
        context.append("--------------------------------")
        return "\n".join(context)
    except Exception as e:
        return f"Error building context: {str(e)}"


def _local_fallback(question: str, user: dict, student_name: str | None, csv_path: str) -> dict:
    """Offline rule-based fallback when no API key is available."""
    import re as _re
    from rank_analysis import build_analysis_payload, build_rank_dataframe
    
    question_lower = question.lower().strip()
    tool_trace = ["local_fallback"]
    
    # 1. Greetings & Conversational Questions
    if question_lower in ["hi", "hello", "hey", "greetings"]:
        return {
            "intent": "greeting",
            "answer": "Hello! I am your **EduRank AI Agent**.\n\nI can act as a **Student Data Agent** to answer questions about student grades and averages, or a **Learning Assistant** to explain study concepts like loops, SQL, and CNNs. How can I assist you today?",
            "actions": ["Ask: 'What is my average?'", "Ask: 'Explain Python loops.'"],
            "highlights": ["EduRank AI Agent Active", "Running in offline mode"],
            "tool_trace": tool_trace,
            "student_name": None
        }
        
    if "how are you" in question_lower:
        return {
            "intent": "greeting",
            "answer": "I'm doing great, thank you! I'm fully loaded and ready to help you analyze student performance or explore academic topics. What are we studying today?",
            "actions": ["Ask: 'Explain CNN.'", "Ask: 'Give me 10 SQL interview questions.'"],
            "highlights": ["Agent Online", "Ready to assist"],
            "tool_trace": tool_trace,
            "student_name": None
        }
        
    if "what can you do" in question_lower or "help" in question_lower:
        return {
            "intent": "greeting",
            "answer": (
                "I can assist you with two primary activities:\n\n"
                "1. **Student Data Agent**: Retrieves metrics, averages, ranks, and subject intelligence from the class database.\n"
                "2. **Learning Assistant**: Explains programming concepts, SQL syntax, neural networks, or structures study plans.\n\n"
                "Try asking: *'What is my average?'*, *'Explain Python loops'*, or *'Give me 10 SQL interview questions'*."
            ),
            "actions": ["Ask about student data", "Ask a programming query"],
            "highlights": ["Data Agent capabilities", "Learning Assistant tutorials"],
            "tool_trace": tool_trace,
            "student_name": None
        }

    # 2. Hardcoded Pre-programmed High-Fidelity Study Tutorials
    if "python loops" in question_lower or "explain loop" in question_lower:
        answer = (
            "A loop is used to execute a block of code repeatedly as long as a specified condition is met. "
            "Python offers two main loop types: `for` loops and `while` loops.\n\n"
            "### Loop Execution Flowchart:\n"
            "```text\n"
            "           [Start]\n"
            "              │\n"
            "              ▼\n"
            "      /===============\\\n"
            "     /  Is condition   \\─── No ───► [Exit Loop]\n"
            "     \\    satisfied?   /\n"
            "      \\===============/\n"
            "              │\n"
            "             Yes\n"
            "              │\n"
            "              ▼\n"
            "       [Execute Code]\n"
            "              │\n"
            "              ▼\n"
            "      [Update Variables]\n"
            "              │\n"
            "              └─────────────────────────( Loop Back )\n"
            "```\n\n"
            "### 1. `for` Loop (Definite Iteration)\n"
            "Used to iterate over a sequence (list, dictionary, tuple, set, or string).\n"
            "```python\n"
            "students = ['chitahmabaram', 'gokul', 'linin']\n"
            "for student in students:\n"
            "    print(f'Active Student: {student}')\n"
            "```\n\n"
            "### 2. `while` Loop (Indefinite Iteration)\n"
            "Executes a block of code as long as the condition remains true.\n"
            "```python\n"
            "count = 1\n"
            "while count <= 3:\n"
            "    print(f'Count is: {count}')\n"
            "    count += 1\n"
            "```\n\n"
            "### Tracing count <= 3 Variable State:\n"
            "| Iteration | Variable `count` | Condition Check `count <= 3` | Action Performed | Value after increment |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
            "| Start | 1 | - | - | - |\n"
            "| 1st | 1 | 1 <= 3 (True) | Print 'Count is: 1' | 2 |\n"
            "| 2nd | 2 | 2 <= 3 (True) | Print 'Count is: 2' | 3 |\n"
            "| 3rd | 3 | 3 <= 3 (True) | Print 'Count is: 3' | 4 |\n"
            "| Exit | 4 | 4 <= 3 (False) | Loop terminates | 4 |"
        )
        return {
            "intent": "learning_assistant",
            "answer": answer,
            "actions": ["Practice loops in your python terminal.", "Learn loop nesting & comprehensions."],
            "highlights": ["for loop is sequence-based", "while loop is condition-based"],
            "tool_trace": tool_trace,
            "student_name": None
        }
        
    elif "sql interview questions" in question_lower or "sql questions" in question_lower:
        answer = (
            "Here are essential SQL interview questions with brief answers and join visualisations:\n\n"
            "### Visualizing SQL JOIN Types:\n"
            "| Join Type | Left Table Match | Right Table Match | If No Match | Venn Diagram |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
            "| **INNER JOIN** | Required | Required | Row is excluded | `[ A ∩ B ]` |\n"
            "| **LEFT JOIN** | Always returned | Optional | NULL for Right | `[ A (∩ B) ]` |\n"
            "| **RIGHT JOIN** | Optional | Always returned | NULL for Left | `[ (A ∩) B ]` |\n\n"
            "### Core Questions:\n"
            "1. **What is the difference between INNER JOIN and LEFT JOIN?**\n"
            "   * *Answer*: `INNER JOIN` returns rows when there is a match in both tables. `LEFT JOIN` returns all rows from the left table, and matched rows from the right table (NULL otherwise).\n"
            "2. **What is a Primary Key vs. Foreign Key?**\n"
            "   * *Answer*: A Primary Key uniquely identifies each record in a table. A Foreign Key is a field in one table that refers to the Primary Key in another table.\n"
            "3. **Explain the GROUP BY clause.**\n"
            "   * *Answer*: Groups rows that have the same values into summary rows (e.g., finding the sum or average per category).\n"
            "4. **What is a Subquery?**\n"
            "   * *Answer*: A query nested inside another query (e.g., inside SELECT, INSERT, UPDATE, or DELETE).\n"
            "5. **What is the difference between UNION and UNION ALL?**\n"
            "   * *Answer*: `UNION` combines result sets and removes duplicates. `UNION ALL` combines them and keeps duplicates."
        )
        return {
            "intent": "learning_assistant",
            "answer": answer,
            "actions": ["Write queries to practice joins.", "Test subqueries on a local database."],
            "highlights": ["INNER vs LEFT Join differences", "UNION vs UNION ALL aggregates"],
            "tool_trace": tool_trace,
            "student_name": None
        }
        
    elif "explain cnn" in question_lower or "what is cnn" in question_lower:
        answer = (
            "A **Convolutional Neural Network (CNN)** is a class of deep neural network most commonly applied to analyze visual imagery. "
            "CNNs use a mathematical operation called **convolution** in place of general matrix multiplication in at least one of their layers.\n\n"
            "### CNN Structure Diagram:\n"
            "```text\n"
            "[Input Image] ──► [Conv Layer] ──► [Pooling Layer] ──► [FC Layer] ──► [Output Class]\n"
            "(Raw Pixels)       (Finds Edges)    (Shrinks Size)     (Classifies)    (e.g., Cat)\n"
            "```\n\n"
            "### Tracing Feature Extraction (Convolution operation):\n"
            "Imagine applying a 3x3 filter (kernel) to a region of the image:\n"
            "```text\n"
            "Image Patch (3x3)      Kernel (3x3)           Output Pixel\n"
            "  [ 1  0  1 ]            [ 1  0 -1 ]\n"
            "  [ 0  1  0 ]    *       [ 1  0 -1 ]   ───►  (1*1) + (0*0) + (1*-1) ... = 2\n"
            "  [ 1  0  1 ]            [ 1  0 -1 ]\n"
            "```\n\n"
            "### Core CNN Layers:\n"
            "1. **Convolutional Layer**: Applies filters (kernels) to the input image to extract feature maps (like edges, textures, or shapes).\n"
            "2. **Activation Function (ReLU)**: Introduces non-linearity to the network, replacing all negative pixel values with zero.\n"
            "3. **Pooling Layer**: Reduces the spatial size (width and height) of the feature maps (commonly using Max Pooling), reducing computation and parameters.\n"
            "4. **Fully Connected Layer (FC)**: Connects all neurons from the previous layer to the output classes to make the final classification."
        )
        return {
            "intent": "learning_assistant",
            "answer": answer,
            "actions": ["Implement a basic CNN using PyTorch or Keras.", "Explore pooling vs convolutional strides."],
            "highlights": ["Uses convolution filters", "Max pooling reduces size", "Classified via FC layer"],
            "tool_trace": tool_trace,
            "student_name": None
        }
        
    elif "study plan for machine learning" in question_lower or "study plan for ml" in question_lower or "learn machine learning" in question_lower:
        answer = (
            "Here is a structured 12-week study plan to master Machine Learning fundamentals:\n\n"
            "### ML Study Plan Roadmap:\n"
            "```text\n"
            "[Foundations] ──► [Supervised] ──► [Unsupervised] ──► [Deploy/Pipelines]\n"
            " (Week 1-4)        (Week 5-8)        (Week 9-10)         (Week 11-12)\n"
            "```\n\n"
            "### Week 1-4: Core Foundations\n"
            "- **Mathematics**: Linear Algebra (vectors, matrices), Calculus (derivatives, gradients), Probability & Statistics.\n"
            "- **Programming**: Python basics, Numpy, Pandas for data processing.\n\n"
            "### Week 5-8: Supervised Learning\n"
            "- **Regression**: Linear and Logistic Regression.\n"
            "- **Classification**: Decision Trees, Random Forests, Support Vector Machines (SVM), and Naive Bayes.\n"
            "- **Evaluation**: Cross-validation, Precision/Recall, ROC-AUC metrics.\n\n"
            "### Week 9-10: Unsupervised Learning & Preprocessing\n"
            "- **Clustering**: K-Means clustering, Hierarchical clustering.\n"
            "- **Dimensionality Reduction**: Principal Component Analysis (PCA).\n"
            "- **Feature Engineering**: Handling missing values, scaling, encoding.\n\n"
            "### Week 11-12: Frameworks & Capstone\n"
            "- Learn **Scikit-Learn** for modeling and building end-to-end pipelines.\n"
            "- Deploy a model to a cloud endpoint or create a local streamlit UI."
        )
        return {
            "intent": "learning_assistant",
            "answer": answer,
            "actions": ["Follow this 12-week schedule.", "Build regression model as Week 5 project."],
            "highlights": ["Math & python foundations first", "Supervised and unsupervised milestones"],
            "tool_trace": tool_trace,
            "student_name": None
        }

    # 3. Dynamic Topic Explanations fallback (Explain X or What is X)
    match_explain = _re.search(r'(?:explain|what is|how does|tell me about)\s+([^?.!]+)', question_lower)
    if match_explain:
        topic = match_explain.group(1).strip().title()
        
        # Avoid overriding student data calculations
        if not any(kw in question_lower for kw in ["average", "avg", "grade", "performance", "score", "marks", "topper", "low scorer", "attendance"]):
            answer = (
                f"Here is a structured overview of **{topic}**:\n\n"
                f"### 1. Introduction to {topic}\n"
                f"**{topic}** represents a key domain in modern computing and academic curriculum. Understanding its fundamentals "
                f"is crucial for building practical problem-solving skills and advancing your technical proficiency.\n\n"
                f"### 2. Core Concepts\n"
                f"- **Syntax and Grammar**: Establishing the foundation and basic blocks of {topic}.\n"
                f"- **Design Patterns**: Applying industry-standard design paradigms and rules.\n"
                f"- **Optimization**: Maximizing performance, complexity efficiency, and readability.\n\n"
                f"### 3. Study Recommendations\n"
                f"- Start with basic code sandboxes or theoretical modules.\n"
                f"- Build minor projects (e.g. CLI utilities, single-page scripts) to apply the concepts.\n\n"
                f"---\n"
                f"*Note: For personalized, real-time AI tutorials and interactive code snippets on **{topic}**, "
                f"please configure a `GEMINI_API_KEY` or `OPENAI_API_KEY` in the `.env` file.*"
            )
            return {
                "intent": "learning_assistant",
                "answer": answer,
                "actions": [f"Learn more about {topic}.", "Configure API keys for live AI responses."],
                "highlights": [f"Overview: {topic}", "API configuration recommended"],
                "tool_trace": tool_trace,
                "student_name": None
            }

    # 4. Student Dataset Queries via Pandas
    try:
        df = build_rank_dataframe(csv_path)
        payload = build_analysis_payload(csv_path)
        students = payload.get("students", [])
        available_names = [s["Name"] for s in students if s.get("Name")]
        
        def _detect_name(q: str) -> str | None:
            for name in sorted(available_names, key=len, reverse=True):
                if _re.search(_re.escape(name.lower()), q.lower()):
                    return name
            return None

        user_type = user.get("type", "teacher")
        user_student_name = user.get("student_name")
        
        # Access control
        if user_type == "student":
            detected_student = user_student_name
        else:
            detected_student = student_name or _detect_name(question)

        # Average query for single student
        if detected_student and any(kw in question_lower for kw in ["average", "avg", "grade", "performance", "score", "marks"]):
            student_row = df[df["Name"].str.lower() == detected_student.lower()]
            if not student_row.empty:
                row = student_row.iloc[0]
                subjects = [c for c in df.columns if c not in ["Name", "Total", "Average", "Rank", "Percentile", "Consistency", "Grade", "Result", "RiskLevel", "Attendance", "AttendanceStatus"]]
                
                # Find strongest and weakest subjects
                subject_scores = {sub: row[sub] for sub in subjects}
                strongest_sub = max(subject_scores.items(), key=lambda x: x[1])
                weakest_sub = min(subject_scores.items(), key=lambda x: x[1])
                
                answer = (
                    f"Your average is **{row['Average']:.1f}%**.\n"
                    f"Your strongest subject is **{strongest_sub[0]}**.\n"
                    f"Your weakest subject is **{weakest_sub[0]}**."
                )
                
                return {
                    "intent": "student_data_agent",
                    "answer": answer,
                    "actions": [f"Review study schedule for {weakest_sub[0]}."],
                    "highlights": [f"Average: {row['Average']:.1f}%", f"Strongest: {strongest_sub[0]}"],
                    "tool_trace": tool_trace,
                    "student_name": row["Name"]
                }
                
        # Topper/low scorer query
        if any(kw in question_lower for kw in ["topper", "top student", "rank 1", "highest scorer"]):
            row = df.nsmallest(1, "Rank").iloc[0]
            return {
                "intent": "student_data_agent",
                "answer": f"{row['Name']} is the topper with an average of {row['Average']:.1f}% and rank #{row['Rank']}.",
                "actions": [f"Topper: {row['Name']}", f"Average: {row['Average']:.1f}%"],
                "highlights": [f"Rank #{row['Rank']}", f"Grade {row['Grade']}"],
                "tool_trace": tool_trace,
                "student_name": row["Name"]
            }

        if any(kw in question_lower for kw in ["low scorer", "lowest", "weakest student", "last rank"]):
            row = df.nsmallest(1, "Average").iloc[0]
            return {
                "intent": "student_data_agent",
                "answer": f"{row['Name']} is the lowest scorer with an average of {row['Average']:.1f}%.",
                "actions": [f"Student: {row['Name']}", f"Average: {row['Average']:.1f}%"],
                "highlights": [f"Rank #{row['Rank']}", f"Grade {row['Grade']}"],
                "tool_trace": tool_trace,
                "student_name": row["Name"]
            }

    except Exception:
        pass

    # Generic friendly conversation fallback
    answer = (
        "Hello! I am currently running in **Offline Mode** (without active LLM API credentials).\n\n"
        "I can answer queries about student grades, averages, toppers, and attendance, "
        "or explain specific concepts like loops, SQL, and CNNs.\n\n"
        "To enable full, open-ended conversational replies, please configure a `GEMINI_API_KEY` or `OPENAI_API_KEY` in the `.env` file."
    )
    return {
        "intent": "offline_mode",
        "answer": answer,
        "actions": ["Configure GEMINI_API_KEY in your .env file.", "Configure OPENAI_API_KEY in your .env file."],
        "highlights": ["Offline Fallback Active", "API Key setup required for custom questions"],
        "tool_trace": tool_trace,
        "student_name": None
    }


def get_agent_response(question: str, user: dict, student_name: str | None = None, csv_path: str = "students.csv") -> dict:
    """Unified entry point for conversational agent queries supporting OpenAI, Gemini, and offline fallbacks."""
    user_type = user.get("type", "teacher")
    user_student_name = user.get("student_name")

    # Access control: force search to own name for student users
    if user_type == "student":
        student_name = user_student_name

    # Build academic context
    context = build_academic_context(user_type, student_name, csv_path)

    system_instruction = (
        "You are EduRank AI, a professional academic assistant and learning tutor. "
        "You operate in two roles:\n"
        "1. **Student Data Agent** — Answer questions about the academic cohort using the injected data below. "
        "Pull data precisely. Never guess or invent scores.\n"
        "2. **Learning Assistant** — Teach programming (Python, SQL, ML, DL, math) with clear structured explanations.\n\n"
        f"{context}\n\n"
        "## Formatting Rules (MANDATORY — follow exactly like ChatGPT)\n\n"
        "ALWAYS format your responses using rich Markdown. Never return a plain wall of text.\n\n"
        "### Structure every response like this:\n"
        "- Use `##` or `###` headings to separate major sections.\n"
        "- Use **numbered lists** (`1. 2. 3.`) for sequential steps, processes, or ranked items.\n"
        "- Use **bullet lists** (`-`) for non-sequential items, features, or notes.\n"
        "- Use **bold** (`**term**`) to highlight key terms, concepts, and important values.\n"
        "- Use *italic* (`*text*`) for emphasis or definitions.\n"
        "- Use fenced code blocks with language tags for ALL code examples:\n"
        "  ```python\n"
        "  # your code here\n"
        "  ```\n"
        "- Use Markdown tables for comparisons, multiple data points, or structured data.\n"
        "- Use `inline code` for variable names, keywords, and short expressions.\n"
        "- Use `>` blockquotes for important tips, warnings, or analogies.\n\n"
        "### For concept/study explanations:\n"
        "1. Start with a **brief definition** (1-2 sentences).\n"
        "2. Give a **real-world analogy** to make it intuitive.\n"
        "3. Show a **step-by-step breakdown** with numbered steps.\n"
        "4. Include a **working code example** in a fenced code block.\n"
        "5. Show an **execution trace table** (use Markdown table) showing variable states.\n"
        "6. End with a **Key Takeaways** section using bullet points.\n\n"
        "At the very end, if applicable, include these exact sections:\n"
        "### Highlights\n"
        "- Key point 1\n"
        "- Key point 2\n\n"
        "### Action Items\n"
        "- Action 1\n"
        "- Action 2"
    )

    # Provider routing
    # Check Gemini first, then OpenAI, then fallback
    if gemini_key:
        # Call Gemini AI Studio API
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
        headers = {"Content-Type": "application/json"}
        prompt = f"{system_instruction}\n\nUser Question: {question}"
        body = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }
        try:
            res = requests.post(url, headers=headers, json=body, timeout=20)
            res.raise_for_status()
            res_json = res.json()
            answer_content = res_json["candidates"][0]["content"]["parts"][0]["text"]
            provider_trace = ["gemini_api"]
            
            return parse_llm_markdown_response(answer_content, provider_trace, student_name)
        except Exception as exc:
            # Fall back to OpenAI or local
            pass

    if openai_key and client:
        # Call OpenAI Chat Completion API
        try:
            response = client.chat.completions.create(
                model=openai_model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": question}
                ]
            )
            answer_content = response.choices[0].message.content
            provider_trace = ["openai_api"]
            return parse_llm_markdown_response(answer_content, provider_trace, student_name)
        except Exception:
            pass

    # Fall back to rule-based fallback if no API keys are set or if API requests fail
    return _local_fallback(question, user, student_name, csv_path)


def parse_llm_markdown_response(answer_content: str, tool_trace: list[str], student_name: str | None) -> dict:
    """Parse markdown response highlights and action items sections."""
    highlights = []
    actions = []
    clean_answer = answer_content

    highlights_match = re.search(r"### Highlights\n(.*?)(?=\n###|$)", answer_content, re.DOTALL | re.IGNORECASE)
    if highlights_match:
        highlights = [line.strip().lstrip("-* ").strip() for line in highlights_match.group(1).strip().split("\n") if line.strip()]
        clean_answer = clean_answer.replace(highlights_match.group(0), "")
        
    actions_match = re.search(r"### Action Items\n(.*?)(?=\n###|$)", answer_content, re.DOTALL | re.IGNORECASE)
    if actions_match:
        actions = [line.strip().lstrip("-* ").strip() for line in actions_match.group(1).strip().split("\n") if line.strip()]
        clean_answer = clean_answer.replace(actions_match.group(0), "")

    clean_answer = clean_answer.strip()

    return {
        "intent": "llm_agent_response",
        "answer": clean_answer,
        "actions": actions if actions else ["Review learning path options."],
        "highlights": highlights if highlights else ["Processed via LLM API."],
        "tool_trace": tool_trace,
        "student_name": student_name
    }


def generate_student_pdf_remarks(student_name: str, student_profile: dict) -> dict | None:
    """Generate structured AI remarks for the student performance report using Gemini or OpenAI."""
    sanitized_profile = sanitize_for_json(student_profile)
    prompt = (
        f"Generate a student analysis report in structured JSON format for student '{student_name}'.\n"
        f"Student Profile Data: {json.dumps(sanitized_profile)}\n\n"
        "You must return a raw JSON object with this exact key structure (no markdown wrap, just raw JSON):\n"
        "{\n"
        '  "strengths": ["list of 1-3 key strengths"],\n'
        '  "improvements": ["list of 1-3 key weaknesses or areas of improvement"],\n'
        '  "risk_assessment": "1-2 sentence academic risk assessment.",\n'
        '  "teacher_remarks": "1-2 sentence teacher remarks."\n'
        "}"
    )

    if gemini_key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        try:
            res = requests.post(url, headers=headers, json=body, timeout=20)
            res.raise_for_status()
            res_json = res.json()
            text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text.strip())
        except Exception:
            pass

    if openai_key and client:
        try:
            response = client.chat.completions.create(
                model=openai_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content.strip())
        except Exception:
            pass

    return None


def generate_teacher_pdf_cohort_report(cohort_payload: dict) -> dict | None:
    """Generate structured AI educator cohort reports using Gemini or OpenAI."""
    # To keep payload clean and small, extract summary info
    summary_data = {
        "summary": cohort_payload.get("summary", {}),
        "subjects": cohort_payload.get("subjects", []),
        "subject_intelligence": cohort_payload.get("subject_intelligence", {}),
        "ai_brief": cohort_payload.get("ai_brief", {})
    }
    sanitized_summary = sanitize_for_json(summary_data)
    
    prompt = (
        "Generate a class performance report in structured JSON format based on the cohort data below.\n"
        f"Cohort Data: {json.dumps(sanitized_summary)}\n\n"
        "You must return a raw JSON object with this exact key structure (no markdown wrap, just raw JSON):\n"
        "{\n"
        '  "class_performance_report": "overall class performance analysis text.",\n'
        '  "at_risk_report": "remedial recommendations for at-risk students text.",\n'
        '  "semester_summary": "semester performance summary text.",\n'
        '  "parent_meeting_report": "parent-teacher meeting talking points guide."\n'
        "}"
    )

    if gemini_key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        try:
            res = requests.post(url, headers=headers, json=body, timeout=20)
            res.raise_for_status()
            res_json = res.json()
            text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text.strip())
        except Exception:
            pass

    if openai_key and client:
        try:
            response = client.chat.completions.create(
                model=openai_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content.strip())
        except Exception:
            pass

    return None
