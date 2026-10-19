"""Tests for the video-toolchain skill script (authored, stdlib-only).

Hermetic: every probe runs against a fake runner / fake which / temporary
files - the suite never depends on the tools of the machine it runs on.
"""

import ast
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "video-toolchain" / "scripts" / "video_toolchain.py"

_spec = importlib.util.spec_from_file_location("video_toolchain", SCRIPT)
vt = importlib.util.module_from_spec(_spec)
sys.modules["video_toolchain"] = vt
_spec.loader.exec_module(vt)


def ok_run(stdout: str):
    return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")


def fail_run():
    return subprocess.CompletedProcess([], 1, stdout="", stderr="boom")


class FakeRunner:
    """Returns ok(stdout) for argv matching a prefix, else a failure."""

    def __init__(self, good: dict[str, str]):
        self.good = good
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        for prefix, stdout in self.good.items():
            if argv[0].endswith(prefix) or (len(argv) > 1 and f"{argv[0]} {argv[1]}".startswith(prefix)):
                return ok_run(stdout)
        return fail_run()


class ProbeCommand(unittest.TestCase):
    def test_returns_first_non_empty_line(self):
        runner = FakeRunner({"node": "\n   v24.1.0  \nmore"})
        self.assertEqual(vt.probe_command(["node", "--version"], runner=runner), "v24.1.0")

    def test_none_on_failure_and_timeout(self):
        self.assertIsNone(vt.probe_command(["nope"], runner=FakeRunner({})))
        def timeout_runner(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, 1)
        self.assertIsNone(vt.probe_command(["slow"], runner=timeout_runner))

    def test_none_on_os_error(self):
        def error_runner(argv, **kwargs):
            raise OSError("not found")
        self.assertIsNone(vt.probe_command(["gone"], runner=error_runner))


class EnvGet(unittest.TestCase):
    def test_exact_key_first(self):
        self.assertEqual(vt.env_get({"CHROME_PATH": "/a", "chrome_path": "/b"}, "CHROME_PATH"), "/a")

    def test_case_drift_found(self):
        env = {"PROGRAMFILES": "C:/Program Files"}
        self.assertEqual(vt.env_get(env, "ProgramFiles"), "C:/Program Files")
        self.assertEqual(vt.env_get(env, "ProgramFiles(x86)"), None)


