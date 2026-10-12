"""Chat over approved docs for Spot. Owner: Person 4. See CONTRACTS.md.

Only approved content (the docs table) goes into the prompt. Never pending proposals.
"""
import config
import db


def ask(user, question):
    """Answer a question from the docs the user may see.
    Returns {"answer": str,
             "sources": [{"doc_id", "title", "version", "author", "approver"}]}."""
    raise NotImplementedError


if __name__ == "__main__":
    pass
