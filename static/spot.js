// Spot front end: renders a Teams-style workspace and talks to app.py.
"use strict";

const $ = (sel) => document.querySelector(sel);
const icon = (name, cls = "") => `<span class="ic ${cls}" style="--i:url(/static/icons/${name}.svg)"></span>`;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function store(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, value);
  } catch { return null; }
}

const COMMANDS = [
  ["add", "Reply to a message to turn its decision into a proposal"],
  ["propose", "Propose a change to one of your team's docs"],
  ["ask", "Ask about approved docs, with citations"],
  ["history", "Approved versions, and what isn't binding"],
  ["pending", "Changes waiting for approval"],
  ["help", "What Spot can do"],
];

const S = {
  user: store("spot.user2") || window.DEMO_DEFAULT_USER || "marcus.chen",
  view: "teams",                  // activity | chat | teams | spot
  loc: store("spot.loc") || "chat:cutover-sync",
  spotTab: "pending",             // pending | history | chat
  state: null,
  posts: [],
  items: [],
  errors: {},
  replyTo: null,
  pending: null,
  collapsed: new Set(),
  spotImg: false,
};

// Spot's profile picture: static/spot-avatar.png if present, else a pin icon.
const spotImage = new Image();
spotImage.onload = () => { S.spotImg = true; if (S.state) { renderChrome(); renderMain(); } };
spotImage.src = "/static/spot-avatar.png";

// ---------------------------------------------------------------- formatting

function md(text) {
  return esc(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|\s)(@(Spot|Payments|Ops Automation))\b/gi, '$1<span class="mention">$2</span>');
}

function person(name) {
  return S.state?.people[name] || { name, display_name: name, title: "", team: "", avatar_color: "#616161" };
}

function initials(name) {
  return person(name).display_name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

function avatar(name, size = "") {
  if (name === "spot") {
    return `<div class="av bot ${size}" title="Spot">${S.spotImg ? '<img src="/static/spot-avatar.png" alt="">' : icon("location_24_filled")}</div>`;
  }
  const p = person(name);
  return `<div class="av ${size}" style="background:${p.avatar_color}" title="${esc(p.display_name)}">${initials(name)}</div>`;
}

function personTitle(name) {
  const p = person(name);
  return [p.title, p.team].filter(Boolean).join(", ");
}

function teamTile(team) {
  const letters = team.name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2);
  return `<div class="av tile" style="background:${team.avatar_color}">${letters}</div>`;
}

function chatAvatar(chat) {
  if (chat.kind === "bot") return avatar("spot");
  const others = chat.members.filter((m) => m !== S.user);
  if (others.length === 1) return avatar(others[0]);
  return `<div class="group-av">${avatar(others[0])}${avatar(others[1])}</div>`;
}

function time(ts) {
  const d = new Date(ts);
  const sameDay = new Date().toDateString() === d.toDateString();
  const t = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  return sameDay ? t : `${d.toLocaleDateString([], { month: "short", day: "numeric" })} ${t}`;
}

// ---------------------------------------------------------------- Adaptive Cards

