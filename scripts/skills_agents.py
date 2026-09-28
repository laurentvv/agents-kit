#!/usr/bin/env python3
"""agents-kit - vendor common agent skills and deploy them to the fleet.

Where sync_agents.py manages the common AGENTS.md BLOCK, this script manages
common SKILLS (folders holding a SKILL.md, e.g. github.com/obra/superpowers):

  skills add <github-url> [--skill NAME] [--ref REF] [--force]
                          Import a skill folder from a GitHub repository into the
                          kit (skills/<NAME>/) and record it in skills.json
                          (source, resolved commit sha, per-file sha256).
                          --force: replace an already vendored skill.
  skills list             Vendored skills: name, source@ref, files, import date.
  skills check <repo>     Are the installed skills identical to the kit?
                          (--diff: list the files that would change)
  skills sync <repo>      Install/update <repo>/.agents/skills/<NAME>/ from the kit
                          and maintain the lock .agents/skills/.agents-kit.json.
                          Refuses a hand-edited install without --force;
                          --dry-run: print the plan without writing.
  skills audit [root]     State of every <root>/<repo>/.agents/skills
                          (same sweep as sync_agents audit; --strict for CI).

Installed skills are byte-for-byte copies. The lock fingerprints (sha256) tell an
updatable install (files match the lock, the kit moved on) from a hand-edited one
(sync would overwrite local changes). Orphan skills (no longer vendored) are
pruned by sync. Skill content is external data: review what you vendor.

GitHub access uses the standard library only (no npx/Node): tarball download via
codeload.github.com, commit resolution via api.github.com (unauthenticated:
60 requests/hour). check/sync/audit need no network: the kit copy is the single
distribution source.

Exit codes: 0 = ok, 1 = drift / refusal (human action needed), 2 = input error.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import importlib.util
import io
import json
import re
import shutil
import sys
import tarfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:  # reuse the helpers of sync_agents.py when it is importable (tests preload it)
    from sync_agents import (
        InputError,
        local_today,
        read_exclusions,
        read_text,
        write_text,
    )
except ImportError:  # loaded from outside scripts/ without a preload: load by path
    _spec = importlib.util.spec_from_file_location(
        "sync_agents", Path(__file__).resolve().parent / "sync_agents.py")
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules.setdefault("sync_agents", _mod)
    _spec.loader.exec_module(_mod)
    from sync_agents import (
        InputError,
        local_today,
        read_exclusions,
        read_text,
        write_text,
    )

KIT = Path(__file__).resolve().parent.parent
SKILLS_DIR = KIT / "skills"        # vendored skills (distribution source)
REGISTRY = KIT / "skills.json"     # kit-side registry: source, ref, fingerprints
DEPLOY_DIR = Path(".agents") / "skills"  # inside consumer repositories
LOCK_NAME = ".agents-kit.json"     # per-repo lock, inside DEPLOY_DIR

SKILL_MARKER = "SKILL.md"
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
SHA_RE = re.compile(r"[0-9a-f]{40}")
GITHUB_RE = re.compile(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")
SPDX_RE = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9._-]+)")
LICENSE_BASENAMES = ("LICENSE", "LICENCE", "COPYING")

STATES = {
    "up_to_date": "up to date",
    "behind": "behind (the kit moved on)",
    "hand_edited": "hand-edited",
    "excluded": "excluded",
}
ACTION_LABEL = {  # short word per plan action, for the audit details
    "install": "missing",
    "update": "behind",
    "hand_edited": "hand-edited",
    "unmanaged": "unmanaged",
    "orphan": "orphan",
}


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprints_of(folder: Path) -> dict[str, str]:
    """relative posix path -> sha256, for every file under folder."""
    out: dict[str, str] = {}
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            out[p.relative_to(folder).as_posix()] = hash_bytes(p.read_bytes())
    return out


def kit_copy_matches(name: str, entry: dict) -> bool:
    folder = SKILLS_DIR / name
    return folder.is_dir() and fingerprints_of(folder) == entry.get("files")


# ------------------------------------------------------------------ registry

def load_registry() -> dict[str, dict]:
    if not REGISTRY.is_file():
        return {}
    try:
        data = json.loads(read_text(REGISTRY))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise InputError(f"INVALID REGISTRY: {REGISTRY} ({e})") from None
    skills = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(skills, dict):
        raise InputError(f'INVALID REGISTRY: {REGISTRY} (expected an object with a "skills" object)')
    for name, entry in skills.items():
        if not (isinstance(entry, dict) and isinstance(entry.get("source"), str)
                and isinstance(entry.get("ref"), str) and isinstance(entry.get("files"), dict)):
            raise InputError(f"INVALID REGISTRY: {REGISTRY} (bad entry for {name})")
    return skills


def save_registry(skills: dict[str, dict]) -> None:
    data = {"version": 1, "skills": {k: skills[k] for k in sorted(skills)}}
    write_text(REGISTRY, json.dumps(data, indent=2) + "\n")


def load_lock(skills_dir: Path) -> dict[str, dict]:
    p = skills_dir / LOCK_NAME
    if not p.is_file():
        return {}
    try:
        data = json.loads(read_text(p))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise InputError(f"INVALID LOCK: {p} ({e})") from None
    skills = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(skills, dict):
        raise InputError(f'INVALID LOCK: {p} (expected an object with a "skills" object)')
    for name, entry in skills.items():
        if not (isinstance(entry, dict) and isinstance(entry.get("files"), dict)):
            raise InputError(f"INVALID LOCK: {p} (bad entry for {name})")
    return skills


def save_lock(skills_dir: Path, lock: dict[str, dict]) -> None:
    skills_dir.mkdir(parents=True, exist_ok=True)
    data = {"version": 1, "skills": {k: lock[k] for k in sorted(lock)}}
    write_text(skills_dir / LOCK_NAME, json.dumps(data, indent=2) + "\n")


# -------------------------------------------------------------------- github

def _http_get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "agents-kit skills"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        raise InputError(f"GITHUB: HTTP {e.code} on {url} (unknown repo/ref or rate limit?)") from None
    except (urllib.error.URLError, OSError) as e:
        raise InputError(f"NETWORK: {e} - check the connection") from None


def resolve_ref(slug: str, ref: str | None) -> str:
    """Commit sha of the requested ref (a 40-hex sha is taken as is)."""
    if ref is not None and SHA_RE.fullmatch(ref):
        return ref
    url = f"https://api.github.com/repos/{slug}/commits/{ref or 'HEAD'}"
    try:
        data = json.loads(_http_get(url).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise InputError(f"GITHUB: unusable answer for {slug} ({ref or 'HEAD'})") from None
    sha = data.get("sha") if isinstance(data, dict) else None
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise InputError(f"GITHUB: no commit sha for {slug} ({ref or 'HEAD'})")
    return sha


def fetch_tarball(slug: str, ref: str) -> bytes:
    return _http_get(f"https://codeload.github.com/{slug}/tar.gz/{ref}")


def slug_of(url: str) -> str:
    m = GITHUB_RE.search(url)
    if m is None:
        raise InputError(f"NOT A GITHUB URL: {url} (expected https://github.com/<owner>/<repo>)")
    return f"{m.group(1)}/{m.group(2)}"


def extract_skill(data: bytes, name: str | None) -> tuple[str, dict[str, bytes]]:
    """Pick the skill folder in a repository tarball: (name, {relative path: content})."""
    files: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
            candidates: dict[str, str] = {}  # skill folder (after the top dir) -> SKILL.md member
            for m in tar.getmembers():
                parts = m.name.split("/")
                if m.isfile() and len(parts) >= 3 and parts[-1] == SKILL_MARKER:
                    candidates["/".join(parts[1:-1])] = m.name
            if name is None:
                if len(candidates) == 1:
                    name = next(iter(candidates)).split("/")[-1]
                else:
                    known = ", ".join(sorted(candidates)) or "none found"
                    raise InputError(f"NO SKILL SELECTED: pass --skill NAME (candidates: {known})")
            folder = next((f for f in candidates if f.split("/")[-1] == name), None)
            if folder is None:
                known = ", ".join(sorted(candidates)) or "none found"
                raise InputError(f"SKILL NOT FOUND: no {SKILL_MARKER} under a folder named {name}"
                                 f" (candidates: {known})")
            if NAME_RE.fullmatch(name) is None:
                raise InputError(f"INVALID SKILL NAME: {name} (letters, digits, dot, dash, underscore)")
            prefix = folder + "/"
            for m in tar.getmembers():
                _top, sep, rel = m.name.partition("/")
                if not sep or not rel.startswith(prefix):
                    continue
                if m.isdir():
                    continue
                if m.issym() or m.islnk() or not m.isfile():
                    print(f"WARNING: skipped non-regular tar member {m.name}")
                    continue
                rel_parts = rel[len(prefix):].split("/")
                if any(part in ("", ".", "..") for part in rel_parts):
                    raise InputError(f"UNSAFE PATH in the tarball: {m.name}")
                files[rel[len(prefix):]] = tar.extractfile(m).read()
    except tarfile.TarError:
        raise InputError("GITHUB: not a readable tarball") from None
    if SKILL_MARKER not in files:
        raise InputError(f"NO SKILL MARKER: {folder} holds no {SKILL_MARKER}")
    return name, files


LICENSE_TEXTS = (  # SPDX identifier for the usual license texts, before falling back to the file name
    ("Apache License", "Apache-2.0"),
    ("GNU GENERAL PUBLIC LICENSE", "GPL"),
    ("GNU Lesser General Public License", "LGPL"),
    ("MIT License", "MIT"),
    ("Mozilla Public License", "MPL"),
    ("The Unlicense", "Unlicense"),
    ("Permission is hereby granted, free of charge", "MIT"),
    ("ISC License", "ISC"),
)


def detect_license(data: bytes) -> str | None:
    """SPDX identifier (best effort) of a top-level license file, if any."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
            for m in tar.getmembers():
                parts = m.name.split("/")
                if len(parts) == 2 and m.isfile() and parts[1].upper().startswith(LICENSE_BASENAMES):
                    head = tar.extractfile(m).read(2048).decode("utf-8", errors="replace")
                    spdx = SPDX_RE.search(head)
                    if spdx:
                        return spdx.group(1)
                    return next((s for marker, s in LICENSE_TEXTS if marker in head), parts[1])
    except tarfile.TarError:
        return None
    return None


