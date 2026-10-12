"""Spot UI: a Microsoft Teams lookalike. Owner: Frankie. See CONTRACTS.md.

Run: python app.py, then open http://localhost:8501
The page in static/ emulates a Teams channel. You talk to Spot by typing
"@Spot <command>"; Spot replies with Adaptive Cards built in this file.
Build against fake return values first (USE_FAKES = True); swap in the real
db, governance and rag at integration.
"""
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from flask import Flask, jsonify, request, send_from_directory

# Flip to False at integration (1:05) to use the real db, governance and rag.
USE_FAKES = True


# ---------------------------------------------------------------------------
# Fake backend: same signatures and return shapes as CONTRACTS.md, kept in
# memory so propose/approve/reject actually change what you see.
# ---------------------------------------------------------------------------

FAKE_USERS = {
    "alice": {"name": "alice", "team": "Ops Automation", "role": "Approver"},
    "bob": {"name": "bob", "team": "Ops Automation", "role": "Contributor"},
    "carol": {"name": "carol", "team": "Payments", "role": "Reader"},
    "dave": {"name": "dave", "team": "Payments", "role": "Approver"},
}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fake_seed():
    def doc(doc_id, title, team, content, author, approver):
        return {"doc_id": doc_id, "title": title, "team": team, "content": content,
                "version": 1, "author": author, "approver": approver,
                "updated_at": "2026-10-01T09:00:00+00:00"}

    docs = [
        doc("ops-uae-identity", "UAE Identity Service: Scope", "Ops Automation",
            "Scope: migrate UAE identity verification to the regional service.\n"
            "Cutover date: 2026-11-02.\n"
            "Out of scope: card tokenization.", "bob", "alice"),
        doc("ops-uae-gateway", "UAE Gateway: Cutover Plan", "Ops Automation",
            "Gateway cutover: 2026-11-16.\n"
            "Rollback window: 48 hours.", "alice", "alice"),
        doc("pay-settlement", "Payments: UAE Settlement Requirements", "Payments",
            "Settlement must run on the regional identity service after cutover.\n"
            "Depends on: UAE Identity Service.", "dave", "dave"),
    ]
    history = [{"doc_id": d["doc_id"], "version": 1, "content": d["content"],
                "changed_by": d["author"], "approved_by": d["approver"],
                "summary": "Initial version", "deadline": None,
                "changed_at": d["updated_at"]} for d in docs]
    proposals = [{
        "proposal_id": str(uuid.uuid4()), "doc_id": "ops-uae-gateway",
        "new_content": "Gateway cutover: 2026-11-09.\nRollback window: 48 hours.",
        "summary": "Move UAE gateway cutover up one week", "deadline": "2026-10-20",
        "proposed_by": "bob", "required_team": "Payments", "status": "pending",
        "approved_by": None, "created_at": "2026-10-10T14:00:00+00:00",
    }]
    return {"docs": {d["doc_id"]: d for d in docs}, "history": history,
            "proposals": proposals, "deps": [("Payments", "Ops Automation")]}


_FAKE = _fake_seed()


def _fake_get_user(name):
    return FAKE_USERS.get(name)


def _fake_get_doc(doc_id):
    d = _FAKE["docs"].get(doc_id)
    return dict(d) if d else None


def _fake_get_docs_for_user(name):
    user = _fake_get_user(name)
    teams = {user["team"]} | {dep for t, dep in _FAKE["deps"] if t == user["team"]}
    return [dict(d) for d in _FAKE["docs"].values() if d["team"] in teams]


def _fake_get_history(doc_id):
    rows = [dict(h) for h in _FAKE["history"] if h["doc_id"] == doc_id]
    return sorted(rows, key=lambda h: h["version"], reverse=True)


def _fake_get_proposals(doc_id):
    return [dict(p) for p in _FAKE["proposals"] if p["doc_id"] == doc_id]


def _fake_get_pending():
    return [dict(p) for p in _FAKE["proposals"] if p["status"] == "pending"]


def _fake_get_dependent_teams(team):
    return [t for t, dep in _FAKE["deps"] if dep == team]


def _fake_reset():
    global _FAKE
    _FAKE = _fake_seed()