const fg = (d, s = d) => ({ default: d, subtle: s });
const COLORS = {
  default: fg("#242424", "#616161"), dark: fg("#242424", "#616161"), light: fg("#FFFFFF", "#F5F5F5"),
  accent: fg("#5B5FC7", "#4F52B2"), good: fg("#0E700E", "#0E700E"), warning: fg("#BC4B09", "#BC4B09"),
  attention: fg("#C4314B", "#C4314B"),
};
const FONT = "'Segoe UI', 'Segoe UI Web (West European)', -apple-system, BlinkMacSystemFont, Roboto, 'Helvetica Neue', sans-serif";
const HOST = new AdaptiveCards.HostConfig({
  fontFamily: FONT,
  supportsInteractivity: true,
  spacing: { small: 4, default: 8, medium: 12, large: 16, extraLarge: 24, padding: 16 },
  separator: { lineThickness: 1, lineColor: "#E0E0E0" },
  fontSizes: { small: 12, default: 14, medium: 14, large: 18, extraLarge: 24 },
  fontWeights: { lighter: 300, default: 400, bolder: 600 },
  containerStyles: {
    default: { backgroundColor: "#FFFFFF", foregroundColors: COLORS },
    emphasis: { backgroundColor: "#F5F5F5", foregroundColors: COLORS },
  },
  actions: { maxActions: 5, spacing: "default", buttonSpacing: 8, actionsOrientation: "horizontal", actionAlignment: "left",
    showCard: { actionMode: "inline", inlineTopMargin: 12, style: "emphasis" } },
  factSet: { title: { weight: "bolder", size: "default", color: "default", wrap: true, maxWidth: 120 },
    value: { size: "default", color: "default", wrap: true }, spacing: 12 },
  inputs: { label: { inputSpacing: "small", requiredInputs: { weight: "bolder", suffix: " *", suffixColor: "attention" },
    optionalInputs: { weight: "bolder" } }, errorMessage: { size: "small", color: "attention" } },
});

AdaptiveCards.AdaptiveCard.onProcessMarkdown = (text, result) => {
  result.outputHtml = md(text);
  result.didProcess = true;
};

function renderCard(json, messageId, loc) {
  const card = new AdaptiveCards.AdaptiveCard();
  card.hostConfig = HOST;
  card.onExecuteAction = (action) => {
    if (action instanceof AdaptiveCards.SubmitAction) runAction(messageId, action.data, loc);
  };
  card.parse(json);
  return card.render();
}

function cardHost(json, messageId, loc) {
  const host = document.createElement("div");
  host.className = "card-host";
  try { host.appendChild(renderCard(json, messageId, loc)); }
  catch (e) { host.textContent = `Card failed to render: ${e}`; }
  return host;
}

function errorBox(text) {
  return `<div class="card-error">${icon("warning_16_filled")}<div>${esc(text)}</div></div>`;
}

// ---------------------------------------------------------------- API

