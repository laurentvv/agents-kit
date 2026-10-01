"""Tests for scripts/skills_agents.py - standard library only, zero network.

The GitHub seam (resolve_ref / fetch_tarball) is mocked with in-memory tarballs;
urlopen is poisoned in setUp so that any accidental network attempt fails the test.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tarfile
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

SHA1 = "a" * 40
SHA2 = "b" * 40
BODY1 = b"# Skill body\n"
BODY2 = b"# Skill body v2\n"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_sync = _load("sync_agents")  # preloaded so skills_agents reuses the same module
sa = _load("skills_agents")
REAL_RESOLVE = sa.resolve_ref  # kept aside: tests patch sa.resolve_ref with a mock


def write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8", newline="\n")


def run(*args: object) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = sa.main([str(a) for a in args])
    return code, out.getvalue()


def fake_tarball(name: str = "using-x", body: bytes = BODY1, extra_skill: bool = True) -> bytes:
    """In-memory GitHub tarball: one requested skill, optionally a second one, MIT license."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        def add(rel: str, data: bytes) -> None:
            info = tarfile.TarInfo(f"superpowers-main/{rel}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))

        add(f"skills/{name}/SKILL.md", body)
        add(f"skills/{name}/extra.md", b"notes\n")
        if extra_skill:
            add("skills/other/SKILL.md", b"# other\n")
        add("LICENSE", b"MIT License\n\nSPDX-License-Identifier: MIT\n")
    return buf.getvalue()


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Kit(unittest.TestCase):
    """Isolated kit (temp skills/ and skills.json) and a poisoned network."""

    def setUp(self):
        poison = mock.patch.object(urllib.request, "urlopen",
                                   side_effect=AssertionError("no network in the tests"))
        poison.start()
        self.addCleanup(poison.stop)
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        kit = self.tmp / "kit"
        (kit / "skills").mkdir(parents=True)
        self.registry = kit / "skills.json"
        for attr, value in (("KIT", kit), ("SKILLS_DIR", kit / "skills"), ("REGISTRY", self.registry)):
            patch = mock.patch.object(sa, attr, value)
            patch.start()
            self.addCleanup(patch.stop)
        self.fleet = self.tmp / "fleet"
        self.fleet.mkdir()

    def github(self, sha: str = SHA1, tarball: bytes | None = None) -> mock.Mock:
        """Mock the GitHub seam; returns the resolve_ref mock for call assertions."""
        resolve = mock.Mock(return_value=sha)
        for target, value in (("resolve_ref", resolve),
                              ("fetch_tarball", mock.Mock(return_value=tarball or fake_tarball()))):
            patch = mock.patch.object(sa, target, value)
            patch.start()
            self.addCleanup(patch.stop)
        return resolve

    def vendored(self, name: str = "using-x", sha: str = SHA1, body: bytes = BODY1) -> None:
        """Vendor a skill through the real `add` path (--force: idempotent for updates)."""
        self.github(sha, fake_tarball(name, body))
        code, out = run("add", "https://github.com/obra/superpowers", "--skill", name, "--force")
        self.assertEqual(code, 0, out)

    def repo(self, name: str) -> Path:
        d = self.fleet / name
        d.mkdir()
        return d

    def lock(self, repo: Path) -> dict:
        return json.loads((repo / ".agents" / "skills" / ".agents-kit.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------- add

class Add(Kit):
    def test_vendors_files_and_registers(self):
        self.github()
        code, out = run("add", "https://github.com/obra/superpowers", "--skill", "using-x")
        self.assertEqual(code, 0, out)
        folder = sa.SKILLS_DIR / "using-x"
        self.assertEqual((folder / "SKILL.md").read_bytes(), BODY1)
        entry = json.loads(self.registry.read_text(encoding="utf-8"))["skills"]["using-x"]
        self.assertEqual(entry["source"], "obra/superpowers")
        self.assertEqual(entry["ref"], SHA1)
        self.assertEqual(entry["files"], {"SKILL.md": sha256_of(BODY1),
                                          "extra.md": sha256_of(b"notes\n")})
        self.assertEqual(entry["license"], "MIT")
        self.assertIn("Added: using-x", out)

    def test_ref_resolved_and_sha_passthrough(self):
        resolve = self.github()
        self.assertEqual(run("add", "https://github.com/obra/superpowers", "--skill", "using-x")[0], 0)
        self.assertEqual(resolve.call_args, mock.call("obra/superpowers", None))
        resolve2 = self.github()
        self.assertEqual(run("add", "https://github.com/obra/superpowers", "--skill", "using-x",
                             "--ref", "v1.2.3")[0], 0)
        self.assertEqual(resolve2.call_args, mock.call("obra/superpowers", "v1.2.3"))
        # a 40-hex ref is taken as is by the REAL resolve_ref (urlopen stays poisoned)
        self.assertEqual(REAL_RESOLVE("obra/superpowers", SHA2), SHA2)

    def test_without_skill_flag(self):
        self.github(tarball=fake_tarball("only-skill", extra_skill=False))
        code, out = run("add", "https://github.com/obra/superpowers")
        self.assertEqual(code, 0, out)
        self.assertTrue((sa.SKILLS_DIR / "only-skill" / "SKILL.md").is_file())
        self.github()  # two candidate skills: the flag becomes required
        code, out = run("add", "https://github.com/obra/superpowers")
        self.assertEqual(code, 2)
        self.assertIn("NO SKILL SELECTED", out)
        self.assertIn("other", out)

    def test_same_content_is_idempotent(self):
        self.vendored()
        self.github()  # same sha, same content
        code, out = run("add", "https://github.com/obra/superpowers", "--skill", "using-x")
        self.assertEqual(code, 0, out)
        self.assertIn("ALREADY UP TO DATE", out)

    def test_new_upstream_refused_then_force_replaces(self):
        self.vendored()
        before = self.registry.read_bytes()
        self.github(SHA2, fake_tarball("using-x", BODY2))
        code, out = run("add", "https://github.com/obra/superpowers", "--skill", "using-x")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", out)
        self.assertEqual(self.registry.read_bytes(), before)
        code, out = run("add", "https://github.com/obra/superpowers", "--skill", "using-x", "--force")
        self.assertEqual(code, 0, out)
        self.assertEqual((sa.SKILLS_DIR / "using-x" / "SKILL.md").read_bytes(), BODY2)
        self.assertEqual(json.loads(self.registry.read_text(encoding="utf-8"))["skills"]["using-x"]["ref"], SHA2)

    def test_hand_edited_kit_copy_refused_without_force(self):
        self.vendored()
        write(sa.SKILLS_DIR / "using-x" / "SKILL.md", "# hand edit\n")
        self.github(SHA2, fake_tarball("using-x", b"# upstream moved\n"))
        code, out = run("add", "https://github.com/obra/superpowers", "--skill", "using-x")
        self.assertEqual(code, 1)
        self.assertIn("hand-edited", out)
        self.assertEqual((sa.SKILLS_DIR / "using-x" / "SKILL.md").read_text(encoding="utf-8"), "# hand edit\n")
        code, out = run("add", "https://github.com/obra/superpowers", "--skill", "using-x", "--force")
        self.assertEqual(code, 0, out)
        self.assertEqual((sa.SKILLS_DIR / "using-x" / "SKILL.md").read_bytes(), b"# upstream moved\n")

    def test_bad_url_and_unknown_skill(self):
        self.assertEqual(run("add", "https://gitlab.com/obra/superpowers")[0], 2)
        code, out = run("sync", self.repo("r"), "--skill", "ghost")
        self.assertEqual(code, 2)
        self.assertIn("UNKNOWN SKILL", out)


class List(Kit):
    def test_list(self):
        code, out = run("list")
        self.assertEqual(code, 0)
        self.assertIn("No skill vendored", out)
        self.vendored()
        code, out = run("list")
        self.assertEqual(code, 0)
        self.assertIn("using-x", out)
        self.assertIn(f"obra/superpowers@{SHA1[:12]}", out)
        self.assertIn("2 file(s)", out)
        self.assertIn("license MIT", out)


# ----------------------------------------------------------------- author

class Author(Kit):
    def write_skill(self, name: str = "docs-x", body: bytes = BODY1) -> Path:
        folder = sa.SKILLS_DIR / name
        folder.mkdir(parents=True, exist_ok=True)
        write(folder / "SKILL.md", body.decode("utf-8"))
        return folder

    def test_registers_files_and_license(self):
        self.write_skill()
        code, out = run("author", "docs-x", "--license", "MIT")
        self.assertEqual(code, 0, out)
        entry = json.loads(self.registry.read_text(encoding="utf-8"))["skills"]["docs-x"]
        self.assertEqual(entry["source"], sa.AUTHORED_SOURCE)
        self.assertEqual(entry["files"], {"SKILL.md": sha256_of(BODY1)})
        self.assertEqual(entry["license"], "MIT")
        self.assertEqual(entry["imported"], sa.local_today().isoformat())
        self.assertIn("Registered: docs-x", out)

    def test_refuses_missing_folder_or_marker(self):
        code, out = run("author", "ghost")
        self.assertEqual(code, 2)
        self.assertIn("NO SKILL MARKER", out)
        (sa.SKILLS_DIR / "hollow").mkdir()
        code, out = run("author", "hollow")
        self.assertEqual(code, 2)
        self.assertIn("NO SKILL MARKER", out)

    def test_invalid_name(self):
        code, out = run("author", "../escape")
        self.assertEqual(code, 2)
        self.assertIn("INVALID SKILL NAME", out)

    def test_idempotent_then_force_refingerprints(self):
        self.write_skill()
        self.assertEqual(run("author", "docs-x")[0], 0)
        code, out = run("author", "docs-x")
        self.assertEqual(code, 0, out)
        self.assertIn("ALREADY UP TO DATE", out)
        write(sa.SKILLS_DIR / "docs-x" / "SKILL.md", "# edited\n")
        code, out = run("author", "docs-x")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", out)
        code, out = run("author", "docs-x", "--force")
        self.assertEqual(code, 0, out)
        self.assertIn("Re-registered", out)
        entry = json.loads(self.registry.read_text(encoding="utf-8"))["skills"]["docs-x"]
        self.assertEqual(entry["files"]["SKILL.md"], sha256_of(b"# edited\n"))

    def test_refuses_to_shadow_a_github_vendored_skill(self):
        self.vendored()
        self.write_skill(name="using-x")
        code, out = run("author", "using-x")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", out)
        self.assertIn("obra/superpowers", out)

    def test_update_skips_authored_skills_offline(self):
        # urlopen stays poisoned: any GitHub attempt for the authored skill must not happen
        self.write_skill()
        self.assertEqual(run("author", "docs-x")[0], 0)
        code, out = run("update")
        self.assertEqual(code, 0, out)
        self.assertIn("authored     docs-x", out)
        self.assertNotIn("FAILED", out)

    def test_authored_skill_deploys_like_any_other(self):
        self.write_skill()
        self.assertEqual(run("author", "docs-x", "--license", "MIT")[0], 0)
        r = self.repo("r")
        self.assertEqual(run("sync", r)[0], 0)
        self.assertEqual((r / ".agents" / "skills" / "docs-x" / "SKILL.md").read_bytes(), BODY1)
        self.assertEqual(self.lock(r)["skills"]["docs-x"]["source"], sa.AUTHORED_SOURCE)
        self.assertEqual(run("check", r)[0], 0)

    def test_list_shows_authored_origin(self):
        self.write_skill()
        self.assertEqual(run("author", "docs-x")[0], 0)
        code, out = run("list")
        self.assertEqual(code, 0, out)
        self.assertIn("docs-x", out)
        self.assertIn("authored in the kit", out)


# ------------------------------------------------------------------- deploy

class Sync(Kit):
    def test_installs_and_writes_the_lock(self):
        self.vendored()
        r = self.repo("r")
        self.assertEqual(run("sync", r)[0], 0)
        target = r / ".agents" / "skills" / "using-x"
        self.assertEqual((target / "SKILL.md").read_bytes(), BODY1)
        entry = self.lock(r)["skills"]["using-x"]
        self.assertEqual(entry["source"], "obra/superpowers")
        self.assertEqual(entry["ref"], SHA1)
        self.assertEqual(entry["files"]["SKILL.md"], sha256_of(BODY1))

    def test_up_to_date_writes_nothing(self):
        self.vendored()
        r = self.repo("r")
        self.assertEqual(run("sync", r)[0], 0)
        skill_file = r / ".agents" / "skills" / "using-x" / "SKILL.md"
        lock_file = r / ".agents" / "skills" / ".agents-kit.json"
        for f in (skill_file, lock_file):
            os.utime(f, (1_000_000_000, 1_000_000_000))
        code, out = run("sync", r)
        self.assertEqual(code, 0, out)
        self.assertEqual(skill_file.stat().st_mtime, 1_000_000_000)
        self.assertEqual(lock_file.stat().st_mtime, 1_000_000_000)

    def test_behind_is_updated(self):
        self.vendored()
        r = self.repo("r")
        self.assertEqual(run("sync", r)[0], 0)
        self.vendored(sha=SHA2, body=BODY2)  # the kit moved on
        code, out = run("sync", r)
        self.assertEqual(code, 0, out)
        self.assertEqual((r / ".agents" / "skills" / "using-x" / "SKILL.md").read_bytes(), BODY2)
        self.assertEqual(self.lock(r)["skills"]["using-x"]["ref"], SHA2)

    def test_hand_edited_refused_then_force(self):
        self.vendored()
        r = self.repo("r")
        self.assertEqual(run("sync", r)[0], 0)
        skill_file = r / ".agents" / "skills" / "using-x" / "SKILL.md"
        write(skill_file, "# local lesson\n")
        code, out = run("sync", r)
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", out)
        self.assertEqual(skill_file.read_text(encoding="utf-8"), "# local lesson\n")
        self.assertEqual(run("sync", r, "--force")[0], 0)
        self.assertEqual(skill_file.read_bytes(), BODY1)
        self.assertEqual(run("check", r)[0], 0)

    def test_dry_run_writes_nothing(self):
        self.vendored()
        r = self.repo("r")
        self.assertEqual(run("sync", r)[0], 0)
        self.vendored(sha=SHA2, body=BODY2)
        before = (r / ".agents" / "skills" / "using-x" / "SKILL.md").read_bytes()
        code, out = run("sync", r, "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("+ SKILL.md", out)
        self.assertIn("Dry run", out)
        self.assertEqual((r / ".agents" / "skills" / "using-x" / "SKILL.md").read_bytes(), before)

    def test_single_skill_filter(self):
        self.vendored()
        self.vendored(name="other")
        r = self.repo("r")
        self.assertEqual(run("sync", r, "--skill", "other")[0], 0)
        self.assertTrue((r / ".agents" / "skills" / "other" / "SKILL.md").is_file())
        self.assertFalse((r / ".agents" / "skills" / "using-x").exists())

    def test_orphan_is_pruned(self):
        self.vendored()
        r = self.repo("r")
        self.assertEqual(run("sync", r)[0], 0)
        sa.save_registry({})  # the kit no longer vendors it
        code, out = run("sync", r, "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("orphan", out)
        self.assertTrue((r / ".agents" / "skills" / "using-x").exists())
        code, out = run("sync", r)
        self.assertEqual(code, 0, out)
        self.assertFalse((r / ".agents" / "skills" / "using-x").exists())
        self.assertEqual(self.lock(r)["skills"], {})


class Check(Kit):
    def test_exit_codes(self):
        self.vendored()
        r = self.repo("r")
        self.assertEqual(run("check", r)[0], 2)  # nothing installed at all
        self.vendored(name="other")
        self.assertEqual(run("sync", r, "--skill", "using-x")[0], 0)
        code, out = run("check", r)  # one skill missing
        self.assertEqual(code, 1, out)
        self.assertIn("install", out)
        self.assertEqual(run("sync", r)[0], 0)
        code, out = run("check", r)
        self.assertEqual(code, 0, out)
        self.assertIn("UP TO DATE", out)

    def test_empty_registry_is_an_input_error(self):
        write(self.registry, json.dumps({"version": 1, "skills": {}}))
        code, out = run("check", self.repo("r"))
        self.assertEqual(code, 2)
        self.assertIn("NO SKILLS", out)


class Audit(Kit):
    def test_sweep_strict_and_exclusions(self):
        self.vendored()
        good, late, edited = self.repo("good"), self.repo("late"), self.repo("edited")
        for r in (good, late, edited):
            self.assertEqual(run("sync", r)[0], 0)
        self.vendored(sha=SHA2, body=BODY2)  # the kit moves on: every repo is behind
        self.assertEqual(run("sync", good)[0], 0)  # good catches up
        skill = edited / ".agents" / "skills" / "using-x" / "SKILL.md"
        write(skill, "# local\n")  # edited becomes hand-edited
        code, out = run("audit", self.fleet)
        self.assertEqual(code, 0)
        self.assertIn("up to date", out)
        self.assertIn("behind", out)
        self.assertIn("hand-edited", out)
        self.assertEqual(run("audit", self.fleet, "--strict")[0], 1)
        self.assertEqual(run("audit", self.fleet, "--strict", "--exclude", "late")[0], 1)
        write(self.fleet / ".agents-kit-ignore", "edited\n")
        self.assertEqual(run("audit", self.fleet, "--strict", "--exclude", "late")[0], 0)

    def test_repos_without_skills_are_skipped(self):
        self.vendored()
        self.repo("plain")
        code, out = run("audit", self.fleet)
        self.assertEqual(code, 0, out)
        self.assertNotIn("plain", out)


class Encoding(Kit):
    def test_non_utf8_lock_and_registry_no_traceback(self):
        self.vendored()
        r = self.repo("r")
        lock_file = r / ".agents" / "skills" / ".agents-kit.json"
        lock_file.parent.mkdir(parents=True)
        lock_file.write_bytes(b"\xff\xfe garbage")
        code, out = run("sync", r)
        self.assertEqual(code, 2)
        self.assertIn("INVALID LOCK", out)
        self.registry.write_bytes(b"\xff\xfe garbage")
        code, out = run("check", r)
        self.assertEqual(code, 2)
        self.assertIn("INVALID REGISTRY", out)


# ------------------------------------------------------- update (online) / deploy

class Update(Kit):
    def test_upstream_unchanged_is_up_to_date(self):
        self.vendored()
        before = self.registry.read_bytes()
        self.github()  # same sha, same content
        code, out = run("update")
        self.assertEqual(code, 0, out)
        self.assertIn("up to date   using-x", out)
        self.assertEqual(self.registry.read_bytes(), before)

    def test_upstream_moved_updates_the_vendored_copy(self):
        self.vendored()
        self.github(SHA2, fake_tarball("using-x", BODY2))
        code, out = run("update")
        self.assertEqual(code, 0, out)
        self.assertIn("update       using-x", out)
        self.assertIn("+ SKILL.md", out)
        self.assertEqual((sa.SKILLS_DIR / "using-x" / "SKILL.md").read_bytes(), BODY2)
        entry = json.loads(self.registry.read_text(encoding="utf-8"))["skills"]["using-x"]
        self.assertEqual(entry["ref"], SHA2)
        self.assertEqual(entry["updated"], sa.local_today().isoformat())
        # the fleet sees the update through a plain sync
        r = self.repo("r")
        self.assertEqual(run("sync", r)[0], 0)
        self.assertEqual((r / ".agents" / "skills" / "using-x" / "SKILL.md").read_bytes(), BODY2)

    def test_repin_when_content_identical(self):
        self.vendored()
        self.github(SHA2, fake_tarball("using-x", BODY1))  # new commit, same files
        code, out = run("update")
        self.assertEqual(code, 0, out)
        self.assertIn("re-pin       using-x", out)
        self.assertEqual(json.loads(self.registry.read_text(encoding="utf-8"))["skills"]["using-x"]["ref"], SHA2)
        self.assertEqual((sa.SKILLS_DIR / "using-x" / "SKILL.md").read_bytes(), BODY1)

    def test_hand_edited_kit_copy_refused_then_force(self):
        self.vendored()
        write(sa.SKILLS_DIR / "using-x" / "SKILL.md", "# local edit\n")
        self.github(SHA2, fake_tarball("using-x", BODY2))
        code, out = run("update")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", out)
        self.assertEqual((sa.SKILLS_DIR / "using-x" / "SKILL.md").read_text(encoding="utf-8"), "# local edit\n")
        code, out = run("update", "--force")
        self.assertEqual(code, 0, out)
        self.assertEqual((sa.SKILLS_DIR / "using-x" / "SKILL.md").read_bytes(), BODY2)

    def test_dry_run_writes_nothing(self):
        self.vendored()
        before = self.registry.read_bytes()
        self.github(SHA2, fake_tarball("using-x", BODY2))
        code, out = run("update", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("update       using-x", out)
        self.assertIn("dry run: nothing written", out)
        self.assertEqual(self.registry.read_bytes(), before)
        self.assertEqual((sa.SKILLS_DIR / "using-x" / "SKILL.md").read_bytes(), BODY1)

    def test_skill_and_ref_flags(self):
        self.vendored()
        resolve = self.github(SHA2, fake_tarball("using-x", BODY2))
        code, out = run("update", "--skill", "using-x", "--ref", "v9.9")
        self.assertEqual(code, 0, out)
        self.assertEqual(resolve.call_args, mock.call("obra/superpowers", "v9.9"))
        self.assertEqual((sa.SKILLS_DIR / "using-x" / "SKILL.md").read_bytes(), BODY2)

    def test_ref_without_skill_and_unknown_skill(self):
        self.vendored()
        code, out = run("update", "--ref", "v1.0")
        self.assertEqual(code, 2)
        self.assertIn("--ref requires --skill", out)
        code, out = run("update", "--skill", "ghost")
        self.assertEqual(code, 2)
        self.assertIn("UNKNOWN SKILL", out)

    def test_upstream_failure_isolated(self):
        self.vendored()
        self.vendored(name="other")
        registry = json.loads(self.registry.read_text(encoding="utf-8"))
        registry["skills"]["other"]["source"] = "someone/gone"
        write(self.registry, json.dumps(registry))
        reasons = {"someone/gone": "GITHUB: HTTP 404"}

        def resolve(slug, ref):
            if slug in reasons:
                raise sa.InputError(reasons[slug])
            return SHA2

        def fetch(slug, sha):
            if slug in reasons:
                raise sa.InputError(reasons[slug])
            return fake_tarball("using-x", BODY2)

        for target, value in (("resolve_ref", mock.Mock(side_effect=resolve)),
                              ("fetch_tarball", mock.Mock(side_effect=fetch))):
            patch = mock.patch.object(sa, target, value)
            patch.start()
            self.addCleanup(patch.stop)
        code, out = run("update")
        self.assertEqual(code, 1, out)
        self.assertIn("FAILED       other", out)
        self.assertIn("update       using-x", out)
        self.assertEqual((sa.SKILLS_DIR / "using-x" / "SKILL.md").read_bytes(), BODY2)


class Deploy(Kit):
    def prep(self):
        self.vendored()
        self.up_to_date = self.repo("fresh")
        self.behind = self.repo("late")
        self.edited = self.repo("edited")
        for r in (self.up_to_date, self.behind, self.edited):
            self.assertEqual(run("sync", r)[0], 0)
        self.vendored(sha=SHA2, body=BODY2)  # the kit moves on
        self.assertEqual(run("sync", self.up_to_date)[0], 0)  # fresh catches up
        write(self.edited / ".agents" / "skills" / "using-x" / "SKILL.md", "# local\n")

    def test_fleet_states(self):
        self.prep()
        self.repo("no-skills")  # skipped: no .agents/skills
        code, out = run("deploy", self.fleet)
        self.assertEqual(code, 1, out)
        self.assertIn("up_to_date", out)
        self.assertIn("applied", out)
        self.assertIn("refused", out)
        self.assertNotIn("no-skills", out)
        self.assertEqual((self.behind / ".agents" / "skills" / "using-x" / "SKILL.md").read_bytes(), BODY2)
        self.assertEqual(
            (self.edited / ".agents" / "skills" / "using-x" / "SKILL.md").read_text(encoding="utf-8"), "# local\n")

    def test_force_overwrites_the_refused_one(self):
        self.prep()
        code, out = run("deploy", self.fleet, "--force")
        self.assertEqual(code, 0, out)
        self.assertEqual((self.edited / ".agents" / "skills" / "using-x" / "SKILL.md").read_bytes(), BODY2)

    def test_dry_run_writes_nothing(self):
        self.prep()
        before = (self.behind / ".agents" / "skills" / "using-x" / "SKILL.md").read_bytes()
        code, out = run("deploy", self.fleet, "--dry-run")
        self.assertEqual(code, 1, out)
        self.assertIn("+ SKILL.md", out)
        self.assertEqual((self.behind / ".agents" / "skills" / "using-x" / "SKILL.md").read_bytes(), before)

    def test_dry_run_reports_up_to_date_repos_correctly(self):
        # regression: dry-run used to report every repo as "applied"
        self.vendored()
        a, b = self.repo("a"), self.repo("b")
        for r in (a, b):
            self.assertEqual(run("sync", r)[0], 0)
        code, out = run("deploy", self.fleet, "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("2 up_to_date", out)
        self.assertNotIn("applied", out.replace("up_to_date", ""))
        self.assertEqual(run("deploy", self.fleet, "--dry-run", "--strict")[0], 0)

    def test_exclusions_and_strict(self):
        self.prep()
        self.assertEqual(run("deploy", self.fleet, "--exclude", "late", "--exclude", "edited", "--strict")[0], 0)
        write(self.fleet / ".agents-kit-ignore", "edited\nlate\n")
        self.assertEqual(run("deploy", self.fleet, "--strict")[0], 0)

    def test_skill_filter(self):
        self.vendored()
        self.vendored(name="other")
        r = self.repo("r")
        (r / ".agents" / "skills").mkdir(parents=True)  # deploy skips repos without the folder
        code, out = run("deploy", self.fleet, "--skill", "other", "--force")
        self.assertEqual(code, 0, out)
        self.assertTrue((r / ".agents" / "skills" / "other").exists())
        self.assertFalse((r / ".agents" / "skills" / "using-x").exists())

    def test_broken_repo_does_not_block_the_fleet(self):
        self.prep()
        broken = self.repo("broken")
        skills_dir = broken / ".agents" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / ".agents-kit.json").write_bytes(b"\xff\xfe garbage")
        code, out = run("deploy", self.fleet)
        self.assertEqual(code, 1, out)
        self.assertIn("error", out)
        self.assertEqual((self.behind / ".agents" / "skills" / "using-x" / "SKILL.md").read_bytes(), BODY2)


class Invariants(unittest.TestCase):
    def test_stdlib_only(self):
        tree = ast.parse((SCRIPTS / "skills_agents.py").read_text(encoding="utf-8"))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split(".")[0])
        self.assertEqual(modules - set(sys.stdlib_module_names) - {"__future__", "sync_agents"}, set())

    def test_sync_agents_surface_unchanged(self):
        # the fleet CI calls exactly this command line: it must keep working
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(_sync.main(["check", str(ROOT)]), 0)
        self.assertIn("UP TO DATE", out.getvalue())


if __name__ == "__main__":
    unittest.main()
