# Node Coverage Matrix

This matrix describes what this skill can author from documented patterns, what
it can statically inspect, and where a same-version seed export is still
required.

The coverage comes from observed same-version demo exports plus FastGPT public
workflow-node documentation. It is still not an official schema. Prefer cloning
target-environment exports when generating production JSON.

## Coverage Levels

| Level | Meaning |
| --- | --- |
| Documented | `node-templates.md` describes observed inputs, outputs, handles, and authoring guidance. |
| Inspector-aware | `fastgpt_canvas_inspect.py` has node-specific validation rules. |
| Seed-required | The node can be discussed, but production authoring should clone a same-version export before generating JSON. |

## Current Coverage

| UI Node | Observed `flowNodeType` | Status | Notes |
| --- | --- | --- | --- |
| System config | `userGuide` | Documented by example | Usually app metadata; not a normal workflow step. |
| Workflow start | `workflowStart` | Documented, inspector-aware | Built-in outputs include `userChatInput`; `userFiles` may be referenced even when omitted from exported outputs. |
| User select | `userSelect` | Documented, inspector-aware | Option keys control branch handles. |
| Form input | `formInput` | Documented | Field keys become output IDs in observed exports. |
| IF/ELSE | `ifElseNode` | Documented, inspector-aware | Supports `source-IF`, `source-ELSE IF N`, and `source-ELSE`. |
| HTTP request | `httpRequest468` | Documented, inspector-aware | Modern exports may only have `httpRawResponse` and `error` until custom outputs are added; do not require `success/code` universally. |
| Variable update | `variableUpdate` | Documented | Use for durable workflow state. |
| Dataset search | `datasetSearchNode` | Documented, inspector-aware | Empty `datasets` is an import action unless intentionally bound. |
| Text editor | `textEditor` | Documented, inspector-aware | Outputs `system_text`. Current exports may require dynamic inputs plus local `{{field}}` placeholders; inspector warns on direct `{{$node.output$}}` interpolation in the textarea. |
| AI chat | `chatNode` | Documented, inspector-aware | Common outputs: `history`, `answerText`, `reasoningText`, `system_error_text`. Inspector warns on optional AI-chat inputs serialized as `value: null` where current UI exports omit `value`. |
| Answer | `answerNode` | Documented | Usually terminal in practice. |
| Question classification | `classifyQuestion` | Documented, inspector-aware | `agents[].key` controls `source-<key>` branch handles. |
| Content extraction | `contentExtract` | Documented, inspector-aware | `extractKeys[].key` creates field-specific outputs with generated IDs. |
| Question optimization | `cfr` | Documented, inspector-aware | Outputs `system_text` for retrieval query enhancement. |
| Dataset quote merge | `datasetConcatNode` | Documented, inspector-aware | Merges multiple `datasetQuote` inputs into one `quoteQA`. |
| Document parsing | `readFiles` | Documented, inspector-aware | Reads `workflowStart.userFiles`; outputs parsed text and raw response. |
| Code run | `code` | Inspector-aware, runtime seed-required for executable syntax | Custom outputs map return-object keys to generated IDs. Inspector checks empty code, missing custom outputs, dangling non-terminal Code nodes, `source_catch-right` catch edges when `catchError=true`, and `function main({...})` input/parameter mismatches; the code-body wrapper/return convention must still be cloned from a same-version node that preview-ran successfully. |
| Batch run | `loop` | Documented, inspector-aware | Parent uses `childrenNodeIdList`; child flow is `loopStart -> ... -> loopEnd`. |
| Parallel run | `parallelRun` | Documented, inspector-aware | Uses the same child-flow shape as batch run plus concurrency/retry settings. |
| Loop start | `loopStart` | Documented, inspector-aware | Inner node; outputs current item and index. |
| Loop end | `loopEnd` | Documented, inspector-aware | Inner node; returns one item result to parent aggregate. |
| Tool calling | `tools` | Documented, inspector-aware | Tool edges use `selectedTools` source and target handles. |
| Tool | `tool` | Documented | Observed built-in Bocha search tool; exact inputs depend on selected tool. |
| Tool set | `toolSet` | Partially documented | Observed as a connected tool container with `system_error_text`. |
| Tool params | `toolParams` | Documented | Inputs are mirrored as outputs for LLM-filled tool parameters. |
| Stop tool | `stopTool` | Documented | Ends a tool call path. |
| Plugin module | `pluginModule` | Partially documented | Minimal observed export only; real plugin/app bindings remain seed-required. |
| Custom feedback | `customFeedback` | Documented, inspector-aware | Telemetry marker; no outputs in observed export. |

## Still Seed-Required

These nodes or node families need more same-version exports before the skill can
claim reliable production authoring coverage:

- Fully parameterized `pluginModule` calls, including dynamic plugin inputs and
  outputs.
- Code node executable syntax and return wrapper conventions, unless a
  same-version Code node export has already preview-run successfully in the
  target FastGPT environment.
- Plugin app internals such as `pluginInput`, `pluginOutput`, and any
  `appModule` variant if they appear in the target environment.
- `lafModule`, because the current demo set did not include a Laf function call.
- `app` or `runApp` style app-calling nodes if the target FastGPT version exposes
  them separately from `pluginModule`.
- `agent`, if the UI exposes a first-class agent node separate from `tools`.
- Tool nodes beyond the observed built-in Bocha search and tool-set examples.

## Authoring Implications

- Use the documented nodes directly for draft generation, but still preserve
  same-version seed shapes where available.
- For partial or seed-required nodes, clone the target export first and only
  change labels, references, and business values.
- Keep the inspector warnings as static-risk signals, not runtime proof.
- Promote a node from seed-required to documented only after a demo export shows
  its inputs, outputs, and edge handles clearly.
