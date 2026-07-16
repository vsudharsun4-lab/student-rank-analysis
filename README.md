# 🎓 EduRank AI - Academic Performance & Recommendation Platform

A sophisticated, **production-ready** AI-powered educational analytics platform designed for intelligent student performance tracking, prediction, and personalized intervention planning.

## ✨ Features

### 🔐 Professional Authentication
- **Role-based access control**: Teacher, Admin, and Student login modes
- **Secure session management**: Werkzeug-based password hashing
- **Demo credentials** for immediate testing
- **Access control**: Students see only their own profiles; teachers see all students

### 📊 Intelligent Dashboard
- **Real-time performance metrics**: KPIs with live data sync
- **AI Briefing system**: Momentum score, trend analysis, and cohort insights
- **Leaderboard rankings**: Top 3 performers with detailed metrics
- **Visual analytics**: Multiple chart types (bar, doughnut, line) for data exploration
- **Comprehensive student table**: Filterable, sortable overview of all students

### 🤖 ML-Powered Predictions
- **Performance trajectory forecasting**: 4-week ahead predictions with confidence scores
- **Risk assessment**: Automatic identification of high-risk students
- **Trend analysis**: Detects improving, declining, or stable patterns
- **Consistency scoring**: Measures score variance and stability

### 💡 Smart Recommendations
- **Personalized learning tips**: Context-aware suggestions based on performance
- **Priority actions**: Actionable interventions for each student
- **Subject-level focus**: Identifies strengths and weaknesses across subjects
- **Peer benchmarking**: Compares student performance to class average and percentiles

### 🎯 Intervention Planning
- **4-week structured plans**: Detailed weekly activities and checkpoints
- **Subject focus mapping**: Prioritizes intervention areas
- **Mentor assignment**: Tracks mentor contact and weekly reviews
- **Escalation protocols**: Automatic flagging of critical cases

### 🤖 AI Agent Workflow
- **Prompt-driven analysis**: Ask natural-language questions about students, subjects, or the cohort
- **Tool orchestration**: The agent routes queries through ranking, profile, and recommendation helpers
- **Student-specific answers**: Supports named student lookups and personalized intervention guidance
- **Resume-ready feature**: Presents the project as an AI agent system, not just a static dashboard

### 📱 Individual Student Profiles
- **Comprehensive analytics**: Subject performance, trends, percentile rank
- **Personalized dashboard**: Student's own performance insights
- **Intervention details**: Custom improvement plans
- **Progress tracking**: Next review dates and metrics

## 🚀 Quick Start

### Installation

1. **Clone/Extract the project**
```bash
cd "student rank analysis"
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
python app.py
```

4. **Access in browser**
```
http://localhost:5000
```

## 📖 Usage Guide

### Login Credentials

#### Teacher Account
- **Email**: `teacher@eduai.com`
- **Password**: `teacher123`
- **Access**: Full dashboard with all students, interventions, recommendations

#### Admin Account
- **Email**: `admin@eduai.com`
- **Password**: `admin123`
- **Access**: Administrative dashboard with full system control

#### Student Account
- **Email**: `student@eduai.com`
- **Password**: `student123`
- **Access**: Personal profile and performance tracking
- **Selection**: Choose from any student name after login

### Dashboard Features

#### 1. **AI Briefing Section**
- **Momentum Score**: Overall cohort performance indicator
- **Narrative**: AI-generated insights about class performance
- **Standout Performers**: Top 3 students with exceptional performance
- **Intervention Candidates**: Students needing support
- **Near-Pass Students**: At-risk but close to passing
- **Risk Distribution**: Breakdown of Low/Medium/High risk students

#### 2. **Key Performance Indicators (KPIs)**
- Student count
- Class average marks
- Highest/lowest total marks
- Pass rate percentage
- Average consistency score

#### 3. **Visualizations**
- Grade distribution (A, B, C, D, F)
- Pass vs Fail analysis
- Score band distribution (90+, 80-89, 70-79, 60-69, <60)
- Subject-wise average performance

#### 4. **Student Overview Table**
- Click "View Profile" to access individual student dashboards
- See rank, average, grade, pass/fail status
- Risk level indicators
- Direct links to detailed profiles

### Student Profile Page

Each student's profile includes:

#### Performance Snapshot
- Current average and trend direction
- Class average comparison
- Percentile ranking
- Grade and risk level

#### Subject Performance
- Individual subject marks
- Pass/Fail status per subject
- Percentile ranking per subject
- Class average for comparison

#### Performance Trajectory
- 4-week performance predictions
- Trend direction (Improving/Declining/Stable)
- Confidence scores for predictions

#### Priority Actions
- Critical intervention needs
- High-priority focus areas
- Actionable recommendations

#### Personalized Learning Tips
- Top 4 tailored recommendations
- Subject-specific strategies
- Study habit suggestions
- Next review date

#### 4-Week Intervention Plan
For at-risk students:
- Weekly focus areas
- Daily activities (if High/Critical)
- Checkpoint assessments
- Mentor assignment status

