#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
"""Prerequisite gate for the kit's video/animation skills (kinetic-reel,
painted-animation, the lemo-opuscar pointer): probe the local toolchain and
fail with one clear remediation line per missing tool.

Required: node, ffmpeg, python with numpy + Pillow, headless Chrome.
Optional: ruby (motion-graphics-music-video only, never fails the run).
Read-only: only subprocess probes of tools already on this machine, no project
file touched (the uv candidate may provision its package cache on first use).

Exit codes: 0 all required tools present, 1 at least one required tool
missing (2 = usage error, argparse).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

PROBE_TIMEOUT = 15.0
UV_ENV_TIMEOUT = 300.0  # first `uv run --with` provisions a cached env


def env_get(env: dict[str, str], name: str) -> str | None:
    """Env lookup that tolerates case drift (a Git Bash child inherits
    PROGRAMFILES uppercase; Windows lookups are case-insensitive, POSIX ones
    are not - exact key first, case-insensitive scan second)."""
    if name in env:
        return env[name]
    folded = name.casefold()
    for key, value in env.items():
        if key.casefold() == folded:
            return value
    return None

HINT_NODE = "install Node.js LTS (https://nodejs.org)"
HINT_FFMPEG = "install ffmpeg (winget install Gyan.FFmpeg / brew install ffmpeg / apt install ffmpeg)"
HINT_PYLIBS = (
    "add numpy and Pillow to the interpreter that runs the render helpers: "
    "uv add numpy pillow (kit rule: uv only)"
)
HINT_CHROME = (
    "install Google Chrome, or set CHROME_PATH / PLAYWRIGHT_CHROME to the "
    "executable, or pass --chrome <path>"
)
HINT_RUBY = "optional - only needed by motion-graphics-music-video (Ruby 3.2+)"

CHROME_ENV_VARS = ("CHROME_PATH", "PLAYWRIGHT_CHROME")
CHROME_WHICH_NAMES = ("chrome", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser")


def probe_command(cmd: list[str], runner=subprocess.run, timeout: float = PROBE_TIMEOUT) -> str | None:
    """First non-empty stdout line of a successful command, else None."""
    try:
        done = runner(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    for line in (done.stdout or "").splitlines():
        if line.strip():
            return line.strip()
    return None


def python_candidates(explicit: str | None, which=shutil.which) -> list[tuple[list[str], float]]:
    """Interpreters to try for numpy + Pillow, cheapest canonical first:
    --python, the kit-idiomatic uv env (may provision its cache once), python, python3."""
    candidates: list[tuple[list[str], float]] = []
    if explicit:
        candidates.append(([explicit], PROBE_TIMEOUT))
    if which("uv"):
        candidates.append((["uv", "run", "--no-project", "--with", "numpy", "--with", "pillow",
                            "python"], UV_ENV_TIMEOUT))
    for name in ("python", "python3"):
        binary = which(name)
        if binary:
            candidates.append(([binary], PROBE_TIMEOUT))
    return candidates


def standard_chrome_paths(platform: str, env: dict[str, str]) -> list[str]:
    """Standard Chrome install locations per platform (no machine specifics)."""
    if platform.startswith("win"):
        candidates = []
        for var in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
            root = env_get(env, var)
            if root:
                candidates.append(f"{root}\\Google\\Chrome\\Application\\chrome.exe")
        return candidates
    if platform == "darwin":
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
        ]
    return [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ]


def find_chrome(
    override: str | None,
    env: dict[str, str],
    platform: str,
    extra_paths: list[str] | None = None,
    which=shutil.which,
    isfile=os.path.isfile,
) -> str | None:
    """Chrome resolution order: --chrome, CHROME_PATH, PLAYWRIGHT_CHROME,
    standard install paths, PATH lookup."""
    candidates: list[str] = [override] if override else []
    candidates += [env_get(env, var) for var in CHROME_ENV_VARS]
    candidates += standard_chrome_paths(platform, env)
    candidates += extra_paths or []
    for path in candidates:
        if path and isfile(path):
            return path
    for name in CHROME_WHICH_NAMES:
        found = which(name)
        if found:
            return found
    return None


def probe_python_modules(
    candidates: list[tuple[list[str], float]], runner=subprocess.run
) -> str | None:
    """Detail line of the first candidate that imports numpy and PIL, else None."""
    code = "import numpy, PIL; print(numpy.__version__ + ' numpy / Pillow ' + PIL.__version__)"
    for argv, timeout in candidates:
        detail = probe_command(argv + ["-c", code], runner=runner, timeout=timeout)
        if detail:
            return f"{detail} (via {argv[0]})"
    return None


def check_everything(
    explicit_python: str | None = None,
    chrome_override: str | None = None,
    env: dict[str, str] | None = None,
    platform: str = sys.platform,
    runner=subprocess.run,
    which=shutil.which,
    chrome_paths: list[str] | None = None,
    isfile=os.path.isfile,
) -> tuple[bool, dict[str, dict[str, str]]]:
    """Probe every tool. Returns (all_required_ok, {tool: status/detail/hint})."""
    env = dict(env if env is not None else os.environ)
    tools: dict[str, dict[str, str]] = {}

    detail = probe_command(["node", "--version"], runner=runner)
    tools["node"] = {"status": "ok" if detail else "missing",
                     "detail": detail or "node not found on PATH", "hint": HINT_NODE}

    detail = probe_command(["ffmpeg", "-version"], runner=runner)
    tools["ffmpeg"] = {"status": "ok" if detail else "missing",
                       "detail": detail or "ffmpeg not found on PATH", "hint": HINT_FFMPEG}

    py_candidates = python_candidates(explicit_python, which=which)
    detail = probe_python_modules(py_candidates, runner=runner)
    tools["python-numpy-pil"] = {
        "status": "ok" if detail else "missing",
        "detail": detail or "no interpreter with numpy + Pillow (uv env, python, python3)",
        "hint": HINT_PYLIBS,
    }

    chrome = find_chrome(chrome_override, env, platform, chrome_paths, which, isfile)
    tools["chrome"] = {"status": "ok" if chrome else "missing",
                       "detail": chrome or "no Chrome executable found", "hint": HINT_CHROME}

    detail = probe_command(["ruby", "--version"], runner=runner)
    tools["ruby (optional)"] = {"status": "ok" if detail else "optional",
                                "detail": detail or "ruby not found (fine unless motion-graphics is used)",
                                "hint": HINT_RUBY}

    ok = all(t["status"] == "ok" for name, t in tools.items() if not name.endswith("(optional)"))
    return ok, tools


def render_text(ok: bool, tools: dict[str, dict[str, str]]) -> str:
    lines = ["video toolchain: " + ("OK" if ok else "MISSING REQUIRED TOOLS")]
    for name, tool in tools.items():
        lines.append(f"  {name}: [{tool['status']}] {tool['detail']}")
        if tool["status"] == "missing":
            lines.append(f"    fix: {tool['hint']}")
    return "\n".join(lines)


def render_json(ok: bool, tools: dict[str, dict[str, str]]) -> str:
    return json.dumps({"ok": ok, "tools": tools}, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--python", help="python binary to probe (default: python, then python3)")
    parser.add_argument("--chrome", help="Chrome executable to use (overrides env and standard paths)")
    args = parser.parse_args(argv)

    encoding = getattr(sys.stdout, "encoding", None)
    if encoding and encoding.lower() != "utf-8":
        sys.stdout.reconfigure(errors="replace")  # type: ignore[union-attr]
    ok, tools = check_everything(args.python, args.chrome)
    print(render_json(ok, tools) if args.json else render_text(ok, tools))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
