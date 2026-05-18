# Node Templates

Use these patterns as authoring guidance. Prefer cloning exact `inputs` and `outputs` from a same-version FastGPT seed export, then changing values and references.

## Contents

- Workflow start
- IF/ELSE
- User select
- Form input
- Variable update
- HTTP request
- Dataset search
- Text editor
- AI chat
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

## Text Editor

Purpose: construct stable text from variables and node outputs.

Use for:

- Knowledge retrieval queries.
- Prompt snippets.
- Combining multiple dataset results.
- Normalizing user input before a downstream node.

Prefer text editor nodes over embedding large interpolation strings in many different nodes.

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

## Answer Node

Purpose: final or simple fixed response.

Important runtime rule: answer nodes are commonly terminal. Do not place fixed replies in the middle of a success path unless current-platform testing proves execution continues to the next node.

Use answer nodes for:

- Login failure.
- Permission denial.
- No matching customer.
- API failure.
- User-selected end.
