# Industrial FastGPT Authoring

This reference defines the production posture for FastGPT JSON generation. Load
it when the user wants an app that is more than a demo, when public/internal
claims need to be precise, or when deciding whether a generated JSON can be
called ready.

## Positioning

FastGPT workflow JSON should be treated as application code:

- `chatConfig` is app configuration and runtime state.
- `nodes` are operators with runtime contracts.
- `edges` are execution wiring.
- HTTP outputs, dataset quotes, form outputs, and internal variables are typed
  interfaces between operators.

The authoring goal is not "write a JSON that parses." The goal is to produce an
importable, inspectable, preview-tested workflow artifact that can be reviewed,
regenerated, repaired, and evolved.

## Production Principles

### 1. Same-Version Export Calibration

Use a seed export from the target FastGPT environment whenever possible.

Preferred workflow:

```text
target FastGPT environment
-> minimal seed export containing required node types
-> clone exact node shapes
-> fill business values
-> run deterministic inspector
-> import copy
-> preview real paths
```

Official/default templates and public examples are useful references, but they
should not override a same-version export that is known to import and render in
the target environment.

### 2. Deterministic Business Control

Do not ask an LLM node to decide:

- identity;
- permissions;
- customer ACL;
- API authorization;
- durable workflow state;
- whether a private customer fact exists.

Use backend/API responses, internal variables, and deterministic `ifElseNode`
conditions for these decisions. LLM nodes should generate prose, coaching,
summaries, extraction drafts, or reasoning outputs after deterministic gates.

### 3. Stable State Is Not Chat History

AI history is conversational context, not stable application memory.

Use internal variables for:

- login/session state;
- selected branch;
- customer identifiers;
- prepared scenario payloads;
- API result objects;
- last generated report/card when follow-up depends on it.

Use chat history for tone and continuity only after the business state has been
made explicit.

### 4. Environment Boundaries

FastGPT exports are not fully portable across environments.

Mark these as post-import configuration unless the target environment is known:

- knowledge-base dataset IDs;
- model provider/model IDs;
- API base URLs;
- real auth tokens;
- private customer records;
- deployment-specific headers.

A public or shareable JSON may contain placeholders and internal variables for
these values, but it must not contain real secrets or private customer data.

### 5. Error Paths Are First-Class

Production workflows should include:

- API catch edges for HTTP nodes with `catchError=true`;
- permission-denied replies;
- no-match/not-found replies;
- failed API success-code branches;
- user-facing recovery or retry guidance;
- menu/re-entry behavior when the app has multiple modes.

Do not rely on the platform silently swallowing errors.

### 6. Reviewable Graphs

Before editing JSON, write a graph plan:

```text
S00 start
-> S01 login gate
-> L02 login form
-> L03 login HTTP
-> L04 success gate
-> P00 permission HTTP
-> G00 menu
```

Then record:

- node IDs;
- flowNodeType;
- important inputs;
- outputs consumed downstream;
- branch handles;
- catch handles;
- expected terminal answer nodes.

This graph is the human review artifact. JSON is the compiled artifact.

## Readiness Levels

Use these labels in handoff reports.

| Label | Meaning | Evidence |
| --- | --- | --- |
| `draft-generated` | JSON was produced but not checked. | File path only. |
| `static-validated` | Deterministic inspector passed or only documented expected warnings remain. | Inspector output. |
| `import-validated` | FastGPT imported the JSON and opened the canvas. | UI/import confirmation. |
| `runtime-validated` | Preview exercised required success, denial, error, and re-entry paths. | Concrete preview path notes. |

Never describe a file as production-ready when it has only reached
`draft-generated`.

## Release Checklist

Before sharing or handing off a generated app:

- JSON parses with UTF-8 or UTF-8 BOM.
- All nodes referenced by edges exist.
- All target handles are valid.
- Branch handles match node type.
- Variable references use variable keys, not visible labels.
- Node output references use output IDs when the target export does so.
- HTTP nodes have URL, method, headers, body, outputs, and catch strategy.
- Real tokens are absent from JSON, docs, and examples.
- Dataset/model/API bindings are either present for the target environment or
  explicitly listed as post-import actions.
- Every business path reaches an answer or intentional wait node.
- Every generated claim says whether validation was static, import, or runtime.

## Public Positioning Language

Use careful claims:

- "Generate and validate FastGPT workflow JSON from real exports."
- "Production-oriented authoring workflow for importable FastGPT apps."
- "Static validation plus explicit import/runtime validation gates."
- "Designed for industrial FastGPT applications where API contracts, ACLs,
  knowledge bases, and workflow state must be reviewable."

Avoid overclaims:

- "Works for every FastGPT version without seed exports."
- "Guaranteed production-ready after JSON validation."
- "No manual post-import configuration required."
