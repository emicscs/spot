"""Proposal / approval workflow for Spot. Owner: Evan. See CONTRACTS.md.

All permission failures raise PermissionError with a human-readable reason, e.g.
"Only Payments can approve: Payments depends on Ops Automation".
"""
import uuid
from datetime import datetime, timezone

import db

PROPOSER_ROLES = ("Contributor", "Approver")


def _now_iso():
    """Current UTC time as an ISO 8601 string, e.g. 2026-10-12T16:12:00Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_user(user):
    """Return the user dict for `user`, or raise PermissionError if unknown."""
    u = db.get_user(user)
    if u is None:
        raise PermissionError(f"Unknown user: {user!r}")
    return u


def _get_doc_or_fail(doc_id):
    doc = db.get_doc(doc_id)
    if doc is None:
        raise ValueError(f"No such doc: {doc_id!r}")
    return doc


def _get_proposal_or_fail(proposal_id):
    rows = db.query(
        "SELECT * FROM proposals WHERE proposal_id = ?", (proposal_id,)
    )
    if not rows:
        raise ValueError(f"No such proposal: {proposal_id!r}")
    return rows[0]


def _routing_reason(required_team, doc_team):
    """Explain why `required_team` is the one that must approve."""
    if required_team == doc_team:
        return f"no other team depends on {doc_team}"
    return f"{required_team} depends on {doc_team}"


def _check_can_decide(user, proposal, verb):
    """Shared permission check for approve/reject.

    `verb` is "approve" or "reject" (used in the error message).
    Returns the user dict on success, raises PermissionError otherwise.
    """
    u = _require_user(user)
    required_team = proposal["required_team"]
    doc = _get_doc_or_fail(proposal["doc_id"])
    reason = _routing_reason(required_team, doc["team"])

    if u["team"] != required_team:
        raise PermissionError(
            f"Only {required_team} can {verb}: {reason} "
            f"({u['name']} is on {u['team']})"
        )
    if u["role"] != "Approver":
        raise PermissionError(
            f"Only an Approver on {required_team} can {verb}: "
            f"{u['name']} is a {u['role']}"
        )
    return u


def _check_pending(proposal):
    if proposal["status"] != "pending":
        raise ValueError(
            f"Proposal {proposal['proposal_id']} is already "
            f"{proposal['status']}, not pending"
        )


def propose(user, doc_id, new_content, summary, deadline):
    """Create a pending proposal. User must be a Contributor or Approver on the
    doc's team. required_team = first team that depends on the doc's team,
    else the doc's own team. Returns proposal_id (uuid4 str)."""
    u = _require_user(user)
    doc = _get_doc_or_fail(doc_id)

    if u["role"] not in PROPOSER_ROLES:
        raise PermissionError(
            f"Only a Contributor or Approver can propose changes: "
            f"{u['name']} is a {u['role']}"
        )
    if u["team"] != doc["team"]:
        raise PermissionError(
            f"Only {doc['team']} can propose changes to {doc_id!r}: "
            f"{u['name']} is on {u['team']}"
        )

    dependents = db.get_dependent_teams(doc["team"])
    required_team = dependents[0] if dependents else doc["team"]

    proposal_id = str(uuid.uuid4())
    db.execute(
        """
        INSERT INTO proposals (
            proposal_id, doc_id, new_content, summary, deadline,
            proposed_by, required_team, status, approved_by, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            proposal_id,
            doc_id,
            new_content,
            summary,
            deadline,
            u["name"],
            required_team,
            "pending",
            None,
            _now_iso(),
        ),
    )
    return proposal_id


def approve(user, proposal_id):
    """Approve a pending proposal. User must be an Approver on required_team.
    In one transaction: update docs (content, version + 1, approver, updated_at),
    insert a history row, mark the proposal approved with approved_by.
    Returns the new version (int)."""
    proposal = _get_proposal_or_fail(proposal_id)
    _check_pending(proposal)
    u = _check_can_decide(user, proposal, "approve")

    now = _now_iso()
    conn = db.get_conn()
    try:
        # Explicit BEGIN so all three writes share one transaction regardless
        # of the connection's isolation_level setting.
        conn.execute("BEGIN")

        # Re-read inside the transaction so the version bump is atomic and we
        # can't double-apply a proposal that was decided concurrently.
        row = conn.execute(
            "SELECT status FROM proposals WHERE proposal_id = ?", (proposal_id,)
        ).fetchone()
        if row is None or row["status"] != "pending":
            raise ValueError(f"Proposal {proposal_id} is no longer pending")

        doc = conn.execute(
            "SELECT version FROM docs WHERE doc_id = ?", (proposal["doc_id"],)
        ).fetchone()
        if doc is None:
            raise ValueError(f"No such doc: {proposal['doc_id']!r}")
        new_version = int(doc["version"]) + 1

        conn.execute(
            """
            UPDATE docs
               SET content = ?, version = ?, approver = ?, updated_at = ?
             WHERE doc_id = ?
            """,
            (proposal["new_content"], new_version, u["name"], now,
             proposal["doc_id"]),
        )
        conn.execute(
            """
            INSERT INTO history (
                doc_id, version, content, changed_by, approved_by,
                summary, deadline, changed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal["doc_id"],
                new_version,
                proposal["new_content"],
                proposal["proposed_by"],
                u["name"],
                proposal["summary"],
                proposal["deadline"],
                now,
            ),
        )
        conn.execute(
            """
            UPDATE proposals
               SET status = 'approved', approved_by = ?
             WHERE proposal_id = ? AND status = 'pending'
            """,
            (u["name"], proposal_id),
        )
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()

    return new_version


