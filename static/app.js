const form = document.querySelector("#analysisForm");
const reportEl = document.querySelector("#report");
const emptyState = document.querySelector("#emptyState");
const loadingState = document.querySelector("#loadingState");
const sampleSelect = document.querySelector("#sampleSelect");

const numericFields = new Set([
  "purchase_price",
  "monthly_rent",
  "down_payment_percent",
  "interest_rate_percent",
  "loan_term_years",
  "annual_property_tax",
  "annual_insurance",
  "monthly_hoa_fee",
  "maintenance_percent_of_rent",
  "monthly_maintenance",
  "vacancy_percent",
  "property_management_percent",
  "annual_appreciation_percent",
  "annual_rent_growth_percent",
  "annual_expense_growth_percent",
  "closing_cost_percent",
  "selling_cost_percent",
]);

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const preciseCurrency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

function formatCurrency(value, precise = false) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
  return precise ? preciseCurrency.format(value) : currency.format(value);
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
  return Number(value).toFixed(digits);
}

function formatMultiple(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
  return `${Number(value).toFixed(2)}x`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

const locationNotice = document.querySelector("#locationNotice");

function renderLocationNotice(check) {
  if (!check || check.status === "ok") {
    locationNotice.classList.add("hidden");
    locationNotice.innerHTML = "";
    return;
  }

  const isWarning = check.status === "warning";
  const messages = isWarning ? check.warnings : check.unverified;
  if (!messages || messages.length === 0) {
    locationNotice.classList.add("hidden");
    locationNotice.innerHTML = "";
    return;
  }

  locationNotice.className = `location-notice ${isWarning ? "mismatch" : "unverified"}`;
  locationNotice.innerHTML = `
    <strong>${isWarning ? "City, state, and ZIP do not match" : "Could not fully verify this address"}</strong>
    <ul>${messages.map((message) => `<li>${escapeHtml(message)}</li>`).join("")}</ul>
  `;
}

async function checkLocationFields() {
  const city = form.elements.namedItem("city").value.trim();
  const state = form.elements.namedItem("state").value.trim();
  const zipCode = form.elements.namedItem("zip_code").value.trim();

  // Wait until all three fields are filled in before judging them.
  if (!city || state.length < 2 || zipCode.length < 5) {
    renderLocationNotice(null);
    return;
  }

  try {
    const response = await fetch("/api/location-check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ city, state: state.toUpperCase(), zip_code: zipCode }),
    });
    if (!response.ok) return;
    renderLocationNotice(await response.json());
  } catch (error) {
    // A failed check must never block the form.
    renderLocationNotice(null);
  }
}

["city", "state", "zip_code"].forEach((name) => {
  const input = form.elements.namedItem(name);
  input.addEventListener("change", checkLocationFields);
  input.addEventListener("blur", checkLocationFields);
});

function collectPayload() {
  const data = new FormData(form);
  const payload = {};
  for (const [key, value] of data.entries()) {
    payload[key] = numericFields.has(key) ? Number(value) : String(value).trim();
  }
  payload.state = payload.state.toUpperCase();
  return payload;
}

function setLoading(isLoading) {
  loadingState.classList.toggle("hidden", !isLoading);
  emptyState.classList.add("hidden");
  reportEl.classList.toggle("hidden", isLoading);
}

function metricCard(label, value, note = "") {
  return `
    <article class="metric-card">
      <span>${label}</span>
      <strong>${value}</strong>
      ${note ? `<small>${note}</small>` : ""}
    </article>
  `;
}

function badge(text, level = "medium") {
  return `<span class="badge ${level}">${text}</span>`;
}

function listItems(items, emptyText) {
  if (!items || items.length === 0) {
    return `<p class="muted">${emptyText}</p>`;
  }
  return `
    <div class="item-list">
      ${items
        .map(
          (item) => `
          <article class="list-item ${item.level || "neutral"}">
            <h4>${item.title}</h4>
            <p>${item.detail}</p>
          </article>
        `
        )
        .join("")}
    </div>
  `;
}

