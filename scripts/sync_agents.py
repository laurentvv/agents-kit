#!/usr/bin/env python3
"""agents-kit - manage the common AGENTS.md block.

The common block is delimited by the HTML markers
``<!-- BEGIN:agents-common ... -->`` / ``<!-- END:agents-common -->``
(same mechanism as the managed blocks of Next.js or OpenSpec): the script
only replaces what lies BETWEEN the markers and preserves all of the
repository-specific content. A marker takes a whole line.

Commands
--------
  audit [root]              State of every <root>/<repo>/AGENTS.md
                             (default: the parent folder of agents-kit).
                             --exclude PATTERN (repeatable) or <root>/.agents-kit-ignore;
                             --strict: exit 1 if a file is neither up to date, generated nor excluded.
  check <repo>              Is the common block identical to the canon? (--diff: show the gap)
  sync  <repo>              Resync the common block from agents-common.md.
                             Refuses to overwrite a hand-edited block or one newer than the
                             canon (--force to override); --dry-run: diff without writing.
  init  <repo> [--name N]   Create AGENTS.md from the template (common block always fresh).
                             --force: overwrite an existing file.
                             --ledger: also create the missing state files.
  adopt <repo>              Insert the common block into an existing unmanaged AGENTS.md without
                             losing anything: the previous content moves to §7 (--dry-run available).
  ledger <repo>             Check (read-only) the 4 state files against §2 of the common block.
  version                   Canon version + fingerprint; --register: publish a new version.

Option --file <path> (check/sync/adopt): target another file than AGENTS.md
at the repository root (e.g. ``template/AGENTS.template.md`` for the kit itself).

Registry ``agents-common.versions.json``: sha256 fingerprint of each published version
of the block. It tells a "behind" block (older version, intact: safe to sync) from a
"hand-edited" one (sync would overwrite local changes), and forbids distributing a
canon that was changed without a version bump.

Legacy markers ``agents-commun`` (v1.x) are still recognized so that ``sync`` can
migrate a repository to the current markers.

No external dependency - Python 3.11+ (standard library only).
Exit codes: 0 = ok, 1 = drift / refusal (human action needed), 2 = input error.
"""
from __future__ import annotations

import argparse
import difflib
import fnmatch
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent  # root of the agents-kit repository
CANON = KIT / "agents-common.md"
TEMPLATE = KIT / "template" / "AGENTS.template.md"
REGISTRY = KIT / "agents-common.versions.json"
EXCLUDE_FILE = ".agents-kit-ignore"

# "agents-commun" is the v1.x marker name, accepted so that sync can migrate old blocks.
_MARKER = r"agents-(?:common|commun)"
BEGIN_RE = re.compile(rf"^\s*<!--\s*BEGIN:{_MARKER}\b")
END_RE = re.compile(rf"^\s*<!--\s*END:{_MARKER}\b")
VERSION_RE = re.compile(rf"BEGIN:{_MARKER}\s+(v[0-9]+(?:\.[0-9]+)*)")
CORRUPTION_RE = re.compile(r"^\\[#*]|\\\*\\\*|&#x20;", re.MULTILINE)
# Blocks managed by other tools (never touched): keyword found on their marker lines;
# the end line also contains "END".
GENERATED_FAMILIES = ("OPENSPEC:", "nextjs-agent-rules", "NEXT-AGENTS-MD-")
PROJECT_CONTENT_THRESHOLD = 5  # non-blank lines outside generated blocks beyond which we migrate

STATES = {
    "up_to_date": "up to date",
    "behind": "behind",
    "hand_edited": "hand-edited",
    "ahead": "ahead of the kit",
    "bad_markers": "invalid markers",
    "generated": "generated (OpenSpec/Next.js - leave alone)",
    "generated_mixed": "unmanaged, keep generated block (to migrate)",
    "corrupted": "corrupted (escaped markdown) - rewrite",
    "unmanaged": "unmanaged (to migrate)",
    "unreadable": "unreadable (not UTF-8)",
    "excluded": "excluded",
}
HEALTHY_STATES = {"up_to_date", "generated", "excluded"}  # anything else fails audit --strict

