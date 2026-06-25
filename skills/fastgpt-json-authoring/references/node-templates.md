# Node Templates

Use these patterns as authoring guidance. Prefer cloning exact `inputs` and `outputs` from a same-version FastGPT seed export, then changing values and references.

## Contents

- Workflow start
- IF/ELSE
- User select
- Form input
- Variable update
- HTTP request
- Question classification
- Content extraction
- Dataset search
- Question optimization
- Dataset quote merge
- Document parsing
- Text editor
- Code
- Batch and parallel run
- AI chat
- Tool calling
- Plugin module
- Custom feedback
- Answer node

## Workflow Start

Purpose: entry node for every execution.

Expected source handle:

```text
<nodeId>-source-right
```

Typical output key:

```text
userChatInput
```

Use the flow-start user question when natural language should drive retrieval or routing.

## IF/ELSE

Purpose: deterministic branching. Use for permission checks, API success checks, login state, and structured data presence.

Expected source handles:

```text
<nodeId>-source-IF
<nodeId>-source-ELSE IF 1
<nodeId>-source-ELSE IF 2
<nodeId>-source-ELSE
```

Authoring guidance:

- Keep conditions deterministic.
- Do not ask the LLM to decide permission or access scope.
- Use backend API outputs or stable variables for authorization checks.
- Same-version exports may serialize "else if" branches as
  `<nodeId>-source-ELSE IF N`. Preserve those handles when cloning an existing
  multi-branch judgment node.
- Observed include operators are `include` and `notInclude`. Do not assume a
  human UI label such as "contains" is the JSON operator name.

## User Select

Purpose: pause workflow and resume from a selected option.

The option key controls the source handle:

```json
{
  "key": "visit_briefing",
  "label": "Visit briefing"
}
```

Edge:

```json
{
  "source": "G00",
  "target": "A01",
  "sourceHandle": "G00-source-visit_briefing",
  "targetHandle": "A01-target-left"
}
```

Use explicit user-select menus instead of bottom entry cards when the user must make a workflow-continuing choice.

## Form Input

Purpose: collect structured input such as account/password, customer keyword, transcript text, or roleplay topic.

Authoring guidance:

- Use form input when structured fields matter.
- Keep labels short and concrete.
- Do not save passwords to global variables.
- Add a variable-update node after the form if downstream nodes need a stable internal variable.
- Text-like fields use the field `key` as the downstream output id.
- A single-select field uses `type: "select"`, `valueType: "string"`, and a
  `list` of `{ "label": "...", "value": "..." }` entries.
- A multi-select field uses `type: "multipleSelect"` and usually
  `valueType: "arrayString"`.
- A file picker field uses `type: "fileSelect"` and can declare
  `canLocalUpload`, `canSelectFile`, `canSelectImg`, `canSelectVideo`,
  `canSelectAudio`, and `maxFiles`.
- Reference-backed select options can use `listInputType: "reference"` with a
  `listReference` array. Some exported built-ins such as `userId`, `appId`, and
  `cTime` may not appear in `chatConfig.variables`.

Observed single-select shape:

```json
{
  "type": "select",
  "key": "陪练场景",
  "label": "陪练场景",
  "valueType": "string",
  "required": true,
  "defaultValue": "",
  "list": [
    {"label": "budget_objection", "value": "budget_objection"},
    {"label": "poc_risk", "value": "poc_risk"}
  ],
  "listInputType": "custom"
}
```

The corresponding output uses the field name as the output id:

```json
{"id": "陪练场景", "key": "陪练场景", "label": "陪练场景", "valueType": "string", "type": "static"}
```

## Variable Update

Purpose: write node outputs or constants into global variables.

Typical use:

```text
login_name = Login API > data.login_name
last_branch = "visit_briefing"
customer_id = Customer Search HTTP > data.customer.id
```

Authoring guidance:

