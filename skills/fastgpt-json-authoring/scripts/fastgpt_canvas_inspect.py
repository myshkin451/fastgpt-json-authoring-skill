#!/usr/bin/env python3
"""Inspect a FastGPT exported application JSON without modifying it."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, deque
from pathlib import Path
from typing import Any


VARIABLE_NODE_ID = "VARIABLE_NODE_ID"
BUILTIN_VARIABLE_KEYS = {"system_entryPoint", "userId", "appId", "cTime"}
BUILTIN_NODE_OUTPUT_VALUE_TYPES = {
    "workflowStart": {
        "userChatInput": "string",
        "userFiles": "arrayString",
    }
}
SECRET_HEADER_KEYS = {"authorization", "x-agent-token", "x-api-key", "api-key"}
INTERPOLATION_RE = re.compile(r"\{\{\$([^.{}$]+)\.([^{}$]+)\$\}\}")
OBJECT_ID_RE = re.compile(r"^[0-9a-fA-F]{24}$")
TEXT_EDITOR_DIRECT_INTERPOLATION_RE = re.compile(r"\{\{\$[^.{}$]+\.[^{}$]+\$\}\}")
UPSTREAM_TARGET_RE = re.compile(r"(G00|M00|menu|gate|entry|入口|菜单|确认门)", re.IGNORECASE)
DOWNSTREAM_SOURCE_RE = re.compile(r"(N00|A12|next|follow|switch|下一步|追问)", re.IGNORECASE)
TERMINAL_NODE_TYPES = {"answerNode", "chatNode", "userGuide", "customFeedback", "stopTool", "loopEnd"}
CODE_SYSTEM_INPUT_KEYS = {"system_addInputParam", "codeType", "code"}
JS_MAIN_DESTRUCTURED_RE = re.compile(r"function\s+main\s*\(\s*\{([^}]*)\}")
CHAT_OPTIONAL_OMIT_VALUE_KEYS = {
    "quoteTemplate",
    "quotePrompt",
    "aiChatTopP",
    "aiChatStopSign",
    "aiChatResponseFormat",
    "aiChatJsonSchema",
}


def load_export(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value is not an object")
    return data


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def get_input(node: dict[str, Any], key: str) -> Any:
    for item in as_list(node.get("inputs")):
        if isinstance(item, dict) and item.get("key") == key:
            return item.get("value")
    return None


def input_item(node: dict[str, Any], key: str) -> dict[str, Any] | None:
    for item in as_list(node.get("inputs")):
        if isinstance(item, dict) and item.get("key") == key:
            return item
    return None


def text_cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("|", "\\|")
    return text if len(text) <= 80 else text[:77] + "..."


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(text_cell(cell) for cell in row) + " |")
    return "\n".join(lines)


def node_name(node_by_id: dict[str, dict[str, Any]], node_id: Any) -> str:
    node = node_by_id.get(str(node_id))
    if not node:
        return f"<missing:{node_id}>"
    return str(node.get("name") or node.get("nodeId") or node_id)


def output_maps(
    nodes: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, str]], dict[str, set[str]], dict[str, dict[str, str]]]:
    by_key: dict[str, dict[str, str]] = {}
    ids: dict[str, set[str]] = {}
    value_types: dict[str, dict[str, str]] = {}
    for node in nodes:
        node_id = str(node.get("nodeId", ""))
        by_key[node_id] = {}
        ids[node_id] = set()
        value_types[node_id] = {}
        for output in as_list(node.get("outputs")):
            if not isinstance(output, dict):
                continue
            output_id = output.get("id")
            output_key = output.get("key")
            if output_id is not None:
                ids[node_id].add(str(output_id))
                if output.get("valueType") is not None:
                    value_types[node_id][str(output_id)] = str(output["valueType"])
            if output_key is not None and output_id is not None:
                by_key[node_id][str(output_key)] = str(output_id)
    return by_key, ids, value_types


def walk_json(value: Any, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk_json(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_json(child, f"{path}[{index}]")


def looks_like_reference_pair(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], str)
        and bool(value[0])
    )


def looks_like_template_value(value: str) -> bool:
    return "{{" in value and "}}" in value


def is_reference_field(path: str) -> bool:
    return ".value" in path or ".variable" in path


def node_input_keys(node: dict[str, Any]) -> set[str]:
    return {
        str(item["key"])
        for item in as_list(node.get("inputs"))
        if isinstance(item, dict) and item.get("key") is not None
    }


def code_custom_input_keys(node: dict[str, Any]) -> set[str]:
    return {
        str(item["key"])
        for item in as_list(node.get("inputs"))
        if (
            isinstance(item, dict)
            and item.get("key") is not None
            and str(item["key"]) not in CODE_SYSTEM_INPUT_KEYS
            and str(item["key"]).isidentifier()
        )
    }


def js_main_destructured_params(code: str) -> set[str] | None:
    match = JS_MAIN_DESTRUCTURED_RE.search(code)
    if not match:
        return None
    params: set[str] = set()
    for raw_part in match.group(1).split(","):
        part = raw_part.strip()
        if not part:
            continue
        name = part.split("=", 1)[0].strip()
        if ":" in name:
            name = name.split(":", 1)[0].strip().strip("\"'")
        if name.isidentifier():
            params.add(name)
    return params


def builtin_node_output_value_type(node: dict[str, Any], output_key: str) -> str | None:
    node_type = str(node.get("flowNodeType", ""))
    return BUILTIN_NODE_OUTPUT_VALUE_TYPES.get(node_type, {}).get(output_key)


def has_node_output(
    node: dict[str, Any],
    node_id: str,
    output_key: str,
    valid_output_ids: dict[str, set[str]],
) -> bool:
    return (
        output_key in valid_output_ids.get(node_id, set())
        or builtin_node_output_value_type(node, output_key) is not None
    )


def first_reference_pair(value: Any) -> list[str] | None:
    if looks_like_reference_pair(value):
        return value
    if isinstance(value, list) and len(value) == 1 and looks_like_reference_pair(value[0]):
        return value[0]
    return None


def source_handle_issue(
    edge: dict[str, Any],
    source_node: dict[str, Any],
    valid_output_ids: dict[str, set[str]],
) -> str | None:
    source = str(edge.get("source", ""))
    handle = str(edge.get("sourceHandle", ""))
    node_type = str(source_node.get("flowNodeType", ""))
    expected_right = f"{source}-source-right"

    if node_type == "ifElseNode":
        if handle in {f"{source}-source-IF", f"{source}-source-ELSE"}:
            return None
        if re.fullmatch(rf"{re.escape(source)}-source-ELSE IF \d+", handle):
            return None
        return "ifElseNode sourceHandle should be source-IF, source-ELSE IF N, or source-ELSE"

    if node_type == "classifyQuestion":
        category_keys = set()
        for category in as_list(get_input(source_node, "agents")):
            if isinstance(category, dict) and category.get("key") is not None:
                category_keys.add(str(category["key"]))
        expected = {f"{source}-source-{key}" for key in category_keys}
        if expected and handle not in expected:
            return "classifyQuestion sourceHandle does not match any agents key"
        if not expected and handle != expected_right:
            return "classifyQuestion has no categories and sourceHandle is not the ordinary right handle"
        return None

    if node_type == "userSelect":
        option_keys = set()
        for option in as_list(get_input(source_node, "userSelectOptions")):
            if isinstance(option, dict) and option.get("key") is not None:
                option_keys.add(str(option["key"]))
        expected = {f"{source}-source-{key}" for key in option_keys}
        if expected and handle not in expected:
            return "userSelect sourceHandle does not match any userSelectOptions key"
        if not expected and handle != expected_right:
            return "userSelect has no options and sourceHandle is not the ordinary right handle"
        return None

    if node_type == "tools":
        if handle == "selectedTools":
            return None
        if handle != expected_right:
            return "tools sourceHandle should be source-right or selectedTools"
        return None

    if node_type.startswith("httpRequest"):
        catch_handle = f"{source}-source_catch-right"
        if handle == catch_handle:
            return None
        if handle != expected_right:
            return "HTTP sourceHandle should be source-right or source_catch-right"
        return None

    if source_node.get("catchError") is True and handle == f"{source}-source_catch-right":
        return None

    if handle != expected_right:
        output_suffix = handle.removeprefix(f"{source}-source-")
        if output_suffix in valid_output_ids.get(source, set()):
            return None
        return "ordinary node sourceHandle should use source-right"
    return None


def target_handle_issue(
    edge: dict[str, Any],
    source_node: dict[str, Any] | None,
    target_node: dict[str, Any] | None,
) -> str | None:
    target = str(edge.get("target", ""))
    target_handle = str(edge.get("targetHandle", ""))
    source_type = str(source_node.get("flowNodeType", "")) if source_node else ""
    source_handle = str(edge.get("sourceHandle", ""))

    if source_type == "tools" and source_handle == "selectedTools":
        if target_handle != "selectedTools":
            return "tools selectedTools edge targetHandle should be selectedTools"
        return None

    if target_node and target_handle != f"{target}-target-left":
        return f"targetHandle should be {target}-target-left"
    return None


def build_reachability(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, int]:
    incoming = Counter(str(edge.get("target", "")) for edge in edges)
    starts = [
        str(node.get("nodeId", ""))
        for node in nodes
        if node.get("flowNodeType") == "workflowStart"
    ]
    starts.extend(
        str(node.get("nodeId", ""))
        for node in nodes
        if str(node.get("nodeId", "")) and incoming[str(node.get("nodeId", ""))] == 0
    )
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        adjacency.setdefault(source, []).append(target)

    depth: dict[str, int] = {}
    queue: deque[tuple[str, int]] = deque((node_id, 0) for node_id in starts)
    while queue:
        node_id, current_depth = queue.popleft()
        if node_id in depth and depth[node_id] <= current_depth:
            continue
        depth[node_id] = current_depth
        for target in adjacency.get(node_id, []):
            queue.append((target, current_depth + 1))
    return depth


def inspect_export(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []

    for required_key in ("chatConfig", "nodes", "edges"):
        if required_key not in data:
            issues.append(f"top-level JSON missing {required_key}")
    if "chatConfig" in data and not isinstance(data.get("chatConfig"), dict):
        issues.append("top-level chatConfig should be an object")
    if "nodes" in data and not isinstance(data.get("nodes"), list):
        issues.append("top-level nodes should be an array")
    if "edges" in data and not isinstance(data.get("edges"), list):
        issues.append("top-level edges should be an array")

    chat_config = as_dict(data.get("chatConfig"))
    if "_id" in chat_config:
        chat_config_id = chat_config.get("_id")
        if not (isinstance(chat_config_id, str) and OBJECT_ID_RE.fullmatch(chat_config_id)):
            issues.append("chatConfig._id should be a 24-character hexadecimal ObjectId string")
    nodes = [node for node in as_list(data.get("nodes")) if isinstance(node, dict)]
    edges = [edge for edge in as_list(data.get("edges")) if isinstance(edge, dict)]
    if "variables" in chat_config and not isinstance(chat_config.get("variables"), list):
        issues.append("chatConfig.variables should be an array")
    variables = [var for var in as_list(chat_config.get("variables")) if isinstance(var, dict)]

    node_by_id = {
        str(node.get("nodeId")): node for node in nodes if node.get("nodeId") is not None
    }
    var_key_by_label = {
        str(var.get("label")): str(var.get("key"))
        for var in variables
        if var.get("label") is not None and var.get("key") is not None
    }
    variable_keys = {str(var.get("key")) for var in variables if var.get("key") is not None}
    variable_value_types = {
        str(var.get("key")): str(var.get("valueType"))
        for var in variables
        if var.get("key") is not None and var.get("valueType") is not None
    }
    output_id_by_node_key, output_ids_by_node, output_value_types_by_node = output_maps(nodes)

    node_ids = [
        str(node.get("nodeId"))
        for node in nodes
        if node.get("nodeId") is not None
    ]
    for node_id, count in Counter(node_ids).items():
        if count > 1:
            issues.append(f"duplicate nodeId {node_id}")
    for node in nodes:
        if not node.get("nodeId"):
            issues.append(f"{node.get('name', '<unnamed node>')}: missing nodeId")
        if not node.get("flowNodeType"):
            issues.append(f"{node.get('name', node.get('nodeId', '<unnamed node>'))}: missing flowNodeType")

    for label, count in Counter(str(var.get("label")) for var in variables if var.get("label") is not None).items():
        if count > 1:
            issues.append(f"duplicate variable label {label}")
    for key, count in Counter(str(var.get("key")) for var in variables if var.get("key") is not None).items():
        if count > 1:
            issues.append(f"duplicate variable key {key}")

    depth = build_reachability(nodes, edges)
    catch_sources = {
        str(edge.get("source", ""))
        for edge in edges
        if str(edge.get("sourceHandle", "")).endswith("-source_catch-right")
    }
    outgoing_sources = Counter(str(edge.get("source", "")) for edge in edges)

    for node in nodes:
        node_id = str(node.get("nodeId", ""))
        node_type = str(node.get("flowNodeType", ""))
        if node_id and node_type not in TERMINAL_NODE_TYPES and outgoing_sources[node_id] == 0:
            issues.append(f"{node.get('name', node_id)}: non-terminal node has no outgoing edge")

    for index, edge in enumerate(edges, 1):
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        source_node = node_by_id.get(source)
        target_node = node_by_id.get(target)
        if not source_node:
            issues.append(f"edge #{index}: missing source node {source}")
        if not target_node:
            issues.append(f"edge #{index}: missing target node {target}")
        target_issue = target_handle_issue(edge, source_node, target_node)
        if target_issue:
            issues.append(f"edge #{index}: {target_issue}")
        if source_node:
            handle_issue = source_handle_issue(edge, source_node, output_ids_by_node)
            if handle_issue:
                issues.append(f"edge #{index} {node_name(node_by_id, source)} -> {node_name(node_by_id, target)}: {handle_issue}")
        if source_node and target_node:
            source_name = str(source_node.get("name", ""))
            target_name = str(target_node.get("name", ""))
            if (
                depth.get(source, -1) > depth.get(target, -1) >= 0
                and (UPSTREAM_TARGET_RE.search(target_name) or DOWNSTREAM_SOURCE_RE.search(source_name))
            ):
                issues.append(
                    f"edge #{index} {source_name} -> {target_name}: suspicious back edge to upstream/menu gate"
                )

    for node in nodes:
        node_id = str(node.get("nodeId", ""))
        for path, value in walk_json(node.get("inputs", []), "inputs"):
            if is_reference_field(path) and looks_like_reference_pair(value):
                owner, ref = value
                if owner == VARIABLE_NODE_ID:
                    if ref not in variable_keys and ref not in BUILTIN_VARIABLE_KEYS:
                        issues.append(f"{node.get('name')} {path}: unknown variable key {ref}")
                elif owner not in node_by_id:
                    issues.append(f"{node.get('name')} {path}: unknown referenced node {owner}")
                elif ref not in output_ids_by_node.get(owner, set()) and not (
                    owner == node_id and ref in node_input_keys(node)
                ) and not has_node_output(node_by_id[owner], owner, ref, output_ids_by_node):
                    issues.append(
                        f"{node.get('name')} {path}: unknown output {ref} on node {node_name(node_by_id, owner)}"
                    )
            if isinstance(value, str):
                for owner, ref in INTERPOLATION_RE.findall(value):
                    if owner == VARIABLE_NODE_ID:
                        if ref not in variable_keys and ref not in BUILTIN_VARIABLE_KEYS:
                            issues.append(f"{node.get('name')} {path}: unknown interpolated variable key {ref}")
                    elif owner not in node_by_id:
                        issues.append(f"{node.get('name')} {path}: unknown interpolated node {owner}")
                    elif ref not in output_ids_by_node.get(owner, set()) and not (
                        owner == node_id and ref in node_input_keys(node)
                    ) and not has_node_output(node_by_id[owner], owner, ref, output_ids_by_node):
                        issues.append(
                            f"{node.get('name')} {path}: unknown interpolated output {ref} on node {node_name(node_by_id, owner)}"
                        )

        node_type = str(node.get("flowNodeType", ""))
        if node_type.startswith("httpRequest"):
            method = get_input(node, "system_httpMethod")
            url = get_input(node, "system_httpReqUrl")
            headers = as_list(get_input(node, "system_httpHeader"))
            content_type = get_input(node, "system_httpContentType")
            json_body = get_input(node, "system_httpJsonBody")
            if not method:
                issues.append(f"{node.get('name')}: HTTP node missing method")
            if not str(url or "").strip():
                issues.append(f"{node.get('name')}: HTTP node missing URL")
            if not headers:
                issues.append(f"{node.get('name')}: HTTP node missing headers")
            if (
                str(method or "").upper() in {"POST", "PUT", "PATCH"}
                and content_type == "json"
                and not str(json_body or "").strip()
            ):
                issues.append(f"{node.get('name')}: HTTP JSON request missing json body")
            if node.get("catchError") is True and node_id not in catch_sources:
                issues.append(f"{node.get('name')}: catchError is true but no catch edge was found")
            for header in headers:
                if not isinstance(header, dict):
                    continue
                header_name = str(header.get("key") or header.get("name") or "").strip().lower()
                header_value = str(header.get("value") or "").strip()
                if (
                    header_name in SECRET_HEADER_KEYS
                    and header_value
                    and "REDACT" not in header_value.upper()
                    and not looks_like_template_value(header_value)
                ):
                    issues.append(f"{node.get('name')}: HTTP header {header_name} may contain an unredacted secret")

        if node_type == "datasetSearchNode" and not as_list(get_input(node, "datasets")):
            issues.append(f"{node.get('name')}: datasetSearchNode datasets value is empty")

        if node_type == "classifyQuestion" and not as_list(get_input(node, "agents")):
            issues.append(f"{node.get('name')}: classifyQuestion agents value is empty")

        if node_type == "contentExtract":
            extract_keys = [
                item
                for item in as_list(get_input(node, "extractKeys"))
                if isinstance(item, dict) and item.get("key") is not None
            ]
            output_keys = {
                str(output.get("key"))
                for output in as_list(node.get("outputs"))
                if isinstance(output, dict) and output.get("key") is not None
            }
            if not extract_keys:
                issues.append(f"{node.get('name')}: contentExtract extractKeys value is empty")
            for required_output in ("success", "fields"):
                if required_output not in output_keys:
                    issues.append(f"{node.get('name')}: contentExtract output missing {required_output}")
            for item in extract_keys:
                field_key = str(item["key"])
                if field_key not in output_keys:
                    issues.append(f"{node.get('name')}: contentExtract output missing field {field_key}")

        if node_type == "cfr":
            if not get_input(node, "userChatInput"):
                issues.append(f"{node.get('name')}: cfr node missing userChatInput")
            if "system_text" not in output_ids_by_node.get(node_id, set()):
                issues.append(f"{node.get('name')}: cfr output missing system_text")

        if node_type == "datasetConcatNode":
            quote_input_count = 0
            for item in as_list(node.get("inputs")):
                if isinstance(item, dict) and item.get("valueType") == "datasetQuote":
                    quote_input_count += 1
            if quote_input_count == 0:
                issues.append(f"{node.get('name')}: datasetConcatNode has no datasetQuote inputs")
            if "quoteQA" not in output_ids_by_node.get(node_id, set()):
                issues.append(f"{node.get('name')}: datasetConcatNode output missing quoteQA")

        if node_type == "readFiles":
            if not get_input(node, "fileUrlList"):
                issues.append(f"{node.get('name')}: readFiles node missing fileUrlList")
            for required_output in ("system_text", "system_rawResponse"):
                if required_output not in output_ids_by_node.get(node_id, set()):
                    issues.append(f"{node.get('name')}: readFiles output missing {required_output}")

        if node_type == "code":
            code_text = str(get_input(node, "code") or "")
            if not code_text.strip():
                issues.append(f"{node.get('name')}: code node missing code")
            code_params = js_main_destructured_params(code_text)
            input_keys = code_custom_input_keys(node)
            if code_params is not None:
                missing_inputs = sorted(code_params - input_keys)
                unused_inputs = sorted(input_keys - code_params)
                if missing_inputs:
                    issues.append(f"{node.get('name')}: code main() params not declared as inputs: {', '.join(missing_inputs)}")
                if unused_inputs:
                    issues.append(f"{node.get('name')}: code inputs not accepted by main(): {', '.join(unused_inputs)}")
            dynamic_outputs = [
                output
                for output in as_list(node.get("outputs"))
                if isinstance(output, dict) and output.get("type") == "dynamic" and output.get("key") != "system_addOutputParam"
            ]
            if not dynamic_outputs:
                issues.append(f"{node.get('name')}: code node has no custom dynamic outputs")

        if node_type == "textEditor":
            text_value = str(get_input(node, "system_textareaInput") or "")
            if TEXT_EDITOR_DIRECT_INTERPOLATION_RE.search(text_value):
                issues.append(
                    f"{node.get('name')}: textEditor uses direct {{$node.output$}} interpolation; current UI-created textEditor nodes should bind dynamic inputs and use local {{field}} placeholders"
                )

        if node_type in {"loop", "parallelRun"}:
            loop_input = get_input(node, "loopInputArray")
            if not loop_input:
                issues.append(f"{node.get('name')}: {node_type} missing loopInputArray")
            else:
                ref_pair = first_reference_pair(loop_input)
                ref_value_type = None
                if ref_pair:
                    owner, ref = ref_pair
                    if owner == VARIABLE_NODE_ID:
                        ref_value_type = variable_value_types.get(ref) or (
                            "string" if ref in BUILTIN_VARIABLE_KEYS else None
                        )
                    elif owner in node_by_id:
                        ref_value_type = output_value_types_by_node.get(owner, {}).get(
                            ref
                        ) or builtin_node_output_value_type(node_by_id[owner], ref)
                if ref_value_type and not (
                    ref_value_type.startswith("array")
                    or ref_value_type in {"any", "arrayAny", "dynamic"}
                ):
                    issues.append(f"{node.get('name')}: {node_type} loopInputArray references non-array valueType {ref_value_type}")
            children = [str(item) for item in as_list(get_input(node, "childrenNodeIdList"))]
            if not children:
                issues.append(f"{node.get('name')}: {node_type} childrenNodeIdList is empty")
            else:
                child_types = {str(node_by_id.get(child_id, {}).get("flowNodeType", "")) for child_id in children}
                if "loopStart" not in child_types:
                    issues.append(f"{node.get('name')}: {node_type} childrenNodeIdList missing loopStart")
                if "loopEnd" not in child_types:
                    issues.append(f"{node.get('name')}: {node_type} childrenNodeIdList missing loopEnd")
            if node_type == "parallelRun":
                for key in ("parallelRunMaxConcurrency", "parallelRunMaxRetryTimes"):
                    if get_input(node, key) is None:
                        issues.append(f"{node.get('name')}: parallelRun missing {key}")

        if node_type == "loopStart":
            for required_output in ("loopStartIndex", "loopStartInput"):
                if required_output not in output_ids_by_node.get(node_id, set()):
                    issues.append(f"{node.get('name')}: loopStart output missing {required_output}")

        if node_type == "loopEnd" and get_input(node, "loopEndInput") is None:
            issues.append(f"{node.get('name')}: loopEnd missing loopEndInput")

        if node_type == "customFeedback" and not str(get_input(node, "system_textareaInput") or "").strip():
            issues.append(f"{node.get('name')}: customFeedback missing feedback text")

        if node_type == "chatNode":
            for key in sorted(CHAT_OPTIONAL_OMIT_VALUE_KEYS):
                item = input_item(node, key)
                if item is not None and "value" in item and item.get("value") is None:
                    issues.append(
                        f"{node.get('name')}: chatNode optional input {key} has value null; current UI exports omit the value field instead of serializing null"
                    )
            max_token = get_input(node, "maxToken")
            if isinstance(max_token, (int, float)) and max_token > 2048:
                issues.append(
                    f"{node.get('name')}: chatNode maxToken={max_token} may exceed the model/UI response limit; current qipaoxian policy is to leave this setting disabled/unset"
                )

    return {
        "top_level_keys": list(data.keys()),
        "chat_config_keys": list(chat_config.keys()),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_type_counts": dict(Counter(str(node.get("flowNodeType", "")) for node in nodes)),
        "variables": variables,
        "nodes": nodes,
        "edges": edges,
        "node_by_id": node_by_id,
        "var_key_by_label": var_key_by_label,
        "output_id_by_node_key": output_id_by_node_key,
        "issues": issues,
    }


def render_markdown(summary: dict[str, Any], max_edges: int) -> str:
    nodes = summary["nodes"]
    edges = summary["edges"]
    node_by_id = summary["node_by_id"]

    lines = [
        "# FastGPT Canvas Inspection",
        "",
        "## Summary",
        "",
        f"- Top-level keys: {', '.join(summary['top_level_keys'])}",
        f"- chatConfig keys: {', '.join(summary['chat_config_keys'])}",
        f"- Nodes: {summary['node_count']}",
        f"- Edges: {summary['edge_count']}",
        f"- Issues: {len(summary['issues'])}",
        "",
        "## Node Type Counts",
        "",
        md_table(
            ["flowNodeType", "count"],
            [[key, count] for key, count in sorted(summary["node_type_counts"].items())],
        ),
        "",
        "## Variables",
        "",
        md_table(
            ["label", "key", "valueType", "type", "required"],
            [
                [
                    var.get("label", ""),
                    var.get("key", ""),
                    var.get("valueType", ""),
                    var.get("type", ""),
                    var.get("required", ""),
                ]
                for var in summary["variables"]
            ],
        ),
        "",
        "## Nodes",
        "",
        md_table(
            ["nodeId", "name", "flowNodeType", "inputs", "outputs", "catchError"],
            [
                [
                    node.get("nodeId", ""),
                    node.get("name", ""),
                    node.get("flowNodeType", ""),
                    len(as_list(node.get("inputs"))),
                    len(as_list(node.get("outputs"))),
                    node.get("catchError", ""),
                ]
                for node in nodes
            ],
        ),
        "",
        "## Edges",
        "",
    ]

    edge_rows = []
    for index, edge in enumerate(edges[:max_edges], 1):
        edge_rows.append(
            [
                index,
                node_name(node_by_id, edge.get("source")),
                edge.get("sourceHandle", ""),
                node_name(node_by_id, edge.get("target")),
                edge.get("targetHandle", ""),
            ]
        )
    lines.append(md_table(["#", "source", "sourceHandle", "target", "targetHandle"], edge_rows))
    if len(edges) > max_edges:
        lines.append("")
        lines.append(f"_Only showing first {max_edges} of {len(edges)} edges._")

    lines.extend(["", "## Indexes", ""])
    lines.append(f"- node_by_id: {len(summary['node_by_id'])} entries")
    lines.append(f"- var_key_by_label: {len(summary['var_key_by_label'])} entries")
    lines.append(f"- output_id_by_node_key: {len(summary['output_id_by_node_key'])} entries")

    lines.extend(["", "## Issues", ""])
    if summary["issues"]:
        lines.extend(f"- {issue}" for issue in summary["issues"])
    else:
        lines.append("- No issues detected.")
    return "\n".join(lines) + "\n"


def render_json(summary: dict[str, Any]) -> str:
    payload = {
        "top_level_keys": summary["top_level_keys"],
        "chat_config_keys": summary["chat_config_keys"],
        "node_count": summary["node_count"],
        "edge_count": summary["edge_count"],
        "node_type_counts": summary["node_type_counts"],
        "var_key_by_label": summary["var_key_by_label"],
        "output_id_by_node_key": summary["output_id_by_node_key"],
        "issues": summary["issues"],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a FastGPT exported JSON canvas.")
    parser.add_argument("path", help="Path to a FastGPT exported JSON file")
    parser.add_argument("--max-edges", type=int, default=80, help="Maximum edges to show in Markdown output")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable JSON summary")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        data = load_export(Path(args.path))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: failed to read valid JSON: {exc}", file=sys.stderr)
        return 2

    summary = inspect_export(data)
    if args.json:
        print(render_json(summary), end="")
    else:
        print(render_markdown(summary, max(args.max_edges, 0)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