SPECIFIC_HEADER = [
    "---",
    "",
    "## §7 Project-specific",
    "",
    (
        "> **Previous content kept as-is by `adopt`** - remove what the common block (§1-§6)"
        " already covers; keep the specific part (mission, commands, invariants, dated pitfalls)."
    ),
]


class InputError(Exception):
    """Unusable input: message printed as-is, exit code 2."""


# ------------------------------------------------------------------ helpers

def read_text(p: Path) -> str:
    """UTF-8 text (BOM tolerated), line endings normalized to LF."""
    return p.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def read_target(p: Path) -> str:
    try:
        return read_text(p)
    except UnicodeDecodeError:
        raise InputError(f"UNREADABLE: {p} (not UTF-8 - convert it to UTF-8)") from None


def write_text(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8", newline="\n")


def local_today() -> date:
    """Today's date in the machine's time zone (the one writing the log)."""
    return datetime.now().astimezone().date()


def version_of(block: str) -> str | None:
    m = VERSION_RE.search(block)
    return m.group(1) if m else None


def version_key(v: str) -> tuple[int, ...]:
    """'v1.10' -> (1, 10); trailing zeros are ignored (v1 == v1.0)."""
    numbers = [int(n) for n in v.lstrip("v").split(".")]
    while len(numbers) > 1 and numbers[-1] == 0:
        numbers.pop()
    return tuple(numbers)


def fingerprint(block: str) -> str:
    return hashlib.sha256(block.encode("utf-8")).hexdigest()


def fingerprints() -> dict[str, str]:
    if not REGISTRY.is_file():
        return {}
    try:
        data = json.loads(read_text(REGISTRY))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise InputError(f"INVALID REGISTRY: {REGISTRY} ({e})") from None
    valid = isinstance(data, dict) and all(
        re.fullmatch(r"v[0-9]+(\.[0-9]+)*", str(v)) and re.fullmatch(r"[0-9a-f]{64}", str(h))
        for v, h in data.items()
    )
    if not valid:
        raise InputError(f"INVALID REGISTRY: {REGISTRY} (expected an object {{\"vX.Y\": \"<sha256>\"}})")
    return data


def canonical_block() -> str:
    canon = read_text(CANON).strip("\n")
    lines = canon.split("\n")
    begins = sum(1 for line in lines if BEGIN_RE.match(line))
    ends = sum(1 for line in lines if END_RE.match(line))
    if begins != 1 or ends != 1 or not BEGIN_RE.match(lines[0]) or not END_RE.match(lines[-1]):
        raise InputError(
            f"INVALID CANON: {CANON} must start with the BEGIN line and end with the END line"
            " (exactly one of each)."
        )
    return canon


def canon_problem() -> str | None:
    """Why the canon must not be distributed, or None."""
    canon = canonical_block()
    v = version_of(canon)
    if v is None:
        return "the canon BEGIN marker carries no version (vX.Y)."
    published = fingerprints().get(v)
    if published == fingerprint(canon):
        return None
    if published is None:
        return f"canon {v} is not registered - run `version --register` after review."
    return (
        f"canon changed without a version bump: {v} is already published with another fingerprint"
        " - bump the version in the BEGIN marker, then `version --register`."
    )


def require_published_canon() -> str:
    reason = canon_problem()
    if reason:
        raise InputError(f"REFUSED: {reason}")
    return canonical_block()


def warn_canon() -> None:
    reason = canon_problem()
    if reason:
        print(f"WARNING: {reason}\n")


def print_diff(before: str, after: str, name: str, after_label: str) -> None:
    lines = difflib.unified_diff(
        before.split("\n"), after.split("\n"), f"{name} (current)", f"{name} ({after_label})", lineterm=""
    )
    print("\n".join(lines))


def replace_block(text: str, bounds: tuple[int, int], block: str) -> str:
    lines = text.split("\n")
    return "\n".join(lines[: bounds[0]] + block.split("\n") + lines[bounds[1] + 1 :])


# ----------------------------------------------------------------- analysis

@dataclass
class Analysis:
    state: str  # key of STATES
    detail: str = ""
    bounds: tuple[int, int] | None = None  # BEGIN/END line indexes, inclusive, when managed

    @property
    def label(self) -> str:
        return f"{STATES[self.state]} {self.detail}".strip()


def generated_zones(lines: list[str]) -> list[tuple[int, int]]:
    """INCLUSIVE [start, end] ranges of the blocks managed by OpenSpec / Next.js."""
    zones: list[tuple[int, int]] = []
    start, family = None, None
    for i, line in enumerate(lines):
        if "<!--" not in line:
            continue
        f = next((f for f in GENERATED_FAMILIES if f in line), None)
        if f is None:
            continue
        if start is None and "END" not in line:
            start, family = i, f
        elif start is not None and f == family and "END" in line:
            zones.append((start, i))
            start = None
    if start is not None:  # no end found: to be safe, the rest of the file is generated
        zones.append((start, len(lines) - 1))
    return zones


def analyze(text: str) -> Analysis:
    lines = text.split("\n")
    begins = [i for i, line in enumerate(lines) if BEGIN_RE.match(line)]
    ends = [i for i, line in enumerate(lines) if END_RE.match(line)]
    if begins or ends:
        if len(begins) != 1 or len(ends) != 1 or ends[0] < begins[0]:
            return Analysis("bad_markers", f"({len(begins)} BEGIN / {len(ends)} END)")
        bounds = (begins[0], ends[0])
        state, detail = compare("\n".join(lines[bounds[0] : bounds[1] + 1]))
        return Analysis(state, detail, bounds)
    zones = generated_zones(lines)
    if zones:
        inside = {i for start, end in zones for i in range(start, end + 1)}
        outside = [line for i, line in enumerate(lines) if i not in inside and line.strip()]
        return Analysis("generated_mixed" if len(outside) > PROJECT_CONTENT_THRESHOLD else "generated")
    if CORRUPTION_RE.search(text):
        return Analysis("corrupted")
    return Analysis("unmanaged")


def compare(block: str) -> tuple[str, str]:
    canon = canonical_block()
    canon_v = version_of(canon) or "?"
    if block == canon:
        return "up_to_date", f"({canon_v})"
    v = version_of(block)
    if v is None:
        return "hand_edited", "(unreadable version in the marker)"
    if canon_v != "?" and version_key(v) > version_key(canon_v):
        return "ahead", f"({v} > canon {canon_v} - update agents-kit?)"
    if fingerprints().get(v) == fingerprint(block):
        if v == canon_v:
            return "behind", f"({v} published; local canon changed without a new version)"
        return "behind", f"({v}, canon {canon_v})"
    return "hand_edited", f"({v} - see check --diff)"


# ----------------------------------------------------------------- commands

def read_exclusions(root: Path) -> list[str]:
    path = root / EXCLUDE_FILE
    if not path.is_file():
        return []
    patterns = (line.strip().rstrip("/\\") for line in read_text(path).split("\n"))
    return [p for p in patterns if p and not p.startswith("#")]


def cmd_audit(root: Path, exclude: list[str], strict: bool) -> int:
    patterns = exclude + read_exclusions(root)
    warn_canon()
    print(f"Audit of the AGENTS.md files under: {root}\n")
    stats: dict[str, int] = {}
    for d in sorted(root.iterdir()):
        target = d / "AGENTS.md"
        if not (d.is_dir() and target.is_file()):
            continue
        if any(fnmatch.fnmatch(d.name, p) for p in patterns):
            a = Analysis("excluded")
        else:
            try:
                a = analyze(read_text(target))
            except UnicodeDecodeError:
                a = Analysis("unreadable")
        stats[a.state] = stats.get(a.state, 0) + 1
        print(f"  {STATES[a.state]:<46} {target}  {a.detail}".rstrip())
    order = list(STATES)
    summary = ", ".join(f"{n} {STATES[s]}" for s, n in sorted(stats.items(), key=lambda kv: order.index(kv[0])))
    print(f"\nSummary: {summary or 'no file found'}")
    return 1 if strict and set(stats) - HEALTHY_STATES else 0


def cmd_check(repo: Path, file: str, diff: bool) -> int:
    target = repo / file
    if not target.is_file():
        print(f"MISSING: {target}")
        return 2
    warn_canon()
    text = read_target(target)
    a = analyze(text)
    if a.state == "bad_markers":
        print(f"INVALID: {target} - {a.label}")
        return 2
    if a.bounds is None:
        print(f"UNMANAGED: {target} - {a.label} (see adopt)")
        return 2
    if a.state == "up_to_date":
        print(f"UP TO DATE: {target} {a.detail}")
        return 0
    print(f"DRIFT: {target} - {a.label}")
    if diff:
        print_diff(text, replace_block(text, a.bounds, canonical_block()), file, "canon")
    return 1


def cmd_sync(repo: Path, file: str, force: bool, dry_run: bool) -> int:
    canon = require_published_canon()
    target = repo / file
    if not target.is_file():
        print(f"MISSING: {target} - use 'init' to create the file.")
        return 2
    text = read_target(target)
    a = analyze(text)
    if a.state == "bad_markers":
        print(f"INVALID: {target} - {a.label}. Fix the markers by hand.")
        return 2
    if a.bounds is None:
        print(f"UNMANAGED: {target} - {a.label}. Use 'adopt' (keeps the content) or 'init --force'.")
        return 2
    if a.state == "up_to_date":
        print(f"ALREADY UP TO DATE: {target} {a.detail}")
        return 0
    if a.state in ("hand_edited", "ahead") and not force:
        print(f"REFUSED: {target} - {a.label}")
        if a.state == "hand_edited":
            print("  The installed block is not a published version: sync would overwrite local changes.")
            print("  See 'check --diff', move what must stay to §7, then run again with --force.")
        else:
            print("  Update agents-kit (git pull) rather than downgrade; --force to downgrade anyway.")
        return 1
    new_text = replace_block(text, a.bounds, canon)
    if dry_run:
        print_diff(text, new_text, file, "after sync")
        print(f"\nDry run: {target} not modified ({a.label}).")
        return 0
    write_text(target, new_text)
    print(f"Synced: {target} - was {a.label}, now {version_of(canon)}")
    return 0


def cmd_init(repo: Path, name: str | None, force: bool, ledger: bool) -> int:
    canon = require_published_canon()
    if not repo.is_dir():
        print(f"FOLDER NOT FOUND: {repo} (create or clone the repository first)")
        return 2
    target = repo / "AGENTS.md"
    existed = target.exists()
    if existed and not force:
        print(f"ALREADY EXISTS: {target} (kept; --force to overwrite, 'adopt' to integrate it)")
        if not ledger:
            return 2
    else:
        template = read_text(TEMPLATE)
        bounds = analyze(template).bounds
        if bounds is None:
            raise InputError(f"INVALID TEMPLATE: {TEMPLATE} (common block not found)")
        # The block always comes from the canon: a template not yet resynced
        # cannot spread an old version.
        text = replace_block(template, bounds, canon).replace("<REPO NAME>", name or repo.name)
        write_text(target, text)
        print(f"{'Replaced' if existed else 'Created'}: {target}")
    if ledger:
        create_ledger(repo)
    return 0


def create_ledger(repo: Path) -> None:
    if not (repo / "feature_list.json").exists():
        write_text(repo / "feature_list.json", '{\n  "features": []\n}\n')
        print("Created: feature_list.json")
    if not (repo / "progress.md").exists():
        write_text(
            repo / "progress.md",
            "# Sprint Progress\n\n"
            "## Current Goal\n- [ ] ...\n\n"
            "## Iteration Milestones\n- [ ] ...\n\n"
            "## Contract Validation\n- Criterion 1: evidence (command run, exit code, screenshot) ...\n",
        )
        print("Created: progress.md")
    if not (repo / "contract.md").exists():
        write_text(
            repo / "contract.md",
            "# Validation Contract\n\n"
            "## Automated Acceptance Criteria\n- [ ] Criterion 1: ...\n\n"
            "## Evaluation Protocol\n"
            "* Test command: `pytest` / `npm test`\n"
            "* Expected behavior: zero warnings, zero failures.\n",
        )
        print("Created: contract.md")
    if not (repo / "log.md").exists():
        write_text(
            repo / "log.md",
            "# Execution Log (Append-Only)\n\n"
            f"## [{local_today().isoformat()}] init | agents-kit instantiation (AGENTS.md template).\n",
        )
        print("Created: log.md")


def insert_block(text: str, canon: str) -> str:
    """Put the block after the leading generated blocks and the H1 title (+ its "> " lead)."""
    lines = text.split("\n")
    zones = dict(generated_zones(lines))
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
        elif i in zones:
            i = zones[i] + 1
        else:
            break
    if i < len(lines) and lines[i].startswith("# "):
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines) and lines[j].startswith(">"):
            while j < len(lines) and lines[j].startswith(">"):
                j += 1
            i = j
        else:
            i += 1
    before, after = lines[:i], lines[i:]
    while before and not before[-1].strip():
        before.pop()
    while after and not after[0].strip():
        after.pop(0)
    insertion = ([""] if before else []) + canon.split("\n") + [""] + SPECIFIC_HEADER + [""]
    return "\n".join(before + insertion + after)