def _fake_propose(user, doc_id, new_content, summary, deadline):
    u, doc = _fake_get_user(user), _FAKE["docs"][doc_id]
    if u["role"] not in ("Contributor", "Approver"):
        raise PermissionError(f"{user} is a {u['role']}; only Contributors and Approvers can propose")
    if u["team"] != doc["team"]:
        raise PermissionError(f"Only {doc['team']} can propose changes to {doc['title']}")
    dependents = _fake_get_dependent_teams(doc["team"])
    proposal_id = str(uuid.uuid4())
    _FAKE["proposals"].append({
        "proposal_id": proposal_id, "doc_id": doc_id, "new_content": new_content,
        "summary": summary, "deadline": deadline, "proposed_by": user,
        "required_team": dependents[0] if dependents else doc["team"],
        "status": "pending", "approved_by": None, "created_at": _now(),
    })
    return proposal_id


def _fake_check_reviewer(user, p):
    u, doc = _fake_get_user(user), _FAKE["docs"][p["doc_id"]]
    if p["status"] != "pending":
        raise PermissionError(f"This proposal is already {p['status']}")
    if u["team"] != p["required_team"]:
        why = (f"{p['required_team']} depends on {doc['team']}"
               if p["required_team"] != doc["team"] else "no other team depends on it")
        raise PermissionError(f"Only {p['required_team']} can approve: {why}")
    if u["role"] != "Approver":
        raise PermissionError(f"{user} is a {u['role']}; only Approvers can approve or reject")


def _fake_find(proposal_id):
    return next(p for p in _FAKE["proposals"] if p["proposal_id"] == proposal_id)


def _fake_approve(user, proposal_id):
    p = _fake_find(proposal_id)
    _fake_check_reviewer(user, p)
    doc = _FAKE["docs"][p["doc_id"]]
    doc.update(content=p["new_content"], version=doc["version"] + 1,
               approver=user, updated_at=_now())
    _FAKE["history"].append({
        "doc_id": doc["doc_id"], "version": doc["version"], "content": p["new_content"],
        "changed_by": p["proposed_by"], "approved_by": user, "summary": p["summary"],
        "deadline": p["deadline"], "changed_at": doc["updated_at"],
    })
    p.update(status="approved", approved_by=user)
    return doc["version"]


def _fake_reject(user, proposal_id):
    p = _fake_find(proposal_id)
    _fake_check_reviewer(user, p)
    p["status"] = "rejected"


def _tokens(text):
    return {w.strip("?.,:()").lower() for w in text.split() if len(w) > 3}


def _fake_ask(user, question):
    words = _tokens(question)
    scored = [(len(words & _tokens(d["title"] + " " + line)), line, d)
              for d in _fake_get_docs_for_user(user) for line in d["content"].splitlines()]
    score, line, d = max(scored, key=lambda s: s[0], default=(0, None, None))
    if score < 2:
        return {"answer": "That isn't in your documents.", "sources": []}
    source = {k: d[k] for k in ("doc_id", "title", "version", "author", "approver")}
    return {"answer": f"{line} (Source: {d['title']}, v{d['version']}, "
                      f"author {d['author']}, approved by {d['approver']})",
            "sources": [source]}


if USE_FAKES:
    db = SimpleNamespace(
        get_user=_fake_get_user, get_docs_for_user=_fake_get_docs_for_user,
        get_doc=_fake_get_doc, get_history=_fake_get_history,
        get_proposals=_fake_get_proposals, get_pending=_fake_get_pending,
        get_dependent_teams=_fake_get_dependent_teams, reset=_fake_reset)
    governance = SimpleNamespace(propose=_fake_propose, approve=_fake_approve,
                                 reject=_fake_reject)
    rag = SimpleNamespace(ask=_fake_ask)
else:
    import db
    import governance
    import rag

USERS = ["alice", "bob", "carol", "dave"]


# ---------------------------------------------------------------------------
# Teams state: channels and posts. UI-only, never stored in the database.
# A post is {"id", "author", "text", "ts", "kind", "params", "replies"}; cards
# are rebuilt from the database on every read, so they refresh in place the
# way Teams Universal Action cards do.
# ---------------------------------------------------------------------------

CHANNELS = [
    {"id": "ops", "team": "Ops Automation", "name": "General"},
    {"id": "pay", "team": "Payments", "name": "General"},
]
TEAM_CHANNEL = {c["team"]: c["id"] for c in CHANNELS}
POSTS = {}
SEEN = {}  # (user, channel) -> number of posts seen


