# ⚡ Quick Start Guide - EduRank AI

## 🎯 Get Started in 5 Minutes

### Step 1: Start the Server ✅
```bash
cd "student rank analysis"
python app.py
```

You should see:
```
* Running on http://127.0.0.1:5000
```

### Step 2: Open in Browser 🌐
Visit: **http://localhost:5000**

---

## 📝 First Login

### Option A: Teacher View (Full Access) 👨‍🏫
1. Select **Teacher** role
2. Email: `teacher@eduai.com`
3. Password: `teacher123`
4. Click "Sign In"

**You'll see:**
- Full student dashboard
- All analytics and charts
- Intervention recommendations
- Class momentum score

### Option B: Student View (Personal Profile) 👨‍🎓
1. Select **Student** role
2. Email: `student@eduai.com`
3. Password: `student123`
4. Choose a student name (e.g., "Arun")
5. Click "Sign In"

**You'll see:**
- Your personal profile
- Performance metrics
- AI recommendations
- 4-week intervention plan

### Option C: Admin View (System Control) ⚙️
1. Select **Admin** role
2. Email: `admin@eduai.com`
3. Password: `admin123`
4. Click "Sign In"

**You'll see:**
- Administrative dashboard
- All system analytics
- Full reporting capabilities

---

## 🗺️ Navigation Guide

### From Dashboard
```
📊 Dashboard Home
├── 📈 KPI Cards (top)
├── 🧠 AI Briefing Section
│   ├── Momentum Score
│   ├── Top Performers
│   ├── Intervention Candidates
│   └── Recommended Actions
├── 🏆 Leaderboard (Top 3)
├── 📊 Charts
│   ├── Grade Distribution
│   ├── Pass vs Fail
│   ├── Score Bands
│   └── Subject Averages
└── 👥 Student Table
    └── Click any student to view profile
```

### Student Profile Page
```
👤 Student Profile
├── Performance Snapshot
│   ├── Grade & Status
│   ├── Total & Average
│   └── Risk Level
├── 📚 Subject Performance
├── 📈 Performance Trajectory (predictions)
├── 💡 Priority Actions
├── 📝 Personalized Tips
└── 🎯 4-Week Intervention Plan
```

---

## 💡 Key Features to Explore

### 1️⃣ AI Briefing Score
Look for the large number in the AI section:
- **Green (85+)**: Class is doing great! 🎉
- **Teal (70-84)**: On track, stable 📈
- **Red (<70)**: Needs attention ⚠️

### 2️⃣ Student Table
Click any student's name to access:
- Their personal dashboard
- Detailed performance breakdown
- AI-generated recommendations
- Intervention planning

### 3️⃣ Performance Trends
In student profile, check the **Performance Trajectory**:
- Shows 4-week predictions
- 📈 📉 ➡️ Trend directions
- Confidence scores

### 4️⃣ Smart Recommendations
Always check the **💡 Personalized Tips** section for:
- Study strategies
- Subject focus areas
- Time management suggestions
- Peer learning opportunities

### 5️⃣ Intervention Plans
For at-risk students see:
- Week-by-week action plans
- Specific subject focus
- Daily activities
- Progress checkpoints

---

## 🔄 Typical User Workflows

### Teacher Workflow
```
1. Login as Teacher
   ↓
2. Review Dashboard → See class momentum
   ↓
3. Check Intervention Candidates → Identify at-risk students
   ↓
4. Click on student name → Review their profile & plan
   ↓
5. View 4-Week Intervention Plan → Implement weekly
   ↓
6. Check Progress Tracker → Update after 1-2 weeks
```

### Student Workflow
```
1. Login as Student (choose your name)
   ↓
2. View Performance Snapshot → See your status
   ↓
3. Check Subject Performance → Identify weak areas
   ↓
4. Read Personalized Tips → Get study suggestions
   ↓
5. Follow 4-Week Plan → Complete weekly activities
   ↓
6. Check Trajectory → Monitor your improvement
```

### Admin Workflow
```
1. Login as Admin
   ↓
2. View System Analytics → Overall performance
   ↓
3. Generate Reports → Class-wide insights
   ↓
4. Monitor Interventions → Track effectiveness
   ↓
5. System Settings → Configure as needed
```

---