# --------------------------------------------------------------------- plans

@dataclass
class SkillPlan:
    name: str
    action: str  # install | update | up_to_date | hand_edited | unmanaged | orphan
    detail: str = ""
    writes: list[str] = field(default_factory=list)
    removes: list[str] = field(default_factory=list)


def plan_repo(repo: Path, registry: dict[str, dict], only: str | None) -> tuple[Path, dict, list[SkillPlan]]:
    if only is not None and only not in registry:
        known = ", ".join(sorted(registry)) or "none"
        raise InputError(f"UNKNOWN SKILL: {only} (vendored in the kit: {known})")
    skills_dir = repo / DEPLOY_DIR
    lock = load_lock(skills_dir)
    plans: list[SkillPlan] = []
    for name in sorted(registry):
        if only is not None and name != only:
            continue
        entry = registry[name]
        target = skills_dir / name
        installed = fingerprints_of(target) if target.is_dir() else {}
        locked = lock.get(name)
        if locked is None and not target.exists():
            plans.append(SkillPlan(name, "install", f"({len(entry['files'])} file(s))",
                                   writes=sorted(entry["files"])))
        elif locked is None:
            plans.append(SkillPlan(name, "unmanaged", "(folder exists, not installed by agents-kit)",
                                   writes=sorted(entry["files"]),
                                   removes=sorted(k for k in installed if k not in entry["files"])))
        elif installed != locked.get("files"):
            plans.append(SkillPlan(name, "hand_edited", "(changed since install)",
                                   writes=sorted(entry["files"]),
                                   removes=sorted(k for k in installed if k not in entry["files"])))
        elif ((entry["files"], entry["ref"], entry["source"])
                == (locked.get("files"), locked.get("ref"), locked.get("source"))):
            plans.append(SkillPlan(name, "up_to_date", f"({entry['ref'][:12]})"))
        else:
            plans.append(SkillPlan(name, "update", f"({entry['ref'][:12]})",
                                   writes=sorted(k for k, v in entry["files"].items() if installed.get(k) != v),
                                   removes=sorted(k for k in installed if k not in entry["files"])))
    plans.extend(SkillPlan(name, "orphan", "(no longer vendored in the kit)")
                 for name in sorted(lock) if name not in registry and (only is None or name == only))
    return skills_dir, lock, plans


