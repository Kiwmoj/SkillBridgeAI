"use strict";

const API = "/api/v1";
const TOKEN_KEY = "skillbridge_token";
let token = localStorage.getItem(TOKEN_KEY) || null;
let me = null;

// ---------- API helper ----------
async function api(path, { method = "GET", body = null, auth = true, form = null } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (auth && token) headers["Authorization"] = `Bearer ${token}`;
  let res;
  try {
    res = await fetch(API + path, { method, headers, body: form || (body ? JSON.stringify(body) : null) });
  } catch {
    throw new Error("Cannot reach the backend. Check your connection.");
  }
  if (res.status === 401 && auth) { signOut(); throw new Error("Your session expired. Please sign in again."); }
  let data = null;
  try { data = await res.json(); } catch { data = null; }
  if (!res.ok) {
    const detail = data && data.detail;
    if (typeof detail === "string") throw new Error(detail);
    if (Array.isArray(detail)) throw new Error(detail.map((e) => e.msg).join("\n"));
    throw new Error(`Request failed (HTTP ${res.status}).`);
  }
  return data;
}

// ---------- utilities ----------
const $ = (sel) => document.querySelector(sel);
const el = (tag, props = {}, ...children) => {
  const node = Object.assign(document.createElement(tag), props);
  for (const c of children) node.append(c?.nodeType ? c : document.createTextNode(c ?? ""));
  if (props["aria-label"]) node.setAttribute("aria-label", props["aria-label"]);
  return node;
};
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), 3000);
}
function esc(s) { return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
const skeleton = (n = 3) => Array.from({ length: n }, () => '<div class="skeleton"></div>').join("");
const empty = (title, text) => `<div class="empty"><b>${esc(title)}</b>${esc(text)}</div>`;
const errorBox = (msg) => `<div class="notice err">${esc(msg)}</div>`;
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "");
function setBusy(btn, busy, label) {
  btn.disabled = busy;
  if (label) btn.textContent = busy ? label : btn.dataset.label;
}
function labeled(btn) { btn.dataset.label = btn.textContent; return btn; }

// ---------- auth screen ----------
let authMode = "login";
function initAuth() {
  document.querySelectorAll(".tab").forEach((tab) =>
    tab.addEventListener("click", () => {
      authMode = tab.dataset.tab;
      document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
      $("#name-field").classList.toggle("hidden", authMode !== "register");
      $("#auth-submit").textContent = authMode === "login" ? "Sign in" : "Create account";
      $("#auth-error").textContent = "";
    })
  );
  $("#auth-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("#auth-error").textContent = "";
    const email = $("#f-email").value.trim();
    const password = $("#f-password").value;
    const name = $("#f-name").value.trim();
    const btn = $("#auth-submit");
    const label = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Please wait…";
    try {
      const payload = authMode === "login" ? { email, password } : { name, email, password };
      const res = await api(`/auth/${authMode === "login" ? "login" : "register"}`, { method: "POST", body: payload, auth: false });
      token = res.access_token;
      localStorage.setItem(TOKEN_KEY, token);
      await enterApp();
    } catch (err) {
      $("#auth-error").textContent = err.message;
    } finally {
      btn.disabled = false;
      btn.textContent = label;
    }
  });
  refreshStatus();
}

async function refreshStatus() {
  const dot = $("#api-dot");
  try {
    const h = await api("/health", { auth: false });
    $("#api-status").textContent = `Backend ${h.status}` + (h.onet_version ? ` · O*NET ${h.onet_version}` : "");
    dot.className = "dot " + (h.status === "healthy" ? "ok" : "");
  } catch {
    $("#api-status").textContent = "Backend unreachable";
    dot.className = "dot bad";
  }
}

function signOut() {
  token = null; me = null;
  localStorage.removeItem(TOKEN_KEY);
  $("#app").classList.add("hidden");
  $("#auth").classList.remove("hidden");
  refreshStatus();
}

async function enterApp() {
  try { me = await api("/auth/me"); } catch { signOut(); return; }
  try { levelInfo = await api("/profile/level"); } catch { levelInfo = null; }
  $("#auth").classList.add("hidden");
  $("#app").classList.remove("hidden");
  $("#who").textContent = me.name;
  $("#who-role").textContent = me.role;
  $("#avatar").textContent = (me.name || "?").trim().charAt(0).toUpperCase();
  buildNav();
  updateLevelChip();
  go("Dashboard");
  if (levelInfo && !levelInfo.skill_level) showLevelModal(true);
}

