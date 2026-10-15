"""Tests for scripts/state_agents.py - the DuckDB ledger CLI (agent-state skill).

Runs against a temporary repository through the real main(); the kit invariant
tests also pin the byte-identical mirror shipped inside the skill.
"""

import ast
import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "state_agents.py"

_spec = importlib.util.spec_from_file_location("state_agents", SCRIPT)
sa = importlib.util.module_from_spec(_spec)
sys.modules["state_agents"] = sa
_spec.loader.exec_module(sa)

# Legacy French headings, built from code points so this file holds no accented
# character (same discipline as scripts/state_agents.py).
_E9 = chr(0xE9)
FR_GOAL_HEADING = "## Objectif Actuel"
FR_MILESTONE_HEADING = "## Jalons de l'It" + _E9 + "ration"
FR_TEST_CMD_LINE = "* Commande d'ex" + _E9 + "cution d" + "es tests : `pytest -q`"


def run(*args: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = sa.main(list(args))
    return code, buffer.getvalue()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


class Repo(unittest.TestCase):
    """Temporary repository addressed through --repo."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()

    def call(self, *args: str) -> tuple[int, str]:
        return run("--repo", str(self.repo), *args)

    def legacy_fixture(self) -> None:
        write(self.repo / "feature_list.json", json.dumps({"features": [
            {"id": "F-01", "name": "engine", "description": "core", "status": "in_progress",
             "dependencies": []},
            {"id": "F-02", "name": "ui", "description": "panels", "status": "pending",
             "dependencies": ["F-01"]},
        ]}))
        write(self.repo / "feature_list_archive.json", json.dumps({"features": [
            {"id": "F-00", "name": "seed", "description": "done before", "status": "completed",
             "dependencies": []},
        ]}))
        write(self.repo / "contract.md",
              "# Validation Contract\n\n"
              "## Automated Acceptance Criteria\n\n"
              "- [ ] S01: first criterion\n"
              "- [x] S02: second criterion\n"
              "- [ ] S03: third criterion\n\n"
              "## Evaluation Protocol\n\n"
              "* Test command: `pytest -q`\n")
        write(self.repo / "progress.md",
              "# Sprint Progress\n\n"
              "## Current Goal\n- [x] ship the engine\n\n"
              "## Iteration Milestones\n- [ ] F-01: engine\n- [x] F-00: seed\n\n"
              "## Contract Validation\n- S01: evidence pending\n")
        write(self.repo / "log.md",
              "# Execution Log (Append-Only)\n\n"
              "## [2026-10-01] init | Project started.\n"
              "## [2026-10-02] gen  | Wrote the engine.\n"
              "## [2026-10-03] eval | Tests green.\n")
        write(self.repo / "docs" / "journal" / "log_2026-08.md",
              "# Execution Log - archive 2026-08\n\n"
              "## [2026-08-01] init | Old project started.\n"
              "## [2026-08-15] sync | Fleet wave one.\n")
        write(self.repo / ".gitignore", "node_modules/\n")

    def query(self, sql: str):
        with sa.open_db(self.repo) as con:
            return con.execute(sql).fetchall()


class Schema(Repo):
    def test_bootstrap_creates_database_and_is_idempotent(self):
        for _ in range(2):
            code, out = self.call("bootstrap")
            self.assertEqual(code, 0)
            self.assertIn("FEATURES 0 active / 0", out)
        self.assertTrue((self.repo / ".agent" / "state.duckdb").is_file())

    def test_check_constraints(self):
        self.call("bootstrap")
        with sa.open_db(self.repo) as con:
            with self.assertRaises(duckdb.Error):
                con.execute("INSERT INTO features (id, name, status) VALUES ('X', 'x', 'bogus')")
            with self.assertRaises(duckdb.Error):
                con.execute("INSERT INTO execution_log (log_date, action, message)"
                            " VALUES ('2026-01-01', 'rot', 'x')")
            with self.assertRaises(duckdb.Error):
                con.execute("INSERT INTO sprint_progress (category, description)"
                            " VALUES ('other', 'x')")


class Migration(Repo):
    def test_full_migration_with_backup(self):
        self.legacy_fixture()
        code, out = self.call("migrate", "--backup")
        self.assertEqual(code, 0)
        self.assertIn("MIGRATED into .agent/state.duckdb: 3 features, 3 criteria,"
                      " 3 steps, 5 log entries.", out)

        features = self.query("SELECT id, name, status, dependencies FROM features ORDER BY id")
        self.assertEqual(features, [
            ("F-00", "seed", "completed", []),
            ("F-01", "engine", "in_progress", []),
            ("F-02", "ui", "pending", ["F-01"]),
        ])

        criteria = self.query("SELECT criterion, passed FROM contract_criteria ORDER BY id")
        self.assertEqual([c for c, _ in criteria],
                         ["S01: first criterion", "S02: second criterion", "S03: third criterion"])
        self.assertEqual([p for _, p in criteria], [False, True, False])
        self.assertEqual(self.query("SELECT value FROM contract_meta WHERE key = 'test_command'"),
                         [("pytest -q",)])

        sprint = self.query("SELECT category, done, description FROM sprint_progress ORDER BY id")
        self.assertEqual(sprint, [
            ("objective", True, "ship the engine"),
            ("milestone", False, "F-01: engine"),
            ("milestone", True, "F-00: seed"),
        ])

        # Chronological order: journal archive first, live log last (increasing ids).
        log = self.query("SELECT log_date, action, message FROM execution_log ORDER BY id")
        self.assertEqual(log, [
            ("2026-08-01", "init", "Old project started."),
            ("2026-08-15", "sync", "Fleet wave one."),
            ("2026-10-01", "init", "Project started."),
            ("2026-10-02", "gen", "Wrote the engine."),
            ("2026-10-03", "eval", "Tests green."),
        ])

        backup = self.repo / ".agent" / "legacy_markdown_backup"
        for rel in ("feature_list.json", "feature_list_archive.json", "contract.md",
                    "progress.md", "log.md",
                    "docs/journal/log_2026-08.md"):
            self.assertTrue((backup / rel).is_file(), rel)
            self.assertFalse((self.repo / rel).exists(), rel)
        self.assertFalse((self.repo / "docs" / "journal").exists())

        gitignore = (self.repo / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("node_modules/", gitignore)
        self.assertIn(sa.WAL_LINE, gitignore)

    def test_nothing_to_migrate(self):
        code, _ = self.call("migrate")
        self.assertEqual(code, 2)
        self.call("bootstrap")
        code, _ = self.call("migrate")
        self.assertEqual(code, 0)

    def test_archive_id_collision_rekeyed(self):
        write(self.repo / "feature_list.json", json.dumps({"features": [
            {"id": "F-01", "name": "new one", "description": "", "status": "in_progress",
             "dependencies": []}]}))
        write(self.repo / "feature_list_archive.json", json.dumps({"features": [
            {"id": "F-01", "name": "old one", "description": "", "status": "completed",
             "dependencies": []}]}))
        code, out = self.call("migrate")
        self.assertEqual(code, 0)
        self.assertEqual(self.query("SELECT id, name, status FROM features ORDER BY id"), [
            ("AA-F-01", "old one", "completed"),
            ("F-01", "new one", "in_progress"),
        ])
        self.assertIn("id reused across sprints, archived row re-keyed AA-F-01", out)


class MigrationEdge(Repo):
    def test_bare_list_archive_and_status_coercion_and_skipped_headings(self):
        write(self.repo / "feature_list_archive.json", json.dumps([
            {"id": "F-00", "name": "seed", "description": "", "status": "awaiting_playtest",
             "dependencies": []},
        ]))
        write(self.repo / "log.md",
              "## [2026-01-01] init | Start.\n"
              "## [2026-01-02] rot | non-standard type is skipped\n")
        code, out = self.call("migrate")
        self.assertEqual(code, 0)
        self.assertEqual(self.query("SELECT id, status FROM features"), [("F-00", "pending")])
        self.assertIn("status 'awaiting_playtest' coerced to 'pending'", out)
        self.assertEqual(self.query("SELECT count(*) FROM execution_log"), [(1,)])
        self.assertIn("1 '## ' heading line(s) skipped", out)
        self.assertIn("Sources kept in place", out)

    def test_malformed_json_rolls_back(self):
        write(self.repo / "feature_list.json", "not json at all")
        write(self.repo / "log.md", "## [2026-01-01] init | Start.\n")
        code, out = self.call("migrate", "--backup")
        self.assertEqual(code, 1)
        self.assertIn("MIGRATION FAILED (rolled back, sources untouched)", out)
        self.assertFalse((self.repo / ".agent" / "state.duckdb").exists())
        self.assertTrue((self.repo / "feature_list.json").is_file())
        self.assertTrue((self.repo / "log.md").is_file())


class MigrationFrench(Repo):
    def test_french_legacy_formats(self):
        write(self.repo / "contract.md",
              "# Contrat\n\n## Crit" + _E9 + "res\n\n- [x] C1: premier\n\n"
              "## Protocole\n\n" + FR_TEST_CMD_LINE + "\n")
        write(self.repo / "progress.md",
              "# Avancement\n\n" + FR_GOAL_HEADING + "\n- [ ] livrer le moteur\n\n"
              + FR_MILESTONE_HEADING + "\n- [x] F-00: amor" + chr(0xE7) + "age\n")
        write(self.repo / "log.md", "## [2026-01-01] init | D" + _E9 + "part.\n")
        code, _ = self.call("migrate")
        self.assertEqual(code, 0)
        self.assertEqual(self.query("SELECT value FROM contract_meta WHERE key = 'test_command'"),
                         [("pytest -q",)])
        self.assertEqual(self.query("SELECT category, done, description FROM sprint_progress"
                                    " ORDER BY id"), [
            ("objective", False, "livrer le moteur"),
            ("milestone", True, "F-00: amor" + chr(0xE7) + "age"),
        ])
        self.assertEqual(self.query("SELECT message FROM execution_log"),
                         [("D" + _E9 + "part.",)])


class Bootstrap(Repo):
    def test_auto_migration_when_database_absent(self):
        self.legacy_fixture()
        code, out = self.call("bootstrap")
        self.assertEqual(code, 0)
        self.assertIn("LEGACY LEDGER DETECTED", out)
        self.assertTrue((self.repo / ".agent" / "state.duckdb").is_file())
        self.assertFalse((self.repo / "log.md").exists())

    def test_bounded_output(self):
        self.call("bootstrap")
        with sa.open_db(self.repo) as con:
            for i in range(25):
                con.execute("INSERT INTO execution_log (log_date, action, message)"
                            " VALUES ('2026-09-01', 'gen', ?)", [f"entry {i}"])
        code, out = self.call("bootstrap")
        self.assertEqual(code, 0)
        self.assertIn("LOG last 20 of 25", out)
        tail = out.split("LOG last 20 of 25\n", 1)[1].split("\n")
        entries = [line for line in tail if line.startswith(" 2026-")]
        self.assertEqual(len(entries), 20)
        self.assertIn("entry 24", out)
        self.assertNotIn("entry 4 |", out)

    def test_completed_features_excluded(self):
        self.legacy_fixture()
        self.call("migrate")
        _, out = self.call("bootstrap")
        self.assertIn("FEATURES 2 active / 3", out)
        self.assertIn("[in_progress] F-01 engine", out)
        self.assertNotIn("F-00 seed", out)


class Ops(Repo):
    def test_log_command(self):
        code, out = self.call("log", "gen", "wrote the module")
        self.assertEqual(code, 0)
        self.assertEqual(self.query("SELECT action, message FROM execution_log"),
                         [("gen", "wrote the module")])
        code, out = self.call("log", "fix", "x" * 220)
        self.assertEqual(code, 0)
        self.assertIn("WARNING: 220-character entry", out)
        with self.assertRaises(SystemExit):
            self.call("log", "rot", "invalid type")

    def test_feature_commands(self):
        self.call("feature", "add", "F-01", "engine", "core module", "--deps", "F-00,F-99")
        self.assertEqual(self.query("SELECT id, status, dependencies FROM features"),
                         [("F-01", "pending", ["F-00", "F-99"])])
        code, _ = self.call("feature", "add", "F-01", "again", "dup")
        self.assertEqual(code, 1)
        code, _ = self.call("feature", "status", "F-01", "in_progress")
        self.assertEqual(code, 0)
        self.assertEqual(self.query("SELECT status FROM features"), [("in_progress",)])
        code, _ = self.call("feature", "status", "F-99", "pending")
        self.assertEqual(code, 1)
        with self.assertRaises(SystemExit):
            self.call("feature", "status", "F-01", "bogus")

    def test_step_commands(self):
        self.call("step", "add", "objective", "ship it")
        self.call("step", "add", "milestone", "F-01 done")
        self.assertEqual(self.query("SELECT category, done FROM sprint_progress ORDER BY id"),
                         [("objective", False), ("milestone", False)])
        code, _ = self.call("step", "done", "2")
        self.assertEqual(code, 0)
        self.assertEqual(self.query("SELECT done FROM sprint_progress WHERE id = 2"), [(True,)])
        code, _ = self.call("step", "done", "99")
        self.assertEqual(code, 1)
        code, out = self.call("step", "reset")
        self.assertEqual(code, 0)
        self.assertIn("SPRINT CLEARED (2 step(s) removed)", out)
        self.assertEqual(self.query("SELECT count(*) FROM sprint_progress"), [(0,)])

    def test_contract_commands(self):
        self.call("contract", "add", "C1: first")
        self.call("contract", "add", "C2: second")
        self.assertEqual(self.query("SELECT count(*) FROM contract_criteria"), [(2,)])
        code, _ = self.call("contract", "pass", "1")
        self.assertEqual(code, 0)
        self.assertEqual(self.query("SELECT passed FROM contract_criteria ORDER BY id"),
                         [(True,), (False,)])
        code, _ = self.call("contract", "pass", "99")
        self.assertEqual(code, 1)
        self.call("contract", "cmd", "pytest -q")
        self.assertEqual(self.query("SELECT value FROM contract_meta"), [("pytest -q",)])

    def test_search_log(self):
        with sa.open_db(self.repo) as con:
            for day, message in (("01", "Fleet wave"), ("02", "engine written"),
                                 ("03", "FLEET wave two")):
                con.execute("INSERT INTO execution_log (log_date, action, message)"
                            " VALUES (?, 'gen', ?)", [f"2026-09-{day}", message])
        code, out = self.call("search-log", "fleet")
        self.assertEqual(code, 0)
        self.assertEqual(len([line for line in out.split("\n") if line.startswith(" ")]), 2)
        self.assertIn("MATCHES 2 shown of 2", out)
        code, out = self.call("search-log", "fleet", "--limit", "1")
        self.assertIn("MATCHES 1 shown of 2", out)

    def test_export_md(self):
        self.call("feature", "add", "F-01", "engine", "core")
        self.call("log", "init", "started")
        code, out = self.call("export-md")
        self.assertEqual(code, 0)
        self.assertIn("WROTE .agent/DASHBOARD.md", out)
        dashboard = (self.repo / ".agent" / "DASHBOARD.md").read_text(encoding="utf-8")
        self.assertIn("# Agent State Dashboard", dashboard)
        self.assertIn("F-01 engine", dashboard)
        self.assertIn("started", dashboard)


class KitInvariants(unittest.TestCase):
    """The shipped skill copy is a byte-identical mirror of the canonical script."""

    def test_script_mirror(self):
        canonical = (ROOT / "scripts" / "state_agents.py").read_bytes()
        shipped = (ROOT / "skills" / "agent-state" / "scripts" / "state_agents.py").read_bytes()
        self.assertEqual(canonical, shipped, "skills/agent-state copy drifted from scripts/")

    def test_imports_stdlib_plus_duckdb_only(self):
        tree = ast.parse((ROOT / "scripts" / "state_agents.py").read_text(encoding="utf-8"))
        allowed = set(sys.stdlib_module_names) | {"duckdb"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], allowed)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                self.assertIn(node.module.split(".")[0], allowed)

    def test_pep723_header_and_shebang(self):
        text = (ROOT / "scripts" / "state_agents.py").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/usr/bin/env python3\n"))
        head = text.split('"""', 1)[0]
        self.assertIn("# requires-python = \">=3.11\"", head)
        self.assertIn("# dependencies = [\"duckdb>=1.1.0\"]", head)


if __name__ == "__main__":
    unittest.main()