def cmd_adopt(repo: Path, file: str, force: bool, dry_run: bool) -> int:
    canon = require_published_canon()
    target = repo / file
    if not target.is_file():
        print(f"MISSING: {target} - use 'init' to create the file.")
        return 2
    text = read_target(target)
    a = analyze(text)
    if a.state == "bad_markers":
        print(f"INVALID: {target} - {a.label}. Fix the markers by hand.")
        return 2
    if a.bounds is not None:
        print(f"ALREADY MANAGED: {target} - {a.label} (use 'sync')")
        return 2
    if a.state in ("corrupted", "generated") and not force:
        print(f"REFUSED: {target} - {a.label}")
        if a.state == "corrupted":
            print("  Adopting would keep the escaped markdown: rewrite it ('init --force') or use --force.")
        else:
            print("  File entirely produced by another tool: leave it to that tool; --force to adopt anyway.")
        return 1
    new_text = insert_block(text, canon)
    if dry_run:
        print_diff(text, new_text, file, "after adopt")
        print(f"\nDry run: {target} not modified.")
        return 0
    write_text(target, new_text)
    print(f"Adopted: {target} ({version_of(canon)}) - sort the previous content moved to §7.")
    return 0


def cmd_version(register: bool) -> int:
    canon = canonical_block()
    v, h = version_of(canon), fingerprint(canon)
    registry = fingerprints()
    print(f"Canon: {v or 'no version'}, sha256 {h[:16]}...")
    if v is not None and registry.get(v) == h:
        print(f"Registered in {REGISTRY.name}.")
        return 0
    if not register or v is None:
        print(f"NOT PUBLISHABLE: {canon_problem()}")
        return 1
    if v in registry:
        print(f"REFUSED: {v} is already published with another fingerprint - bump the version in the BEGIN marker.")
        return 1
    highest = max(registry, key=version_key, default=None)
    if highest is not None and version_key(v) <= version_key(highest):
        print(f"REFUSED: {v} must be higher than the last published version ({highest}).")
        return 1
    registry[v] = h
    ordered = dict(sorted(registry.items(), key=lambda kv: version_key(kv[0])))
    write_text(REGISTRY, json.dumps(ordered, indent=2) + "\n")
    print(f"Registered: {v} in {REGISTRY.name}.")
    print("Now resync the template and the kit's AGENTS.md (sync . --file ...).")
    return 0