// ---------- skill level ----------
let levelInfo = null;
const levelName = () => {
  const id = levelInfo?.effective_level || "beginner";
  return levelInfo?.levels?.find((l) => l.id === id)?.label || "Beginner";
};
function updateLevelChip() {
  const chip = $("#level-chip");
  chip.textContent = levelInfo?.skill_level ? `Level: ${levelName()} · change` : "Choose your level";
  chip.onclick = () => showLevelModal(false);
}
function showLevelModal(first) {
  const modal = $("#level-modal");
  modal.innerHTML = "";
  const card = el("div", { className: "modal-card" });
  card.append(
    el("h1", { id: "level-title" }, first ? "Where are you starting from?" : "Change your skill level"),
    el("p", { className: "muted" }, "There is no wrong answer. Everything in SkillBridge adapts to this: your roadmaps, projects, skill analysis and AI explanations. You can change it any time."),
  );
  const grid = el("div", { className: "level-grid" });
  (levelInfo?.levels || []).forEach((l) => {
    const b = el("button", { type: "button", className: "level-card" + (levelInfo.skill_level === l.id ? " selected" : "") },
      el("b", {}, l.label), el("span", {}, l.summary));
    b.addEventListener("click", async () => {
      try {
        levelInfo = await api("/profile/level", { method: "PUT", body: { skill_level: l.id } });
        modal.classList.add("hidden");
        updateLevelChip();
        toast(`Level set to ${l.label}. New roadmaps and projects will match it.`);
        go(currentPage);
      } catch (e) { toast(e.message); }
    });
    grid.append(b);
  });
  card.append(grid);
  const close = el("button", { className: "ghost small", type: "button" }, first ? "Not sure yet? Skip for now (we'll keep things beginner-friendly)" : "Close");
  close.addEventListener("click", () => modal.classList.add("hidden"));
  card.append(close);
  modal.append(card);
  modal.classList.remove("hidden");
}
const levelNote = () => el("div", { className: "notice", style: "background:rgba(139,92,246,.1);border-color:rgba(139,92,246,.35);color:#d8ccff" },
  `Adapted for your level: ${levelName()}. `, el("a", { href: "#", onclick: (e) => { e.preventDefault(); showLevelModal(false); } }, "Change level"));

// ---------- navigation ----------
const NAV = [
  ["Dashboard", "▦", "Home"],
  ["Career Explorer", "⌕", "Careers"],
  ["Skill Gap", "↗", "Skills"],
  ["Roadmaps", "☰", "Plans"],
  ["Project Studio", "✎", "Projects"],
  ["Portfolio", "▣", "Work"],
  ["Opportunities", "◎", "Options"],
  ["Settings", "⚙", "Settings"],
];
const VIEWS = () => ({
  "Dashboard": viewDashboard,
  "Career Explorer": viewCareers,
  "Skill Gap": viewSkillGap,
  "Roadmaps": viewRoadmaps,
  "Project Studio": viewProjects,
  "Portfolio": viewPortfolio,
  "Opportunities": viewOpportunities,
  "Settings": viewSettings,
});
function buildNav() {
  const nav = $("#nav");
  nav.innerHTML = "";
  NAV.forEach(([p, icon, short]) => {
    const b = el("button", { className: "nav-item", title: p, type: "button" },
      el("span", { className: "nav-icon", textContent: icon }),
      el("span", { className: "nav-label", textContent: p }),
      el("span", { className: "nav-short", textContent: short }));
    b.setAttribute("aria-label", p);
    b.addEventListener("click", () => go(p));
    nav.append(b);
  });
}
let currentPage = "Dashboard";
function go(page) {
  currentPage = page;
  document.querySelectorAll(".nav-item").forEach((n) => n.classList.toggle("active", n.getAttribute("aria-label") === page));
  const view = $("#view");
  view.innerHTML = "";
  view.style.animation = "none"; void view.offsetWidth; view.style.animation = "";
  window.scrollTo(0, 0);
  VIEWS()[page](view);
}
function head(title, subtitle) {
  return el("div", { className: "page-head", innerHTML: `<h1>${esc(title)}</h1><p class="muted">${esc(subtitle)}</p>` });
}
function bars(rows) {
  return rows.map(([label, value, max]) => {
    const pct = max ? Math.round((100 * value) / max) : 0;
    return `<div class="bar-row"><span>${esc(label)}</span><div class="bar"><i style="width:${pct}%"></i></div><span>${value}</span></div>`;
  }).join("");
}
function donut(parts) {
  const total = parts.reduce((s, p) => s + p.value, 0);
  if (!total) return empty("No projects yet", "Create one in Project Studio to see your status breakdown.");
  const r = 54, c = 2 * Math.PI * r;
  let offset = 0;
  const arcs = parts.filter((p) => p.value).map((p) => {
    const len = (p.value / total) * c;
    const svg = `<circle r="${r}" cx="75" cy="75" fill="none" stroke="${p.color}" stroke-width="16" stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-offset}" transform="rotate(-90 75 75)"></circle>`;
    offset += len;
    return svg;
  }).join("");
  const legend = parts.map((p) => `<div><i style="background:${p.color}"></i>${esc(p.label)} · <b>${p.value}</b></div>`).join("");
  return `<div class="donut-wrap"><svg class="donut" viewBox="0 0 150 150" role="img" aria-label="Project status breakdown">
    <circle r="${r}" cx="75" cy="75" fill="none" stroke="rgba(120,140,220,.12)" stroke-width="16"></circle>${arcs}
    <text x="75" y="72" text-anchor="middle" fill="#e8ecff" font-size="26" font-weight="800">${total}</text>
    <text x="75" y="92" text-anchor="middle" fill="#98a2c8" font-size="11">projects</text></svg>
    <div class="legend">${legend}</div></div>`;
}

