// Spot: a fictional Teams workspace backed by the existing governance contracts.
"use strict";
const $ = (sel) => document.querySelector(sel);
const icon = (name, cls = "") => `<span aria-hidden="true" class="ic ${cls}" style="--i:url(/static/icons/${name}.svg)"></span>`;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function store(key, value) {
  try { if (value === undefined) return localStorage.getItem(key); localStorage.setItem(key, value); } catch { return null; }
}
const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
function applyTheme(theme, save = false) {
  document.documentElement.dataset.theme = theme;
  if (save) store("spot.theme", theme);
  const dark = theme === "dark";
  const toggle = $("#theme-toggle");
  toggle.setAttribute("aria-pressed", String(dark));
  toggle.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
  toggle.title = dark ? "Switch to light mode" : "Switch to dark mode";
  toggle.innerHTML = icon(dark ? "weather_sunny_20_regular" : "weather_moon_20_regular");
  $("meta[name='theme-color']").content = dark ? "#1b1b23" : "#eeedf5";
  const scrollTop = $("#feed").scrollTop;
  refreshCardThemes();
  $("#feed").scrollTo({ top: scrollTop, behavior: "instant" });
}
systemTheme.addEventListener("change", (e) => {
  if (!["light", "dark"].includes(store("spot.theme"))) applyTheme(e.matches ? "dark" : "light");
});
const COMMANDS = [
  ["add", "Reply to a message to capture its decision"],
  ["propose", "Propose a change to your team's requirements"],
  ["ask", "Ask about approved requirements, with sources"],
  ["history", "See approved versions and their receipts"],
  ["pending", "Review changes waiting for approval"],
  ["help", "See what Spot can do"],
];
const savedLoc = store("spot.loc") || "chat:cutover-sync";
const NATIVE_APPS = {
  calendar: { title: "Calendar", glyph: "calendar_ltr_24_regular", description: "Your program, one meeting at a time.", note: "Sample agenda · October 12–16, 2026" },
};
const S = {
  user: store("spot.user2") || window.DEMO_DEFAULT_USER || "marcus.chen", view: savedLoc.startsWith("channel:") ? "teams" : "chat",
  loc: savedLoc, spotTab: "pending", contentTab: "conversation", state: null,
  posts: [], items: [], documents: [], errors: {}, replyTo: null, pending: null,
  collapsed: new Set(["ops", "pay"]), filter: "all", busy: false, loading: false,
  requestId: 0, drawerReturn: null, agendaDay: "all",
};
function md(text) {
  return esc(text).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|\s)(@(Spot|Payments|Ops Automation))\b/gi, '$1<span class="mention">$2</span>');
}
function person(name) {
  return S.state?.people[name] || { name, display_name: name, title: "", team: "", avatar_color: "#77718d" };
}
function initials(name) { return person(name).display_name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase(); }
function avatar(name, size = "", presence = false) {
  if (name === "spot") return `<span class="av bot ${size}" title="Spot"><img src="/static/spot-avatar.png" alt=""></span>`;
  const p = person(name);
  return `<span class="av ${size}" style="background:${esc(p.avatar_color)}" title="${esc(p.display_name)}"><span>${esc(initials(name))}</span>${S.state?.people[name] ? `<img src="/static/avatars/${encodeURIComponent(name)}.jpg" alt="" decoding="async">` : ""}${presence ? '<i class="presence" aria-hidden="true"></i>' : ""}</span>`;
}
// Broken local portraits gracefully reveal each person's initials.
document.addEventListener("error", (e) => { if (e.target.matches?.(".av img")) e.target.remove(); }, true);
function personTitle(name) { const p = person(name); return [p.title, p.team].filter(Boolean).join(" · "); }
function teamTile(team) {
  const letters = team.name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2);
  return `<span class="av tile" style="background:${esc(team.avatar_color)}">${esc(letters)}</span>`;
}
function chatAvatar(chat) {
  if (chat.kind === "bot") return avatar("spot");
  const others = chat.members.filter((m) => m !== S.user);
  if (others.length < 2) return avatar(others[0] || S.user);
  return `<span class="group-av">${avatar(others[0])}${avatar(others[1])}</span>`;
}
function time(ts) { return new Date(ts).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }); }
function shortDate(ts) {
  const d = new Date(ts);
  return d.toDateString() === new Date().toDateString() ? time(ts) : d.toLocaleDateString([], { month: "short", day: "numeric" });
}
function fullDate(ts) { return new Date(ts).toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" }); }
function currentLoc() { return S.view === "spot" ? `spot:${S.user}` : S.loc; }
function empty(title, copy, glyph = "checkmark_circle_16_filled") {
  return `<div class="empty">${icon(glyph)}<strong>${esc(title)}</strong>${esc(copy)}</div>`;
}
// ---------------------------------------------------------------- Adaptive Cards

const fg = (d, s = d) => ({ default: d, subtle: s });
function createCardHostConfig() {
  const style = getComputedStyle(document.documentElement);
  const color = (name) => style.getPropertyValue(name).trim();
  const colors = {
    default: fg(color("--text"), color("--subtle")), dark: fg(color("--text"), color("--subtle")),
    light: fg("#FFFFFF", "#F5F5F5"), accent: fg(color("--brand")), good: fg(color("--green")),
    warning: fg(color("--warning")), attention: fg(color("--red")),
  };
  return new AdaptiveCards.HostConfig({
    fontFamily: style.getPropertyValue("--font").trim(),
    supportsInteractivity: true,
    spacing: { small: 4, default: 8, medium: 12, large: 16, extraLarge: 24, padding: 20 },
    separator: { lineThickness: 1, lineColor: color("--stroke") },
    fontSizes: { small: 12, default: 14, medium: 16, large: 18, extraLarge: 24 },
    fontWeights: { lighter: 300, default: 400, bolder: 600 },
    containerStyles: {
      default: { backgroundColor: color("--card"), foregroundColors: colors },
      emphasis: { backgroundColor: color("--hover"), foregroundColors: colors },
    },
    actions: { maxActions: 5, spacing: "default", buttonSpacing: 8, actionsOrientation: "horizontal", actionAlignment: "left",
      showCard: { actionMode: "inline", inlineTopMargin: 12, style: "emphasis" } },
    factSet: { title: { weight: "bolder", size: "default", color: "default", wrap: true, maxWidth: 120 },
      value: { size: "default", color: "default", wrap: true }, spacing: 12 },
    inputs: { label: { inputSpacing: "small", requiredInputs: { weight: "bolder", suffix: " *", suffixColor: "attention" },
      optionalInputs: { weight: "bolder" } }, errorMessage: { size: "small", color: "attention" } },
  });
}

AdaptiveCards.AdaptiveCard.onProcessMarkdown = (text, result) => {
  result.outputHtml = md(text);
  result.didProcess = true;
};

function renderCard(json, messageId, loc) {
  const reviewer = json.actions?.find((a) => ["approve", "reject"].includes(a.data?.action))?.data.required_team;
  if (reviewer && !(S.state.me.role === "Approver" && S.state.me.team === reviewer)) {
    json = { ...json,
      actions: json.actions.filter((a) => !["approve", "reject"].includes(a.data?.action)),
      body: [...json.body, { type: "TextBlock", text: `Review is assigned to ${reviewer} approvers.`,
        wrap: true, isSubtle: true, size: "Small", spacing: "Medium" }],
    };
  }
  const card = new AdaptiveCards.AdaptiveCard();
  card.hostConfig = createCardHostConfig();
  card.onExecuteAction = (action) => {
    if (action instanceof AdaptiveCards.SubmitAction) runAction(messageId, action.data, loc);
  };
  card.parse(json);
  return card.render();
}

function cardHost(json, messageId, loc) {
  const host = document.createElement("div");
  host.className = "card-host";
  host.spotCard = { json, messageId, loc };
  try { host.appendChild(renderCard(json, messageId, loc)); }
  catch (e) { host.textContent = `Card failed to render: ${e}`; }
  return host;
}

function refreshCardThemes() {
  // Re-render inline card colors while retaining in-progress forms and expanded text.
  document.querySelectorAll(".card-host").forEach((host) => {
    if (!host.spotCard) return;
    const fields = [...host.querySelectorAll("input,textarea,select")];
    const values = fields.map((field) => ({ value: field.value, checked: field.checked }));
    const focused = fields.indexOf(document.activeElement);
    const selection = focused >= 0 ? [fields[focused].selectionStart, fields[focused].selectionEnd] : null;
    const expanded = [...host.querySelectorAll('button[aria-expanded="true"]')].map((b) => b.textContent);
    const { json, messageId, loc } = host.spotCard;
    host.replaceChildren(renderCard(json, messageId, loc));
    expanded.forEach((title) => [...host.querySelectorAll('button[aria-expanded="false"]')].find((b) => b.textContent === title)?.click());
    const nextFields = [...host.querySelectorAll("input,textarea,select")];
    nextFields.forEach((field, i) => {
      if (!values[i]) return;
      field.value = values[i].value;
      if (field.type === "checkbox" || field.type === "radio") field.checked = values[i].checked;
    });
    if (focused >= 0 && nextFields[focused]) {
      nextFields[focused].focus({ preventScroll: true });
      if (selection[0] !== null) nextFields[focused].setSelectionRange(...selection);
    }
    if (S.busy) host.querySelectorAll(".ac-pushButton").forEach((b) => { b.disabled = true; });
  });
}

function errorBox(text) {
  return `<div class="card-error">${icon("warning_16_filled")}<div>${esc(text)}</div></div>`;
}

// API requests capture their identity and ignore older navigation responses.
async function api(path, body) {
  const res = await fetch(path, body === undefined ? undefined : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("The workspace couldn't complete that request. Please try again.");
  return res.json();
}
const q = (params) => new URLSearchParams(params).toString();
async function loadState() {
  const user = S.user;
  const [state, files] = await Promise.all([
    api(`/api/state?${q({ user })}`), api(`/api/documents?${q({ user })}`),
  ]);
  if (S.user !== user) return;
  S.state = state; S.documents = files.documents;
  renderChrome();
}
async function loadMain(scroll = "bottom") {
  const requestId = ++S.requestId;
  const user = S.user, loc = currentLoc();
  S.loading = true;
  $("#feed").setAttribute("aria-busy", "true");
  $("#send").disabled = true;
  try {
    if (S.view === "spot" && S.spotTab !== "chat") {
      const { items } = await api(`/api/spot/${S.spotTab}?${q({ user })}`);
      if (requestId !== S.requestId) return;
      S.items = items;
    } else if (S.view !== "activity" && !NATIVE_APPS[S.view]) {
      const { posts, error } = await api(`/api/location?${q({ user, loc })}`);
      if (requestId !== S.requestId) return;
      S.posts = posts;
      if (error) toast(error);
    }
    await loadState();
    if (requestId !== S.requestId) return;
    S.loading = false;
    renderMain(scroll);
    autosize();
  } catch (error) {
    if (requestId !== S.requestId) return;
    S.loading = false;
    $("#feed").innerHTML = `${empty("Couldn't open the workspace", "Check your connection and try again.", "warning_16_filled")}<div style="text-align:center"><button class="btn" id="retry">Try again</button></div>`;
    $("#composer").classList.add("hidden");
    toast(error.message);
  } finally { if (requestId === S.requestId) $("#feed").setAttribute("aria-busy", "false"); }
}
function draftKey() { return `spot.draft.${S.user}.${currentLoc()}`; }
function saveDraft() { store(draftKey(), $("#compose").value); }
function restoreDraft() { $("#compose").value = store(draftKey()) || ""; autosize(); hidePopup(); }
async function send() {
  const box = $("#compose"), text = box.value.trim();
  if (!text || S.busy || S.loading) return;
  const loc = currentLoc(), user = S.user, parentId = S.replyTo;
  S.busy = true; box.value = ""; saveDraft(); autosize(); hidePopup();
  S.pending = { text, typing: loc.startsWith("spot:") || /@spot\b/i.test(text), parent: parentId };
  renderMain("bottom");
  try {
    const { posts } = await api("/api/post", { user, loc, text, parent_id: parentId });
    S.posts = posts; S.errors = {}; S.replyTo = null;
  } catch (error) { box.value = box.value.trim() ? `${text}\n${box.value}` : text; saveDraft(); toast(error.message); }
  finally {
    S.pending = null; S.busy = false;
    renderMain(parentId ? "keep" : "bottom"); autosize();
    loadState().catch((error) => toast(error.message)); box.focus();
  }
}
async function runAction(messageId, data, loc) {
  if (S.busy) return;
  S.busy = true;
  document.querySelectorAll(".ac-pushButton").forEach((b) => { b.disabled = true; });
  try {
    const res = await api("/api/action", { user: S.user, loc, message_id: messageId, data });
    S.errors = res.error ? { [messageId]: res.error } : {};
    if (loc === "spot-app") {
      const { items } = await api(`/api/spot/${S.spotTab}?${q({ user: S.user })}`);
      S.items = items;
    } else S.posts = res.posts;
    await loadState(); renderMain("keep");
    document.querySelector(".card-error")?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    if (!res.error) toast(data.action === "approve" ? "Change approved. The new version is in History." : data.action === "reject" ? "Change rejected. Approved requirements are unchanged." : data.action === "submit_proposal" ? "Proposal submitted for review." : "Updated");
  } catch (error) { toast(error.message); }
  finally { S.busy = false; document.querySelectorAll(".ac-pushButton").forEach((b) => { b.disabled = false; }); autosize(); }
}
function renderChrome() {
  const { me, org, switcher, activity } = S.state;
  $("#sidebar").setAttribute("aria-label", NATIVE_APPS[S.view]?.title || "Conversations");
  $("#org").innerHTML = `<span class="org-logo"><span class="mastercard-mark" aria-hidden="true"></span></span><div><strong>${esc(org)}</strong><small>Autonomous Region Program</small></div>`;
  $("#user-name").textContent = me.display_name;
  $("#user-button").title = `${me.display_name} · ${me.team} · ${me.role}. Switch demo user.`;
  $("#me-avatar").innerHTML = avatar(me.name, "", true);
  $("#rail-spot").innerHTML = avatar("spot");
  const option = (u) => `<option value="${u}" ${u === S.user ? "selected" : ""}>${esc(person(u).display_name)} (${esc(person(u).team)} · ${esc(person(u).role)})</option>`;
  $("#user-select").innerHTML = `<optgroup label="Demo users">${switcher.slice(0, 4).map(option).join("")}</optgroup><optgroup label="Workspace members">${switcher.slice(4).map(option).join("")}</optgroup>`;
  $("#user-menu").innerHTML = `<div class="menu-title">Experience another perspective</div><div class="menu-subtitle">Switch roles to walk through the approval flow.</div>${switcher.map((u, i) => `${i === 4 ? '<div class="section">Workspace members</div>' : ""}<button class="user-option ${u === S.user ? "on" : ""}" data-user="${u}" aria-pressed="${u === S.user}">${avatar(u)}<div><strong>${esc(person(u).display_name)}</strong><small>${esc(person(u).team)}</small></div><span class="role-pill ${person(u).role.toLowerCase()}">${esc(person(u).role)}</span></button>`).join("")}`;
  const badge = $("#activity-badge"); badge.textContent = activity.length; badge.classList.toggle("hidden", !activity.length);
  document.querySelectorAll(".rail-item").forEach((b) => {
    b.classList.toggle("on", b.dataset.view === S.view);
    if (b.dataset.view === S.view) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
  });
  renderList();
}
function chatRow(c) {
  const p = c.preview, who = p ? (p.author === S.user ? "You" : p.author === "system" ? "" : person(p.author).display_name.split(" ")[0]) : "";
  const prev = p ? `${who ? who + ": " : ""}${p.text.replace(/\*\*/g, "")}` : "Start a conversation";
  return `<button class="chat-row ${c.location === currentLoc() ? "on" : ""} ${c.unread ? "unread" : ""}" data-loc="${c.location}" ${c.location === currentLoc() ? 'aria-current="page"' : ""}>${chatAvatar(c)}<span class="row-main"><span class="row-top"><span class="row-name">${esc(c.name)}</span>${p ? `<span class="row-time">${shortDate(p.ts)}</span>` : ""}${c.unread ? '<i class="unread-dot"></i>' : ""}</span><span class="row-prev" style="display:block">${esc(prev)}</span></span></button>`;
}
function renderList() {
  const { teams, chats, activity } = S.state;
  const dismiss = `<button class="icon-button sidebar-close" id="close-sidebar" aria-label="Close conversations">${icon("dismiss_20_regular")}</button>`;
  if (NATIVE_APPS[S.view]) {
    const app = NATIVE_APPS[S.view];
    $("#list").innerHTML = `<div class="list-head"><h1>${esc(app.title)}</h1>${dismiss}</div><div class="native-sidebar"><span class="native-app-icon">${icon(app.glyph)}</span><h2>${esc(app.description)}</h2><p>${esc(app.note)}</p></div><div class="section">Your workspace</div><div class="spot-links"><button class="spot-link" data-view="chat">${icon("chat_24_regular", "sm")}Conversations</button><button class="spot-link" data-view="teams">${icon("people_team_24_regular", "sm")}Teams & channels</button><button class="spot-link" data-spot-tab="pending">${avatar("spot", "sm")}Open Spot</button></div>`;
    return;
  }
  if (S.view === "activity") {
    $("#list").innerHTML = `<div class="list-head"><h1>Activity</h1>${dismiss}</div><div class="section">Awaiting your team <span>${activity.length}</span></div>` + (activity.length ? activity.map((a) => `<button class="act" data-review="${esc(a.proposal_id)}">${avatar("spot", "sm")}<div><strong>Approval requested</strong><small>${esc(a.summary)}</small><small>${esc(a.proposed_by)} · ${shortDate(a.ts)}</small></div></button>`).join("") : empty("All caught up", "Your team has no pending requests."));
    return;
  }
  if (S.view === "spot") {
    $("#list").innerHTML = `<div class="list-head"><h1>Your decisions, aligned.</h1>${dismiss}</div><div class="spot-nav"><div class="spot-nav-title">${avatar("spot", "sm")}Meet Spot</div><p>A shared source of truth for the requirements your teams depend on.</p><button class="btn" data-spot-tab="chat">Ask Spot a question ${icon("arrow_right_20_regular", "sm")}</button></div><div class="section">Workspace</div><div class="spot-links">${[["pending", "Pending approvals", "checkmark_circle_16_filled"], ["history", "Version history", "calendar_ltr_24_regular"], ["chat", "Chat with Spot", "chat_24_regular"]].map(([id, label, glyph]) => `<button class="spot-link ${S.spotTab === id ? "on" : ""}" data-spot-tab="${id}">${icon(glyph, "sm")}${label}</button>`).join("")}</div><div class="section">Back to the conversation</div>${chats.filter((c) => c.kind !== "bot").slice(0, 2).map(chatRow).join("")}`;
    return;
  }
  const unreadOnly = S.filter === "unread";
  const teamHtml = teams.map((t) => {
    const channels = t.channels.filter((c) => !unreadOnly || c.unread);
    if (!channels.length) return "";
    const collapsed = S.collapsed.has(t.id) && !unreadOnly;
    return `<button class="team-row ${collapsed ? "collapsed" : ""}" data-team="${t.id}" aria-expanded="${!collapsed}">${icon("chevron_down_12_regular", "xs")}${teamTile(t)}<span>${esc(t.name)}</span></button>${collapsed ? "" : channels.map((c) => `<button class="ch-row ${c.location === currentLoc() ? "on" : ""} ${c.unread ? "unread" : ""}" data-loc="${c.location}" title="${esc(c.name)}" ${c.location === currentLoc() ? 'aria-current="page"' : ""}><span class="channel-hash">#</span><span>${esc(c.name)}</span>${c.unread ? '<i class="unread-dot"></i>' : ""}</button>`).join("")}`;
  }).join("");
  const visibleChats = chats.filter((c) => !unreadOnly || c.unread);
  const chatHtml = visibleChats.map(chatRow).join("");
  const teamsBlock = teamHtml ? `<div class="section">Teams & channels <span>${teams.length}</span></div>${teamHtml}` : "";
  const favorites = visibleChats.filter((c) => c.kind === "bot").map(chatRow).join("");
  const conversations = visibleChats.filter((c) => c.kind !== "bot").map(chatRow).join("");
  const chatsBlock = `${favorites ? `<div class="section">Favorites</div>${favorites}` : ""}${conversations ? `<div class="section">Chats</div>${conversations}` : ""}`;
  const content = S.view === "chat" ? chatsBlock : teamsBlock;
  $("#list").innerHTML = `<div class="list-head"><h1>${S.view === "chat" ? "Chat" : "Teams"}</h1><button class="icon-button" id="find-conversation" title="Find a conversation" aria-label="Find a conversation">${icon("search_20_regular")}</button>${dismiss}</div><div class="list-filters"><button class="filter-chip ${!unreadOnly ? "on" : ""}" data-filter="all" aria-pressed="${!unreadOnly}">${S.view === "chat" ? "Chats" : "All"}</button><button class="filter-chip ${unreadOnly ? "on" : ""}" data-filter="unread" aria-pressed="${unreadOnly}">Unread</button></div>` + (content || empty("You're all caught up", "No unread conversations."));
}
function renderHead() {
  const mobile = `<button class="icon-button sidebar-toggle" id="toggle-sidebar" aria-label="Toggle conversations" aria-expanded="${$("#sidebar").classList.contains("mobile-open")}">${icon("panel_left_20_regular")}</button>`;
  let content = "";
  if (NATIVE_APPS[S.view]) {
    const app = NATIVE_APPS[S.view];
    content = `${icon(app.glyph)}<div class="head-copy"><div class="head-title">${esc(app.title)}</div><div class="head-sub">${esc(app.note)}</div></div>`;
  } else if (S.view === "spot") {
    content = `${avatar("spot", "lg")}<div class="head-copy"><div class="head-title">Spot <span class="role-pill">App</span></div><div class="head-sub">Keep every team on the same page</div></div><nav class="tabs" aria-label="Spot views">${[["pending", "Pending"], ["history", "History"], ["chat", "Chat"]].map(([id, label]) => `<button class="tab ${S.spotTab === id ? "on" : ""}" data-spot-tab="${id}" ${S.spotTab === id ? 'aria-current="page"' : ""}>${label}</button>`).join("")}</nav><div class="head-actions"><button class="icon-button" id="spot-info" aria-label="About Spot">${icon("info_16_regular")}</button></div>`;
  } else if (S.view === "activity") {
    content = `${icon("alert_24_regular")}<div class="head-copy"><div class="head-title">Your activity</div><div class="head-sub">The decisions that need your team's attention</div></div>`;
  } else {
    const loc = currentLoc(), channel = loc.startsWith("channel:");
    const team = S.state.teams.find((t) => t.channels.some((c) => c.location === loc));
    const ch = team?.channels.find((c) => c.location === loc);
    const chat = S.state.chats.find((c) => c.location === loc);
    const title = channel ? ch?.name : chat?.name;
    const members = chat?.members || [];
    const sub = channel ? team?.name : chat?.kind === "bot" ? "Requirements version control" : `${members.length} members · Shared conversation`;
    const tabs = `<nav class="tabs" aria-label="Conversation views">${[["conversation", channel ? "Posts" : "Chat"], ["files", channel ? "Files" : "Shared"]].map(([id, label]) => `<button class="tab ${S.contentTab === id ? "on" : ""}" data-content-tab="${id}" ${S.contentTab === id ? 'aria-current="page"' : ""}>${label}</button>`).join("")}</nav>`;
    content = `${channel && team ? teamTile(team) : chat ? chatAvatar(chat) : ""}<div class="head-copy"><div class="head-title">${esc(title || "Conversation")}</div>${channel || chat?.kind === "bot" ? `<div class="head-sub">${esc(sub || "")}</div>` : ""}</div>${tabs}<div class="head-actions">${members.length > 1 ? `<button class="member-stack" id="members" title="View ${members.length} members" aria-label="View ${members.length} members">${icon("people_20_regular")}<span class="member-count">${members.length}</span></button><span class="head-divider"></span>` : ""}<button class="icon-button" id="conversation-search" title="Search this conversation" aria-label="Search this conversation">${icon("search_20_regular")}</button><button class="icon-button" id="conversation-info" title="Conversation details" aria-label="Conversation details">${icon("info_16_regular")}</button></div>`;
  }
  $("#head").innerHTML = mobile + content;
}
function messageEl(m, loc, small, replyParent = null) {
  const el = document.createElement("div");
  if (m.kind === "system") { el.className = "system"; el.innerHTML = `${icon("people_20_regular", "sm")}<span>${esc(m.text)}</span>`; return el; }
  el.className = "msg";
  const quote = replyParent && m.author !== "spot" ? `<div class="reply-quote"><button class="quoted-author" data-jump="${esc(replyParent.id)}">${esc(person(replyParent.author).display_name)}</button><div>${esc((replyParent.text || "Shared a card").slice(0, 240))}${(replyParent.text || "").length > 240 ? "…" : ""}</div></div>` : "";
  el.innerHTML = `${avatar(m.author, small ? "sm" : "")}<div class="msg-body"><div class="msg-head"><button class="person-button" data-person="${esc(m.author)}" title="${esc(personTitle(m.author))}">${esc(person(m.author).display_name)}</button>${m.author === "spot" ? '<span class="tag">APP</span>' : ""}<time datetime="${esc(m.ts)}" title="${esc(fullDate(m.ts))}">${time(m.ts)}</time></div>${m.text ? `<div class="msg-text">${quote}${md(m.text)}</div>` : ""}</div>`;
  const body = el.querySelector(".msg-body");
  if (m.card) body.appendChild(cardHost(m.card, m.id, loc));
  if (S.errors[m.id]) body.insertAdjacentHTML("beforeend", errorBox(S.errors[m.id]));
  return el;
}
function renderFeed(scroll) {
  const feed = $("#feed"), keep = feed.scrollTop, loc = currentLoc();
  const inner = document.createElement("div"); inner.className = "feed-inner";
  if (loc.startsWith("spot:")) inner.innerHTML = `<div class="spot-welcome"><div class="spot-welcome-top">${avatar("spot", "lg")}<div><h2>A little clarity goes a long way.</h2><p>Ask a question. Capture a change. Keep a receipt.</p></div></div><div class="quick-prompts"><button class="quick-prompt" data-prompt="ask What is the cutover date for the UAE identity service?">What's the UAE identity cutover date?</button><button class="quick-prompt" data-prompt="pending">Review pending changes</button><button class="quick-prompt" data-prompt="help">What can Spot do?</button></div></div>`;
  const posts = S.posts.map((p) => ({ ...p, replies: [...p.replies] }));
  if (S.pending) {
    const mine = { id: "pending", author: S.user, text: S.pending.text, ts: new Date().toISOString(), replies: [] };
    const parent = posts.find((p) => p.id === S.pending.parent);
    if (parent) parent.replies.push(mine); else posts.push(mine);
  }
  if (!loc.startsWith("channel:")) {
    // Teams chats are one chronological stream; channel posts keep nested threads.
    const entries = posts.flatMap((post) => [
      { message: post, parent: null, rootId: post.id },
      ...post.replies.map((message) => ({ message, parent: post, rootId: post.id })),
    ]).sort((a, b) => new Date(a.message.ts) - new Date(b.message.ts));
    let day = "", previous = null;
    for (const { message, parent, rootId } of entries) {
      const messageDay = new Date(message.ts).toDateString();
      if (messageDay !== day) {
        const date = document.createElement("div"); date.className = "day";
        date.textContent = fullDate(message.ts); inner.appendChild(date); day = messageDay; previous = null;
      }
      if (message.kind === "system") {
        inner.appendChild(messageEl(message, loc)); previous = null; continue;
      }
      const continued = previous && previous.author === message.author && new Date(message.ts) - new Date(previous.ts) < 120000;
      const box = document.createElement("div");
      box.className = `post${message.author === S.user ? " own" : ""}${continued ? " continued" : ""}`;
      box.dataset.id = message.id;
      box.appendChild(messageEl(message, loc, false, parent));
      box.insertAdjacentHTML("beforeend", `<button class="reply-link" data-reply="${rootId}">${icon("arrow_reply_20_regular", "xs")}Reply</button>`);
      inner.appendChild(box); previous = message;
    }
    if (!entries.length) inner.insertAdjacentHTML("beforeend", empty("Start the conversation", "Share an update or mention @Spot to ask a question.", "chat_24_regular"));
    if (S.pending?.typing) inner.insertAdjacentHTML("beforeend", typingHtml(false));
    feed.replaceChildren(inner);
    feed.scrollTop = scroll === "keep" ? keep : scroll === "top" ? 0 : feed.scrollHeight;
    return;
  }
  let day = "";
  for (const post of posts) {
    const postDay = new Date(post.ts).toDateString();
    if (postDay !== day) { const date = document.createElement("div"); date.className = "day"; date.textContent = fullDate(post.ts); inner.appendChild(date); day = postDay; }
    if (post.kind === "system") { inner.appendChild(messageEl(post, loc)); continue; }
    const box = document.createElement("div"); box.className = `post ${post.author === S.user ? "own" : ""}`; box.dataset.id = post.id;
    box.appendChild(messageEl(post, loc));
    if (post.replies.length || (S.pending?.typing && S.pending.parent === post.id)) {
      const replies = document.createElement("div"); replies.className = "replies";
      replies.innerHTML = `<div class="thread-label">${icon("arrow_reply_20_regular", "xs")}${post.replies.length} ${post.replies.length === 1 ? "reply" : "replies"} in this thread</div>`;
      post.replies.forEach((r) => replies.appendChild(messageEl(r, loc, true)));
      if (S.pending?.typing && S.pending.parent === post.id) replies.insertAdjacentHTML("beforeend", typingHtml(true));
      box.appendChild(replies);
    }
    box.insertAdjacentHTML("beforeend", `<button class="reply-link" data-reply="${post.id}">${icon("arrow_reply_20_regular", "xs")}Reply${post.replies.length ? " to thread" : ""}</button>`);
    inner.appendChild(box);
  }
  if (!posts.length) inner.insertAdjacentHTML("beforeend", empty("Start the conversation", "Share an update or mention @Spot to ask a question.", "chat_24_regular"));
  if (S.pending?.typing && !S.pending.parent) inner.insertAdjacentHTML("beforeend", typingHtml(false));
  feed.replaceChildren(inner);
  feed.scrollTop = scroll === "keep" ? keep : scroll === "top" ? 0 : feed.scrollHeight;
}
function typingHtml(small) { return `<div class="msg">${avatar("spot", small ? "sm" : "")}<div class="msg-body"><div class="msg-head"><b>Spot</b><time>is thinking…</time></div><span class="typing" aria-label="Spot is replying"><i></i><i></i><i></i></span></div></div>`; }
function renderSpotItems(scroll) {
  const feed = $("#feed"), keep = feed.scrollTop, pending = S.spotTab === "pending";
  const inner = document.createElement("div"); inner.className = "feed-inner spot-items";
  const count = S.items.filter((i) => i.id !== "propose").length;
  inner.innerHTML = `<div class="spot-intro"><div class="eyebrow">A shared source of truth</div><h1>${pending ? "Good decisions start here." : "Every change has a story."}</h1><p>${pending ? "Review what’s changing. Align the teams that depend on it." : "The approved versions, the people behind them, and the decisions that made them binding."}</p>${pending ? `<div class="spot-summary"><div><strong>${count.toString().padStart(2, "0")}</strong><span>changes awaiting<br>approval</span></div><div><strong>${esc(S.state.me.team)}</strong><span>your team</span></div><div><span class="role-pill ${S.state.me.role.toLowerCase()}">${esc(S.state.me.role)}</span><span>your role</span></div></div>` : ""}</div>`;
  for (const item of S.items) {
    if (item.id === "propose") inner.insertAdjacentHTML("beforeend", '<div class="section-label">Start a proposal <small>Changes are reviewed before they become binding.</small></div>');
    inner.appendChild(cardHost(item.card, item.id, "spot-app"));
    if (S.errors[item.id]) inner.insertAdjacentHTML("beforeend", errorBox(S.errors[item.id]));
  }
  if (pending && !count) inner.insertAdjacentHTML("beforeend", empty("Everything is up to date", "No changes are waiting for approval."));
  if (!pending && !S.items.length) inner.insertAdjacentHTML("beforeend", empty("No document history yet", "Your team has no approved requirements to display."));
  feed.replaceChildren(inner); feed.scrollTop = scroll === "keep" ? keep : 0;
}
const SAMPLE_AGENDA = [
  { id: "gateway", date: "2026-10-14", start: "10:00", end: "10:30", title: "Gateway readiness check-in", organizer: "daniel.okafor", loc: "chat:gateway-readiness", summary: "Compare the gateway checklist with approved requirements and capture open questions before the next review." },
  { id: "runbook", date: "2026-10-15", start: "14:00", end: "14:45", title: "Cutover runbook walkthrough", organizer: "priya.raman", loc: "channel:arp-cutover", summary: "Walk through owners, dependencies, and rollback steps. Bring any requirement changes to Spot for review." },
  { id: "program", date: "2026-10-16", start: "11:00", end: "11:30", title: "Program weekly sync", organizer: "sofia.alvarez", loc: "channel:arp-general", summary: "Share this week’s decisions and align on the next steps across the Autonomous Region Program." },
];
function visibleAgenda() {
  const locations = new Set([...S.state.chats.map((c) => c.location), ...S.state.teams.flatMap((t) => t.channels.map((c) => c.location))]);
  return SAMPLE_AGENDA.filter((event) => locations.has(event.loc));
}
function meetingTime(event) { return `${time(`${event.date}T${event.start}`)} – ${time(`${event.date}T${event.end}`)}`; }
function nativeIntro(eyebrow, title, description) {
  return `<div class="files-intro"><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1><p>${esc(description)}</p></div>`;
}
function renderNativeApp() {
  const inner = document.createElement("div"); inner.className = "feed-inner native-view";
  const events = visibleAgenda();
  const days = [...new Set(events.map((event) => event.date))];
  if (!days.includes(S.agendaDay)) S.agendaDay = "all";
  inner.innerHTML = nativeIntro("October 12–16, 2026", "Your week at a glance", "A sample agenda for the demo, linked to your visible conversations.") + `<div class="native-filters" aria-label="Filter agenda by day">${[["all", "This week"], ...days.map((date) => [date, new Date(`${date}T12:00`).toLocaleDateString([], { weekday: "short", day: "numeric" })])].map(([date, label]) => `<button class="filter-chip ${S.agendaDay === date ? "on" : ""}" data-agenda-day="${date}" aria-pressed="${S.agendaDay === date}">${esc(label)}</button>`).join("")}</div><div class="agenda-list">${events.filter((event) => S.agendaDay === "all" || event.date === S.agendaDay).map((event) => `<button class="agenda-event" data-meeting="${event.id}"><span class="agenda-date"><small>${new Date(`${event.date}T12:00`).toLocaleDateString([], { weekday: "short" })}</small><strong>${event.date.slice(-2)}</strong></span><span class="agenda-copy"><strong>${esc(event.title)}</strong><span>${esc(meetingTime(event))}</span><small>Organized by ${esc(person(event.organizer).display_name)}</small></span>${icon("chevron_right_12_regular", "sm")}</button>`).join("")}</div>`;
  if (!events.length) inner.insertAdjacentHTML("beforeend", empty("No sample meetings", "Your visible conversations have no meetings in this demo agenda.", "calendar_ltr_24_regular"));
  $("#feed").replaceChildren(inner); $("#feed").scrollTop = 0;
}
function showMeeting(id) {
  const event = visibleAgenda().find((event) => event.id === id); if (!event) return;
  showDrawer("Meeting details", `<h2 class="document-title">${esc(event.title)}</h2><p class="drawer-description">${esc(event.summary)}</p><div class="profile-facts"><div><small>When</small><strong>${esc(fullDate(`${event.date}T12:00`))}</strong><small>${esc(meetingTime(event))} · local time</small></div><div><small>Organizer</small><strong>${esc(person(event.organizer).display_name)}</strong></div></div><p class="drawer-description">Sample meeting for the demo.</p><button class="btn primary" data-loc="${event.loc}">Open conversation ${icon("arrow_right_20_regular", "sm")}</button>`);
}
function renderFiles() {
  const inner = document.createElement("div"); inner.className = "feed-inner files-view";
  inner.innerHTML = `<div class="files-intro"><div class="eyebrow">Your team’s source of truth</div><h1>Approved requirements</h1><p>Current documents available to ${esc(S.state.me.team)}. Every version has a named approver.</p></div><div class="file-list"><div class="file-table-head"><span>Document</span><span>Owner</span><span>Status</span></div>${S.documents.map((d) => `<button class="file-row" data-doc="${esc(d.doc_id)}"><span class="file-name">${icon("contact_card_24_regular")}<span><strong>${esc(d.title)}</strong><small>Version ${d.version} · Updated ${shortDate(d.updated_at)}</small></span></span><span>${esc(d.team)}</span><span class="approved-pill">✓ Approved</span></button>`).join("")}</div>`;
  if (!S.documents.length) inner.insertAdjacentHTML("beforeend", empty("No files yet", "Your team has no approved documents."));
  $("#feed").replaceChildren(inner); $("#feed").scrollTop = 0;
}
function renderActivityMain() {
  const inner = document.createElement("div"); inner.className = "feed-inner spot-items";
  inner.innerHTML = `<div class="spot-intro"><div class="eyebrow">Stay in the loop</div><h1>${S.state.activity.length ? "Your team’s next decisions." : "You’re all caught up."}</h1><p>Approval requests routed to ${esc(S.state.me.team)} appear here.</p></div>${S.state.activity.map((a) => `<div class="spot-welcome"><div class="spot-welcome-top">${avatar("spot")}<div><h2>${esc(a.summary)}</h2><p>${esc(a.doc)} · Proposed by ${esc(a.proposed_by)}</p></div></div><div class="quick-prompts"><button class="btn primary" data-review="${esc(a.proposal_id)}">Review proposal ${icon("arrow_right_20_regular", "sm")}</button></div></div>`).join("")}`;
  if (!S.state.activity.length) inner.insertAdjacentHTML("beforeend", empty("Nothing needs your team’s attention", "Open Spot to browse pending changes across the program."));
  $("#feed").replaceChildren(inner); $("#feed").scrollTop = 0;
}
function renderMain(scroll = "bottom") {
  if (!S.state) return;
  renderHead();
  const spotCards = S.view === "spot" && S.spotTab !== "chat";
  const nativeApp = !!NATIVE_APPS[S.view];
  const files = !nativeApp && S.view !== "spot" && S.view !== "activity" && S.contentTab === "files";
  $("#composer").classList.toggle("hidden", nativeApp || spotCards || files || S.view === "activity");
  $("#feed").setAttribute("aria-label", nativeApp ? NATIVE_APPS[S.view].title : files ? "Approved files" : "Messages");
  $(".panel").setAttribute("aria-label", nativeApp ? NATIVE_APPS[S.view].title : "Conversation");
  $("#feed").classList.toggle("chat-feed", !nativeApp && !spotCards && !files && S.view !== "activity" && !currentLoc().startsWith("channel:"));
  if (nativeApp) { renderNativeApp(); return; }
  if (spotCards) { renderSpotItems(scroll); return; }
  if (files) { renderFiles(); return; }
  if (S.view === "activity") { renderActivityMain(); return; }
  renderFeed(scroll);
  $("#compose").placeholder = currentLoc().startsWith("spot:") ? "Ask Spot a question, or type / for commands…" : S.replyTo ? "Reply to this thread…" : currentLoc().startsWith("chat:") ? "Type a message…" : "Start a post…";
  const parent = S.posts.find((p) => p.id === S.replyTo), replying = $("#replying");
  replying.classList.toggle("hidden", !parent);
  if (parent) replying.innerHTML = `${icon("arrow_reply_20_regular", "sm")}<b>${esc(person(parent.author).display_name)}</b><span>${esc((parent.text || "").slice(0, 90))}</span><button data-cancel-reply aria-label="Cancel reply">${icon("dismiss_20_regular", "sm")}</button>`;
}
// Composer suggestions and keyboard navigation.
let popupItems = [], popupIndex = 0;
function showPopup(title, items) {
  popupItems = items; popupIndex = 0;
  $("#popup").innerHTML = `<div class="popup-head">${esc(title)}</div>${items.map((it, i) => `<button class="pop-item ${i === 0 ? "on" : ""}" role="option" aria-selected="${i === 0}" data-i="${i}">${it.html}</button>`).join("")}`;
  $("#popup").classList.remove("hidden");
}
function hidePopup() { $("#popup").classList.add("hidden"); popupItems = []; }
function updatePopup() {
  const v = $("#compose").value, mention = v.match(/(^|\s)@(\w*)$/);
  if (mention && "spot".startsWith(mention[2].toLowerCase())) {
    showPopup("Mention an app", [{ html: `${avatar("spot")}<div><b>Spot</b><small>Requirements version control</small></div>`, apply: () => v.replace(/@\w*$/, "@Spot ") }]); return;
  }
  const inSpot = currentLoc().startsWith("spot:");
  if ((!inSpot && /^\s*@Spot\s+$/i.test(v)) || (inSpot && v === "/")) {
    showPopup("Spot commands", COMMANDS.map(([cmd, desc]) => ({ html: `${avatar("spot", "sm")}<div><b>${cmd}</b><small>${desc}</small></div>`, apply: () => `${inSpot ? "" : "@Spot "}${cmd} ` }))); return;
  }
  hidePopup();
}
function choosePopup(i) {
  const it = popupItems[i]; if (!it) return;
  $("#compose").value = it.apply(); $("#compose").focus();
  $("#compose").setSelectionRange($("#compose").value.length, $("#compose").value.length);
  autosize(); saveDraft(); updatePopup();
}
function autosize() {
  const box = $("#compose"); box.style.height = "auto"; box.style.height = `${Math.min(box.scrollHeight || 33, 160)}px`;
  const ready = !!box.value.trim() && !S.busy && !S.loading;
  $("#send").classList.toggle("ready", ready); $("#send").disabled = !ready;
}
function toast(text) {
  const t = $("#toast"); t.textContent = text; t.classList.remove("hidden");
  clearTimeout(toast.timer); toast.timer = setTimeout(() => t.classList.add("hidden"), 4000);
}
function setUserMenu(open) {
  $("#user-menu").classList.toggle("hidden", !open); $("#user-button").setAttribute("aria-expanded", String(open));
  if (open) $("#user-menu .user-option.on")?.focus();
}
function closeSearch(restoreFocus = false) {
  if (restoreFocus && $("#search-results").contains(document.activeElement)) $("#search").focus();
  $("#search-results").classList.add("hidden"); $("#search").setAttribute("aria-expanded", "false");
}
function focusSearch() { $("#search").focus(); $("#search").select(); renderSearch(); }
function renderSearch() {
  if (!S.state) return;
  const term = $("#search").value.trim().toLowerCase(), results = $("#search-results");
  if (!term) { closeSearch(); return; }
  const matching = (value) => String(value || "").toLowerCase().includes(term);
  const chats = S.state.chats.filter((c) => matching(c.name));
  const channels = S.state.teams.flatMap((t) => t.channels.map((c) => ({ ...c, team: t.name }))).filter((c) => matching(c.name) || matching(c.team));
  const people = Object.values(S.state.people).filter((p) => matching(p.display_name) || matching(p.team));
  const docs = S.documents.filter((d) => matching(d.title) || matching(d.content));
  const inConversation = !NATIVE_APPS[S.view] && S.view !== "activity" && (S.view !== "spot" || S.spotTab === "chat") && (S.view === "spot" || S.contentTab === "conversation");
  const messages = (inConversation ? S.posts : []).flatMap((p) => [p, ...p.replies].map((m) => ({ ...m, parent: currentLoc().startsWith("channel:") ? p.id : m.id }))).filter((m) => matching(m.text));
  const group = (label, items) => items.length ? `<div class="section">${label}</div>${items.slice(0, 5).join("")}` : "";
  results.innerHTML = group("Conversations", chats.map((c) => `<button class="search-result" data-loc="${c.location}">${chatAvatar(c)}<div><strong>${esc(c.name)}</strong><small>${c.kind === "bot" ? "App" : `${c.members.length} members`}</small></div></button>`)) + group("Channels", channels.map((c) => `<button class="search-result" data-loc="${c.location}">${icon("people_team_24_regular")}<div><strong>${esc(c.name)}</strong><small>${esc(c.team)}</small></div></button>`)) + group("In this conversation", messages.map((m) => `<button class="search-result" data-jump="${esc(m.parent)}">${avatar(m.author, "sm")}<div><strong>${esc(person(m.author).display_name)}</strong><small>${esc(m.text.slice(0, 150))}</small></div></button>`)) + group("Approved files", docs.map((d) => `<button class="search-result" data-doc="${esc(d.doc_id)}">${icon("contact_card_24_regular")}<div><strong>${esc(d.title)}</strong><small>Version ${d.version} · ${esc(d.team)}</small></div></button>`)) + group("People", people.map((p) => `<button class="search-result" data-person="${esc(p.name)}">${avatar(p.name, "sm")}<div><strong>${esc(p.display_name)}</strong><small>${esc(p.title)}</small></div></button>`));
  if (!results.innerHTML) results.innerHTML = `<div class="search-empty">No results for “${esc($("#search").value.trim())}”. Try a person, channel, or requirement.</div>`;
  results.classList.remove("hidden"); $("#search").setAttribute("aria-expanded", "true");
}
function showDrawer(title, html) {
  closeSearch(); setUserMenu(false);
  S.drawerReturn = document.activeElement;
  $("#drawer").innerHTML = `<div class="drawer-heading"><span>${esc(title)}</span><button class="icon-button" id="close-drawer" aria-label="Close details">${icon("dismiss_20_regular")}</button></div>${html}`;
  $("#drawer").classList.remove("hidden"); $("#drawer-backdrop").classList.remove("hidden"); $("#drawer").focus();
}
function closeDrawer() {
  $("#drawer").classList.add("hidden"); $("#drawer-backdrop").classList.add("hidden");
  if (S.drawerReturn?.isConnected) S.drawerReturn.focus(); S.drawerReturn = null;
}
function showPerson(name) {
  if (name === "spot") { showSpotInfo(); return; }
  const p = person(name);
  showDrawer("Profile", `<div class="profile-top">${avatar(name, "xl")}<h2>${esc(p.display_name)}</h2><p>${esc(p.title)}</p><span class="role-pill ${p.role?.toLowerCase()}">${esc(p.role)}</span></div><div class="profile-facts"><div><small>Team</small><strong>${esc(p.team)}</strong></div><div><small>Organization</small><strong>${esc(S.state.org)}</strong></div></div><p class="drawer-description">Fictional profile in the Autonomous Region Program demo. Portrait is a sample image.</p>`);
}
function showSpotInfo() {
  showDrawer("About Spot", `<div class="profile-top">${avatar("spot", "xl")}<h2>Meet Spot.</h2><p>Your requirements, in sync.</p></div><p class="drawer-description">Spot gives project requirements the same clarity as version-controlled code. Capture decisions where they happen, get sign-off from the teams that depend on them, and keep an approved record.</p><div class="profile-facts">${COMMANDS.map(([cmd, desc]) => `<div><strong>@Spot ${cmd}</strong><small>${esc(desc)}</small></div>`).join("")}</div>`);
}
function showMembers() {
  const chat = S.state.chats.find((c) => c.location === currentLoc());
  if (!chat || chat.kind === "bot") { showSpotInfo(); return; }
  showDrawer(`Members · ${chat.members.length}`, `<p class="drawer-description">${esc(chat.name)}</p>${chat.members.map((u) => `<div class="member-row">${avatar(u)}<div><button class="person-button" data-person="${u}"><strong>${esc(person(u).display_name)}</strong></button><small>${esc(person(u).title)}</small></div></div>`).join("")}`);
}
function showConversationInfo() {
  if (currentLoc().startsWith("spot:")) { showSpotInfo(); return; }
  if (currentLoc().startsWith("chat:")) { showMembers(); return; }
  const t = S.state.teams.find((t) => t.channels.some((c) => c.location === S.loc));
  const ch = t?.channels.find((c) => c.location === S.loc);
  showDrawer("Channel details", `<div class="profile-top">${t ? teamTile(t) : ""}<h2>${esc(ch?.name)}</h2><p>${esc(t?.name)}</p></div><p class="drawer-description">A shared channel for the Autonomous Region Program. Mention @Spot in a post or reply to capture a decision, ask about requirements, or check approved history.</p><button class="btn primary" data-content-tab="files">Browse approved files</button>`);
}
function showDocument(id) {
  const d = S.documents.find((doc) => doc.doc_id === id); if (!d) return;
  showDrawer("Approved requirement", `<h2 class="document-title">${esc(d.title)}</h2><div class="document-meta"><span class="approved-pill">✓ Approved</span>Version ${d.version} · ${esc(d.team)}</div><div class="document-content">${esc(d.content)}</div><div class="profile-facts"><div><small>Author</small><strong>${esc(person(d.author).display_name)}</strong></div><div><small>Approved by</small><strong>${esc(person(d.approver).display_name)}</strong></div><div><small>Updated</small><strong>${esc(fullDate(d.updated_at))}</strong></div></div><button class="btn primary" data-doc-history="${esc(id)}">View version history ${icon("arrow_right_20_regular", "sm")}</button>`);
}
function canNavigate() { if (S.busy || S.loading) { toast("Finishing your request…"); return false; } return true; }
function setSidebarOpen(open, restoreFocus = false) {
  const visible = open && window.matchMedia("(max-width: 760px)").matches;
  $("#sidebar").classList.toggle("mobile-open", visible);
  $("#sidebar-backdrop").classList.toggle("hidden", !visible);
  $("#toggle-sidebar")?.setAttribute("aria-expanded", String(visible));
  if (visible) $("#list").querySelector('[aria-current="page"], button')?.focus();
  else if (restoreFocus) $("#toggle-sidebar")?.focus();
}
window.matchMedia("(max-width: 760px)").addEventListener("change", () => setSidebarOpen(false));
function alignConversationNavigation() {
  if (!["chat", "teams"].includes(S.view)) return;
  S.view = S.loc.startsWith("channel:") ? "teams" : "chat";
  const team = S.state.teams.find((t) => t.channels.some((c) => c.location === S.loc));
  if (team) S.collapsed.delete(team.id);
}
function prepareNavigation() {
  saveDraft(); hidePopup(); closeSearch(); setUserMenu(false); closeDrawer();
  setSidebarOpen(false);
  S.errors = {}; S.replyTo = null;
}
async function open(loc) {
  if (!canNavigate()) return;
  prepareNavigation();
  if (loc.startsWith("spot:")) { S.view = "spot"; S.spotTab = "chat"; }
  else { S.loc = loc; S.view = loc.startsWith("chat:") ? "chat" : "teams"; }
  alignConversationNavigation();
  S.contentTab = "conversation"; store("spot.loc", S.loc); restoreDraft();
  await loadMain();
}
async function switchUser(user) {
  if (!canNavigate() || !S.state.people[user] || user === "spot") return;
  prepareNavigation(); S.user = user; store("spot.user2", user); S.documents = []; S.posts = [];
  // Invalidate any earlier location request before fetching this identity's state.
  ++S.requestId; S.loading = true;
  try {
    await loadState();
    const visible = [...S.state.chats.map((c) => c.location), ...S.state.teams.flatMap((t) => t.channels.map((c) => c.location))];
    if (!visible.includes(S.loc)) S.loc = visible.find((loc) => !loc.startsWith("spot:")) || visible[0];
    alignConversationNavigation();
    store("spot.loc", S.loc); restoreDraft(); await loadMain();
    toast(`${S.state.me.display_name} · ${S.state.me.team} · ${S.state.me.role}`);
  } catch (error) { toast(error.message); S.loading = false; autosize(); }
}
// Click routing uses data attributes so all rendered controls stay functional.
document.addEventListener("click", async (e) => {
  if (!e.target.closest(".user-wrap")) setUserMenu(false);
  if (!e.target.closest(".search-wrap")) closeSearch();
  const t = e.target.closest("button,[data-cancel-reply]"); if (!t) return;
  if (t.dataset.loc) { open(t.dataset.loc); return; }
  if (t.dataset.user) { switchUser(t.dataset.user); return; }
  if (t.dataset.person) { showPerson(t.dataset.person); return; }
  if (t.dataset.agendaDay) { S.agendaDay = t.dataset.agendaDay; renderNativeApp(); return; }
  if (t.dataset.meeting) { showMeeting(t.dataset.meeting); return; }
  if (t.dataset.doc) { showDocument(t.dataset.doc); return; }
  if (t.dataset.review) {
    if (!canNavigate()) return;
    prepareNavigation(); S.view = "spot"; S.spotTab = "pending"; restoreDraft();
    await loadMain("top");
    const card = [...document.querySelectorAll(".card-host")].find((host) => host.spotCard?.messageId === t.dataset.review);
    if (card) {
      card.tabIndex = -1; card.focus({ preventScroll: true });
      card.scrollIntoView({ block: "center", behavior: "smooth" }); card.classList.add("flash");
      setTimeout(() => card.classList.remove("flash"), 2000);
    } else toast("This proposal is no longer waiting for review.");
    return;
  }
  if (t.dataset.jump) {
    closeSearch(); S.contentTab = "conversation";
    if (S.view === "spot") S.spotTab = "chat";
    renderMain("keep");
    const post = Array.from(document.querySelectorAll(".post")).find((p) => p.dataset.id === t.dataset.jump);
    post?.scrollIntoView({ behavior: "smooth", block: "center" }); post?.classList.add("flash");
    setTimeout(() => post?.classList.remove("flash"), 2000); return;
  }
  if (t.dataset.team) { S.collapsed.has(t.dataset.team) ? S.collapsed.delete(t.dataset.team) : S.collapsed.add(t.dataset.team); renderList(); return; }
  if (t.dataset.filter) { S.filter = t.dataset.filter; renderList(); return; }
  if (t.dataset.reply) { if (!canNavigate() || S.loading) return; S.replyTo = t.dataset.reply; renderMain("keep"); $("#compose").focus(); return; }
  if (t.hasAttribute("data-cancel-reply")) { S.replyTo = null; renderMain("keep"); return; }
  if (t.classList.contains("pop-item")) { choosePopup(+t.dataset.i); return; }
  if (t.dataset.prompt) { $("#compose").value = t.dataset.prompt; autosize(); saveDraft(); $("#compose").focus(); return; }
  if (t.dataset.docHistory) {
    if (!canNavigate()) return;
    prepareNavigation(); S.view = "spot"; S.spotTab = "history";
    try {
      await api("/api/action", { user: S.user, loc: "spot-app", message_id: "history-picker", data: { action: "pick_history", doc_id: t.dataset.docHistory } });
      restoreDraft(); await loadMain("top");
    } catch (error) { toast(error.message); } return;
  }
  if (t.dataset.spotTab) {
    if (!canNavigate()) return;
    prepareNavigation(); S.view = "spot"; S.spotTab = t.dataset.spotTab; restoreDraft(); loadMain("top"); return;
  }
  if (t.dataset.contentTab) {
    if (!canNavigate()) return;
    closeDrawer(); saveDraft(); hidePopup(); S.contentTab = t.dataset.contentTab; renderMain(S.contentTab === "files" ? "top" : "bottom"); return;
  }
  if (t.dataset.view) {
    if (!canNavigate() || !S.state) return;
    prepareNavigation(); S.view = t.dataset.view; S.contentTab = "conversation";
    if (S.view === "chat" && !S.loc.startsWith("chat:")) S.loc = S.state.chats.find((c) => c.kind !== "bot")?.location || S.state.chats[0].location;
    if (S.view === "teams" && !S.loc.startsWith("channel:")) S.loc = S.state.teams[0]?.channels[0]?.location || S.loc;
    alignConversationNavigation();
    store("spot.loc", S.loc); restoreDraft(); loadMain(S.view === "spot" || NATIVE_APPS[S.view] ? "top" : "bottom"); return;
  }
  switch (t.id) {
    case "theme-toggle": applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark", true); break;
    case "reset": {
      if (!canNavigate()) return;
      hidePopup(); closeSearch(); setUserMenu(false); closeDrawer(); setSidebarOpen(false);
      $("#reset-dialog").showModal(); break;
    }
    case "cancel-reset": $("#reset-dialog").close(); break;
    case "confirm-reset": {
      if (!canNavigate()) return;
      const dialog = $("#reset-dialog"), cancel = $("#cancel-reset");
      S.busy = true; t.disabled = true; cancel.disabled = true; t.textContent = "Resetting…";
      dialog.setAttribute("aria-busy", "true");
      try {
        await api("/api/reset", {}); S.errors = {}; S.replyTo = null; await loadMain();
        dialog.close(); toast("Demo reset. Ready for another walkthrough.");
      }
      catch (error) { toast(error.message); }
      finally {
        S.busy = false; t.disabled = false; cancel.disabled = false; t.textContent = "Reset demo";
        dialog.removeAttribute("aria-busy"); autosize();
      } break;
    }
    case "retry": S.state ? loadMain() : init(); break;
    case "user-button": setUserMenu($("#user-menu").classList.contains("hidden")); break;
    case "toggle-sidebar": setSidebarOpen(!$("#sidebar").classList.contains("mobile-open")); break;
    case "sidebar-backdrop": case "close-sidebar": setSidebarOpen(false, true); break;
    case "members": showMembers(); break;
    case "conversation-info": showConversationInfo(); break;
    case "spot-info": showSpotInfo(); break;
    case "close-drawer": closeDrawer(); break;
    case "find-conversation": case "conversation-search": focusSearch(); break;
    case "send": send(); break;
    case "mention": case "composer-spot": {
      const box = $("#compose"); box.value += `${box.value && !/\s$/.test(box.value) ? " " : ""}@Spot `;
      box.focus(); autosize(); saveDraft(); updatePopup(); break;
    }
    case "format": {
      const box = $("#compose"), start = box.selectionStart, end = box.selectionEnd;
      box.setRangeText(`**${box.value.slice(start, end) || "bold text"}**`, start, end, "select"); box.focus(); autosize(); saveDraft(); break;
    }
    case "emoji": {
      const value = $("#compose").value;
      showPopup("Add a little expression", ["👍", "✅", "🎉", "👋", "💡", "🙌"].map((emoji) => ({ html: `<span style="font-size:20px">${emoji}</span>`, apply: () => `${value}${value && !/\s$/.test(value) ? " " : ""}${emoji} ` }))); break;
    }
  }
});
$("#drawer-backdrop").addEventListener("click", closeDrawer);
$("#reset-dialog").addEventListener("cancel", (e) => { if (S.busy) e.preventDefault(); });
$("#user-select").addEventListener("change", (e) => switchUser(e.target.value));
$("#search").addEventListener("input", renderSearch);
$("#search").addEventListener("focus", renderSearch);
$("#search").addEventListener("keydown", (e) => {
  if (!["ArrowDown", "ArrowUp", "Enter"].includes(e.key)) return;
  const results = [...$("#search-results").querySelectorAll(".search-result")];
  if (!results.length || $("#search-results").classList.contains("hidden")) return;
  e.preventDefault();
  if (e.key === "Enter") results[0].click();
  else (e.key === "ArrowUp" ? results.at(-1) : results[0]).focus();
});
$("#search-results").addEventListener("keydown", (e) => {
  if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) return;
  const results = [...$("#search-results").querySelectorAll(".search-result")];
  if (!results.length) return;
  const index = results.indexOf(document.activeElement);
  const next = e.key === "Home" ? 0 : e.key === "End" ? results.length - 1
    : (index + (e.key === "ArrowUp" ? -1 : 1) + results.length) % results.length;
  e.preventDefault(); results[next].focus(); results[next].scrollIntoView({ block: "nearest" });
});
$("#compose").addEventListener("input", () => { autosize(); saveDraft(); updatePopup(); });
$("#compose").addEventListener("keydown", (e) => {
  const openPopup = !$("#popup").classList.contains("hidden") && popupItems.length;
  if (openPopup && ["ArrowDown", "ArrowUp"].includes(e.key)) {
    e.preventDefault(); popupIndex = (popupIndex + (e.key === "ArrowDown" ? 1 : popupItems.length - 1)) % popupItems.length;
    document.querySelectorAll(".pop-item").forEach((el, i) => { el.classList.toggle("on", i === popupIndex); el.setAttribute("aria-selected", String(i === popupIndex)); }); return;
  }
  if (openPopup && (e.key === "Tab" || (e.key === "Enter" && !e.shiftKey))) { e.preventDefault(); choosePopup(popupIndex); return; }
  if (e.key === "Escape") { hidePopup(); S.replyTo = null; renderMain("keep"); return; }
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); focusSearch(); }
  if (e.key === "Escape") {
    hidePopup(); closeSearch(true); setUserMenu(false); closeDrawer();
    if ($("#sidebar").classList.contains("mobile-open")) setSidebarOpen(false, true);
  }
  if (e.key === "Tab" && !$("#drawer").classList.contains("hidden")) {
    const elements = [...$("#drawer").querySelectorAll("button,a,input,select,textarea,[tabindex='0']")];
    const first = elements[0], last = elements[elements.length - 1];
    if (e.shiftKey && (document.activeElement === first || document.activeElement === $("#drawer"))) { e.preventDefault(); last?.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
  }
});
window.addEventListener("beforeunload", saveDraft);
async function init() {
  try {
    await loadState();
    const visible = [...S.state.chats.map((c) => c.location), ...S.state.teams.flatMap((t) => t.channels.map((c) => c.location))];
    if (!visible.includes(S.loc)) S.loc = visible.find((loc) => !loc.startsWith("spot:")) || visible[0];
    alignConversationNavigation();
    restoreDraft(); await loadMain();
  } catch (error) {
    $("#feed").setAttribute("aria-busy", "false");
    $("#feed").innerHTML = `${empty("Couldn't connect to your workspace", "Make sure the demo server is running.", "warning_16_filled")}<div style="text-align:center"><button class="btn" id="retry">Try again</button></div>`;
    $("#composer").classList.add("hidden"); toast(error.message);
  }
}
applyTheme(document.documentElement.dataset.theme);
init();
