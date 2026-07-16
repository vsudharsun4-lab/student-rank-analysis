const state = {
  students: [],
  subjects: [],
  selectedSubjects: [],
  subjectIntelligence: {},
  subjectMetric: "average",
  filters: {
    search: "",
    risk: "all",
  },
  charts: {
    grade: null,
    result: null,
    subjectAverage: null,
  },
};

function setDateChip() {
  const date = new Date().toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  document.getElementById("liveDate").textContent = `Updated ${date}`;
}

function renderKpis(summary) {
  const container = document.getElementById("kpis");
  const items = [
    { label: "Students", value: summary.student_count, note: "Active in cohort" },
    { label: "Class Average", value: summary.class_average, note: "Across all subjects" },
    { label: "Highest Total", value: summary.highest_total, note: "Top score" },
    { label: "Lowest Total", value: summary.lowest_total, note: "Bottom score" },
    { label: "Pass Rate", value: `${summary.pass_rate}%`, note: "Pass / total" },
    { label: "Avg Consistency", value: summary.avg_consistency, note: "Stability index" },
  ];

  if (summary.attendance_present) {
    items.push({ label: "Attendance", value: `${summary.average_attendance}%`, note: "Class average" });
  }

  container.innerHTML = items
    .map(
      (item) => `
      <article class="kpi">
        <p class="kpi__label">${item.label}</p>
        <p class="kpi__value">${item.value}</p>
        <div class="kpi__note">${item.note}</div>
      </article>
    `,
    )
    .join("");
}

function renderBriefing(data) {
  const { momentum, narrative, insights, actions, standout_performers, intervention_candidates, near_pass_students, risk_breakdown, subject_focus } = data.ai_brief;

  // Momentum Score
  const scoreEl = document.getElementById("momentumScore");
  const scoreColor =
    momentum.score >= 85
      ? "#1f8f5f"
      : momentum.score >= 70
        ? "#0f9d7a"
        : "#c93838";
  scoreEl.innerHTML = `
    <div style="font-size: 3.2rem; font-weight: 700; color: ${scoreColor}; margin-bottom: 0.5rem;">${momentum.score}</div>
    <p style="margin: 0; color: var(--text-soft); font-size: 0.9rem;">Cohort Momentum Score</p>
    <p style="margin: 0.5rem 0 0; color: var(--text); font-weight: 600;">${momentum.status}</p>
  `;

  // Narrative
  document.getElementById("aiNarrative").textContent = narrative;

  // Brief KPIs
  const briefKpisEl = document.getElementById("briefKpis");
  briefKpisEl.innerHTML = `
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.8rem; margin-bottom: 1.5rem;">
      <div style="background: rgba(15, 157, 122, 0.08); padding: 0.8rem; border-radius: 8px;">
        <p style="margin: 0; font-size: 0.75rem; color: var(--text-soft); text-transform: uppercase;">Pass Rate</p>
        <p style="margin: 0.4rem 0 0; font-size: 1.2rem; font-weight: 700; color: var(--brand);">${data.ai_brief.class_profile.pass_rate}%</p>
      </div>
      <div style="background: rgba(46, 111, 255, 0.08); padding: 0.8rem; border-radius: 8px;">
        <p style="margin: 0; font-size: 0.75rem; color: var(--text-soft); text-transform: uppercase;">Class Avg</p>
        <p style="margin: 0.4rem 0 0; font-size: 1.2rem; font-weight: 700; color: var(--brand-3);">${data.ai_brief.class_profile.class_average}</p>
      </div>
    </div>
  `;

  // Insights
  const insightEl = document.getElementById("aiInsightList");
  insightEl.innerHTML = insights
    .map((insight) => `<li style="padding: 0.6rem 0; color: var(--text-soft); font-size: 0.9rem; line-height: 1.5;">${insight}</li>`)
    .join("");

  // Standout performers
  const standoutEl = document.getElementById("standoutList");
  standoutEl.innerHTML = standout_performers
    .map(
      (student) => `
      <div style="padding: 0.8rem; background: var(--panel-soft); border-radius: 8px; margin-bottom: 0.6rem;">
        <p style="margin: 0; font-weight: 600; color: var(--text);">${student.name}</p>
        <p style="margin: 0.3rem 0 0; font-size: 0.85rem; color: var(--text-soft);">Avg: ${student.average} | Rank #${student.rank}</p>
      </div>
    `,
    )
    .join("");

  // Intervention candidates
  const interventionEl = document.getElementById("interventionList");
  interventionEl.innerHTML = intervention_candidates
    .map(
      (student) => `
      <div style="padding: 0.8rem; background: rgba(201, 56, 56, 0.08); border-radius: 8px; margin-bottom: 0.6rem; border-left: 3px solid var(--danger);">
        <p style="margin: 0; font-weight: 600; color: var(--text);">${student.name}</p>
        <p style="margin: 0.3rem 0 0; font-size: 0.85rem; color: var(--text-soft);">Avg: ${student.average} | ${student.result}</p>
      </div>
    `,
    )
    .join("");

  // Near-pass students
  const nearPassEl = document.getElementById("nearPassList");
  nearPassEl.innerHTML = near_pass_students
    .map(
      (student) => `
      <div style="padding: 0.8rem; background: rgba(217, 119, 6, 0.08); border-radius: 8px; margin-bottom: 0.6rem; border-left: 3px solid var(--warning);">
        <p style="margin: 0; font-weight: 600; color: var(--text);">${student.name}</p>
        <p style="margin: 0.3rem 0 0; font-size: 0.85rem; color: var(--text-soft);">Avg: ${student.average}</p>
      </div>
    `,
    )
    .join("");

  // Risk breakdown
  const riskEl = document.getElementById("riskBreakdown");
  riskEl.innerHTML = `
    <div style="display: grid; gap: 0.6rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem; background: rgba(31, 143, 95, 0.08); border-radius: 6px;">
        <span style="font-size: 0.85rem; color: var(--text-soft);">Low Risk</span>
        <span style="font-weight: 700; color: var(--success);">${risk_breakdown.Low}</span>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem; background: rgba(217, 119, 6, 0.08); border-radius: 6px;">
        <span style="font-size: 0.85rem; color: var(--text-soft);">Medium Risk</span>
        <span style="font-weight: 700; color: var(--warning);">${risk_breakdown.Medium}</span>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem; background: rgba(201, 56, 56, 0.08); border-radius: 6px;">
        <span style="font-size: 0.85rem; color: var(--text-soft);">High Risk</span>
        <span style="font-weight: 700; color: var(--danger);">${risk_breakdown.High}</span>
      </div>
    </div>
  `;

  // Subject focus
  const subjectFocusEl = document.getElementById("subjectFocusList");
  subjectFocusEl.innerHTML = subject_focus
    .map(
      (subject) => `
      <div style="padding: 0.7rem; background: var(--panel-soft); border-radius: 8px; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
        <span style="font-weight: 600; color: var(--text);">${subject.subject}</span>
        <span style="font-size: 0.85rem; background: var(--brand); color: #fff; padding: 0.3rem 0.6rem; border-radius: 4px;">${subject.priority}</span>
      </div>
    `,
    )
    .join("");

  // Recommended actions
  const actionEl = document.getElementById("actionList");
  actionEl.innerHTML = data.ai_brief.actions
    .map((action) => `<li style="padding: 0.6rem 0; color: var(--text); font-size: 0.9rem; line-height: 1.4;">${action}</li>`)
    .join("");
}

