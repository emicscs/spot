"""Streamlit UI for Spot. Owner: Contributor 1. See CONTRACTS.md.

Run: streamlit run app.py
Tabs: Pending, History, Chat. Sidebar: user picker, team/role, Reset demo.
Build against fake return values first; swap in real imports
(db, governance, rag) at integration.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from html import escape
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
    with st.sidebar:
        st.caption("DEMO CONTROLS (not part of Teams)")
        user = st.selectbox("Signed in as", USERS, key="user")
        info = db.get_user(user)
        st.markdown(f"**{info['team']}** · {info['role']}")
        if st.button("Reset demo", width="stretch"):
            db.reset()
            for key in list(st.session_state):
                if key.startswith("chat_"):
                    del st.session_state[key]
            st.toast("Demo data reset")
    return user


def render_pending(user):
    """Pending tab: proposals with old vs new content, summary, deadline,
    routing line, Approve/Reject buttons (show PermissionError reason),
    and a Propose change form. Returns None."""
    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)
    render_propose_form(user)
    pending = db.get_pending()
    if not pending:
        st.caption("No pending proposals.")
    for p in pending:
        render_proposal_card(user, p)


def routing_line(p, doc):
    """Human-readable reason a proposal went to its required_team."""
    if p["required_team"] != doc["team"]:
        return f"Routed to: {p['required_team']} (depends on {doc['team']})"
    return f"Routed to: {p['required_team']} (no other team depends on it)"


def render_proposal_card(user, p):
    doc = db.get_doc(p["doc_id"])
    with st.container(border=True, key=f"card_{p['proposal_id']}"):
        facts = [("Document", doc["title"]), ("Proposed by", p["proposed_by"]),
                 ("Deadline", p["deadline"] or "none"),
                 ("Routed to", routing_line(p, doc).removeprefix("Routed to: "))]
        st.markdown(
            f'<div class="ac-head"><span>📍 Spot</span><span>{escape(p["created_at"][:10])}</span></div>'
            f'<div class="ac-title">Approval requested from {escape(p["required_team"])}</div>'
            f'<div class="ac-sub">{escape(p["summary"])}</div>'
            '<table class="ac-facts">' + "".join(
                f"<tr><td>{k}</td><td>{escape(str(v))}</td></tr>" for k, v in facts)
            + "</table>",
            unsafe_allow_html=True)
        old_html, new_html = diff_html(doc["content"], p["new_content"])
        old, new = st.columns(2)
        old.markdown(f'<div class="ac-doc">Current (v{doc["version"]}, approved)</div>{old_html}',
                     unsafe_allow_html=True)
        new.markdown(f'<div class="ac-doc">Proposed</div>{new_html}', unsafe_allow_html=True)
        approve_col, reject_col, _ = st.columns([1, 1, 8], gap="small")
        action = None
        if approve_col.button("Approve", key=f"approve_{p['proposal_id']}", type="primary"):
            action = "approve"
        if reject_col.button("Reject", key=f"reject_{p['proposal_id']}"):
            action = "reject"
        if action:
            try:
                if action == "approve":
                    version = governance.approve(user, p["proposal_id"])
                    st.session_state.flash = (f"Approved by {user}: {doc['title']} "
                                              f"is now v{version}")
                else:
                    governance.reject(user, p["proposal_id"])
                    st.session_state.flash = f"Rejected by {user}: {p['summary']}"
            except PermissionError as e:
                st.error(f"Blocked: {e}")
            else:
                st.rerun()


def render_propose_form(user):
    me = db.get_user(user)
    with st.expander("Propose a change"):
        if me["role"] not in ("Contributor", "Approver"):
            st.caption(f"{user} is a {me['role']} and can't propose changes.")
            return
        own = {d["doc_id"]: d for d in db.get_docs_for_user(user) if d["team"] == me["team"]}
        doc_id = st.selectbox("Doc", list(own), key="propose_doc",
                              format_func=lambda i: f"{own[i]['title']} (v{own[i]['version']})")
        doc = own[doc_id]
        with st.form(f"propose_{doc_id}_v{doc['version']}", clear_on_submit=True):
            content = st.text_area("New content", value=doc["content"], height=150)
            summary = st.text_input("Summary of the change")
            deadline = st.date_input("Approval deadline", value=date.today() + timedelta(days=7))
            if st.form_submit_button("Propose", type="primary"):
                if not summary.strip() or content.strip() == doc["content"].strip():
                    st.warning("Change the content and add a summary.")
                    return
                try:
                    pid = governance.propose(user, doc_id, content, summary, deadline.isoformat())
                except PermissionError as e:
                    st.error(f"Blocked: {e}")
                    return
                routed = next(p for p in db.get_pending() if p["proposal_id"] == pid)
                st.session_state.flash = (f"Proposal sent. "
                                          f"{routing_line(routed, doc)}")
                st.rerun()


def render_history(user):
    """History tab: pick a doc, show approved versions, then pending/rejected
    proposals labeled "Not approved: not binding." Returns None."""
    docs = {d["doc_id"]: d for d in db.get_docs_for_user(user)}
    if not docs:
        st.caption("No documents visible to you.")
        return
    doc_id = st.selectbox("Document", list(docs), key="history_doc",
                          format_func=lambda i: f"{docs[i]['title']} ({docs[i]['team']})")
    doc = docs[doc_id]
    st.markdown(f"**Current: v{doc['version']}**, approved by {doc['approver']}")

    st.markdown("##### Approved versions")
    st.dataframe(
        [{"Version": h["version"], "Changed by": h["changed_by"],
          "Approved by": h["approved_by"], "Summary": h["summary"],
          "Deadline": h["deadline"] or "", "Date": (h["changed_at"] or "")[:10]}
         for h in db.get_history(doc_id)],
        hide_index=True, width="stretch")

    open_or_rejected = [p for p in db.get_proposals(doc_id) if p["status"] != "approved"]
    if open_or_rejected:
        st.markdown("##### Not approved: not binding")
        for p in open_or_rejected:
            with st.container(border=True):
                st.markdown(f"**{p['status'].capitalize()}** · Not approved: not binding.")
                st.caption(f"{p['summary']} · proposed by {p['proposed_by']} · "
                           f"needs {p['required_team']} · deadline {p['deadline']}")


def render_chat(user):
    """Chat tab: question box, calls rag.ask, shows answer and sources. Returns None."""
    log = st.session_state.setdefault(f"chat_{user}", [])
    st.caption("Answers come only from approved documents you can see. "
               "Pending proposals are never used.")
    with st.form("ask_form", clear_on_submit=True):
        question = st.text_input("Ask Spot", placeholder="What is the cutover date for "
                                                         "the UAE identity service?")
        if st.form_submit_button("Ask", type="primary") and question.strip():
            with st.spinner("Reading approved docs..."):
                log.append({"question": question, **rag.ask(user, question)})
    for turn in reversed(log):
        with st.chat_message("user"):
            st.markdown(turn["question"])
        with st.chat_message("assistant", avatar="📍"):
            st.markdown(turn["answer"])
            if turn["sources"]:
                st.markdown("".join(
                    f'<span class="chip">📄 {escape(s["title"])} · v{s["version"]} · '
                    f'by {escape(s["author"])} · approved by {escape(str(s["approver"]))}</span>'
                    for s in turn["sources"]), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Teams look: fake Teams shell around the app. Cosmetic only; cut first.
# ---------------------------------------------------------------------------

TEAMS_CSS = """<style>
html, body, [class*="css"], .stApp, button, input, textarea {
  font-family: "Segoe UI", -apple-system, "Helvetica Neue", Arial, sans-serif; }
