"""Tests for scripts/mcp_agents.py - the MCP fleet management CLI (agent-mcp skill).

Runs against temporary repositories and throwaway localhost listeners through
the real main(); the kit invariant tests also pin the byte-identical mirror
shipped inside the skill and the committed descriptor template.
"""

import ast
import contextlib
import http.server
import importlib.util
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "mcp_agents.py"

_spec = importlib.util.spec_from_file_location("mcp_agents", SCRIPT)
ma = importlib.util.module_from_spec(_spec)
sys.modules["mcp_agents"] = ma
_spec.loader.exec_module(ma)


def run(*args: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = ma.main(list(args))
    return code, buffer.getvalue()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


class Temp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()


class Parser(Temp):
    def test_full_descriptor(self):
        data = ma.parse_yaml_subset(textwrap.dedent(
            """\
            # leading comment
            version: 1
            defaults:
                timeout_seconds: 3
            servers:
                daemon:
                    probe:
                        url: 'http://127.0.0.1:8080/'
                    freshness:
                        roots: ['C:/corpus']
                        globs: ['**/BUILT_AT.txt']
                        max_age_hours: 1080
                    items:
                        - path: 'D:/a'
                          label: 'one'
                          filetypes: ['md', 'txt']
                        - path: 'D:/b'
                          label: 'two'
                kb:
                    probe:
                        command: ['<path>/tool.exe', '--version']
            """
        ))
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["defaults"]["timeout_seconds"], 3)
        daemon = data["servers"]["daemon"]
        self.assertEqual(daemon["probe"]["url"], "http://127.0.0.1:8080/")
        self.assertEqual(daemon["freshness"]["max_age_hours"], 1080)
        self.assertEqual(daemon["items"][0]["filetypes"], ["md", "txt"])
        self.assertEqual(daemon["items"][1]["label"], "two")
        self.assertEqual(data["servers"]["kb"]["probe"]["command"], ["<path>/tool.exe", "--version"])

    def test_same_indent_list(self):
        self.assertEqual(ma.parse_yaml_subset("keys:\n- a\n- b\n"), {"keys": ["a", "b"]})

    def test_windows_path_stays_literal_in_single_quotes(self):
        data = ma.parse_yaml_subset("start: 'C:\\repo\\start-x.cmd'\nplain: C:/fwd/path\n")
        self.assertEqual(data["start"], "C:\\repo\\start-x.cmd")
        self.assertEqual(data["plain"], "C:/fwd/path")

    def test_scalars(self):
        data = ma.parse_yaml_subset("a: true\nb: false\nc: 42\nd: 3.5\ne:\nf: '~'\ng: []\nh: {}\n")
        self.assertEqual(data["a"], True)
        self.assertEqual(data["c"], 42)
        self.assertEqual(data["d"], 3.5)
        self.assertEqual(data["e"], {})
        self.assertEqual(data["f"], "~")
        self.assertEqual(data["g"], [])
        self.assertEqual(data["h"], {})

    def test_tab_rejected(self):
        with self.assertRaises(ma.YamlError):
            ma.parse_yaml_subset("a:\n\tb: 1\n")

    def test_root_must_be_mapping(self):
        with self.assertRaises(ma.YamlError):
            ma.parse_yaml_subset("- a\n- b\n")

    def test_windows_drive_scalar_item_is_not_a_mapping(self):
        data = ma.parse_yaml_subset("roots:\n    - C:\\dir\n    - 'D:/other'\n")
        self.assertEqual(data["roots"], ["C:\\dir", "D:/other"])


