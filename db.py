"""Database layer for Spot. Owner: Contributor 2. See CONTRACTS.md."""
import sqlite3

import config

USERS = {
    "alice": {"name": "alice", "team": "Ops Automation", "role": "Approver"},
    "bob": {"name": "bob", "team": "Ops Automation", "role": "Contributor"},
    "carol": {"name": "carol", "team": "Payments", "role": "Reader"},
    "dave": {"name": "dave", "team": "Payments", "role": "Approver"},
}


def get_conn():
    """Return a sqlite3.Connection to config.DB_PATH with row_factory = sqlite3.Row."""
    raise NotImplementedError


def execute(sql, params=()):
    """Run a write statement with parameterized (?) params and commit."""
    raise NotImplementedError


def query(sql, params=()):
    """Run a SELECT with parameterized (?) params. Returns a list of dicts."""
    raise NotImplementedError


def get_user(name):
    """Returns {"name", "team", "role"} or None."""
    raise NotImplementedError


def get_docs_for_user(name):
    """Returns a list of doc dicts (keys = docs columns) the user may see:
    own team's docs plus docs of teams their team depends on."""
    raise NotImplementedError


def get_doc(doc_id):
    """Returns a doc dict (keys = docs columns) or None."""
    raise NotImplementedError


def get_history(doc_id):
    """Returns a list of history dicts (keys = history columns), newest first."""
    raise NotImplementedError


def get_proposals(doc_id):
    """Returns a list of proposal dicts (keys = proposals columns), all statuses."""
    raise NotImplementedError


def get_pending():
    """Returns a list of proposal dicts with status == "pending"."""
    raise NotImplementedError


def get_dependent_teams(team):
    """Returns a list of team names that depend on `team`."""
    raise NotImplementedError


def reset():
    """Drops and recreates all tables, then calls seed.seed(). Returns None."""
    raise NotImplementedError


if __name__ == "__main__":
    pass
