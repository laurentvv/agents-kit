#!/usr/bin/env python3
"""agents-kit - keep the machine's MCP servers observable and lifecycled.

Fourth managed concern of the kit, next to the canon (sync_agents.py), the
skills (skills_agents.py) and the state (state_agents.py): the MCP servers.

Machine specifics live in a LOCAL, git-ignored descriptor (mcp-fleet.local.yml
next to .agent/, template: template/mcp-fleet.template.yml) - the kit itself
holds no machine path and no repository name.

  mcp_agents.py <command> [--repo PATH] [--config PATH] [--json]

  inventory [--fleet ROOT]   Parse MCP declarations: user-level config files
                             (mcpServers or mcp.servers key) and repo-level
                             .mcp.json files under the fleet roots. Token-like
                             values (token/key/secret/password) are masked.
  audit                      Declared vs running: run each fleet entry probe
                             (localhost HTTP, process or command) and report
                             up / down / unknown.
  probe <name>               Deep check of one entry: reachability probe,
                             freshness globs (e.g. **/BUILT_AT.txt) and every
                             path referenced by its declared config file.
  doctor                     audit + freshness + referenced paths for every
                             entry; non-zero exit on any down/stale/missing
                             (CI-usable).
  start|stop|restart <name>  Run the lifecycle command declared in the fleet
                             descriptor (e.g. a start-*.cmd). Process-level
                             only; these are the only effectful commands -
                             everything else is strictly read-only.

Read-only by default; no network beyond the explicitly declared probes
(localhost daemons); standard library only, Python 3.11+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DESCRIPTOR_NAME = "mcp-fleet.local.yml"
ENV_CONFIG = "MCP_FLEET_CONFIG"
SECRET_KEY_HINTS = ("token", "key", "secret", "password")
SECRET_VALUE_RE = re.compile(r"(?i)\b(token|api[_-]?key|secret|password)\b\s*[:=]\s*\S+")
DEFAULT_TIMEOUT = 3.0
DEFAULT_MAX_AGE_HOURS = 336.0

# User-level config candidates probed by `inventory` (existing files only;
# the descriptor may declare more under inventory.user_configs).
USER_CONFIG_CANDIDATES = (
    Path.home() / ".zcode" / "cli" / "config.json",
    Path.home() / ".zcode" / "settings.json",
    Path.home() / ".claude.json",
)


class InputError(Exception):
    """A clean, user-facing error: printed without a traceback."""


# ---------------------------------------------------------------------------
# Minimal YAML subset parser (the fleet descriptor; documented in the template)
# ---------------------------------------------------------------------------

class YamlError(InputError):
    """The descriptor uses something outside the supported YAML subset."""


def _strip_comment(line: str) -> str:
    """Drop a trailing comment; '#' inside quotes or glued to text survives."""
    out: list[str] = []
    quote: str | None = None
    for ch in line:
        if quote is not None:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            out.append(ch)
        elif ch == "#" and (not out or out[-1] in " \t"):
            return "".join(out).rstrip()
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _split_flow(text: str) -> list[str]:
    """Split a flow body on commas that sit outside quotes and brackets."""
    parts: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    depth = 0
    for ch in text:
        if quote is not None:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [part.strip() for part in parts if part.strip()]


def _flow(value: str) -> Any:
    """Parse a flow scalar: 'x', "x", [a, 'b'], {}, [] or a plain scalar.

    Quoted strings are taken literally (no escape processing): use single
    quotes around Windows paths so backslashes stay backslashes.
    """
    value = value.strip()
    if not value:
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [] if not inner else [_flow(part) for part in _split_flow(inner)]
    if value.startswith("{") and value.endswith("}"):
        inner = value[1:-1].strip()
        if not inner:
            return {}
        result: dict[str, Any] = {}
        for part in _split_flow(inner):
            if ":" not in part:
                raise YamlError(f"unsupported flow mapping entry: {part!r}")
            key, _, val = part.partition(":")
            key_value = _flow(key.strip())
            if not isinstance(key_value, str):
                raise YamlError(f"unsupported flow key: {part!r}")
            result[key_value] = _flow(val)
        return result
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~"):
        return None
    for caster in (int, float):
        try:
            return caster(value)  # type: ignore[call-arg]
        except ValueError:
            continue
    return value


def _parse_map(lines: list[tuple[int, str]], start: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    i = start
    while i < len(lines):
        line_indent, content = lines[i]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise YamlError(f"unexpected indent: {content!r}")
        if content.startswith("- "):
            # A list placed at the same indent as its key (common YAML idiom).
            if not result:
                raise YamlError(f"list before any key: {content!r}")
            last_key = next(reversed(result))
            result[last_key], i = _parse_list(lines, i, line_indent)
            continue
        key, sep, inline = content.partition(":")
        if not sep:
            raise YamlError(f"expected 'key: value', got: {content!r}")
        key_value = _flow(key.strip())
        if not isinstance(key_value, str) or not key_value:
            raise YamlError(f"unsupported key: {content!r}")
        inline = inline.strip()
        if inline:
            result[key_value] = _flow(inline)
            i += 1
        elif i + 1 < len(lines) and lines[i + 1][0] > indent:
            result[key_value], i = _parse_block(lines, i + 1, lines[i + 1][0])
        else:
            result[key_value] = {}
            i += 1
    return result, i


def _parse_list(lines: list[tuple[int, str]], start: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    i = start
    while i < len(lines):
        line_indent, content = lines[i]
        if line_indent != indent:
            break
        stripped = content.lstrip()
        if not stripped.startswith("- "):
            break
        body = stripped[2:].strip()
        if not body:
            raise YamlError("empty list items are not supported")
        if re.match(r"^[^\s/'\"\\]+:(\s|$)", body) and not body.startswith("["):
            # "- key: value" opens a mapping whose block continues at the
            # column right after "- " (list-of-mappings idiom).
            virtual = [(indent + 2, body)]
            j = i + 1
            while j < len(lines) and lines[j][0] >= indent + 2:
                virtual.append(lines[j])
                j += 1
            item, _ = _parse_map(virtual, 0, indent + 2)
            items.append(item)
            i = j
        else:
            items.append(_flow(body))
            i += 1
    return items, i


def _parse_block(lines: list[tuple[int, str]], start: int, indent: int) -> tuple[Any, int]:
    first = lines[start][1].lstrip()
    if first.startswith("- ") or first == "-":
        return _parse_list(lines, start, indent)
    return _parse_map(lines, start, indent)


def parse_yaml_subset(text: str) -> dict[str, Any]:
    """Parse the descriptor's YAML subset into a dict (see the template).

    Supported: nested mappings (spaces only), block lists of scalars or of
    mappings, inline flow lists/dicts, quoted strings, comments, blank lines.
    """
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        indent_part = raw[: len(raw) - len(raw.lstrip())]
        if "\t" in indent_part:
            raise YamlError("tab indentation is not supported (spaces only)")
        stripped = _strip_comment(raw)
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        lines.append((indent, stripped.strip()))
    if not lines:
        return {}
    value, _ = _parse_block(lines, 0, lines[0][0])
    if not isinstance(value, dict):
        raise YamlError("the descriptor root must be a mapping")
    return value


# ---------------------------------------------------------------------------
# Secret masking (kit rule: no secret value on screen or in logs)
# ---------------------------------------------------------------------------

def mask_secrets(obj: Any) -> Any:
    """Recursively mask values under token-like keys and secret-looking strings."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            if any(hint in str(key).lower() for hint in SECRET_KEY_HINTS):
                out[str(key)] = "***"
            else:
                out[str(key)] = mask_secrets(value)
        return out
    if isinstance(obj, list):
        return [mask_secrets(item) for item in obj]
    if isinstance(obj, str):
        return SECRET_VALUE_RE.sub("***", obj)
    return obj


