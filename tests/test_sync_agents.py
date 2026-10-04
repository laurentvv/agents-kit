"""Tests for scripts/sync_agents.py - standard library only (unittest).

Run: uv run --no-project python -m unittest discover -s tests -v
No canon version and no section title is hardcoded: bumping the version of the
common block must not break any test.
"""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "sync_agents.py"
_spec = importlib.util.spec_from_file_location("sync_agents", SCRIPT)
sa = importlib.util.module_from_spec(_spec)
sys.modules["sync_agents"] = sa  # required by dataclasses
_spec.loader.exec_module(sa)

CANON = (ROOT / "agents-common.md").read_text(encoding="utf-8").strip("\n")
TODAY = date(2026, 9, 26)


def write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8", newline="\n")


def run(*args: object) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = sa.main([str(a) for a in args])
    return code, out.getvalue()


V = sa.version_of(CANON)  # current canon version
NEWER = "v999.0"  # always above the current version
assert V is not None and (0, 95) < sa.version_key(V) < sa.version_key(NEWER)


def with_line(block: str, line: str) -> str:
    """Simulated local edit: one line added right before the END marker."""
    lines = block.split("\n")
    return "\n".join(lines[:-1] + [line, ""] + lines[-1:])


def block_version(canon: str, version: str, marker: str | None = None) -> str:
    """Canon variant: another version in the BEGIN marker (optionally another marker name)
    and a line of its own."""
    first, rest = canon.split("\n", 1)
    first = re.sub(r"(BEGIN:)(agents-comm(?:on|un))(\s+)v[0-9.]+",
                   lambda m: f"{m[1]}{marker or m[2]}{m[3]}{version}", first, count=1)
    if marker:
        rest = re.sub(r"END:agents-comm(?:on|un)", f"END:{marker}", rest)
    return with_line(first + "\n" + rest, f"- content specific to {version}")


OLD = block_version(CANON, "v0.9")  # older published version (registered in the isolated kit)
LEGACY = block_version(CANON, "v0.8", marker="agents-commun")  # v1.x marker name
assert sa.version_of(OLD) == "v0.9" and "BEGIN:agents-commun v0.8" in LEGACY


def managed_file(block: str = CANON, specific: str = "## §7 Project-specific\n\n- local rule\n") -> str:
    return f"# AGENTS.md - test\n\n{block}\n\n---\n\n{specific}"


def is_subsequence(small: list[str], big: list[str]) -> bool:
    it = iter(big)
    return all(line in it for line in small)


# ------------------------------------------------------------- real repository

class KitInvariants(unittest.TestCase):
    def test_canon_registered(self):
        self.assertIsNone(sa.canon_problem())
        registry = json.loads((ROOT / "agents-common.versions.json").read_text(encoding="utf-8"))
        self.assertEqual(registry[sa.version_of(CANON)], sa.fingerprint(CANON))

    def test_kit_and_template_match_the_canon(self):
        self.assertEqual(run("check", ROOT)[0], 0)
        self.assertEqual(run("check", ROOT, "--file", "template/AGENTS.template.md")[0], 0)

    def test_canon_is_generic(self):
        machine = re.compile(r"\b[A-Za-z]:[\\/]|/home/|/Users/|\\Users\\|[\w.+-]+@[\w-]+\.[a-z]{2,}")
        self.assertIsNone(machine.search(CANON), "the common block must stay generic (no path/e-mail)")

    def test_canon_is_lean_and_clean(self):
        self.assertLess(len(CANON.encode("utf-8")), 8192, "block budget: < 8 KB (loaded in every session)")
        self.assertIsNone(sa.CORRUPTION_RE.search(CANON), "escaped-markdown token in the canon")

    def test_standard_library_only(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split(".")[0])
        self.assertEqual(modules - set(sys.stdlib_module_names) - {"__future__"}, set())