def repo_state(plans: list[SkillPlan]) -> str:
    actions = {p.action for p in plans}
    if actions & {"hand_edited", "unmanaged"}:
        return "hand_edited"
    return "up_to_date" if actions <= {"up_to_date"} else "behind"


def apply_plan(skills_dir: Path, plan: SkillPlan, entry: dict) -> None:
    target = skills_dir / plan.name
    for rel in plan.removes:
        (target / rel).unlink(missing_ok=True)
        folder = (target / rel).parent
        while folder != target:
            try:
                folder.rmdir()
            except OSError:
                break
            folder = folder.parent
    for rel in plan.writes:
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((SKILLS_DIR / plan.name / rel).read_bytes())


# ------------------------------------------------------------------ commands

def cmd_add(url: str, name: str | None, ref: str | None, force: bool) -> int:
    slug = slug_of(url)
    sha = resolve_ref(slug, ref)
    data = fetch_tarball(slug, sha)
    name, files = extract_skill(data, name)
    entry_files = {rel: hash_bytes(content) for rel, content in sorted(files.items())}
    registry = load_registry()
    existing = registry.get(name)
    if existing is not None:
        dirty = not kit_copy_matches(name, existing)
        if existing.get("files") == entry_files and existing.get("ref") == sha and not dirty:
            print(f"ALREADY UP TO DATE: {name} ({slug}@{sha[:12]})")
            return 0
        if not force:
            print(f"REFUSED: {name} is already vendored ({existing.get('ref', '?')[:12]}) - --force to replace it.")
            if dirty:
                print("  The kit copy was hand-edited (does not match skills.json).")
            return 1
        if dirty:
            print("  WARNING: the kit copy was hand-edited; --force overwrites it.")
    target = SKILLS_DIR / name
    if target.exists():
        shutil.rmtree(target)
    for rel, content in sorted(files.items()):
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
    entry = {"source": slug, "ref": sha, "imported": local_today().isoformat(), "files": entry_files}
    license_id = detect_license(data)
    if license_id:
        entry["license"] = license_id
    registry[name] = entry
    save_registry(registry)
    print(f"{'Replaced' if existing else 'Added'}: {name} ({slug}@{sha[:12]}, {len(files)} file(s))")
    print("Deploy it with: uv run --no-project python scripts/skills_agents.py sync <repo>")
    return 0


