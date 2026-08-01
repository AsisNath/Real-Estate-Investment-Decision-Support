const summaryEl = document.querySelector("#kbSummary");
const listEl = document.querySelector("#kbList");
const filterEl = document.querySelector("#kbFilter");
const addForm = document.querySelector("#addNoteForm");
const resultEl = document.querySelector("#addNoteResult");
const scopeSelect = document.querySelector("#scopeSelect");
const valueField = document.querySelector("#valueField");
const valueLabel = document.querySelector("#valueLabel");
const valueInput = document.querySelector("#valueInput");
const stateField = document.querySelector("#stateField");
const viewer = document.querySelector("#noteViewer");
const noteTitle = document.querySelector("#noteTitle");
const noteMeta = document.querySelector("#noteMeta");
const noteBody = document.querySelector("#noteBody");

let allNotes = [];

const SCOPE_FIELDS = {
  zip: { label: "ZIP code", placeholder: "78704", needsState: false },
  state: { label: "State", placeholder: "TX", needsState: false },
  city: { label: "City", placeholder: "Austin", needsState: true },
  property: { label: "Address", placeholder: "725 N Delaware St 46202", needsState: false },
  global: { label: "", placeholder: "", needsState: false },
  custom: { label: "Folder path", placeholder: "lenders/acme_bank", needsState: false },
};

const TEMPLATE = `# Policy Notes - [Place]

**Property context:** [what this covers]
**Researched:** ${new Date().toISOString().slice(0, 10)}
**Method:** [where these facts came from]

## 1. Restriction or rule

- [Fact.] - [Source name](https://example.gov) - as of ${new Date()
  .toISOString()
  .slice(0, 10)} official

## 5. High-Attention Flags (summary for NorthStar report)

| Flag | Severity | Why |
|---|---|---|
| [Short flag title] | HIGH | [Why it could change the decision] |

## NorthStar Machine-Readable Summary

- rent_growth_cap_percent: 3
- short_term_rental_allowed: false
`;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function severityChips(counts) {
  return ["high", "medium", "low"]
    .filter((level) => counts[level] > 0)
    .map((level) => `<span class="badge ${level}">${counts[level]} ${level}</span>`)
    .join("");
}

function sourceBadge(source) {
  const labels = { researched: "AI-researched", user: "Added by you", legacy: "Legacy folder" };
  const classes = { researched: "low", user: "medium", legacy: "" };
  return `<span class="badge source-badge ${classes[source] || ""}">${labels[source] || source}</span>`;
}

function renderSummary(data) {
  if (data.note_count === 0) {
    summaryEl.innerHTML = `
      <h2>No notes yet</h2>
      <p>Add a local policy note on the right, or run the <code>property-policy-research</code> Skill to generate one.</p>
      <p class="muted">Folder: <code>${escapeHtml(data.folder_path)}</code></p>
    `;
    return;
  }

  summaryEl.innerHTML = `
    <div class="kb-stats">
      <article><span>Notes</span><strong>${data.note_count}</strong></article>
      <article><span>High-attention flags</span><strong>${data.high_flag_total}</strong></article>
      <article><span>Stale (over ${data.stale_after_days} days)</span><strong>${data.stale_count}</strong></article>
    </div>
    <p class="muted">Folder: <code>${escapeHtml(data.folder_path)}</code></p>
  `;
}

function renderList(notes) {
  if (notes.length === 0) {
    listEl.innerHTML = `<p class="muted">No notes match this filter.</p>`;
    return;
  }

  listEl.innerHTML = notes
    .map((note) => {
      const citations =
        note.official_citations + note.secondary_citations > 0
          ? `${note.official_citations} official / ${note.secondary_citations} secondary citations`
          : "No tagged citations";
      const freshness = note.researched
        ? `Researched ${escapeHtml(note.researched)}${
            note.days_old !== null ? ` (${note.days_old} days ago)` : ""
          }`
        : "No research date recorded";
      return `
        <article class="kb-note ${note.is_stale ? "stale" : ""}">
          <div class="kb-note-head">
            <h3>${escapeHtml(note.place)}</h3>
            ${sourceBadge(note.source)}${severityChips(note.flag_counts)}
          </div>
          <p class="kb-note-scope">${escapeHtml(note.applies_to)}</p>
          <p class="kb-note-meta">${freshness} &middot; ${citations}${
        note.diligence_count ? ` &middot; ${note.diligence_count} diligence items` : ""
      }</p>
          ${note.is_stale ? `<p class="kb-stale-warning">Older than the freshness window - re-run the research Skill before relying on it.</p>` : ""}
          <p class="kb-note-path"><code>${escapeHtml(note.relative_path)}</code></p>
          <button type="button" class="secondary-action" data-path="${escapeHtml(note.relative_path)}">View note</button>
        </article>
      `;
    })
    .join("");
}

