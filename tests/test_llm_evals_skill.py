"""Invariants of the authored llm-evals skill (doc-only: no script to test)."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "llm-evals"
REFERENCE_FILES = (
    "references/promptfoo.md",
    "references/deepeval.md",
    "references/inspect-ai.md",
)


class KitInvariants(unittest.TestCase):
    """Same discipline as the other kit skills: registered, English, secret-free."""

    def test_skill_registered_in_skills_json(self):
        registry = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
        entry = registry["skills"].get("llm-evals")
        self.assertIsNotNone(entry, "llm-evals must be in skills.json")
        self.assertEqual(entry["source"], "(authored)")
        self.assertEqual(entry["license"], "MIT")
        expected = {"SKILL.md", *REFERENCE_FILES}
        self.assertEqual(set(entry["files"]), expected)

    def test_skill_files_are_ascii(self):
        files = [SKILL_DIR / "SKILL.md", *(SKILL_DIR / r for r in REFERENCE_FILES)]
        for path in files:
            self.assertTrue(path.is_file(), f"missing skill file: {path.name}")
            path.read_bytes().decode("ascii")

    def test_no_secrets_in_skill(self):
        for path in SKILL_DIR.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("sk-", text)
            self.assertNotIn("api_key=", text)


if __name__ == "__main__":
    unittest.main()