def cmd_list() -> int:
    registry = load_registry()
    if not registry:
        print("No skill vendored yet: skills add <github-url> --skill <name>")
        return 0
    for name, entry in sorted(registry.items()):
        license_id = f"  license {entry['license']}" if entry.get("license") else ""
        print(f"  {name:<28} {entry['source']}@{entry['ref'][:12]}  "
              f"{len(entry['files'])} file(s)  imported {entry.get('imported', '?')}{license_id}")
    return 0


def print_plans(skills_dir: Path, plans: list[SkillPlan]) -> None:
    for p in plans:
        print(f"  {p.action:<11} {skills_dir / p.name} {p.detail}".rstrip())
        for rel in p.removes:
            print(f"    - {rel}")
        for rel in p.writes:
            print(f"    + {rel}")


def cmd_check(repo: Path, only: str | None, diff: bool) -> int:
    registry = load_registry()
    skills_dir, lock, plans = plan_repo(repo, registry, only)
    if not plans:
        print("NO SKILLS: nothing vendored in the kit and nothing installed")
        return 2
    if not skills_dir.is_dir() and not lock:
        print(f"NO SKILLS: {skills_dir} (nothing installed - 'skills sync' installs the kit skills)")
        return 2
    print(f"Skills of {repo} (kit source):")
    print_plans(skills_dir, plans)
    drift = [p for p in plans if p.action != "up_to_date"]
    if not drift:
        print("UP TO DATE")
        return 0
    if diff:
        print("\n--diff only lists the actions above (nothing is written).")
    return 1


def cmd_sync(repo: Path, only: str | None, force: bool, dry_run: bool) -> int:
    registry = load_registry()
    skills_dir, lock, plans = plan_repo(repo, registry, only)
    refused = [p for p in plans if p.action in ("hand_edited", "unmanaged")]
    if refused and not force:
        for p in refused:
            print(f"REFUSED: {skills_dir / p.name} - {STATES['hand_edited']} {p.detail}")
        print("  sync would overwrite local changes: 'skills check --diff', move what must stay, then --force.")
        return 1
    changed = False
    for p in plans:
        if p.action == "up_to_date":
            continue
        print(f"  {p.action:<11} {skills_dir / p.name} {p.detail}".rstrip())
        if dry_run:
            for rel in p.removes:
                print(f"    - {rel}")
            for rel in p.writes:
                print(f"    + {rel}")
            continue
        changed = True
        if p.action == "orphan":
            target = skills_dir / p.name
            if target.exists():
                shutil.rmtree(target)
            del lock[p.name]
            continue
        apply_plan(skills_dir, p, registry[p.name])
        lock[p.name] = {"source": registry[p.name]["source"], "ref": registry[p.name]["ref"],
                        "files": registry[p.name]["files"]}
    if dry_run:
        print("\nDry run: nothing written.")
        return 0
    if changed:
        save_lock(skills_dir, lock)
    done = sum(1 for p in plans if p.action != "up_to_date")
    print(f"Applied: {done} skill(s)" if done else "Nothing to do")
    return 0