class EnglishOnly(unittest.TestCase):
    """The repository is English-only: no French letters, quotes or file names come back."""

    # Built from code points so that this source file stays free of French characters itself:
    # a-grave/circumflex, c-cedilla, e-acute/grave/circumflex/diaeresis, i/o/u/y variants, oe/ae ligatures
    # (lower and upper case) and the French quotation marks.
    FRENCH_CHARS = re.compile("[" + "".join(map(chr, (
        0xE0, 0xE2, 0xE7, 0xE8, 0xE9, 0xEA, 0xEB, 0xEE, 0xEF, 0xF4, 0xF9, 0xFB, 0xFC, 0xFF, 0x153, 0xE6,
        0xC0, 0xC2, 0xC7, 0xC8, 0xC9, 0xCA, 0xCB, 0xCE, 0xCF, 0xD4, 0xD9, 0xDB, 0xDC, 0x178, 0x152, 0xC6,
        0xAB, 0xBB,
    ))) + "]")
    FRENCH_NAMES = re.compile(r"(?<![a-z])commun(?![a-z])|outillage|mesure", re.IGNORECASE)
    # ".zcode": agent-session state of the harness (plans written in the chat language,
    # i.e. French here), git-ignored, never repository content.
    # "scratch": disposable chat-language artifacts (explainer/project-dashboard skills),
    # git-ignored, never committed - the guard keeps covering everything committed.
    SKIP = frozenset({".git", "__pycache__", ".venv", "node_modules", ".ruff_cache", ".zcode", "scratch"})

    def files(self):
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in self.SKIP]
            for name in filenames:
                yield Path(dirpath) / name

    def test_no_french_characters(self):
        offenders = []
        for path in self.files():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for n, line in enumerate(text.split("\n"), 1):
                if self.FRENCH_CHARS.search(line):
                    offenders.append(f"{path.relative_to(ROOT)}:{n}")
        self.assertEqual(offenders, [])

    FRENCH_WORDS = re.compile(
        r"\b(les|des|est|pour|dans|avec|une|sont|pas|sur|qui|aux|cette|leur|chaque|fichier|fichiers"
        r"|doit|mais|comme|tout|toute|tous|ainsi|lorsque|puis|nous|vous)\b"
    )

    def test_no_french_words(self):
        """Accent-free French (e.g. a CI step name) slips past the character check."""
        offenders = []
        for path in self.files():
            if path == Path(__file__).resolve():  # Cli names the rejected legacy flags on purpose
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for n, line in enumerate(text.split("\n"), 1):
                if self.FRENCH_WORDS.search(line):
                    offenders.append(f"{path.relative_to(ROOT)}:{n}")
        self.assertEqual(offenders, [])

    def test_no_french_file_names(self):
        names = [str(p.relative_to(ROOT)) for p in self.files() if self.FRENCH_NAMES.search(p.name)]
        self.assertEqual(names, [])


# ---------------------------------------------------------------- isolated kit