// ---------- Dashboard ----------
async function viewDashboard(view) {
  view.append(head(`Welcome back, ${(me.name || "").split(" ")[0] || "there"}`, "Your career development workspace"));
  const cards = el("div", { className: "cards" });
  view.append(cards);
  const defs = [
    ["Saved roadmaps", "saved_roadmaps"],
    ["Projects", "project_total"],
    ["Activities done", "learning_activities_completed"],
    ["Saved opportunities", "saved_opportunities"],
  ];
  defs.forEach(([k]) => cards.append(el("div", { className: "card", innerHTML: `<div class="k">${k}</div><div class="v">—</div>` })));
  const charts = el("div", { className: "grid-2" });
  const statusPanel = el("section", { className: "panel", innerHTML: `<h2>Project status</h2>${skeleton(1)}` });
  const learnPanel = el("section", { className: "panel", innerHTML: `<h2>Learning progress</h2>${skeleton(1)}` });
  charts.append(statusPanel, learnPanel);
  view.append(charts);

  const levelTips = {
    beginner: "You are starting from zero, and that is fine. Pick a career below, open it, and follow the beginner steps.",
    intermediate: "You have the basics. Use the Skill Gap Analyzer to find what to learn next, then build a project.",
    advanced: "Go deep: pick a specialization, take on a capstone project and aim for senior-level credentials.",
  };
  view.append(el("div", { className: "level-banner" },
    el("b", {}, `Your level: ${levelName()}${levelInfo?.skill_level ? "" : " (default until you choose)"}`),
    el("div", { className: "muted" }, levelTips[levelInfo?.effective_level || "beginner"])));
  const recPanel = el("section", { className: "panel", innerHTML: `<h2>Careers to explore at your level</h2>${skeleton(1)}` });
  view.append(recPanel);
  api("/occupations/recommended").then((r) => {
    recPanel.innerHTML = "<h2>Careers to explore at your level</h2><p class=\"muted tiny\">Chosen by how much preparation O*NET says each career needs (Job Zone). Every career is open to anyone.</p>";
    if (!r.careers.length) { recPanel.insertAdjacentHTML("beforeend", empty("No careers loaded", "Career data has not been imported yet.")); return; }
    const chips = el("div", { className: "chips" });
    r.careers.forEach((c) => {
      const b = el("button", { className: "ghost small", type: "button" }, c.title);
      b.addEventListener("click", () => { go("Career Explorer"); setTimeout(() => window.openCareer && window.openCareer(c.id), 50); });
      chips.append(b);
    });
    recPanel.append(chips);
  }).catch((e) => { recPanel.innerHTML = "<h2>Careers to explore at your level</h2>" + errorBox(e.message); });

  const quick = el("section", { className: "panel" });
  quick.append(el("h2", {}, "Jump in"));
  const row = el("div", { className: "row" });
  [["Explore careers", "Career Explorer"], ["Analyze my skills", "Skill Gap"], ["Build a roadmap", "Roadmaps"], ["Start a project", "Project Studio"]]
    .forEach(([label, page], i) => {
      const b = el("button", { className: i ? "ghost" : "", type: "button", textContent: label });
      b.addEventListener("click", () => go(page));
      row.append(b);
    });
  quick.append(row);
  view.append(quick);

  const tour = el("section", { className: "panel tour-panel" });
  tour.innerHTML = `
    <div class="tour-copy">
      <span class="badge">20-SECOND PRODUCT TOUR</span>
      <h2>See how SkillBridge helps you plan a career with evidence</h2>
      <p class="muted">A local, self-contained walkthrough. No external video host, no tracking.</p>
    </div>
    <video controls preload="metadata" playsinline poster="/assets/tour-poster.png">
      <source src="/assets/skillbridge-tour.webm" type="video/webm" />
      <source src="/assets/skillbridge-tour.mp4" type="video/mp4" />
      Your browser does not support HTML video.
    </video>`;
  view.append(tour);

  try {
    const p = await api("/progress");
    defs.forEach(([, key], i) => { cards.children[i].querySelector(".v").textContent = p[key]; });
    statusPanel.innerHTML = "<h2>Project status</h2>" + donut([
      { label: "Planned", value: p.projects_planned, color: "#3b82f6" },
      { label: "In progress", value: p.projects_in_progress, color: "#8b5cf6" },
      { label: "Completed", value: p.projects_completed, color: "#34d399" },
    ]);
    const total = p.learning_activity_total;
    learnPanel.innerHTML = "<h2>Learning progress</h2>" + (total
      ? bars([
        ["Activities completed", p.learning_activities_completed, total],
        ["Projects completed", p.projects_completed, p.project_total],
      ]) + `<div class="chips"><span class="chip">${p.skill_assessment_total} skill assessments</span><span class="chip">${p.portfolio_total} portfolio items</span></div>`
      : empty("Nothing tracked yet", "Generate a roadmap to start tracking learning activities."));
  } catch (e) {
    statusPanel.innerHTML = "<h2>Project status</h2>" + errorBox(e.message);
    learnPanel.innerHTML = "<h2>Learning progress</h2>" + errorBox("Progress data is unavailable right now.");
  }
}

