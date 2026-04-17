/* Apollo Outreach Analytics — Dashboard App */

(function () {
  "use strict";

  const DATA_URL = "data/apollo_dashboard.json";

  // DOM refs
  const elGenerated = document.getElementById("generated-at");
  const elKpi = document.getElementById("kpi-grid");
  const elError = document.getElementById("error-banner");
  const elSearch = document.getElementById("filter-search");
  const elStatus = document.getElementById("filter-status");
  const elCampaignTypeWrap = document.getElementById("filter-campaign-type-wrap");
  const elCampaignType = document.getElementById("filter-campaign-type");
  const elPersonaWrap = document.getElementById("filter-persona-wrap");
  const elPersona = document.getElementById("filter-persona");
  const elIndustryWrap = document.getElementById("filter-industry-wrap");
  const elIndustry = document.getElementById("filter-industry");

  let DATA = null;

  // ── Fetch data ─────────────────────────────────────────────
  fetch(DATA_URL)
    .then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    })
    .then(function (json) {
      if (!json || !json.sequence_performance) throw new Error("empty");
      DATA = json;
      init();
    })
    .catch(function () {
      showError("No dashboard data found. Run export_dashboard_data.py first.");
    });

  function showError(msg) {
    elError.textContent = msg;
    elError.classList.remove("hidden");
  }

  // ── Init ───────────────────────────────────────────────────
  function init() {
    // Generated timestamp
    if (DATA.generated_at) {
      var d = new Date(DATA.generated_at);
      elGenerated.textContent = "Data generated: " + d.toLocaleString();
    }

    // Populate dynamic filters
    populateFilter(elCampaignType, elCampaignTypeWrap, "campaign_type");
    populateFilter(elPersona, elPersonaWrap, "persona");
    populateFilter(elIndustry, elIndustryWrap, "industry");

    // Wire up filter events
    [elSearch, elStatus, elCampaignType, elPersona, elIndustry].forEach(function (el) {
      el.addEventListener("input", render);
      el.addEventListener("change", render);
    });

    render();
  }

  function populateFilter(selectEl, wrapEl, field) {
    var vals = [];
    DATA.sequence_performance.forEach(function (r) {
      var v = r[field];
      if (v && vals.indexOf(v) === -1) vals.push(v);
    });
    vals.sort();
    if (vals.length === 0) return;
    wrapEl.classList.remove("hidden");
    vals.forEach(function (v) {
      var opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      selectEl.appendChild(opt);
    });
  }

  // ── Filtering ──────────────────────────────────────────────
  function getFilteredPerformance() {
    var search = elSearch.value.toLowerCase().trim();
    var status = elStatus.value;
    var cType = elCampaignType.value;
    var persona = elPersona.value;
    var industry = elIndustry.value;

    return DATA.sequence_performance.filter(function (r) {
      // Status filter
      if (status === "active_inactive") {
        if (r.sequence_status !== "active" && r.sequence_status !== "inactive") return false;
      } else if (status !== "all") {
        if (r.sequence_status !== status) return false;
      }
      // Campaign type
      if (cType && r.campaign_type !== cType) return false;
      // Persona
      if (persona && r.persona !== persona) return false;
      // Industry
      if (industry && r.industry !== industry) return false;
      // Search
      if (search && (r.sequence_name || "").toLowerCase().indexOf(search) === -1) return false;
      return true;
    });
  }

  // ── Render ─────────────────────────────────────────────────
  function render() {
    var filtered = getFilteredPerformance();

    // Sort by messages_count desc
    filtered.sort(function (a, b) { return (b.messages_count || 0) - (a.messages_count || 0); });

    renderKPI(filtered);
    renderSequenceTable(filtered);
    renderSimpleTable("table-message-status", DATA.message_status_summary, ["status", "messages_count", "pct"]);
    renderSimpleTable("table-reply-type", DATA.reply_type_summary, ["reply_type", "messages_count", "pct"]);
    renderSimpleTable("table-sequence-status", DATA.sequence_status_summary, ["sequence_status", "messages_count", "pct"]);
  }

  // ── KPI ────────────────────────────────────────────────────
  function renderKPI(rows) {
    var totalSeq = rows.length;
    var sum = { messages: 0, completed: 0, failed: 0, opened: 0, clicked: 0, replied: 0, positive: 0, bounced: 0, unsub: 0 };

    rows.forEach(function (r) {
      sum.messages += r.messages_count || 0;
      sum.completed += r.completed_count || 0;
      sum.failed += r.failed_count || 0;
      sum.opened += r.opened_count || 0;
      sum.clicked += r.clicked_count || 0;
      sum.replied += r.replied_count || 0;
      sum.positive += r.positive_reply_count || 0;
      sum.bounced += r.bounced_count || 0;
      sum.unsub += r.unsubscribed_count || 0;
    });

    function rate(num) {
      if (!sum.messages) return "0.0%";
      return (num / sum.messages * 100).toFixed(1) + "%";
    }

    var cards = [
      { label: "Total Sequences", value: totalSeq },
      { label: "Total Messages", value: sum.messages.toLocaleString() },
      { label: "Completed", value: sum.completed.toLocaleString() },
      { label: "Failed", value: sum.failed.toLocaleString() },
      { label: "Open Rate", value: rate(sum.opened) },
      { label: "Click Rate", value: rate(sum.clicked) },
      { label: "Reply Rate", value: rate(sum.replied) },
      { label: "Positive Reply Rate", value: rate(sum.positive) },
      { label: "Bounce Rate", value: rate(sum.bounced) },
      { label: "Unsubscribe Rate", value: rate(sum.unsub) },
    ];

    elKpi.innerHTML = cards.map(function (c) {
      return '<div class="kpi-card"><div class="kpi-label">' + esc(c.label) + '</div><div class="kpi-value">' + esc(String(c.value)) + '</div></div>';
    }).join("");
  }

  // ── Sequence performance table ─────────────────────────────
  var SEQ_COLS = [
    { key: "sequence_name", label: "Sequence", cls: "" },
    { key: "sequence_status", label: "Status", cls: "" },
    { key: "messages_count", label: "Messages", cls: "num" },
    { key: "completed_count", label: "Completed", cls: "num" },
    { key: "failed_count", label: "Failed", cls: "num" },
    { key: "opened_count", label: "Opened", cls: "num" },
    { key: "clicked_count", label: "Clicked", cls: "num" },
    { key: "replied_count", label: "Replied", cls: "num" },
    { key: "positive_reply_count", label: "Positive", cls: "num" },
    { key: "open_rate", label: "Open %", cls: "num" },
    { key: "click_rate", label: "Click %", cls: "num" },
    { key: "reply_rate", label: "Reply %", cls: "num" },
    { key: "positive_reply_rate", label: "Positive %", cls: "num" },
    { key: "bounce_rate", label: "Bounce %", cls: "num" },
    { key: "unsubscribe_rate", label: "Unsub %", cls: "num" },
  ];

  var seqSortCol = "messages_count";
  var seqSortAsc = false;

  function renderSequenceTable(rows) {
    rows.sort(function (a, b) {
      var va = a[seqSortCol], vb = b[seqSortCol];
      if (va == null) va = "";
      if (vb == null) vb = "";
      if (typeof va === "number" && typeof vb === "number") return seqSortAsc ? va - vb : vb - va;
      return seqSortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
    });

    var html = "<thead><tr>";
    SEQ_COLS.forEach(function (col) {
      var arrow = col.key === seqSortCol ? (seqSortAsc ? " ▲" : " ▼") : "";
      html += '<th class="' + col.cls + '" data-col="' + col.key + '">' + esc(col.label) + arrow + "</th>";
    });
    html += "</tr></thead><tbody>";

    rows.forEach(function (r) {
      html += "<tr>";
      SEQ_COLS.forEach(function (col) {
        var v = r[col.key];
        if (col.key === "sequence_status") {
          html += "<td>" + statusBadge(v) + "</td>";
        } else if (col.key.endsWith("_rate")) {
          html += '<td class="num">' + fmtRate(v) + "</td>";
        } else if (col.cls === "num") {
          html += '<td class="num">' + fmtNum(v) + "</td>";
        } else {
          html += "<td>" + esc(v == null ? "" : String(v)) + "</td>";
        }
      });
      html += "</tr>";
    });

    html += "</tbody>";
    var table = document.getElementById("table-sequence-performance");
    table.innerHTML = html;

    // Click-to-sort
    table.querySelectorAll("thead th").forEach(function (th) {
      th.addEventListener("click", function () {
        var col = th.getAttribute("data-col");
        if (seqSortCol === col) {
          seqSortAsc = !seqSortAsc;
        } else {
          seqSortCol = col;
          seqSortAsc = col === "sequence_name";
        }
        render();
      });
    });
  }

  // ── Simple table renderer ──────────────────────────────────
  function renderSimpleTable(tableId, rows, cols) {
    if (!rows || !rows.length) {
      document.getElementById(tableId).innerHTML = "<tbody><tr><td>No data</td></tr></tbody>";
      return;
    }
    var html = "<thead><tr>";
    cols.forEach(function (c) {
      var isNum = c !== cols[0];
      html += '<th class="' + (isNum ? "num" : "") + '">' + esc(colLabel(c)) + "</th>";
    });
    html += "</tr></thead><tbody>";
    rows.forEach(function (r) {
      html += "<tr>";
      cols.forEach(function (c, i) {
        var v = r[c];
        if (c === "pct") {
          html += '<td class="num">' + fmtRate(v) + "</td>";
        } else if (i > 0) {
          html += '<td class="num">' + fmtNum(v) + "</td>";
        } else {
          html += "<td>" + esc(v == null ? "(null)" : String(v)) + "</td>";
        }
      });
      html += "</tr>";
    });
    html += "</tbody>";
    document.getElementById(tableId).innerHTML = html;
  }

  // ── Helpers ────────────────────────────────────────────────
  function esc(s) {
    var d = document.createElement("div");
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
  }

  function fmtNum(v) {
    if (v == null) return "0";
    return Number(v).toLocaleString();
  }

  function fmtRate(v) {
    if (v == null || v === "") return "-";
    return (Number(v) * 100).toFixed(1) + "%";
  }

  function statusBadge(s) {
    var cls = "badge badge-" + (s || "unknown");
    return '<span class="' + cls + '">' + esc(s || "unknown") + "</span>";
  }

  function colLabel(key) {
    return key.replace(/_/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }
})();