async function api(path, body) {
  const res = await fetch(path, body === undefined ? undefined : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  return res.json();
}

const q = (params) => new URLSearchParams(params).toString();

async function loadState() {
  S.state = await api(`/api/state?${q({ user: S.user })}`);
  renderChrome();
}

async function loadMain(scroll = "bottom") {
  if (S.view === "spot" && S.spotTab !== "chat") {
    const { items } = await api(`/api/spot/${S.spotTab}?${q({ user: S.user })}`);
    S.items = items;
  } else {
    const { posts, error } = await api(`/api/location?${q({ user: S.user, loc: currentLoc() })}`);
    S.posts = posts;
    if (error) toast(error);
  }
  renderMain(scroll);
  await loadState();
}

function currentLoc() {
  return S.view === "spot" ? `spot:${S.user}` : S.loc;
}

async function send() {
  const box = $("#compose");
  const text = box.value.trim();
  if (!text) return;
  box.value = "";
  autosize();
  hidePopup();
  const loc = currentLoc();
  const parentId = S.replyTo;
  const toSpot = loc.startsWith("spot:") || /@spot\b/i.test(text);
  S.pending = { text, typing: toSpot, parent: S.replyTo };
  renderMain("bottom");
  if (toSpot) await sleep(600);
  const { posts } = await api("/api/post", { user: S.user, loc, text, parent_id: S.replyTo });
  S.pending = null;
  S.replyTo = null;
  S.posts = posts;
  S.errors = {};
  renderMain(parentId ? "keep" : "bottom");
  loadState();
}

async function runAction(messageId, data, loc) {
  const res = await api("/api/action", { user: S.user, loc, message_id: messageId, data });
  S.errors = res.error ? { [messageId]: res.error } : {};
  if (loc === "spot-app") {
    const { items } = await api(`/api/spot/${S.spotTab}?${q({ user: S.user })}`);
    S.items = items;
  } else {
    S.posts = res.posts;
  }
  renderMain("keep");
  document.querySelector(".card-error")?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  if (!res.error) toast(data.action === "approve" ? "Approved" : data.action === "reject" ? "Rejected" :
    data.action === "submit_proposal" ? "Proposal submitted" : "Updated");
  loadState();
}

// ---------------------------------------------------------------- chrome

function renderChrome() {
  const { me, org, switcher, activity } = S.state;
  $("#org").innerHTML = `${esc(org)} <small>· Autonomous Region Program</small>`;
  $("#me-avatar").innerHTML = `<div title="${esc(me.display_name)}, ${esc(personTitle(me.name))}">${avatar(me.name)}</div>`;
  $("#rail-spot").innerHTML = avatar("spot");

  const sel = $("#user-select");
  const option = (u) => `<option value="${u}" ${u === S.user ? "selected" : ""}>${esc(person(u).display_name)} (${esc(person(u).team)} · ${esc(person(u).role)})</option>`;
  sel.innerHTML = `<optgroup label="Demo users">${switcher.slice(0, 4).map(option).join("")}</optgroup>
    <optgroup label="Others">${switcher.slice(4).map(option).join("")}</optgroup>`;

  const badge = $("#activity-badge");
  badge.textContent = activity.length;
  badge.classList.toggle("hidden", !activity.length);
  document.querySelectorAll(".rail-item").forEach((b) => b.classList.toggle("on", b.dataset.view === S.view));

  if (S.view === "activity") renderActivity(activity);
  else renderList();
}

function renderList() {
  const { teams, chats } = S.state;
  const loc = currentLoc();
  const teamHtml = teams.map((t) => {
    const collapsed = S.collapsed.has(t.id);
    return `
      <button class="team-row ${collapsed ? "collapsed" : ""}" data-team="${t.id}">
        ${icon("chevron_down_12_regular", "xs")}${teamTile(t)}<span>${esc(t.name)}</span>
      </button>
      ${collapsed ? "" : t.channels.map((c) => `
        <button class="ch-row ${c.location === loc ? "on" : ""} ${c.unread && c.location !== loc ? "unread" : ""}" data-loc="${c.location}">${esc(c.name)}</button>`).join("")}`;
  }).join("");
  const chatHtml = chats.map((c) => {
    const p = c.preview;
    const who = p ? (p.author === S.user ? "You" : p.author === "system" ? "" : person(p.author).display_name.split(" ")[0]) : "";
    const prev = p ? `${who ? who + ": " : ""}${p.text.replace(/\*\*/g, "")}` : "";
    return `
      <button class="chat-row ${c.location === loc ? "on" : ""} ${c.unread && c.location !== loc ? "unread" : ""}" data-loc="${c.location}">
        ${chatAvatar(c)}
        <div class="row-main">
          <div class="row-top"><span class="row-name">${esc(c.name)}</span>${p ? `<span class="row-time">${time(p.ts)}</span>` : ""}</div>
          <div class="row-prev">${esc(prev)}</div>
        </div>
      </button>`;
  }).join("");
  const teamsBlock = `<div class="section">Teams</div>${teamHtml}`;
  const chatsBlock = `<div class="section">Chats</div>${chatHtml}`;
  const title = S.view === "chat" ? "Chat" : S.view === "spot" ? "Spot" : "Teams";
  $("#list").innerHTML = `<div class="list-head"><h1>${title}</h1></div>` +
    (S.view === "chat" ? chatsBlock + teamsBlock : teamsBlock + chatsBlock);
}

function renderActivity(activity) {
  $("#list").innerHTML = `<div class="list-head"><h1>Activity</h1></div>` + (activity.length ? activity.map((a) => `
    <button class="act" data-loc="${a.location}">
      ${avatar("spot")}
      <div><strong>Spot</strong> needs <strong>${esc(S.state.me.team)}</strong> to approve a change
        <small>${esc(a.summary)}</small><small>${esc(a.doc)} · proposed by ${esc(a.proposed_by)} · ${time(a.ts)}</small></div>
    </button>`).join("") : `<div class="empty">You're all caught up.</div>`);
}

// ---------------------------------------------------------------- main pane

function renderHead() {
  const loc = currentLoc();
  if (S.view === "spot") {
    const tab = (id, label) => `<button class="tab ${S.spotTab === id ? "on" : ""}" data-spot-tab="${id}">${label}</button>`;
    $("#head").innerHTML = `${avatar("spot", "lg")}<div><div class="head-title">Spot</div>
      <div class="head-sub">Requirements version control</div></div>
      <nav class="tabs">${tab("pending", "Pending")}${tab("history", "History")}${tab("chat", "Chat")}</nav>`;
    return;
  }
  const [kind, id] = loc.split(":");
  if (kind === "channel") {
    const team = S.state.teams.find((t) => t.channels.some((c) => c.id === id));
    const ch = team?.channels.find((c) => c.id === id);
    $("#head").innerHTML = team ? `${teamTile(team)}<div><div class="head-title">${esc(ch.name)}</div>
      <div class="head-sub">${esc(team.name)}</div></div>
      <nav class="tabs"><span class="tab on">Posts</span><span class="tab">Files</span></nav>` : "";
  } else {
    const chat = S.state.chats.find((c) => c.location === loc);
    $("#head").innerHTML = chat ? `${chatAvatar(chat)}<div><div class="head-title">${esc(chat.name)}</div>
      <div class="head-sub">${chat.kind === "bot" ? "App" : chat.members.map((m) => esc(person(m).display_name)).join(", ")}</div></div>` : "";
  }
}

function messageEl(m, loc, small) {
  if (m.kind === "system") {
    const d = document.createElement("div");
    d.className = "system";
    d.textContent = m.text;
    return d;
  }
  const p = person(m.author);
  const el = document.createElement("div");
  el.className = "msg";
  el.innerHTML = `${avatar(m.author, small ? "sm" : "")}
    <div class="msg-body">
      <div class="msg-head"><b title="${esc(personTitle(m.author))}">${esc(p.display_name)}</b>
        ${m.author === "spot" ? '<span class="tag">App</span>' : ""}<time>${time(m.ts)}</time></div>
      ${m.text ? `<div class="msg-text">${md(m.text)}</div>` : ""}
    </div>`;
  const body = el.querySelector(".msg-body");
  if (m.card) body.appendChild(cardHost(m.card, m.id, loc));
  if (S.errors[m.id]) body.insertAdjacentHTML("beforeend", errorBox(S.errors[m.id]));
  return el;
}

function renderFeed(scroll) {
  const feed = $("#feed");
  const keep = feed.scrollTop;
  const loc = currentLoc();
  const inner = document.createElement("div");
  inner.className = "feed-inner";
  const posts = S.posts.map((p) => ({ ...p, replies: [...p.replies] }));
  if (S.pending) {
    const mine = { id: "pending", author: S.user, text: S.pending.text, ts: new Date().toISOString(), replies: [] };
    const parent = posts.find((p) => p.id === S.pending.parent);
    if (parent) parent.replies.push(mine); else posts.push(mine);
  }
  for (const post of posts) {
    if (post.kind === "system") { inner.appendChild(messageEl(post, loc)); continue; }
    const box = document.createElement("div");
    box.className = "post";
    box.dataset.id = post.id;
    box.appendChild(messageEl(post, loc));
    if (post.replies.length || (S.pending?.typing && S.pending.parent === post.id)) {
      const replies = document.createElement("div");
      replies.className = "replies";
      post.replies.forEach((r) => replies.appendChild(messageEl(r, loc, true)));
      if (S.pending?.typing && S.pending.parent === post.id) replies.insertAdjacentHTML("beforeend", typingHtml(true));
      box.appendChild(replies);
    }
    box.insertAdjacentHTML("beforeend", `<button class="reply-link" data-reply="${post.id}">${icon("arrow_reply_20_regular", "sm")}Reply</button>`);
    inner.appendChild(box);
  }
  if (S.pending?.typing && !S.pending.parent) inner.insertAdjacentHTML("beforeend", `<div class="post">${typingHtml(false)}</div>`);
  feed.replaceChildren(inner);
  feed.scrollTop = scroll === "keep" ? keep : feed.scrollHeight;
}

function typingHtml(small) {
  return `<div class="msg">${avatar("spot", small ? "sm" : "")}<div class="msg-body"><div class="msg-head"><b>Spot</b><time>is typing…</time></div>
    <span class="typing"><i></i><i></i><i></i></span></div></div>`;
}

function renderSpotItems() {
  const feed = $("#feed");
  const keep = feed.scrollTop;
  const inner = document.createElement("div");
  inner.className = "feed-inner spot-items";
  for (const item of S.items) {
    inner.appendChild(cardHost(item.card, item.id, "spot-app"));
    if (S.errors[item.id]) inner.insertAdjacentHTML("beforeend", errorBox(S.errors[item.id]));
  }
  if (!S.items.length) inner.innerHTML = `<div class="empty">Nothing here yet.</div>`;
  feed.replaceChildren(inner);
  feed.scrollTop = keep;
}

function renderMain(scroll = "bottom") {
  if (!S.state) return;
  renderHead();
  const spotCards = S.view === "spot" && S.spotTab !== "chat";
  $("#composer").classList.toggle("hidden", spotCards);
  if (spotCards) { renderSpotItems(); return; }
  renderFeed(scroll);
  const loc = currentLoc();
  $("#compose").placeholder = loc.startsWith("spot:") ? "Message Spot (try: help)"
    : S.replyTo ? "Reply" : loc.startsWith("chat:") ? "Type a message. Mention @Spot to use Spot." : "Start a post. Mention @Spot to use Spot.";
  const replying = $("#replying");
  const parent = S.posts.find((p) => p.id === S.replyTo);
  replying.classList.toggle("hidden", !parent);
  if (parent) replying.innerHTML = `${icon("arrow_reply_20_regular", "sm")} Replying to <b>${esc(person(parent.author).display_name)}</b>
    <span>${esc((parent.text || "").slice(0, 60))}${(parent.text || "").length > 60 ? "…" : ""}</span><button data-cancel-reply>${icon("dismiss_20_regular", "sm")}</button>`;
}

// ---------------------------------------------------------------- composer: @mention and command menu

let popupItems = [];
let popupIndex = 0;

function showPopup(title, items) {
  popupItems = items;
  popupIndex = 0;
  $("#popup").innerHTML = `<div class="popup-head">${title}</div>` + items.map((it, i) => `
    <button class="pop-item ${i === 0 ? "on" : ""}" data-i="${i}">${it.html}</button>`).join("");
  $("#popup").classList.remove("hidden");
}

function hidePopup() { $("#popup").classList.add("hidden"); popupItems = []; }

function updatePopup() {
  const v = $("#compose").value;
  const mention = v.match(/(^|\s)@(\w*)$/);
  if (mention && "spot".startsWith(mention[2].toLowerCase())) {
    showPopup("Suggestions", [{
      html: `${avatar("spot")}<div><b>Spot</b><small>App · requirements version control</small></div>`,
      apply: () => v.replace(/@\w*$/, "@Spot "),
    }]);
    return;
  }
  const inSpot = currentLoc().startsWith("spot:");
  if ((!inSpot && /^\s*@Spot\s+$/i.test(v)) || (inSpot && v === "/")) {
    showPopup("Spot commands", COMMANDS.map(([cmd, desc]) => ({
      html: `${avatar("spot")}<div><b>${cmd}</b><small>${desc}</small></div>`,
      apply: () => `${inSpot ? "" : "@Spot "}${cmd} `,
    })));
    return;
  }
  hidePopup();
}

function choosePopup(i) {
  const it = popupItems[i];
  if (!it) return;
  const box = $("#compose");
  box.value = it.apply();
  box.focus();
  box.setSelectionRange(box.value.length, box.value.length);
  autosize();
  updatePopup();
}

function autosize() {
  const box = $("#compose");
  box.style.height = "auto";
  box.style.height = `${Math.min(box.scrollHeight, 160)}px`;
  $("#send").classList.toggle("ready", !!box.value.trim());
}

// ---------------------------------------------------------------- events

function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.classList.remove("hidden");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.add("hidden"), 2200);
}

