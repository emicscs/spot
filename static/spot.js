// Spot front end: renders a Teams-style chat and talks to app.py.
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
  ["propose", "Propose a change to one of your team's docs"],
  ["ask", "Ask about approved docs, with citations"],
  ["history", "See approved versions and what isn't binding"],
  ["pending", "List changes waiting for approval"],
  ["help", "What Spot can do"],
];

const S = {
  user: store("spot.user") || "bob",
  chat: store("spot.chat") || "dm",
  view: "chat",
  state: null,
  posts: [],
  errors: {},
  pending: null, // optimistic message while the server answers
};

// ---------------------------------------------------------------- formatting

function md(text) {
  return esc(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|\s)(@(Spot|Payments|Ops Automation))\b/gi, '$1<span class="mention">$2</span>');
}

function initials(name) { return name.slice(0, 2).toUpperCase(); }

function avatar(name, size = "") {
  if (name === "Spot") return `<div class="av bot ${size}">${icon("location_24_filled")}</div>`;
  return `<div class="av ${size}">${initials(name)}</div>`;
}

function chatAvatar(chat, size = "") {
  if (chat.id === "dm") return avatar("Spot", size);
  const colors = { ops: ["#DCE8FA", "#0F548C"], pay: ["#DFF6DD", "#0E700E"] }[chat.id] || ["#D9DBF3", "#3D3E66"];
  const letters = chat.name.split(" ").map((w) => w[0]).join("").slice(0, 2);
  return `<div class="av group ${size}" style="background:${colors[0]};color:${colors[1]}">${letters}</div>`;
}

function time(ts) {
  const d = new Date(ts);
  const today = new Date().toDateString() === d.toDateString();
  const t = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  return today ? t : `${d.getMonth() + 1}/${d.getDate()} ${t}`;
}

// ---------------------------------------------------------------- Adaptive Cards

const fg = (d, s = d) => ({ default: d, subtle: s });
const COLORS = {
  default: fg("#FFFFFF", "#ADADAD"), dark: fg("#242424", "#616161"), light: fg("#FFFFFF", "#D6D6D6"),
  accent: fg("#7F85F5", "#9EA2FF"), good: fg("#92C353", "#92C353"), warning: fg("#F8D22A", "#F8D22A"),
  attention: fg("#E37D80", "#E37D80"),
};
const HOST = new AdaptiveCards.HostConfig({
  fontFamily: "'Segoe UI', 'Segoe UI Web (West European)', -apple-system, BlinkMacSystemFont, Roboto, 'Helvetica Neue', sans-serif",
  supportsInteractivity: true,
  spacing: { small: 4, default: 8, medium: 12, large: 16, extraLarge: 24, padding: 16 },
  separator: { lineThickness: 1, lineColor: "#3D3D3D" },
  fontSizes: { small: 12, default: 14, medium: 16, large: 18, extraLarge: 24 },
  fontWeights: { lighter: 300, default: 400, bolder: 600 },
  fontTypes: {
    default: {
      fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
      fontSizes: { small: 12, default: 14, medium: 16, large: 18, extraLarge: 24 },
      fontWeights: { lighter: 300, default: 400, bolder: 600 },
    },
    monospace: {
      fontFamily: "Consolas, 'Courier New', monospace",
      fontSizes: { small: 12, default: 13, medium: 14, large: 16, extraLarge: 20 },
      fontWeights: { lighter: 300, default: 400, bolder: 700 },
    },
  },
  containerStyles: {
    default: { backgroundColor: "#292929", foregroundColors: COLORS },
    emphasis: { backgroundColor: "#1F1F1F", foregroundColors: COLORS },
  },
  actions: { maxActions: 5, spacing: "default", buttonSpacing: 8, actionsOrientation: "horizontal", actionAlignment: "left",
    showCard: { actionMode: "inline", inlineTopMargin: 8 } },
  factSet: { title: { weight: "bolder", size: "default", color: "default", wrap: true, maxWidth: 140 },
    value: { size: "default", color: "default", wrap: true }, spacing: 12 },
  inputs: { label: { inputSpacing: "small", requiredInputs: { weight: "bolder", suffix: " *", suffixColor: "attention" },
    optionalInputs: { weight: "bolder" } }, errorMessage: { size: "small", color: "attention" } },
});