function renderLeaderboard(topThree) {
  const container = document.getElementById("topThree");
  container.innerHTML = topThree
    .map(
      (student, index) => `
      <div style="display: grid; grid-template-columns: auto 1fr auto; gap: 1.5rem; padding: 1.5rem; background: var(--panel-soft); border-radius: 12px; margin-bottom: 1rem; align-items: center;">
        <div style="width: 50px; height: 50px; border-radius: 12px; background: linear-gradient(135deg, var(--brand) 0%, var(--brand-3) 100%); display: grid; place-items: center; color: #fff; font-weight: 700; font-size: 1.4rem;">
          #${index + 1}
        </div>
        <div>
          <p style="margin: 0; font-weight: 700; font-size: 1.1rem; color: var(--text);">${student.Name}</p>
          <p style="margin: 0.4rem 0 0; color: var(--text-soft); font-size: 0.9rem;">Grade: <strong>${student.Grade}</strong></p>
        </div>
        <div style="text-align: right;">
          <p style="margin: 0; font-size: 1.8rem; font-weight: 700; color: var(--brand);">${student.Total}</p>
          <p style="margin: 0.3rem 0 0; color: var(--text-soft); font-size: 0.8rem;">Total Marks</p>
        </div>
      </div>
    `,
    )
    .join("");
}

function createChart(chartId, type, labels, data, title) {
  const ctx = document.getElementById(chartId).getContext("2d");

  if (state.charts[chartId]) {
    state.charts[chartId].destroy();
  }

  const chartColors =
    type === "doughnut"
      ? ["#0f9d7a", "#ff7c43", "#2e6fff", "#c93838", "#fbbf24"]
      : type === "bar"
        ? "#0f9d7a"
        : "#2e6fff";

  state.charts[chartId] = new Chart(ctx, {
    type: type,
    data: {
      labels: labels,
      datasets: [
        {
          label: title,
          data: data,
          backgroundColor: chartColors,
          borderColor: "transparent",
          borderRadius: 8,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: type === "doughnut",
          position: "bottom",
        },
      },
      scales: type !== "doughnut" ? { y: { beginAtZero: true } } : {},
    },
  });
}

