"use strict";

const API = "/api/v1";
const TOKEN_KEY = "skillbridge_token";
let token = localStorage.getItem(TOKEN_KEY) || null;
let me = null;

// ---------- API helper ----------
async function api(path, { method = "GET", body = null, auth = true } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (auth && token) headers["Authorization"] = `Bearer ${token}`;
  let res;
  try {
    res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : null });
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
  return node;
};
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), 2600);
}
function esc(s) { return String(s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

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
    btn.disabled = true;
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
    }
  });
  refreshStatus();
}

async function refreshStatus() {
  try {
    const h = await api("/health", { auth: false });
    $("#api-status").textContent = `${h.status} · v${h.version}` + (h.onet_version ? ` · O*NET ${h.onet_version}` : "");
  } catch {
    $("#api-status").textContent = "unreachable";
  }
}

function signOut() {
  token = null; me = null;
  localStorage.removeItem(TOKEN_KEY);
  $("#app").classList.add("hidden");
  $("#auth").classList.remove("hidden");
}

async function enterApp() {
  try { me = await api("/auth/me"); } catch { signOut(); return; }
  $("#auth").classList.add("hidden");
  $("#app").classList.remove("hidden");
  $("#who").textContent = `${me.name} · ${me.role}`;
  buildNav();
  go("Dashboard");
}

// ---------- navigation ----------
const PAGES = ["Dashboard", "Career Explorer", "Skill Gap", "Career Reality Check", "Opportunities", "Settings"];
let current = "Dashboard";
function buildNav() {
  const nav = $("#nav");
  nav.innerHTML = "";
  PAGES.forEach((p) => {
    const b = el("button", { className: "nav-item", textContent: p });
    b.addEventListener("click", () => go(p));
    nav.append(b);
  });
}
function go(page) {
  current = page;
  document.querySelectorAll(".nav-item").forEach((n) => n.classList.toggle("active", n.textContent === page));
  const view = $("#view");
  view.innerHTML = "";
  ({
    "Dashboard": viewDashboard,
    "Career Explorer": viewCareers,
    "Skill Gap": viewSkillGap,
    "Career Reality Check": viewReality,
    "Opportunities": viewOpportunities,
    "Settings": viewSettings,
  })[page](view);
}
function head(title, subtitle) {
  return el("div", { className: "page-head", innerHTML: `<h1>${esc(title)}</h1><p class="muted">${esc(subtitle)}</p>` });
}

// ---------- Dashboard ----------
async function viewDashboard(view) {
  view.append(head("Dashboard", "Your career development workspace"));
  const cards = el("div", { className: "cards" });
  view.append(cards);
  const defs = [
    ["Saved roadmaps", "saved_roadmaps"],
    ["Projects", "project_total"],
    ["Activities done", "learning_activities_completed"],
    ["Saved opportunities", "saved_opportunities"],
  ];
  defs.forEach(([k]) => cards.append(el("div", { className: "card", innerHTML: `<div class="k">${k}</div><div class="v">—</div>` })));
  try {
    const p = await api("/progress");
    defs.forEach(([, key], i) => { cards.children[i].querySelector(".v").textContent = p[key]; });
  } catch (e) { toast(e.message); }
}

// ---------- Career Explorer ----------
async function viewCareers(view) {
  view.append(head("Career Explorer", "Search official O*NET occupations"));
  const panel = el("div", { className: "panel" });
  const input = el("input", { placeholder: "Occupation title, code, or alternate title (e.g. nurse)" });
  const btn = el("button", { textContent: "Search" });
  panel.append(el("div", { className: "row" }, el("div", { className: "grow" }, input), btn));
  const results = el("div", {});
  panel.append(results);
  view.append(panel);
  const detail = el("div", { className: "panel hidden" });
  view.append(detail);

  async function search() {
    results.innerHTML = '<p class="muted">Searching… <span class="spinner"></span></p>';
    try {
      const items = await api(`/occupations/search?q=${encodeURIComponent(input.value.trim())}&limit=25`);
      results.innerHTML = "";
      if (!items.length) { results.innerHTML = '<p class="muted">No matches. An administrator must import O*NET data first.</p>'; return; }
      items.forEach((it) => {
        const row = el("div", { className: "list-item" });
        row.innerHTML = `<h3>${esc(it.title)}</h3><div class="muted tiny">${esc(it.onet_soc_code)} · O*NET ${esc(it.dataset_version || "?")}</div>`;
        const open = el("button", { className: "small", textContent: "View details" });
        open.addEventListener("click", () => showDetail(it.id, detail));
        row.append(el("div", { style: "margin-top:10px" }, open));
        results.append(row);
      });
    } catch (e) { results.innerHTML = `<p class="error">${esc(e.message)}</p>`; }
  }
  btn.addEventListener("click", search);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") search(); });
}

