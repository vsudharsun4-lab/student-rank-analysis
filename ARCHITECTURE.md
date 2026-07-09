# 🏗️ EduRank AI - Technical Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer (Browser)                  │
├─────────────────────────────────────────────────────────────┤
│  Templates (HTML) │  Styles (CSS)  │  Scripts (JavaScript)   │
│  - login.html     │  - styles.css  │  - dashboard.js         │
│  - dashboard.html │                │  - script.js            │
│  - student_...    │                │                         │
│  - error.html     │                │                         │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/JSON
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Backend Layer (Flask)                     │
├─────────────────────────────────────────────────────────────┤
│  Authorization   │   Routes    │  Session Management         │
│  - Auth Check    │  - GET /    │  - Login/Logout            │
│  - Role Check    │  - GET /api │  - Session Store           │
│  - Access List   │  - POST /   │  - Cookie Handling         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│           Analytics & Prediction Engine (Python)            │
├─────────────────────────────────────────────────────────────┤
│  Data Processing  │  ML Models    │  Recommendations        │
│  - CSV parsing    │  - Trajectory │  - AI suggestions       │
│  - Ranking calc   │  - Trends     │  - Interventions        │
│  - Grade mapping  │  - Predictions│  - Risk assessment      │
│  - Risk scoring   │  - Confidence │  - Priority planning    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                 Data Layer (CSV File)                        │
├─────────────────────────────────────────────────────────────┤
│            students.csv (Name, Subject marks, ...)          │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Structure

### 1. **app.py** - Flask Application Server
**Responsibilities:**
- HTTP request handling
- Routing and URL mapping
- Session management
- Authentication/Authorization
- API endpoint response formatting
- Error handling
- Template rendering

**Key Imports:**
```python
from flask import Flask, request, session, redirect, render_template, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from rank_analysis import build_analysis_payload, get_student_profile
```

**Request Flow:**
```
Request → Route Handler → Auth Check → Data Processing → Response
```

### 2. **rank_analysis.py** - Analytics Engine
**Responsibilities:**
- Data loading and processing
- Statistical calculations
- Student ranking
- Performance analysis
- ML predictions
- Recommendation generation
- Intervention planning

**Core Functions:**

#### Data Processing Functions
```python
build_rank_dataframe(csv_path)
  ↓ Reads CSV
  ↓ Calculates Total, Average, Grade
  ↓ Computes Rank, Percentile, Consistency
  ↓ Returns enriched DataFrame

get_subject_columns(data)
  ↓ Returns list of subject names

format_student_snapshot(row)
  ↓ Formats student record for API response
```

#### Analytics Functions
```python
build_subject_intelligence(data, subjects)
  ↓ Average, highest, lowest, variance per subject

build_score_bands(data)
  ↓ Distribution across 5 bands

build_ai_brief(data, subject_intelligence)
  ↓ Momentum score, narrative, insights
```

#### Prediction Functions
```python
generate_performance_trajectory(avg, consistency, risk)
  ↓ 4-week predictions with confidence scores
  ↓ Trend direction analysis

generate_recommendations(student_row, subjects, intelligence, class_avg)
  ↓ Context-aware suggestions
  ↓ Priority actions
  ↓ Study tips
```

#### Planning Functions
```python
generate_intervention_plan(student_row, subjects, intelligence)
  ↓ 4-week structured plan
  ↓ Weekly focus areas
  ↓ Daily activities
  ↓ Checkpoint assessments

get_student_profile(student_name, csv_path)
  ↓ Comprehensive student analytics
  ↓ All predictions and recommendations
```

---

## Data Flow Architecture

### User Login Flow
```
1. User clicks login button
   ↓
2. Form submission to POST /login
   ↓
3. Validate email exists in DEMO_USERS
   ↓
4. Check password hash (werkzeug)
   ↓
5. Create session: session['user_email'] = email
   ↓
6. Redirect to dashboard or student profile
   ↓
7. All future requests check session['user_email']
```

