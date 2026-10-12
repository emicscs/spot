"""Streamlit UI for Spot. Owner: Contributor 1. See CONTRACTS.md.

Run: streamlit run app.py
Tabs: Pending, History, Chat. Sidebar: user picker, team/role, Reset demo.
Build against fake return values first; swap in real imports
(db, governance, rag) at integration.
"""


def render_sidebar():
    """Sidebar: user picker (4 users), shows team and role, Reset demo button.
    Returns the selected user name (str)."""
    raise NotImplementedError


def render_pending(user):
    """Pending tab: proposals with old vs new content, summary, deadline,
    routing line, Approve/Reject buttons (show PermissionError reason),
    and a Propose change form. Returns None."""
    raise NotImplementedError


def render_history(user):
    """History tab: pick a doc, show approved versions, then pending/rejected
    proposals labeled "Not approved: not binding." Returns None."""
    raise NotImplementedError


def render_chat(user):
    """Chat tab: question box, calls rag.ask, shows answer and sources. Returns None."""
    raise NotImplementedError


def main():
    """Page setup, sidebar, and the three tabs. Returns None."""
    raise NotImplementedError


if __name__ == "__main__":
    pass
