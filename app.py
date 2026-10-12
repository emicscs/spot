"""Spot UI: a Microsoft Teams lookalike for a fictional Mastercard workspace. Owner: Contributor 1.

Run: python app.py, then open http://localhost:8501
Teams, channels, chats and seed messages come from workspace.py. Spot is a bot:
mention "@Spot" in any channel or chat (or talk to it directly in the Spot app)
and it replies with Adaptive Cards built here. All data goes through the
contract functions in db, governance and rag. See CONTRACTS.md.
"""
import difflib
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from flask import Flask, jsonify, request, send_from_directory

import db
import governance
import rag
import workspace

CORE_USERS = ["marcus.chen", "priya.raman", "daniel.okafor", "elena.rossi"]
# Where Spot posts approval requests for each contract team.
TEAM_HOME = {"Ops Automation": "channel:ops-general", "Payments": "channel:pay-general"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _user(name):
    if name == "spot":
        return workspace.SPOT_BOT
    return db.get_user(name) or {"name": name, "display_name": name, "title": "",
                                 "team": None, "role": "", "avatar_color": "#616161"}


def _name(name):
    return _user(name)["display_name"] if name else ""


def _tokens(text):
    return {w.strip("?.,:()!").lower() for w in text.split() if len(w) > 3}


def _nice_date(value):
    try:
        return date.fromisoformat(str(value)[:10]).strftime("%b %-d, %Y")
    except ValueError:
        return value or "none"


# ---------------------------------------------------------------------------
# Workspace state: who sees what, and the posts in each location. UI-only;
# never stored in the database. A post is {"id", "author", "text", "ts", "kind",
# "params", "replies"}. Cards are rebuilt from the database on every read, so
# they refresh in place the way Teams Universal Action cards do.
# ---------------------------------------------------------------------------

POSTS = {}
SEEN = {}                    # (user, location) -> message count seen
BASELINE = {}                # location -> message count right after reset (already "read")
SPOT_VIEW = {}               # user -> {"propose_doc", "propose_summary", "history_doc"}


def _channels_for(user):
    allowed = workspace.CHANNEL_RESTRICTIONS.get(user)
    teams = []
    for t in workspace.TEAMS:
        if user not in t["members"]:
            continue
        channels = [c for c in t["channels"] if not allowed or c["id"] in allowed]
        if channels:
            teams.append({**t, "channels": channels})
    return teams


def _chats_for(user):
    return [c for c in workspace.CHATS if user in c["members"]]


def _can_see(user, loc):
    if loc == f"spot:{user}":
        return True
    kind, _, ident = loc.partition(":")
    if kind == "channel":
        return any(c["id"] == ident for t in _channels_for(user) for c in t["channels"])
    if kind == "chat":
        return any(c["id"] == ident for c in _chats_for(user))
    return False


def _posts(loc):
    if loc not in POSTS:
        POSTS[loc] = []
        if loc.startswith("spot:"):
            user = loc.split(":", 1)[1]
            _post(loc, "spot", f"Hi {_name(user).split()[0]}! I'm **Spot**. I keep the program's "
                               "requirements under version control. Try **help**.")
    return POSTS[loc]


def _post(loc, author, text="", kind=None, params=None, parent=None, ts=None, msg_id=None):
    msg = {"id": msg_id or uuid.uuid4().hex[:12], "author": author, "text": text,
           "ts": ts or _now(), "kind": kind, "params": params or {}, "replies": []}
    (parent["replies"] if parent else _posts(loc)).append(msg)
    return msg


def _find(loc, message_id):
    for post in _posts(loc):
        for msg in [post] + post["replies"]:
            if msg["id"] == message_id:
                return post, msg
    raise KeyError(message_id)


def _proposal(proposal_id, doc_id=None):
    docs = [doc_id] if doc_id else [p["doc_id"] for p in db.get_pending()]
    for d in docs:
        for p in db.get_proposals(d):
            if p["proposal_id"] == proposal_id:
                return p
    return None


def _proposal_params(p):
    return {"proposal_id": p["proposal_id"], "doc_id": p["doc_id"],
            "old_content": db.get_doc(p["doc_id"])["content"]}


def reset_ui():
    POSTS.clear()
    SEEN.clear()
    BASELINE.clear()
    SPOT_VIEW.clear()
    by_id = {}
    for m in sorted(workspace.MESSAGES, key=lambda m: m["timestamp"]):
        kind, params = ("system", {}) if m["author"] == "system" else (None, {})
        if m["proposal_id"]:
            p = _proposal(m["proposal_id"])
            if p:
                kind, params = "proposal", _proposal_params(p)
        parent = by_id.get(m["thread_parent_id"])
        by_id[m["message_id"]] = _post(m["location"], m["author"], m["text"], kind=kind,
                                       params=params, parent=parent, ts=m["timestamp"],
                                       msg_id=m["message_id"])
    BASELINE.update({loc: len(posts) for loc, posts in POSTS.items()})


def _announce(p, skip_loc=None):
    """Post the approval request in the reviewing team's home channel."""
    loc = TEAM_HOME.get(p["required_team"])
    if loc and loc != skip_loc:
        _post(loc, "spot", f"**{p['required_team']}**, your approval is needed.",
              kind="proposal", params=_proposal_params(p))


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


def _routing(p, doc):
    if p["required_team"] != doc["team"]:
        return f"{p['required_team']} (depends on {doc['team']})"
    return f"{p['required_team']} (no other team depends on it)"


def _diff_inlines(old, new, context=8):
    """Word-level diff as RichTextBlock runs: removed words struck through, added words bold."""
    a, b = old.split(), new.split()
    runs = []
    ops = difflib.SequenceMatcher(None, a, b).get_opcodes()
    for i, (tag, a1, a2, b1, b2) in enumerate(ops):
        if tag == "equal":
            words = a[a1:a2]
            if len(words) > context * 2:
                head = words[:context] if i else []
                tail = words[-context:] if i < len(ops) - 1 else []
                words = head + ["…"] + tail
            runs.append({"type": "TextRun", "text": " ".join(words) + " "})
            continue
        if a2 > a1:
            runs.append({"type": "TextRun", "text": " ".join(a[a1:a2]), "strikethrough": True,
                         "color": "Attention"})
            runs.append({"type": "TextRun", "text": " "})
        if b2 > b1:
            runs.append({"type": "TextRun", "text": " ".join(b[b1:b2]), "weight": "Bolder",
                         "color": "Good"})
            runs.append({"type": "TextRun", "text": " "})
    return runs


def proposal_card(params):
    p = _proposal(params["proposal_id"], params["doc_id"])
    doc = db.get_doc(params["doc_id"])
    if not p or not doc:
        return _card([_text("This proposal no longer exists.", isSubtle=True)])
    status = p["status"]
    status_line = {
        "pending": _text(f"● Pending approval from {p['required_team']}", size="Small",
                         weight="Bolder", color="Accent"),
        "approved": _text(f"✓ Approved by {_name(p['approved_by'])}", size="Small",
                          weight="Bolder", color="Good"),
        "rejected": _text("✕ Rejected", size="Small", weight="Bolder", color="Attention"),
    }[status]
    body = [
        status_line,
        _text(p["summary"], size="Large", weight="Bolder", spacing="Small"),
        _text(f"{doc['title']} · proposed by {_name(p['proposed_by'])}", isSubtle=True,
              size="Small", spacing="None"),
        {"type": "FactSet", "spacing": "Medium", "facts": [
            {"title": "Deadline", "value": _nice_date(p["deadline"])},
            {"title": "Routed to", "value": _routing(p, doc)},
        ]},
        _text("Changes", weight="Bolder", size="Small", isSubtle=True, separator=True,
              spacing="Medium"),
        {"type": "RichTextBlock", "spacing": "Small",
         "inlines": _diff_inlines(params.get("old_content", doc["content"]), p["new_content"])},
    ]
    full_text = {"type": "Action.ShowCard", "title": "View full text", "card": _card([
        _text("Proposed text", weight="Bolder", size="Small", isSubtle=True),
        _text(p["new_content"])])}
    if status == "approved":
        body.append(_text(f"Binding. {doc['title']} is v{doc['version']}, approved by "
                          f"{_name(p['approved_by'])} and recorded in History.",
                          size="Small", color="Good", spacing="Medium"))
        return _card(body, [full_text])
    if status == "rejected":
        body.append(_text("Not approved: not binding.", size="Small", color="Attention",
                          spacing="Medium"))
        return _card(body, [full_text])
    data = {"proposal_id": p["proposal_id"], "doc_id": p["doc_id"]}
    return _card(body, [
        {"type": "Action.Submit", "title": "Approve", "style": "positive",
         "data": {"action": "approve", **data}},
        {"type": "Action.Submit", "title": "Reject", "data": {"action": "reject", **data}},
        full_text,
    ])


def propose_form_card(params):
    doc = db.get_doc(params["doc_id"])
    dependents = db.get_dependent_teams(doc["team"])
    route = (f"{dependents[0]}, because {dependents[0]} depends on {doc['team']}"
             if dependents else f"{doc['team']}, because no other team depends on it")
    return _card([
        _text("New proposal", size="Small", weight="Bolder", color="Accent"),
        _text(doc["title"], size="Large", weight="Bolder", spacing="Small"),
        _text(f"Current: v{doc['version']}, approved by {_name(doc['approver'])}",
              isSubtle=True, size="Small", spacing="None"),
        {"type": "Input.Text", "id": "summary", "label": "What changed and why",
         "value": params.get("summary", ""), "isRequired": True,
         "placeholder": "e.g. Cutover moved two weeks per cutover sync on Oct 9",
         "errorMessage": "Add a short summary"},
        {"type": "Input.Text", "id": "new_content", "label": "Updated requirement text",
         "isMultiline": True, "value": doc["content"], "isRequired": True,
         "errorMessage": "Enter the new text"},
        {"type": "Input.Date", "id": "deadline", "label": "Approval needed by",
         "value": (date.today() + timedelta(days=7)).isoformat(), "isRequired": True},
        _text(f"Spot will route this to {route}.", isSubtle=True, size="Small"),
    ], [{"type": "Action.Submit", "title": "Submit for approval", "style": "positive",
         "data": {"action": "submit_proposal", "doc_id": doc["doc_id"]}}])


def doc_picker_card(params):
    return _card([
        _text(params["prompt"], weight="Bolder"),
        {"type": "Input.ChoiceSet", "id": "doc_id", "style": "compact", "isRequired": True,
         "value": params["docs"][0]["doc_id"],
         "choices": [{"title": d["title"], "value": d["doc_id"]} for d in params["docs"]]},
    ], [{"type": "Action.Submit", "title": "Continue",
         "data": {"action": params["next"], "summary": params.get("summary", "")}}])


def history_card(params):
    doc = db.get_doc(params["doc_id"])
    body = [
        _text("History", size="Small", weight="Bolder", color="Accent"),
        _text(doc["title"], size="Large", weight="Bolder", spacing="Small"),
        _text(f"{doc['team']} · current v{doc['version']}, approved by {_name(doc['approver'])}",
              isSubtle=True, size="Small", spacing="None"),
    ]
    for i, h in enumerate(db.get_history(doc["doc_id"])):
        meta = (f"Changed by {_name(h['changed_by'])} · approved by {_name(h['approved_by'])} · "
                f"{_nice_date(h['changed_at'])}")
        if h["deadline"]:
            meta += f" · deadline {_nice_date(h['deadline'])}"
        body.append({"type": "ColumnSet", "separator": True, "spacing": "Medium", "columns": [
            {"type": "Column", "width": "44px", "items": [
                _text(f"v{h['version']}", weight="Bolder", size="Medium",
                      color="Good" if i == 0 else "Default")]},
            {"type": "Column", "width": "stretch", "items": [
                _text(h["summary"] + ("  ·  Current" if i == 0 else ""), weight="Bolder"),
                _text(meta, isSubtle=True, size="Small", spacing="None")]},
        ]})
    if not any(h["version"] == 1 for h in db.get_history(doc["doc_id"])):
        current = doc["version"] == 1
        body.append({"type": "ColumnSet", "separator": True, "spacing": "Medium", "columns": [
            {"type": "Column", "width": "44px", "items": [
                _text("v1", weight="Bolder", size="Medium", color="Good" if current else "Default")]},
            {"type": "Column", "width": "stretch", "items": [
                _text("Original approved version" + ("  ·  Current" if current else ""), weight="Bolder"),
                _text(f"Author {_name(doc['author'])}" + (f" · approved by {_name(doc['approver'])}"
                                                        if current else ""),
                      isSubtle=True, size="Small", spacing="None")]},
        ]})
    not_binding = [p for p in db.get_proposals(doc["doc_id"]) if p["status"] != "approved"]
    if not_binding:
        body.append(_text("Not approved: not binding", weight="Bolder", color="Attention",
                          separator=True, spacing="Large"))
        for p in not_binding:
            body.append(_text(f"{p['status'].capitalize()}: {p['summary']}", spacing="Small"))
            body.append(_text(f"Proposed by {_name(p['proposed_by'])} · needs {p['required_team']} · "
                              f"deadline {_nice_date(p['deadline'])}. Not approved: not binding.",
                              isSubtle=True, size="Small", spacing="None"))
    return _card(body)


def answer_card(params):
    body = [_text(params["answer"])]
    if params["sources"]:
        body.append(_text("Sources", size="Small", weight="Bolder", isSubtle=True,
                          separator=True, spacing="Medium"))
        for i, s in enumerate(params["sources"][:4], 1):
            body.append({"type": "RichTextBlock", "spacing": "Small", "inlines": [
                {"type": "TextRun", "text": f"[{i}] ", "color": "Accent", "weight": "Bolder"},
                {"type": "TextRun", "text": s["title"], "weight": "Bolder"},
                {"type": "TextRun", "text": f"  v{s['version']} · by {_name(s['author'])} · "
                                            f"approved by {_name(s['approver'])}",
                 "isSubtle": True, "size": "Small"},
            ]})
    body.append(_text("Answered from approved documents only. Pending proposals are never used.",
                      isSubtle=True, size="Small", spacing="Medium"))
    return _card(body)


def help_card(params):
    return _card([
        _text("What Spot can do", size="Large", weight="Bolder"),
        {"type": "FactSet", "facts": [
            {"title": "@Spot add", "value": "Reply to a message to turn its decision into a proposal"},
            {"title": "@Spot propose <doc>", "value": "Propose a change to one of your team's docs"},
            {"title": "@Spot ask <question>", "value": "Ask about approved docs, with citations"},
            {"title": "@Spot history <doc>", "value": "Approved versions, and what isn't binding"},
            {"title": "@Spot pending", "value": "Changes waiting for approval"},
        ]},
        _text("A change only becomes binding when an Approver on the dependent team approves it.",
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


def _picker(docs, prompt, next_action, summary=""):
    return {"kind": "doc_picker", "params": {
        "prompt": prompt, "next": next_action, "summary": summary,
        "docs": [{"doc_id": d["doc_id"], "title": d["title"]} for d in docs]}}


def _start_proposal(user, loc, post, context, summary):
    me = db.get_user(user)
    if me["role"] not in ("Contributor", "Approver"):
        _post(loc, "spot", f"{_name(user)}, you're a **{me['role']}** on {me['team']}, so you can't "
                           "propose changes. Ask a Contributor or Approver.", parent=post)
        return
    own = [d for d in db.get_docs_for_user(user) if d["team"] == me["team"]]
    doc = _match_doc(own, context)
    if doc:
        _post(loc, "spot", kind="propose_form", parent=post,
              params={"doc_id": doc["doc_id"], "summary": summary})
    else:
        _post(loc, "spot", parent=post, **_picker(own, "Which doc does this change?",
                                                   "pick_propose", summary))


def handle_command(user, loc, text, post, parent_text=""):
    command = re.sub(r"@spot\b", "", text, flags=re.I).strip()
    word, _, rest = command.partition(" ")
    word = word.lower()
    if word in ("", "help"):
        _post(loc, "spot", kind="help", parent=post)
    elif word == "add":
        summary = rest or parent_text.split(". ")[0][:120]
        _start_proposal(user, loc, post, f"{rest} {parent_text}", summary)
    elif word == "propose":
        _start_proposal(user, loc, post, rest, "")
    elif word == "history":
        docs = db.get_docs_for_user(user)
        doc = _match_doc(docs, rest)
        if doc:
            _post(loc, "spot", kind="history", params={"doc_id": doc["doc_id"]}, parent=post)
        else:
            _post(loc, "spot", parent=post, **_picker(docs, "Which doc's history?", "pick_history"))
    elif word == "pending":
        pending = db.get_pending()
        if not pending:
            _post(loc, "spot", "Nothing is waiting for approval.", parent=post)
        for p in pending:
            _post(loc, "spot", kind="proposal", params=_proposal_params(p), parent=post)
    else:
        question = rest if word == "ask" else command
        try:
            result = rag.ask(user, question)
        except Exception as e:  # keep the demo alive if the LLM call fails
            _post(loc, "spot", f"Sorry, I couldn't reach the language model ({e}).", parent=post)
            return
        _post(loc, "spot", kind="answer", params=result, parent=post)


def _submit_proposal(user, data):
    doc = db.get_doc(data["doc_id"])
    if data.get("new_content", "").strip() == doc["content"].strip():
        raise ValueError("Nothing changed. Edit the requirement text before submitting.")
    pid = governance.propose(user, doc["doc_id"], data["new_content"], data["summary"],
                             data["deadline"])
    return _proposal(pid, doc["doc_id"]), doc


def handle_action(user, loc, message_id, data):
    """Runs a card button. Returns an error string, or None on success."""
    action = data.get("action")
    if loc == "spot-app":  # cards in the Spot app's Pending and History views
        view = SPOT_VIEW.setdefault(user, {})
        if action == "pick_propose":
            view.update(propose_doc=data["doc_id"], propose_summary=data.get("summary", ""))
        elif action == "pick_history":
            view["history_doc"] = data["doc_id"]
        elif action == "submit_proposal":
            p, doc = _submit_proposal(user, data)
            view.pop("propose_doc", None)
            _announce(p)
        elif action == "approve":
            governance.approve(user, data["proposal_id"])
        elif action == "reject":
            governance.reject(user, data["proposal_id"])
        return None

    post, msg = _find(loc, message_id)
    if action == "pick_propose":
        msg.update(kind="propose_form", params={"doc_id": data["doc_id"],
                                                "summary": data.get("summary", "")})
    elif action == "pick_history":
        msg.update(kind="history", params={"doc_id": data["doc_id"]})
    elif action == "submit_proposal":
        p, doc = _submit_proposal(user, data)
        msg.update(kind="proposal", params=_proposal_params(p) | {"old_content": doc["content"]},
                   text=f"Proposal created: {p['summary']}. Routed to {_routing(p, doc)}.")
        _announce(p, skip_loc=loc)
    elif action == "approve":
        version = governance.approve(user, data["proposal_id"])
        doc = db.get_doc(data["doc_id"])
        _post(loc, "spot", f"**{_name(user)}** approved. **{doc['title']}** is now **v{version}** "
                           "and recorded in History.", parent=post)
    elif action == "reject":
        governance.reject(user, data["proposal_id"])
        _post(loc, "spot", f"**{_name(user)}** rejected this change. It is not binding.",
              parent=post)
    return None


# ---------------------------------------------------------------------------
# HTTP API for static/spot.js
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder="static", static_url_path="/static")


def _render(msg):
    out = {k: msg[k] for k in ("id", "author", "text", "ts", "kind")}
    out["card"] = CARDS[msg["kind"]](msg["params"]) if msg["kind"] in CARDS else None
    return out


def _view(user, loc):
    SEEN[(user, loc)] = len(_posts(loc))
    return [dict(_render(p), replies=[_render(r) for r in p["replies"]]) for p in _posts(loc)]


def _unread(user, loc):
    return SEEN.get((user, loc), BASELINE.get(loc, 1)) < len(_posts(loc))


def _activity(user):
    me = db.get_user(user)
    items = []
    for p in db.get_pending():
        if p["required_team"] != me["team"]:
            continue
        loc = next((l for l, posts in POSTS.items() if _can_see(user, l) and any(
            m.get("params", {}).get("proposal_id") == p["proposal_id"]
            for post in posts for m in [post] + post["replies"])), TEAM_HOME.get(me["team"]))
        doc = db.get_doc(p["doc_id"])
        items.append({"location": loc, "summary": p["summary"], "doc": doc["title"],
                      "proposed_by": _name(p["proposed_by"]), "ts": p["created_at"]})
    return sorted(items, key=lambda a: a["ts"], reverse=True)


def _state(user):
    people = {u: _user(u) for u in workspace.ALL_USERS + ["spot"]}
    teams = [{"id": t["id"], "name": t["name"], "avatar_color": t["avatar_color"],
              "channels": [dict(c, location=f"channel:{c['id']}",
                                unread=_unread(user, f"channel:{c['id']}"))
                           for c in t["channels"]]}
             for t in _channels_for(user)]
    chats = [{"location": f"spot:{user}", "name": "Spot", "kind": "bot", "members": ["spot"]}]
    for c in _chats_for(user):
        others = [m for m in c["members"] if m != user]
        chats.append({"location": f"chat:{c['id']}", "kind": c["kind"], "members": c["members"],
                      "name": c["name"] or ", ".join(_name(m) for m in others)})
    for c in chats:
        posts = _posts(c["location"])
        last = posts[-1] if posts else None
        if last and last["replies"]:
            last = last["replies"][-1]
        c["unread"] = _unread(user, c["location"])
        c["preview"] = last and {"author": last["author"], "ts": last["ts"],
                                 "text": last["text"] or "Sent a card"}
    return {"me": _user(user), "org": workspace.ORG_NAME, "people": people,
            "switcher": CORE_USERS + [u for u in workspace.ALL_USERS if u not in CORE_USERS],
            "teams": teams, "chats": chats, "activity": _activity(user)}


def _spot_items(user, tab):
    view = SPOT_VIEW.setdefault(user, {})
    if tab == "pending":
        me = db.get_user(user)
        items = []
        if me["role"] in ("Contributor", "Approver"):
            if view.get("propose_doc"):
                items.append({"id": "propose", "card": propose_form_card(
                    {"doc_id": view["propose_doc"], "summary": view.get("propose_summary", "")})})
            else:
                own = [d for d in db.get_docs_for_user(user) if d["team"] == me["team"]]
                items.append({"id": "propose", "card": doc_picker_card(_picker(
                    own, "Propose a change to one of your team's docs", "pick_propose")["params"])})
        items += [{"id": p["proposal_id"], "card": proposal_card(_proposal_params(p))}
                  for p in db.get_pending()]
        return items
    docs = db.get_docs_for_user(user)
    ids = [d["doc_id"] for d in docs]
    doc_id = view.get("history_doc") or ("ops-uae-identity" if "ops-uae-identity" in ids else ids[0])
    picker = _picker(docs, "Pick a document", "pick_history")["params"]
    picker["docs"].sort(key=lambda d: d["doc_id"] != doc_id)
    return [{"id": "history-picker", "card": doc_picker_card(picker)},
            {"id": "history", "card": history_card({"doc_id": doc_id})}]


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/state")
def api_state():
    return jsonify(_state(request.args["user"]))


@app.get("/api/location")
def api_location():
    user, loc = request.args["user"], request.args["loc"]
    if not _can_see(user, loc):
        return jsonify({"posts": [], "error": "You're not a member of this conversation."})
    return jsonify({"posts": _view(user, loc)})


@app.get("/api/spot/<tab>")
def api_spot(tab):
    return jsonify({"items": _spot_items(request.args["user"], tab)})


@app.post("/api/post")
def api_post():
    body = request.get_json()
    user, loc, text = body["user"], body["loc"], body["text"].strip()
    parent = None
    if body.get("parent_id"):
        parent, _ = _find(loc, body["parent_id"])
    post = _post(loc, user, text, parent=parent)
    if loc.startswith("spot:") or re.search(r"@spot\b", text, flags=re.I):
        handle_command(user, loc, text, parent or post,
                       parent_text=parent["text"] if parent else "")
    return jsonify({"posts": _view(user, loc)})


@app.post("/api/action")
def api_action():
    body = request.get_json()
    user, loc = body["user"], body["loc"]
    try:
        error = handle_action(user, loc, body["message_id"], body["data"])
    except (PermissionError, ValueError) as e:
        error = str(e)
    posts = [] if loc == "spot-app" else _view(user, loc)
    return jsonify({"posts": posts, "error": error})


@app.post("/api/reset")
def api_reset():
    db.reset()
    reset_ui()
    return jsonify({"ok": True})


def main():
    db.reset()  # every start is a clean demo
    reset_ui()
    app.run(host="127.0.0.1", port=8501, debug=False)


if __name__ == "__main__":
    main()