### Dashboard Load Flow
```
1. GET /dashboard
   ↓
2. get_current_user() from session
   ↓
3. If not authenticated → redirect to login
   ↓
4. Render dashboard.html template
   ↓
5. JavaScript calls GET /api/analysis
   ↓
6. app.py calls build_analysis_payload()
   ↓
7. rank_analysis.py processes students.csv
   ↓
8. Returns JSON with all analytics
   ↓
9. JavaScript renders charts and tables
```

### Student Profile Load Flow
```
1. GET /student/<name>
   ↓
2. Validate user access (own profile or teacher)
   ↓
3. Render student_profile.html
   ↓
4. JavaScript calls GET /api/student/<name>
   ↓
5. app.py calls get_student_profile()
   ↓
6. rank_analysis.py:
   a. build_rank_dataframe()
   b. generate_performance_trajectory()
   c. generate_recommendations()
   d. generate_intervention_plan()
   e. compile_profile()
   ↓
7. Returns JSON with all student data
   ↓
8. JavaScript renders profile page
```

---

## API Endpoints Architecture

### Authentication Endpoints
```
GET  /login              → Returns login.html form
POST /login              → Process login, create session
GET  /logout             → Clear session, redirect to login
GET  /auth/check         → Check if authenticated (JSON)
```

### Page Endpoints
```
GET  /                   → Redirect to dashboard or login
GET  /dashboard          → Render dashboard.html
GET  /student/<name>     → Render student_profile.html
```

### API Endpoints (JSON)
```
GET  /api/analysis       → Full analysis payload
GET  /api/student/<name> → Individual student profile
GET  /api/students       → All students list
GET  /api/summary        → Dashboard summary stats
GET  /api/recommendations→ Student recommendations
GET  /api/interventions  → Intervention list
```

### Error Endpoints
```
404  → error.html with "Page not found"
500  → error.html with "Internal error"
```

---

## Frontend Architecture

### Template Structure
```
templates/
├── login.html
│   ├── Role selector (Teacher/Student/Admin)
│   ├── Email input
│   ├── Password input
│   ├── Student selector (conditional)
│   └── Submit button
│
├── dashboard.html
│   ├── Header/Topbar
│   ├── Hero section
│   ├── KPI cards section
│   ├── AI Briefing panel
│   ├── Leaderboard section
│   ├── Charts section
│   └── Student table
│
├── student_profile.html
│   ├── Header with back link
│   ├── Performance snapshot card
│   ├── Subject performance grid
│   ├── Trajectory predictions
│   ├── Priority actions
│   ├── Personalized tips
│   └── Intervention plan (conditional)
│
└── error.html
    ├── Error icon
    ├── Error message
    └── Action buttons
```

### JavaScript Module Structure
```
dashboard.js
├── State object
│   ├── students[]
│   ├── subjects[]
│   ├── charts{}
│   └── filters{}
│
├── Initialization
│   └── loadDashboard()
│
├── Data Loading
│   ├── fetch /api/analysis
│   ├── fetch /api/students
│   └── fetch /api/interventions
│
├── Rendering
│   ├── renderKpis()
│   ├── renderBriefing()
│   ├── renderLeaderboard()
│   ├── createChart()
│   ├── loadStudentsTable()
│   └── loadInterventions()
│
└── Event Listeners
    ├── DOMContentLoaded
    └── Click handlers
```

### CSS Module Structure
```
styles.css
├── CSS Variables (:root)
├── Base Styles (body, *,  html)
├── Layout (grid, flexbox)
├── Components
│   ├── .topbar
│   ├── .panel
│   ├── .kpi
│   ├── .badge
│   ├── .chart-canvas
│   └── .table
├── Responsive Media Queries
└── Animations/Transitions
```

---

## Database-Like Structure (CSV)

