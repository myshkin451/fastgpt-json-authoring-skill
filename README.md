# FastGPT JSON Authoring Skill

面向生产的 FastGPT 工作流 JSON 生成、检查与修复技能。

This is an industrial-grade, platform-neutral skill package for authoring,
inspecting, repairing, and validating FastGPT application exports. It is designed
for AI coding agents that support skill-style instructions, including Codex,
Claude Code, OpenClaw, Trae, CoStrict, and similar agent runtimes.

## Why This Exists

FastGPT canvas workflows are easy to start by hand, but production applications
quickly become graph programs: nodes are operators, edges are execution wiring,
`chatConfig.variables` is application state, and HTTP/dataset/AI nodes form
runtime contracts.

Generic template-first generators can produce impressive demos, but real
FastGPT imports are version-sensitive. A JSON file can parse, import, and still
fail at canvas render time or preview time because one field shape, output id,
handle, or dataset binding is wrong.

This project takes a stricter position:

- **Same-version export calibration first**: clone node shapes from real exports
  produced by the target FastGPT environment.
- **Graph-program authoring**: design the workflow as an explicit node/edge/state
  graph before editing JSON.
- **Deterministic inspection**: run a script that checks handles, references,
  HTTP nodes, dataset bindings, catch branches, and secret hygiene.
- **Production handoff discipline**: clearly mark what is import-ready, what must
  be manually rebound after import, and what still needs preview validation.

## Core Capabilities

- Generate importable FastGPT workflow JSON from a workflow spec and a seed
  export.
- Repair broken canvas exports with focused JSON patches.
- Validate node IDs, edge handles, branch handles, output references, variable
  keys, template interpolations, HTTP catch edges, and empty dataset bindings.
- Document FastGPT JSON structures for repeatable application development.
- Support practical node shapes observed in real exports:
  `formInput`, `userSelect`, `ifElseNode`, `httpRequest468`, `variableUpdate`,
  `datasetSearchNode`, `textEditor`, `chatNode`, and `answerNode`.
- Handle production details such as token redaction, environment-specific
  knowledge-base bindings, and FastGPT UI/runtime quirks.

## What Makes It Different

This skill deliberately does not claim that an abstract schema is enough.

Compared with a pure official-template or natural-language-to-JSON approach,
this project emphasizes:

- real exported node shapes over remembered schemas;
- output IDs over visible output labels;
- `VARIABLE_NODE_ID` variable keys over UI variable names;
- explicit workflow state over AI chat history as business memory;
- backend/API authority over LLM-based permission or ACL judgment;
- import checks plus FastGPT preview checks, not only JSON syntax validation.

See:

- `skills/fastgpt-json-authoring/references/industrial-authoring.md`
- `skills/fastgpt-json-authoring/references/template-first-vs-export-calibrated.md`

## Repository Layout

```text
skills/fastgpt-json-authoring/
  SKILL.md                         # Skill entrypoint and execution protocol
  agents/openai.yaml               # Optional UI metadata for OpenAI/Codex-style hosts
  references/
    authoring-workflow.md          # End-to-end workflow for generation and repair
    industrial-authoring.md        # Production-grade authoring principles
    json-schema.md                 # Observed FastGPT export structure
    node-templates.md              # Node-shape guidance from real exports
    template-first-vs-export-calibrated.md
  scripts/
    fastgpt_canvas_inspect.py      # Deterministic inspector

examples/
  hr-recruiting-assistant.json     # Small generic import candidate

tests/
  fixtures/
  test_fastgpt_canvas_inspect.py
```

## Installation

This repository uses a standard skill folder layout. Copy or symlink the skill
folder into the skill directory used by your agent runtime.

For Codex-style hosts:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/fastgpt-json-authoring "${CODEX_HOME:-$HOME/.codex}/skills/"
```

For Claude Code or other skill-based platforms, copy
`skills/fastgpt-json-authoring` into that platform's skills directory and keep
the `references/` and `scripts/` folders with it.

## Basic Usage

Ask your agent to use the skill with a current FastGPT export:

```text
Use fastgpt-json-authoring to generate a FastGPT app JSON.
Seed export: ./exports/minimal-current-version.json
Workflow: login -> permission check -> menu -> customer search -> knowledge retrieval -> AI answer.
HTTP API contract: ...
```

Inspect an existing export directly:

```bash
python3 skills/fastgpt-json-authoring/scripts/fastgpt_canvas_inspect.py app.json
python3 skills/fastgpt-json-authoring/scripts/fastgpt_canvas_inspect.py app.json --json
```

The inspector is read-only. It reports node counts, variables, edge handles,
unresolved references, incomplete HTTP nodes, empty dataset-search bindings,
catch-edge gaps, suspicious menu back-edges, and possible secret leaks.

## Production Workflow

1. Export a small seed app from the target FastGPT environment.
2. Include every node type the target workflow needs.
3. Redact tokens and private customer data.
4. Generate a node inventory and graph plan.
5. Clone seed node shapes and fill business values.
6. Generate edges after node IDs and option keys are final.
7. Run the inspector until all blocking issues are gone.
8. Import into a FastGPT copy.
9. Rebind environment-specific resources such as knowledge bases, model IDs, and
   real HTTP tokens.
10. Preview every success path, denial path, API error path, and menu/re-entry
   path.

## Validation

```bash
python3 -m unittest discover -s tests
python3 -m py_compile skills/fastgpt-json-authoring/scripts/fastgpt_canvas_inspect.py
```

No third-party Python dependencies are required.

## Status And Scope

This project is production-oriented, but FastGPT export schemas can change
between deployments. A generated file should be described as:

- **static-validated** after the inspector passes or only expected warnings
  remain;
- **import-validated** after FastGPT imports it and the canvas opens;
- **runtime-validated** after preview exercises the required business paths.

Do not call a JSON file production-ready only because it parses. Real readiness
requires import and preview evidence.

## License

Apache-2.0. See `LICENSE`.
