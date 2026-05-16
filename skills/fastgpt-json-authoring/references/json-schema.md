# FastGPT JSON Schema Notes

This reference captures the stable patterns observed in FastGPT application exports. It is not an official schema. Always calibrate against an export from the target FastGPT version before generating production JSON.

## Contents

- Top-level shape
- Global variables
- Node anatomy
- Output IDs
- References and interpolation
- Edge handles
- Entry points
- Dataset bindings
- Secret hygiene

## Top-Level Shape

A FastGPT app export is a JSON object with three primary keys:

```json
{
  "chatConfig": {},
  "nodes": [],
  "edges": []
}
```

`chatConfig` stores app-level settings such as welcome text, variables, file upload flags, automatic execution flags, and optional bottom entry points.

`nodes` stores canvas nodes. Each node is an operator with `flowNodeType`, `inputs`, and `outputs`.

`edges` stores directed graph wiring between source and target handles.

Exports may be UTF-8 with BOM. Read with `utf-8-sig` in Python.

## Global Variables

Variables live under `chatConfig.variables`.

```json
{
  "type": "internal",
  "key": "gI8CiITZ",
  "label": "login_name",
  "valueType": "string",
  "description": "",
  "required": false,
  "defaultValue": "",
  "icon": "core/workflow/inputType/internal"
}
```

Important fields:

| Field | Meaning |
| --- | --- |
| `label` | Human-visible name in FastGPT UI. |
| `key` | Internal reference key used by JSON references. |
| `valueType` | Data type such as `string`, `boolean`, `object`, `any`, `arrayString`, `chatHistory`, or `datasetQuote`. |
| `type` | Usually `internal` for workflow state. |
| `required` | Keep internal state variables false unless the user must provide them before flow starts. |

Maintain a map:

```text
variable label -> variable key
```

Do not reference a variable by its visible label unless the field explicitly expects plain text.

## Node Anatomy

Common node shape:

```json
{
  "nodeId": "A03",
  "name": "A03 Customer Search HTTP",
  "intro": "",
  "avatar": "core/workflow/template/httpRequest",
  "flowNodeType": "httpRequest468",
  "position": { "x": 0, "y": 0 },
  "version": "4.9.7",
  "catchError": true,
  "inputs": [],
  "outputs": []
}
```

Required for graph correctness:

- `nodeId` is the unique identifier used by edges and references.
- `flowNodeType` selects FastGPT behavior.
- `inputs` stores configuration and references.
- `outputs` declares values other nodes can consume.

`position`, `intro`, `avatar`, and `version` are UI/runtime metadata. Prefer cloning them from a same-version seed export rather than inventing values.

## Output IDs

Node outputs often have both a visible `key` and an internal `id`.

```json
{
  "id": "vntBIe",
  "key": "success",
  "label": "success",
  "valueType": "boolean"
}
```

Later references usually use the output `id`, not the `key`.

Maintain a map:

```text
nodeId + output key -> output id
```

This is especially important for HTTP nodes, because humans remember `data.name` or `success`, while FastGPT references the generated output ID.

## References And Interpolation

Structured input references are two-element arrays:

```json
["VARIABLE_NODE_ID", "gI8CiITZ"]
["A03", "vntBIe"]
```

The first array item is either:

- `VARIABLE_NODE_ID` for global variables.
- A real `nodeId` for node outputs.

The second item is:

- A variable key when the owner is `VARIABLE_NODE_ID`.
- An output id when the owner is a node.

Text interpolation uses:

```text
{{$VARIABLE_NODE_ID.gI8CiITZ$}}
{{$A03.vntBIe$}}
```

Do not write `{{$login_name$}}` unless a specific node field documents that syntax. For most canvas references, use the generated IDs.

HTTP JSON bodies can also contain placeholders for that HTTP node's custom variables, such as `{{login_name}}`. Those names are local request parameters, not global variable labels.

## Edge Handles

An edge has source, target, and handles:

```json
{
  "source": "S00",
  "target": "S01",
  "sourceHandle": "S00-source-right",
  "targetHandle": "S01-target-left"
}
```

Handle rules:

| Source type | Valid `sourceHandle` |
| --- | --- |
| Ordinary node | `<sourceNodeId>-source-right` |
| `ifElseNode` true branch | `<sourceNodeId>-source-IF` |
| `ifElseNode` false branch | `<sourceNodeId>-source-ELSE` |
| `userSelect` option | `<sourceNodeId>-source-<option.key>` |
| HTTP catch branch | `<sourceNodeId>-source_catch-right` |

Every target handle should be:

```text
<targetNodeId>-target-left
```

When generating JSON, create edges after node IDs and user-select option keys are final.

## Entry Points

Bottom function entry cards live under `chatConfig.entryPoints`:

```json
[
  { "id": "visit", "name": "Visit Briefing" }
]
```

The selected entry point may be readable through:

```json
["VARIABLE_NODE_ID", "system_entryPoint"]
```

`system_entryPoint` is a built-in pseudo-variable and may not appear in `chatConfig.variables`.

Important caveat: bottom entry cards are UI state, not guaranteed workflow continuation controls. During a paused `formInput` or `userSelect`, users may be unable to select an entry card and then continue the same paused node. Prefer explicit user-select routing inside the workflow when deterministic behavior matters.

## Dataset Bindings

Knowledge-base search nodes usually store selected datasets inside an input named `datasets`. Dataset identifiers are environment-specific.

If dataset IDs are known, clone the exact field shape from a seed export. If they are unknown, leave the node importable but add an explicit post-import step:

```text
Open the dataset search node and manually select the knowledge base.
```

The inspector flags empty dataset selections because imports can look correct while retrieval silently returns nothing.

## Secret Hygiene

FastGPT exports may include HTTP headers or URLs. Before committing or sharing:

- Remove `Authorization`, `X-Agent-Token`, `X-API-Key`, and similar header values.
- Replace private base URLs with placeholders unless the repository is private and intended for deployment.
- Avoid exporting real customer names, transcripts, or account data in sample fixtures.