- Write constants as literal strings when the node supports literal values.
- Write references as `["VARIABLE_NODE_ID", "<varKey>"]` or `["<nodeId>", "<outputId>"]`.
- Prefer explicit state variables for business memory. Do not rely on AI chat history as durable workflow state.

## HTTP Request

Common `flowNodeType` in observed exports:

```text
httpRequest468
```

Minimum completeness checklist:

- Method, for example `GET` or `POST`.
- Full URL.
- Headers, including `Content-Type` when JSON is sent.
- Body for `POST`, `PUT`, or `PATCH`.
- Output fields such as `success`, `code`, `message`, and specific `data.*` values.
- Error capture strategy.

Secret rule: configure real tokens in the FastGPT UI or deployment environment, not in public JSON examples.

Query parameter rule: if the current FastGPT version shows query parameters in
the HTTP node's Params table, write the raw logical value there and let the
platform perform URL encoding. Do not pre-encode Chinese or other non-ASCII
values in Params. For example, qipaoxian `GetRights` should use URL
`/API/UserNew/GetRights` with Params `category=日报`, not Params
`category=%E6%97%A5%E6%8A%A5`. Some editors auto-migrate URL query strings into
Params, so re-check the post-import preview details.

Observed header variable interpolation:

```json
{
  "key": "X-Agent-Token",
  "type": "string",
  "value": "{{$VARIABLE_NODE_ID.agentTokenKey$}}"
}
```

Observed JSON body interpolation uses HTTP-local custom input names:

```json
"system_httpJsonBody": "{\n  \"scenario_key\": \"{{scenario_key}}\"\n}"
```

Observed HTTP dynamic outputs:

```json
{"id": "gZ6JqQ", "type": "dynamic", "key": "success", "label": "success", "valueType": "any"}
{"id": "x6trJY", "type": "dynamic", "key": "code", "label": "code", "valueType": "any"}
{"id": "nvE6AV", "type": "dynamic", "key": "message", "label": "message", "valueType": "any"}
{"id": "h74qzh", "type": "dynamic", "key": "data.file_id", "label": "data.file_id", "valueType": "any"}
```

If `catchError` is true, connect `<nodeId>-source_catch-right` to an error answer
or recovery branch. A sample can export catch enabled without an actual catch
edge, but generated production apps should not rely on that.

File form outputs can be referenced by HTTP custom inputs as `arrayString`.

Observed form-data body shape:

```json
{
  "key": "system_httpContentType",
  "valueType": "string",
  "value": "form-data"
}
```

```json
{
  "key": "system_httpFormBody",
  "valueType": "any",
  "value": [
    {
      "key": "record",
      "type": "string",
      "value": "{{$HTTP_NODE_ID.测试文件$}}"
    },
    {
      "key": "purpose",
      "type": "string",
      "value": "{{$HTTP_NODE_ID.purpose$}}"
    }
  ]
}
```

In this shape, the interpolation owner is the HTTP node itself and the referenced
name is one of that HTTP node's custom input keys, not an HTTP output id.

Typical branch pattern:

```text
HTTP -> Judge success -> Save variables -> Business branch
HTTP.catch -> Friendly error answer
```

If `catchError=true`, add a catch edge unless the runtime intentionally swallows errors.

## Question Classification

Purpose: route natural-language requests into deterministic branches.

Observed `flowNodeType`:

```text
classifyQuestion
```

Key inputs:

- `model`
- `systemPrompt`
- `history`
- `userChatInput`
- `agents`

The `agents` input is a list of category labels and stable keys:

```json
[
  {"value": "售前咨询", "key": "wqre"},
  {"value": "售后故障", "key": "sdfa"},
  {"value": "其他问题", "key": "agex"}
]
```

Each category key controls an outgoing branch handle:

```text
<nodeId>-source-wqre
<nodeId>-source-sdfa
<nodeId>-source-agex
```

The standard output is:

```json
{"id": "cqResult", "key": "cqResult", "label": "分类结果", "valueType": "string", "type": "static"}
```