# ------------------------------------------------------------------- ledger

STATUSES = ("pending", "in_progress", "completed")
LOG_TYPES = ("init", "gen", "eval", "fix", "sync", "done", "err")
LEDGER_FILES = ("feature_list.json", "contract.md", "progress.md", "log.md")
LEDGER_LOCATIONS = (".", ".agents", "memory-bank")
LOG_ENTRY_RE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]\s+(\S+)\s*\|\s*\S")
CRITERION_RE = re.compile(r"^\s*[-*]\s+\[[ xX]\]", re.MULTILINE)
ENTRY_BUDGET = 200
MAX_LOG_SIZE = 150 * 1024
MIN_CRITERIA, MAX_CRITERIA = 15, 30


class Report:
    def __init__(self) -> None:
        self.lines: list[tuple[str, str, str]] = []

    def error(self, where: str, message: str) -> None:
        self.lines.append(("ERROR", where, message))

    def warn(self, where: str, message: str) -> None:
        self.lines.append(("WARN ", where, message))

    def count(self, level: str) -> int:
        return sum(1 for n, _, _ in self.lines if n.strip() == level)


def load_json(p: Path, r: Report) -> object | None:
    try:
        return json.loads(read_text(p))
    except UnicodeDecodeError:
        r.error(p.name, "not UTF-8")
    except json.JSONDecodeError as e:
        r.error(p.name, f"invalid JSON (line {e.lineno}, column {e.colno})")
    return None


