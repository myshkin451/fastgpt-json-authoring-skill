---
name: fastgpt-json-authoring
description: Author, inspect, repair, and validate FastGPT exported application JSON for importable canvas workflows. Use when Codex needs to generate a new FastGPT app JSON, convert a workflow spec into FastGPT nodes and edges, analyze or refactor an exported FastGPT JSON file, diagnose broken canvas wiring, validate node handles and variable references, or document FastGPT JSON structure.
---

# FastGPT JSON Authoring

Use this skill to treat a FastGPT app export as a reviewable graph program instead of a hand-drawn canvas. The goal is to produce JSON that is likely to import cleanly, then validate it with deterministic checks before the user opens FastGPT.

## Quick Start

1. If the user provides an existing export, inspect it first:

```bash
python3 skills/fastgpt-json-authoring/scripts/fastgpt_canvas_inspect.py app.json
```

2. If authoring a new app, ask for or create a same-version seed export that contains the needed node types. FastGPT JSON is version-sensitive; use the seed to copy exact node shapes.

3. Draft the workflow as a graph before editing JSON:

```text
S00 -> S01
S01.IF -> L02 -> L03 -> L04
S01.ELSE -> P00
```

4. Generate in this order: variables, nodes, outputs, input references, then edges.

5. Run the inspector again. Do not hand off a generated JSON with unresolved references, missing handles, incomplete HTTP nodes, or suspicious menu back-edges unless the risk is intentionally documented.

## What To Load

- Read `references/json-schema.md` when creating or modifying JSON structure, variables, references, interpolation, edges, or node IDs.
- Read `references/node-templates.md` when constructing specific node types such as HTTP, user select, form input, AI chat, dataset search, text editor, or variable update nodes.
- Read `references/authoring-workflow.md` when planning a full app, recovering from a broken canvas, designing import validation, or deciding how to handle platform quirks.
- Run `scripts/fastgpt_canvas_inspect.py` on every provided or generated export.

## Authoring Rules

- Preserve exact node shapes from a current FastGPT export whenever possible. Generate IDs and labels, but do not invent unknown schema fields when a seed node can be cloned.
- Keep three indexes while editing: `node name -> nodeId`, `variable label -> variable key`, and `node output key -> output id`.
- Use variable keys, not visible labels, inside JSON references. Visible labels like `login_name` are for humans; references use generated keys under `chatConfig.variables`.
- Use output IDs, not output keys, in references and interpolations. HTTP output key `success` is not enough; later nodes usually reference that output's `id`.
- Treat `chatConfig.entryPoints` as platform UI state, not as a reliable workflow trigger during paused user interactions. Prefer explicit user-select menus inside the workflow when deterministic continuation matters.
- Avoid long chains that reconnect downstream nodes back to upstream login, menu, or form gates. If a platform import or runtime behaves oddly around loops, duplicate the required gate or route through a fresh top-level pass.
- Never store secrets in committed exports or docs. Redact API tokens and Authorization-like headers before publishing examples.
- For knowledge-base nodes, expect dataset bindings to be environment-specific. If dataset IDs are unknown, leave a clear TODO and require manual selection after import.

## Validation Checklist

Before final handoff, verify:

- JSON parses with UTF-8 or UTF-8 BOM.
- Top level has `chatConfig`, `nodes`, and `edges`.
- All edge source and target node IDs exist.
- Every `targetHandle` is `<targetNodeId>-target-left`.
- Ordinary nodes use `<sourceNodeId>-source-right`.
- `ifElseNode` uses `source-IF` or `source-ELSE`.
- `userSelect` edges use option keys from `userSelectOptions`.
- HTTP catch edges use `<nodeId>-source_catch-right`.
- Reference pairs like `["VARIABLE_NODE_ID", "<varKey>"]` and `["<nodeId>", "<outputId>"]` resolve.
- Interpolations like `{{$VARIABLE_NODE_ID.<varKey>$}}` and `{{$<nodeId>.<outputId>$}}` resolve.
- HTTP nodes have method, URL, headers, JSON body when required, output fields, and planned error handling.
- Dataset search nodes have selected datasets or an explicit post-import action.
- Generated examples contain no real credentials, customer data, private URLs, or project-only business content.