Authoring guidance:

- Use classification for routing, not for permissions or identity decisions.
- Keep category keys stable and ASCII when possible; downstream edges depend on
  these keys.
- If exact branch reliability matters, add a fallback category such as `other`.

## Content Extraction

Purpose: extract structured fields from text before HTTP calls, branching, or
AI generation.

Observed `flowNodeType`:

```text
contentExtract
```

Key inputs:

- `model`
- `description`
- `history`
- `content`
- `extractKeys`

Observed `extractKeys` shape:

```json
[
  {
    "valueType": "string",
    "required": false,
    "defaultValue": "",
    "desc": "this is test",
    "key": "test",
    "enum": ""
  }
]
```

Fixed outputs:

```json
{"id": "success", "key": "success", "label": "字段完全提取", "valueType": "boolean", "type": "static"}
{"id": "fields", "key": "fields", "label": "完整提取结果", "valueType": "string", "type": "static"}
{"id": "system_error_text", "key": "system_error_text", "type": "error", "valueType": "string"}
```

Each `extractKeys[].key` also becomes an output. The visible key is the field
key, but the `id` may be generated:

```json
{"id": "uBpKfPkp8tJbYoWG", "key": "test", "label": "提取结果-test", "valueType": "string", "type": "static"}
```

Authoring guidance:

- Maintain a field-key to output-id map for extracted fields.
- Use `success` for deterministic follow-up checks when all required fields
  must be present.
- Treat `fields` as a JSON string unless a same-version export proves object
  output in the target environment.

## Dataset Search

Purpose: retrieve knowledge-base references.

Key input:

```text
datasets
```

Question input can be:

- Flow start user question for natural Q&A.
- A constructed search prompt from a text editor node.
- A follow-up question variable.
- A compact customer briefing plus retrieval task.

Good pattern:

```text
Text editor builds retrieval query -> Dataset search -> AI chat uses dataset quote
```

For a first implementation, one broad dataset-search node can be enough. Split into product, case, talk-track, and SOP searches later when ranking quality or citation control requires it.

## Question Optimization

Purpose: rewrite follow-up questions into better retrieval queries for RAG.

Observed `flowNodeType`:

```text
cfr
```

Key inputs:

- `model`
- `systemPrompt`
- `history`
- `userChatInput`

Observed output:

```json
{"id": "system_text", "key": "system_text", "valueType": "string", "type": "static"}
```

Good pattern:

```text
Question optimization -> Dataset search -> AI chat
```

The optimized output is meant for retrieval. Avoid feeding it to the final AI
answer as the only user question unless that is the intended UX.

## Dataset Quote Merge

Purpose: merge multiple dataset-search quote lists into a single `datasetQuote`
input for one AI chat node.

Observed `flowNodeType`:

```text
datasetConcatNode
```

Key inputs:

- `limit`
- `system_datasetQuoteList`
- one dynamic input per quote source, with `valueType: "datasetQuote"`

Observed dynamic quote input:

```json
{
  "key": "uf0ULngEOoDObvhK",
  "renderTypeList": ["reference"],
  "label": "workflow:quote_num-1",
  "valueType": "datasetQuote",
  "value": ["DATASET_SEARCH_NODE_ID", "quoteQA"]
}
```

Observed output:

```json
{"id": "quoteQA", "key": "quoteQA", "valueType": "datasetQuote", "type": "static"}
```

Good pattern:

```text
Dataset search A -> Dataset search B -> Dataset quote merge -> AI chat
```

Use this when multiple retrieval paths should feed a single answer node.

## Document Parsing

Purpose: parse user-uploaded documents into plain text for downstream nodes.

Observed `flowNodeType`:

```text
readFiles
```

Key input:

```json
{
  "key": "fileUrlList",
  "renderTypeList": ["reference"],
  "valueType": "arrayString",
  "value": [["WORKFLOW_START_NODE_ID", "userFiles"]]
}
```