### Current: File-Based
```
students.csv
│
├─ Headers: Name, Maths, Science, English, Social, Computer
│
├─ Records:
│  ├ Arun, 59, 85, 88, 72, 80
│  ├ Ravi, 95, 80, 78, 85, 90
│  └ ...
│
└─ Processing:
   └─ pandas.read_csv() → DataFrame
```

### Future: Database-Based
```
PostgreSQL/MongoDB
│
├─ students table
│  ├ id (primary key)
│  ├ name
│  ├ email
│  └─ created_at
│
├─ marks table
│  ├ student_id (foreign key)
│  ├ subject
│  ├ marks
│  └─ term
│
└─ recommendations table
   ├ student_id
   ├ recommendation_text
   └─ created_at
```

---

## Authentication & Authorization

### Session Management
```python
session = {
    'user_email': 'teacher@eduai.com',
    'user_type': 'teacher',  # or 'admin', 'student'
    'user_name': 'Mr. Kumar',
    'student_name': None,     # Only for students
}
```

### Role-Based Access Control (RBAC)
```
Teacher/Admin:
├─ /dashboard → ✅ Access
├─ /api/analysis → ✅ Full access
├─ /api/students → ✅ All students
└─ /api/interventions → ✅ View all

Student:
├─ /student/<own_name> → ✅ Access
├─ /student/<other_name> → ❌ Denied
├─ /api/student/<own_name> → ✅ Access
└─ /api/student/<other_name> → ❌ Denied
```

### Security Layers
```
1. Route Protection: Check session['user_email']
2. Role Validation: Verify user_type in session
3. Data Access: Conditional API responses
4. Error Handling: 403 Forbidden for denials
```

---

## ML/Prediction Algorithm

### Performance Trajectory Prediction

**Inputs:**
```python
current_avg: float (0-100)
consistency: float (0-100)  # Score stability
risk_level: str             # 'Low', 'Medium', 'High'
```

**Logic:**
```python
for week in range(1, 5):
    stability_factor = consistency / 100  # 0 to 1
    
    # Determine trend direction
    if risk_level == 'Low':
        trend_direction = +1    # Upward
    elif risk_level == 'High':
        trend_direction = -0.5  # Downward
    else:
        trend_direction = +0.2  # Slight upward
    
    # Calculate weekly change
    weekly_change = trend_direction * (1 - stability_factor)
    
    # Predict next week
    predicted = current_avg + (weekly_change * week * 0.5)
    
    # Confidence higher for stable students
    confidence = 85 + (stability_factor * 15)
    
    predictions.append({
        'week': week,
        'score': clamp(predicted, 0, 100),
        'confidence': confidence
    })
```

**Assumptions:**
- Linear trend over 4 weeks
- Stability affects prediction variance
- Risk level influences direction
- Scores clamp at 0-100 range

### Recommendation Engine

**Decision Tree:**
```
If Result == 'Fail':
  ├─ Priority: Critical
  ├─ Actions: Pass mark focus
  └─ Example: "Focus on 35+ in all subjects"

Elif Average < 50:
  ├─ Priority: High
  ├─ Actions: Comprehensive support
  └─ Example: "2-hour daily sessions"

Elif Average < 65:
  ├─ Priority: Medium
  ├─ Actions: Targeted improvement
  └─ Example: "Weak subject focus"

Elif Average >= 85:
  ├─ Priority: Excellence
  ├─ Actions: Maintain & enhance
  └─ Example: "Peer tutoring"

Else:
  ├─ Priority: On Track
  ├─ Actions: Consistency
  └─ Example: "Reduce subject variance"
```

### Intervention Plan Generation

**Structure:**
```
For each of 4 weeks:
├─ Focus areas: weakest subjects
├─ Daily activities:
│  ├─ Main subject: 1.5-2 hours
│  ├─ Practice tests: 2x weekly
│  └─ Peer review: weekly
└─ Checkpoint: mini-assessment
```

---

## Error Handling Strategy

### Route Error Handling
```python
try:
    # Route logic
except Exception as e:
    return render_template('error.html', 
                         message=str(e)), 500
```