function open(loc) {
  if (loc.startsWith("spot:")) { S.view = "spot"; S.spotTab = "chat"; }
  else { S.loc = loc; if (S.view === "spot" || S.view === "activity") S.view = loc.startsWith("chat:") ? "chat" : "teams"; }
  S.errors = {};
  S.replyTo = null;
  store("spot.loc", S.loc);
  loadMain();
}

document.addEventListener("click", async (e) => {
  const t = e.target.closest("[data-loc],[data-team],[data-view],[data-spot-tab],[data-reply],[data-cancel-reply],.pop-item,#reset");
  if (!t) return;
  if (t.classList.contains("pop-item")) { choosePopup(+t.dataset.i); return; }
  if (t.dataset.loc) { open(t.dataset.loc); return; }
  if (t.dataset.team) {
    S.collapsed.has(t.dataset.team) ? S.collapsed.delete(t.dataset.team) : S.collapsed.add(t.dataset.team);
    renderList();
    return;
  }
  if (t.dataset.reply) {
    S.replyTo = t.dataset.reply;
    renderMain("keep");
    $("#compose").focus();
    return;
  }
  if (t.hasAttribute("data-cancel-reply")) { S.replyTo = null; renderMain("keep"); return; }
  if (t.dataset.spotTab) { S.spotTab = t.dataset.spotTab; S.errors = {}; loadMain(); return; }
  if (t.id === "reset") {
    await api("/api/reset", {});
    S.errors = {};
    S.replyTo = null;
    await loadMain();
    toast("Demo reset");
    return;
  }
  if (t.dataset.view) {
    S.view = t.dataset.view;
    S.errors = {};
    if (S.view === "spot") { loadMain(); return; }
    if (S.view === "chat" && !S.loc.startsWith("chat:")) S.loc = S.state.chats[1]?.location || S.loc;
    loadMain();
  }
});