Observed outputs:

```json
{"id": "system_text", "key": "system_text", "label": "文档解析结果", "valueType": "string", "type": "static"}
{"id": "system_rawResponse", "key": "system_rawResponse", "label": "原始响应", "valueType": "arrayObject", "type": "static"}
{"id": "system_error_text", "key": "system_error_text", "type": "error", "valueType": "string"}
```

Export caveat: some same-version exports reference `workflowStart.userFiles`
even when the start node does not explicitly list `userFiles` in `outputs`.
Treat `workflowStart.userFiles` as a built-in output when file upload is enabled
or a downstream file-aware node has been configured.

## Text Editor

Purpose: construct stable text from variables and node outputs.

Use for:

- Knowledge retrieval queries.
- Prompt snippets.
- Combining multiple dataset results.
- Normalizing user input before a downstream node.

Prefer text editor nodes over embedding large interpolation strings in many different nodes.

Current UI-created text editor nodes may use a dynamic-input shape instead of a
single textarea-only shape. In a 2026-06-24 FastGPT export, `textEditor`
serialized as `version=486` with:

- `system_textareaInput`
- `system_addInputParam`
- one custom input per upstream value, each with `renderTypeList:
  ["reference"]`

The textarea used local placeholders such as `{{q}}` or `{{customer_name}}`,
while the custom input carried the real FastGPT reference such as
`["workflowStart", "userChatInput"]` or `["F02", "customer_name"]`.
The custom input also carried runtime metadata such as `canEdit: true` and
`customInputConfig`. Preserve these fields from the seed. Without them, the JSON
reference can look correct in static inspection while preview output leaves
literal placeholders like `{{customer_name}}`.

Keep the custom input key, label, and placeholder aligned. The safest current
shape is:

```json
{"key": "customer_name", "label": "customer_name", "value": ["F05", "customer_name"]}
```

```text
客户名称：{{customer_name}}
```

Do not set `label` to a friendly Chinese caption such as `客户名称` while using
`{{customer_name}}` in the textarea. In current previews this can leave the
placeholder unresolved. Keep human-friendly Chinese labels on the upstream form
field, not on the text editor's dynamic input alias.

When repairing current-version exports, prefer this pattern:

```text
Form field -> textEditor custom input customer_name
Textarea: 客户名称：{{customer_name}}
```

Do not paste direct FastGPT interpolation such as `{{$F02.customer_name$}}`
inside the textarea unless the target environment's own export proves that
shape. Direct interpolation can parse as JSON but drift from the current editor
shape and make later UI edits fragile.

## Code

Purpose: transform data, build arrays for batch/parallel nodes, normalize JSON,
or perform deterministic calculations.

Observed `flowNodeType`:

```text
code
```

Key inputs:

- `system_addInputParam`
- custom input keys such as `data1` and `data2`
- `codeType`, commonly `js` or `py`
- `code`

Observed fixed outputs:

```json
{"id": "system_addOutputParam", "key": "system_addOutputParam", "type": "dynamic", "valueType": "dynamic"}
{"id": "system_rawResponse", "key": "system_rawResponse", "valueType": "object", "type": "static"}
{"id": "error", "key": "error", "type": "error", "valueType": "string"}
```

Each custom output maps a return-object key to a generated output id:

```json
{"id": "qLUQfhG0ILRX", "type": "dynamic", "key": "textArray", "valueType": "arrayAny", "label": "textArray"}
```

Authoring guidance:

- Code node JSON shape and executable syntax are not enough to validate each
  other. Same-version exports can show inputs and outputs, while the code body
  still needs a target-environment preview run that proves it returns an object.
- In the 2026-06-22 qipaoxian community export, Code nodes used ordinary
  `source-right` edges for their success path and did not add parallel Code
  `source_catch-right` edges. Treat generated Code catch edges as target-version
  suspicious unless a current same-environment export proves they are expected.