def _post(channel, author, text="", kind=None, params=None, parent=None):
    msg = {"id": uuid.uuid4().hex[:12], "author": author, "text": text, "ts": _now(),
           "kind": kind, "params": params or {}, "replies": []}
    (parent["replies"] if parent else POSTS[channel]).append(msg)
    return msg


def _find_post(channel, message_id):
    for post in POSTS[channel]:
        for msg in [post] + post["replies"]:
            if msg["id"] == message_id:
                return post, msg
    raise KeyError(message_id)


def _announce(p, old_content, skip_channel=None):
    """Post the approval request in the reviewing team's channel."""
    channel = TEAM_CHANNEL.get(p["required_team"])
    if channel and channel != skip_channel:
        _post(channel, "Spot", f"**@{p['required_team']}** approval requested",
              kind="proposal", params={"proposal_id": p["proposal_id"],
                                       "doc_id": p["doc_id"], "old_content": old_content})


def reset_ui():
    POSTS.clear()
    SEEN.clear()
    for c in CHANNELS:
        POSTS[c["id"]] = []
        _post(c["id"], "Spot", "Hi, I'm **Spot**. I keep this team's requirements under "
                               "version control. Mention me with **@Spot help** to get started.")
    for p in db.get_pending():
        doc = db.get_doc(p["doc_id"])
        _announce(p, doc["content"])
        if TEAM_CHANNEL.get(doc["team"]) != TEAM_CHANNEL.get(p["required_team"]):
            _post(TEAM_CHANNEL[doc["team"]], "Spot",
                  f"**{p['proposed_by']}** proposed a change. Waiting on "
                  f"**{p['required_team']}**.", kind="proposal",
                  params={"proposal_id": p["proposal_id"], "doc_id": p["doc_id"],
                          "old_content": doc["content"]})


# ---------------------------------------------------------------------------
# Adaptive Cards (schema 1.5). The same JSON would ship to real Teams.
# ---------------------------------------------------------------------------

def _card(body, actions=None):
    card = {"type": "AdaptiveCard", "version": "1.5", "body": body}
    if actions:
        card["actions"] = actions
    return card


def _text(text, **kw):
    return {"type": "TextBlock", "text": text, "wrap": True, **kw}


def _eyebrow(label):
    return _text(f"SPOT · {label}", size="Small", weight="Bolder", isSubtle=True,
                 spacing="None")


def _routing(p, doc):
    if p["required_team"] != doc["team"]:
        return f"{p['required_team']} (depends on {doc['team']})"
    return f"{p['required_team']} (no other team depends on it)"


def _content_column(label, content, other, color):
    other_lines = set(other.splitlines())
    lines = [_text(line, fontType="Monospace", size="Small", spacing="None",
                   **({"color": color, "weight": "Bolder"} if line not in other_lines else {}))
             for line in content.splitlines() if line.strip()]
    return {"type": "Column", "width": "stretch", "items": [
        _text(label, size="Small", weight="Bolder", isSubtle=True),
        {"type": "Container", "style": "emphasis", "bleed": False, "items": lines},
    ]}


def proposal_card(params):
    p = next((x for x in db.get_proposals(params["doc_id"])
              if x["proposal_id"] == params["proposal_id"]), None)
    doc = db.get_doc(params["doc_id"])
    if not p or not doc:
        return _card([_text("This proposal no longer exists.", isSubtle=True)])
    old = params.get("old_content", doc["content"])
    status = p["status"]
    title = {"pending": f"Approval requested from {p['required_team']}",
             "approved": f"Approved by {p['approved_by']}",
             "rejected": "Rejected"}[status]
    body = [
        _eyebrow("CHANGE REQUEST"),
        _text(title, size="Large", weight="Bolder", spacing="Small",
              **({"color": "Good"} if status == "approved" else
                 {"color": "Attention"} if status == "rejected" else {})),
        _text(p["summary"], spacing="Small"),
        {"type": "FactSet", "facts": [
            {"title": "Document", "value": doc["title"]},
            {"title": "Proposed by", "value": p["proposed_by"]},
            {"title": "Deadline", "value": p["deadline"] or "none"},
            {"title": "Routed to", "value": _routing(p, doc)},
        ]},
        {"type": "ColumnSet", "spacing": "Medium", "columns": [
            _content_column("CURRENT · APPROVED" if status == "pending" else "BEFORE",
                            old, p["new_content"], "Attention"),
            _content_column("PROPOSED" if status == "pending" else "AFTER",
                            p["new_content"], old, "Good"),
        ]},
    ]
    if status == "approved":
        body.append(_text(f"✅ Binding now. {doc['title']} is v{doc['version']}, "
                          f"changed by {p['proposed_by']}, approved by {p['approved_by']}.",
                          color="Good", size="Small", spacing="Medium"))
        return _card(body)
    if status == "rejected":
        body.append(_text("Not approved: not binding.", color="Attention", size="Small",
                          spacing="Medium"))
        return _card(body)
    data = {"proposal_id": p["proposal_id"], "doc_id": p["doc_id"]}
    return _card(body, [
        {"type": "Action.Submit", "title": "Approve", "style": "positive",
         "data": {"action": "approve", **data}},
        {"type": "Action.Submit", "title": "Reject", "style": "destructive",
         "data": {"action": "reject", **data}},
    ])