class Discovery(Temp):
    def descriptor(self) -> Path:
        write(
            self.repo / "mcp-fleet.local.yml",
            "servers:\n    x:\n        probe:\n            command: ['true']\n",
        )
        return self.repo / "mcp-fleet.local.yml"

    def test_repo_local_found_by_upward_walk(self):
        nested = self.repo / "deep" / "deeper"
        nested.mkdir(parents=True)
        self.descriptor()
        found = ma.find_descriptor(nested, None)
        self.assertEqual(found, self.repo / "mcp-fleet.local.yml")

    def test_explicit_config_wins(self):
        self.descriptor()
        other = self.tmp / "other.yml"
        write(other, "servers:\n    y: {}\n")
        self.assertEqual(ma.find_descriptor(self.repo, str(other)), other)

    def test_env_var(self):
        self.descriptor()
        env_file = self.tmp / "env.yml"
        write(env_file, "servers:\n    z: {}\n")
        old = os.environ.get(ma.ENV_CONFIG)
        os.environ[ma.ENV_CONFIG] = str(env_file)
        try:
            self.assertEqual(ma.find_descriptor(self.repo, None), env_file)
        finally:
            if old is None:
                del os.environ[ma.ENV_CONFIG]
            else:
                os.environ[ma.ENV_CONFIG] = old

    def test_missing_descriptor_clean_error(self):
        empty = self.tmp / "empty"
        empty.mkdir()
        code, out = run("audit", "--repo", str(empty))
        self.assertEqual(code, 1)
        self.assertIn("NO DESCRIPTOR", out)
        self.assertNotIn("Traceback", out)

    def test_missing_explicit_clean_error(self):
        code, out = run("audit", "--repo", str(self.repo), "--config", str(self.tmp / "nope.yml"))
        self.assertEqual(code, 1)
        self.assertIn("DESCRIPTOR NOT FOUND", out)


class Masking(unittest.TestCase):
    def test_token_like_keys_masked(self):
        masked = ma.mask_secrets({"access_token": "abc", "api_key": "xyz", "Password": "p", "n": 5})
        self.assertEqual(masked, {"access_token": "***", "api_key": "***", "Password": "***", "n": 5})

    def test_nested_and_list(self):
        masked = ma.mask_secrets({"a": [{"secret": "s"}], "b": {"token_id": "t"}})
        self.assertEqual(masked, {"a": [{"secret": "***"}], "b": {"token_id": "***"}})

    def test_embedded_assignment_masked(self):
        self.assertEqual(ma.mask_secrets("run --api-key=zzz up"), "run --*** up")
        self.assertEqual(ma.mask_secrets("no secrets here"), "no secrets here")


