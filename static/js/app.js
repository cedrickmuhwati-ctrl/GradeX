/* GradeX front-end: programme switching, count-up numbers, simple charts, predictor, data table, forms */
(function () {
  "use strict";
  const BOOT = window.GRADEX;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const state = { slug: null, summary: null, page: 0, query: "", charts: {}, scatterKey: "attendance" };
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const INDIGO = "#6366f1", CYAN = "#22d3ee", GREY = "#94a3b8";

  function toast(msg) {
    const t = $("#toast"); t.textContent = msg; t.classList.add("show");
    clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove("show"), 3200);
  }
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* ---------------- navbar ---------------- */
  const burger = $("#burger"), links = $("#links");
  burger.addEventListener("click", () => {
    const open = links.classList.toggle("open");
    burger.setAttribute("aria-expanded", open);
  });
  $$("[data-link]").forEach(a => a.addEventListener("click", () => links.classList.remove("open")));
  const sections = $$("[data-link]").map(a => ({ a, el: document.querySelector(a.getAttribute("href")) })).filter(x => x.el);
  const toTop = $("#toTop");
  toTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  function onScroll() {
    toTop.classList.toggle("show", window.scrollY > 600);
    const y = window.scrollY + 140;
    let cur = null;
    sections.forEach(s => { if (s.el.offsetTop <= y) cur = s; });
    sections.forEach(s => s.a.classList.toggle("active", s === cur));
  }
  window.addEventListener("scroll", onScroll, { passive: true }); onScroll();

  /* ---------------- reveal + count-up ---------------- */
  const io = "IntersectionObserver" in window ? new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      e.target.classList.add("in");
      if (e.target.classList.contains("stat")) { const c = $(".counter", e.target); if (c) countUp(c); }
      if (e.target.dataset.meters) animateMeters();
      io.unobserve(e.target);
    });
  }, { threshold: 0.25 }) : null;
  function observeReveals() {
    $$(".reveal").forEach(el => { if (io) io.observe(el); else el.classList.add("in"); });
  }

  function fmt(v, dec) { return dec ? v.toFixed(dec) : String(Math.round(v)); }
  function countUp(el) {
    const target = parseFloat(el.dataset.target || "0");
    const dec = (el.dataset.target || "").includes(".") ? 1 : 0;
    const suffix = el.dataset.suffix || "";
    el.innerHTML = "";
    const num = document.createElement("span"); el.appendChild(num);
    if (suffix) { const s = document.createElement("span"); s.className = "suffix"; s.textContent = suffix; el.appendChild(s); }
    if (reduceMotion) { num.textContent = fmt(target, dec); return; }
    const dur = 1700, t0 = performance.now(), my = (el._run = (el._run || 0) + 1);
    (function tick(now) {
      if (el._run !== my) return;
      const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      num.textContent = fmt(target * e, dec);
      if (p < 1) requestAnimationFrame(tick); else num.textContent = fmt(target, dec);
    })(t0);
  }
  function setCounters(c) {
    const map = { students: "", avg: "", min: "", pass: "%", attendance: "%", accuracy: "%" };
    $$(".counter").forEach(el => {
      const k = el.dataset.key;
      el.dataset.target = c[k]; el.dataset.suffix = map[k] || "";
      const stat = el.closest(".stat");
      if (stat && stat.classList.contains("in")) countUp(el);   // already visible: replay for new programme
      else { el.innerHTML = "<span>0</span>" + (map[k] ? `<span class="suffix">${map[k]}</span>` : ""); }
    });
  }

  /* ---------------- programmes ---------------- */
  function renderProgrammes(list, selected) {
    $$("[data-prog-select]").forEach(box => {
      box.innerHTML = "";
      list.forEach(p => {
        const b = document.createElement("button");
        b.className = "pill" + (p.slug === selected ? " on" : ""); b.type = "button";
        b.textContent = p.title; b.dataset.slug = p.slug;
        b.addEventListener("click", () => loadProgramme(p.slug));
        box.appendChild(b);
      });
    });
  }
  async function loadProgramme(slug) {
    document.body.classList.add("loading");
    try {
      const r = await fetch("/api/summary/" + slug);
      if (!r.ok) throw new Error("Could not load " + slug);
      const s = await r.json();
      state.slug = slug; state.summary = s; state.page = 0; state.query = ""; $("#q").value = "";
      $$("[data-prog-title]").forEach(el => el.textContent = s.title);
      $$(".pill").forEach(p => p.classList.toggle("on", p.dataset.slug === slug));
      setCounters(s.counters); renderBasics(s); renderCharts(s); renderScorecard(s); renderTable();
      $("#dl").href = "/api/download/" + slug + ".csv";
      predict();
    } catch (e) { toast(e.message); }
    document.body.classList.remove("loading");
  }

  function renderBasics(s) {
    const box = $("#heroBasics");
    box.innerHTML = s.basics.map(b => {
      const pct = Math.round(Math.abs(b.r) * 100);
      return `<div class="basic"><div class="row"><span><i class="bi ${b.icon}"></i>${esc(b.name)}</span><span class="val">${pct}% link</span></div>
        <div class="meter"><span data-w="${pct}"></span></div>
        <small>Passing students average ${b.pass_mean}${esc(b.unit)}; failing students ${b.fail_mean}${esc(b.unit)}</small></div>`;
    }).join("");
    setTimeout(() => $$(".meter span", box).forEach(m => m.style.width = m.dataset.w + "%"), 120);
  }
  function animateMeters() {}

  /* ---------------- charts (simple and readable) ---------------- */
  Chart.defaults.font.family = "Poppins, sans-serif";
  const root = document.documentElement;
  const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
  let GRID = "#eef0f4";
  function applyChartTheme() {            // chart text and grid colours follow the chosen theme
    const dark = root.dataset.theme === "dark";
    Chart.defaults.color = dark ? "#cbd5e1" : "#4b5563";
    GRID = dark ? "#243049" : "#eef0f4";
  }
  applyChartTheme();
  function setTheme(t, save) {
    root.setAttribute("data-theme", t);
    if (save) { try { localStorage.setItem("gradex-theme", t); } catch (e) {} }
    applyChartTheme(); if (state.summary) renderCharts(state.summary);
  }
  $("#themeBtn").addEventListener("click", () => setTheme(root.dataset.theme === "dark" ? "light" : "dark", true));
  darkQuery.addEventListener("change", e => {   // follow the system only if no manual choice was saved
    let saved = null; try { saved = localStorage.getItem("gradex-theme"); } catch (err) {}
    if (!saved) setTheme(e.matches ? "dark" : "light", false);
  });
  function mk(id, cfg) {
    if (state.charts[id]) state.charts[id].destroy();
    state.charts[id] = new Chart($("#" + id), cfg);
  }
  const base = { responsive: true, maintainAspectRatio: false, animation: { duration: reduceMotion ? 0 : 900 } };

  function renderCharts(s) {
    // 1. Students in each class
    mk("chDist", {
      type: "bar",
      data: { labels: s.distribution.map(d => d.short === "Fail" ? "Fail" : "Class " + d.short + "\n" + d.range),
              datasets: [{ data: s.distribution.map(d => d.count), backgroundColor: s.distribution.map(d => d.colour), borderRadius: 8 }] },
      options: { ...base, plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => c.parsed.y + " students" } } },
                 scales: { y: { beginAtZero: true, title: { display: true, text: "Number of students" }, grid: { color: GRID } }, x: { grid: { display: false } } } }
    });
    // 2. Models: average error (lower is better)
    const real = s.models;
    mk("chModels", {
      type: "bar",
      data: { labels: real.map(m => m.model), datasets: [{ data: real.map(m => m.mae),
              backgroundColor: real.map(m => m.model === s.best ? INDIGO : m.model === "Mean baseline" ? "#cbd5e1" : "#a5b4fc"), borderRadius: 8 }] },
      options: { ...base, indexAxis: "y", plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => c.parsed.x + " marks off on average" } } },
                 scales: { x: { beginAtZero: true, title: { display: true, text: "Average error in marks (shorter bar = better)" }, grid: { color: GRID } }, y: { grid: { display: false } } } }
    });
    // 3. Feature importance
    mk("chImp", {
      type: "bar",
      data: { labels: s.importance.map(i => i.label), datasets: [{ data: s.importance.map(i => i.share), backgroundColor: CYAN, borderRadius: 8 }] },
      options: { ...base, indexAxis: "y", plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => c.parsed.x + "% of the influence" } } },
                 scales: { x: { beginAtZero: true, title: { display: true, text: "Share of influence on the final mark (%)" }, grid: { color: GRID } }, y: { grid: { display: false } } } }
    });
    $("#insDist").textContent = s.insights.dist;
    $("#insModels").textContent = s.insights.models;
    $("#insImp").textContent = s.insights.importance;
    renderScatter();
  }
  function renderScatter() {
    const s = state.summary; if (!s) return;
    const rel = s.relations[state.scatterKey];
    const unit = state.scatterKey === "study_hours" ? "Study hours per week" : rel.label + " (%)";
    mk("chScatter", {
      type: "scatter",
      data: { datasets: [
        { label: "Students", data: rel.points, backgroundColor: "rgba(99,102,241,.5)", pointRadius: 4 },
        { label: "Trend", type: "line", data: rel.line, borderColor: "#ef4444", borderWidth: 3, pointRadius: 0 }] },
      options: { ...base, plugins: { legend: { display: false } },
                 scales: { x: { title: { display: true, text: unit }, grid: { color: GRID } }, y: { min: 0, max: 100, title: { display: true, text: "Final mark (%)" }, grid: { color: GRID } } } }
    });
    const b = s.basics.find(x => x.key === state.scatterKey);
    $("#insScatter").textContent = b && b.fail_mean != null
      ? `Students who passed averaged ${b.pass_mean}${b.unit} here; those who failed averaged ${b.fail_mean}${b.unit}.`
      : "Each dot is one student; the red line shows the overall trend.";
  }
  $$("#seg button").forEach(b => b.addEventListener("click", () => {
    $$("#seg button").forEach(x => x.classList.toggle("on", x === b));
    state.scatterKey = b.dataset.key; renderScatter();
  }));

  function renderScorecard(s) {
    $("#modelTable tbody").innerHTML = s.models.map(m =>
      `<tr class="${m.model === s.best ? "best" : ""}"><td>${esc(m.model)}${m.model === s.best ? '<span class="best-tag">BEST</span>' : ""}</td>
       <td>${m.mae.toFixed(2)} marks</td><td>${(m.r2 * 100).toFixed(1)}%</td><td>${m.pass_acc.toFixed(1)}%</td></tr>`).join("");
  }

  /* ---------------- raw data table ---------------- */
  const PAGE = 15;
  const COLS = [["attendance", "Attendance %"], ["coursework", "Coursework %"], ["prev_avg", "Prev. average %"], ["study_hours", "Study h/wk"],
    ["part_time_hours", "Part-time h/wk"], ["a_level_points", "A-Level pts"], ["level", "Level"], ["housing", "Housing"],
    ["funding", "Funding"], ["internet", "Internet"], ["final_mark", "Final mark %"]];
  function renderTable() {
    const s = state.summary; if (!s) return;
    const q = state.query.toLowerCase();
    const rows = q ? s.rows.filter(r => Object.values(r).some(v => String(v).toLowerCase().includes(q))) : s.rows;
    const pages = Math.max(1, Math.ceil(rows.length / PAGE));
    state.page = Math.min(state.page, pages - 1);
    const slice = rows.slice(state.page * PAGE, state.page * PAGE + PAGE);
    $("#rawTable thead").innerHTML = "<tr><th>#</th>" + COLS.map(c => `<th>${c[1]}</th>`).join("") + "</tr>";
    $("#rawTable tbody").innerHTML = slice.map((r, i) =>
      `<tr><td>${state.page * PAGE + i + 1}</td>` + COLS.map(c => `<td>${esc(r[c[0]] ?? "")}</td>`).join("") + "</tr>").join("")
      || `<tr><td colspan="${COLS.length + 1}">No matching students.</td></tr>`;
    $("#pageInfo").textContent = `Showing ${rows.length ? state.page * PAGE + 1 : 0}-${Math.min(rows.length, (state.page + 1) * PAGE)} of ${rows.length} students`;
    $("#prev").disabled = state.page === 0; $("#next").disabled = state.page >= pages - 1;
  }
  $("#prev").addEventListener("click", () => { state.page--; renderTable(); });
  $("#next").addEventListener("click", () => { state.page++; renderTable(); });
  $("#q").addEventListener("input", e => { state.query = e.target.value; state.page = 0; renderTable(); });

  /* ---------------- predictor ---------------- */
  let pending = null;
  function formValues() {
    const v = {};
    $$("#predictForm input[type=range]").forEach(i => v[i.name] = parseFloat(i.value));
    $$("#predictForm select").forEach(s => v[s.name] = s.value);
    return v;
  }
  async function predict() {
    if (!state.slug) return;
    const my = (pending = Symbol());
    try {
      const r = await fetch("/api/predict/" + state.slug, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(formValues()) });
      const d = await r.json();
      if (my !== pending) return;
      $("#predNum").textContent = d.mark.toFixed(0);
      const badge = $("#predClass"); badge.textContent = d.class.label; badge.style.background = d.class.colour;
      badge.style.color = ["#22d3ee", "#84cc16", "#f59e0b"].includes(d.class.colour) ? "#111" : "#fff";
      $("#marker").style.left = Math.min(100, Math.max(0, d.mark)) + "%";
      $("#predMsg").textContent = d.passed
        ? `Likely to pass (pass mark ${BOOT.pass}%). Best model: ${d.best}.`
        : `At risk of failing (pass mark ${BOOT.pass}%). Best model: ${d.best}.`;
      $("#predModels").innerHTML = Object.entries(d.models).map(([n, v]) =>
        `<div class="chip ${n === d.best ? "best" : ""}">${esc(n)}<b>${v.toFixed(0)}%</b></div>`).join("");
      $("#predTips").innerHTML = d.tips.length
        ? d.tips.map(t => `<li>${esc(t.text)}: about <b>+${t.gain.toFixed(1)} marks</b></li>`).join("")
        : "<li class='muted'>This profile is already strong on the factors we can change.</li>";
    } catch (e) { /* ignore transient errors while sliding */ }
  }
  let debounce;
  $$("#predictForm input[type=range]").forEach(i => i.addEventListener("input", () => {
    $("#o-" + i.name).textContent = i.value; clearTimeout(debounce); debounce = setTimeout(predict, 120);
  }));
  $$("#predictForm select").forEach(s => s.addEventListener("change", predict));

  /* ---------------- upload + contact ---------------- */
  $("#uploadForm").addEventListener("submit", async e => {
    e.preventDefault();
    const msg = $("#upMsg"); msg.className = "small"; msg.textContent = "Uploading and analysing…";
    const fd = new FormData(); fd.append("name", $("#upName").value); fd.append("file", $("#upFile").files[0]);
    try {
      const r = await fetch("/api/upload", { method: "POST", body: fd }); const d = await r.json();
      if (!r.ok) { msg.className = "small err"; msg.textContent = d.error || "Upload failed."; return; }
      msg.className = "small ok"; msg.textContent = "Added! Switching to your new programme.";
      renderProgrammes(d.programmes, d.slug); await loadProgramme(d.slug);
      document.getElementById("services").scrollIntoView({ behavior: "smooth" });
    } catch (err) { msg.className = "small err"; msg.textContent = "Could not reach the server."; }
  });
  $("#contactForm").addEventListener("submit", async e => {
    e.preventDefault();
    try {
      const r = await fetch("/api/contact", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: $("#cName").value, email: $("#cEmail").value, subject: $("#cSubject").value, message: $("#cMsg").value }) });
      const d = await r.json();
      if (!r.ok) return toast(d.error || "Could not send.");
      e.target.reset(); toast("Thank you! Your message was saved.");
    } catch (err) { toast("Could not reach the server."); }
  });

  /* ---------------- start ---------------- */
  observeReveals();
  const first = BOOT.programmes[0];
  renderProgrammes(BOOT.programmes, first && first.slug);
  if (first) loadProgramme(first.slug);
})();