def propose_form_card(params):
    doc = db.get_doc(params["doc_id"])
    dependents = db.get_dependent_teams(doc["team"])
    route = (f"{dependents[0]}, because {dependents[0]} depends on {doc['team']}"
             if dependents else f"{doc['team']}, because no other team depends on it")
    return _card([
        _eyebrow("PROPOSE A CHANGE"),
        _text(doc["title"], size="Large", weight="Bolder", spacing="Small"),
        _text(f"Current: v{doc['version']}, approved by {doc['approver']}",
              isSubtle=True, size="Small", spacing="None"),
        {"type": "Input.Text", "id": "new_content", "label": "New content",
         "isMultiline": True, "value": doc["content"], "isRequired": True,
         "errorMessage": "Enter the new content"},
        {"type": "Input.Text", "id": "summary", "label": "What changed and why",
         "placeholder": "e.g. Cutover moved two weeks per Infra meeting 10/9",
         "isRequired": True, "errorMessage": "Add a short summary"},
        {"type": "Input.Date", "id": "deadline", "label": "Approval needed by",
         "value": (date.today() + timedelta(days=7)).isoformat(), "isRequired": True},
        _text(f"Spot will route this to {route}.", isSubtle=True, size="Small"),
    ], [{"type": "Action.Submit", "title": "Submit for approval", "style": "positive",
         "data": {"action": "submit_proposal", "doc_id": doc["doc_id"]}}])


def doc_picker_card(params):
    return _card([
        _eyebrow(params["label"].upper()),
        _text(params["prompt"], weight="Bolder"),
        {"type": "Input.ChoiceSet", "id": "doc_id", "style": "compact", "isRequired": True,
         "value": params["docs"][0]["doc_id"],
         "choices": [{"title": d["title"], "value": d["doc_id"]} for d in params["docs"]]},
    ], [{"type": "Action.Submit", "title": "Continue",
         "data": {"action": params["next"]}}])


def history_card(params):
    doc = db.get_doc(params["doc_id"])
    body = [
        _eyebrow("HISTORY"),
        _text(doc["title"], size="Large", weight="Bolder", spacing="Small"),
        _text(f"{doc['team']} · current v{doc['version']}, approved by {doc['approver']}",
              isSubtle=True, size="Small", spacing="None"),
    ]
    for i, h in enumerate(db.get_history(doc["doc_id"])):
        meta = (f"changed by {h['changed_by']} · approved by {h['approved_by']} · "
                f"{(h['changed_at'] or '')[:10]}")
        if h["deadline"]:
            meta += f" · deadline {h['deadline']}"
        body.append({"type": "ColumnSet", "separator": True, "spacing": "Medium", "columns": [
            {"type": "Column", "width": "40px", "items": [
                _text(f"v{h['version']}", weight="Bolder", size="Medium",
                      **({"color": "Good"} if i == 0 else {}))]},
            {"type": "Column", "width": "stretch", "items": [
                _text(h["summary"] + ("  ·  **CURRENT**" if i == 0 else "")),
                _text(meta, isSubtle=True, size="Small", spacing="None")]},
        ]})
    not_binding = [p for p in db.get_proposals(doc["doc_id"]) if p["status"] != "approved"]
    if not_binding:
        body.append(_text("NOT APPROVED: NOT BINDING", weight="Bolder", size="Small",
                          color="Attention", separator=True, spacing="Large"))
        for p in not_binding:
            body.append(_text(f"**{p['status'].capitalize()}:** {p['summary']}", spacing="Small"))
            body.append(_text(f"proposed by {p['proposed_by']} · needs {p['required_team']} · "
                              f"deadline {p['deadline']} · Not approved: not binding.",
                              isSubtle=True, size="Small", spacing="None"))
    return _card(body)