AdaptiveCards.AdaptiveCard.onProcessMarkdown = (text, result) => {
  result.outputHtml = md(text);
  result.didProcess = true;
};

function renderCard(json, messageId) {
  const card = new AdaptiveCards.AdaptiveCard();
  card.hostConfig = HOST;
  card.onExecuteAction = (action) => {
    if (action instanceof AdaptiveCards.SubmitAction) runAction(messageId, action.data);
  };
  card.parse(json);
  return card.render();
}

// ---------------------------------------------------------------- API

async function api(path, body) {
  const res = await fetch(path, body === undefined ? undefined : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  return res.json();
}

async function loadChat(scroll = "bottom") {
  const { posts } = await api(`/api/channel/${S.chat}?user=${S.user}`);
  S.posts = posts;
  renderFeed(scroll);
  await loadState();
}

async function loadState() {
  S.state = await api(`/api/state?user=${S.user}`);
  renderChrome();
}

async function send() {
  const box = $("#compose");
  const text = box.value.trim();
  if (!text) return;
  box.value = "";
  autosize();
  hidePopup();
  const toSpot = S.chat === "dm" || /@spot\b/i.test(text);
  S.pending = { text, typing: toSpot };
  renderFeed("bottom");
  if (toSpot) await sleep(700);
  const { posts } = await api("/api/post", { user: S.user, channel: S.chat, text });
  S.pending = null;
  S.posts = posts;
  S.errors = {};
  renderFeed("bottom");
  loadState();
}

async function runAction(messageId, data) {
  const res = await api("/api/action", { user: S.user, channel: S.chat, message_id: messageId, data });
  S.errors = res.error ? { [messageId]: res.error } : {};
  S.posts = res.posts;
  renderFeed(res.error ? "keep" : "bottom");
  document.querySelector(".card-error")?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  loadState();
}

// ---------------------------------------------------------------- rendering

function renderChrome() {
  const { me, users, channels, activity } = S.state;

  $("#me-btn").innerHTML = `<div class="av">${initials(me.name)}<span class="presence"></span></div>`;
  $("#me-menu").innerHTML =
    `<div class="menu-label">Switch account (demo)</div>` +
    users.map((u) => `
      <button class="menu-item" data-user="${u.name}">
        <div class="av">${initials(u.name)}</div>
        <div class="who">${esc(u.name)}<small>${esc(u.team)} · ${esc(u.role)}</small></div>
        ${u.name === me.name ? icon("checkmark_circle_16_filled", "sm check") : ""}
      </button>`).join("") +
    `<hr><button class="menu-item" data-reset>${icon("arrow_left_20_regular")}<div class="who">Reset demo<small>Restore seed data and clear chats</small></div></button>`;

  const badge = $("#activity-badge");
  badge.textContent = activity.length;
  badge.classList.toggle("hidden", !activity.length);
  document.querySelectorAll(".rail-item").forEach((b) => b.classList.toggle("on", b.dataset.view === S.view));

  const chat = channels.find((c) => c.id === S.chat) || channels[0];
  $("#chat-avatar").innerHTML = chatAvatar(chat);
  $("#chat-name").textContent = chat.name;
  $("#chat-meta").innerHTML = chat.id === "dm" ? `<span>App</span>` :
    `${icon("people_20_regular", "sm")}<span>Group chat · Spot is a member</span>`;
  $("#suggest").innerHTML = chat.id === "dm" ? COMMANDS.map(([cmd, desc]) =>
    `<button class="chip" data-cmd="${cmd}" title="${desc}">${cmd}</button>`).join("") : "";
  $("#compose").placeholder = chat.id === "dm" ? "Type a message to Spot" : "Type a message. Use @Spot to ask Spot.";

  if (S.view === "activity") renderActivity(activity);
  else renderList(channels);
}

function renderList(channels) {
  const row = (c) => {
    const p = c.preview;
    const prev = p ? `${p.author === S.user ? "You" : p.author}: ${p.text.replace(/\*\*/g, "")}` : "";
    const unread = c.unread && c.id !== S.chat;
    return `
      <button class="chat-row ${c.id === S.chat ? "on" : ""} ${unread ? "unread" : ""}" data-chat="${c.id}">
        ${chatAvatar(c)}
        <div class="row-main">
          <div class="row-top"><span class="row-name">${esc(c.name)}</span>${p ? `<span class="row-time">${time(p.ts)}</span>` : ""}</div>
          <div class="row-prev">${esc(prev)}</div>
        </div>
        ${unread ? '<span class="dot"></span>' : ""}
      </button>`;
  };
  $("#list").innerHTML = `
    <div class="list-head"><h1>Chat</h1>
      <button class="tb-icon">${icon("search_20_regular")}</button>
      <button class="tb-icon">${icon("video_20_regular")}</button>
      <button class="tb-icon">${icon("compose_20_regular")}</button></div>
    <div class="pills"><span class="pill">Unread</span><span class="pill">Meeting chats</span><span class="pill">Unmuted</span></div>
    <div class="section">${icon("chevron_down_12_regular", "xs")} Favorites</div>
    ${channels.filter((c) => c.id === "dm").map(row).join("")}
    <div class="section">${icon("chevron_down_12_regular", "xs")} Chats</div>
    ${channels.filter((c) => c.id !== "dm").map(row).join("")}`;
}

function renderActivity(activity) {
  $("#list").innerHTML = `
    <div class="list-head"><h1>Activity</h1></div>
    ${activity.length ? [...activity].reverse().map((a) => `
      <button class="act" data-chat="${a.channel}">
        ${avatar("Spot")}
        <div><strong>Spot</strong> needs <strong>${esc(S.state.me.team)}</strong> to review a change
          <small>${esc(a.summary)}</small><small>${esc(a.doc)} · proposed by ${esc(a.proposed_by)} · ${time(a.ts)}</small></div>
      </button>`).join("") : `<div class="empty">You're all caught up.</div>`}`;
}

function message(m, prev, isReply) {
  const mine = m.author === S.user;
  const cont = prev && prev.author === m.author;
  const head = cont ? "" : `<div class="meta">${mine ? "" : `<b>${esc(m.author)}</b>`}<span>${time(m.ts)}</span></div>`;
  const row = document.createElement("div");
  row.className = `row ${mine ? "mine" : ""} ${cont ? "cont" : ""}`;
  row.innerHTML = `
    ${mine ? "" : `<div class="av-slot">${cont ? "" : avatar(m.author)}</div>`}
    <div class="bubble-col">${head}
      ${m.text ? `<div class="bubble">${md(m.text)}</div>` : ""}
    </div>`;
  const col = row.querySelector(".bubble-col");
  if (m.card) {
    const host = document.createElement("div");
    host.className = "card-host";
    if (m.text) host.style.marginTop = "6px";
    try { host.appendChild(renderCard(m.card, m.id)); }
    catch (e) { host.textContent = `Card failed to render: ${e}`; }
    col.appendChild(host);
  }
  if (S.errors[m.id]) {
    col.insertAdjacentHTML("beforeend",
      `<div class="card-error">${icon("warning_16_filled")}<div>${esc(S.errors[m.id])}</div></div>`);
  }
  return row;
}

function renderFeed(scroll) {
  const feed = $("#feed");
  const keep = feed.scrollTop;
  const chat = (S.state?.channels || []).find((c) => c.id === S.chat);
  const inner = document.createElement("div");
  inner.className = "feed-inner";
  if (S.chat === "dm") {
    inner.insertAdjacentHTML("beforeend", `<div class="hero">${avatar("Spot", "lg")}
      <h2>Spot</h2><p>Version control for requirements. Propose changes, get them approved by the teams that depend on you, and ask questions about approved docs.</p></div>`);
  } else if (chat) {
    inner.insertAdjacentHTML("beforeend", `<div class="hero">${chatAvatar(chat, "lg")}
      <h2>${esc(chat.name)}</h2><p>Group chat for the ${esc(chat.team)} team. Spot is a member: mention <span class="mention">@Spot</span> to use it.</p></div>`);
  }
  const flat = S.posts.flatMap((p) => [p, ...p.replies]);
  if (S.pending) {
    flat.push({ id: "pending", author: S.user, text: S.pending.text, ts: new Date().toISOString() });
  }
  flat.forEach((m, i) => inner.appendChild(message(m, flat[i - 1])));
  if (S.pending?.typing) {
    inner.insertAdjacentHTML("beforeend", `<div class="row"><div class="av-slot">${avatar("Spot")}</div>
      <div class="bubble-col"><div class="meta"><b>Spot</b><span>is typing…</span></div>
      <div class="bubble"><span class="typing"><i></i><i></i><i></i></span></div></div></div>`);
  }
  feed.replaceChildren(inner);
  feed.scrollTop = scroll === "keep" ? keep : feed.scrollHeight;
}

// ---------------------------------------------------------------- composer: @mention and command menu

let popupItems = [];
let popupIndex = 0;

function showPopup(title, items) {
  popupItems = items;
  popupIndex = 0;
  const pop = $("#popup");
  pop.innerHTML = `<div class="popup-head">${title}</div>` + items.map((it, i) => `
    <button class="pop-item ${i === 0 ? "on" : ""}" data-i="${i}">${it.html}</button>`).join("");
  pop.classList.remove("hidden");
}

function hidePopup() { $("#popup").classList.add("hidden"); popupItems = []; }

function updatePopup() {
  const v = $("#compose").value;
  const mention = v.match(/(^|\s)@(\w*)$/);
  if (mention && "spot".startsWith(mention[2].toLowerCase())) {
    showPopup("Suggestions", [{
      html: `${avatar("Spot")}<div><b>Spot</b><small>App · requirements version control</small></div>`,
      apply: () => v.replace(/@\w*$/, "@Spot "),
    }]);
    return;
  }
  if (S.chat !== "dm" && /^\s*@Spot\s+$/i.test(v)) {
    showPopup("Spot commands", COMMANDS.map(([cmd, desc]) => ({
      html: `${avatar("Spot")}<div><b>${cmd}</b><small>${desc}</small></div>`,
      apply: () => `@Spot ${cmd} `,
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

function openChat(id) {
  S.chat = id;
  S.view = "chat";
  S.errors = {};
  store("spot.chat", id);
  loadChat();
}

document.addEventListener("click", async (e) => {
  const chip = e.target.closest("[data-cmd]");
  if (chip) {
    const b = $("#compose");
    b.value = `${chip.dataset.cmd} `;
    b.focus();
    autosize();
    return;
  }
  const t = e.target.closest("[data-chat],[data-user],[data-reset],[data-view],#me-btn,.pop-item");
  if (!t) { if (!e.target.closest("#me-menu")) $("#me-menu").classList.add("hidden"); return; }
  if (t.id === "me-btn") { $("#me-menu").classList.toggle("hidden"); return; }
  if (t.classList.contains("pop-item")) { choosePopup(+t.dataset.i); return; }
  if (t.dataset.chat) { openChat(t.dataset.chat); return; }
  if (t.dataset.user) {
    $("#me-menu").classList.add("hidden");
    S.user = t.dataset.user;
    store("spot.user", S.user);
    S.errors = {};
    await loadChat();
    toast(`Signed in as ${S.user} · ${S.state.me.team} ${S.state.me.role}`);
    return;
  }
  if (t.hasAttribute("data-reset")) {
    $("#me-menu").classList.add("hidden");
    await api("/api/reset", {});
    S.errors = {};
    await loadChat();
    toast("Demo reset");
    return;
  }
  if (t.dataset.view) {
    if (t.dataset.view === "activity" || t.dataset.view === "chat") {
      S.view = t.dataset.view;
      renderChrome();
    } else if (t.dataset.view === "spot") {
      openChat("dm");
    }
  }
});

const box = $("#compose");
box.addEventListener("input", () => { autosize(); updatePopup(); });
box.addEventListener("keydown", (e) => {
  const open = !$("#popup").classList.contains("hidden") && popupItems.length;
  if (open && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
    e.preventDefault();
    popupIndex = (popupIndex + (e.key === "ArrowDown" ? 1 : popupItems.length - 1)) % popupItems.length;
    document.querySelectorAll(".pop-item").forEach((el, i) => el.classList.toggle("on", i === popupIndex));
    return;
  }
  if (open && (e.key === "Tab" || (e.key === "Enter" && !e.shiftKey))) {
    e.preventDefault();
    choosePopup(popupIndex);
    return;
  }
  if (e.key === "Escape") { hidePopup(); return; }
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
$("#send").addEventListener("click", send);

loadChat();