def cmd_audit(root: Path, exclude: list[str], strict: bool) -> int:
    registry = load_registry()
    if not registry:
        print("NO SKILLS: nothing vendored in the kit - nothing to audit")
        return 2
    patterns = exclude + read_exclusions(root)
    print(f"Audit of the .agents/skills folders under: {root}\n")
    stats: dict[str, int] = {}
    for d in sorted(root.iterdir()):
        skills_dir = d / DEPLOY_DIR
        if not (d.is_dir() and skills_dir.is_dir()):
            continue
        if any(fnmatch.fnmatch(d.name, p) for p in patterns):
            state, detail = "excluded", ""
        else:
            _, _, plans = plan_repo(d, registry, None)
            if not skills_dir.is_dir() or (not (skills_dir / LOCK_NAME).is_file() and not any(skills_dir.iterdir())):
                continue
            counts: dict[str, int] = {}
            for p in plans:
                counts[p.action] = counts.get(p.action, 0) + 1
            state = repo_state(plans)
            labels = [f"{n} {ACTION_LABEL[a]}" for a, n in sorted(counts.items()) if a != "up_to_date"]
            detail = f"({', '.join(labels)})" if labels else ""
        stats[state] = stats.get(state, 0) + 1
        print(f"  {STATES[state]:<34} {d}  {detail}".rstrip())
    order = list(STATES)
    summary = ", ".join(f"{n} {STATES[s]}" for s, n in sorted(stats.items(), key=lambda kv: order.index(kv[0])))
    print(f"\nSummary: {summary or 'no skills folder found'}")
    return 1 if strict and set(stats) - {"up_to_date", "excluded"} else 0


# ---------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="agents-kit - common skills for the fleet")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="vendor a skill from a GitHub repository")
    a.add_argument("url", help="https://github.com/<owner>/<repo>")
    a.add_argument("--skill", help="skill folder name in the repository (default: the only one)")
    a.add_argument("--ref", help="branch, tag or commit (default: default branch HEAD)")
    a.add_argument("--force", action="store_true", help="replace an already vendored skill")

    sub.add_parser("list", help="vendored skills")

    c = sub.add_parser("check", help="are the installed skills up to date?")
    s = sub.add_parser("sync", help="install/update the kit skills in a repository")
    for p in (c, s):
        p.add_argument("repo", type=Path)
        p.add_argument("--skill", help="limit to this skill")
    c.add_argument("--diff", action="store_true", help="list the files that would change")
    s.add_argument("--force", action="store_true", help="overwrite a hand-edited install")
    s.add_argument("--dry-run", action="store_true", help="print the plan without writing")

    au = sub.add_parser("audit", help="state of every .agents/skills under <root>")
    au.add_argument("root", nargs="?", type=Path, default=KIT.parent)
    au.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                    help="folder to skip (glob pattern, repeatable)")
    au.add_argument("--strict", action="store_true", help="exit 1 unless every repo is up to date")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "add":
            return cmd_add(args.url, args.skill, args.ref, args.force)
        if args.cmd == "list":
            return cmd_list()
        if args.cmd == "check":
            return cmd_check(args.repo.resolve(), args.skill, args.diff)
        if args.cmd == "sync":
            return cmd_sync(args.repo.resolve(), args.skill, args.force, args.dry_run)
        if args.cmd == "audit":
            if not args.root.is_dir():
                print(f"Root not found: {args.root}")
                return 2
            return cmd_audit(args.root, args.exclude, args.strict)
        ap.error(f"unknown command {args.cmd!r}")
    except InputError as e:
        print(e)
        return 2
    return 2


if __name__ == "__main__":
    # Windows console / Git Bash pipe: an unrepresentable character must never crash the script.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    sys.exit(main())