## 📊 Understanding the Metrics

### KPI Cards
| Card | Meaning |
|------|---------|
| Students | Total students in class |
| Class Average | Mean score across all students |
| Highest Total | Top student's marks |
| Lowest Total | Bottom student's marks |
| Pass Rate | % of students passing |
| Avg Consistency | How steady are students' scores |

### Grades
- **A**: 90+ (Excellent)
- **B**: 80-89 (Good)
- **C**: 70-79 (Average)
- **D**: 60-69 (Below Average)
- **F**: <60 (Fail)

### Risk Levels
- 🟢 **Low Risk**: Performing well, on track
- 🟡 **Medium Risk**: Adequate, needs monitoring
- 🔴 **High Risk**: Critical, needs intervention

### Results
- ✅ **Pass**: All subjects ≥ 35 marks
- ❌ **Fail**: Any subject < 35 marks

---

## 🎮 Interactive Features

### Hover Effects
- KPI cards change appearance
- Student rows highlight
- Buttons show tooltips
- Charts show data points

### Clickable Elements
- Student names → View profile
- "View Profile" button → Student dashboard
- Back buttons → Return to dashboard
- Logout → Exit and return to login

### Responsive
- Works on desktop, tablet, mobile
- Touch-friendly buttons
- Scales beautifully
- Fast loading

---

## ✨ Pro Tips

### 🔍 Finding At-Risk Students
1. Look at **Intervention Candidates** in AI Briefing
2. Check the red-highlighted students in table
3. View their profile for 4-week plan
4. Implement weekly interventions

### 📈 Tracking Improvement
1. Note current average score
2. Check performance trajectory
3. See 4-week predictions
4. Compare predictions to actuals

### 💬 Class Communication
1. Use AI Briefing insights for class announcements
2. Share top performers (motivation)
3. Share subject focus areas (guidance)
4. Use recommended actions for planning

### 🎓 Peer Learning
1. Identify top performers per subject
2. Match with struggling students
3. Create peer tutoring pairs
4. Track progress weekly

---

## 🐛 Troubleshooting

### "Can't connect to server"
```
Check if Flask is running:
- Terminal should show "Running on http://127.0.0.1:5000"
- Try: http://localhost:5000 or http://127.0.0.1:5000
```

### "Login failed"
```
Check credentials (note case sensitivity):
- teacher@eduai.com / teacher123
- admin@eduai.com / admin123
- student@eduai.com / student123
```

### "Student not found"
```
Ensure:
- Student name matches CSV file exactly
- Check students.csv for correct spelling
- Names are case-sensitive
```

### "Charts not showing"
```
Check browser console for errors:
- Press F12
- Look at Console tab
- Reports should appear after a moment
```

---

## 📚 What Each Page Shows

### Login Page
- Role selection (Teacher/Student/Admin)
- Email and password fields
- Optional student selection (if Student role)
- Demo credentials reference

### Dashboard
- Overview of entire class
- Real-time analytics
- Performance charts
- All students quick view
- Call-to-action buttons

### Student Profile
- Individual performance details
- Subject breakdown
- Performance predictions
- Personalized recommendations
- Intervention planning

### Error Page
- Clear error message
- Navigation back to dashboard
- Quick links to main sections

---

## 🚀 Next Steps

After exploring the platform:

1. **Add more students** → Edit `students.csv`
2. **Customize colors** → Edit `static/styles.css`
3. **Change grading scale** → Edit `rank_analysis.py`
4. **Add subjects** → Update CSV headers
5. **Deploy online** → Use Gunicorn/Heroku

---

## 📞 Need Help?

Check these resources:
- [README.md](README.md) - Full documentation
- [FEATURES.md](FEATURES.md) - Feature details
- Code comments in `app.py` and `rank_analysis.py`
- Error messages provide clues

---

## ✅ Verification Checklist

After login, verify you can:
- [ ] See dashboard with KPI cards
- [ ] View AI briefing with momentum score
- [ ] See student table with all names
- [ ] Click on any student → View profile
- [ ] See performance charts
- [ ] View personalized tips
- [ ] Check intervention plans
- [ ] See performance trajectory
- [ ] Access logout button

**If all checked ✓ → You're ready to use EduRank AI!** 🎉

---

Happy analyzing! 🚀