// ---------- Career Explorer ----------
async function viewCareers(view) {
  view.append(head("Career Explorer", "Search official O*NET occupations"));
  const panel = el("div", { className: "panel" });
  const input = el("input", { placeholder: "Occupation title, code, or alternate title (e.g. nurse)", "aria-label": "Search occupations" });
  const btn = labeled(el("button", { textContent: "Search", type: "button" }));
  panel.append(el("div", { className: "row" }, el("div", { className: "grow" }, input), btn));
  const results = el("div", {});
  panel.append(results);
  view.append(panel);
  const detail = el("div", { className: "panel hidden" });
  view.append(detail);
  window.openCareer = (id) => { showDetail(id, detail); detail.scrollIntoView({ behavior: "smooth", block: "start" }); };

  async function search() {
    results.innerHTML = skeleton(3);
    try {
      const items = await api(`/occupations/search?q=${encodeURIComponent(input.value.trim())}&limit=25`);
      results.innerHTML = "";
      if (!items.length) { results.innerHTML = empty("No matches", "Try a different title or keyword. If this stays empty, an administrator must import O*NET data."); return; }
      items.forEach((it) => {
        const row = el("div", { className: "list-item" });
        row.innerHTML = `<h3>${esc(it.title)}</h3><div class="muted tiny">${esc(it.onet_soc_code)} · O*NET ${esc(it.dataset_version || "?")}</div>`;
        const open = el("button", { className: "small", textContent: "View details", type: "button" });
        open.addEventListener("click", () => { showDetail(it.id, detail); detail.scrollIntoView({ behavior: "smooth", block: "start" }); });
        row.append(el("div", { style: "margin-top:10px" }, open));
        results.append(row);
      });
    } catch (e) { results.innerHTML = errorBox(e.message); }
  }
  btn.addEventListener("click", search);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") search(); });
}

async function showDetail(id, detail) {
  detail.classList.remove("hidden");
  detail.innerHTML = skeleton(2);
  try {
    const d = await api(`/occupations/${id}?limit=40`);
    const o = d.occupation;
    const rated = d.descriptors.filter((x) => x.rating != null && x.scale === "IM")
      .sort((a, b) => b.rating - a.rating).slice(0, 12);
    detail.innerHTML =
      `<div class="row center"><h2 class="grow">${esc(o.title)}</h2><span class="badge">${esc(o.onet_soc_code)}</span></div>` +
      `<p>${esc(o.description || "")}</p>` +
      (rated.length ? `<h2 style="margin-top:16px">Most important abilities</h2><p class="muted tiny">O*NET importance rating, scale 1 to 5</p>${bars(rated.map((x) => [x.name, x.rating, 5]))}`
        : empty("No rated descriptors", "None were imported for this occupation.")) +
      `<p style="margin-top:14px"><a href="https://www.onetonline.org/link/summary/${esc(o.onet_soc_code)}" target="_blank" rel="noopener">View the full profile on O*NET OnLine ↗</a></p>` +
      `<div class="muted tiny" style="margin-top:12px">${esc(d.attribution.credit)} · <a href="${esc(d.attribution.source_url)}" target="_blank" rel="noopener">O*NET database</a> · <a href="${esc(d.attribution.license_url)}" target="_blank" rel="noopener">CC BY 4.0 license</a></div>`;
    const save = labeled(el("button", { className: "small", textContent: "Save career", type: "button", style: "margin-top:14px" }));
    save.addEventListener("click", async () => {
      try { await api(`/occupations/saved/${id}`, { method: "PUT" }); toast("Career saved."); } catch (e) { toast(e.message); }
    });
    detail.append(save);
    try {
      const p = await api(`/occupations/${id}/profile`);
      const paths = p.pathways.map((w) => `<div class="path ${w.most_common ? "common" : ""}"><b>${esc(w.label)}</b>
        <span class="muted tiny">${w.percent_of_workers != null ? `${w.percent_of_workers}% of workers · ` : ""}${esc(w.source)}</span>
        <p class="muted" style="margin:6px 0 0">${esc(w.summary)}</p>${w.most_common ? '<span class="badge ok" style="margin-top:8px">Most common route</span>' : ""}</div>`).join("");
      const zone = p.job_zone ? `<p class="muted"><b>How much preparation?</b> ${esc(p.job_zone.name)}. ${esc(p.job_zone.education || "")}</p>` : "";
      detail.insertAdjacentHTML("beforeend",
        `<h2 style="margin-top:20px">Getting started at your level (${esc(levelName())})</h2><ul class="tips">${p.getting_started.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>` +
        `<h2 style="margin-top:20px">Ways into this career</h2>${zone}<div class="path-grid">${paths}</div>`);
    } catch (e) { detail.insertAdjacentHTML("beforeend", errorBox(e.message)); }
  } catch (e) { detail.innerHTML = errorBox(e.message); }
}