async function loadDashboard() {
  try {
    const response = await fetch("/api/analysis");
    if (!response.ok) {
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      throw new Error("Failed to load dashboard data");
    }

    const data = await response.json();
    state.subjects = data.subjects;
    state.subjectIntelligence = data.subject_intelligence;
    state.students = data.students;

    // Render all components
    setDateChip();
    renderKpis(data.summary);
    renderBriefing(data);
    renderLeaderboard(data.top_3);

    // Create charts
    const gradeLabels = Object.keys(data.grade_distribution).sort();
    const gradeData = gradeLabels.map((grade) => data.grade_distribution[grade]);
    createChart("gradeChart", "bar", gradeLabels, gradeData, "Students per Grade");

    const resultLabels = Object.keys(data.result_distribution);
    const resultData = resultLabels.map((result) => data.result_distribution[result]);
    createChart("resultChart", "doughnut", resultLabels, resultData, "Result Distribution");

    const subjectLabels = data.subjects;
    const subjectData = subjectLabels.map((subject) => data.subject_intelligence[subject].average);
    createChart("subjectChart", "bar", subjectLabels, subjectData, "Subject Average");

    // Load students table
    await loadStudentsTable();
    
    // Load interventions
    await loadInterventions();
  } catch (error) {
    console.error("Error loading dashboard:", error);
  }
}

async function loadStudentsTable() {
  try {
    const response = await fetch("/api/students");
    if (!response.ok) throw new Error("Failed to load students");

    const { students } = await response.json();
    const tbody = document.getElementById("studentsTableBody");
    
    tbody.innerHTML = students
      .map(
        (student) => `
        <tr style="border-bottom: 1px solid var(--line);">
          <td style="padding: 1rem; font-weight: 500;">
            <a href="/student/${student.Name}" style="color: var(--brand); text-decoration: none; font-weight: 600;">
              ${student.Name}
            </a>
          </td>
          <td style="padding: 1rem; text-align: center;">#${student.Rank}</td>
          <td style="padding: 1rem; text-align: center; font-weight: 600;">${student.Average}</td>
          <td style="padding: 1rem; text-align: center;">
            <span style="background: linear-gradient(135deg, var(--brand) 0%, var(--brand-3) 100%); color: #fff; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
              ${student.Grade}
            </span>
          </td>
          <td style="padding: 1rem; text-align: center;">
            <span style="background: ${student.Result === "Pass" ? "rgba(31, 143, 95, 0.15); color: var(--success);" : "rgba(201, 56, 56, 0.15); color: var(--danger);"} padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
              ${student.Result}
            </span>
          </td>
          <td style="padding: 1rem; text-align: center;">
            <span style="background: ${
              student.RiskLevel === "Low"
                ? "rgba(31, 143, 95, 0.15); color: var(--success);"
                : student.RiskLevel === "Medium"
                  ? "rgba(217, 119, 6, 0.15); color: var(--warning);"
                  : "rgba(201, 56, 56, 0.15); color: var(--danger);"
            } padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
              ${student.RiskLevel}
            </span>
          </td>
          <td style="padding: 1rem; text-align: center;">
            <a href="/student/${student.Name}" style="color: var(--brand-3); text-decoration: none; font-weight: 600; font-size: 0.85rem;">
              View Profile →
            </a>
          </td>
        </tr>
      `,
      )
      .join("");
  } catch (error) {
    console.error("Error loading students table:", error);
  }
}

async function loadInterventions() {
  try {
    const response = await fetch("/api/interventions");
    if (!response.ok) throw new Error("Failed to load interventions");

    const { interventions } = await response.json();
    const container = document.getElementById("interventionsContainer");

    if (interventions.length === 0) {
      container.innerHTML = `<p style="color: var(--text-soft); text-align: center;">No interventions required. All students are performing well!</p>`;
      return;
    }

    container.innerHTML = interventions
      .map(
        (intervention) => `
        <div style="padding: 1rem; background: ${intervention.status === "Critical" ? "rgba(201, 56, 56, 0.08)" : "rgba(217, 119, 6, 0.08)"}; border-left: 3px solid ${intervention.status === "Critical" ? "var(--danger)" : "var(--warning)"}; border-radius: 8px; display: grid; grid-template-columns: 1fr auto; gap: 1rem; align-items: center;">
          <div>
            <p style="margin: 0; font-weight: 600; color: var(--text);">${intervention.name}</p>
            <p style="margin: 0.4rem 0 0; font-size: 0.9rem; color: var(--text-soft);">
              Status: <strong>${intervention.status}</strong> | Avg: ${intervention.average} | Reason: ${intervention.reason}
            </p>
            <p style="margin: 0.3rem 0 0; font-size: 0.8rem; color: var(--text-soft);">Assigned: ${intervention.assigned_date}</p>
          </div>
          <a href="/student/${intervention.name}" style="padding: 0.6rem 1.2rem; background: linear-gradient(135deg, var(--brand) 0%, var(--brand-3) 100%); color: #fff; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.85rem; white-space: nowrap;">
            View Plan
          </a>
        </div>
      `,
      )
      .join("");
  } catch (error) {
    console.error("Error loading interventions:", error);
  }
}

// Load dashboard on page load
document.addEventListener("DOMContentLoaded", loadDashboard);