### API Error Handling
```python
# Unauthorized
if not get_current_user():
    return jsonify({'error': 'Unauthorized'}), 401

# Access denied
if user['type'] == 'student' and user['student_name'] != student_name:
    return jsonify({'error': 'Access denied'}), 403

# Not found
if student.empty:
    return jsonify({'error': 'Student not found'}), 404
```

### Frontend Error Handling
```javascript
async function loadDashboard() {
    try {
        const response = await fetch('/api/analysis');
        if (!response.ok) {
            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }
            throw new Error('Failed to load');
        }
        const data = await response.json();
        // Process data
    } catch (error) {
        console.error('Error:', error);
        // Show error UI
    }
}
```

---

## Performance Optimization

### Backend Optimization
```
1. Efficient DataFrame operations
   └─ Vectorized calculations with NumPy/Pandas

2. Caching (Future)
   └─ Cache analysis results with TTL

3. Lazy Loading (Future)
   └─ Load predictions only when needed

4. Database Indexing (Future)
   └─ Index on student_id, name, etc.
```

### Frontend Optimization
```
1. Minimal JSON responses
   └─ Return only needed fields

2. Chart.js for lightweight viz
   └─ Only 3 charts on dashboard

3. Event delegation
   └─ Single handler for table clicks

4. Static file caching
   └─ Browser cache for CSS/JS

5. Async API calls
   └─ Non-blocking data fetching
```

---

## Deployment Architecture

### Development
```
├─ Flask debug mode: ON
├─ Hot reload: Enabled
├─ Port: 5000
└─ Host: 127.0.0.1
```

### Production (Future)
```
├─ WSGI Server: Gunicorn
├─ Reverse Proxy: Nginx
├─ Database: PostgreSQL
├─ Session Store: Redis
├─ Environment: Docker
└─ Hosting: AWS/Heroku/DigitalOcean
```

### Scaling Strategy
```
Current (Single Server):
└─ All layers on one machine

Horizontal Scaling:
├─ API servers: Load-balanced
├─ Database: Dedicated server
├─ Cache: Redis cluster
└─ static files: CDN

Vertical Scaling:
├─ Increase CPU cores
├─ Increase RAM
└─ Optimize code
```

---

## Testing Strategy

### Unit Testing (Future)
```python
test_rank_calculation()
test_grade_mapping()
test_prediction_model()
test_recommendation_engine()
```

### Integration Testing (Future)
```python
test_login_flow()
test_dashboard_load()
test_api_endpoints()
test_student_profile()
```

### Manual Testing Checklist
```
☐ Login with all roles
☐ View dashboard
☐ Click student links
☐ Check charts render
☐ View student profile
☐ Check recommendations
☐ Test logout
☐ Test 404 errors
☐ Test unauthorized access
```

---

## Extension Points

### Adding New Features
```
1. New Student Metric
   └─ Edit rank_analysis.py: add calculation → add to API

2. New Chart
   └─ Edit dashboard.html: add canvas → dashboard.js: createChart()

3. New API Endpoint
   └─ Edit app.py: add @app.route() → return jsonify()

4. New ML Model
   └─ Edit rank_analysis.py: add function → call from app.py

5. New Report
   └─ Create new template → new route in app.py
```

### Configuration Points
```
In app.py:
├─ app.secret_key  → Change for production
├─ DEMO_USERS      → Add more users
└─ Port 5000       → Change port

In rank_analysis.py:
├─ grade()         → Adjust grading scale
├─ pass_fail()     → Change pass mark
└─ Momentum formula → Adjust weights

In students.csv:
├─ Add subjects    → Update headers
├─ Add students    → Add rows
└─ Update marks    → Refresh data
```

---

This architecture is designed to be:
- **Scalable**: From 10 to 10,000+ students
- **Maintainable**: Clear separation of concerns
- **Extensible**: Easy to add features
- **Secure**: Role-based access control
- **Performant**: Efficient data processing
