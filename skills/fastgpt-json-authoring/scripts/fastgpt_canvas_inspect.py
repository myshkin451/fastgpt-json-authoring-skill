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
BUILTIN_VARIABLE_KEYS = {"system_entryPoint"}
SECRET_HEADER_KEYS = {"authorization", "x-agent-token", "x-api-key", "api-key"}
INTERPOLATION_RE = re.compile(r"\{\{\$([^.{}$]+)\.([^{}$]+)\$\}\}")
UPSTREAM_TARGET_RE = re.compile(r"(G00|M00|menu|gate|entry|入口|菜单|确认门)", re.IGNORECASE)
DOWNSTREAM_SOURCE_RE = re.compile(r"(N00|A12|next|follow|switch|下一步|追问)", re.IGNORECASE)


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


def output_maps(nodes: list[dict[str, Any]]) -> tuple[dict[str, dict[str, str]], dict[str, set[str]]]:
    by_key: dict[str, dict[str, str]] = {}
    ids: dict[str, set[str]] = {}
    for node in nodes:
        node_id = str(node.get("nodeId", ""))
        by_key[node_id] = {}
        ids[node_id] = set()
        for output in as_list(node.get("outputs")):
            if not isinstance(output, dict):
                continue
            output_id = output.get("id")
            output_key = output.get("key")
            if output_id is not None:
                ids[node_id].add(str(output_id))
            if output_key is not None and output_id is not None:
                by_key[node_id][str(output_key)] = str(output_id)
    return by_key, ids


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


def is_reference_field(path: str) -> bool:
    return ".value" in path or ".variable" in path


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
        if handle not in {f"{source}-source-IF", f"{source}-source-ELSE"}:
            return "ifElseNode sourceHandle should end with source-IF or source-ELSE"
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

    if node_type.startswith("httpRequest"):
        catch_handle = f"{source}-source_catch-right"
        if handle == catch_handle:
            return None
        if handle != expected_right:
            return "HTTP sourceHandle should be source-right or source_catch-right"
        return None

    if handle != expected_right:
        output_suffix = handle.removeprefix(f"{source}-source-")
        if output_suffix in valid_output_ids.get(source, set()):
            return None
        return "ordinary node sourceHandle should use source-right"
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
    output_id_by_node_key, output_ids_by_node = output_maps(nodes)

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

    for index, edge in enumerate(edges, 1):
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        source_node = node_by_id.get(source)
        target_node = node_by_id.get(target)
        if not source_node:
            issues.append(f"edge #{index}: missing source node {source}")
        if not target_node:
            issues.append(f"edge #{index}: missing target node {target}")
        if target and edge.get("targetHandle") != f"{target}-target-left":
            issues.append(f"edge #{index}: targetHandle should be {target}-target-left")
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
                elif ref not in output_ids_by_node.get(owner, set()):
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
                    elif ref not in output_ids_by_node.get(owner, set()):
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
            output_keys = {
                str(output.get("key"))
                for output in as_list(node.get("outputs"))
                if isinstance(output, dict) and output.get("key") is not None
            }
            if not method:
                issues.append(f"{node.get('name')}: HTTP node missing method")
            if not str(url or "").strip():
                issues.append(f"{node.get('name')}: HTTP node missing URL")
            if not headers:
                issues.append(f"{node.get('name')}: HTTP node missing headers")
            if str(method or "").upper() in {"POST", "PUT", "PATCH"} and content_type == "json" and not str(json_body or "").strip():
                issues.append(f"{node.get('name')}: HTTP JSON request missing json body")
            for required_output in ("success", "code"):
                if required_output not in output_keys:
                    issues.append(f"{node.get('name')}: HTTP output missing {required_output}")
            if node.get("catchError") is True and node_id not in catch_sources:
                issues.append(f"{node.get('name')}: catchError is true but no catch edge was found")
            for header in headers:
                if not isinstance(header, dict):
                    continue
                header_name = str(header.get("key") or header.get("name") or "").strip().lower()
                header_value = str(header.get("value") or "").strip()
                if header_name in SECRET_HEADER_KEYS and header_value and "REDACT" not in header_value.upper():
                    issues.append(f"{node.get('name')}: HTTP header {header_name} may contain an unredacted secret")

        if node_type == "datasetSearchNode" and not as_list(get_input(node, "datasets")):
            issues.append(f"{node.get('name')}: datasetSearchNode datasets value is empty")

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