- In a 2026-06-24 current FastGPT export, a Code node with `catchError=true`
  used a `source_catch-right` catch branch. Preserve the seed export's edge
  policy: ordinary `source-right` for success paths, and `source_catch-right`
  only when the same-version seed actually has a catch branch.
- Current Code custom inputs can require the same runtime metadata as other
  dynamic inputs: preserve `customInputConfig`, `canEdit: true`, and the
  exported description/default flags from the seed. Missing metadata can make
  `function main({deckTitle})` receive empty values even when the input value is
  a valid reference such as `["F05", "deck_title"]`.
- For the observed JavaScript wrapper `function main({...})`, every destructured
  parameter should have a matching custom Code input key, and every custom input
  consumed by the node should appear in the destructured parameter list. A
  mismatch can import cleanly while the node returns empty or fallback values at
  runtime.
- Return an object/dict from code. Add one custom output per key that
  downstream nodes need.
- Do not infer whether JavaScript should be a bare `return {}`, `async
  function main() {}`, `module.exports = ...`, or another platform wrapper from
  memory. Clone a working same-version Code node sample for the exact runtime.
- If the Code node is only needed for values such as timestamps, trace IDs, or
  small deterministic transforms, prefer a backend HTTP helper endpoint when a
  working Code seed is unavailable.
- Use code to build arrays before `loop` or `parallelRun`.
- Preserve generated output IDs from seed exports or regenerate unique IDs and
  update every downstream reference.

## Batch And Parallel Run

Purpose: apply a sub-workflow to every item in an array. Batch runs sequentially;
parallel run executes multiple items concurrently and aggregates success/failure.

Observed batch `flowNodeType`:

```text
loop
```

Observed parallel `flowNodeType`:

```text
parallelRun
```

Both use child nodes:

```text
loopStart -> inner workflow -> loopEnd
```

Key parent inputs:

- `loopInputArray`
- `childrenNodeIdList`
- `nodeWidth`
- `nodeHeight`
- `loopNodeInputHeight`

Parallel-only inputs:

- `parallelRunMaxConcurrency`
- `parallelRunMaxRetryTimes`

Observed `loopStart` outputs:

```json
{"id": "loopStartIndex", "key": "loopStartIndex", "valueType": "number", "type": "static"}
{"id": "loopStartInput", "key": "loopStartInput", "valueType": "string", "type": "static"}
```

Observed `loopEnd` input:

```json
{"key": "loopEndInput", "renderTypeList": ["reference"], "valueType": "any", "value": ["INNER_NODE_ID", "answerText"]}
```

Observed batch output:

```json
{"id": "loopArray", "key": "loopArray", "label": "数组执行结果", "valueType": "arrayString", "type": "static"}
```

Observed parallel outputs:

```json
{"id": "parallelSuccessResults", "key": "parallelSuccessResults", "valueType": "arrayString", "type": "static"}
{"id": "parallelFullResults", "key": "parallelFullResults", "valueType": "arrayObject", "type": "static"}
{"id": "parallelStatus", "key": "parallelStatus", "valueType": "string", "type": "static"}
```

Authoring guidance:

- Feed `loopInputArray` from an array output, often a code-node custom output.
- Keep interactive nodes such as `formInput` and `userSelect` outside loop and
  parallel child workflows.
- Preserve `childrenNodeIdList`; it is how the parent node knows which canvas
  nodes belong to its inner workflow.
- Use the parent node's aggregate output (`loopArray` or
  `parallelSuccessResults`) downstream, not individual child-node outputs from
  outside the child workflow.

## AI Chat

Purpose: LLM generation.

Authoring guidance:

- Prefer cloning a current same-environment UI-created AI chat node before
  generating production chat nodes. In a FastGPT 4.9.7 export captured on
  2026-06-22, the UI-created chat node had 18 inputs in this order:
  `model`, `temperature`, `maxToken`, `isResponseAnswerText`,
  `aiChatQuoteRole`, `quoteTemplate`, `quotePrompt`, `aiChatVision`,
  `aiChatReasoning`, `aiChatTopP`, `aiChatStopSign`,
  `aiChatResponseFormat`, `aiChatJsonSchema`, `systemPrompt`, `history`,
  `quoteQA`, `fileUrlList`, `userChatInput`. Older generated templates that
  omit `quoteQA` should be treated as stale for that environment, even if they
  still import.
- Preserve optional-field omission exactly. In a 2026-06-24 current FastGPT
  export, optional AI-chat inputs such as `quoteTemplate`, `quotePrompt`,
  `aiChatTopP`, `aiChatStopSign`, `aiChatResponseFormat`, and
  `aiChatJsonSchema` were present as input objects but had no `value` key. Do
  not serialize those as `"value": null`; newer UI/runtime code can treat null
  differently from an omitted value.
- Treat model and generation settings as seed-specific, not global defaults. The
  2026-06-24 minimal chat export used `model=deepseek-v4-flash`,
  `temperature=0`, `maxToken=2000`, `aiChatVision=true`,
  `aiChatReasoning=true`, and `history=6`. If a production workflow needs
  `history=0` or an internal JSON node with `isResponseAnswerText=false`, make
  those changes intentionally and document the import/runtime preview check.
  For generated user apps, do not carry `temperature.value` or `maxToken.value`
  forward merely because a seed export contains them; leave those controls
  omitted unless the user explicitly wants temperature/response-limit tuning or
  a same-environment runtime preview proves the values are required.
- Current chat outputs may mark `reasoningText` as `invalid: true`. Preserve the
  seed output object unless a downstream node intentionally consumes reasoning
  text.
- Feed AI nodes explicit business state: customer briefing, retrieved references, current question, branch name, and last generated card if needed.
- Internal AI nodes such as planners, routers, JSON extractors, scorers, and
  summarizers that feed downstream deterministic nodes must set
  `isResponseAnswerText=false`. Otherwise FastGPT can stream internal JSON or
  scratch output directly to the user.
- Only the final user-facing answer node should stream/respond directly. If an
  internal AI node's output is needed later, consume its `answerText` from a
  downstream parser, text editor, variable update, or answer node.
- Use history as conversational texture, not as the only business memory. For
  deterministic workflow apps that already carry state in explicit variables
  such as `last_data_pack_json`, prefer `history=0` unless a same-version
  runtime preview proves higher history values work. A preview error such as
  `Cannot read properties of undefined (reading 'length')` on a chat node is a
  signal to remove chat-history dependency first.
- Treat explicit generation parameters as runtime hypotheses, not harmless
  schema details. A same-environment minimal chat node may export with no
  `temperature.value` or `maxToken.value`; in one Sangfor/FastGPT 4.9.7 preview
  on 2026-06-22, the missing `maxToken` value was reported at runtime as
  `最大响应 tokens: 1` and the node finished with `超出回复限制`. The qipaoxian
  project decision after that test was to stop using `maxToken` as a repair
  lever: keep the setting disabled/unset in JSON, do not tune it through imports,
  and re-calibrate AI chat node behavior on a clean/community FastGPT instance.
- Be conservative with imported `maxToken` values. Some FastGPT versions validate
  the model's response limit when opening the LLM node settings panel; an
  oversized imported `maxToken` can make the panel fail with a "response limit"
  style error. For qipaoxian exports, do not set this field explicitly unless the
  user reopens this line of investigation in a new target environment.
- Separate initial generation and follow-up generation only when the prompts or required inputs are materially different.
- If follow-up should refine a previous answer, save the previous AI output into a variable such as `last_briefing_card`.

Latency investigation pattern:

```text
T0 Static minimal chat
Start -> Chat, static short prompt, same model, no upstream variables.

T1 Static long chat
Start -> Chat, static prompt containing the same business context as the slow node.

T2 Variable-interpolated chat
Start -> variable/text/code setup -> Chat with the same prompt text assembled
through FastGPT references such as {{$VARIABLE_NODE_ID.varKey$}} or
{{$UPSTREAM_NODE.outputId$}}.

T3 Current business node
The real production branch.
```