// ---------- Skill Gap ----------
function viewSkillGap(view) {
  view.append(head("Skill Gap Analyzer", "Compare your skills with official O*NET requirements"));
  view.append(levelNote());
  const panel = el("div", { className: "panel" });
  const title = el("input", { placeholder: "Occupation title (e.g. Registered Nurses)" });
  const skills = el("textarea", { placeholder: "One skill per line, e.g.\nCritical Thinking\nActive Listening\nPatient care" });
  const btn = labeled(el("button", { textContent: "Analyze", type: "button" }));
  panel.append(el("label", {}, "Occupation", title), el("label", {}, "Current skills", skills), btn);
  const out = el("div", {});
  panel.append(out);
  view.append(panel);
  btn.addEventListener("click", async () => {
    if (!title.value.trim()) { toast("Enter an occupation first."); return; }
    out.innerHTML = skeleton(2);
    setBusy(btn, true, "Analyzing…");
    try {
      const r = await api("/skill-gap", { method: "POST", body: {
        occupation_title: title.value.trim(),
        current_skills: skills.value.split("\n").map((s) => s.trim()).filter(Boolean),
      }});
      const chips = (arr, cls, cap = 24) => arr.length
        ? `<div class="chips">${[...arr].sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0)).slice(0, cap).map((x) => `<span class="chip ${cls}">${esc(x.name)}${x.rating != null ? ` · ${esc(x.rating)}` : ""}</span>`).join("")}${arr.length > cap ? `<span class="chip">+${arr.length - cap} more</span>` : ""}</div>`
        : '<p class="muted">None found.</p>';
      const rest = r.gaps.filter((g) => !(r.focus || []).some((f) => f.name === g.name));
      out.innerHTML =
        `<div class="row center" style="margin-top:18px"><h2 class="grow">${esc(r.occupation)}</h2><span class="badge">${esc(r.source)}</span><span class="badge">${esc(levelName())} view</span></div>` +
        (r.notice ? `<div class="notice">${esc(r.notice)}</div>` : "") +
        (r.source_url ? `<p class="tiny"><a href="${esc(r.source_url)}" target="_blank" rel="noopener">Verify on O*NET OnLine ↗</a></p>` : "") +
        (r.guidance ? `<div class="level-banner" style="margin-top:14px"><b>Start here</b><div class="muted">${esc(r.guidance)}</div></div>${chips(r.focus || [], "gap", 12)}` : "") +
        `<h2 style="margin-top:16px">Strengths you already have</h2>${r.strengths.length ? chips(r.strengths, "good") : '<p class="muted">Nothing listed yet. That is fine, add skills above, or just follow the Start here list.</p>'}` +
        (rest.length ? `<details style="margin-top:16px"><summary class="muted">See all other skills for this career (${rest.length})</summary>${chips(rest, "gap", 40)}</details>` : "");
    } catch (e) { out.innerHTML = errorBox(e.message); } finally { setBusy(btn, false, "Analyzing…"); }
  });
}

