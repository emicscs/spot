"""Startup must preserve an imported database and still initialize a fresh demo."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import config
import db


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = patch.object(config, "DB_PATH", str(Path(self.directory.name) / "spot.db"))
        self.database.start()
        self.addCleanup(self.database.stop)
        self.server = patch.object(app.app, "run")
        self.server.start()
        self.addCleanup(self.server.stop)

    def test_startup_initializes_a_missing_database(self):
        app.main()
        self.assertEqual(len(db.query("SELECT * FROM docs")), 9)
        self.assertEqual(len(db.get_pending()), 2)

    def test_startup_preserves_documents_proposals_and_history(self):
        db.reset()
        db.execute("UPDATE docs SET content = ?, version = ? WHERE doc_id = ?",
                   ("Imported approved content", 7, "ops-uae-gateway"))
        db.execute("DELETE FROM proposals WHERE doc_id = ?", ("ops-uae-identity",))
        db.execute("INSERT INTO history (doc_id, version, content) VALUES (?, ?, ?)",
                   ("ops-uae-gateway", 7, "Imported approved content"))
        expected = {table: db.query(f"SELECT * FROM {table}") for table in db.TABLES}

        app.main()
        app.main()

        actual = {table: db.query(f"SELECT * FROM {table}") for table in db.TABLES}
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
