const state = {
  students: [],
  questions: [
    "What is my average?",
    "Explain Python loops.",
    "Give me 10 SQL interview questions.",
    "Explain CNN.",
    "Create a study plan for Machine Learning.",
    "Who is the topper?"
  ],
};

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Converts a markdown string to safe HTML.
 * Supports: headings, bold, italic, inline code, fenced code blocks,
 * ordered/unordered lists, blockquotes, horizontal rules, and tables.
 */

/**
 * Processes inline markdown syntax (bold, italic, inline code) into HTML.
 * Defined at module level so it can be used by both markdownToHtml() and renderResultHtml().
 */
function inlineMarkdown(text) {
  // Escape HTML first
  let t = String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  // Bold + italic
  t = t.replace(/\*\*\*(.*?)\*\*\*/g, "<strong><em>$1</em></strong>");
  // Bold
  t = t.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  t = t.replace(/__(.*?)__/g, "<strong>$1</strong>");
  // Italic
  t = t.replace(/\*(.*?)\*/g, "<em>$1</em>");
  t = t.replace(/_(.*?)_/g, "<em>$1</em>");
  // Inline code
  t = t.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');
  return t;
}

function markdownToHtml(md) {
  if (!md) return "";

  const lines = md.split("\n");
  let html = "";
  let inCodeBlock = false;
  let codeLang = "";
  let codeLines = [];
  let inTable = false;
  let tableRows = [];
  let inUnorderedList = false;
  let inOrderedList = false;

  function flushList() {
    if (inUnorderedList) {
      html += "</ul>";
      inUnorderedList = false;
    }
    if (inOrderedList) {
      html += "</ol>";
      inOrderedList = false;
    }
  }

  function flushTable() {
    if (!inTable) return;
    inTable = false;
    if (tableRows.length === 0) return;
    let tableHtml = '<table class="md-table">';
    tableRows.forEach((row, idx) => {
      const cells = row.split("|").map(c => c.trim()).filter((_, i, a) => i > 0 && i < a.length - 1);
      if (idx === 0) {
        tableHtml += "<thead><tr>" + cells.map(c => `<th>${inlineMarkdown(c)}</th>`).join("") + "</tr></thead><tbody>";
      } else if (idx === 1 && /^[\s|:-]+$/.test(row)) {
        // separator row — skip
      } else {
        tableHtml += "<tr>" + cells.map(c => `<td>${inlineMarkdown(c)}</td>`).join("") + "</tr>";
      }
    });
    tableHtml += "</tbody></table>";
    html += tableHtml;
    tableRows = [];
  }


  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];

    // --- Fenced code block ---
    if (/^```/.test(raw)) {
      if (!inCodeBlock) {
        flushList();
        flushTable();
        inCodeBlock = true;
        codeLang = raw.slice(3).trim() || "";
        codeLines = [];
      } else {
        inCodeBlock = false;
        const langLabel = codeLang ? `<span class="md-code-lang">${escapeHtml(codeLang)}</span>` : "";
        html += `<div class="md-code-block">${langLabel}<pre><code>${codeLines.map(l => escapeHtml(l)).join("\n")}</code></pre></div>`;
        codeLang = "";
        codeLines = [];
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(raw);
      continue;
    }

    // --- Table ---
    if (/\|/.test(raw) && raw.trim().startsWith("|")) {
      flushList();
      if (!inTable) inTable = true;
      tableRows.push(raw);
      continue;
    } else if (inTable) {
      flushTable();
    }

    // --- Horizontal rule ---
    if (/^(---+|===+|\*\*\*+)\s*$/.test(raw.trim())) {
      flushList();
      html += "<hr class=\"md-hr\">";
      continue;
    }

    // --- Headings ---
    const h6 = raw.match(/^#{6}\s+(.*)/);
    const h5 = raw.match(/^#{5}\s+(.*)/);
    const h4 = raw.match(/^#{4}\s+(.*)/);
    const h3 = raw.match(/^#{3}\s+(.*)/);
    const h2 = raw.match(/^#{2}\s+(.*)/);
    const h1 = raw.match(/^#\s+(.*)/);
    if (h6) { flushList(); html += `<h6 class="md-h6">${inlineMarkdown(h6[1])}</h6>`; continue; }
    if (h5) { flushList(); html += `<h5 class="md-h5">${inlineMarkdown(h5[1])}</h5>`; continue; }
    if (h4) { flushList(); html += `<h4 class="md-h4">${inlineMarkdown(h4[1])}</h4>`; continue; }
    if (h3) { flushList(); html += `<h3 class="md-h3">${inlineMarkdown(h3[1])}</h3>`; continue; }
    if (h2) { flushList(); html += `<h2 class="md-h2">${inlineMarkdown(h2[1])}</h2>`; continue; }
    if (h1) { flushList(); html += `<h1 class="md-h1">${inlineMarkdown(h1[1])}</h1>`; continue; }

    // --- Blockquote ---
    const bq = raw.match(/^>\s?(.*)/);
    if (bq) {
      flushList();
      html += `<blockquote class="md-blockquote">${inlineMarkdown(bq[1])}</blockquote>`;
      continue;
    }

    // --- Unordered list item ---
    const ulItem = raw.match(/^[\s]*[-*+]\s+(.*)/);
    if (ulItem) {
      if (inOrderedList) { html += "</ol>"; inOrderedList = false; }
      if (!inUnorderedList) { html += '<ul class="md-ul">'; inUnorderedList = true; }
      html += `<li>${inlineMarkdown(ulItem[1])}</li>`;
      continue;
    }

    // --- Ordered list item ---
    const olItem = raw.match(/^[\s]*\d+\.\s+(.*)/);
    if (olItem) {
      if (inUnorderedList) { html += "</ul>"; inUnorderedList = false; }
      if (!inOrderedList) { html += '<ol class="md-ol">'; inOrderedList = true; }
      html += `<li>${inlineMarkdown(olItem[1])}</li>`;
      continue;
    }

    // --- Blank line ---
    if (raw.trim() === "") {
      flushList();
      continue;
    }

    // --- Default paragraph ---
    flushList();
    html += `<p class="md-p">${inlineMarkdown(raw)}</p>`;
  }

  // Flush any open blocks
  flushList();
  flushTable();
  if (inCodeBlock && codeLines.length) {
    html += `<div class="md-code-block"><pre><code>${codeLines.map(l => escapeHtml(l)).join("\n")}</code></pre></div>`;
  }

  return html;
}

function setDateChip() {
  const date = new Date().toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  document.getElementById("liveDate").textContent = `Updated ${date}`;
}


function renderStudentFocusOptions() {
  const select = document.getElementById("studentFocus");
  if (!select || !state.students.length) {
    return;
  }

  const options = [
    '<option value="">Auto-detect from prompt</option>',
    ...state.students.map((student) => `<option value="${escapeHtml(student.Name)}">${escapeHtml(student.Name)}</option>`),
  ];
  select.innerHTML = options.join("");
}

function renderPromptRow() {
  const container = document.getElementById("promptRow");
  const suggestions = state.questions.slice(0, 4);
  container.innerHTML = suggestions
    .map(
      (question) => `
        <button type="button" class="chat-suggestion" data-question="${escapeHtml(question)}">${escapeHtml(question)}</button>
      `,
    )
    .join("");

  container.querySelectorAll("[data-question]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById("chatInput");
      input.value = button.dataset.question;
      input.focus();
    });
  });
}

function renderSuggestionButtons() {
  const container = document.getElementById("chatSuggestions");
  container.innerHTML = state.questions
    .map(
      (question) => `
        <button type="button" class="chat-suggestion" data-question="${escapeHtml(question)}">${escapeHtml(question)}</button>
      `,
    )
    .join("");

  container.querySelectorAll("[data-question]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById("chatInput");
      input.value = button.dataset.question;
      input.focus();
    });
  });
}

function appendMessage(role, bodyHtml, metaText) {
  const thread = document.getElementById("chatThread");
  const message = document.createElement("article");
  message.className = `chat-message chat-message--${role}`;
  message.innerHTML = `
    <div class="chat-message__meta">${escapeHtml(metaText || (role === "user" ? "You" : "EduRank Agent"))}</div>
    <div class="chat-message__body">${bodyHtml}</div>
  `;
  thread.appendChild(message);
  thread.scrollTop = thread.scrollHeight;
  return message;
}

function renderResultHtml(result) {
  const intent = escapeHtml(result.intent || "agent_response");
  // Use markdownToHtml for rich structured formatting of AI answers
  const answerHtml = markdownToHtml(result.answer || "No response generated.");
  const studentLabel = result.student_name
    ? `<span class="chat-pill">${escapeHtml(result.student_name)}</span>`
    : "";

  const traceHtml = Array.isArray(result.tool_trace) && result.tool_trace.length
    ? `<div class="chat-message__pill-row">${result.tool_trace.map((item) => `<span class="chat-pill">${escapeHtml(item)}</span>`).join("")}</div>`
    : "";

  const highlightsHtml = Array.isArray(result.highlights) && result.highlights.length
    ? `<ul class="chat-message__highlights">${result.highlights.map((item) => `<li>${inlineMarkdown(escapeHtml(item))}</li>`).join("")}</ul>`
    : "";

  const actionsHtml = Array.isArray(result.actions) && result.actions.length
    ? `<ul class="chat-message__actions">${result.actions.map((item) => `<li>${inlineMarkdown(escapeHtml(item))}</li>`).join("")}</ul>`
    : `<p class="chat-message__text" style="margin-top: 0.75rem; color: var(--text-soft);">No follow-up actions were generated.</p>`;

  return `
    <div class="chat-message__pill-row" style="margin-top: 0; margin-bottom: 0.6rem;">
      <span class="chat-pill">${intent}</span>
      ${studentLabel}
    </div>
    <div class="md-answer">${answerHtml}</div>
    ${traceHtml}
    ${highlightsHtml}
    ${actionsHtml}
  `;
}

function seedGreeting() {
  const thread = document.getElementById("chatThread");
  if (thread.childElementCount > 0) {
    return;
  }

  appendMessage(
    "assistant",
    `
      <p class="chat-message__text">Welcome! I am your <strong>Student Data Agent &amp; Learning Assistant</strong>.</p>
      <p class="chat-message__text">You can ask me questions about your academic data, or ask general study topics, coding questions, and tutorials.</p>
      <div class="chat-message__pill-row">
        <span class="chat-pill">What is my average?</span>
        <span class="chat-pill">Explain Python loops.</span>
        <span class="chat-pill">Explain CNN.</span>
        <span class="chat-pill">Give me 10 SQL interview questions.</span>
      </div>
    `,
    "EduRank AI Agent",
  );
}

async function sendQuestion() {
  const input = document.getElementById("chatInput");
  const sendButton = document.getElementById("chatSend");
  const studentFocus = document.getElementById("studentFocus");
  const question = input.value.trim();
  const studentName = studentFocus.value;

  if (!question) {
    return;
  }

  appendMessage("user", `<p class="chat-message__text">${escapeHtml(question)}</p>`, "You");
  input.value = "";
  input.focus();

  const typingBubble = appendMessage("assistant", `<p class="chat-message__text" style="color: var(--text-soft);">Thinking through the dataset...</p>`, "EduRank Agent");
  sendButton.disabled = true;
  sendButton.textContent = "Sending...";

  try {
    const response = await fetch("/api/agent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, student_name: studentName }),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Agent request failed");
    }

    typingBubble.innerHTML = `
      <div class="chat-message__meta">EduRank Agent</div>
      <div class="chat-message__body">${renderResultHtml(result)}</div>
    `;
  } catch (error) {
    typingBubble.innerHTML = `
      <div class="chat-message__meta">EduRank Agent</div>
      <div class="chat-message__body"><p class="chat-message__text" style="color: var(--danger);">${escapeHtml(error.message)}</p></div>
    `;
  } finally {
    sendButton.disabled = false;
    sendButton.textContent = "Send Message";
  }
}

async function loadChatContext() {
  try {
    const response = await fetch("/api/analysis");
    if (!response.ok) {
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      throw new Error("Failed to load analysis data");
    }

    const data = await response.json();
    state.students = Array.isArray(data.students) ? data.students : [];
    state.questions = [
      "What is my average?",
      "Explain Python loops.",
      "Give me 10 SQL interview questions.",
      "Explain CNN.",
      "Create a study plan for Machine Learning.",
      "Who is the topper?"
    ];

    renderStudentFocusOptions();
    renderPromptRow();
    renderSuggestionButtons();
  } catch (error) {
    console.error("Failed to load chat context:", error.message);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setDateChip();
  seedGreeting();
  loadChatContext();

  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await sendQuestion();
  });

  input.addEventListener("keydown", async (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await sendQuestion();
    }
  });
});