function policyFlags(flags) {
  if (!flags || flags.length === 0) {
    return `<p class="muted">No high-attention policy flags were found in the current policy record.</p>`;
  }

  return `
    <div class="policy-flags">
      ${flags
        .map(
          (flag) => `
            <article class="policy-flag ${flag.level || "medium"}">
              <div>
                <span>${flag.category}${flag.jurisdiction ? ` &middot; ${flag.jurisdiction}` : ""}</span>
                <h4>${flag.title}</h4>
              </div>
              ${badge(flag.level || "medium", flag.level || "medium")}
              <p>${flag.detail}</p>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function sourceLinks(links) {
  if (!links || links.length === 0) {
    return `<p class="muted">No online source links are attached to this policy record. Add local notes to the knowledge bank for this property.</p>`;
  }

  const groups = new Map();
  for (const link of links) {
    const jurisdiction = link.jurisdiction || "Other sources";
    if (!groups.has(jurisdiction)) groups.set(jurisdiction, []);
    groups.get(jurisdiction).push(link);
  }

  return [...groups.entries()]
    .map(
      ([jurisdiction, groupLinks]) => `
        <h5 class="jurisdiction-label">${jurisdiction}</h5>
        <div class="source-links">
          ${groupLinks
            .map(
              (link) => `
                <a href="${link.url}" target="_blank" rel="noopener noreferrer">
                  <span>${link.category}</span>
                  <strong>${link.label}</strong>
                </a>
              `
            )
            .join("")}
        </div>
      `
    )
    .join("");
}

function knowledgeBankPanel(knowledgeBank) {
  const documents = knowledgeBank.documents || [];
  const documentsHtml = documents.length
    ? documents
        .map((doc) => {
          const meta = [
            doc.researched ? `Researched ${escapeHtml(doc.researched)}` : "",
            doc.flag_count ? `${doc.flag_count} high-attention flag${doc.flag_count === 1 ? "" : "s"} applied to this report` : "",
          ]
            .filter(Boolean)
            .join(" &middot; ");
          const citations =
            doc.official_citations + doc.secondary_citations > 0
              ? `${doc.official_citations} official / ${doc.secondary_citations} secondary citations`
              : "";
          return `
            <details class="knowledge-doc">
              <summary>${escapeHtml(doc.place || doc.relative_path)}</summary>
              ${meta ? `<p class="doc-meta">${meta}</p>` : ""}
              ${citations ? `<p class="doc-meta">${citations}</p>` : ""}
              ${doc.is_stale ? `<p class="doc-meta stale-note">This note is ${doc.days_old} days old. Re-run the research Skill before relying on it.</p>` : ""}
              <p class="doc-meta">File: <code>${escapeHtml(doc.relative_path)}</code></p>
              <div class="note-body">${doc.html || `<pre>${escapeHtml(doc.excerpt)}</pre>`}</div>
            </details>
          `;
        })
        .join("")
    : `<p class="muted">No matching knowledge-bank policy files were found for this property.</p>`;

  return `
    <section class="report-section knowledge-bank">
      <div class="section-title">
        <div>
          <h3>Knowledge Bank Fallback</h3>
          <p>Use this folder for HOA rules, city policy notes, local law, lease restrictions, or manual due-diligence findings.</p>
        </div>
      </div>
      <div class="folder-callout">
        <strong>Folder to use now</strong>
        <code>${knowledgeBank.folder_path}</code>
      </div>
      <p class="muted">${knowledgeBank.instructions}</p>
      ${documentsHtml}
      <a class="kb-link" href="/knowledge-bank">Open the Knowledge Bank to browse or add notes &rarr;</a>
    </section>
  `;
}

function assumptionConflictsPanel(conflicts) {
  if (!conflicts || conflicts.length === 0) return "";

  return `
    <section class="report-section conflict-block">
      <div class="section-title">
        <div>
          <h3>Assumptions the Local Rules Do Not Support</h3>
          <p>Knowledge-bank notes record limits that contradict the numbers entered above.</p>
        </div>
      </div>
      <div class="item-list">
        ${conflicts
          .map(
            (conflict) => `
              <article class="list-item ${conflict.level}">
                <h4>${escapeHtml(conflict.title)}</h4>
                <p>${escapeHtml(conflict.detail)}</p>
              </article>
            `
          )
          .join("")}
      </div>
    </section>
  `;
}

function diligencePanel(items) {
  if (!items || items.length === 0) return "";

  return `
    <section class="report-section">
      <div class="section-title">
        <div>
          <h3>Diligence Checklist</h3>
          <p>Open questions the policy notes say must be confirmed before closing.</p>
        </div>
      </div>
      <ul class="diligence-list">
        ${items
          .map(
            (entry) => `
              <li>
                <span>${escapeHtml(entry.item)}</span>
                <code>${escapeHtml(entry.source_document)}</code>
              </li>
            `
          )
          .join("")}
      </ul>
    </section>
  `;
}

function locationCheckPanel(check) {
  if (!check) return "";

  const warnings = check.warnings || [];
  const unverified = check.unverified || [];
  if (warnings.length === 0 && unverified.length === 0) return "";

  const isWarning = check.status === "warning";
  const items = (isWarning ? warnings : unverified)
    .map((message) => `<li>${escapeHtml(message)}</li>`)
    .join("");
  const expected =
    isWarning && check.expected_city
      ? `<p class="muted">ZIP directory match: ${escapeHtml(check.expected_city)}, ${escapeHtml(
          check.expected_state || ""
        )} (${escapeHtml(check.expected_county || "")}).</p>`
      : "";

  return `
    <section class="location-check ${isWarning ? "mismatch" : "unverified"}">
      <h3>${isWarning ? "Check the address you entered" : "Address partly unverified"}</h3>
      <p>${
        isWarning
          ? "The city, state, and ZIP code do not describe the same place. The market and policy sections below may be for a different location."
          : "Some parts of this address could not be confirmed against the built-in location directory."
      }</p>
      <ul>${items}</ul>
      ${expected}
    </section>
  `;
}

function projectionTable(report) {
  const rows = [5, 10]
    .map((year) => {
      const projection = report.financials.projections[String(year)];
      return `
        <tr>
          <td>${projection.holding_period_years} years</td>
          <td>${formatCurrency(projection.final_year_noi)}</td>
          <td>${formatPercent(projection.exit_cap_rate)}</td>
          <td>${formatCurrency(projection.sale.loan_balance)}</td>
          <td>${formatCurrency(projection.sale.selling_costs)}</td>
          <td>${formatCurrency(projection.sale.net_sale_proceeds)}</td>
          <td>${formatCurrency(projection.total_distributions)}</td>
          <td>${formatMultiple(projection.equity_multiple)}</td>
          <td>${formatPercent(projection.irr)}</td>
        </tr>
      `;
    })
    .join("");

  return `
    <table>
      <thead>
        <tr>
          <th>Holding Period</th>
          <th>Final-Year NOI</th>
          <th>Exit Cap Rate</th>
          <th>Loan Balance</th>
          <th>Sales Costs</th>
          <th>Net Sale Proceeds</th>
          <th>Total Cash Returned</th>
          <th>Equity Multiple</th>
          <th>IRR</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderReport(report) {
  const f = report.financials;
  const recommendationClass = report.recommendation.status.toLowerCase().replaceAll(" ", "-");

  reportEl.innerHTML = `
    ${locationCheckPanel(report.location_check)}
    ${assumptionConflictsPanel(report.assumption_conflicts)}

    <div class="recommendation ${recommendationClass}">
      <div>
        <p class="eyebrow">Final recommendation</p>
        <h2>${report.recommendation.status}</h2>
        <p>${report.recommendation.reasons.join(" ")}</p>
      </div>
      ${badge(`Overall risk: ${report.overall_risk}`, report.overall_risk)}
    </div>

    <section class="report-section">
      <div class="section-title">
        <h3>${report.property.address}</h3>
        <p>${report.property.city}, ${report.property.state} ${report.property.zip_code}</p>
      </div>
      <div class="metric-grid">
        ${metricCard("Monthly Cash Flow", formatCurrency(f.monthly_cash_flow, true))}
        ${metricCard("Annual Cash Flow", formatCurrency(f.annual_cash_flow))}
        ${metricCard("Net Operating Income (NOI)", formatCurrency(f.noi))}
        ${metricCard("Going-In Cap Rate", formatPercent(f.cap_rate))}
        ${metricCard("Cash-on-Cash (CoC) Return", formatPercent(f.cash_on_cash_return))}
        ${metricCard("DSCR", formatNumber(f.dscr))}
        ${metricCard("Loan-to-Value (LTV)", formatPercent(f.ltv))}
        ${metricCard("Break-Even Rent", formatCurrency(f.break_even_monthly_rent))}
        ${metricCard("5-Year IRR", formatPercent(f.irr_5_year))}
        ${metricCard("10-Year IRR", formatPercent(f.irr_10_year))}
        ${metricCard("5-Year Equity Multiple", formatMultiple(f.equity_multiple_5_year))}
        ${metricCard("10-Year Equity Multiple", formatMultiple(f.equity_multiple_10_year))}
        ${metricCard("Exit Cap Rates", `${formatPercent(f.exit_cap_rate_5_year)} / ${formatPercent(f.exit_cap_rate_10_year)}`, "5-year / 10-year")}
      </div>
    </section>

    <section class="report-section two-column">
      <div>
        <div class="section-title">
          <h3>Market Snapshot</h3>
          <p>${report.market.market_name}</p>
        </div>
        <dl class="detail-list">
          <div><dt>Median rent estimate</dt><dd>${formatCurrency(report.market.median_rent_estimate)}</dd></div>
          <div><dt>Rent trend</dt><dd>${report.market.rent_trend}</dd></div>
          <div><dt>Value trend</dt><dd>${report.market.home_value_trend}</dd></div>
          <div><dt>Tax note</dt><dd>${report.market.property_tax_note}</dd></div>
          <div><dt>Source</dt><dd>${report.market.source_label} (${report.market.confidence} confidence)</dd></div>
        </dl>
      </div>
      <div>
        <div class="section-title">
          <h3>Policy Review</h3>
          <p>${report.policy.jurisdiction_name}</p>
        </div>
        <dl class="detail-list">
          <div><dt>Landlord-tenant</dt><dd>${report.policy.landlord_tenant_summary}</dd></div>
          <div><dt>Rent restrictions</dt><dd>${report.policy.rent_control_summary}</dd></div>
          <div><dt>Short-term rental</dt><dd>${report.policy.short_term_rental_summary}</dd></div>
          <div><dt>HOA/rental limits</dt><dd>${report.policy.rental_restriction_summary}</dd></div>
          <div><dt>Jurisdictions reviewed</dt><dd>${(report.policy.jurisdiction_levels || []).join("; ") || report.policy.jurisdiction_name}</dd></div>
          <div><dt>Source</dt><dd>${report.policy.source_label} (${report.policy.confidence} confidence)</dd></div>
        </dl>
      </div>
    </section>

    <section class="report-section">
      <div class="section-title">
        <div>
          <h3>Policy Restrictions and Sources</h3>
          <p>City/county, state, HOA/private, and other rules that could affect this investment. High-attention issues are flagged first. Use the links to verify the current rule before relying on the analysis.</p>
        </div>
      </div>
      ${policyFlags(report.policy.restriction_flags)}
      <h4 class="subsection-label">Read more online</h4>
      ${sourceLinks(report.policy.links)}
    </section>

    ${diligencePanel(report.diligence_items)}

    ${knowledgeBankPanel(report.knowledge_bank)}

    <section class="report-section">
      <div class="section-title">
        <div>
          <h3>Investor Assumptions</h3>
          <p>These editable rates drive the final financial analysis and should be stress-tested before purchase.</p>
        </div>
      </div>
      <div class="metric-grid compact">
        ${metricCard("Holding Periods", f.holding_periods.map((year) => `${year} years`).join(" / "))}
        ${metricCard("Appreciation Rate", formatPercent(f.growth_assumptions.annual_appreciation))}
        ${metricCard("Rent Growth Rate", formatPercent(f.growth_assumptions.annual_rent_growth))}
        ${metricCard("Expense Inflation Rate", formatPercent(f.growth_assumptions.annual_expense_inflation))}
        ${metricCard("Closing Costs", formatPercent(f.sale_assumptions.closing_cost_percent), formatCurrency(f.closing_costs))}
        ${metricCard("Sales Costs", formatPercent(f.sale_assumptions.selling_cost_percent), "Applied to projected sale value")}
      </div>
    </section>

    <section class="report-section">
      <div class="section-title">
        <div>
          <h3>Financial Detail</h3>
          <p>Deterministic model based on the assumptions entered.</p>
        </div>
      </div>
      <div class="metric-grid compact">
        ${metricCard("Purchase Price", formatCurrency(f.purchase_price))}
        ${metricCard("Down Payment", formatCurrency(f.down_payment))}
        ${metricCard("Loan Amount", formatCurrency(f.loan_amount))}
        ${metricCard("Loan-to-Value", formatPercent(f.ltv))}
        ${metricCard("Monthly Mortgage", formatCurrency(f.monthly_mortgage_payment, true))}
        ${metricCard("NOI", formatCurrency(f.noi))}
        ${metricCard("Operating Expenses", formatCurrency(f.operating_expenses.total))}
      </div>
      ${projectionTable(report)}
    </section>

    <section class="report-section two-column">
      <div>
        <div class="section-title">
          <h3>Risks</h3>
          <p>Items to verify before making a real purchase.</p>
        </div>
        ${listItems(report.risks, "No major risks triggered by the current analysis rules.")}
      </div>
      <div>
        <div class="section-title">
          <h3>Opportunities</h3>
          <p>Positive signals from the model and sample market context.</p>
        </div>
        ${listItems(report.opportunities, "No clear opportunities triggered by the current analysis rules.")}
      </div>
    </section>

    ${
      report.missing_data_flags.length
        ? `<section class="report-section warning-block">
            <h3>Missing Data Flags</h3>
            <ul>${report.missing_data_flags.map((flag) => `<li>${flag}</li>`).join("")}</ul>
          </section>`
        : ""
    }

    <p class="disclaimer">${report.disclaimer}</p>
  `;

  reportEl.classList.remove("hidden");
}

async function loadSamples() {
  const response = await fetch("/api/sample-properties");
  const data = await response.json();
  data.properties.forEach((property, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = property.label;
    sampleSelect.appendChild(option);
  });

  sampleSelect.addEventListener("change", () => {
    const selected = data.properties[Number(sampleSelect.value)];
    if (!selected) return;
    Object.entries(selected).forEach(([key, value]) => {
      const input = form.elements.namedItem(key);
      if (input) input.value = value;
    });
    checkLocationFields();
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(true);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectPayload()),
    });

    if (!response.ok) {
      const details = await response.text();
      throw new Error(details);
    }

    const report = await response.json();
    renderReport(report);
  } catch (error) {
    reportEl.innerHTML = `
      <section class="report-section error-block">
        <h2>Analysis failed</h2>
        <p>${error.message}</p>
      </section>
    `;
    reportEl.classList.remove("hidden");
  } finally {
    setLoading(false);
  }
});

loadSamples();
checkLocationFields();
