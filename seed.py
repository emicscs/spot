"""Seed data for Spot. Owner: Derrick. See CONTRACTS.md."""
import sqlite3
import uuid
from datetime import datetime, timezone

import config
import db


DOCS = [
    (
        "ops-uae-identity",
        "UAE Identity Service Integration Scope",
        "Ops Automation",
        "The UAE Identity Service integrates digital ID verification for regional merchants and acquiring institutions. The cutover date for the UAE identity service is scheduled for November 14, 2026. Prior to cutover, automated credential rotation and staging sandbox verification must be finalized.",
        1,
        "bob",
        "alice",
        "2026-10-01T09:00:00Z",
    ),
    (
        "ops-uae-gateway",
        "UAE Payment Gateway Requirements",
        "Ops Automation",
        "Defines protocol bridging between local UAE acquiring networks and central clearing channels. Gateway routing requires dual-region active-active deployment with sub-50ms failover.",
        1,
        "bob",
        "alice",
        "2026-10-02T10:30:00Z",
    ),
    (
        "ops-infra-topology",
        "Cloud Infrastructure Topology & Network Boundaries",
        "Ops Automation",
        "Architecture reference for regional infrastructure zones, VPC peering across Middle East payment zones, and baseline firewall compliance requirements.",
        1,
        "alice",
        "alice",
        "2026-09-28T14:15:00Z",
    ),
    (
        "ops-batch-scheduler",
        "Operational Batch Scheduler Runbook",
        "Ops Automation",
        "Operating procedures for nightly reconciliation batch triggers, alerting thresholds, and automated retry mechanisms for transient network drops.",
        1,
        "bob",
        "alice",
        "2026-09-30T11:00:00Z",
    ),
    (
        "pay-core-routing",
        "Payment Core Transaction Routing Specification",
        "Payments",
        "Specifies ISO 20022 message transformation and routing across domestic switch participants. Dependent upon Ops Automation connectivity endpoints and network topology.",
        1,
        "dave",
        "dave",
        "2026-10-03T08:45:00Z",
    ),
    (
        "pay-settlement-rules",
        "Merchant Clearing and Settlement Rules",
        "Payments",
        "Business rules determining multi-currency net settlement cycles, fee calculation schedules, and end-of-day bank payout processing.",
        1,
        "dave",
        "dave",
        "2026-10-04T12:00:00Z",
    ),
    (
        "pay-fraud-scoring",
        "Transaction Fraud Risk Scoring & Limits",
        "Payments",
        "Threshold limits, real-time token scoring models, and step-up authentication rules for high-value cross-border merchant transfers.",
        1,
        "carol",
        "dave",
        "2026-10-05T15:20:00Z",
    ),
    (
        "pay-dispute-workflow",
        "Chargeback and Dispute Handling Workflow",
        "Payments",
        "Standard operating procedure for handling cardholder dispute requests, evidence collection timelines, and arbitration escalations.",
        1,
        "carol",
        "dave",
        "2026-10-06T16:10:00Z",
    ),
    (
        "pay-decision-log",
        "Payments Architecture Decision Log (ADR-019)",
        "Payments",
        "Decision record confirming adoption of tokenized credentials for all MENA region acquiring connections, retiring legacy symmetric keys.",
        1,
        "dave",
        "dave",
        "2026-10-07T13:30:00Z",
    ),
]

DEPENDENCIES = [
    ("Payments", "Ops Automation"),
]

PENDING_PROPOSAL = {
    "proposal_id": str(uuid.uuid4()),
    "doc_id": "ops-uae-gateway",
    "new_content": "Defines protocol bridging between local UAE acquiring networks and central clearing channels. Cutover schedule moved up one week to accelerate pilot merchant onboarding. Gateway routing requires dual-region active-active deployment with sub-50ms failover.",
    "summary": "Move UAE gateway cutover up one week",
    "deadline": "2026-11-01T17:00:00Z",
    "proposed_by": "bob",
    "required_team": "Payments",
    "status": "pending",
    "approved_by": None,
    "created_at": "2026-10-10T14:00:00Z",
}


def seed():
    """Insert 8-10 seed docs (Ops Automation and Payments), the dependency row
    ("Payments", "Ops Automation"), and one pending proposal on the UAE gateway doc.
    Uses db.execute. Returns None."""
    for doc in DOCS:
        db.execute(
            """
            INSERT INTO docs (doc_id, title, team, content, version, author, approver, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            doc,
        )

    for dep in DEPENDENCIES:
        db.execute(
            """
            INSERT INTO team_dependencies (team, depends_on)
            VALUES (?, ?)
            """,
            dep,
        )

    db.execute(
        """
        INSERT INTO proposals (
            proposal_id, doc_id, new_content, summary, deadline,
            proposed_by, required_team, status, approved_by, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            PENDING_PROPOSAL["proposal_id"],
            PENDING_PROPOSAL["doc_id"],
            PENDING_PROPOSAL["new_content"],
            PENDING_PROPOSAL["summary"],
            PENDING_PROPOSAL["deadline"],
            PENDING_PROPOSAL["proposed_by"],
            PENDING_PROPOSAL["required_team"],
            PENDING_PROPOSAL["status"],
            PENDING_PROPOSAL["approved_by"],
            PENDING_PROPOSAL["created_at"],
        ),
    )


def _init_tables_if_needed(conn):
    """Helper for testing seed.py independently before db.py is fully implemented."""
    conn.executescript(
        """
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
    )
    conn.commit()


if __name__ == "__main__":
    print(f"Target Demo Target Doc ID: ops-uae-identity")
    print("Cutover Date: November 14, 2026")

    # Verify self-contained or through db.py
    try:
        db.reset()
        print("Called db.reset() successfully.")
    except (NotImplementedError, AttributeError):
        print("db.reset() not implemented yet; initializing schema directly for verification...")
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.executescript(
            """
            DROP TABLE IF EXISTS docs;
            DROP TABLE IF EXISTS proposals;
            DROP TABLE IF EXISTS history;
            DROP TABLE IF EXISTS team_dependencies;
            """
        )
        _init_tables_if_needed(conn)

        # Monkey-patch db.execute for independent verification
        orig_execute = getattr(db, "execute", None)
        def _temp_execute(sql, params=()):
            c = conn.cursor()
            c.execute(sql, params)
            conn.commit()
        db.execute = _temp_execute

        seed()

        if orig_execute:
            db.execute = orig_execute

    # Verify counts
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM docs")
    doc_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM team_dependencies")
    dep_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM proposals WHERE status = 'pending'")
    proposal_count = c.fetchone()[0]

    c.execute("SELECT doc_id, title FROM docs WHERE content LIKE '%cutover date for the UAE identity service%'")
    uae_id_docs = c.fetchall()

    print(f"Total seeded docs: {doc_count} (expected 8-10)")
    print(f"Total dependencies: {dep_count} (expected 1)")
    print(f"Total pending proposals: {proposal_count} (expected 1)")
    print(f"Docs containing UAE identity service cutover: {len(uae_id_docs)} (expected exactly 1)")
    for row in uae_id_docs:
        print(f"  - [{row['doc_id']}] {row['title']}")

    assert doc_count >= 8 and doc_count <= 10, f"Expected 8-10 docs, got {doc_count}"
    assert dep_count == 1, f"Expected 1 dependency, got {dep_count}"
    assert proposal_count == 1, f"Expected 1 pending proposal, got {proposal_count}"
    assert len(uae_id_docs) == 1, f"Expected exactly 1 doc with UAE cutover date, got {len(uae_id_docs)}"
    print("All seed assertions passed!")