class IsolatedKit(unittest.TestCase):
    """Temporary canon, registry and template: the real kit is never touched."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        kit = self.tmp / "kit"
        kit.mkdir()
        self.canon = kit / "agents-common.md"
        write(self.canon, CANON + "\n")
        self.registry = kit / "agents-common.versions.json"
        write(self.registry, json.dumps({
            "v0.8": sa.fingerprint(LEGACY), "v0.9": sa.fingerprint(OLD), V: sa.fingerprint(CANON)}))
        self.template = kit / "AGENTS.template.md"
        shutil.copy(ROOT / "template" / "AGENTS.template.md", self.template)
        for name, path in (("CANON", self.canon), ("REGISTRY", self.registry), ("TEMPLATE", self.template)):
            patch = mock.patch.object(sa, name, path)
            patch.start()
            self.addCleanup(patch.stop)
        self.fleet = self.tmp / "fleet"
        self.fleet.mkdir()

    def repo(self, name: str, content: str | bytes | None = None) -> Path:
        d = self.fleet / name
        d.mkdir()
        if isinstance(content, bytes):
            (d / "AGENTS.md").write_bytes(content)
        elif content is not None:
            write(d / "AGENTS.md", content)
        return d

    def state(self, text: str) -> str:
        return sa.analyze(text).state

    def set_canon(self, text: str) -> None:
        write(self.canon, text + "\n")


class Analyze(IsolatedKit):
    def test_up_to_date(self):
        self.assertEqual(self.state(managed_file()), "up_to_date")

    def test_bom_and_crlf(self):  # BEGIN marker on the very first line, right after the BOM
        def windows(block: str) -> bytes:
            return b"\xef\xbb\xbf" + f"{block}\n\n## §7\n- r\n".replace("\n", "\r\n").encode("utf-8")

        d = self.repo("bom", windows(CANON))
        self.assertEqual(self.state(sa.read_text(d / "AGENTS.md")), "up_to_date")
        old = self.repo("old", windows(OLD))
        self.assertEqual(run("sync", old)[0], 0)
        self.assertEqual((old / "AGENTS.md").read_bytes(), f"{CANON}\n\n## §7\n- r\n".encode())

    def test_behind(self):
        self.assertEqual(self.state(managed_file(OLD)), "behind")

    def test_hand_edited(self):
        self.assertEqual(self.state(managed_file(with_line(CANON, "- local addition"))), "hand_edited")

    def test_ahead(self):
        self.assertEqual(self.state(managed_file(block_version(CANON, NEWER))), "ahead")

    def test_bad_markers(self):
        self.assertEqual(self.state(managed_file() + "\n" + CANON + "\n"), "bad_markers")
        no_end = "\n".join(line for line in managed_file().split("\n") if not sa.END_RE.match(line))
        self.assertEqual(self.state(no_end), "bad_markers")

    def test_marker_quoted_in_prose(self):
        text = "# Project\n\nA line `<!-- BEGIN:agents-common v1.0 -->` then `<!-- END:agents-common -->`.\n"
        self.assertEqual(self.state(text), "unmanaged")

    def test_generated_blocks(self):
        openspec = "<!-- OPENSPEC:START -->\n# OpenSpec\nUse openspec.\n<!-- OPENSPEC:END -->\n"
        self.assertEqual(self.state(openspec), "generated")
        nextjs = (
            "<!-- BEGIN:nextjs-agent-rules -->\n# Next\n<!-- END:nextjs-agent-rules -->\n\n# fire_UI\n\n"
            + "".join(f"- project rule {i}\n" for i in range(6))
        )
        self.assertEqual(self.state(nextjs), "generated_mixed")

    def test_corrupted(self):
        self.assertEqual(self.state("\\# Title\n\n\\*\\*bold\\*\\*&#x20;\n"), "corrupted")


class Legacy(IsolatedKit):
    """v1.x blocks use the `agents-commun` marker name; sync migrates them to the current one."""

    def test_legacy_block_is_behind_and_sync_migrates_it(self):
        specific = "## §7 Specific\n\n- rule A\n- [2026-09-01] lesson\n"
        d = self.repo("legacy", managed_file(LEGACY, specific))
        self.assertEqual(self.state(sa.read_text(d / "AGENTS.md")), "behind")
        self.assertEqual(run("sync", d)[0], 0)
        self.assertEqual((d / "AGENTS.md").read_bytes(), managed_file(CANON, specific).encode("utf-8"))
        self.assertNotIn("agents-commun", sa.read_text(d / "AGENTS.md"))

    def test_hand_edited_legacy_block_is_refused(self):
        d = self.repo("legacy", managed_file(with_line(LEGACY, "- lesson written inside the block")))
        before = (d / "AGENTS.md").read_bytes()
        code, out = run("sync", d)
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", out)
        self.assertEqual((d / "AGENTS.md").read_bytes(), before)

    def test_legacy_and_new_block_together_are_invalid(self):
        self.assertEqual(self.state(managed_file(LEGACY) + "\n" + CANON + "\n"), "bad_markers")


class Audit(IsolatedKit):
    def test_non_utf8_file_does_not_stop_the_audit(self):
        self.repo("old", "# Caf\xe9\n".encode("cp1252"))
        self.repo("good", managed_file())
        code, out = run("audit", self.fleet)
        self.assertEqual(code, 0)
        self.assertIn("unreadable", out)
        self.assertIn("up to date", out)

    def test_exclusions(self):
        self.repo("backup_2026", "# frozen\n")
        self.repo("vendor-x", "# third party\n")
        self.repo("active", "# to migrate\n")
        write(self.fleet / ".agents-kit-ignore", "# frozen backups\nbackup_*\n")
        code, out = run("audit", self.fleet, "--exclude", "vendor-*")
        self.assertEqual(code, 0)
        self.assertIn("2 excluded", out)
        self.assertIn("1 unmanaged (to migrate)", out)

    def test_strict(self):
        self.repo("good", managed_file())
        self.assertEqual(run("audit", self.fleet, "--strict")[0], 0)
        self.repo("late", managed_file(OLD))
        self.assertEqual(run("audit", self.fleet, "--strict")[0], 1)
        self.assertEqual(run("audit", self.fleet, "--strict", "--exclude", "late")[0], 0)


class Sync(IsolatedKit):
    def test_behind_is_synced_and_specific_part_kept(self):
        d = self.repo("r", managed_file(OLD))
        self.assertEqual(run("sync", d)[0], 0)
        self.assertEqual((d / "AGENTS.md").read_bytes(), managed_file().encode("utf-8"))

    def test_refused_without_force(self):
        for name, block in (("edited", with_line(CANON, "- local lesson")), ("ahead", block_version(CANON, NEWER))):
            d = self.repo(name, managed_file(block))
            before = (d / "AGENTS.md").read_bytes()
            code, out = run("sync", d)
            self.assertEqual(code, 1, name)
            self.assertIn("REFUSED", out)
            self.assertEqual((d / "AGENTS.md").read_bytes(), before, name)

    def test_force_keeps_the_specific_part(self):
        specific = "## §7 Specific\n\n- rule A\n- rule B - with a dash\n\n### Pitfalls\n- [2026-09-01] x\n"
        d = self.repo("m", managed_file(with_line(CANON, "- local lesson"), specific))
        self.assertEqual(run("sync", d, "--force")[0], 0)
        self.assertEqual((d / "AGENTS.md").read_bytes(), managed_file(CANON, specific).encode("utf-8"))

    def test_up_to_date_is_not_rewritten(self):
        d = self.repo("ok", managed_file())
        os.utime(d / "AGENTS.md", (1_000_000_000, 1_000_000_000))
        code, out = run("sync", d)
        self.assertEqual(code, 0)
        self.assertIn("ALREADY UP TO DATE", out)
        self.assertEqual((d / "AGENTS.md").stat().st_mtime, 1_000_000_000)

    def test_dry_run(self):
        d = self.repo("r", managed_file(OLD))
        before = (d / "AGENTS.md").read_bytes()
        code, out = run("sync", d, "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("+++ AGENTS.md (after sync)", out)
        self.assertIn("-- content specific to v0.9", out)
        self.assertEqual((d / "AGENTS.md").read_bytes(), before)

    def test_check_diff(self):
        d = self.repo("m", managed_file(with_line(CANON, "- local lesson")))
        code, out = run("check", d, "--diff")
        self.assertEqual(code, 1)
        self.assertIn("-- local lesson", out)

    def test_unregistered_canon_is_never_distributed(self):
        r = self.repo("r", managed_file(OLD))
        n = self.repo("n", "# Project\n\n- rule\n")
        empty = self.repo("empty")
        self.set_canon(with_line(CANON, "- silent edit"))
        before_r, before_n = (r / "AGENTS.md").read_bytes(), (n / "AGENTS.md").read_bytes()
        for args in (("sync", r), ("adopt", n), ("init", empty)):
            code, out = run(*args)
            self.assertEqual(code, 2, args[0])
            self.assertIn("REFUSED", out)
        self.assertEqual((r / "AGENTS.md").read_bytes(), before_r)
        self.assertEqual((n / "AGENTS.md").read_bytes(), before_n)
        self.assertFalse((empty / "AGENTS.md").exists())


class Version(IsolatedKit):
    def test_status(self):
        self.assertEqual(run("version")[0], 0)
        self.set_canon(block_version(CANON, NEWER))
        self.assertEqual(run("version")[0], 1)

    def test_published_version_is_never_rewritten(self):
        self.set_canon(with_line(CANON, "- changed without a version bump"))
        before = self.registry.read_bytes()
        code, out = run("version", "--register")
        self.assertEqual(code, 1)
        self.assertIn("already published", out)
        self.assertEqual(self.registry.read_bytes(), before)

    def test_invalid_registry(self):
        for content in ('{"latest": "abc"}', "[1, 2]", "{not json"):
            write(self.registry, content)
            code, out = run("version")
            self.assertEqual(code, 2, content)
            self.assertIn("INVALID REGISTRY", out)

    def test_lower_version_is_refused(self):
        self.set_canon(block_version(CANON, "v0.95"))
        self.assertEqual(run("version", "--register")[0], 1)

    def test_new_version_then_fleet_behind(self):
        d = self.repo("current", managed_file())
        new = block_version(CANON, NEWER)
        self.set_canon(new)
        self.assertEqual(run("version", "--register")[0], 0)
        self.assertEqual(json.loads(self.registry.read_text(encoding="utf-8"))[NEWER], sa.fingerprint(new))
        self.assertEqual(sa.analyze(sa.read_text(d / "AGENTS.md")).state, "behind")
        self.assertEqual(run("sync", d)[0], 0)
        self.assertEqual(sa.analyze(sa.read_text(d / "AGENTS.md")).state, "up_to_date")


class Adopt(IsolatedKit):
    def adopt(self, d: Path, original: str) -> list[str]:
        self.assertEqual(run("adopt", d)[0], 0)
        after = sa.read_text(d / "AGENTS.md").split("\n")
        self.assertTrue(is_subsequence(original.split("\n"), after), "an original line disappeared")
        self.assertEqual(run("check", d)[0], 0)
        return after

    def test_after_title_and_lead(self):
        original = "# My repo\n\n> Intro lead.\n\n## Rules\n- a\n- b\n"
        after = self.adopt(self.repo("d", original), original)
        start = next(i for i, line in enumerate(after) if sa.BEGIN_RE.match(line))
        self.assertEqual(after[start - 2], "> Intro lead.")
        self.assertLess(after.index("## §7 Project-specific"), after.index("## Rules"))

    def test_after_leading_generated_block(self):
        original = (
            "<!-- BEGIN:nextjs-agent-rules -->\n# Next\n<!-- END:nextjs-agent-rules -->\n\n"
            "# fire_UI\n\n## Stack\n" + "".join(f"- r{i}\n" for i in range(6))
        )
        after = self.adopt(self.repo("d", original), original)
        start = next(i for i, line in enumerate(after) if sa.BEGIN_RE.match(line))
        self.assertGreater(start, after.index("# fire_UI"))

    def test_dry_run(self):
        d = self.repo("d", "# X\n\n- r\n")
        code, out = run("adopt", d, "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("+## §7 Project-specific", out)
        self.assertEqual(sa.read_text(d / "AGENTS.md"), "# X\n\n- r\n")

    def test_refusals(self):
        self.assertEqual(run("adopt", self.repo("managed", managed_file()))[0], 2)
        corrupted = self.repo("corrupted", "\\# Title\n\\*\\*x\\*\\*\n")
        self.assertEqual(run("adopt", corrupted)[0], 1)
        self.assertEqual(run("adopt", corrupted, "--force")[0], 0)


class Init(IsolatedKit):
    def test_missing_folder(self):
        code, out = run("init", self.fleet / "does-not-exist")
        self.assertEqual(code, 2)
        self.assertIn("FOLDER NOT FOUND", out)

    def test_stale_template_gets_the_canon(self):
        text = self.template.read_text(encoding="utf-8")
        write(self.template, sa.replace_block(text, sa.analyze(text).bounds, OLD))
        d = self.repo("new")
        self.assertEqual(run("init", d, "--name", "My Project")[0], 0)
        text = sa.read_text(d / "AGENTS.md")
        self.assertEqual(sa.analyze(text).state, "up_to_date")
        self.assertIn("# AGENTS.md", text)
        self.assertIn("My Project", text)
        self.assertNotIn("<REPO NAME>", text)

    def test_ledger_next_to_existing_agents_md(self):
        d = self.repo("existing", "# Existing\n")
        code, out = run("init", d, "--ledger")
        self.assertEqual(code, 0)
        self.assertIn("ALREADY EXISTS", out)
        self.assertEqual(sa.read_text(d / "AGENTS.md"), "# Existing\n")
        for f in sa.LEDGER_FILES:
            self.assertTrue((d / f).is_file(), f)
        self.assertIn("# Validation Contract", sa.read_text(d / "contract.md"))
        self.assertEqual(run("init", self.repo("other", "# A\n"))[0], 2)


class Cli(unittest.TestCase):
    def test_old_french_flags_are_rejected(self):
        for args in (["check", ".", "--fichier", "x"], ["init", ".", "--nom", "x"], ["audit", "--exclure", "x"],
                     ["version", "--enregistrer"], ["ledger", ".", "--statut", "x"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
                sa.main(args)
            self.assertEqual(cm.exception.code, 2, args)


# ---------------------------------------------------------------------- ledger

def valid_ledger(base: Path, month: str = "2026-09") -> None:
    base.mkdir(parents=True, exist_ok=True)
    features = [
        {"id": "F-01", "name": "a", "description": "...", "status": "in_progress", "dependencies": []},
        {"id": "F-02", "name": "b", "description": "...", "status": "pending", "dependencies": ["F-01", "F-00"]},
    ]
    write(base / "feature_list.json", json.dumps({"features": features}))
    archive = [{"id": "F-00", "name": "z", "status": "completed", "dependencies": []}]
    write(base / "feature_list_archive.json", json.dumps({"features": archive}))
    write(base / "contract.md", "# Contract\n\n" + "".join(f"- [ ] C{i:02d}: criterion\n" for i in range(1, 16)))
    write(base / "progress.md", "# Sprint\n")
    write(base / "log.md", f"# Log\n\n## [{month}-01] init | Start.\n## [{month}-02] gen  | Next.\n")


class Ledger(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, True)

    def check(self, **options) -> tuple[int, str]:
        params = {"folder": None, "extra_statuses": [], "extra_types": [], "variant_b": False, "strict": False}
        params.update(options)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sa.cmd_ledger(self.repo, today=TODAY, **params)
        return code, out.getvalue()

    def test_valid(self):
        valid_ledger(self.repo)
        code, out = self.check(strict=True)
        self.assertEqual(code, 0, out)
        self.assertIn("0 error(s), 0 warning(s)", out)

    def test_errors(self):
        valid_ledger(self.repo)
        write(self.repo / "feature_list.json", '{"features": [')
        self.assertEqual(self.check()[0], 1)
        write(self.repo / "feature_list.json", json.dumps({"features": [
            {"id": "F-01", "name": "a", "status": "pending"}, {"id": "F-01", "name": "b", "status": "pending"}]}))
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("duplicate id F-01", out)
        valid_ledger(self.repo)
        (self.repo / "progress.md").unlink()
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("progress.md - missing", out)

    def test_warnings(self):
        valid_ledger(self.repo)
        write(self.repo / "feature_list.json", json.dumps({"features": [
            {"id": "F-01", "name": "a", "status": "awaiting_playtest", "dependencies": []},
            {"id": "F-02", "name": "b", "status": "completed", "dependencies": ["F-99"]}]}))
        write(self.repo / "log.md", "# Log\n\n"
              "## [2026-08-31] gen  | Previous month.\n"
              "## [2026-09-01] rot  | Project type.\n"
              f"## [2026-09-02] gen  | {'x' * 220}\n"
              "## 2026-09-03 gen | no brackets\n")
        write(self.repo / "contract.md", "# Contract\n\n- [ ] C01: single criterion\n")
        code, out = self.check()
        self.assertEqual(code, 0, out)
        for expected in ('non-standard status "awaiting_playtest"', "move it to feature_list_archive.json",
                         "unknown dependency F-99", 'non-standard type "rot"', "budget ~200",
                         "outside the current month", "malformed entry", '1 "- [ ]" criterion(s)'):
            self.assertIn(expected, out)
        self.assertEqual(self.check(strict=True)[0], 1)
        code, out = self.check(extra_statuses=["awaiting_playtest"], extra_types=["rot"])
        self.assertNotIn("non-standard", out)

    def test_unexpected_types_do_not_crash(self):
        valid_ledger(self.repo)
        write(self.repo / "feature_list.json", json.dumps({"features": [
            {"id": "F-01", "name": "a", "status": ["pending"], "dependencies": [{"id": "F-00"}]}]}))
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn('missing or non-text "status"', out)
        self.assertIn("unknown dependency", out)

    def test_agents_folder_and_variant_b(self):
        valid_ledger(self.repo / ".agents")
        (self.repo / ".agents" / "log.md").unlink()
        self.assertEqual(self.check()[0], 1)
        code, out = self.check(variant_b=True)
        self.assertEqual(code, 0, out)
        self.assertIn(".agents", out)

    def test_between_sprints(self):
        valid_ledger(self.repo)
        (self.repo / "contract.md").unlink()
        (self.repo / "progress.md").unlink()
        code, out = self.check()
        self.assertEqual(code, 1, "active sprint: contract and progress are required")
        write(self.repo / "feature_list.json", '{"features": []}')
        code, out = self.check(strict=True)
        self.assertEqual(code, 0, out)
        self.assertIn("between sprints", out)

    def test_no_ledger(self):
        self.assertEqual(self.check()[0], 2)


if __name__ == "__main__":
    unittest.main()
