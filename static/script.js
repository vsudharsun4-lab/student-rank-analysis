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

function renderTopThree(topThree) {
  const container = document.getElementById("topThree");
  container.innerHTML = topThree
    .map(
      (item, index) => `
      <article class="leader">
        <div class="leader__position">Rank #${index + 1}</div>
        <div class="leader__name">${item.Name}</div>
        <div class="leader__meta">Total ${item.Total} | Grade ${item.Grade}</div>
      </article>
    `,
    )
    .join("");
}

function renderSubjectToppers(subjectToppers) {
  const container = document.getElementById("subjectToppers");
  container.innerHTML = Object.entries(subjectToppers)
    .map(
      ([subject, topper]) => `
      <article class="subject">
        <h4>${subject} Topper</h4>
        <strong>${topper.name}</strong>
        <div class="subject__meta">Score ${topper.marks}</div>
      </article>
    `,
    )
    .join("");
}

function renderSubjectIntelligence(subjectIntelligence) {
  const container = document.getElementById("subjectIntelligence");
  container.innerHTML = Object.entries(subjectIntelligence)
    .map(
      ([subject, metrics]) => `
      <article class="subject">
        <h4>${subject}</h4>
        <div class="subject__meta">Average ${metrics.average}</div>
        <div class="subject__meta">High ${metrics.highest} | Low ${metrics.lowest}</div>
        <div class="subject__meta">Variance ${metrics.variance}</div>
      </article>
    `,
    )
    .join("");
}

function buildPersonCard(item) {
  return `
    <article class="list-card">
      <strong>${item.name}</strong>
      <p>Rank ${item.rank} | Grade ${item.grade} | ${item.result}</p>
      <p>Total ${item.total} | Average ${item.average} | Percentile ${item.percentile}%</p>
      <p>Risk Level ${item.risk}</p>
    </article>
  `;
}

function renderBriefKpis(aiBrief) {
  const profile = aiBrief.class_profile;
  const risk = aiBrief.risk_breakdown;
  const metrics = [
    { label: "Pass Rate", value: `${profile.pass_rate}%` },
    { label: "Class Avg", value: profile.class_average },
    { label: "Median Avg", value: profile.median_average },
    { label: "Consistency", value: profile.consistency },
    { label: "Score Spread", value: profile.score_spread },
    { label: "High Risk", value: risk.High },
  ];

  document.getElementById("briefKpis").innerHTML = metrics
    .map(
      (metric) => `
        <div class="brief-kpi">
          <span>${metric.label}</span>
          <strong>${metric.value}</strong>
        </div>
      `,
    )
    .join("");
}

function renderRiskBreakdown(riskBreakdown) {
  document.getElementById("riskBreakdown").innerHTML = `
    <div class="risk-pill risk-pill--low">Low ${riskBreakdown.Low}</div>
    <div class="risk-pill risk-pill--medium">Medium ${riskBreakdown.Medium}</div>
    <div class="risk-pill risk-pill--high">High ${riskBreakdown.High}</div>
  `;
}

function renderSubjectFocus(subjectFocus) {
  document.getElementById("subjectFocusList").innerHTML = subjectFocus
    .map(
      (item) => `
        <article class="list-card">
          <strong>${item.subject}</strong>
          <p>Average ${item.average}</p>
          <p>Priority ${item.priority}</p>
        </article>
      `,
    )
    .join("");
}

function renderAiBrief(aiBrief) {
  document.getElementById("momentumScore").textContent = `Momentum ${aiBrief.momentum.score} (${aiBrief.momentum.status})`;
  document.getElementById("aiNarrative").textContent = aiBrief.narrative;
  renderBriefKpis(aiBrief);
  renderRiskBreakdown(aiBrief.risk_breakdown);
  renderSubjectFocus(aiBrief.subject_focus);

  document.getElementById("aiInsightList").innerHTML = aiBrief.insights
    .map((insight) => `<li>${insight}</li>`)
    .join("");

  document.getElementById("standoutList").innerHTML = aiBrief.standout_performers
    .map(buildPersonCard)
    .join("");

  document.getElementById("interventionList").innerHTML = aiBrief.intervention_candidates
    .map(buildPersonCard)
    .join("");

  document.getElementById("nearPassList").innerHTML = aiBrief.near_pass_students.length
    ? aiBrief.near_pass_students.map(buildPersonCard).join("")
    : `<article class="list-card"><strong>No near-pass students</strong><p>Current cohort has either clear pass or deeper support requirements.</p></article>`;

  document.getElementById("actionList").innerHTML = aiBrief.actions
    .map((action) => `<li>${action}</li>`)
    .join("");
}