def check_features(base: Path, statuses: set[str], r: Report) -> None:
    data = load_json(base / "feature_list.json", r)
    if data is None:
        return
    features = data.get("features") if isinstance(data, dict) else None
    if not isinstance(features, list):
        r.error("feature_list.json", 'expected an object { "features": [ ... ] }')
        return
    archived: set[str] = set()
    if (base / "feature_list_archive.json").is_file():
        archive = load_json(base / "feature_list_archive.json", r)
        items = archive.get("features") if isinstance(archive, dict) else archive
        if isinstance(items, list):
            archived = {f["id"] for f in items if isinstance(f, dict) and isinstance(f.get("id"), str)}
    ids = [f.get("id") for f in features if isinstance(f, dict)]
    seen: set[str] = set()
    for n, f in enumerate(features, 1):
        where = f"feature_list.json #{n}"
        if not isinstance(f, dict):
            r.error(where, "expected an object")
            continue
        fid = f.get("id")
        if not isinstance(fid, str) or not fid.strip():
            r.error(where, 'missing "id"')
        elif fid in seen:
            r.error(where, f"duplicate id {fid}")
        else:
            seen.add(fid)
            where = f"feature_list.json {fid}"
        status = f.get("status")
        if not isinstance(status, str):
            r.error(where, 'missing or non-text "status"')
        elif status not in statuses:
            r.warn(where, f'non-standard status "{status}" - declare it in §7, then --status {status}')
        elif status == "completed":
            r.warn(where, "completed: move it to feature_list_archive.json")
        if not f.get("name"):
            r.warn(where, 'missing "name"')
        deps = f.get("dependencies", [])
        if not isinstance(deps, list):
            r.error(where, '"dependencies" must be a list')
            continue
        for dep in deps:
            if not isinstance(dep, str) or (dep not in ids and dep not in archived):
                r.warn(where, f"unknown dependency {dep}")


