# Template-First vs Export-Calibrated Authoring

Use this reference when comparing this skill with template-first FastGPT JSON
generators, including public official or vendor examples.

## Summary

Template-first generators are useful. They provide broad node coverage, clean
rules, and a fast path from natural-language requirements to a plausible JSON
workflow.

This skill uses a stricter production posture: official/default templates are
references, but a same-version FastGPT export from the target environment is the
highest-value source for real import compatibility.

## Why Template-First Is Not Enough

FastGPT JSON is version-sensitive and environment-sensitive.

Common failure modes:

- The JSON parses but the canvas cannot open.
- A node imports but one input field uses a shape that the current UI cannot
  render.
- A visible output key exists, but downstream nodes require the generated output
  `id`.
- An HTTP body placeholder is valid as an HTTP-local variable, but a generic
  validator misreads it as an invalid global reference.
- A dataset node imports with `datasets=[]`, so retrieval silently returns
  nothing until manually rebound.
- Bottom function entry cards look like routes but do not behave reliably while
  a form or user-select node is waiting.

These are not theoretical schema problems. They are import/render/runtime
compatibility problems.

## Comparison

| Dimension | Template-first generator | Export-calibrated authoring |
| --- | --- | --- |
| Primary source | Default templates and written rules | Same-version exported JSON |
| Speed | Fast for greenfield demos | Slightly slower, safer for production |
| Node coverage | Broad when docs are complete | Accurate for sampled node types |
| Import compatibility | Depends on template freshness | Calibrated to target environment |
| Runtime quirks | Often generalized | Captured as observed platform behavior |
| Dataset/model bindings | Easy to overstate portability | Explicit post-import actions |
| Best use | Brainstorming, scaffolding, common demos | Production candidates and repairs |

## How To Use Both

Recommended synthesis:

1. Use template-first docs to decide which node types belong in the workflow.
2. Create or request a same-version seed export containing those node types.
3. Clone real node shapes from the seed export.
4. Fill values and references according to the business graph.
5. Run deterministic inspection.
6. Import into a FastGPT copy.
7. Preview business paths.

In this model, template-first rules help with design breadth, while
export-calibrated authoring protects runtime fidelity.

## Rules For Conflicts

When sources disagree, use this priority order:

1. A same-version export from the target FastGPT environment that has imported
   and opened successfully.
2. A same-version minimal sample deliberately created to test a specific node
   shape.
3. This skill's observed references and inspector behavior.
4. Official/default node templates.
5. Public examples from a different FastGPT version or environment.
6. Model memory.

Do not let a generic validator reject a known-good same-version pattern without
manual review. Instead, update the validator or document the expected warning.

## Practical Differences Observed

### HTTP Body Placeholders

Observed FastGPT HTTP JSON bodies can use local placeholders:

```json
"system_httpJsonBody": "{\n  \"scenario_key\": \"{{scenario_key}}\"\n}"
```

Here `scenario_key` is an HTTP custom input key, not a global variable label.
Do not automatically treat this as an invalid legacy reference.

### Header Variable Interpolation

Observed header interpolation can reference internal variables:

```json
{
  "key": "X-Agent-Token",
  "type": "string",
  "value": "{{$VARIABLE_NODE_ID.v027$}}"
}
```

`VARIABLE_NODE_ID` is a pseudo-owner for global variables, not a real node.

### Form Field Outputs

Observed `formInput` exports can declare field-level outputs:

```json
{"id": "陪练场景", "key": "陪练场景", "label": "陪练场景", "valueType": "string"}
```

These outputs are useful when saving structured form fields into internal
variables. Do not assume `formInputResult` is always the only usable output.

### Dataset Bindings

Dataset IDs are environment-specific. A generated app can still be valuable with
`datasets=[]` if the handoff explicitly says to reselect the knowledge base
after import. The inspector should flag this as an action item, not always a
fatal schema error.

## Public Messaging

Fair comparison language:

- "Template-first generators are useful for broad scaffolding; this project adds
  export-calibrated validation for production FastGPT apps."
- "Designed to catch the practical import, canvas, and preview issues that a
  schema-only validator may miss."
- "Works best with a current seed export from the target FastGPT deployment."

Avoid hostile claims:

- "Official tools are wrong."
- "This guarantees every generated JSON works everywhere."
- "No FastGPT preview is necessary."