If T0 and T1 are fast but T2/T3 show 100s+ TTFT, inspect FastGPT reference
resolution, upstream node timing, variable size/serialization, and chat-node
configuration before changing the business prompt. If all variants show
occasional 100s+ TTFT, treat it as model gateway/platform queueing until proven
otherwise.

Observed knowledge-base quote binding:

```json
{
  "key": "quoteQA",
  "renderTypeList": ["settingDatasetQuotePrompt"],
  "valueType": "datasetQuote",
  "value": ["DATASET_SEARCH_NODE_ID", "quoteQA"]
}
```

Observed file input binding:

```json
{
  "key": "fileUrlList",
  "renderTypeList": ["reference", "input"],
  "valueType": "arrayString",
  "value": [["WORKFLOW_START_NODE_ID", "userFiles"]]
}
```

## Tool Calling

Purpose: let an LLM dynamically choose from connected tools, rather than running
a fixed path.

Observed `flowNodeType` values:

```text
tools
tool
toolSet
stopTool
toolParams
```

Observed `tools` outputs:

```json
{"id": "answerText", "key": "answerText", "label": "AI 回复内容", "valueType": "string", "type": "static"}
{"id": "system_error_text", "key": "system_error_text", "type": "error", "valueType": "string"}
```

Tool-selection edges are special. They do not use ordinary source/target
handles:

```json
{
  "source": "TOOLS_NODE_ID",
  "target": "TOOL_NODE_ID",
  "sourceHandle": "selectedTools",
  "targetHandle": "selectedTools"
}
```

`tools` can also continue as an ordinary node:

```text
TOOLS_NODE_ID-source-right -> stopTool or downstream node
```

Observed `tool` output from a built-in search tool:

```json
{"id": "result", "key": "result", "valueType": "arrayObject", "type": "static"}
{"id": "error", "key": "error", "valueType": "string", "type": "error"}
```

Observed `toolParams` rule: inputs become outputs with the same keys so the
tool-calling LLM can fill them.

Authoring guidance:

- Start with few tools and precise descriptions; tool-calling behavior is model
  sensitive.
- Use `stopTool` when a tool path should end the current tool call without
  asking the LLM to summarize all tool results.
- Do not serialize real tool API keys in exports. `system_input_config` can
  declare secret inputs without storing secret values.

## Plugin Module

Purpose: call a plugin/app module from the current workflow.

Observed `flowNodeType`:

```text
pluginModule
```

Observed minimal input/output:

```json
{"key": "system_forbid_stream", "renderTypeList": ["switch"], "valueType": "boolean", "value": false}
{"id": "system_error_text", "key": "system_error_text", "type": "error", "valueType": "string"}
```

Open uncertainty: this demo export only captured a minimal plugin module, not a
fully parameterized plugin call with plugin input/output bindings. For production
authoring, still request a same-version seed export that includes the actual
plugin/app binding and any dynamic outputs.

## Custom Feedback

Purpose: record a conversation feedback marker for analytics or debugging.

Observed `flowNodeType`:

```text
customFeedback
```

Key input:

```json
{"key": "system_textareaInput", "renderTypeList": ["textarea", "reference"], "valueType": "string"}
```

Observed outputs:

```json
[]
```

Authoring guidance:

- Treat custom feedback as telemetry, not a business-state update.
- It can sit mid-flow and continue through ordinary `source-right` handles.

## Answer Node

Purpose: final or simple fixed response.

Important runtime rule: answer nodes are commonly terminal. Do not place fixed replies in the middle of a success path unless current-platform testing proves execution continues to the next node.

Use answer nodes for:

- Login failure.
- Permission denial.
- No matching customer.
- API failure.
- User-selected end.