# ---------------------------------------------------------------------------
# Descriptor: discovery, loading, accessors
# ---------------------------------------------------------------------------

def find_descriptor(repo: Path, explicit: str | None) -> Path:
    """--config > MCP_FLEET_CONFIG > <repo>/mcp-fleet.local.yml > upward walk."""
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise InputError(f"DESCRIPTOR NOT FOUND: {path}")
        return path
    env = os.environ.get(ENV_CONFIG)
    if env:
        path = Path(env)
        if not path.is_file():
            raise InputError(f"{ENV_CONFIG} points to a missing file: {path}")
        return path
    current = repo.resolve()
    while True:
        candidate = current / DESCRIPTOR_NAME
        if candidate.is_file():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    raise InputError(
        f"NO DESCRIPTOR: no {DESCRIPTOR_NAME} found from {repo} upward "
        f"(copy template/mcp-fleet.template.yml next to .agent/ and fill in "
        f"the machine paths)"
    )


def load_descriptor(repo: Path, explicit: str | None) -> tuple[Path, dict[str, Any]]:
    path = find_descriptor(repo, explicit)
    try:
        data = parse_yaml_subset(path.read_text(encoding="utf-8-sig"))
    except YamlError as exc:
        raise InputError(f"BAD DESCRIPTOR {path}: {exc}") from exc
    if not isinstance(data.get("servers"), dict) or not data.get("servers"):
        raise InputError(f"BAD DESCRIPTOR {path}: the 'servers' mapping is empty or missing")
    return path, data


