# CONTRACTS.md — Frozen contract (nobody changes it)

Users (hardcoded dict USERS in db.py; all people are fictional). Keys are lowercase "first.last".
Each entry: {"name", "display_name", "title", "team", "role", "avatar_color"}.

Core demo users:
- priya.raman: Priya Raman, Technical Program Manager, team "Ops Automation", role "Approver"   (was alice)
- marcus.chen: Marcus Chen, Infrastructure Engineer, team "Ops Automation", role "Contributor"  (was bob)
- elena.rossi: Elena Rossi, Business Analyst, team "Payments", role "Reader"                   (was carol)
- daniel.okafor: Daniel Okafor, Engineering Manager, team "Payments", role "Approver"          (was dave)

Background users (appear in workspace messages only; role "Reader"):
- sofia.alvarez: Sofia Alvarez, Program Director, team "Program Office"
- james.whitfield: James Whitfield, Security Architect, team "Information Security"
- aisha.karimi: Aisha Karimi, Compliance Lead, team "Compliance & Legal"
- tomas.novak: Tomas Novak, Network Engineer, team "Network Engineering"
- hannah.brooks: Hannah Brooks, Project Coordinator, team "Program Office"
- ravi.menon: Ravi Menon, Site Reliability Engineer, team "Ops Automation"

SQLite tables:
- docs(doc_id TEXT PRIMARY KEY, title TEXT, team TEXT, content TEXT, version INTEGER, author TEXT, approver TEXT, updated_at TEXT): approved content only
- proposals(proposal_id TEXT PRIMARY KEY, doc_id TEXT, new_content TEXT, summary TEXT, deadline TEXT, proposed_by TEXT, required_team TEXT, status TEXT, approved_by TEXT, created_at TEXT): status is "pending" | "approved" | "rejected"
- history(doc_id TEXT, version INTEGER, content TEXT, changed_by TEXT, approved_by TEXT, summary TEXT, deadline TEXT, changed_at TEXT): one row per approved change
- team_dependencies(team TEXT, depends_on TEXT): "team depends on depends_on". Seed: ("Payments", "Ops Automation")

Function signatures and return shapes:
- db.py
  - get_conn() -> sqlite3.Connection with row_factory = sqlite3.Row
  - execute(sql, params=()) and query(sql, params=()) -> shared helpers; query returns a list of dicts
  - get_user(name) -> {"name", "display_name", "title", "team", "role", "avatar_color"} or None
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
  - seed() -> inserts seed docs, the dependency row, and the two pending proposals below (uses db.execute)

Rules:
- Readers see docs from their own team and from teams their team depends on.
- Contributors and Approvers can propose changes to their own team's docs.
- A proposal is routed to the teams that depend on the doc's team (required_team = first dependent team). If none, it goes to the doc's own team.
- Only an Approver on required_team can approve or reject. A team cannot approve its own change when another team depends on it.
- Docs change only through approve().

Fixed seed data (workspace.py messages link to these, so use these exact values):
- Doc "ops-uae-identity": title "UAE Identity Service Integration Scope", team "Ops Automation", v1 says the cutover date for the UAE identity service is November 14, 2026.
- Doc "ops-uae-gateway": title "UAE Payment Gateway Requirements", team "Ops Automation".
- Proposal "3f2b8c1e-7a4d-4e9b-9c2f-5d1a6b8e0c47" (pending): doc "ops-uae-identity", summary "UAE identity service cutover moved two weeks", new content moves the cutover to November 28, 2026, proposed_by "marcus.chen", required_team "Payments", deadline "2026-10-16".
- Proposal "a91d4f60-2c3b-4b7e-8f15-6e0c9d2b7a38" (pending, never approved): doc "ops-uae-gateway", summary "Move UAE gateway cutover up one week", proposed_by "marcus.chen", required_team "Payments", deadline "2026-10-20".
- Only these two IDs are fixed; proposals created at runtime still use uuid4().

workspace.py (data only, no logic; owned by Frankie): the fictional Mastercard Teams workspace (teams, channels, chats, memberships, the Spot bot user, and 25-40 seed messages). Message fields: message_id, location, author, timestamp, text, thread_parent_id (optional), mentions_spot (bool), proposal_id (optional, one of the fixed IDs above).

Conventions (from the stack):
- Use uuid4 strings for proposal_id.
- Store dates and timestamps as ISO 8601 strings.
- Always use parameterized queries (?), never string formatting.