class Inventory(Temp):
    def setUp(self):
        super().setUp()
        self._saved_candidates = ma.USER_CONFIG_CANDIDATES
        ma.USER_CONFIG_CANDIDATES = ()
        self.addCleanup(setattr, ma, "USER_CONFIG_CANDIDATES", self._saved_candidates)

    def test_user_config_both_key_styles(self):
        zcode = self.tmp / "config.json"
        write(zcode, json.dumps({
            "mcp": {"servers": {
                "kb": {"command": "uv", "args": ["run", "kb"], "enabled": True},
                "off": {"command": "x", "enabled": False},
            }}
        }))
        claude = self.tmp / "claude.json"
        write(claude, json.dumps({"mcpServers": {"remote": {"command": "npx", "args": ["-y", "srv"]}}}))
        entries = ma.collect_inventory([zcode, claude], [])
        by_name = {e["name"]: e for e in entries}
        self.assertEqual(by_name["kb"]["origin"], "user")
        self.assertEqual(by_name["kb"]["command"], "uv run kb")
        self.assertFalse(by_name["off"]["enabled"])
        self.assertEqual(by_name["remote"]["command"], "npx -y srv")

    def test_repo_level_walk_and_masking(self):
        user = self.tmp / "user.json"
        write(user, json.dumps({"mcpServers": {"tok": {"command": "srv", "args": ["--token=abc123"]}}}))
        fleet = self.tmp / "fleet"
        (fleet / "repoa").mkdir(parents=True)
        write(fleet / "repoa" / ".mcp.json", json.dumps({"mcpServers": {"local": {"command": "m"}}}))
        entries = ma.collect_inventory([user], [fleet])
        by_name = {e["name"]: e for e in entries}
        self.assertEqual(by_name["local"]["origin"], "repo")
        # Masking is a CLI-layer concern: the collector returns raw values.
        self.assertEqual(by_name["tok"]["command"], "srv --token=abc123")

    def test_cli_json_masks_token_values(self):
        user = self.tmp / "user.json"
        write(user, json.dumps({
            "mcpServers": {
                "tok": {"command": "srv", "args": ["--token=abc123"], "api_key": "xyz"},
            }
        }))
        write(self.repo / "mcp-fleet.local.yml", "\n".join([
            "inventory:",
            "    user_configs:",
            f"        - '{user}'",
            "servers:",
            "    x: {}",
        ]))
        code, out = run("inventory", "--repo", str(self.repo), "--json")
        self.assertEqual(code, 0)
        self.assertIn("***", out)
        self.assertNotIn("abc123", out)
        self.assertNotIn("xyz", out)

    def test_cli_inventory_json(self):
        fleet = self.tmp / "fleet"
        (fleet / "repoa").mkdir(parents=True)
        write(fleet / "repoa" / ".mcp.json", json.dumps({"mcpServers": {"local": {"command": "m"}}}))
        code, out = run("inventory", "--repo", str(self.repo), "--fleet", str(fleet), "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual([e["name"] for e in data], ["local"])

    def test_cli_inventory_table(self):
        fleet = self.tmp / "fleet"
        (fleet / "repoa").mkdir(parents=True)
        write(fleet / "repoa" / ".mcp.json", json.dumps({"mcpServers": {"local": {"command": "m"}}}))
        code, out = run("inventory", "--repo", str(self.repo), "--fleet", str(fleet))
        self.assertEqual(code, 0)
        self.assertIn("local", out)
        self.assertIn("enabled", out)


class Listener:
    """A throwaway localhost HTTP server on an ephemeral port."""

    def __init__(self):
        self.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), http.server.BaseHTTPRequestHandler
        )
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/"

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class Probes(unittest.TestCase):
    def test_url_up(self):
        listener = Listener()
        self.addCleanup(listener.stop)
        self.assertEqual(ma.probe_url(listener.url, 2.0)[0], "up")

    def test_url_down_on_closed_port(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        verdict, _ = ma.probe_url(f"http://127.0.0.1:{port}/", 2.0)
        self.assertEqual(verdict, "down")

    def test_command_up_and_down(self):
        up = [sys.executable, "-c", "print('md-doc-search 1.0')"]
        self.assertEqual(ma.probe_command(up, 10.0), ("up", "md-doc-search 1.0"))
        down = [sys.executable, "-c", "raise SystemExit(3)"]
        self.assertEqual(ma.probe_command(down, 10.0), ("down", "exit 3"))

    def test_missing_binary_is_down(self):
        verdict, _ = ma.probe_command(["no-such-binary-xyz", "--version"], 5.0)
        self.assertEqual(verdict, "down")

    def test_run_probe_unknown(self):
        self.assertEqual(ma.run_probe({}, 1.0), ("unknown", "none", "no probe declared"))
        verdict, kind, _ = ma.run_probe({"neither": 1}, 1.0)
        self.assertEqual((verdict, kind), ("unknown", "none"))


class Freshness(Temp):
    def test_fresh_and_stale(self):
        root = self.tmp / "corpus"
        (root / "godot").mkdir(parents=True)
        marker = root / "godot" / "BUILT_AT.txt"
        write(marker, "godot")
        entry = {"freshness": {"roots": [str(root)], "globs": ["*/BUILT_AT.txt"], "max_age_hours": 24}}
        verdict, _lines = ma.check_freshness(entry, time.time())
        self.assertEqual(verdict, "fresh")
        old = time.time() - 100 * 3600
        os.utime(marker, (old, old))
        verdict, _ = ma.check_freshness(entry, time.time())
        self.assertEqual(verdict, "stale")

    def test_missing_glob(self):
        root = self.tmp / "empty-corpus"
        root.mkdir()
        entry = {"freshness": {"roots": [str(root)], "globs": ["**/BUILT_AT.txt"], "max_age_hours": 24}}
        verdict, lines = ma.check_freshness(entry, time.time())
        self.assertEqual(verdict, "missing")
        self.assertIn("no match", lines[0])

    def test_none_when_undeclared(self):
        self.assertEqual(ma.check_freshness({}, time.time()), ("none", []))


class ReferencedPaths(Temp):
    def test_yaml_style_extraction(self):
        existing_dir = self.tmp / "indexed"
        existing_dir.mkdir()
        existing_file = self.tmp / "data.db"
        existing_file.write_bytes(b"x")
        missing = self.tmp / "gone" / "renamed"
        config = self.tmp / "config.yml"
        write(config, "\n".join([
            "app:",
            f"    directory: {existing_dir}",
            "indexer:",
            "    directories:",
            f"        - path: '{existing_file}'",
            "          label: 'one'",
            f"        - path: '{missing}'",
            "          label: 'two'",
        ]))
        paths = ma.extract_referenced_paths(config.read_text(encoding="utf-8"))
        self.assertIn(str(existing_dir), paths)
        self.assertIn(str(existing_file), paths)
        self.assertIn(str(missing), paths)
        entry = {"referenced_paths": {"config_file": str(config)}}
        verdict, lines = ma.check_referenced_paths(entry)
        self.assertEqual(verdict, "missing")
        self.assertTrue(any("MISSING" in line for line in lines))

    def test_python_style_extraction(self):
        existing = self.tmp / "tool.exe"
        existing.write_bytes(b"MZ")
        config = self.tmp / "config.py"
        write(config, "\n".join([
            "from pathlib import Path",
            f'DEFAULT_BIN = Path(r"{existing}")',
            'DEFAULT_URL = "http://127.0.0.1:4433"',
        ]))
        paths = ma.extract_referenced_paths(config.read_text(encoding="utf-8"))
        self.assertEqual(paths, [str(existing)])

    def test_missing_config_file(self):
        entry = {"referenced_paths": {"config_file": str(self.tmp / "nope.yml")}}
        verdict, lines = ma.check_referenced_paths(entry)
        self.assertEqual(verdict, "missing")
        self.assertIn("config file not found", lines[0])

    def test_none_when_undeclared(self):
        self.assertEqual(ma.check_referenced_paths({}), ("none", []))


class Doctor(Temp):
    def descriptor(self, healthy: bool) -> Path:
        corpus = self.tmp / "corpus"
        corpus.mkdir(exist_ok=True)
        marker = corpus / "BUILT_AT.txt"
        write(marker, "x")
        if not healthy:
            old = time.time() - 999 * 3600
            os.utime(marker, (old, old))
        existing = self.tmp / "ref.txt"
        existing.write_bytes(b"x")
        config = self.tmp / "cfg.yml"
        write(config, f"root: {corpus}\nbin: {existing}\n")
        path = self.repo / "mcp-fleet.local.yml"
        write(path, "\n".join([
            "defaults:",
            "    timeout_seconds: 5",
            "servers:",
            "    good:",
            "        probe:",
            f"            command: ['{sys.executable}', '-c', 'pass']",
            "        freshness:",
            f"            roots: ['{corpus}']",
            "            globs: ['BUILT_AT.txt']",
            "            max_age_hours: 24",
            "        referenced_paths:",
            f"            config_file: '{config}'",
        ]))
        return path

    def test_all_healthy_exits_zero(self):
        self.descriptor(healthy=True)
        code, out = run("doctor", "--repo", str(self.repo))
        self.assertEqual(code, 0, out)
        self.assertIn("HEALTHY", out)
        self.assertIn("1/1 healthy", out)

    def test_stale_entry_exits_one(self):
        self.descriptor(healthy=False)
        code, out = run("doctor", "--repo", str(self.repo))
        self.assertEqual(code, 1, out)
        self.assertIn("UNHEALTHY", out)
        self.assertIn("stale", out)

    def test_doctor_json(self):
        self.descriptor(healthy=True)
        code, out = run("doctor", "--repo", str(self.repo), "--json")
        self.assertEqual(code, 0)
        data = json.loads(out[out.rindex("\n[") + 1:])
        self.assertEqual(data[0]["healthy"], True)


class Audit(Temp):
    def test_audit_verdicts_and_exit(self):
        listener = Listener()
        self.addCleanup(listener.stop)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            dead_port = sock.getsockname()[1]
        path = self.repo / "mcp-fleet.local.yml"
        write(path, "\n".join([
            "servers:",
            "    alive:",
            "        probe:",
            f"            url: '{listener.url}'",
            "    dead:",
            "        probe:",
            f"            url: 'http://127.0.0.1:{dead_port}/'",
            "    mystery:",
            "        description: no probe declared",
        ]))
        code, out = run("audit", "--repo", str(self.repo))
        self.assertEqual(code, 1)
        self.assertIn("up       alive", out)
        self.assertIn("down     dead", out)
        self.assertIn("unknown  mystery", out)

    def test_audit_json(self):
        path = self.repo / "mcp-fleet.local.yml"
        write(path, "servers:\n    x:\n        probe:\n            command: ['true']\n")
        code, out = run("audit", "--repo", str(self.repo), "--json")
        self.assertEqual(code, 0, out)
        data = json.loads(out)
        self.assertEqual(data[0]["name"], "x")
        self.assertIn(data[0]["verdict"], ("up", "down"))


class Lifecycle(Temp):
    def test_start_runs_declared_command(self):
        marker = self.tmp / "started.txt"
        path = self.repo / "mcp-fleet.local.yml"
        write(path, "\n".join([
            "servers:",
            "    daemon:",
            "        lifecycle:",
            f"            start: ['{sys.executable}', '-c', 'from pathlib import Path as P; P(r\"{marker}\").write_text(\"on\")']",
        ]))
        code, out = run("start", "daemon", "--repo", str(self.repo))
        self.assertEqual(code, 0, out)
        self.assertTrue(marker.is_file())

    def test_unknown_server_fails_cleanly(self):
        write(self.repo / "mcp-fleet.local.yml", "servers:\n    x: {}\n")
        code, out = run("stop", "nope", "--repo", str(self.repo))
        self.assertEqual(code, 1)
        self.assertIn("UNKNOWN SERVER", out)

    def test_undeclared_action_fails(self):
        write(self.repo / "mcp-fleet.local.yml", "servers:\n    x: {}\n")
        code, out = run("restart", "x", "--repo", str(self.repo))
        self.assertEqual(code, 1)
        self.assertIn("no stop/start commands declared", out)


class ReadOnly(Temp):
    def test_read_only_commands_never_write(self):
        listener = Listener()
        self.addCleanup(listener.stop)
        write(self.repo / "mcp-fleet.local.yml", "\n".join([
            "servers:",
            "    web:",
            "        probe:",
            f"            url: '{listener.url}'",
        ]))
        (self.repo / "trackme.txt").write_text("stable", encoding="utf-8")

        def snapshot() -> dict[str, bytes]:
            return {
                str(p.relative_to(self.repo)): p.read_bytes()
                for p in sorted(self.repo.rglob("*"))
                if p.is_file()
            }

        before = snapshot()
        for args in (["inventory"], ["audit"], ["probe", "web"], ["doctor"], ["doctor", "--json"]):
            code, _ = run(*args, "--repo", str(self.repo))
            self.assertEqual(code, 0, args)
        self.assertEqual(snapshot(), before)


class KitInvariants(unittest.TestCase):
    def test_script_mirror_is_byte_identical(self):
        mirror = ROOT / "skills" / "agent-mcp" / "scripts" / "mcp_agents.py"
        self.assertEqual(SCRIPT.read_bytes(), mirror.read_bytes())

    def test_imports_stdlib_only(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        allowed = set(sys.stdlib_module_names)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            else:
                continue
            for name in names:
                self.assertTrue(name.split(".")[0] in allowed, f"non-stdlib import: {name}")

    def test_script_is_lf_and_utf8_no_bom(self):
        raw = SCRIPT.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r\n", raw)

    def test_gitattributes_pins_lf_on_byte_compared_paths(self):
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("scripts/** text eol=lf", attributes)
        self.assertIn("skills/** text eol=lf", attributes)

    def test_gitignore_covers_local_descriptor(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("mcp-fleet.local.yml", ignored)

    def test_template_is_valid_and_path_free(self):
        template = ROOT / "template" / "mcp-fleet.template.yml"
        raw = template.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r\n", raw)
        text = raw.decode("utf-8")
        data = ma.parse_yaml_subset(text)
        self.assertIn("servers", data)
        self.assertIn("defaults", data)
        # Machine specifics stay out of the kit: no absolute Windows path and
        # no home-directory fragment anywhere in the template.
        self.assertNotRegex(text, r"[A-Za-z]:\\")
        self.assertNotRegex(text, r"(?i)\busers\b")
        self.assertNotRegex(text, r"(?i)\bDesktop\b")

    def test_template_is_git_tracked(self):
        completed = subprocess.run(
            ["git", "ls-files", "template/mcp-fleet.template.yml"],
            capture_output=True, text=True, cwd=ROOT, check=True,
        )
        self.assertEqual(completed.stdout.strip(), "template/mcp-fleet.template.yml")

    def test_local_descriptor_is_not_git_tracked(self):
        completed = subprocess.run(
            ["git", "ls-files", "mcp-fleet.local.yml"],
            capture_output=True, text=True, cwd=ROOT, check=True,
        )
        self.assertEqual(completed.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
