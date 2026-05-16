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
<nodeId>-source-ELSE
```

Authoring guidance:

- Keep conditions deterministic.
- Do not ask the LLM to decide permission or access scope.
- Use backend API outputs or stable variables for authorization checks.

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

## Answer Node

Purpose: final or simple fixed response.

Important runtime rule: answer nodes are commonly terminal. Do not place fixed replies in the middle of a success path unless current-platform testing proves execution continues to the next node.

Use answer nodes for:

- Login failure.
- Permission denial.
- No matching customer.
- API failure.
- User-selected end.