function renderTraces(traces) {
  const panel = document.querySelector("#tracePanel");
  const list = document.querySelector("#traceList");
  if (!traces || traces.length === 0) {
    panel.classList.add("hidden");
    return;
  }

  panel.classList.remove("hidden");
  list.innerHTML = traces
    .map(
      (trace) => `
        <article class="kb-note trace">
          <div class="kb-note-head">
            <h3>${escapeHtml(trace.applies_to)}</h3>
            <span class="badge low">${trace.entry_count} run${trace.entry_count === 1 ? "" : "s"}</span>
          </div>
          <p class="kb-note-path"><code>${escapeHtml(trace.relative_path)}</code></p>
          <button type="button" class="secondary-action" data-trace="${escapeHtml(trace.relative_path)}">View trail</button>
        </article>
      `
    )
    .join("");
}

async function loadInventory() {
  const response = await fetch("/api/knowledge-bank");
  const data = await response.json();
  allNotes = data.notes;
  renderSummary(data);
  renderTraces(data.traces);
  applyFilter();
}

function applyFilter() {
  const term = filterEl.value.trim().toLowerCase();
  const filtered = term
    ? allNotes.filter((note) =>
        `${note.place} ${note.applies_to} ${note.relative_path}`.toLowerCase().includes(term)
      )
    : allNotes;
  renderList(filtered);
}

function showInViewer(title, meta, html) {
  noteTitle.textContent = title;
  noteMeta.textContent = meta;
  noteBody.innerHTML = html;
  viewer.classList.remove("hidden");
  viewer.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function openNote(path) {
  const response = await fetch(`/api/knowledge-bank/note?path=${encodeURIComponent(path)}`);
  if (!response.ok) return;
  const note = await response.json();

  const sourceLabels = { researched: "AI-researched", user: "Added by you", legacy: "Legacy folder" };
  const bits = [sourceLabels[note.source] || note.source, note.applies_to];
  if (note.researched) bits.push(`Researched ${note.researched}`);
  bits.push(`${note.official_citations} official / ${note.secondary_citations} secondary citations`);
  showInViewer(note.place || note.name, bits.join(" · "), note.html);
}

async function openTrace(path) {
  const response = await fetch(`/api/knowledge-bank/trace?path=${encodeURIComponent(path)}`);
  if (!response.ok) return;
  const trace = await response.json();

  showInViewer(
    `Analysis trail - ${trace.applies_to}`,
    "Written by NorthStar on each analysis. Never read back into a report.",
    trace.html
  );
}

function syncScopeFields() {
  const config = SCOPE_FIELDS[scopeSelect.value];
  valueField.classList.toggle("hidden", !config.label);
  stateField.classList.toggle("hidden", !config.needsState);
  valueLabel.textContent = config.label;
  valueInput.placeholder = config.placeholder;
}

listEl.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-path]");
  if (button) openNote(button.dataset.path);
});

document.querySelector("#traceList").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-trace]");
  if (button) openTrace(button.dataset.trace);
});

document.querySelector("#closeNote").addEventListener("click", () => {
  viewer.classList.add("hidden");
});

document.querySelector("#templateButton").addEventListener("click", () => {
  document.querySelector("#contentInput").value = TEMPLATE;
});

filterEl.addEventListener("input", applyFilter);
scopeSelect.addEventListener("change", syncScopeFields);

addForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  resultEl.classList.remove("hidden", "error");
  resultEl.textContent = "Saving...";

  const payload = {
    scope: scopeSelect.value,
    value: valueInput.value.trim(),
    state: document.querySelector("#stateInput").value.trim(),
    filename: document.querySelector("#filenameInput").value.trim() || "policy-notes.md",
    content: document.querySelector("#contentInput").value,
    overwrite: document.querySelector("#overwriteInput").checked,
  };

  try {
    const response = await fetch("/api/knowledge-bank/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok) {
      resultEl.classList.add("error");
      resultEl.textContent = data.detail || "Could not save the note.";
      return;
    }

    resultEl.textContent = `Saved to ${data.relative_path}. Applies to: ${data.applies_to}.${
      data.flag_count ? ` ${data.flag_count} flag(s) will appear in matching reports.` : ""
    }`;
    document.querySelector("#contentInput").value = "";
    loadInventory();
  } catch (error) {
    resultEl.classList.add("error");
    resultEl.textContent = `Could not save the note: ${error.message}`;
  }
});

syncScopeFields();
loadInventory();