async function showDetail(id, detail) {
  detail.classList.remove("hidden");
  detail.innerHTML = '<p class="muted">Loading… <span class="spinner"></span></p>';
  try {
    const d = await api(`/occupations/${id}?limit=40`);
    const o = d.occupation;
    const skills = d.descriptors.filter((x) => x.rating != null).slice(0, 12)
      .map((x) => `• ${esc(x.name)} (${esc(x.category)}${x.rating != null ? ` · ${x.rating}` : ""})`).join("\n");
    detail.innerHTML =
      `<h2>${esc(o.title)}</h2><div class="muted tiny">${esc(o.onet_soc_code)}</div>` +
      `<p>${esc(o.description || "")}</p>` +
      `<div class="muted tiny">${esc(d.attribution.credit)}</div>` +
      `<div class="result">${esc(skills || "No rated descriptors imported.")}</div>`;
    const save = el("button", { className: "small", textContent: "Save career", style: "margin-top:12px" });
    save.addEventListener("click", async () => { try { await api(`/occupations/saved/${id}`, { method: "PUT" }); toast("Career saved."); } catch (e) { toast(e.message); } });
    detail.append(save);
  } catch (e) { detail.innerHTML = `<p class="error">${esc(e.message)}</p>`; }
}

// ---------- Skill Gap ----------
function viewSkillGap(view) {
  view.append(head("Skill Gap Analyzer", "Compare your skills with official O*NET requirements"));
  const panel = el("div", { className: "panel" });
  const title = el("input", { placeholder: "Occupation title (e.g. Registered Nurses)" });
  const skills = el("textarea", { placeholder: "Your current skills, one per line" });
  const btn = el("button", { textContent: "Analyze" });
  panel.append(el("label", {}, "Occupation", title), el("label", {}, "Current skills", skills), btn);
  const out = el("div", { className: "result hidden" });
  panel.append(out);
  view.append(panel);
  btn.addEventListener("click", async () => {
    out.classList.remove("hidden");
    out.textContent = "Analyzing…";
    try {
      const r = await api("/skill-gap", { method: "POST", body: {
        occupation_title: title.value.trim() || null,
        current_skills: skills.value.split("\n").map((s) => s.trim()).filter(Boolean),
      }});
      const fmt = (arr) => arr.length ? arr.map((x) => `• ${x.name}${x.rating != null ? ` (${x.rating})` : ""}`).join("\n") : "None found";
      out.textContent = `Occupation: ${r.occupation}\nSource: ${r.source}\n${r.notice || ""}\n\nStrengths:\n${fmt(r.strengths)}\n\nGaps:\n${fmt(r.gaps)}`;
    } catch (e) { out.textContent = e.message; }
  });
}