class ChromeResolution(unittest.TestCase):
    def test_order_override_env_extra(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "chrome.exe"
            fake.write_bytes(b"x")
            other = Path(tmp) / "never.exe"
            other.write_bytes(b"x")
            env = {"CHROME_PATH": str(fake), "PLAYWRIGHT_CHROME": str(other)}
            self.assertEqual(vt.find_chrome(None, env, "win32"), str(fake))
            self.assertEqual(vt.find_chrome(str(other), env, "win32"), str(other))
            env2 = {"PLAYWRIGHT_CHROME": str(other)}
            self.assertEqual(vt.find_chrome(None, env2, "win32"), str(other))
            # no env hit: extra paths (standard-path injection point) win over PATH
            self.assertEqual(
                vt.find_chrome(None, {}, "linux", extra_paths=[str(fake)], which=lambda n: str(other)),
                str(fake),
            )

    def test_standard_windows_paths_case_insensitive(self):
        env = {"PROGRAMFILES": "C:/Program Files"}  # Git Bash inheritance drift
        self.assertEqual(
            vt.standard_chrome_paths("win32", env),
            ["C:/Program Files\\Google\\Chrome\\Application\\chrome.exe"],
        )

    def test_path_lookup_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "chromium"
            fake.write_bytes(b"x")
            found = vt.find_chrome(None, {}, "linux", which=lambda n: str(fake) if n == "chromium" else None)
            self.assertEqual(found, str(fake))

    def test_missing(self):
        self.assertIsNone(vt.find_chrome(None, {}, "linux", which=lambda n: None))


class PythonCandidates(unittest.TestCase):
    def test_order_uv_before_bare_python(self):
        argvs = [argv for argv, _ in vt.python_candidates(None, which=lambda n: f"/bin/{n}")]
        self.assertEqual(argvs[0], ["uv", "run", "--no-project", "--with", "numpy",
                                    "--with", "pillow", "python"])
        self.assertIn(["/bin/python"], argvs)
        self.assertIn(["/bin/python3"], argvs)

    def test_explicit_first_and_no_uv(self):
        argvs = [argv for argv, _ in vt.python_candidates("/x/py", which=lambda n: None)]
        self.assertEqual(argvs, [["/x/py"]])

    def test_probe_reports_working_candidate(self):
        runner = FakeRunner({"uv": "2.5.4 numpy / Pillow 13.0.0"})
        detail = vt.probe_python_modules([(["uv", "python"], 1.0)], runner=runner)
        self.assertIn("numpy / Pillow", detail)
        self.assertIn("(via uv)", detail)
        self.assertIsNone(vt.probe_python_modules([(["python"], 1.0)], runner=FakeRunner({})))


class CheckEverything(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.chrome = Path(self.tmp) / "chrome.exe"
        self.chrome.write_bytes(b"x")

    def all_ok_runner(self):
        return FakeRunner({
            "node": "v24.1.0",
            "ffmpeg": "ffmpeg version 9.0",
            "uv run": "1.0 numpy / Pillow 2.0",
            "python": "1.0 numpy / Pillow 2.0",
            "ruby": "ruby 3.2.0",
        })

    def check(self, runner=None, env=None, **kwargs):
        kwargs.setdefault("chrome_paths", [str(self.chrome)])
        return vt.check_everything(
            runner=runner or self.all_ok_runner(),
            env=env if env is not None else {},
            which=kwargs.pop("which", lambda n: "/bin/" + n),
            **kwargs,
        )

    def test_all_present_ok(self):
        ok, tools = self.check()
        self.assertTrue(ok)
        self.assertEqual(tools["node"]["status"], "ok")
        self.assertEqual(tools["chrome"]["detail"], str(self.chrome))
        self.assertEqual(tools["ruby (optional)"]["status"], "ok")

    def test_missing_required_fails_with_named_hint(self):
        ok, tools = self.check(runner=FakeRunner({"node": "v1"}), which=lambda n: None,
                               chrome_paths=[])
        self.assertFalse(ok)
        for name in ("ffmpeg", "python-numpy-pil", "chrome"):
            self.assertEqual(tools[name]["status"], "missing", name)
            self.assertTrue(tools[name]["hint"], name)

    def test_ruby_optional_never_fails(self):
        ok, tools = self.check(runner=FakeRunner({
            "node": "v1", "ffmpeg": "f", "uv run": "n/p", "python": "n/p",
        }))
        self.assertTrue(ok)
        self.assertEqual(tools["ruby (optional)"]["status"], "optional")

    def test_chrome_via_env(self):
        ok, _ = self.check(env={"CHROME_PATH": str(self.chrome)})
        self.assertTrue(ok)


class OutputAndMain(unittest.TestCase):
    def check_args(self, **kwargs):
        return vt.check_everything(
            runner=FakeRunner({"node": "v1", "ffmpeg": "f", "uv run": "n/p", "python": "n/p"}),
            env={},
            which=lambda n: None,
            **kwargs,
        )

    def test_json_output_shape(self):
        ok, tools = self.check_args()
        payload = json.loads(vt.render_json(ok, tools))
        self.assertEqual(payload["ok"], False)
        self.assertIn("tools", payload)
        self.assertEqual(
            sorted(payload["tools"]),
            sorted(["node", "ffmpeg", "python-numpy-pil", "chrome", "ruby (optional)"]),
        )
        self.assertEqual(payload["tools"]["chrome"]["status"], "missing")

    def test_text_names_every_missing_tool(self):
        ok, tools = self.check_args()
        text = vt.render_text(ok, tools)
        self.assertIn("MISSING REQUIRED TOOLS", text)
        self.assertIn("chrome: [missing]", text)
        self.assertIn("fix:", text)

    def test_main_exit_codes_and_json_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            chrome = Path(tmp) / "chrome.exe"
            chrome.write_bytes(b"x")
            good = FakeRunner({"node": "v1", "ffmpeg": "f", "uv run": "n/p", "python": "n/p"})
            bad = FakeRunner({})
            real_check = vt.check_everything  # bound defaults (runner/which) resist
            for runner, which, code, argv, needle in (   # module-attr patching: inject here
                (good, lambda n: "/bin/" + n, 0, ["--chrome", str(chrome)], "OK"),
                (bad, lambda n: None, 1, ["--json"], '"ok": false'),
            ):
                def injected(*a, runner=runner, which=which, **k):
                    return real_check(*a, runner=runner, env={}, which=which, **k)

                with mock.patch.object(vt, "check_everything", side_effect=injected):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        self.assertEqual(vt.main(argv), code)
                    self.assertIn(needle, buffer.getvalue())


class KitInvariants(unittest.TestCase):
    """Same discipline as the other kit scripts: stdlib-only, ASCII messages."""

    def test_stdlib_only_imports(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                imported.add((node.module or "").split(".")[0])
        self.assertEqual(imported - set(sys.stdlib_module_names), set())

    def test_source_is_ascii(self):
        SCRIPT.read_bytes().decode("ascii")

    def test_skill_registered_in_skills_json(self):
        registry = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
        entry = registry["skills"].get("video-toolchain")
        self.assertIsNotNone(entry, "video-toolchain must be in skills.json")
        self.assertEqual(entry["source"], "(authored)")
        self.assertEqual(entry["license"], "MIT")
        self.assertIn("scripts/video_toolchain.py", entry["files"])
        self.assertIn("SKILL.md", entry["files"])

    def test_no_secrets_in_skill(self):
        for path in (SCRIPT, SCRIPT.parent.parent / "SKILL.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("sk-", text)
            self.assertNotIn("api_key=", text.replace("API_KEY env var", ""))


if __name__ == "__main__":
    unittest.main()