$("#user-select").addEventListener("change", async (e) => {
  S.user = e.target.value;
  store("spot.user2", S.user);
  S.errors = {};
  S.replyTo = null;
  await loadState();
  const visible = [...S.state.chats.map((c) => c.location), ...S.state.teams.flatMap((t) => t.channels.map((c) => c.location))];
  if (S.view !== "spot" && !visible.includes(S.loc)) S.loc = visible[1] || visible[0];
  await loadMain("keep");
  toast(`Signed in as ${S.state.me.display_name} · ${S.state.me.team} ${S.state.me.role}`);
});

const box = $("#compose");
box.addEventListener("input", () => { autosize(); updatePopup(); });
box.addEventListener("keydown", (e) => {
  const openPopup = !$("#popup").classList.contains("hidden") && popupItems.length;
  if (openPopup && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
    e.preventDefault();
    popupIndex = (popupIndex + (e.key === "ArrowDown" ? 1 : popupItems.length - 1)) % popupItems.length;
    document.querySelectorAll(".pop-item").forEach((el, i) => el.classList.toggle("on", i === popupIndex));
    return;
  }
  if (openPopup && (e.key === "Tab" || (e.key === "Enter" && !e.shiftKey))) {
    e.preventDefault();
    choosePopup(popupIndex);
    return;
  }
  if (e.key === "Escape") { hidePopup(); if (S.replyTo) { S.replyTo = null; renderMain("keep"); } return; }
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
$("#send").addEventListener("click", send);

loadState().then(() => loadMain());