def server_names(descriptor: dict[str, Any]) -> list[str]:
    return sorted(descriptor.get("servers", {}))


def get_server(descriptor: dict[str, Any], name: str) -> dict[str, Any]:
    try:
        entry = descriptor["servers"][name]
    except KeyError:
        declared = ", ".join(server_names(descriptor))
        raise InputError(f"UNKNOWN SERVER: {name} (declared: {declared})") from None
    if not isinstance(entry, dict):
        raise InputError(f"BAD DESCRIPTOR: server {name} must be a mapping")
    return entry


def default_of(descriptor: dict[str, Any], key: str, fallback: float) -> float:
    try:
        return float(descriptor.get("defaults", {}).get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


# ---------------------------------------------------------------------------
# Probes: URL (localhost HTTP), command, process
# ---------------------------------------------------------------------------

def _short_reason(exc: BaseException) -> str:
    text = str(exc).strip().splitlines()
    return (text[0] if text else exc.__class__.__name__)[:70]


def probe_url(url: str, timeout: float) -> tuple[str, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return "up", f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        return "up", f"HTTP {exc.code}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return "down", _short_reason(exc)


def probe_command(argv: str | list[str], timeout: float) -> tuple[str, str]:
    try:
        completed = subprocess.run(
            argv,
            shell=isinstance(argv, str),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "down", _short_reason(exc)
    if completed.returncode == 0:
        first_line = (completed.stdout or completed.stderr or "").strip().splitlines()
        return "up", first_line[0][:60] if first_line else "exit 0"
    return "down", f"exit {completed.returncode}"


def probe_process(name: str) -> tuple[str, str]:
    if os.name == "nt":
        argv = ["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"]
    else:
        argv = ["pgrep", "-f", name]
    try:
        completed = subprocess.run(
            argv, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "unknown", _short_reason(exc)
    out = completed.stdout
    if "INFO:" in out:  # tasklist found nothing
        return "down", "process not found"
    return ("up", "process running") if out.strip() else ("down", "process not found")


def run_probe(probe: dict[str, Any], timeout: float) -> tuple[str, str, str]:
    """Return (verdict, kind, detail) for a declared probe mapping."""
    if not isinstance(probe, dict) or not probe:
        return "unknown", "none", "no probe declared"
    if "url" in probe:
        verdict, detail = probe_url(str(probe["url"]), timeout)
        return verdict, "url", detail
    if "command" in probe:
        verdict, detail = probe_command(probe["command"], timeout)
        return verdict, "command", detail
    if "process" in probe:
        verdict, detail = probe_process(str(probe["process"]))
        return verdict, "process", detail
    return "unknown", "none", "probe mapping has no url/command/process key"


# ---------------------------------------------------------------------------
# Freshness and referenced paths
# ---------------------------------------------------------------------------

def check_freshness(entry: dict[str, Any], now: float) -> tuple[str, list[str]]:
    """Verdict fresh|stale|missing|none plus human lines for the freshness block."""
    block = entry.get("freshness")
    if not block:
        return "none", []
    roots = [Path(r) for r in _as_list(block.get("roots"))]
    globs = _as_list(block.get("globs"))
    if not roots or not globs:
        return "missing", ["freshness: roots and globs must both be declared"]
    try:
        max_age = float(block.get("max_age_hours", DEFAULT_MAX_AGE_HOURS))
    except (TypeError, ValueError):
        return "missing", ["freshness: max_age_hours must be a number"]
    lines: list[str] = []
    newest: float | None = None
    unmatched: list[str] = []
    for root in roots:
        if not root.is_dir():
            unmatched.append(str(root))
            continue
        for pattern in globs:
            matches = [p for p in root.glob(pattern) if p.is_file()]
            if not matches:
                unmatched.append(f"{root}/{pattern}")
                continue
            candidate = max(p.stat().st_mtime for p in matches)
            newest = candidate if newest is None else max(newest, candidate)
    if newest is None:
        return "missing", [f"freshness: no match for {path}" for path in unmatched]
    age_hours = (now - newest) / 3600.0
    verdict = "fresh" if age_hours <= max_age else "stale"
    lines.append(
        f"freshness: {verdict} (newest marker {age_hours:.1f} h old, budget {max_age:.0f} h)"
    )
    lines.extend(f"freshness: no match for {path}" for path in unmatched)
    return verdict, lines


WIN_PATH_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]:[\\/][^\s\"'|<>]*)")
POSIX_QUOTED_RE = re.compile(r"r?[\"'](/[^\"']*)[\"']")
PATH_KEY_RE = re.compile(
    r"^\s*-?\s*(path|directory|dir|root|folder|config_file|home|bin|binary|corpus)"
    r"\w*\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)


def extract_referenced_paths(text: str) -> list[str]:
    """Absolute paths referenced by a config file (format-agnostic scan)."""
    found: list[str] = []

    def add(candidate: str) -> None:
        candidate = candidate.strip().strip("'\"").rstrip(".,;:)")
        if len(candidate) < 2 or "://" in candidate or "{" in candidate or "*" in candidate:
            return
        if candidate not in found:
            found.append(candidate)

    for match in WIN_PATH_RE.finditer(text):
        add(match.group(1))
    for match in POSIX_QUOTED_RE.finditer(text):
        add(match.group(1))
    for line in text.splitlines():
        key_match = PATH_KEY_RE.match(line)
        if key_match:
            add(key_match.group(2))
    return found


def check_referenced_paths(entry: dict[str, Any]) -> tuple[str, list[str]]:
    """Verdict ok|missing|none plus lines for the referenced_paths block."""
    block = entry.get("referenced_paths")
    if not block:
        return "none", []
    config_file = Path(str(block.get("config_file", "")))
    if not config_file.is_file():
        return "missing", [f"referenced: config file not found: {config_file}"]
    try:
        text = config_file.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        return "missing", [f"referenced: cannot read {config_file.name}: {_short_reason(exc)}"]
    paths = extract_referenced_paths(text)
    if not paths:
        return "none", [f"referenced: no absolute path found in {config_file.name}"]
    lines = []
    missing = 0
    for path in paths:
        if Path(path).exists():
            lines.append(f"referenced: ok   {path}")
        else:
            missing += 1
            lines.append(f"referenced: MISSING {path}")
    return ("missing" if missing else "ok"), lines


# ---------------------------------------------------------------------------
# Inventory: user-level and repo-level MCP declarations
# ---------------------------------------------------------------------------

def read_mcp_entries(config_path: Path) -> list[dict[str, Any]]:
    """Normalize every mcpServers / mcp.servers entry of one JSON config."""
    try:
        data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    servers: Any = None
    if isinstance(data.get("mcpServers"), dict):
        servers = data["mcpServers"]
    elif isinstance(data.get("mcp"), dict) and isinstance(data["mcp"].get("servers"), dict):
        servers = data["mcp"]["servers"]
    if not isinstance(servers, dict):
        return []
    entries = []
    for name, spec in servers.items():
        spec = spec if isinstance(spec, dict) else {}
        command = str(spec.get("command", "") or "")
        args = _as_list(spec.get("args"))
        argv = " ".join([command] + args) if command else ""
        entries.append(
            {
                "name": str(name),
                "enabled": bool(spec.get("enabled", True)),
                "command": argv,
                "source": str(config_path),
            }
        )
    return entries


def collect_inventory(
    extra_user: list[Path], fleet_roots: list[Path]
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(entry: dict[str, Any], origin: str) -> None:
        key = entry["name"] + entry["source"]
        if key not in seen:
            seen.add(key)
            entry["origin"] = origin
            entries.append(entry)

    user_files = [p for p in USER_CONFIG_CANDIDATES if p.is_file()]
    user_files.extend(p for p in extra_user if p.is_file() and p not in user_files)
    for config_path in user_files:
        for entry in read_mcp_entries(config_path):
            add(entry, "user")
    for root in fleet_roots:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            config_path = child / ".mcp.json"
            if config_path.is_file():
                for entry in read_mcp_entries(config_path):
                    add(entry, "repo")
    return entries


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_inventory(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    extra_user: list[Path] = []
    fleet_roots: list[Path] = []
    if args.config or os.environ.get(ENV_CONFIG) or (repo / DESCRIPTOR_NAME).is_file():
        try:
            _, descriptor = load_descriptor(repo, args.config)
        except InputError as exc:
            print(f"ERROR: {exc}")
            return 1
        inventory_block = descriptor.get("inventory", {})
        extra_user = [Path(p) for p in _as_list(inventory_block.get("user_configs"))]
        fleet_roots.extend(Path(p) for p in _as_list(inventory_block.get("fleet_roots")))
    if args.fleet:
        fleet_roots.append(Path(args.fleet))
    if not fleet_roots:
        fleet_roots = [repo.parent]
    entries = mask_secrets(collect_inventory(extra_user, fleet_roots))
    if args.json:
        print(json.dumps(entries, indent=2))
        return 0
    if not entries:
        print("inventory: no MCP declaration found")
        return 0
    width = max(len(entry["name"]) for entry in entries)
    for entry in entries:
        state = "enabled " if entry["enabled"] else "disabled"
        print(f"  {entry['name']:<{width}}  {state}  {entry['origin']:<5}  {entry['command']}")
        print(f"  {'':<{width}}  source: {entry['source']}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    try:
        path, descriptor = load_descriptor(Path(args.repo), args.config)
    except InputError as exc:
        print(f"ERROR: {exc}")
        return 1
    timeout = default_of(descriptor, "timeout_seconds", DEFAULT_TIMEOUT)
    results = []
    for name in server_names(descriptor):
        verdict, kind, detail = run_probe(get_server(descriptor, name).get("probe", {}), timeout)
        results.append({"name": name, "verdict": verdict, "probe": kind, "detail": detail})
    if args.json:
        print(json.dumps(mask_secrets(results), indent=2))
    else:
        print(f"audit: {len(results)} declared server(s) in {path.name}")
        for row in results:
            print(f"  {row['verdict']:<8} {row['name']:<20} [{row['probe']}] {row['detail']}")
    return 0 if all(row["verdict"] != "down" for row in results) else 1


def deep_checks(entry: dict[str, Any], timeout: float, now: float) -> tuple[list[str], bool]:
    """All read-only checks of one entry: report lines + overall healthy flag."""
    lines: list[str] = []
    healthy = True
    verdict, kind, detail = run_probe(entry.get("probe", {}), timeout)
    lines.append(f"probe:    {verdict:<8} [{kind}] {detail}")
    healthy = healthy and verdict == "up"
    fresh_verdict, fresh_lines = check_freshness(entry, now)
    lines.extend(fresh_lines)
    healthy = healthy and fresh_verdict in ("fresh", "none")
    ref_verdict, ref_lines = check_referenced_paths(entry)
    lines.extend(ref_lines)
    healthy = healthy and ref_verdict in ("ok", "none")
    for source in _as_list(entry.get("config_sources")):
        ok = Path(source).is_file()
        lines.append(f"config:   {'ok   ' if ok else 'MISSING'} {source}")
        healthy = healthy and ok
    return lines, healthy


def cmd_probe(args: argparse.Namespace) -> int:
    try:
        _, descriptor = load_descriptor(Path(args.repo), args.config)
        entry = get_server(descriptor, args.name)
    except InputError as exc:
        print(f"ERROR: {exc}")
        return 1
    timeout = default_of(descriptor, "timeout_seconds", DEFAULT_TIMEOUT)
    lines, healthy = deep_checks(entry, timeout, time.time())
    print(f"probe {args.name}:")
    for line in lines:
        print(f"  {line}")
    print(f"  verdict: {'HEALTHY' if healthy else 'UNHEALTHY'}")
    return 0 if healthy else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    try:
        path, descriptor = load_descriptor(Path(args.repo), args.config)
    except InputError as exc:
        print(f"ERROR: {exc}")
        return 1
    timeout = default_of(descriptor, "timeout_seconds", DEFAULT_TIMEOUT)
    now = time.time()
    report: list[dict[str, Any]] = []
    unhealthy = 0
    for name in server_names(descriptor):
        lines, healthy = deep_checks(get_server(descriptor, name), timeout, now)
        unhealthy += 0 if healthy else 1
        report.append({"name": name, "healthy": healthy, "checks": lines})
        print(f"{name}: {'HEALTHY' if healthy else 'UNHEALTHY'}")
        for line in lines:
            print(f"  {line}")
    print(f"doctor: {len(report) - unhealthy}/{len(report)} healthy ({path.name})")
    if args.json:
        print(json.dumps(mask_secrets(report), indent=2))
    return 1 if unhealthy else 0


def cmd_lifecycle(args: argparse.Namespace) -> int:
    try:
        _, descriptor = load_descriptor(Path(args.repo), args.config)
        entry = get_server(descriptor, args.name)
    except InputError as exc:
        print(f"ERROR: {exc}")
        return 1
    lifecycle = entry.get("lifecycle", {})
    action = args.action
    if action == "restart" and "restart" not in lifecycle:
        steps = [s for s in (lifecycle.get("stop"), lifecycle.get("start")) if s]
        if not steps:
            print(f"ERROR: no stop/start commands declared for {args.name}")
            return 1
    else:
        command = lifecycle.get(action)
        if not command:
            print(f"ERROR: no {action} command declared for {args.name}")
            return 1
        steps = [command]
    failed = 0
    for step in steps:
        print(f"  $ {step}")
        try:
            completed = subprocess.run(step, shell=isinstance(step, str), check=False)
        except OSError as exc:
            print(f"ERROR: {_short_reason(exc)}")
            failed += 1
            continue
        if completed.returncode != 0:
            print(f"ERROR: exit {completed.returncode}")
            failed += 1
    state = "done" if not failed else f"{failed} step(s) failed"
    print(f"{action} {args.name}: {state}")
    return 1 if failed else 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

COMMON = argparse.ArgumentParser(add_help=False)
COMMON.add_argument("--repo", default=".", help="repository root (default: current folder)")
COMMON.add_argument("--config", default=None, help="explicit fleet descriptor path")
COMMON.add_argument("--json", action="store_true", help="machine-readable output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp_agents.py",
        description="MCP fleet management for agents-kit (read-only by default).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    inventory = sub.add_parser(
        "inventory", parents=[COMMON], help="parse MCP declarations (user + fleet configs)"
    )
    inventory.add_argument("--fleet", default=None, help="extra root walked for .mcp.json files")
    inventory.set_defaults(func=cmd_inventory)

    audit = sub.add_parser(
        "audit", parents=[COMMON], help="declared vs running: probe every fleet entry"
    )
    audit.set_defaults(func=cmd_audit)

    probe = sub.add_parser("probe", parents=[COMMON], help="deep check of one entry")
    probe.add_argument("name", help="server name in the descriptor")
    probe.set_defaults(func=cmd_probe)

    doctor = sub.add_parser(
        "doctor", parents=[COMMON], help="audit + freshness + referenced paths (CI gate)"
    )
    doctor.set_defaults(func=cmd_doctor)

    for action in ("start", "stop", "restart"):
        lifecycle = sub.add_parser(
            action, parents=[COMMON], help=f"run the declared {action} command"
        )
        lifecycle.add_argument("name", help="server name in the descriptor")
        lifecycle.set_defaults(func=cmd_lifecycle, action=action)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except InputError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