function gradeColorMap(grade) {
  const colors = {
    A: "#1f8f5f",
    B: "#0f9d7a",
    C: "#2e6fff",
    D: "#d97706",
    F: "#c93838",
  };
  return colors[grade] || "#5b6770";
}

function getFilteredStudents() {
  return state.students.filter((student) => {
    const nameMatch = student.Name.toLowerCase().includes(state.filters.search);
    const riskMatch = state.filters.risk === "all" || student.RiskLevel === state.filters.risk;
    return nameMatch && riskMatch;
  });
}

function renderStudentTableHead(subjects) {
  const thead = document.getElementById("studentTableHead");
  const subjectHeaders = subjects.map((subject) => `<th>${subject}</th>`).join("");

  thead.innerHTML = `
    <tr>
      <th>Rank</th>
      <th>Name</th>
      ${subjectHeaders}
      <th>Total</th>
      <th>Average</th>
      <th>Percentile</th>
      <th>Consistency</th>
      <th>Grade</th>
      <th>Risk</th>
      <th>Result</th>
    </tr>
  `;
}

function renderStudentRows(students, subjects) {
  const tbody = document.getElementById("studentRows");
  if (!students.length) {
    tbody.innerHTML = `<tr><td colspan="${subjects.length + 9}">No students match this filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = students
    .map((student) => {
      const resultClass = student.Result === "Pass" ? "badge--pass" : "badge--fail";
      const subjectCells = subjects
        .map((subject) => `<td>${student[subject]}</td>`)
        .join("");

      return `
        <tr>
          <td>${student.Rank}</td>
          <td>${student.Name}</td>
          ${subjectCells}
          <td>${student.Total}</td>
          <td>${Number(student.Average).toFixed(2)}</td>
          <td>${Number(student.Percentile).toFixed(2)}%</td>
          <td>${Number(student.Consistency).toFixed(2)}</td>
          <td style="color:${gradeColorMap(student.Grade)};font-weight:700;">${student.Grade}</td>
          <td><span class="risk risk--${student.RiskLevel}">${student.RiskLevel}</span></td>
          <td><span class="badge ${resultClass}">${student.Result}</span></td>
        </tr>
      `;
    })
    .join("");
}

function destroyCharts() {
  Object.values(state.charts).forEach((chart) => {
    if (chart) chart.destroy();
  });
}

function metricLabel(metric) {
  const labels = {
    average: "Average Marks",
    highest: "Highest Marks",
    lowest: "Lowest Marks",
    variance: "Variance",
  };
  return labels[metric] || "Average Marks";
}

function metricYAxisMax(metric) {
  if (metric === "variance") {
    return undefined;
  }
  return 100;
}

function renderSubjectMetricChart() {
  const subjectIntelligence = state.subjectIntelligence;
  const metric = state.subjectMetric;
  const selectedSubjects = state.selectedSubjects;

  const selectedEntries = Object.entries(subjectIntelligence).filter(([subject]) =>
    selectedSubjects.includes(subject),
  );

  const labels = selectedEntries.map(([subject]) => subject);
  const values = selectedEntries.map(([, metrics]) => Number(metrics[metric]));

  if (state.charts.subjectAverage) {
    state.charts.subjectAverage.destroy();
  }

  state.charts.subjectAverage = new Chart(document.getElementById("subjectAverageChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: metricLabel(metric),
          data: values,
          backgroundColor: labels.map((_, index) => {
            const palette = ["#0f9d7a", "#2e6fff", "#ff7c43", "#1f8f5f", "#d97706", "#5b6770"];
            return palette[index % palette.length];
          }),
          borderRadius: 10,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          beginAtZero: true,
          max: metricYAxisMax(metric),
          ticks: { precision: 0 },
        },
      },
    },
  });
}

function renderSubjectSelector() {
  const container = document.getElementById("subjectSelector");
  container.innerHTML = state.subjects
    .map(
      (subject) => `
        <label class="subject-selector__item">
          <input
            type="checkbox"
            value="${subject}"
            ${state.selectedSubjects.includes(subject) ? "checked" : ""}
          >
          <span>${subject}</span>
        </label>
      `,
    )
    .join("");
}

function renderCharts(gradeDistribution, resultDistribution) {
  destroyCharts();

  state.charts.grade = new Chart(document.getElementById("gradeChart"), {
    type: "bar",
    data: {
      labels: Object.keys(gradeDistribution),
      datasets: [
        {
          label: "Students",
          data: Object.values(gradeDistribution),
          backgroundColor: ["#1f8f5f", "#0f9d7a", "#2e6fff", "#f59e0b", "#dc2626"],
          borderRadius: 10,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });

  state.charts.result = new Chart(document.getElementById("resultChart"), {
    type: "doughnut",
    data: {
      labels: Object.keys(resultDistribution),
      datasets: [
        {
          data: Object.values(resultDistribution),
          backgroundColor: Object.keys(resultDistribution).map((label) =>
            label === "Pass" ? "#1f8f5f" : "#dc2626",
          ),
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
    },
  });

  renderSubjectMetricChart();
}

function renderFilteredTable() {
  const filteredStudents = getFilteredStudents();
  const tableStats = document.getElementById("tableStats");
  tableStats.textContent = `Showing ${filteredStudents.length} of ${state.students.length} students`;
  renderStudentRows(filteredStudents, state.subjects);
}

function attachControls() {
  const searchInput = document.getElementById("searchInput");
  const riskFilter = document.getElementById("riskFilter");
  const subjectMetric = document.getElementById("subjectMetric");
  const subjectSelector = document.getElementById("subjectSelector");

  searchInput.addEventListener("input", () => {
    state.filters.search = searchInput.value.trim().toLowerCase();
    renderFilteredTable();
  });

  riskFilter.addEventListener("change", () => {
    state.filters.risk = riskFilter.value;
    renderFilteredTable();
  });

  subjectMetric.addEventListener("change", () => {
    state.subjectMetric = subjectMetric.value;
    renderSubjectMetricChart();
  });

  subjectSelector.addEventListener("change", () => {
    const selected = Array.from(subjectSelector.querySelectorAll("input[type='checkbox']:checked"))
      .map((input) => input.value);

    if (!selected.length) {
      renderSubjectSelector();
      return;
    }

    state.selectedSubjects = selected;
    renderSubjectMetricChart();
  });
}

async function loadDashboard() {
  setDateChip();
  const response = await fetch("/api/analysis");
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }

  const payload = await response.json();
  state.students = payload.students;
  state.subjects = payload.subjects;
  state.selectedSubjects = [...payload.subjects];
  state.subjectIntelligence = payload.subject_intelligence;

  renderKpis(payload.summary);
  renderAiBrief(payload.ai_brief);
  renderTopThree(payload.top_3);
  renderSubjectToppers(payload.subject_toppers);
  renderSubjectIntelligence(payload.subject_intelligence);
  renderSubjectSelector();
  renderStudentTableHead(state.subjects);
  renderCharts(payload.grade_distribution, payload.result_distribution);
  renderFilteredTable();
  attachControls();
}

loadDashboard().catch((error) => {
  const kpiContainer = document.getElementById("kpis");
  kpiContainer.innerHTML = `<article class="kpi"><p class="kpi__label">Dashboard Status</p><p class="kpi__value">Failed to load</p><div class="kpi__note">${error.message}</div></article>`;
});