def answer_card(params):
    body = [_eyebrow("ANSWER"), _text(params["answer"], spacing="Small")]
    if params["sources"]:
        body.append(_text("SOURCES", size="Small", weight="Bolder", isSubtle=True,
                          separator=True, spacing="Medium"))
        for s in params["sources"]:
            body.append(_text(f"📄 **{s['title']}** · v{s['version']} · by {s['author']} · "
                              f"approved by {s['approver']}", size="Small", spacing="Small"))
    body.append(_text("Answered from approved documents only. Pending proposals are never used.",
                      isSubtle=True, size="Small", spacing="Medium"))
    return _card(body)


def help_card(params):
    return _card([
        _eyebrow("HELP"),
        _text("Here's what I can do", size="Large", weight="Bolder", spacing="Small"),
        {"type": "FactSet", "facts": [
            {"title": "@Spot propose <doc>", "value": "Propose a change to one of your team's docs"},
            {"title": "@Spot ask <question>", "value": "Ask about approved docs, with citations"},
            {"title": "@Spot history <doc>", "value": "See approved versions and what isn't binding"},
            {"title": "@Spot pending", "value": "List changes waiting for approval"},
        ]},
        _text("Changes only become binding when an Approver on the dependent team approves them.",
              isSubtle=True, size="Small"),
    ])


CARDS = {"proposal": proposal_card, "propose_form": propose_form_card,
         "doc_picker": doc_picker_card, "history": history_card,
         "answer": answer_card, "help": help_card}


# ---------------------------------------------------------------------------
# @Spot commands and card actions
# ---------------------------------------------------------------------------

def _match_doc(docs, query):
    words = _tokens(query)
    scored = [(len(words & _tokens(d["title"] + " " + d["doc_id"].replace("-", " "))), d)
              for d in docs]
    score, doc = max(scored, key=lambda s: s[0], default=(0, None))
    return doc if score else None


def _picker(user, docs, label, prompt, next_action):
    return {"kind": "doc_picker", "params": {
        "label": label, "prompt": prompt, "next": next_action,
        "docs": [{"doc_id": d["doc_id"], "title": d["title"]} for d in docs]}}


def handle_command(user, channel, text, post):
    command = re.sub(r"@spot\b", "", text, flags=re.I).strip()
    word, _, rest = command.partition(" ")
    word = word.lower()
    me = db.get_user(user)

    if word in ("", "help"):
        _post(channel, "Spot", kind="help", parent=post)
    elif word == "propose":
        if me["role"] not in ("Contributor", "Approver"):
            _post(channel, "Spot", f"{user}, you're a **{me['role']}** on {me['team']}, so you "
                                   "can't propose changes. Ask a Contributor or Approver.",
                  parent=post)
            return
        own = [d for d in db.get_docs_for_user(user) if d["team"] == me["team"]]
        doc = _match_doc(own, rest)
        if doc:
            _post(channel, "Spot", kind="propose_form", params={"doc_id": doc["doc_id"]},
                  parent=post)
        else:
            _post(channel, "Spot", parent=post, **_picker(
                user, own, "Propose a change", "Which doc do you want to change?",
                "pick_propose"))
    elif word == "history":
        docs = db.get_docs_for_user(user)
        doc = _match_doc(docs, rest)
        if doc:
            _post(channel, "Spot", kind="history", params={"doc_id": doc["doc_id"]}, parent=post)
        else:
            _post(channel, "Spot", parent=post, **_picker(
                user, docs, "History", "Which doc's history?", "pick_history"))
    elif word == "pending":
        pending = db.get_pending()
        if not pending:
            _post(channel, "Spot", "Nothing is waiting for approval.", parent=post)
        for p in pending:
            _post(channel, "Spot", kind="proposal", parent=post,
                  params={"proposal_id": p["proposal_id"], "doc_id": p["doc_id"],
                          "old_content": db.get_doc(p["doc_id"])["content"]})
    else:
        question = rest if word == "ask" else command
        try:
            result = rag.ask(user, question)
        except Exception as e:  # keep the demo alive if the LLM call fails
            _post(channel, "Spot", f"Sorry, I couldn't reach the language model ({e}).",
                  parent=post)
            return
        _post(channel, "Spot", kind="answer", params=result, parent=post)


