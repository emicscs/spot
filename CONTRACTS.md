# CONTRACTS.md — Frozen contract (nobody changes it)

Users (hardcoded dict in db.py):
- alice: team "Ops Automation", role "Approver"
- bob: team "Ops Automation", role "Contributor"
- carol: team "Payments", role "Reader"
- dave: team "Payments", role "Approver"

SQLite tables:
- docs(doc_id TEXT PRIMARY KEY, title TEXT, team TEXT, content TEXT, version INTEGER, author TEXT, approver TEXT, updated_at TEXT): approved content only
- proposals(proposal_id TEXT PRIMARY KEY, doc_id TEXT, new_content TEXT, summary TEXT, deadline TEXT, proposed_by TEXT, required_team TEXT, status TEXT, approved_by TEXT, created_at TEXT): status is "pending" | "approved" | "rejected"
- history(doc_id TEXT, version INTEGER, content TEXT, changed_by TEXT, approved_by TEXT, summary TEXT, deadline TEXT, changed_at TEXT): one row per approved change
- team_dependencies(team TEXT, depends_on TEXT): "team depends on depends_on". Seed: ("Payments", "Ops Automation")

Function signatures and return shapes:
- db.py
  - get_conn() -> sqlite3.Connection with row_factory = sqlite3.Row
  - execute(sql, params=()) and query(sql, params=()) -> shared helpers; query returns a list of dicts
  - get_user(name) -> {"name", "team", "role"} or None
  - get_docs_for_user(name) -> list of doc dicts (keys = docs columns)
  - get_doc(doc_id) -> doc dict or None
  - get_history(doc_id) -> list of history dicts, newest first
  - get_proposals(doc_id) -> list of proposal dicts (all statuses)
  - get_pending() -> list of pending proposal dicts
  - get_dependent_teams(team) -> list of team names that depend on `team`
  - reset() -> drops and recreates all tables, then calls seed.seed()
- governance.py
  - propose(user, doc_id, new_content, summary, deadline) -> proposal_id
  - approve(user, proposal_id) -> new version (int)
  - reject(user, proposal_id) -> None
  - All permission failures raise PermissionError with a human-readable reason, e.g. "Only Payments can approve: Payments depends on Ops Automation"
  - approve() does all its writes in one transaction
- rag.py
  - ask(user, question) -> {"answer": str, "sources": [{"doc_id", "title", "version", "author", "approver"}]}
- seed.py
  - seed() -> inserts seed docs, the dependency row, and one pending proposal (uses db.execute)

Rules:
- Readers see docs from their own team and from teams their team depends on.
- Contributors and Approvers can propose changes to their own team's docs.
- A proposal is routed to the teams that depend on the doc's team (required_team = first dependent team). If none, it goes to the doc's own team.
- Only an Approver on required_team can approve or reject. A team cannot approve its own change when another team depends on it.
- Docs change only through approve().

Conventions (from the stack):
- Use uuid4 strings for proposal_id.
- Store dates and timestamps as ISO 8601 strings.
- Always use parameterized queries (?), never string formatting.
