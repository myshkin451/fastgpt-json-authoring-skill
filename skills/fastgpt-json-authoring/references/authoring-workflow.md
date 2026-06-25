# Authoring Workflow

Use this process when a user asks for a new FastGPT app JSON, a major refactor, or a repair of an exported canvas.

For production/industrial-grade claims, also read `industrial-authoring.md`.

## Contents

- Inputs to request or infer
- Planning graph
- Node inventory
- ID strategy
- Generation order
- Repair workflow
- Import validation
- Known platform quirks

## Inputs To Request Or Infer

Best input set:

- A current FastGPT export from the target environment.
- A written workflow spec.
- API contracts for HTTP nodes.
- Knowledge-base names or IDs if retrieval is needed.
- Required global variables and branch permissions.

If no export is available, generate a candidate JSON only with a clear warning: exact import compatibility must be validated in FastGPT, and node shapes may need calibration.

This public skill repository intentionally ships only small generic fixtures, not a complete production seed export. Treat those fixtures as inspector tests, not proof that every node shape matches a target FastGPT deployment.

## Planning Graph

Before JSON editing, write a compact graph:

```text
S00 Workflow start
-> S01 Login state IF

S01.IF no login
-> L02 Login form
-> L03 Login HTTP
-> L04 Login success IF
-> L05 Save login variables
-> M00 Main menu

S01.ELSE already logged in
-> M00 Main menu

M00.option.visit
-> A01 Permission IF
-> A02 Customer input
-> A03 Customer search HTTP
-> A04 Save customer
-> A05 Knowledge search
-> A06 AI generate
```

Then annotate edge handles:

```text
S01.IF uses S01-source-IF
M00.option.visit uses M00-source-visit
L03.catch uses L03-source_catch-right
```

This catches most canvas mistakes before JSON work begins.

## Node Inventory

For non-trivial apps, record a table before editing JSON:

| Field | Purpose |
| --- | --- |
| `nodeId` | Stable JSON identity used by edges and references. |
| `name` | Human-readable canvas label. |
| `flowNodeType` | Runtime operator type. |
| Position | Canvas layout and branch readability. |
| Upstream data | Which node/variable outputs this node consumes. |
| Outputs consumed downstream | Output ids/keys needed later. |
| Success edge | Normal next node. |
| Failure/catch edge | Error branch or denial branch. |
| Import action | Any manual binding after import. |

Keep the table short. It is a review aid, not a second schema.

## ID Strategy

Use stable semantic IDs while authoring when FastGPT accepts them, for example `S00`, `A03`, or `M00`. If the platform rewrites IDs on import, keep a source map in comments outside the JSON or in a companion doc.

Generate random-looking keys for global variables and output IDs only when needed. They must be unique, but they do not need semantic meaning.

Maintain these maps:

```text
node_by_name
node_by_id
var_key_by_label
output_id_by_node_key
user_select_option_key_by_label
```

## Generation Order

1. Define readiness target: draft, static-validated, import-validated, or runtime-validated.
2. Define `chatConfig` and variables.
3. Create nodes with names, `flowNodeType`, cloned metadata, and positions.
4. Create node outputs and record output IDs.
5. Fill node inputs and references.
6. Create edges with valid handles.
7. Run the inspector.
8. Import to FastGPT and perform preview tests.

Do not create edges before user-select option keys are final.

## Repair Workflow

When a user provides a broken export:

1. Run the inspector and read the issues.
2. Build a node table by `nodeId`, `name`, and `flowNodeType`.
3. Build an edge table with source names and target names.
4. Check whether the apparent bug is a JSON wiring issue, a runtime platform quirk, or a business-flow design issue.
5. Patch the smallest set of nodes or edges.
6. Re-run the inspector.
7. Ask the user to import and preview only if local JSON checks pass.

If the canvas has a suspicious downstream-to-upstream loop and FastGPT silently stops, remove the loop first and replace it with one of:

- A terminal answer telling the user to start a new turn.
- A duplicated menu node later in the graph.
- A top-level router that runs on the next user message.

## Import Validation

After import, verify in FastGPT UI:

- Node count and edge count look expected.
- Knowledge-base selections survived import.
- HTTP headers are configured.
- Custom HTTP outputs are still present.
- User-select option edges still point to the intended branches.
- Current-version `textEditor` nodes still show dynamic input parameters and
  local `{{field}}` placeholders rather than stale direct interpolation.
- AI-chat optional inputs that the seed omitted are still omitted, not imported
  as visible `null` values.
- Preview reaches each success branch.
- Preview reaches each error branch.
- AI nodes receive the expected variables and retrieved references.
- For latency-sensitive AI nodes, record time-to-first-token and total duration
  across repeated runs. If a UI-created minimal chat node is fast but a
  production chat node is intermittently slow, create A/B preview branches that
  isolate static prompt text, variable-interpolated prompt text, and upstream
  Code/variable-update steps. Do not use qipaoxian JSON imports to tune
  `maxToken`; keep that setting disabled unless a new target environment is
  explicitly being calibrated.

Use the exact readiness labels from `industrial-authoring.md` in the handoff:
`static-validated`, `import-validated`, and `runtime-validated`.

Keep one tiny "smoke export" per FastGPT version if possible. It becomes the calibration file for future generated apps.

## Known Platform Quirks

These are observed behaviors, not guaranteed product rules:

- Bottom function entry cards can be readable as `system_entryPoint`, but they are not reliable as a continuation mechanism while a form or user-select node is waiting.
- Fixed answer nodes often behave as terminal nodes. Test before placing them in the middle of a success path.
- Some canvas loops or downstream-to-upstream reconnections may import but behave inconsistently at runtime. Prefer simple forward flow with explicit re-entry on the next user message.
- Dataset IDs and model IDs are environment-specific. A public example should not pretend they are portable.
- HTTP node output fields have generated IDs. A visible key such as `success` is not enough for downstream references.
- A chat node can import with a stale but tolerated shape. For example, an older
  generated FastGPT 4.9.7 `chatNode` without `quoteQA` parsed, while a current
  UI-created node exported 18 inputs including `quoteQA`. Prefer the current UI
  seed for repairs and generators.
- A partial UI canvas can be an excellent shape seed while still being an
  incomplete workflow. In the 2026-06-22 qipaoxian community export, the graph
  imported cleanly and inspector shape checks passed, but the business branch
  ended at a non-terminal Code node and several downstream answer_context nodes
  were absent. Check dangling non-terminal nodes before treating an export as a
  repair base.
- Code node success edges in the qipaoxian community export used ordinary
  `source-right`. Do not add Code `source_catch-right` edges just because HTTP
  nodes use catch branches; preserve the current export's edge policy.
- Current Code exports can use `source_catch-right` when `catchError=true`.
  Treat Code catch branches as seed-specific: preserve them when present in the
  same-version export, and do not infer them from HTTP behavior alone.
- A current text editor can use dynamic inputs plus local placeholders. If a
  repaired JSON imports but the editor UI shows direct `{{$node.output$}}`
  strings inside the textarea, rebuild that node from a current `textEditor`
  seed before chasing prompt bugs.
- `null` is not the same as an omitted field in newer AI-chat inputs. If an LLM
  settings panel or preview fails with null/include-style JavaScript errors,
  compare the broken node's optional input objects against a fresh UI-created
  chat node.
- High TTFT with modest token counts is not explained by token volume alone.
  Check model gateway queueing, explicit generation settings, variable
  interpolation, and upstream workflow timing separately.
