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

    def test_code_main_params_must_match_declared_inputs(self) -> None:
        data = {
            "chatConfig": {"variables": []},
            "nodes": [
                {"nodeId": "S00", "name": "start", "flowNodeType": "workflowStart", "inputs": [], "outputs": [{"id": "userChatInput", "key": "userChatInput", "valueType": "string"}]},
                {
                    "nodeId": "C00",
                    "name": "code",
                    "flowNodeType": "code",
                    "inputs": [
                        {"key": "system_addInputParam"},
                        {"key": "data1", "value": ["S00", "userChatInput"]},
                        {"key": "data2", "value": ["S00", "userChatInput"]},
                        {"key": "codeType", "value": "js"},
                        {"key": "code", "value": "function main({data1, missing}){ return {result: data1}; }"},
                    ],
                    "outputs": [{"id": "result", "key": "result", "type": "dynamic", "valueType": "string"}],
                },
                {"nodeId": "A00", "name": "answer", "flowNodeType": "answerNode", "inputs": [], "outputs": []},
            ],
            "edges": [
                {"source": "S00", "target": "C00", "sourceHandle": "S00-source-right", "targetHandle": "C00-target-left"},
                {"source": "C00", "target": "A00", "sourceHandle": "C00-source-right", "targetHandle": "A00-target-left"},
            ],
        }

        issues = self.inspector.inspect_export(data)["issues"]
        rendered = "\n".join(issues)

        self.assertIn("code main() params not declared as inputs: missing", rendered)
        self.assertIn("code inputs not accepted by main(): data2", rendered)

    def test_non_terminal_dangling_node_is_reported(self) -> None:
        data = {
            "chatConfig": {"variables": []},
            "nodes": [
                {"nodeId": "S00", "name": "start", "flowNodeType": "workflowStart", "inputs": [], "outputs": [{"id": "userChatInput", "key": "userChatInput", "valueType": "string"}]},
                {"nodeId": "V00", "name": "save state", "flowNodeType": "variableUpdate", "inputs": [{"key": "updateList", "value": []}], "outputs": []},
            ],
            "edges": [
                {"source": "S00", "target": "V00", "sourceHandle": "S00-source-right", "targetHandle": "V00-target-left"}
            ],
        }

        issues = self.inspector.inspect_export(data)["issues"]

        self.assertTrue(any("save state: non-terminal node has no outgoing edge" in issue for issue in issues))

    def test_code_catch_edge_is_valid_when_catch_error_is_enabled(self) -> None:
        data = {
            "chatConfig": {"variables": []},
            "nodes": [
                {"nodeId": "S00", "name": "start", "flowNodeType": "workflowStart", "inputs": [], "outputs": [{"id": "userChatInput", "key": "userChatInput", "valueType": "string"}]},
                {
                    "nodeId": "C00",
                    "name": "code",
                    "flowNodeType": "code",
                    "catchError": True,
                    "inputs": [
                        {"key": "system_addInputParam"},
                        {"key": "data1", "value": ["S00", "userChatInput"]},
                        {"key": "codeType", "value": "js"},
                        {"key": "code", "value": "function main({data1}){ return {result: data1}; }"},
                    ],
                    "outputs": [{"id": "result", "key": "result", "type": "dynamic", "valueType": "string"}],
                },
                {"nodeId": "A00", "name": "answer", "flowNodeType": "answerNode", "inputs": [], "outputs": []},
            ],
            "edges": [
                {"source": "S00", "target": "C00", "sourceHandle": "S00-source-right", "targetHandle": "C00-target-left"},
                {"source": "C00", "target": "A00", "sourceHandle": "C00-source_catch-right", "targetHandle": "A00-target-left"},
            ],
        }

        issues = self.inspector.inspect_export(data)["issues"]

        self.assertFalse(any("ordinary node sourceHandle" in issue for issue in issues))

    def test_chat_node_optional_null_values_are_reported(self) -> None:
        data = {
            "chatConfig": {"variables": []},
            "nodes": [
                {
                    "nodeId": "C00",
                    "name": "chat",
                    "flowNodeType": "chatNode",
                    "inputs": [
                        {"key": "model", "value": "deepseek-v4-flash"},
                        {"key": "systemPrompt", "value": "hello"},
                        {"key": "userChatInput", "value": "hello"},
                        {"key": "quotePrompt", "value": None},
                    ],
                    "outputs": [{"id": "answerText", "key": "answerText", "valueType": "string"}],
                }
            ],
            "edges": [],
        }

        issues = self.inspector.inspect_export(data)["issues"]

        self.assertTrue(any("quotePrompt has value null" in issue for issue in issues))

    def test_text_editor_direct_interpolation_is_reported(self) -> None:
        data = {
            "chatConfig": {"variables": []},
            "nodes": [
                {"nodeId": "S00", "name": "start", "flowNodeType": "workflowStart", "inputs": [], "outputs": [{"id": "userChatInput", "key": "userChatInput", "valueType": "string"}]},
                {
                    "nodeId": "T00",
                    "name": "text",
                    "flowNodeType": "textEditor",
                    "inputs": [{"key": "system_textareaInput", "value": "用户输入：{{$S00.userChatInput$}}"}],
                    "outputs": [{"id": "system_text", "key": "system_text", "valueType": "string"}],
                },
                {"nodeId": "A00", "name": "answer", "flowNodeType": "answerNode", "inputs": [], "outputs": []},
            ],
            "edges": [
                {"source": "S00", "target": "T00", "sourceHandle": "S00-source-right", "targetHandle": "T00-target-left"},
                {"source": "T00", "target": "A00", "sourceHandle": "T00-source-right", "targetHandle": "A00-target-left"},
            ],
        }

        issues = self.inspector.inspect_export(data)["issues"]

        self.assertTrue(any("textEditor uses direct" in issue for issue in issues))

    def test_missing_top_level_shape_is_reported(self) -> None:
        issues = self.inspector.inspect_export({})["issues"]

        self.assertIn("top-level JSON missing chatConfig", issues)
        self.assertIn("top-level JSON missing nodes", issues)
        self.assertIn("top-level JSON missing edges", issues)

    def test_classify_question_category_handles_are_valid(self) -> None:
        data = {
            "chatConfig": {"variables": []},
            "nodes": [
                {"nodeId": "S00", "name": "start", "flowNodeType": "workflowStart", "inputs": [], "outputs": [{"id": "userChatInput", "key": "userChatInput", "valueType": "string"}]},
                {
                    "nodeId": "C00",
                    "name": "classify",
                    "flowNodeType": "classifyQuestion",
                    "inputs": [{"key": "agents", "value": [{"key": "sales", "value": "Sales"}]}],
                    "outputs": [{"id": "cqResult", "key": "cqResult", "valueType": "string"}],
                },
                {"nodeId": "A00", "name": "answer", "flowNodeType": "answerNode", "inputs": [], "outputs": []},
            ],
            "edges": [
                {"source": "S00", "target": "C00", "sourceHandle": "S00-source-right", "targetHandle": "C00-target-left"},
                {"source": "C00", "target": "A00", "sourceHandle": "C00-source-sales", "targetHandle": "A00-target-left"},
            ],
        }

        issues = self.inspector.inspect_export(data)["issues"]

        self.assertFalse(any("classifyQuestion sourceHandle" in issue for issue in issues))

    def test_tools_selected_edges_are_valid(self) -> None:
        data = {
            "chatConfig": {"variables": []},
            "nodes": [
                {"nodeId": "S00", "name": "start", "flowNodeType": "workflowStart", "inputs": [], "outputs": [{"id": "userChatInput", "key": "userChatInput", "valueType": "string"}]},
                {"nodeId": "T00", "name": "tools", "flowNodeType": "tools", "inputs": [], "outputs": [{"id": "answerText", "key": "answerText", "valueType": "string"}]},
                {"nodeId": "K00", "name": "tool", "flowNodeType": "tool", "inputs": [], "outputs": [{"id": "result", "key": "result", "valueType": "arrayObject"}]},
                {"nodeId": "E00", "name": "stop", "flowNodeType": "stopTool", "inputs": [], "outputs": []},
            ],
            "edges": [
                {"source": "S00", "target": "T00", "sourceHandle": "S00-source-right", "targetHandle": "T00-target-left"},
                {"source": "T00", "target": "K00", "sourceHandle": "selectedTools", "targetHandle": "selectedTools"},
                {"source": "T00", "target": "E00", "sourceHandle": "T00-source-right", "targetHandle": "E00-target-left"},
            ],
        }

        issues = self.inspector.inspect_export(data)["issues"]

        self.assertFalse(any("selectedTools" in issue for issue in issues))

    def test_workflow_start_user_files_is_allowed_as_builtin_output(self) -> None:
        data = {
            "chatConfig": {"variables": []},
            "nodes": [
                {"nodeId": "S00", "name": "start", "flowNodeType": "workflowStart", "inputs": [], "outputs": [{"id": "userChatInput", "key": "userChatInput", "valueType": "string"}]},
                {
                    "nodeId": "R00",
                    "name": "read files",
                    "flowNodeType": "readFiles",
                    "inputs": [{"key": "fileUrlList", "value": [["S00", "userFiles"]]}],
                    "outputs": [
                        {"id": "system_text", "key": "system_text", "valueType": "string"},
                        {"id": "system_rawResponse", "key": "system_rawResponse", "valueType": "arrayObject"},
                    ],
                },
            ],
            "edges": [
                {"source": "S00", "target": "R00", "sourceHandle": "S00-source-right", "targetHandle": "R00-target-left"}
            ],
        }

        issues = self.inspector.inspect_export(data)["issues"]

        self.assertFalse(any("unknown output userFiles" in issue for issue in issues))

    def test_loop_input_warns_when_reference_is_not_array(self) -> None:
        data = {
            "chatConfig": {"variables": []},
            "nodes": [
                {"nodeId": "S00", "name": "start", "flowNodeType": "workflowStart", "inputs": [], "outputs": [{"id": "userChatInput", "key": "userChatInput", "valueType": "string"}]},
                {
                    "nodeId": "L00",
                    "name": "loop",
                    "flowNodeType": "loop",
                    "inputs": [
                        {"key": "loopInputArray", "value": [["S00", "userChatInput"]]},
                        {"key": "childrenNodeIdList", "value": ["LS0", "LE0"]},
                    ],
                    "outputs": [{"id": "loopArray", "key": "loopArray", "valueType": "arrayString"}],
                },
                {"nodeId": "LS0", "name": "start item", "flowNodeType": "loopStart", "inputs": [], "outputs": [{"id": "loopStartIndex", "key": "loopStartIndex", "valueType": "number"}, {"id": "loopStartInput", "key": "loopStartInput", "valueType": "string"}]},
                {"nodeId": "LE0", "name": "end item", "flowNodeType": "loopEnd", "inputs": [{"key": "loopEndInput", "value": ["LS0", "loopStartInput"]}], "outputs": []},
            ],
            "edges": [
                {"source": "S00", "target": "L00", "sourceHandle": "S00-source-right", "targetHandle": "L00-target-left"}
            ],
        }

        issues = self.inspector.inspect_export(data)["issues"]

        self.assertTrue(any("loopInputArray references non-array valueType string" in issue for issue in issues))

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