def handle_action(user, channel, message_id, data):
    """Runs a card button. Returns an error string, or None on success."""
    post, msg = _find_post(channel, message_id)
    action = data.get("action")
    if action == "pick_propose":
        msg.update(kind="propose_form", params={"doc_id": data["doc_id"]})
    elif action == "pick_history":
        msg.update(kind="history", params={"doc_id": data["doc_id"]})
    elif action == "submit_proposal":
        doc = db.get_doc(data["doc_id"])
        if data.get("new_content", "").strip() == doc["content"].strip():
            return "Nothing changed. Edit the content before submitting."
        pid = governance.propose(user, doc["doc_id"], data["new_content"],
                                 data["summary"], data["deadline"])
        p = next(x for x in db.get_pending() if x["proposal_id"] == pid)
        msg.update(kind="proposal", params={"proposal_id": pid, "doc_id": doc["doc_id"],
                                            "old_content": doc["content"]})
        target = TEAM_CHANNEL.get(p["required_team"])
        where = (f" I've asked them in **{p['required_team']} › General**."
                 if target and target != channel else "")
        _post(channel, "Spot", f"Routed to **{_routing(p, doc)}**.{where}", parent=post)
        _announce(p, doc["content"], skip_channel=channel)
    elif action == "approve":
        version = governance.approve(user, data["proposal_id"])
        doc = db.get_doc(data["doc_id"])
        _post(channel, "Spot", f"**{user}** approved. **{doc['title']}** is now "
                               f"**v{version}** and recorded in History.", parent=post)
    elif action == "reject":
        governance.reject(user, data["proposal_id"])
        _post(channel, "Spot", f"**{user}** rejected this change. It is not binding.",
              parent=post)
    return None


# ---------------------------------------------------------------------------
# HTTP API for static/spot.js
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder="static", static_url_path="/static")


def _render(msg):
    out = {k: msg[k] for k in ("id", "author", "text", "ts")}
    out["card"] = CARDS[msg["kind"]](msg["params"]) if msg["kind"] else None
    return out


def _channel_view(user, channel):
    SEEN[(user, channel)] = len(POSTS[channel])
    return [dict(_render(p), replies=[_render(r) for r in p["replies"]])
            for p in POSTS[channel]]


def _state(user):
    me = db.get_user(user)
    pending = [p for p in db.get_pending() if p["required_team"] == me["team"]]
    activity = []
    for p in pending:
        doc = db.get_doc(p["doc_id"])
        activity.append({"channel": TEAM_CHANNEL.get(me["team"]), "summary": p["summary"],
                         "doc": doc["title"], "proposed_by": p["proposed_by"],
                         "ts": p["created_at"]})
    channels = [dict(c, unread=max(0, len(POSTS[c["id"]]) - SEEN.get((user, c["id"]), 0)))
                for c in CHANNELS]
    return {"me": me, "users": [db.get_user(u) for u in USERS],
            "channels": channels, "activity": activity}


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/state")
def api_state():
    return jsonify(_state(request.args["user"]))


@app.get("/api/channel/<channel>")
def api_channel(channel):
    return jsonify({"posts": _channel_view(request.args["user"], channel)})


@app.post("/api/post")
def api_post():
    body = request.get_json()
    user, channel, text = body["user"], body["channel"], body["text"].strip()
    post = _post(channel, user, text)
    if re.search(r"@spot\b", text, flags=re.I):
        handle_command(user, channel, text, post)
    return jsonify({"posts": _channel_view(user, channel)})


@app.post("/api/action")
def api_action():
    body = request.get_json()
    user, channel = body["user"], body["channel"]
    try:
        error = handle_action(user, channel, body["message_id"], body["data"])
    except PermissionError as e:
        error = str(e)
    return jsonify({"posts": _channel_view(user, channel), "error": error})


@app.post("/api/reset")
def api_reset():
    db.reset()
    reset_ui()
    return jsonify({"ok": True})


def main():
    try:
        db.get_pending()
    except Exception:  # first run against the real db: create and seed it
        db.reset()
    reset_ui()
    app.run(host="127.0.0.1", port=8501, debug=False)


if __name__ == "__main__":
    main()