#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stToolbarActions"],
[data-testid="stAppDeployButton"] { display: none; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding: 2.6rem 1.5rem 2rem; max-width: 100%; }
[data-testid="stSidebar"] { background: #E1DFDD; border-right: 2px dashed #A19F9D; }
.t-top { display: flex; align-items: center; gap: 16px; background: #464775; color: #fff;
  margin: -1.2rem -1rem 0.8rem; padding: 8px 16px; border-radius: 6px; }
.t-brand { font-weight: 600; font-size: 14px; white-space: nowrap; }
.t-search { flex: 1; max-width: 520px; margin: 0 auto; background: #ffffff26; border-radius: 4px;
  padding: 5px 12px; font-size: 13px; color: #ffffffcc; }
.t-me { width: 30px; height: 30px; border-radius: 50%; background: #E8EBFA; color: #464775;
  display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 12px; }
.t-rail { display: flex; flex-direction: column; gap: 6px; background: #EBEBEB;
  border-radius: 6px; padding: 8px 0; }
.t-ri { position: relative; text-align: center; font-size: 10px; color: #616161; padding: 6px 0; }
.t-ri .ico { display: block; font-size: 20px; filter: grayscale(1); }
.t-ri.on { color: #5B5FC7; font-weight: 600; border-left: 3px solid #5B5FC7; }
.t-ri.on .ico { filter: none; }
.t-badge { position: absolute; top: 2px; right: 22%; background: #C4314B; color: #fff;
  border-radius: 8px; font-size: 10px; padding: 0 5px; font-weight: 700; }
.t-app { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.t-logo { width: 32px; height: 32px; border-radius: 6px; background: #5B5FC7; color: #fff;
  display: flex; align-items: center; justify-content: center; font-weight: 700; }
.t-title { font-weight: 700; font-size: 18px; line-height: 1.1; }
.t-sub { font-size: 12px; color: #616161; }
.stTabs [data-baseweb="tab-list"] { gap: 20px; border-bottom: 1px solid #E0E0E0; }
.stTabs [data-baseweb="tab"] { font-weight: 600; }
[class*="st-key-card_"] { background: #fff; border-radius: 8px !important;
  box-shadow: 0 2px 4px #00000024; border: 1px solid #E0E0E0 !important; }
.ac-head { display: flex; justify-content: space-between; font-size: 12px; color: #616161; }
.ac-title { font-size: 16px; font-weight: 700; margin-top: 4px; }
.ac-sub { font-size: 14px; margin: 2px 0 8px; }
.ac-facts td { padding: 2px 16px 2px 0; font-size: 13px; border: none; vertical-align: top; }
.ac-facts td:first-child { font-weight: 600; white-space: nowrap; }
.ac-facts table, .ac-facts tr { border: none; }
.ac-doc { font-size: 12px; font-weight: 600; color: #616161; margin-bottom: 2px; }
.ac-pre { background: #FAFAFA; border: 1px solid #E0E0E0; border-radius: 4px; padding: 8px;
  font-family: Consolas, monospace; font-size: 13px; white-space: pre-wrap; }
.ac-pre .del { background: #FDE7E9; text-decoration: line-through; }
.ac-pre .add { background: #E7F2DA; }
.chip { display: inline-block; background: #E8EBFA; color: #464775; border-radius: 12px;
  padding: 2px 10px; font-size: 12px; margin: 2px 4px 0 0; }
</style>"""


def render_top_bar(me):
    initials = me["name"][:2].upper()
    st.markdown(
        '<div class="t-top"><div class="t-brand">Teams</div>'
        '<div class="t-search">🔍 Search</div>'
        f'<div class="t-me" title="{me["name"]}">{initials}</div></div>',
        unsafe_allow_html=True)


def render_rail(me):
    waiting = sum(1 for p in db.get_pending() if p["required_team"] == me["team"])
    badge = f'<span class="t-badge">{waiting}</span>' if waiting else ""
    items = [("🔔", "Activity", badge, ""), ("💬", "Chat", "", ""), ("👥", "Teams", "", ""),
             ("📅", "Calendar", "", ""), ("📍", "Spot", "", " on")]
    st.markdown(
        '<div class="t-rail">' + "".join(
            f'<div class="t-ri{on}"><span class="ico">{ico}</span>{label}{b}</div>'
            for ico, label, b, on in items) + "</div>",
        unsafe_allow_html=True)


def render_app_header(me):
    st.markdown(
        '<div class="t-app"><div class="t-logo">S</div><div>'
        '<div class="t-title">Spot</div>'
        f'<div class="t-sub">Requirements version control · {escape(me["team"])}</div>'
        '</div></div>',
        unsafe_allow_html=True)


def diff_html(old, new):
    """Old and new content as two <div>s, changed lines highlighted."""
    old_lines, new_lines = old.splitlines(), new.splitlines()

    def block(lines, other, cls):
        return '<div class="ac-pre">' + "<br>".join(
            f'<span class="{cls}">{escape(l)}</span>' if l not in other else escape(l)
            for l in lines) + "</div>"

    return block(old_lines, set(new_lines), "del"), block(new_lines, set(old_lines), "add")


def main():
    """Page setup, sidebar, and the three tabs. Returns None."""
    st.set_page_config(page_title="Spot", page_icon="📍", layout="wide")
    st.markdown(TEAMS_CSS, unsafe_allow_html=True)
    user = render_sidebar()
    me = db.get_user(user)
    render_top_bar(me)
    rail, body = st.columns([1, 13], gap="small")
    with rail:
        render_rail(me)
    with body:
        render_app_header(me)
        approvals, history, chat = st.tabs(["Approvals", "History", "Ask Spot"])
        with approvals:
            render_pending(user)
        with history:
            render_history(user)
        with chat:
            render_chat(user)


if __name__ == "__main__":
    main()
