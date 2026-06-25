---
name: fastgpt-json-authoring
description: Author, inspect, repair, and validate production-grade FastGPT exported application JSON for importable canvas workflows. Use when an AI coding agent needs to generate a new FastGPT app JSON, convert a workflow spec into nodes and edges, analyze or refactor an exported FastGPT JSON file, diagnose broken canvas wiring, validate node handles and variable references, or document FastGPT JSON structure.
---

# FastGPT JSON Authoring

Use this skill to treat a FastGPT app export as a reviewable graph program instead of a hand-drawn canvas. The goal is to produce JSON that is likely to import cleanly, then validate it with deterministic checks before the user opens FastGPT.

中文定位：这是一个面向生产环境的 FastGPT / AIBuilder JSON authoring skill。
它优先使用目标环境的同版本导出样本来校准节点形状，适合生成、检查、
修复和重构可导入的复杂 FastGPT 工作流 JSON。

This skill is platform-neutral: it can guide any skill-capable coding agent. The
implementation currently ships a Python inspector and reference docs, but the
authoring rules are not tied to one agent platform.

Production standard:

- Prefer same-version FastGPT seed exports over remembered schemas.
- Treat JSON parsing as the lowest bar, not proof of readiness.
- Distinguish static validation, import validation, and runtime preview
  validation.
- Never let LLM reasoning replace backend/API authority for permissions, ACLs,
  identity, or durable business state.
- Keep internal LLM planner/extractor nodes silent to the user. In FastGPT
  exports this usually means `isResponseAnswerText=false`; only final answer
  nodes should stream directly.

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

6. For production apps, import into a FastGPT copy and preview success, denial,
   API-error, and menu/re-entry paths before calling the app runtime-validated.

## What To Load

- Read `references/industrial-authoring.md` when positioning an app as
  production/industrial-grade, designing release gates, or deciding what can be
  claimed after static validation.
- Read `references/json-schema.md` when creating or modifying JSON structure, variables, references, interpolation, edges, or node IDs.
- Read `references/node-templates.md` when constructing specific node types such as HTTP, user select, form input, AI chat, dataset search, text editor, or variable update nodes.
- Read `references/node-coverage.md` when deciding whether a node type is
  documented, inspector-aware, or still seed-required.
- Read `references/authoring-workflow.md` when planning a full app, recovering from a broken canvas, designing import validation, or deciding how to handle platform quirks.
- Read `references/template-first-vs-export-calibrated.md` when comparing this
  skill with template-first generators or deciding whether official/default
  templates can override real same-version exports.
- Run `scripts/fastgpt_canvas_inspect.py` on every provided or generated export.

## Authoring Rules

- Preserve exact node shapes from a current FastGPT export whenever possible. Generate IDs and labels, but do not invent unknown schema fields when a seed node can be cloned.
- Preserve field absence vs explicit `null`. Current FastGPT UI exports may omit `value` for optional AI-chat inputs; serializing those same fields as `null` can break newer editors or runtimes.
- For current UI-created `textEditor` nodes, bind upstream values as dynamic inputs and use local `{{field}}` placeholders in the textarea. Do not migrate structured form assembly by pasting direct `{{$node.output$}}` interpolation into the text area unless the target export proves that shape.
- Treat Code node executable syntax as runtime-version-specific. Before generating production JSON with `flowNodeType: "code"`, obtain a same-version export of a Code node that has actually preview-run successfully, or avoid the Code node and move the deterministic calculation behind an HTTP helper endpoint.
- Keep three indexes while editing: `node name -> nodeId`, `variable label -> variable key`, and `node output key -> output id`.
- Use variable keys, not visible labels, inside JSON references. Visible labels like `login_name` are for humans; references use generated keys under `chatConfig.variables`.
- Use output IDs, not output keys, in references and interpolations. HTTP output key `success` is not enough; later nodes usually reference that output's `id`.
- Treat `chatConfig.entryPoints` as platform UI state, not as a reliable workflow trigger during paused user interactions. Prefer explicit user-select menus inside the workflow when deterministic continuation matters.
- Avoid long chains that reconnect downstream nodes back to upstream login, menu, or form gates. If a platform import or runtime behaves oddly around loops, duplicate the required gate or route through a fresh top-level pass.
- For HTTP nodes, distinguish FastGPT global-variable interpolation
  `{{$VARIABLE_NODE_ID.<varKey>$}}` from HTTP-local request-body placeholders
  such as `{{scenario_key}}`.
- For environment-specific resources such as datasets, models, base URLs, and
  tokens, generate a clear import action instead of pretending the binding is
  portable.
- Never store secrets in committed exports or docs. Redact API tokens and Authorization-like headers before publishing examples.
- For knowledge-base nodes, expect dataset bindings to be environment-specific. If dataset IDs are unknown, leave a clear TODO and require manual selection after import.

## Readiness Labels

Use precise language:

- `static-validated`: inspector passed or only documented expected warnings remain.
- `import-validated`: FastGPT imported the JSON and the canvas opened.
- `runtime-validated`: FastGPT preview exercised the required business paths.

Do not call a generated app production-ready if only static validation has run.

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
- Code or other current-version catch edges may also use `<nodeId>-source_catch-right` when the same-version seed has `catchError=true`; preserve the seed policy.
- `classifyQuestion` edges use category keys from `agents`.
- `tools` selected-tool edges use `selectedTools` as both source and target handle.
- Reference pairs like `["VARIABLE_NODE_ID", "<varKey>"]` and `["<nodeId>", "<outputId>"]` resolve.
- Interpolations like `{{$VARIABLE_NODE_ID.<varKey>$}}` and `{{$<nodeId>.<outputId>$}}` resolve.
- HTTP nodes have method, URL, headers, JSON body when required, output fields, and planned error handling.
- Dataset search nodes have selected datasets or an explicit post-import action.
- Current `textEditor` nodes use dynamic inputs and local `{{field}}` placeholders when assembling structured form/context text.
- AI-chat optional inputs copied from the seed preserve omitted `value` fields instead of serializing them as `null`.
- Loop and parallel nodes have array inputs and a child workflow containing
  `loopStart` and `loopEnd`.
- Content extraction nodes have outputs for every `extractKeys` field.
- Generated examples contain no real credentials, customer data, private URLs, or project-only business content.
