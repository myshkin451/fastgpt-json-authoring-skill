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

- Return an object/dict from code. Add one custom output per key that
  downstream nodes need.
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

- Feed AI nodes explicit business state: customer briefing, retrieved references, current question, branch name, and last generated card if needed.
- Use history as conversational texture, not as the only business memory.
- Separate initial generation and follow-up generation only when the prompts or required inputs are materially different.
- If follow-up should refine a previous answer, save the previous AI output into a variable such as `last_briefing_card`.

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