// ---------- Career Reality Check (AI) ----------
function viewReality(view) {
  view.append(head("Career Reality Check", "AI guidance grounded in retrieved sources"));
  const panel = el("div", { className: "panel" });
  const q = el("textarea", { placeholder: "Describe the career, costs, training, or trade-offs you want examined." });
  const btn = el("button", { textContent: "Generate" });
  panel.append(el("label", {}, "Your question", q), btn);
  const out = el("div", { className: "result hidden" });
  panel.append(out);
  view.append(panel);
  btn.addEventListener("click", async () => {
    if (!q.value.trim()) { toast("Enter a question first."); return; }
    out.classList.remove("hidden");
  out.innerHTML = 'Working… <span class="spinner"></span>';
    btn.disabled = true;
    try {
      const r = await api("/ai/generate", { method: "POST", body: { purpose: "Career Reality Check", question: q.value.trim() } });
    const header = r.generated ? "AI-generated guidance" : "Compiled from official sources (not AI-generated)";
    const sources = (r.sources || []).map((s) => {
      const ref = [s.reference, s.url, s.text].filter(Boolean).join("\n");
      return `[${s.id}] ${s.title} (${s.source_type})\n${ref}`;
    }).join("\n\n");
    out.textContent = `${header}\n\n${r.answer}\n\nRetrieved references:\n${sources || "None"}`;
    } catch (e) {
    out.textContent = "This request could not be completed.\n\n" + e.message;
    } finally { btn.disabled = false; }
  });
}

// ---------- Opportunities ----------
const APP_STATUSES = ["saved", "preparing", "applied", "closed"];
function viewOpportunities(view) {
  view.append(head("Opportunities & Colleges", "Official directories — verify details at the source"));
  const panel = el("div", { className: "panel" });
  const input = el("input", { placeholder: "Career, college, or training topic (e.g. nursing)" });
  const btn = el("button", { textContent: "Find" });
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
      savedList.innerHTML = items.length ? "" : '<p class="muted">Nothing saved yet. Search above and click Save.</p>';
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
        const del = el("button", { className: "ghost small", textContent: "Remove" });
        del.addEventListener("click", async () => {
          try { await api(`/opportunities/saved/${it.id}`, { method: "DELETE" }); loadSaved(); } catch (e) { toast(e.message); }
        });
        const controls = el("div", { className: "row", style: "margin-top:10px;align-items:center" },
          el("span", { className: "muted tiny" }, "Status:"), select, open, del);
        row.append(controls);
        savedList.append(row);
      });
    } catch (e) { savedList.innerHTML = `<p class="error">${esc(e.message)}</p>`; }
  }

  async function find() {
    const q = input.value.trim();
    if (!q) { results.innerHTML = '<p class="muted">Enter a career, college, or training topic first.</p>'; return; }
    results.innerHTML = '<p class="muted">Searching… <span class="spinner"></span></p>';
    try {
      const items = await api(`/opportunities?q=${encodeURIComponent(q)}`, { auth: false });
      results.innerHTML = "";
      items.forEach((it) => {
        const row = el("div", { className: "list-item" });
        row.innerHTML = `<h3>${esc(it.title)}</h3><div class="muted tiny">${esc(it.organization)}</div><p>${esc(it.details)}</p>`;
        const open = el("a", { href: it.url, target: "_blank", rel: "noopener", textContent: "Open source ↗" });
        const save = el("button", { className: "small", textContent: "Save" });
        save.addEventListener("click", async () => {
          try {
            await api("/opportunities/save", { method: "POST", body: {
              title: it.title, organization: it.organization, url: it.url, details: it.details } });
            toast("Saved.");
            loadSaved();
          } catch (e) { toast(e.message); }
        });
        row.append(el("div", { className: "row", style: "margin-top:10px;align-items:center" }, open, save));
        results.append(row);
      });
    } catch (e) { results.innerHTML = `<p class="error">${esc(e.message)}</p>`; }
  }
  btn.addEventListener("click", find);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") find(); });
  loadSaved();
}

// ---------- Settings ----------
function viewSettings(view) {
  view.append(head("Settings", "Account and data"));
  const panel = el("div", { className: "panel" });
  panel.innerHTML = `<h2>Account</h2><p class="muted">${esc(me.name)} — ${esc(me.email)} <span class="badge">${esc(me.role)}</span></p>`;
  const note = el("p", { className: "muted tiny", innerHTML: "AI features require a Gemini key configured on the backend. Your data stays on the server you connect to." });
  panel.append(note);
  view.append(panel);
}

// ---------- boot ----------
$("#logout").addEventListener("click", signOut);
initAuth();
if (token) enterApp();
