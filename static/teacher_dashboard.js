function updateDate() {
  const options = { weekday: "short", month: "short", day: "numeric", year: "numeric" };
  document.getElementById("liveDate").textContent = new Date().toLocaleDateString("en-US", options);
}

function setUploadMessage(message, variant) {
  const messageEl = document.getElementById("uploadMessage");
  messageEl.textContent = message;
  messageEl.className = `upload-message upload-message--${variant}`;
}

function renderSchema(schema) {
  const columnsEl = document.getElementById("schemaColumns");
  columnsEl.innerHTML = "";

  schema.columns.forEach((column) => {
    const chip = document.createElement("span");
    chip.className = "schema-chip";
    chip.textContent = column;
    columnsEl.appendChild(chip);
  });

  document.getElementById("schemaInfo").textContent = `Current dataset: ${schema.student_count} students, ${schema.subjects.length} subjects`;
}

function updateTemplateDownloadLink() {
  const input = document.getElementById("templateSubjectCount");
  const link = document.getElementById("downloadTemplateBtn");
  if (!input || !link) {
    return;
  }

  const parsed = Number.parseInt(input.value, 10);
  const boundedCount = Number.isNaN(parsed) ? 6 : Math.min(20, Math.max(1, parsed));
  input.value = String(boundedCount);
  link.href = `/api/teacher/template?subject_count=${boundedCount}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderPreview(rows) {
  const container = document.getElementById("previewContainer");
  if (!rows || rows.length === 0) {
    container.innerHTML = '<p class="teacher-helper">No preview data returned.</p>';
    return;
  }

  const columns = Object.keys(rows[0]);
  const tableHead = columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("");
  const tableRows = rows
    .map((row) => {
      const cells = columns.map((column) => `<td>${escapeHtml(row[column])}</td>`).join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");

  container.innerHTML = `
    <div style="overflow-x: auto;">
      <table class="preview-table">
        <thead><tr>${tableHead}</tr></thead>
        <tbody>${tableRows}</tbody>
      </table>
    </div>
  `;
}

async function loadSchema() {
  try {
    const response = await fetch("/api/teacher/marks-schema");
    const payload = await response.json();

    if (!response.ok) {
      setUploadMessage(payload.error || "Could not load schema", "error");
      return;
    }

    renderSchema(payload);
  } catch (error) {
    setUploadMessage("Could not load schema", "error");
  }
}

async function uploadMarks(event) {
  event.preventDefault();

  const fileInput = document.getElementById("marksFile");
  const uploadBtn = document.getElementById("uploadBtn");

  if (!fileInput.files || fileInput.files.length === 0) {
    setUploadMessage("Please choose a CSV file", "error");
    return;
  }

  const formData = new FormData();
  formData.append("marks_file", fileInput.files[0]);

  uploadBtn.disabled = true;
  uploadBtn.textContent = "Uploading...";
  setUploadMessage("Uploading and validating marks file...", "neutral");

  try {
    const response = await fetch("/api/teacher/upload-marks", {
      method: "POST",
      body: formData,
    });

    const payload = await response.json();

    if (!response.ok) {
      setUploadMessage(payload.error || "Upload failed", "error");
      return;
    }

    setUploadMessage(payload.message || "Upload successful", "success");
    document.getElementById("uploadMeta").textContent = `Saved ${payload.student_count} students across ${payload.subjects.length} subjects. Updated: ${payload.updated_at}`;
    renderPreview(payload.preview || []);
    await loadSchema();
    fileInput.value = "";
  } catch (error) {
    setUploadMessage("Upload failed due to a network error", "error");
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Upload Marks";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  updateDate();
  loadSchema();
  updateTemplateDownloadLink();

  const templateCountInput = document.getElementById("templateSubjectCount");
  if (templateCountInput) {
    templateCountInput.addEventListener("change", updateTemplateDownloadLink);
    templateCountInput.addEventListener("input", updateTemplateDownloadLink);
  }

  document.getElementById("marksUploadForm").addEventListener("submit", uploadMarks);
});