// ---------- Roadmaps ----------
function viewRoadmaps(view) {
  view.append(head("Learning Roadmaps", "Personalized plans built from O*NET occupation data"));
  view.append(levelNote());
  const panel = el("div", { className: "panel" });
  const title = el("input", { placeholder: "Target occupation (e.g. Software Developers)" });
  const skills = el("textarea", { placeholder: "Skills you already have, one per line (optional)", style: "min-height:70px" });
  const btn = labeled(el("button", { textContent: "Generate roadmap", type: "button" }));
  panel.append(el("label", {}, "Target occupation", title), el("label", {}, "Current skills", skills), btn);
  const msg = el("div", {});
  panel.append(msg);
  view.append(panel);
  const list = el("div", {});
  view.append(list);

  async function load() {
    list.innerHTML = skeleton(2);
    try {
      const [roadmaps, activities] = await Promise.all([api("/roadmaps"), api("/activities")]);
      list.innerHTML = "";
      if (!roadmaps.length) { list.innerHTML = `<div class="panel">${empty("No roadmaps yet", "Generate one above to get a step-by-step plan.")}</div>`; return; }
      roadmaps.forEach((rm) => {
        const steps = activities.filter((a) => a.roadmap_id === rm.id);
        const done = steps.filter((a) => a.status === "completed").length;
        const pct = steps.length ? Math.round((100 * done) / steps.length) : 0;
        const card = el("section", { className: "panel" });
        card.innerHTML = `<div class="row center"><h2 class="grow">${esc(rm.occupation_title)}</h2><span class="badge ${pct === 100 ? "ok" : ""}">${done}/${steps.length} steps</span></div>
          <div class="bar" style="margin:10px 0"><i style="width:${pct}%"></i></div>
          <div class="result" style="max-height:240px">${esc(rm.content)}</div>`;
        const ul = el("ul", { className: "steps" });
        steps.forEach((a) => {
          const cb = el("input", { type: "checkbox", checked: a.status === "completed" });
          cb.addEventListener("change", async () => {
            try {
              await api(`/activities/${a.id}`, { method: "PATCH", body: { title: a.title, roadmap_id: rm.id, status: cb.checked ? "completed" : "not_started" } });
              load();
            } catch (e) { toast(e.message); cb.checked = !cb.checked; }
          });
          ul.append(el("li", { className: a.status === "completed" ? "done" : "" }, cb, el("span", {}, a.title)));
        });
        card.append(ul);
        const refs = (rm.sources || []).filter((s) => s.url).map((s) => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)} (O*NET OnLine) ↗</a>`);
        if (refs.length) card.append(el("p", { className: "tiny muted", innerHTML: "Sources: " + refs.join(" · ") }));
        const meta = el("div", { className: "row center", style: "margin-top:12px" },
          el("span", { className: "badge " + (rm.generated === false ? "warn" : ""), textContent: "Created " + fmtDate(rm.created_at) }));
        const del = el("button", { className: "danger small", textContent: "Delete", type: "button" });
        del.addEventListener("click", async () => {
          if (!confirm("Delete this roadmap and its steps?")) return;
          try { await api(`/roadmaps/${rm.id}`, { method: "DELETE" }); load(); } catch (e) { toast(e.message); }
        });
        meta.append(del);
        card.append(meta);
        list.append(card);
      });
    } catch (e) { list.innerHTML = `<div class="panel">${errorBox(e.message)}</div>`; }
  }

  btn.addEventListener("click", async () => {
    if (!title.value.trim()) { toast("Enter a target occupation first."); return; }
    setBusy(btn, true, "Generating…");
    msg.innerHTML = "";
    try {
      const r = await api("/roadmaps", { method: "POST", body: {
        occupation_title: title.value.trim(),
        current_skills: skills.value.split("\n").map((s) => s.trim()).filter(Boolean),
      }});
      toast(r.generated ? "Roadmap generated." : "Roadmap compiled from O*NET data.");
      load();
    } catch (e) { msg.innerHTML = errorBox(e.message); } finally { setBusy(btn, false, "Generating…"); }
  });
  load();
}

// ---------- Project Studio ----------
const PROJECT_STATUSES = ["planned", "in_progress", "completed"];
function viewProjects(view) {
  view.append(head("Project Studio", "Career-related projects with trackable milestones"));
  view.append(levelNote());
  const panel = el("div", { className: "panel" });
  const occ = el("input", { placeholder: "Occupation (e.g. Software Developers)" });
  const exp = el("textarea", { placeholder: "Your experience level or interests (optional)", style: "min-height:70px" });
  const btn = labeled(el("button", { textContent: "Generate project", type: "button" }));
  panel.append(el("label", {}, "Occupation", occ), el("label", {}, "About you", exp), btn);
  const msg = el("div", {});
  panel.append(msg);
  view.append(panel);
  const list = el("div", {});
  view.append(list);

  async function patch(p, body) {
    try { await api(`/projects/${p.id}`, { method: "PATCH", body }); load(); } catch (e) { toast(e.message); }
  }
  async function load() {
    list.innerHTML = skeleton(2);
    try {
      const projects = await api("/projects");
      list.innerHTML = "";
      if (!projects.length) { list.innerHTML = `<div class="panel">${empty("No projects yet", "Generate a project above to get a brief and milestones.")}</div>`; return; }
      projects.forEach((p) => {
        const card = el("section", { className: "panel" });
        card.innerHTML = `<div class="row center"><h2 class="grow">${esc(p.title)}</h2><span class="badge ${p.status === "completed" ? "ok" : ""}">${esc(p.status.replace("_", " "))}</span></div>
          <div class="bar" style="margin:10px 0"><i style="width:${p.progress || 0}%"></i></div>
          <p class="muted" style="white-space:pre-wrap">${esc(p.description || "")}</p>`;
        const ul = el("ul", { className: "steps" });
        (p.milestones || []).forEach((m, i) => {
          const cb = el("input", { type: "checkbox", checked: !!m.done });
          cb.addEventListener("change", () => {
            const next = p.milestones.map((x, j) => (j === i ? { ...x, done: cb.checked } : x));
            patch(p, { milestones: next });
          });
          ul.append(el("li", { className: m.done ? "done" : "" }, cb, el("span", {}, m.title)));
        });
        card.append(ul);
        const select = el("select");
        PROJECT_STATUSES.forEach((s) => select.append(el("option", { value: s, selected: s === p.status }, s.replace("_", " "))));
        select.addEventListener("change", () => patch(p, { status: select.value }));
        const del = el("button", { className: "danger small", textContent: "Delete", type: "button" });
        del.addEventListener("click", async () => {
          if (!confirm("Delete this project?")) return;
          try { await api(`/projects/${p.id}`, { method: "DELETE" }); load(); } catch (e) { toast(e.message); }
        });
        card.append(el("div", { className: "row center", style: "margin-top:12px" }, el("span", { className: "muted tiny" }, "Status:"), select, del));
        list.append(card);
      });
    } catch (e) { list.innerHTML = `<div class="panel">${errorBox(e.message)}</div>`; }
  }

  btn.addEventListener("click", async () => {
    if (!occ.value.trim()) { toast("Enter an occupation first."); return; }
    setBusy(btn, true, "Generating…");
    msg.innerHTML = "";
    try {
      await api("/projects", { method: "POST", body: { occupation: occ.value.trim(), experience: exp.value.trim() } });
      toast("Project created.");
      load();
    } catch (e) { msg.innerHTML = errorBox(e.message); } finally { setBusy(btn, false, "Generating…"); }
  });
  load();
}

// ---------- Portfolio ----------
function viewPortfolio(view) {
  view.append(head("Portfolio", "Upload and organize your work"));
  const panel = el("div", { className: "panel" });
  const file = el("input", { type: "file", accept: "image/png,image/jpeg,image/webp,image/gif" });
  const btn = labeled(el("button", { textContent: "Upload", type: "button" }));
  panel.append(el("label", {}, "Image file", file), btn,
    el("p", { className: "muted tiny", style: "margin-top:10px" }, "Files stay on the server you connect to. AI portfolio review is only available when the server operator enables it."));
  const msg = el("div", {});
  panel.append(msg);
  view.append(panel);
  const list = el("div", {});
  view.append(list);

  async function load() {
    list.innerHTML = skeleton(2);
    try {
      const items = await api("/portfolio");
      list.innerHTML = "";
      if (!items.length) { list.innerHTML = `<div class="panel">${empty("Your portfolio is empty", "Upload an image of your work to get started.")}</div>`; return; }
      const panelList = el("section", { className: "panel" });
      panelList.append(el("h2", {}, `${items.length} item${items.length === 1 ? "" : "s"}`));
      items.forEach((it) => {
        const row = el("div", { className: "list-item" });
        row.innerHTML = `<div class="row center"><h3 class="grow">${esc(it.title || it.filename)}</h3><span class="badge">${fmtDate(it.created_at)}</span></div>
          <div class="muted tiny">${esc(it.filename)}</div>${it.evaluation ? `<div class="result">${esc(typeof it.evaluation === "string" ? it.evaluation : JSON.stringify(it.evaluation, null, 2))}</div>` : ""}`;
        panelList.append(row);
      });
      list.append(panelList);
    } catch (e) { list.innerHTML = `<div class="panel">${errorBox(e.message)}</div>`; }
  }

  btn.addEventListener("click", async () => {
    if (!file.files.length) { toast("Choose a file first."); return; }
    const form = new FormData();
    form.append("file", file.files[0]);
    setBusy(btn, true, "Uploading…");
    msg.innerHTML = "";
    try {
      await api("/portfolio/upload", { method: "POST", form });
      file.value = "";
      toast("Uploaded.");
      load();
    } catch (e) { msg.innerHTML = errorBox(e.message); } finally { setBusy(btn, false, "Uploading…"); }
  });
  load();
}

// ---------- Opportunities ----------
const APP_STATUSES = ["saved", "preparing", "applied", "closed"];
function viewOpportunities(view) {
  view.append(head("Opportunities & Colleges", "Official directories. Verify details at the source."));
  const panel = el("div", { className: "panel" });
  const input = el("input", { placeholder: "Career, college, or training topic (e.g. nursing)", "aria-label": "Search opportunities" });
  const btn = labeled(el("button", { textContent: "Find", type: "button" }));
  panel.append(el("div", { className: "row" }, el("div", { className: "grow" }, input), btn));
  const results = el("div", {});
  panel.append(results);
  view.append(panel);

  const savedPanel = el("div", { className: "panel" });
  savedPanel.append(el("h2", {}, "Saved opportunities"));
  const savedList = el("div", {});
  savedPanel.append(savedList);
  view.append(savedPanel);

  async function loadSaved() {
    try {
      const items = await api("/opportunities/saved");
      savedList.innerHTML = items.length ? "" : empty("Nothing saved yet", "Search above and click Save to track an opportunity.");
      items.forEach((it) => {
        const row = el("div", { className: "list-item" });
        row.innerHTML = `<h3>${esc(it.title)}</h3><div class="muted tiny">${esc(it.organization || "")}</div>`;
        const select = el("select");
        APP_STATUSES.forEach((s) => select.append(el("option", { value: s, selected: s === it.application_status }, s)));
        select.addEventListener("change", async () => {
          try { await api(`/opportunities/saved/${it.id}`, { method: "PATCH", body: { application_status: select.value } }); toast("Status updated."); }
          catch (e) { toast(e.message); }
        });
        const open = el("a", { href: it.url || "#", target: "_blank", rel: "noopener", textContent: "Open ↗" });
        const del = el("button", { className: "ghost small", textContent: "Remove", type: "button" });
        del.addEventListener("click", async () => {
          try { await api(`/opportunities/saved/${it.id}`, { method: "DELETE" }); loadSaved(); } catch (e) { toast(e.message); }
        });
        row.append(el("div", { className: "row center", style: "margin-top:10px" },
          el("span", { className: "muted tiny" }, "Status:"), select, open, del));
        savedList.append(row);
      });
    } catch (e) { savedList.innerHTML = errorBox(e.message); }
  }

  async function find() {
    const q = input.value.trim();
    if (!q) { results.innerHTML = empty("Enter a topic", "Try a career, college, or training topic."); return; }
    results.innerHTML = skeleton(3);
    try {
      const items = await api(`/opportunities?q=${encodeURIComponent(q)}`, { auth: false });
      results.innerHTML = items.length ? "" : empty("No results", "Try a broader topic.");
      items.forEach((it) => {
        const row = el("div", { className: "list-item" });
        row.innerHTML = `<h3>${esc(it.title)}</h3><div class="muted tiny">${esc(it.organization)}</div><p>${esc(it.details)}</p>`;
        const open = el("a", { href: it.url, target: "_blank", rel: "noopener", textContent: "Open source ↗" });
        const save = el("button", { className: "small", textContent: "Save", type: "button" });
        save.addEventListener("click", async () => {
          try {
            await api("/opportunities/save", { method: "POST", body: { title: it.title, organization: it.organization, url: it.url, details: it.details } });
            toast("Saved.");
            loadSaved();
          } catch (e) { toast(e.message); }
        });
        row.append(el("div", { className: "row center", style: "margin-top:10px" }, open, save));
        results.append(row);
      });
    } catch (e) { results.innerHTML = errorBox(e.message); }
  }
  btn.addEventListener("click", find);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") find(); });
  loadSaved();
}

// ---------- Settings ----------
function viewSettings(view) {
  view.append(head("Settings", "Account and data"));
  const panel = el("div", { className: "panel" });
  panel.innerHTML = `<h2>Account</h2><p class="muted">${esc(me.name)} · ${esc(me.email)} <span class="badge">${esc(me.role)}</span></p>`;
  panel.append(el("p", { className: "muted tiny", textContent: "Career guidance uses verified O*NET references by default. Optional text generation is managed privately by the server operator. Your data stays on the server you connect to." }));
  const lv = el("div", { style: "margin-top:16px" }, el("h2", {}, "Skill level"),
    el("p", { className: "muted" }, `Current level: ${levelInfo?.skill_level ? levelName() : "not chosen yet (beginner-friendly defaults)"}`));
  const change = el("button", { type: "button", className: "small" }, "Change skill level");
  change.addEventListener("click", () => showLevelModal(false));
  lv.append(change);
  panel.append(lv);
  const about = el("div", { className: "panel" });
  about.innerHTML = '<h2>About</h2><p class="muted">SkillBridge AI is open source. Source code: <a href="https://github.com/Kiwmoj/SkillBridgeAI" target="_blank" rel="noopener">github.com/Kiwmoj/SkillBridgeAI ↗</a></p>';
  view.append(panel, about);
}

// ---------- boot ----------
$("#logout").addEventListener("click", signOut);
initAuth();
if (token) enterApp();