def check_log(base: Path, types: set[str], today: date, r: Report) -> None:
    p = base / "log.md"
    size = p.stat().st_size
    if size > MAX_LOG_SIZE:
        r.warn("log.md", f"{size // 1024} KB > {MAX_LOG_SIZE // 1024} KB: rotate to docs/journal/")
    try:
        lines = read_text(p).split("\n")
    except UnicodeDecodeError:
        r.error("log.md", "not UTF-8")
        return
    month = today.strftime("%Y-%m")
    out_of_month, previous = 0, None
    for i, line in enumerate(lines):
        if not line.startswith("## "):  # the log only holds entries
            continue
        where = f"log.md:{i + 1}"
        m = LOG_ENTRY_RE.match(line)
        if not m:
            r.warn(where, "malformed entry (expected: ## [YYYY-MM-DD] type | message)")
            continue
        day, type_ = m.groups()
        try:
            when = date.fromisoformat(day)
        except ValueError:
            r.warn(where, f"invalid date {day}")
            continue
        if type_ not in types:
            r.warn(where, f'non-standard type "{type_}" - declare it in §7, then --type {type_}')
        length = len(line)
        for following in lines[i + 1 :]:
            if following.startswith("#"):
                break
            length += len(following.strip())
        if length > ENTRY_BUDGET:
            r.warn(where, f"{length}-character entry (budget ~{ENTRY_BUDGET}, details go in the commit)")
        if previous is not None and when < previous:
            r.warn(where, f"date earlier than the previous entry ({previous}) - append-only log")
        previous = when
        if day[:7] != month:
            out_of_month += 1
    if out_of_month:
        r.warn("log.md", f"{out_of_month} entry(ies) outside the current month ({month}):"
                         " rotate to docs/journal/log_YYYY-MM.md")