## 🏗️ Architecture

### Backend Structure
```
app.py                  # Flask server with routes & auth
rank_analysis.py        # ML models & analytics engine
requirements.txt        # Python dependencies
students.csv            # Student data
```

### Frontend Structure
```
templates/
  ├── login.html           # Authentication page
  ├── dashboard.html       # Teacher/Admin dashboard
  ├── student_profile.html # Individual student view
  └── error.html          # Error handling

static/
  ├── styles.css          # Modern, responsive styling
  ├── dashboard.js        # Dashboard interactivity
  └── script.js           # General site scripts
```

### Key Components

#### Authentication System
- Secure password hashing with Werkzeug
- Session-based authentication
- Role-specific access control
- Protected API endpoints

#### Analytics Engine
- Real-time data processing
- Grade calculation and ranking
- Risk categorization
- Momentum scoring

#### ML Prediction Module
- Performance trajectory forecasting
- Trend analysis
- Consistency evaluation
- Confidence scoring

#### Recommendation Engine
- Context-aware suggestions
- Priority action generation
- Intervention plan creation
- Subject-level analytics

## 📊 Data Model

### Student Record Fields
```python
{
    "Name": string,
    "Total": int,              # Sum of all subject marks
    "Average": float,          # Average across subjects
    "Grade": string,           # A/B/C/D/F
    "Rank": int,              # Class rank
    "Result": string,         # Pass/Fail
    "RiskLevel": string,      # Low/Medium/High
    "Percentile": float,      # Percentile ranking
    "Consistency": float      # Score variance measure
}
```

### Subject Scores
All subject marks are included (Maths, Science, English, Social, Computer)

## 🔒 Security Features

- ✅ Password hashing using Werkzeug security
- ✅ Session-based authentication
- ✅ CSRF-ready Flask configuration
- ✅ Access control checks on all endpoints
- ✅ Role-based API restrictions
- ✅ Error handling without information leakage

## 🎨 UI/UX Design

- **Modern Gradient UI**: Smooth color transitions and professional appearance
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark/Light Mode Ready**: CSS variables allow easy theme switching
- **Interactive Charts**: Real-time chart.js visualizations
- **Smooth Animations**: Reveal animations and transitions
- **Accessibility**: Semantic HTML and ARIA attributes

## 💻 API Endpoints

### Public Routes
```
GET  /                         # Home (redirects to dashboard)
GET  /login                    # Login page
POST /login                    # Handle login
GET  /logout                   # Logout
```

### Protected Routes (Auth Required)
```
GET  /dashboard                # Main dashboard
GET  /student/<name>           # Student profile page
GET  /api/analysis             # Full analysis payload
GET  /api/student/<name>       # Student API data
GET  /api/students             # All students list
GET  /api/summary              # Dashboard summary
GET  /api/recommendations      # Student recommendations
GET  /api/interventions        # Intervention list
```

## 🔧 Configuration

### Customization Options

#### Change Secret Key (Production)
Edit `app.py`:
```python
app.secret_key = "your-secure-key-here"
```

#### Add More Students
Edit `students.csv`:
```
Name,Maths,Science,English,Social,Computer
NewStudent,85,90,78,88,92
```

#### Adjust Grading Scale
Edit `grade()` function in `rank_analysis.py`:
```python
def grade(avg: float) -> str:
    if avg >= 90: return "A"
    # ... etc
```

## 📈 Performance Metrics

### Calculated Metrics
- **Total Marks**: Sum of all subject scores
- **Average**: Mean across subjects
- **Grade**: Letter grade based on average
- **Rank**: Numerical ranking in class
- **Percentile**: Percentage of class below student
- **Consistency**: Measure of score variance (0-100)
- **Pass/Fail**: Based on minimum marks (35)
- **Risk Level**: Low/Medium/High based on performance

### Momentum Score
Formula: `(pass_rate × 0.65) + (consistency × 0.35)`
- Indicates overall cohort health
- Ranges from 0-100
- Interpreted as: Excellent (85+), Stable (70-84), Needs Attention (<70)

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Change port in app.py
app.run(host="0.0.0.0", port=5001, debug=True)
```

### Module Not Found
```bash
pip install -r requirements.txt --upgrade
```

### CSV Not Found
Ensure `students.csv` is in the project root directory

### Students Not Loading
Check CSV format and headers match expected column names

## 📚 Future Enhancements

- ✨ Database integration (PostgreSQL/MongoDB)
- ✨ Advanced ML models (Random Forest, Neural Networks)
- ✨ Email notifications for interventions
- ✨ Export reports (PDF, Excel)
- ✨ Parent dashboard and notifications
- ✨ Custom assessment creation
- ✨ Real-time collaboration features
- ✨ Mobile app version

## 📄 License

This project is provided as-is for educational and institutional use.

## 👨‍💼 Support

For issues, feature requests, or suggestions, please refer to the code comments and documentation within the application.

---

**EduRank AI** - Empowering educators with intelligent, actionable student insights. 🚀
