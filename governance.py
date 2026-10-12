"""Proposal / approval workflow for Spot. Owner: Person 3. See CONTRACTS.md.

All permission failures raise PermissionError with a human-readable reason, e.g.
"Only Payments can approve: Payments depends on Ops Automation".
"""
import db


def propose(user, doc_id, new_content, summary, deadline):
    """Create a pending proposal. User must be a Contributor or Approver on the
    doc's team. required_team = first team that depends on the doc's team,
    else the doc's own team. Returns proposal_id (uuid4 str)."""
    raise NotImplementedError


def approve(user, proposal_id):
    """Approve a pending proposal. User must be an Approver on required_team.
    In one transaction: update docs (content, version + 1, approver, updated_at),
    insert a history row, mark the proposal approved with approved_by.
    Returns the new version (int)."""
    raise NotImplementedError


def reject(user, proposal_id):
    """Reject a pending proposal. Same permission checks as approve().
    Marks the proposal rejected. Returns None."""
    raise NotImplementedError


if __name__ == "__main__":
    pass