def check_contract(base: Path, r: Report) -> None:
    try:
        n = len(CRITERION_RE.findall(read_text(base / "contract.md")))
    except UnicodeDecodeError:
        r.error("contract.md", "not UTF-8")
        return
    if not MIN_CRITERIA <= n <= MAX_CRITERIA:
        r.warn("contract.md", f'{n} "- [ ]" criterion(s) (expected {MIN_CRITERIA}-{MAX_CRITERIA})')


def count_active_features(base: Path) -> int | None:
    """Number of active features, None if feature_list.json is missing or unreadable."""
    try:
        data = json.loads(read_text(base / "feature_list.json"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    features = data.get("features") if isinstance(data, dict) else None
    return len(features) if isinstance(features, list) else None


def cmd_ledger(
    repo: Path,
    folder: str | None,
    extra_statuses: list[str],
    extra_types: list[str],
    variant_b: bool,
    strict: bool,
    today: date | None = None,
) -> int:
    if not repo.is_dir():
        print(f"FOLDER NOT FOUND: {repo}")
        return 2
    candidates = [repo / folder] if folder else [repo / loc for loc in LEDGER_LOCATIONS]
    base = next((c for c in candidates if any((c / f).is_file() for f in LEDGER_FILES)), None)
    if base is None:
        print(f"NO LEDGER: {repo} (root, .agents/, memory-bank/) - 'init {repo} --ledger' creates one.")
        return 2
    r = Report()
    # Between sprints (no active feature), contract and progress are archived (§3 Closure).
    between_sprints = count_active_features(base) == 0
    expected = [
        f for f in LEDGER_FILES
        if not (variant_b and f == "log.md")
        and not (between_sprints and f in ("contract.md", "progress.md"))
    ]
    for f in expected:
        if not (base / f).is_file():
            r.error(f, "missing (§3 Bootstrap: create it; 'init --ledger' for a ledger at the root)")
    if (base / "feature_list.json").is_file():
        check_features(base, set(STATUSES) | set(extra_statuses), r)
    if "log.md" in expected and (base / "log.md").is_file():
        check_log(base, set(LOG_TYPES) | set(extra_types), today or local_today(), r)
    if (base / "contract.md").is_file():
        check_contract(base, r)
    print(f"Ledger: {base.resolve()}")
    if between_sprints:
        print("  (no active feature: between sprints, contract and progress archived)")
    for level, where, message in r.lines:
        print(f"  {level} {where} - {message}")
    errors, warnings = r.count("ERROR"), r.count("WARN")
    print(f"\nSummary: {errors} error(s), {warnings} warning(s)")
    return 1 if errors or (strict and warnings) else 0


# --------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="agents-kit - common AGENTS.md block")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="state of every AGENTS.md under <root>")
    a.add_argument("root", nargs="?", type=Path, default=KIT.parent)
    a.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                   help=f"folder to skip (glob pattern, repeatable; see also <root>/{EXCLUDE_FILE})")
    a.add_argument("--strict", action="store_true", help="exit 1 if a file is neither up to date, generated nor excluded")

    c = sub.add_parser("check", help="is the common block up to date?")
    s = sub.add_parser("sync", help="resync the common block")
    ad = sub.add_parser("adopt", help="integrate the common block into an existing unmanaged AGENTS.md")
    for p in (c, s, ad):
        p.add_argument("repo", type=Path)
        p.add_argument("--file", default="AGENTS.md", help="alternative target (default: AGENTS.md)")
    c.add_argument("--diff", action="store_true", help="show the gap between the installed block and the canon")
    for p in (s, ad):
        p.add_argument("--dry-run", action="store_true", help="show the diff without writing anything")
    s.add_argument("--force", action="store_true", help="overwrite a hand-edited or newer block")
    ad.add_argument("--force", action="store_true", help="adopt even a corrupted or generated file")

    i = sub.add_parser("init", help="create AGENTS.md from the template")
    i.add_argument("repo", type=Path)
    i.add_argument("--name", help="displayed repository name (default: folder name)")
    i.add_argument("--force", action="store_true", help="overwrite an existing AGENTS.md")
    i.add_argument("--ledger", action="store_true", help="also create the missing state files")

    lg = sub.add_parser("ledger", help="check the 4 state files (read-only)")
    lg.add_argument("repo", type=Path)
    lg.add_argument("--dir", help="ledger location (default: root, .agents/ or memory-bank/)")
    lg.add_argument("--status", action="append", default=[], help="extended status declared in §7 (repeatable)")
    lg.add_argument("--type", action="append", default=[], help="extended log type declared in §7 (repeatable)")
    lg.add_argument("--variant-b", action="store_true", help="log kept in a database (DuckDB/SQLite): no log.md")
    lg.add_argument("--strict", action="store_true", help="exit 1 on warnings too")

    v = sub.add_parser("version", help="canon version and fingerprint")
    v.add_argument("--register", action="store_true", help="publish the canon version in the registry")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "audit":
            if not args.root.is_dir():
                print(f"Root not found: {args.root}")
                return 2
            return cmd_audit(args.root, args.exclude, args.strict)
        if args.cmd == "check":
            return cmd_check(args.repo.resolve(), args.file, args.diff)
        if args.cmd == "sync":
            return cmd_sync(args.repo.resolve(), args.file, args.force, args.dry_run)
        if args.cmd == "adopt":
            return cmd_adopt(args.repo.resolve(), args.file, args.force, args.dry_run)
        if args.cmd == "ledger":
            return cmd_ledger(args.repo.resolve(), args.dir, args.status, args.type, args.variant_b, args.strict)
        if args.cmd == "version":
            return cmd_version(args.register)
        return cmd_init(args.repo.resolve(), args.name, args.force, args.ledger)
    except InputError as e:
        print(e)
        return 2


if __name__ == "__main__":
    # Windows console / Git Bash pipe: an unrepresentable character must never crash the script.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    sys.exit(main())
