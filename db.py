"""Database layer for Spot. Owner: Contributor 2. See CONTRACTS.md."""
import sqlite3

import config

USERS = {
    "alice": {"name": "alice", "team": "Ops Automation", "role": "Approver"},
    "bob": {"name": "bob", "team": "Ops Automation", "role": "Contributor"},
    "carol": {"name": "carol", "team": "Payments", "role": "Reader"},
    "dave": {"name": "dave", "team": "Payments", "role": "Approver"},
}

TABLES = ("docs", "proposals", "history", "team_dependencies")

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
    doc_id TEXT PRIMARY KEY,
    title TEXT,
    team TEXT,
    content TEXT,
    version INTEGER,
    author TEXT,
    approver TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS proposals (
    proposal_id TEXT PRIMARY KEY,
    doc_id TEXT,
    new_content TEXT,
    summary TEXT,
    deadline TEXT,
    proposed_by TEXT,
    required_team TEXT,
    status TEXT,
    approved_by TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS history (
    doc_id TEXT,
    version INTEGER,
    content TEXT,
    changed_by TEXT,
    approved_by TEXT,
    summary TEXT,
    deadline TEXT,
    changed_at TEXT
);
CREATE TABLE IF NOT EXISTS team_dependencies (
    team TEXT,
    depends_on TEXT
);
"""


def get_conn():
    """Return a sqlite3.Connection to config.DB_PATH with row_factory = sqlite3.Row."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def execute(sql, params=()):
    """Run a write statement with parameterized (?) params and commit."""
    conn = get_conn()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def query(sql, params=()):
    """Run a SELECT with parameterized (?) params. Returns a list of dicts."""
    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def create_tables():
    """Create all tables if they do not already exist."""
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def drop_tables():
    """Drop all tables if they exist."""
    conn = get_conn()
    try:
        conn.executescript(
            "".join(f"DROP TABLE IF EXISTS {name};\n" for name in TABLES)
        )
        conn.commit()
    finally:
        conn.close()


def get_user(name):
    """Returns {"name", "team", "role"} or None."""
    user = USERS.get(name)
    return dict(user) if user else None


def get_docs_for_user(name):
    """Returns a list of doc dicts (keys = docs columns) the user may see:
    own team's docs plus docs of teams their team depends on."""
    user = get_user(name)
    if user is None:
        return []
    return query(
        """
        SELECT * FROM docs
        WHERE team = ?
           OR team IN (SELECT depends_on FROM team_dependencies WHERE team = ?)
        ORDER BY team, title
        """,
        (user["team"], user["team"]),
    )


def get_doc(doc_id):
    """Returns a doc dict (keys = docs columns) or None."""
    rows = query("SELECT * FROM docs WHERE doc_id = ?", (doc_id,))
    return rows[0] if rows else None


def get_history(doc_id):
    """Returns a list of history dicts (keys = history columns), newest first."""
    return query(
        "SELECT * FROM history WHERE doc_id = ? ORDER BY version DESC, changed_at DESC",
        (doc_id,),
    )


def get_proposals(doc_id):
    """Returns a list of proposal dicts (keys = proposals columns), all statuses."""
    return query(
        "SELECT * FROM proposals WHERE doc_id = ? ORDER BY created_at DESC",
        (doc_id,),
    )


def get_pending():
    """Returns a list of proposal dicts with status == "pending"."""
    return query(
        "SELECT * FROM proposals WHERE status = ? ORDER BY created_at DESC",
        ("pending",),
    )


def get_dependent_teams(team):
    """Returns a list of team names that depend on `team`."""
    rows = query(
        "SELECT team FROM team_dependencies WHERE depends_on = ? ORDER BY team",
        (team,),
    )
    return [row["team"] for row in rows]


def reset():
    """Drops and recreates all tables, then calls seed.seed(). Returns None."""
    import seed  # imported here: seed.py imports db, so a top-level import would be circular

    drop_tables()
    create_tables()
    seed.seed()


if __name__ == "__main__":
    import uuid

    def _inline_seed():
        """Temporary stand-in used only until seed.py is implemented."""
        now = "2026-10-01T09:00:00+00:00"
        docs = [
            ("ops-uae-gateway", "UAE Payment Gateway Requirements", "Ops Automation",
             "Gateway routing requires dual-region active-active deployment.", 1, "bob", "alice", now),
            ("pay-core-routing", "Payment Core Transaction Routing Specification", "Payments",
             "Specifies ISO 20022 message routing.", 1, "dave", "dave", now),
        ]
        for doc in docs:
            execute(
                "INSERT INTO docs (doc_id, title, team, content, version, author, approver, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                doc,
            )
        execute("INSERT INTO team_dependencies (team, depends_on) VALUES (?, ?)",
                ("Payments", "Ops Automation"))
        execute(
            "INSERT INTO proposals (proposal_id, doc_id, new_content, summary, deadline, proposed_by, "
            "required_team, status, approved_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), "ops-uae-gateway", "Updated gateway content.", "Move cutover up one week",
             "2026-11-01T17:00:00+00:00", "bob", "Payments", "pending", None, now),
        )

    def _snapshot():
        return {t: query(f"SELECT * FROM {t}") for t in TABLES}

    def _do_reset():
        try:
            reset()
            return "seed.seed()"
        except NotImplementedError:
            drop_tables()
            create_tables()
            _inline_seed()
            return "inline seed (seed.py not implemented yet)"

    print("DB_PATH:", config.DB_PATH)
    source = _do_reset()
    print("Seeded via:", source)

    carol_docs = get_docs_for_user("carol")
    carol_teams = sorted({d["team"] for d in carol_docs})
    print("carol sees", len(carol_docs), "docs from teams:", carol_teams)
    assert carol_teams == ["Ops Automation", "Payments"], carol_teams

    bob_teams = sorted({d["team"] for d in get_docs_for_user("bob")})
    print("bob sees teams:", bob_teams)
    assert bob_teams == ["Ops Automation"], bob_teams

    assert get_docs_for_user("nobody") == []
    assert get_user("alice") == {"name": "alice", "team": "Ops Automation", "role": "Approver"}
    assert get_user("zed") is None

    deps = get_dependent_teams("Ops Automation")
    print("depends on Ops Automation:", deps)
    assert deps == ["Payments"], deps
    assert get_dependent_teams("Payments") == []

    pending = get_pending()
    print("pending proposals:", len(pending))
    assert len(pending) == 1 and pending[0]["status"] == "pending"
    assert get_proposals(pending[0]["doc_id"])[0]["proposal_id"] == pending[0]["proposal_id"]

    doc = get_doc(pending[0]["doc_id"])
    assert doc is not None and doc["doc_id"] == pending[0]["doc_id"]
    assert get_doc("does-not-exist") is None
    assert get_history(doc["doc_id"]) == []

    # Reset twice in a row must leave exactly the seed data (ignoring the random proposal_id).
    first = _snapshot()
    _do_reset()
    second = _snapshot()
    for t in TABLES:
        a = [{k: v for k, v in r.items() if k != "proposal_id"} for r in first[t]]
        b = [{k: v for k, v in r.items() if k != "proposal_id"} for r in second[t]]
        assert a == b, f"{t} differs after second reset"
    print("reset() twice leaves identical seed data")
    print("All db.py checks passed.")
