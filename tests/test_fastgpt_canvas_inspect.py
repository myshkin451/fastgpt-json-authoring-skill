from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "fastgpt-json-authoring" / "scripts" / "fastgpt_canvas_inspect.py"
FIXTURES = ROOT / "tests" / "fixtures"


def load_inspector_module():
    spec = importlib.util.spec_from_file_location("fastgpt_canvas_inspect", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load inspector module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FastGPTCanvasInspectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inspector = load_inspector_module()

    def test_minimal_valid_export_has_no_issues(self) -> None:
        data = self.inspector.load_export(FIXTURES / "minimal_valid_app.json")
        summary = self.inspector.inspect_export(data)

        self.assertEqual(summary["node_count"], 2)
        self.assertEqual(summary["edge_count"], 1)
        self.assertEqual(summary["issues"], [])
        self.assertEqual(summary["var_key_by_label"]["login_name"], "varLogin")

    def test_risky_export_reports_expected_issues(self) -> None:
        data = self.inspector.load_export(FIXTURES / "risky_backedge_app.json")
        issues = self.inspector.inspect_export(data)["issues"]
        rendered = "\n".join(issues)

        self.assertIn("suspicious back edge", rendered)
        self.assertIn("datasetSearchNode datasets value is empty", rendered)
        self.assertIn("catchError is true but no catch edge was found", rendered)
        self.assertIn("may contain an unredacted secret", rendered)

    def test_cli_json_output_is_machine_readable(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(FIXTURES / "minimal_valid_app.json"),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(payload["node_count"], 2)
        self.assertEqual(payload["edge_count"], 1)
        self.assertEqual(payload["issues"], [])

    def test_utf8_bom_export_loads(self) -> None:
        source = (FIXTURES / "minimal_valid_app.json").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bom.json"
            path.write_text("\ufeff" + source, encoding="utf-8")

            data = self.inspector.load_export(path)

        self.assertIn("chatConfig", data)

    def test_unknown_output_reference_is_reported(self) -> None:
        data = self.inspector.load_export(FIXTURES / "minimal_valid_app.json")
        data["nodes"][1]["inputs"].append(
            {
                "key": "badRef",
                "value": ["S00", "missingOutput"],
            }
        )

        issues = self.inspector.inspect_export(data)["issues"]

        self.assertTrue(any("unknown output missingOutput" in issue for issue in issues))

    def test_missing_top_level_shape_is_reported(self) -> None:
        issues = self.inspector.inspect_export({})["issues"]

        self.assertIn("top-level JSON missing chatConfig", issues)
        self.assertIn("top-level JSON missing nodes", issues)
        self.assertIn("top-level JSON missing edges", issues)

    def test_duplicate_ids_are_reported(self) -> None:
        data = self.inspector.load_export(FIXTURES / "minimal_valid_app.json")
        data["nodes"].append(dict(data["nodes"][0]))
        data["chatConfig"]["variables"].append(dict(data["chatConfig"]["variables"][0]))

        issues = self.inspector.inspect_export(data)["issues"]
        rendered = "\n".join(issues)

        self.assertIn("duplicate nodeId S00", rendered)
        self.assertIn("duplicate variable label login_name", rendered)
        self.assertIn("duplicate variable key varLogin", rendered)

    def test_skill_frontmatter_matches_codex_skill_rules(self) -> None:
        skill_md = ROOT / "skills" / "fastgpt-json-authoring" / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)

        self.assertIsNotNone(match)
        frontmatter = {}
        for line in match.group(1).splitlines():
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip()

        self.assertEqual(set(frontmatter), {"name", "description"})
        self.assertEqual(frontmatter["name"], "fastgpt-json-authoring")
        self.assertRegex(frontmatter["name"], r"^[a-z0-9-]+$")
        self.assertLessEqual(len(frontmatter["name"]), 64)
        self.assertGreater(len(frontmatter["description"]), 80)
        self.assertLessEqual(len(frontmatter["description"]), 1024)
        self.assertNotRegex(frontmatter["description"], r"[<>]")


if __name__ == "__main__":
    unittest.main()
