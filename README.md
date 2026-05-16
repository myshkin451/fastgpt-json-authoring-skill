# FastGPT JSON Authoring Skill

A Codex skill for authoring, inspecting, and validating FastGPT exported application JSON.

FastGPT canvas workflows can be edited by hand in the browser, but large flows become hard to reason about. This skill treats an exported app as a graph program: `chatConfig` defines app state, `nodes` define operators, and `edges` define execution wiring.

## What It Provides

- A reusable Codex skill at `skills/fastgpt-json-authoring`.
- A deterministic inspector script for exported FastGPT JSON.
- Reference docs for variables, node IDs, output IDs, handles, HTTP nodes, knowledge-base search, and import validation.
- Test fixtures that protect the inspector from regressions.

## Install

Copy or symlink the skill folder into your Codex skills directory:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/fastgpt-json-authoring "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Then ask Codex to use `$fastgpt-json-authoring`.

## Inspect A FastGPT Export

```bash
python3 skills/fastgpt-json-authoring/scripts/fastgpt_canvas_inspect.py path/to/app.json
python3 skills/fastgpt-json-authoring/scripts/fastgpt_canvas_inspect.py path/to/app.json --json
```

The inspector is read-only. It reports node counts, variable keys, edge handles, unresolved references, incomplete HTTP nodes, empty dataset-search bindings, and risky back-edges to upstream menu gates.

## Test

```bash
python3 -m unittest discover -s tests
python3 -m py_compile skills/fastgpt-json-authoring/scripts/fastgpt_canvas_inspect.py
```

No third-party Python dependencies are required.

## Notes

FastGPT export schemas can change across versions. For best results, start from a seed export produced by the target FastGPT environment and clone the exact node shapes that app version expects.

This repository intentionally includes only generic fixtures, not a full same-version production seed export. A future authoring session should ask the user for a current redacted export before claiming version-specific import compatibility.
