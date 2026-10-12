"""Streamlit UI for Spot. Owner: Frankie. See CONTRACTS.md.

Run: streamlit run app.py
Tabs: Pending, History, Chat. Sidebar: user picker, team/role, Reset demo.
Build against fake return values first; swap in real imports
(db, governance, rag) at integration.
"""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import streamlit as st

# Flip to False at integration (1:05) to use the real db, governance and rag.
USE_FAKES = True


# ---------------------------------------------------------------------------
# Fake backend: same signatures and return shapes as CONTRACTS.md, kept in
# st.session_state so propose/approve/reject actually change what you see.
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


def _store():
    if "fake" not in st.session_state:
        st.session_state.fake = _fake_seed()
    return st.session_state.fake


def _fake_get_user(name):
    return FAKE_USERS.get(name)


def _fake_get_doc(doc_id):
    d = _store()["docs"].get(doc_id)
    return dict(d) if d else None


def _fake_get_docs_for_user(name):
    user = _fake_get_user(name)
    teams = {user["team"]} | {dep for t, dep in _store()["deps"] if t == user["team"]}
    return [dict(d) for d in _store()["docs"].values() if d["team"] in teams]


def _fake_get_history(doc_id):
    rows = [dict(h) for h in _store()["history"] if h["doc_id"] == doc_id]
    return sorted(rows, key=lambda h: h["version"], reverse=True)


def _fake_get_proposals(doc_id):
    return [dict(p) for p in _store()["proposals"] if p["doc_id"] == doc_id]


def _fake_get_pending():
    return [dict(p) for p in _store()["proposals"] if p["status"] == "pending"]


def _fake_get_dependent_teams(team):
    return [t for t, dep in _store()["deps"] if dep == team]


def _fake_reset():
    st.session_state.pop("fake", None)


def _fake_propose(user, doc_id, new_content, summary, deadline):
    u, doc = _fake_get_user(user), _store()["docs"][doc_id]
    if u["role"] not in ("Contributor", "Approver"):
        raise PermissionError(f"{user} is a {u['role']}; only Contributors and Approvers can propose")
    if u["team"] != doc["team"]:
        raise PermissionError(f"Only {doc['team']} can propose changes to {doc['title']}")
    dependents = _fake_get_dependent_teams(doc["team"])
    proposal_id = str(uuid.uuid4())
    _store()["proposals"].append({
        "proposal_id": proposal_id, "doc_id": doc_id, "new_content": new_content,
        "summary": summary, "deadline": deadline, "proposed_by": user,
        "required_team": dependents[0] if dependents else doc["team"],
        "status": "pending", "approved_by": None, "created_at": _now(),
    })
    return proposal_id


def _fake_check_reviewer(user, p):
    u, doc = _fake_get_user(user), _store()["docs"][p["doc_id"]]
    if p["status"] != "pending":
        raise PermissionError(f"This proposal is already {p['status']}")
    if u["team"] != p["required_team"]:
        why = (f"{p['required_team']} depends on {doc['team']}"
               if p["required_team"] != doc["team"] else "no other team depends on it")
        raise PermissionError(f"Only {p['required_team']} can approve: {why}")
    if u["role"] != "Approver":
        raise PermissionError(f"{user} is a {u['role']}; only Approvers can approve or reject")


def _fake_find(proposal_id):
    return next(p for p in _store()["proposals"] if p["proposal_id"] == proposal_id)


def _fake_approve(user, proposal_id):
    p = _fake_find(proposal_id)
    _fake_check_reviewer(user, p)
    doc = _store()["docs"][p["doc_id"]]
    doc.update(content=p["new_content"], version=doc["version"] + 1,
               approver=user, updated_at=_now())
    _store()["history"].append({
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


def _fake_ask(user, question):
    def tokens(text):
        return {w.strip("?.,:").lower() for w in text.split() if len(w) > 3}

    words = tokens(question)
    scored = [(len(words & tokens(d["title"] + " " + line)), line, d)
              for d in _fake_get_docs_for_user(user) for line in d["content"].splitlines()]
    score, line, d = max(scored, key=lambda s: s[0], default=(0, None, None))
    if score < 2:
        return {"answer": "That isn't in your documents.", "sources": []}
    source = {k: d[k] for k in ("doc_id", "title", "version", "author", "approver")}
    return {"answer": f"{line} ({d['title']}, v{d['version']}, "
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
# UI
# ---------------------------------------------------------------------------

def render_sidebar():
    """Sidebar: user picker (4 users), shows team and role, Reset demo button.
    Returns the selected user name (str)."""
    return "dave"


def render_pending(user):
    """Pending tab: proposals with old vs new content, summary, deadline,
    routing line, Approve/Reject buttons (show PermissionError reason),
    and a Propose change form. Returns None."""
    st.info("Approvals: coming next")


def render_history(user):
    """History tab: pick a doc, show approved versions, then pending/rejected
    proposals labeled "Not approved: not binding." Returns None."""
    st.info("History: coming next")


def render_chat(user):
    """Chat tab: question box, calls rag.ask, shows answer and sources. Returns None."""
    st.info("Ask Spot: coming next")


def main():
    """Page setup, sidebar, and the three tabs. Returns None."""
    st.set_page_config(page_title="Spot", page_icon="📍", layout="wide")
    user = render_sidebar()
    approvals, history, chat = st.tabs(["Approvals", "History", "Ask Spot"])
    with approvals:
        render_pending(user)
    with history:
        render_history(user)
    with chat:
        render_chat(user)


if __name__ == "__main__":
    main()