def reject(user, proposal_id):
    """Reject a pending proposal. Same permission checks as approve().
    Marks the proposal rejected. Returns None."""
    proposal = _get_proposal_or_fail(proposal_id)
    _check_pending(proposal)
    u = _check_can_decide(user, proposal, "reject")

    db.execute(
        """
        UPDATE proposals
           SET status = 'rejected', approved_by = ?
         WHERE proposal_id = ? AND status = 'pending'
        """,
        (u["name"], proposal_id),
    )
    return None


if __name__ == "__main__":
    # "Done when" scenarios, run against a fresh database.
    db.reset()

    # Pick an Ops Automation doc from the seed so we don't depend on exact ids.
    ops_docs = [d for d in db.get_docs_for_user("bob") if d["team"] == "Ops Automation"]
    assert ops_docs, "seed should contain at least one Ops Automation doc"
    doc_id = ops_docs[0]["doc_id"]
    before = db.get_doc(doc_id)
    history_before = len(db.get_history(doc_id))
    print(f"Using doc {doc_id!r} (team={before['team']}, version={before['version']})")

    # 1. bob proposes and it routes to Payments
    pid = propose(
        "bob", doc_id,
        before["content"] + " Cutover moved to 2026-11-21.",
        "Shift cutover by one week",
        "2026-11-21",
    )
    p = [x for x in db.get_proposals(doc_id) if x["proposal_id"] == pid][0]
    assert p["status"] == "pending", p
    assert p["proposed_by"] == "bob", p
    assert p["required_team"] == "Payments", p
    print(f"1. bob proposed {pid} -> routed to {p['required_team']}  OK")

    # 2. alice approving raises PermissionError (own team)
    try:
        approve("alice", pid)
        raise AssertionError("alice should not be able to approve")
    except PermissionError as e:
        print(f"2. alice approve -> PermissionError: {e}  OK")

    # 3. carol approving raises PermissionError (Reader)
    try:
        approve("carol", pid)
        raise AssertionError("carol should not be able to approve")
    except PermissionError as e:
        print(f"3. carol approve -> PermissionError: {e}  OK")

    # Nothing should have changed yet.
    assert db.get_doc(doc_id)["version"] == before["version"]
    assert len(db.get_history(doc_id)) == history_before

    # 4. dave approving bumps the version and adds a history row
    new_version = approve("dave", pid)
    after = db.get_doc(doc_id)
    hist = db.get_history(doc_id)
    assert new_version == before["version"] + 1, (new_version, before["version"])
    assert after["version"] == new_version, after
    assert after["approver"] == "dave", after
    assert after["content"].endswith("Cutover moved to 2026-11-21."), after
    assert len(hist) == history_before + 1, hist
    assert hist[0]["version"] == new_version, hist[0]
    assert hist[0]["changed_by"] == "bob", hist[0]
    assert hist[0]["approved_by"] == "dave", hist[0]
    assert hist[0]["summary"] == "Shift cutover by one week", hist[0]
    assert hist[0]["deadline"] == "2026-11-21", hist[0]
    p = [x for x in db.get_proposals(doc_id) if x["proposal_id"] == pid][0]
    assert p["status"] == "approved" and p["approved_by"] == "dave", p
    print(f"4. dave approved -> version {before['version']} -> {new_version}, "
          f"history rows {history_before} -> {len(hist)}  OK")

    # Extras: double-approve is refused; reject works with the same checks.
    try:
        approve("dave", pid)
        raise AssertionError("approving twice should fail")
    except ValueError as e:
        print(f"   re-approve refused: {e}  OK")

    pid2 = propose("alice", doc_id, "Something else", "Try again", "2026-12-01")
    try:
        reject("bob", pid2)
        raise AssertionError("bob should not be able to reject")
    except PermissionError as e:
        print(f"   bob reject -> PermissionError: {e}  OK")
    assert reject("dave", pid2) is None
    p2 = [x for x in db.get_proposals(doc_id) if x["proposal_id"] == pid2][0]
    assert p2["status"] == "rejected" and p2["approved_by"] == "dave", p2
    assert db.get_doc(doc_id)["version"] == new_version  # reject changes nothing
    print(f"   dave rejected {pid2}  OK")

    try:
        propose("carol", doc_id, "x", "Reader attempt", "2026-12-01")
        raise AssertionError("carol should not be able to propose")
    except PermissionError as e:
        print(f"   carol propose -> PermissionError: {e}  OK")

    print("All governance scenarios passed.")
