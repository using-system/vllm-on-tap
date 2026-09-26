# vllm-on-tap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship vllm-on-tap v0.1.0 — an Agent Plugins-native plugin whose skills configure an environment, serve a vLLM preset on it and destroy it, on `local-vllm`, `local-vllm-metal`, `local-vllm-docker` and `aca`.

**Architecture:** The repository root is the plugin: `plugin.json` plus `skills/`. Three command skills (`vot-config`, `vot-serve`, `vot-destroy`) orchestrate; three guide skills (`stack-guide` with one reference per stack type, `load-preset`, `vllm-guide`) hold the commands and formats. No scripts, agents or MCP servers ship in the plugin; CI validates the manifest, the presets and the skills' frontmatter; a tag-driven workflow releases.

**Tech Stack:** Markdown skills (Agent Skills format), YAML presets validated by JSON Schema, GitHub Actions, `check-jsonschema`, Python 3.12 + PyYAML + pytest for one CI check, git-cliff, the `oddyssey-release` GitHub App.

**Spec:** `docs/superpowers/specs/2026-09-26-vllm-on-tap-design.md` — read it before any task.

## Global Constraints

- English only in every committed file.
- Never write a secret, token, key value, subscription id or tenant id in any committed file; name variables instead (`HF_TOKEN`, `VOT_API_KEY`). Examples use obviously fake values (`<subscription name>`, `https://otel.example.com:4317`).
- `plugin.json` `$schema` is exactly `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`; `version` starts at `0.1.0`; `license` is `MIT`.
- Stack types are exactly `local-vllm`, `local-vllm-metal`, `local-vllm-docker`, `aca`.
- A served preset is one unit named `vot-<preset>`.
- Local stacks bind `127.0.0.1` only; `aca` always requires an API key and restricts its ingress to the caller's public IP (the key does not cover every vLLM route).
- Traces only: `--otlp-traces-endpoint`; no collector, no metrics export.
- No ACR, no weight cache, one fixed replica on ACA (`minReplicas: 1`, `maxReplicas: 1`).
- Pinned image: `vllm/vllm-openai:v0.30.0`.
- Every GitHub Action is pinned by full commit SHA with its version in a comment.
- Never commit on `main`; branch `type/short-description`; Conventional Commits titles; no `!` / `BREAKING CHANGE`.
- A command skill routes to a guide section and never restates its commands.

## Review Focus

1. A custom preset in `.vot/presets/` with a typo (`vllm_arg:` instead of `vllm_args:`) — expected: `load-preset` refuses it with the schema error, the serve does not start. Pinned by the schema's `additionalProperties: false` and its test in Task 2.
2. `/vot-serve` of a preset already served (`vot-<preset>` exists) — expected: the user is asked to destroy first or stop, never a second unit or a silent overwrite. Pinned in `vot-serve` step 4 (Task 6) and each reference's *Serve* "already exists" check (Tasks 4–5).
3. `aca` serve with `VOT_API_KEY` unset — expected: refused before any Azure call, naming the variable. Pinned in the `aca` reference's *Serve* check 1 (Task 5), `vot-serve` step 4 running the *Serve* checks in their written order (Task 6), and exercised in Task 9.
4. A `local-vllm*` serve whose port is taken — expected: refused with the port named, not a vLLM crash buried in a log. Pinned in the local references' *Serve* first check (Task 4) and exercised in Task 8.
5. A preset whose `gpu_memory_gb` exceeds 80 on `aca` — expected: refused (no ACA serverless profile fits), not a create that never becomes ready. Pinned in the `aca` reference's profile rule (Task 5).

---

### Task 1: Repository skeleton, manifest and the CI check

**Files:**
- Create: `plugin.json`, `.gitignore`, `ci/check_repo.py`, `ci/test_check_repo.py`, `.github/workflows/ci.yml` (`LICENSE` and `README.md` already exist on `main`: MIT, created with the repository)

**Interfaces:**
- Produces: `ci/check_repo.py` with `check_skills(root: Path) -> list[str]` and `check_presets(root: Path) -> list[str]` (each returns error strings, empty when valid) and a `main()` that prints errors and exits 1 when any; CI job `validate` that later tasks' files must pass.

- [ ] **Step 1: Start from `main`**

The repository exists (`https://github.com/using-system/vllm-on-tap`, `main` = the initial README and MIT LICENSE) and the spec and this plan are on `docs/design-spec`, merged to `main` through its own PR on the maintainer's go. Then:

```bash
cd ~/Repos/github/vllm-on-tap
git fetch origin && git switch -c chore/skeleton origin/main
```

- [ ] **Step 2: Write `plugin.json`**

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "vllm-on-tap",
  "version": "0.1.0",
  "description": "Serve vLLM presets on demand - locally, on Apple Silicon, in Docker or on Azure Container Apps serverless GPUs - with their traces exported over OTLP, and tear them down again.",
  "author": {"name": "using-system", "url": "https://github.com/using-system"},
  "homepage": "https://github.com/using-system/vllm-on-tap#readme",
  "repository": "https://github.com/using-system/vllm-on-tap",
  "license": "MIT",
  "keywords": ["vllm", "inference", "llm", "azure-container-apps", "gpu", "opentelemetry"]
}
```

- [ ] **Step 3: Write `.gitignore`** (keep the existing `LICENSE` untouched)

```gitignore
__pycache__/
.pytest_cache/
.venv/
```

- [ ] **Step 4: Write the failing tests `ci/test_check_repo.py`**

```python
from pathlib import Path

from check_repo import check_presets, check_skills


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_valid_skill_passes(tmp_path):
    write(tmp_path / "skills/vot-serve/SKILL.md", "---\nname: vot-serve\ndescription: Serve a preset.\n---\n# x\n")
    assert check_skills(tmp_path) == []


def test_skill_without_frontmatter_fails(tmp_path):
    write(tmp_path / "skills/vot-serve/SKILL.md", "# no frontmatter\n")
    assert check_skills(tmp_path) == ["skills/vot-serve/SKILL.md: no YAML frontmatter"]


def test_skill_name_must_match_directory(tmp_path):
    write(tmp_path / "skills/vot-serve/SKILL.md", "---\nname: serve\ndescription: d\n---\n")
    assert check_skills(tmp_path) == ["skills/vot-serve/SKILL.md: name 'serve' != directory 'vot-serve'"]


def test_skill_needs_description(tmp_path):
    write(tmp_path / "skills/vot-serve/SKILL.md", "---\nname: vot-serve\n---\n")
    assert check_skills(tmp_path) == ["skills/vot-serve/SKILL.md: missing description"]


def test_no_skills_directory_fails(tmp_path):
    assert check_skills(tmp_path) == ["skills/: no SKILL.md found"]


def test_preset_name_must_match_file(tmp_path):
    write(tmp_path / "presets/gemma.yaml", "name: other\nmodel: m\n")
    assert check_presets(tmp_path) == ["presets/gemma.yaml: name 'other' != file name 'gemma'"]


def test_valid_preset_passes(tmp_path):
    write(tmp_path / "presets/gemma.yaml", "name: gemma\nmodel: m\n")
    assert check_presets(tmp_path) == []
```

- [ ] **Step 5: Run to see them fail**

Run: `cd ci && uv run --no-project --with pytest --with pyyaml pytest -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'check_repo'`

- [ ] **Step 6: Write `ci/check_repo.py`**

```python
"""Repository checks CI runs next to the JSON Schema validations."""

import sys
from pathlib import Path

import yaml


def _frontmatter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    data = yaml.safe_load(text[4:end])
    return data if isinstance(data, dict) else None


def check_skills(root: Path) -> list[str]:
    files = sorted((root / "skills").glob("*/SKILL.md"))
    if not files:
        return ["skills/: no SKILL.md found"]
    errors = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        meta = _frontmatter(path.read_text())
        if meta is None:
            errors.append(f"{rel}: no YAML frontmatter")
            continue
        directory = path.parent.name
        if meta.get("name") != directory:
            errors.append(f"{rel}: name '{meta.get('name')}' != directory '{directory}'")
        if not meta.get("description"):
            errors.append(f"{rel}: missing description")
    return errors


def check_presets(root: Path) -> list[str]:
    errors = []
    for path in sorted((root / "presets").glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        if data.get("name") != path.stem:
            errors.append(
                f"{path.relative_to(root).as_posix()}: name '{data.get('name')}' != file name '{path.stem}'"
            )
    return errors


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    errors = check_skills(root) + check_presets(root)
    for error in errors:
        print(error)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Run the tests to see them pass**

Run: `cd ci && uv run --no-project --with pytest --with pyyaml pytest -q`
Expected: `7 passed`

- [ ] **Step 8: Write `.github/workflows/ci.yml`**

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-26.04
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@bec219d24cd3e171d82865faccec33120bb574f4 # v10.1.0
      - name: Test the repository checks
        run: cd ci && uv run --no-project --with pytest --with pyyaml pytest -q
      - name: plugin.json against the Agent Plugins 1.0.0 schema
        run: uvx check-jsonschema --schemafile https://agent-plugins.org/schemas/1.0.0/plugin.schema.json plugin.json
      - name: Presets against presets/schema.json
        run: |
          shopt -s nullglob
          files=(presets/*.yaml)
          [ ${#files[@]} -eq 0 ] || uvx check-jsonschema --schemafile presets/schema.json "${files[@]}"
      - name: Skills and preset names
        run: uv run --no-project --with pyyaml python ci/check_repo.py .
```

- [ ] **Step 9: Run the CI commands locally**

Run: `uvx check-jsonschema --schemafile https://agent-plugins.org/schemas/1.0.0/plugin.schema.json plugin.json`
Expected: `ok -- validation done`
Run: `uv run --no-project --with pyyaml python ci/check_repo.py .`
Expected: prints `skills/: no SKILL.md found`, exit 1 — correct until Task 3 adds the first skill (the CI job stays red until then; Tasks 1–3 land on the same PR).

- [ ] **Step 10: Commit**

```bash
git add plugin.json .gitignore ci .github/workflows/ci.yml
git commit -m "chore(repo): plugin manifest, license and ci checks"
```

---

### Task 2: Preset schema and the first preset

**Files:**
- Create: `presets/schema.json`, `presets/gemma4-12b-qat.yaml`, `ci/fixtures/bad-preset.yaml`

**Interfaces:**
- Consumes: CI job `validate` (Task 1).
- Produces: `presets/schema.json` — the preset contract `load-preset` (Task 3) cites; `presets/gemma4-12b-qat.yaml`.

- [ ] **Step 1: Write the failing fixture `ci/fixtures/bad-preset.yaml`** (Review Focus 1)

```yaml
name: bad-preset
model: google/gemma-4-12B-it-qat-w4a16-ct
vllm_arg:
  --max-model-len: 16384
```

- [ ] **Step 2: Write `presets/schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://raw.githubusercontent.com/using-system/vllm-on-tap/main/presets/schema.json",
  "title": "vllm-on-tap preset",
  "type": "object",
  "additionalProperties": false,
  "required": ["name", "model"],
  "properties": {
    "name": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]*$"},
    "description": {"type": "string"},
    "model": {"type": "string", "minLength": 1},
    "served_model_name": {"type": "string", "minLength": 1},
    "gpu_memory_gb": {"type": "number", "exclusiveMinimum": 0},
    "vllm_args": {"$ref": "#/$defs/vllm_args"},
    "env": {"type": "array", "items": {"type": "string", "pattern": "^[A-Z_][A-Z0-9_]*$"}},
    "stacks": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "local-vllm": {"$ref": "#/$defs/override"},
        "local-vllm-metal": {"$ref": "#/$defs/override"},
        "local-vllm-docker": {"$ref": "#/$defs/override"},
        "aca": {"$ref": "#/$defs/override"}
      }
    }
  },
  "$defs": {
    "vllm_args": {
      "type": "object",
      "propertyNames": {"pattern": "^--[a-z0-9][a-z0-9-]*$"},
      "additionalProperties": {"type": ["string", "number", "boolean"]}
    },
    "override": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "model": {"type": "string", "minLength": 1},
        "vllm_args": {"$ref": "#/$defs/vllm_args"},
        "gpu_memory_gb": {"type": "number", "exclusiveMinimum": 0}
      }
    }
  }
}
```

- [ ] **Step 3: Run the schema on the bad fixture to see it refuse**

Run: `uvx check-jsonschema --schemafile presets/schema.json ci/fixtures/bad-preset.yaml`
Expected: FAIL, `Additional properties are not allowed ('vllm_arg' was unexpected)`

- [ ] **Step 4: Write `presets/gemma4-12b-qat.yaml`**

```yaml
name: gemma4-12b-qat
description: Gemma 4 12B instruction-tuned, Google's QAT 4-bit weights (compressed-tensors, w4a16)
model: google/gemma-4-12B-it-qat-w4a16-ct
served_model_name: gemma4-12b
gpu_memory_gb: 16
vllm_args:
  --max-model-len: 16384
  --gpu-memory-utilization: 0.90
env: []
stacks:
  local-vllm-metal:
    model: mlx-community/gemma-4-12B-it-4bit
```

- [ ] **Step 5: Validate it**

Run: `uvx check-jsonschema --schemafile presets/schema.json presets/gemma4-12b-qat.yaml && uv run --no-project --with pyyaml python -c "import sys; sys.path.insert(0,'ci'); from check_repo import check_presets; from pathlib import Path; print(check_presets(Path('.')))"`
Expected: `ok -- validation done` then `[]`

- [ ] **Step 6: Commit**

```bash
git add presets ci/fixtures
git commit -m "feat(presets): preset schema and the gemma4-12b-qat preset"
```

---

### Task 3: `load-preset` and `vllm-guide` skills

**Files:**
- Create: `skills/load-preset/SKILL.md`, `skills/vllm-guide/SKILL.md`

**Interfaces:**
- Consumes: `presets/schema.json` (Task 2).
- Produces: the sections other skills route to by name — `load-preset`: *Format*, *Resolve*, *Validate*, *Merge*, *Builtin presets*; `vllm-guide`: *Serve flags*, *Traces over OTLP*, *API key*, *OpenAI API*, *Tuning*.

- [ ] **Step 1: Write `skills/load-preset/SKILL.md`**

````markdown
---
name: load-preset
description: The vllm-on-tap preset - its format, where a preset name resolves (custom in .vot/presets/, then builtin in the official repository), how it is validated and how its per-stack overrides merge. Read when a preset is served, listed, written or checked.
---

# load-preset

A preset states what vLLM serves - never where or how it is hosted (no image,
region, port or resource name).

## Format

The contract is `presets/schema.json` in the official repository
(`https://raw.githubusercontent.com/using-system/vllm-on-tap/main/presets/schema.json`).

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | the preset's name, equal to the file name without `.yaml` |
| `description` | no | one line |
| `model` | yes | Hugging Face repository id vLLM serves |
| `served_model_name` | no | the OpenAI API `model` name clients send; defaults to `name` |
| `gpu_memory_gb` | no | the smallest GPU memory the preset runs on |
| `vllm_args` | no | flags passed as-is to `vllm serve`, one per key (`--flag: value`); `true` is a bare flag, `false` omits it |
| `env` | no | names of environment variables the preset needs (`HF_TOKEN` for a gated model) |
| `stacks.<stack type>` | no | overrides of `model`, `vllm_args` (merged key by key) and `gpu_memory_gb` for one stack type |

## Resolve

For a preset name `<name>`, in order:

1. `.vot/presets/<name>.yaml` in the user's repository - a custom preset,
   which shadows a builtin of the same name.
2. `https://raw.githubusercontent.com/using-system/vllm-on-tap/main/presets/<name>.yaml`
   (`curl -fsSL <url>`); a 404 means no builtin of that name.

Found in neither: list the available presets (the files in `.vot/presets/`
and the *Builtin presets* below) and stop.

## Validate

Validate the resolved file before use:

```bash
uvx check-jsonschema --schemafile https://raw.githubusercontent.com/using-system/vllm-on-tap/main/presets/schema.json <preset file>
```

A builtin fetched over HTTP is first saved to `.vot/run/<name>.yaml`. Any
error: show it and stop - a preset that fails its schema is never served.
Also refuse a `name` that differs from the file name.

## Merge

After validation, when the preset has `stacks.<current stack type>`: its
`model` and `gpu_memory_gb` replace the preset's; its `vllm_args` are merged
key by key into the preset's (the override wins). `served_model_name`
defaults to `name` when absent.

## Builtin presets

| Name | Model | GPU memory |
|---|---|---|
| `gemma4-12b-qat` | `google/gemma-4-12B-it-qat-w4a16-ct` (MLX `mlx-community/gemma-4-12B-it-4bit` on `local-vllm-metal`) | 16 GB |
````

- [ ] **Step 2: Write `skills/vllm-guide/SKILL.md`**

````markdown
---
name: vllm-guide
description: vLLM capabilities a vllm-on-tap preset or serve needs - the serve flags, tracing over OTLP, the API key, the OpenAI-compatible API and tuning for a GPU - each linked to vLLM's documentation. Read when writing or adjusting a preset, or when a serve adds tracing or an API key.
---

# vllm-guide

Documentation root: https://docs.vllm.ai/en/latest/

## Serve flags

- `vllm serve <model>` - the model is the positional argument; the
  `vllm/vllm-openai` image's entrypoint is already `vllm serve`, so a
  container's arguments start with the model.
- `--host 127.0.0.1 --port <port>` - bind address and port (default port 8000).
- `--served-model-name <name>` - the name clients send as `model`.
- `--max-model-len <tokens>` - context length; lower it when the KV cache does not fit.
- `--gpu-memory-utilization <0..1>` - share of GPU memory vLLM takes (default 0.9).
- `--dtype float16|bfloat16|auto` - T4 (compute capability 7.5) has no bf16: vLLM falls back to fp16 there.
- `--tensor-parallel-size <n>` - split over n GPUs; ACA serverless has one GPU per replica, so 1.
- `--quantization <method>` - usually inferred from the checkpoint (compressed-tensors w4a16 needs compute capability >= 7.5).
- Reference: https://docs.vllm.ai/en/latest/cli/serve.html

## Traces over OTLP

- `--otlp-traces-endpoint <url>` - vLLM exports one span per request over OTLP.
- Protocol: gRPC by default; set `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf`
  when the endpoint is OTLP/HTTP (port 4318, or a URL ending in `/v1/traces`).
- OTLP/HTTP: vLLM hands the flag's value to the exporter verbatim, with no
  path appended - the value must be the full URL ending in `/v1/traces`
  (`http://host:4318` alone posts to `/` and the traces are lost). gRPC
  takes `host:port` or `http(s)://host:port` with no path.
- `OTEL_SERVICE_NAME=vot-<preset>` names the service the spans belong to.
- Metrics have no OTLP export (Prometheus `/metrics` only); vllm-on-tap exports traces only.
- The OpenTelemetry packages are part of vLLM's base requirements; an install
  that reports them missing is repaired with `pip install 'vllm[otel]'`.
- Reference: https://docs.vllm.ai/en/latest/examples/online_serving/opentelemetry.html

## API key

- When `VLLM_API_KEY` is set in its environment (or `--api-key <key>` is
  passed), vLLM requires `Authorization: Bearer <key>` on the `/v1`, `/v2`,
  `/inference` and `/cohere` routes only. Other routes - `/invocations`
  (full inference), `/tokenize`, `/pause`, `/abort_requests`,
  `/update_weights` - stay open (vLLM docs, "API Key Authentication
  Limitations"): a public endpoint also needs a network restriction.
- Prefer the environment variable so the key never appears in a command line.
- Reference: https://docs.vllm.ai/en/latest/usage/security.html

## OpenAI API

- `GET /v1/models` - lists the served name; the readiness check.
- `POST /v1/chat/completions` - chat:

```bash
curl -s <base url>/v1/chat/completions -H 'Content-Type: application/json' \
  [-H "Authorization: Bearer $VOT_API_KEY"] \
  -d '{"model":"<served name>","messages":[{"role":"user","content":"Say hello in one sentence."}],"max_tokens":64}'
```

- Reference: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html

## Tuning

- Out of memory at start: lower `--max-model-len`, then `--gpu-memory-utilization`.
- Weights size ~ parameters x bytes per weight (4-bit ~ 0.5 byte, bf16 2 bytes);
  `gpu_memory_gb` must hold the weights plus the KV cache.
````

- [ ] **Step 3: Run the repository check**

Run: `uv run --no-project --with pyyaml python ci/check_repo.py .`
Expected: no output, exit 0

- [ ] **Step 4: Commit**

```bash
git add skills/load-preset skills/vllm-guide
git commit -m "feat(skills): load-preset and vllm-guide"
```

---

### Task 4: `stack-guide` and the three local references

**Files:**
- Create: `skills/stack-guide/SKILL.md`, `skills/stack-guide/references/local-vllm.md`, `skills/stack-guide/references/local-vllm-metal.md`, `skills/stack-guide/references/local-vllm-docker.md`

**Interfaces:**
- Consumes: `vllm-guide` sections (Task 3).
- Produces: the reference contract — sections *Prerequisites and install*, *Config fields*, *Prepare*, *Serve*, *Ready when*, *Destroy*, *Traps* — that the command skills (Task 6) route to by name.

- [ ] **Step 1: Write `skills/stack-guide/SKILL.md`**

````markdown
---
name: stack-guide
description: How vllm-on-tap runs vLLM on each stack type - local-vllm (Linux), local-vllm-metal (macOS, Apple Silicon), local-vllm-docker (Linux, NVIDIA) and aca (Azure Container Apps serverless GPU) - one reference per type with its prerequisites, config fields, serve, readiness, destroy and traps. Read the current stack type's reference only.
---

# stack-guide

One reference per stack type in `references/<stack type>.md`. Read only the
current environment's type.

Every reference has these sections, in this order:

- **Prerequisites and install** - the tools the type needs, how to check
  them, and each one's official install command (run only on the user's yes).
- **Config fields** - the `config` keys of an environment of this type, with defaults.
- **Prepare** - what `/vot-config` creates once (only `aca` has one).
- **Serve** - numbered checks, run in their written order and stopping at the first refusal (the "already served" one leads to the destroy-or-stop question), then the exact command that starts unit `vot-<preset>`.
- **Ready when** - the readiness check and its time bound.
- **Destroy** - the exact command that removes unit `vot-<preset>`.
- **Traps** - one line each.

Placeholders used in the references: `<preset>` (the preset name),
`<model>`, `<served name>`, `<vllm args>` (the merged `vllm_args` rendered
as `--flag value`, `true` as `--flag`, `false` omitted), `<port>` and the
other `config` fields by their key.

Tracing (every type): when the environment has `otlp_endpoint`, add
`--otlp-traces-endpoint <otlp_endpoint>` to `<vllm args>` and set
`OTEL_SERVICE_NAME=vot-<preset>` in vLLM's environment. For an OTLP/HTTP
endpoint (port 4318 or a `/v1/traces` path) also set
`OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf` and pass the full URL
ending in `/v1/traces`, appending that path when the environment's value
lacks it (vllm-guide's *Traces over OTLP*).

Preset environment (every type): each name in the preset's `env` must be set
in the user's shell - refuse naming the missing one - and is passed to vLLM
by name, never by value in a file.
````

- [ ] **Step 2: Write `skills/stack-guide/references/local-vllm.md`**

````markdown
# local-vllm (Linux, NVIDIA GPU)

> Not yet verified live: written from vLLM's documentation. Remove this line
> once a Linux machine with an NVIDIA GPU has run config, serve and destroy.

## Prerequisites and install

- `nvidia-smi` succeeds (an NVIDIA driver is installed) - not installable here; the user's.
- `vllm --version` succeeds. Install: `uv tool install vllm` (or `pip install vllm`).
- `curl --version` succeeds.

## Config fields

- `port` - default `8000`.

## Prepare

None.

## Serve

1. Already served: `test -f .vot/run/vot-<preset>.pid && kill -0 "$(cat .vot/run/vot-<preset>.pid)"` succeeds -> unit exists.
2. Port taken: `lsof -iTCP:<port> -sTCP:LISTEN` prints a line -> refuse, naming the port.
3. Start:

```bash
mkdir -p .vot/run
[OTEL_SERVICE_NAME=vot-<preset>] [OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf] \
nohup vllm serve <model> --host 127.0.0.1 --port <port> --served-model-name <served name> <vllm args> \
  > .vot/run/vot-<preset>.log 2>&1 &
echo $! > .vot/run/vot-<preset>.pid
```

Base URL: `http://127.0.0.1:<port>`.

## Ready when

`curl -sf http://127.0.0.1:<port>/v1/models` lists `<served name>`; poll every
10 s for up to 15 min (the first run downloads the weights). On timeout or
when the PID dies: `tail -n 50 .vot/run/vot-<preset>.log`.

## Destroy

```bash
kill "$(cat .vot/run/vot-<preset>.pid)"; sleep 5; kill -9 "$(cat .vot/run/vot-<preset>.pid)" 2>/dev/null
rm -f .vot/run/vot-<preset>.pid .vot/run/vot-<preset>.log .vot/run/<preset>.yaml
```

No PID file: report that the unit does not exist.

## Traps

- The weights land in `~/.cache/huggingface`; a destroy keeps them.
- `nohup` output goes to the log file only; read it on failure, never assume.
````

- [ ] **Step 3: Write `skills/stack-guide/references/local-vllm-metal.md`**

````markdown
# local-vllm-metal (macOS, Apple Silicon)

## Prerequisites and install

- macOS 15 or later on Apple Silicon: `sw_vers -productVersion` >= 15 and `uname -m` = `arm64`. Not installable here.
- `vllm --version` succeeds with the vllm-metal plugin. Install: `brew tap vllm-project/vllm-metal https://github.com/vllm-project/vllm-metal && brew install vllm-project/vllm-metal/vllm-metal` (the tap is not a `homebrew-*` repository, so it needs its URL).
- `curl --version` succeeds.

## Config fields

- `port` - default `8000`.

## Prepare

None.

## Serve

Identical to local-vllm's *Serve* (same checks, same command, same
`.vot/run/` files), with the preset's `local-vllm-metal` model - MLX weights
(`mlx-community/...`); vllm-metal does not load compressed-tensors checkpoints.

## Ready when

Identical to local-vllm's, up to 15 min.

## Destroy

Identical to local-vllm's.

## Traps

- Unified memory is shared with the system: `gpu_memory_gb` compares with
  `sysctl -n hw.memsize` / 1e9, leaving ~8 GB to macOS; warn when tighter.
- Supported models: https://github.com/vllm-project/vllm-metal/blob/main/docs/supported_models.md
- `--dtype` and CUDA-only flags (`--tensor-parallel-size` > 1) do not apply.
````

- [ ] **Step 4: Write `skills/stack-guide/references/local-vllm-docker.md`**

````markdown
# local-vllm-docker (Linux, NVIDIA GPU)

> Not yet verified live: written from vLLM's documentation. Remove this line
> once a Linux machine with an NVIDIA GPU has run config, serve and destroy.

## Prerequisites and install

- `docker info` succeeds. Install: https://docs.docker.com/engine/install/
- GPU access: `docker run --rm --gpus all ubuntu nvidia-smi` succeeds. Install the NVIDIA Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
- `curl --version` succeeds.

## Config fields

- `port` - default `8000`.
- `image` - optional; default `vllm/vllm-openai:v0.30.0`.

## Prepare

None.

## Serve

1. Already served: `docker ps -a --filter name=^vot-<preset>$ --format '{{.Names}}'` prints a name -> unit exists.
2. Port taken: `lsof -iTCP:<port> -sTCP:LISTEN` prints a line -> refuse, naming the port.
3. Start (the image's entrypoint is `vllm serve`, so the arguments start with the model):

```bash
docker run -d --name vot-<preset> --gpus all --ipc=host \
  -p 127.0.0.1:<port>:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  [-e HF_TOKEN] [-e OTEL_SERVICE_NAME=vot-<preset>] [-e OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf] \
  <image> <model> --served-model-name <served name> <vllm args>
```

Base URL: `http://127.0.0.1:<port>`.

## Ready when

`curl -sf http://127.0.0.1:<port>/v1/models` lists `<served name>`; poll every
10 s for up to 15 min. On timeout or exit: `docker logs --tail 50 vot-<preset>`.

## Destroy

```bash
docker rm -f vot-<preset>
```

`No such container`: report that the unit does not exist.

## Traps

- An `otlp_endpoint` on `localhost` means the container itself: use
  `host.docker.internal` (with `--add-host=host.docker.internal:host-gateway`) to reach the host.
- `-e HF_TOKEN` (no value) passes the shell's variable by name.
````

- [ ] **Step 5: Run the repository check**

Run: `uv run --no-project --with pyyaml python ci/check_repo.py .`
Expected: no output, exit 0

- [ ] **Step 6: Commit**

```bash
git add skills/stack-guide
git commit -m "feat(stack-guide): the stack contract and the local references"
```

---

### Task 5: The `aca` reference

**Files:**
- Create: `skills/stack-guide/references/aca.md`

**Interfaces:**
- Consumes: the reference contract (Task 4), `vllm-guide` *API key* (Task 3).
- Produces: `aca` sections *Prepare* (used by `/vot-config`) and *Serve*/*Destroy*.

- [ ] **Step 1: Write `skills/stack-guide/references/aca.md`**

````markdown
# aca (Azure Container Apps, serverless GPU)

## Prerequisites and install

- `az version` succeeds. Install: https://learn.microsoft.com/cli/azure/install-azure-cli (macOS: `brew install azure-cli`).
- `az account show` succeeds - otherwise the user runs `az login`; never run it for them.
- `az extension show --name containerapp` succeeds. Install: `az extension add --name containerapp --upgrade`.
- `az provider show --namespace Microsoft.App --query registrationState -o tsv` prints `Registered`. Install: `az provider register --namespace Microsoft.App --wait`.
- `jq --version` succeeds (to build the app spec below). Install: `brew install jq` / the distribution's package.

## Config fields

- `subscription` - name as `az account list --query "[].name" -o tsv` prints it.
- `location` - a region with serverless GPUs; T4 and A100: `australiaeast`, `brazilsouth`, `canadacentral`, `eastus`, `italynorth`, `swedencentral`, `westus`, `westus3`; T4 only: `centralindia`, `francecentral`, `japaneast`, `northcentralus`, `southcentralus`, `southeastasia`, `southindia`, `westeurope`, `westus2`.
- `resource_group` - default `rg-vot`.
- `environment` - the Container Apps environment; default `vot-env`.
- `api_key_env` - the name of the shell variable holding the API key; default `VOT_API_KEY`.
- `image` - optional; default `vllm/vllm-openai:v0.30.0`.

Every command below runs with `--subscription "<subscription>"`.

## Prepare

Each step: reuse when it exists, create on the user's yes otherwise.

```bash
az group show --name <resource_group>
az group create --name <resource_group> --location <location>

az containerapp env show --name <environment> --resource-group <resource_group>
az containerapp env create --name <environment> --resource-group <resource_group> --location <location> --enable-workload-profiles

az containerapp env workload-profile list --name <environment> --resource-group <resource_group> --query "[].name" -o tsv
az containerapp env workload-profile add --name <environment> --resource-group <resource_group> --workload-profile-name gpu-t4 --workload-profile-type Consumption-GPU-NC8as-T4
az containerapp env workload-profile add --name <environment> --resource-group <resource_group> --workload-profile-name gpu-a100 --workload-profile-type Consumption-GPU-NC24-A100
```

A profile `add` refused for quota: tell the user to request "Managed
Environment Consumption T4 GPUs" / "Managed Environment Consumption NCA100
GPUs" on the environment's Quota page
(https://learn.microsoft.com/azure/container-apps/quota-requests), and save
the environment anyway.

## Serve

Checks, in this order, stopping at the first refusal:

1. `<api_key_env>` unset in the shell -> refuse before any Azure call, naming the variable.
2. Profile from `gpu_memory_gb`: <= 16 -> `gpu-t4` (cpu `8`, memory `56Gi`); <= 80 -> `gpu-a100` (cpu `24`, memory `220Gi`); > 80 -> refuse (no serverless profile fits).
3. The profile exists: `az containerapp env workload-profile list --name <environment> --resource-group <resource_group> --query "[].name" -o tsv` lists it; otherwise refuse and route to `/vot-config` (quota).
4. Already served: `az containerapp show --name vot-<preset> --resource-group <resource_group>` succeeds -> unit exists.

Create. `az containerapp create --args` cannot carry vLLM's `--flags` (az
parses them as its own), so the app is created from a YAML spec, built with
`jq` and streamed through process substitution: the secrets' values come
from the shell and never touch the disk.

```bash
ENV_ID="$(az containerapp env show --name <environment> --resource-group <resource_group> --query id -o tsv)"
CALLER_IP="$(curl -fsS https://api.ipify.org)"
ARGS='["<model>","--served-model-name","<served name>","--port","8000", <vllm args as JSON strings>]'
ENVS='[{"name":"VLLM_API_KEY","secretRef":"vllm-api-key"}]'   # + {"name":"HF_TOKEN","secretRef":"hf-token"}, {"name":"OTEL_SERVICE_NAME","value":"vot-<preset>"}, {"name":"OTEL_EXPORTER_OTLP_TRACES_PROTOCOL","value":"http/protobuf"} when they apply
SECRETS="$(jq -n --arg k "${<api_key_env>}" '[{name:"vllm-api-key",value:$k}]')"   # + {name:"hf-token",value:$ENV.HF_TOKEN} when the preset lists HF_TOKEN
az containerapp create --name vot-<preset> --resource-group <resource_group> --yaml <(jq -n \
  --arg loc "<location>" --arg env "$ENV_ID" --arg wp "<profile>" --arg img "<image>" \
  --arg ip "$CALLER_IP/32" --argjson cpu <cpu> --arg mem "<memory>" \
  --argjson args "$ARGS" --argjson envs "$ENVS" --argjson secrets "$SECRETS" '{
    location: $loc,
    properties: {
      environmentId: $env,
      workloadProfileName: $wp,
      configuration: {
        activeRevisionsMode: "Single",
        ingress: {external: true, targetPort: 8000, transport: "auto",
          ipSecurityRestrictions: [{name: "caller", ipAddressRange: $ip, action: "Allow"}]},
        secrets: $secrets
      },
      template: {
        containers: [{name: "vllm", image: $img, args: $args, env: $envs,
          resources: {cpu: $cpu, memory: $mem}}],
        scale: {minReplicas: 1, maxReplicas: 1}
      }
    }
  }')
```

(`jq` emits JSON, which is valid YAML.) Base URL:
`https://$(az containerapp show --name vot-<preset> --resource-group <resource_group> --query properties.configuration.ingress.fqdn -o tsv)`.
Say it: billing runs until `/vot-destroy <preset>`, and only this machine's
public IP can reach the app (`/vot-serve` again from another network).

## Ready when

`curl -sf -H "Authorization: Bearer ${<api_key_env>}" <base url>/v1/models`
lists `<served name>`; poll every 20 s for up to 30 min (image pull ~10 GB,
then the weights). On timeout:
`az containerapp logs show --name vot-<preset> --resource-group <resource_group> --tail 50`.

## Destroy

```bash
az containerapp delete --name vot-<preset> --resource-group <resource_group> --yes
```

`ResourceNotFound`: report that the unit does not exist. The environment and
its GPU profiles stay; `az group delete --name <resource_group>` removes
everything and is the user's call, never a destroy's.

## Traps

- GPU workload profiles get no default health probes, so a long model load is not restarted.
- One GPU per replica; `--tensor-parallel-size` stays 1.
- The platform driver sets the CUDA ceiling (driver 570 -> CUDA 12.x, 580 -> 13.x): an image built for a newer CUDA fails at start - check the log's CUDA error first.
- The secret values expand from the shell into the process substitution; they never go into a file or a command line.
- The API key covers `/v1`, `/v2`, `/inference`, `/cohere` only; `/invocations`, `/tokenize`, `/pause`, `/abort_requests`, `/update_weights` are protected by the ingress IP restriction alone - never remove it.
- The caller's IP changes (another network, a VPN): update the rule with `az containerapp ingress access-restriction set --name vot-<preset> --resource-group <resource_group> --rule-name caller --ip-address <new ip>/32 --action Allow`.
- An `otlp_endpoint` on `localhost` or a private address is unreachable from the app.
````

- [ ] **Step 2: Run the repository check**

Run: `uv run --no-project --with pyyaml python ci/check_repo.py .`
Expected: no output, exit 0

- [ ] **Step 3: Commit**

```bash
git add skills/stack-guide/references/aca.md
git commit -m "feat(stack-guide): the aca reference"
```

---

### Task 6: The three command skills

**Files:**
- Create: `skills/vot-config/SKILL.md`, `skills/vot-serve/SKILL.md`, `skills/vot-destroy/SKILL.md`

**Interfaces:**
- Consumes: `stack-guide` sections (Tasks 4–5), `load-preset` sections (Task 3), `vllm-guide` *OpenAI API* (Task 3).
- Produces: the user-facing entry points `vot-config`, `vot-serve <preset>`, `vot-destroy <preset>`.

- [ ] **Step 1: Write `skills/vot-config/SKILL.md`**

````markdown
---
name: vot-config
description: Create, update or select a vllm-on-tap environment - its stack type (local-vllm, local-vllm-metal, local-vllm-docker, aca), its config and its optional OTLP traces endpoint - checking and offering to install the tools it needs, and on aca preparing the resource group, the Container Apps environment and its GPU profiles. Use when the user wants to configure where presets are served.
---

# /vot-config

State lives in the user's repository under `.vot/`:
`.vot/environments/<name>.yaml` (committed) and `.vot/config.yaml`
(`current: <name>`, gitignored). Never write a secret into either.

1. **First run.** When `.vot/` does not exist, append to the repository's
   `.gitignore` the two lines `.vot/config.yaml` and `.vot/run/`.
2. **Choose.** List `.vot/environments/*.yaml` (name, stack) and the current
   one; offer: create one, update one, or make one current (then go to step 8).
3. **Stack type.** On create: ask the name and the stack type
   (`local-vllm`, `local-vllm-metal`, `local-vllm-docker`, `aca`). Read the
   stack-guide skill's reference for that type.
4. **Tools.** Run that reference's *Prerequisites and install* checks. For a
   missing tool, show its install command and run it only on the user's yes;
   what is the user's (a driver, `az login`) is stated, never done.
5. **Config.** Ask the reference's *Config fields*, showing the defaults.
6. **Prepare.** When the reference has a *Prepare* section, run it.
7. **Traces.** Ask `otlp_endpoint` (optional, empty to skip). On `aca`, warn
   when it names `localhost` or a private address.
8. **Write.** Write `.vot/environments/<name>.yaml`:

   ```yaml
   name: <name>
   stack: <stack type>
   otlp_endpoint: <url>        # omitted when empty
   config:
     <field>: <value>
   ```

   then `.vot/config.yaml` with `current: <name>`, and print a summary: the
   environment, its stack, its config, whether traces are exported.
````

- [ ] **Step 2: Write `skills/vot-serve/SKILL.md`**

````markdown
---
name: vot-serve
description: Serve a vLLM preset on the current vllm-on-tap environment - resolve the preset (custom or builtin), start vLLM on the environment's stack as unit vot-<preset>, wait until it answers, and print the endpoint with a ready-to-paste request. Use when the user wants a preset running; the argument is the preset name.
---

# /vot-serve <preset>

1. **Environment.** Read `.vot/config.yaml` and
   `.vot/environments/<current>.yaml`. None: tell the user to run
   `/vot-config` and stop.
2. **Preset.** No preset given: list the available presets per the
   load-preset skill's *Resolve* and stop. Otherwise resolve, validate and
   merge it per load-preset's *Resolve*, *Validate* and *Merge*, for the
   environment's stack type.
3. **Stack.** Read the stack-guide skill's `SKILL.md` and the reference of
   the environment's stack type.
4. **Checks.** Run the reference's *Serve* checks in their written order,
   stopping at the first refusal. At the "already served" check, when
   `vot-<preset>` exists: ask whether to destroy it first (then run
   `/vot-destroy <preset>`'s steps and continue) or stop. Never start a
   second unit.
5. **Start.** Run the reference's *Serve* start command, with tracing per
   stack-guide when the environment has `otlp_endpoint`.
6. **Wait.** Run the reference's *Ready when*. On timeout, show the log
   lines it names and leave the unit for the user to inspect or destroy.
7. **Report.** Print the base URL, the served name, and the vllm-guide
   skill's *OpenAI API* `curl` filled in (with the Authorization header on
   `aca`); on `aca`, repeat that billing runs until `/vot-destroy <preset>`.
````

- [ ] **Step 3: Write `skills/vot-destroy/SKILL.md`**

````markdown
---
name: vot-destroy
description: Destroy the unit vot-<preset> a vllm-on-tap serve created on the current environment (a process, a container or a Container App), keeping the environment itself. Use when the user wants a served preset stopped and removed; the argument is the preset name.
---

# /vot-destroy <preset>

1. **Environment.** Read `.vot/config.yaml` and
   `.vot/environments/<current>.yaml`. None: tell the user to run
   `/vot-config` and stop.
2. **Stack.** Read the stack-guide skill's reference for the environment's
   stack type.
3. **Destroy.** Run the reference's *Destroy* for `vot-<preset>`. A unit that
   does not exist is reported, not an error.
4. **Report.** Say what was removed and what stays (on `aca`: the
   environment and its GPU profiles).
````

- [ ] **Step 4: Run the repository check**

Run: `uv run --no-project --with pyyaml python ci/check_repo.py .`
Expected: no output, exit 0

- [ ] **Step 5: Commit**

```bash
git add skills/vot-config skills/vot-serve skills/vot-destroy
git commit -m "feat(skills): vot-config, vot-serve and vot-destroy"
```

---

### Task 7: README, release workflow, changelog config

**Files:**
- Create: `cliff.toml`, `CHANGELOG.md`, `.github/workflows/release.yml`
- Modify: `README.md` (the initial one GitHub created)

**Interfaces:**
- Consumes: `plugin.json` (Task 1).
- Produces: the tag-driven release (spec section 11).

- [ ] **Step 1: Rewrite `README.md`** — sections, one short paragraph or list each: *What it does* (serve a vLLM preset on demand, tear it down, traces over OTLP); *Install* (the repository root is an Agent Plugins plugin: install it through a marketplace that lists it, or try it from a clone with `claude --plugin-dir <path to the clone>` on Claude Code); *Use* (`/vot-config`, `/vot-serve gemma4-12b-qat`, `/vot-destroy gemma4-12b-qat`); *Stacks* (the four types, one line each; `local-vllm` and `local-vllm-docker` marked not yet verified live); *Presets* (builtin list, custom in `.vot/presets/<name>.yaml`, the schema link); *Traces* (`otlp_endpoint`, traces only); *Cost and exposure* (ACA bills while the app exists; its ingress admits the serving machine's public IP only); *License* (MIT).

- [ ] **Step 2: Write `cliff.toml`** — copy oddyssey's `cliff.toml` (`~/Repos/github/oddyssey/cliff.toml`) verbatim: same template, the `@word` backtick preprocessor, the same `commit_parsers` with `^chore\\(release\\)` skipped.

- [ ] **Step 3: Write `CHANGELOG.md`**

```markdown
# Changelog
```

- [ ] **Step 4: Write `.github/workflows/release.yml`** — oddyssey's `release.yml` (`~/Repos/github/oddyssey/.github/workflows/release.yml`) adapted, keeping its `prepare` / `release` split, its comments' rationale, the strict semver gate, the previous-tag range, the PR opened by the App token, the `--match-head-commit` merge, the tag re-point with the ambient token and the idempotent release creation. Differences, exactly:
  - header comment: drop PyPI and marketplace mentions;
  - `prepare`: no `setup-uv`; the bump step is
    ```yaml
          - name: Bump the version in plugin.json
            env:
              VERSION: ${{ steps.version.outputs.version }}
            run: |
              jq --arg v "$VERSION" '.version = $v' plugin.json > plugin.json.tmp
              mv plugin.json.tmp plugin.json
    ```
    no marketplace step; the artifact `path` is `plugin.json` and `CHANGELOG.md`;
  - `release`: no "Clear the generated marketplace tree" step; `add-paths` is `plugin.json` and `CHANGELOG.md`; the backfill check reads the version with
    `TAG_VERSION="$(git show "${BUILD_OID}:plugin.json" | jq -r .version)"`;
  - no `build` and no `publish-pypi` jobs.

- [ ] **Step 5: Validate the workflow syntax**

Run: `uvx check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/release.yml .github/workflows/ci.yml`
Expected: `ok -- validation done`

- [ ] **Step 6: Commit and open the PR**

```bash
git add README.md cliff.toml CHANGELOG.md .github/workflows/release.yml
git commit -m "chore(release): tag-driven release workflow and readme"
git push -u origin chore/skeleton
```

Before the PR: a fresh reviewer sub-agent (most capable model) reviews the whole branch against `main` with the spec as requirement; findings are fixed and the same reviewer re-checks until it returns none. Then open the PR `feat: vllm-on-tap v0.1 plugin - skills, presets, ci and release` against `main` and merge it, each on the maintainer's go; CI `validate` must be green. Tasks 8-9 need this merge: `load-preset` fetches builtin presets and `presets/schema.json` from `main`.

- [ ] **Step 7: Maintainer actions (not automatable here)** — state them to the maintainer and wait:
  - install the `oddyssey-release` GitHub App on `using-system/vllm-on-tap`;
  - add `vars.RELEASE_APP_CLIENT_ID` and `secrets.RELEASE_APP_PRIVATE_KEY` to the repository (same values as oddyssey's);
  - add a `main` ruleset letting the App merge the release PR and the workflow's `GITHUB_TOKEN` force-push `v*` tags.

---

### Task 8: Live acceptance on `local-vllm-metal`

**Files:**
- Modify: `skills/stack-guide/references/local-vllm-metal.md` (only what the live run corrects), `presets/gemma4-12b-qat.yaml` (only if the MLX model id must change)

- [ ] **Step 0: Branch** from the merged `main`: `git fetch origin && git switch -c fix/live-acceptance origin/main` (Tasks 8-9 commit their corrections here).
- [ ] **Step 1: In a scratch repository** (`mkdir -p /tmp/vot-lab && cd /tmp/vot-lab && git init`), with Claude Code started as `claude --plugin-dir ~/Repos/github/vllm-on-tap` (the branch checked out), run `/vot-config`: create `mac`, `local-vllm-metal`, port 8000, no OTLP endpoint. Expected: `.vot/environments/mac.yaml`, `.vot/config.yaml` = `current: mac`, `.gitignore` carries both lines.
- [ ] **Step 2: Review Focus 4** — occupy the port (`python3 -m http.server 8000 &`), run `/vot-serve gemma4-12b-qat`. Expected: refused, port 8000 named. Stop the server.
- [ ] **Step 3: Run `/vot-serve gemma4-12b-qat`.** Expected: ready within 15 min, the printed `curl` returns a chat completion.
- [ ] **Step 4: Review Focus 2** — run `/vot-serve gemma4-12b-qat` again. Expected: asked to destroy first or stop; answer stop; still one process.
- [ ] **Step 5: Traces** — start oddyssey's local stack (`odd_stack_up`), update `mac` with `otlp_endpoint: http://127.0.0.1:4317`, destroy and serve again, send one chat request. Expected: a trace for service `vot-gemma4-12b-qat` in the local Tempo.
- [ ] **Step 6: Run `/vot-destroy gemma4-12b-qat`.** Expected: process gone, `.vot/run/` files removed; a second destroy reports the unit does not exist.
- [ ] **Step 7: Fix the reference with what the run proved wrong, commit**

```bash
git add skills presets
git commit -m "fix(stack-guide): local-vllm-metal verified live"
```

---

### Task 9: Live acceptance on `aca`

**Files:**
- Modify: `skills/stack-guide/references/aca.md` (only what the live run corrects), `presets/gemma4-12b-qat.yaml` (`gpu_memory_gb` to 80 only if fp16 on T4 fails)

- [ ] **Step 1: `/vot-config`** in the scratch repository: create `azure`, `aca`, the maintainer's subscription, `swedencentral`, defaults otherwise. Expected: resource group, environment and both GPU profiles exist (or the quota message), `.vot/environments/azure.yaml` holds names only.
- [ ] **Step 2: Review Focus 3** — `unset VOT_API_KEY`, run `/vot-serve gemma4-12b-qat`. Expected: refused naming `VOT_API_KEY`, no Azure call made.
- [ ] **Step 3: Review Focus 5** — a custom `.vot/presets/huge.yaml` (`name: huge`, `model: google/gemma-4-31B-it`, `gpu_memory_gb: 96`), `/vot-serve huge`. Expected: refused, no profile fits. Remove the file.
- [ ] **Step 4: Review Focus 1** — a custom `.vot/presets/typo.yaml` with `vllm_arg:`, `/vot-serve typo`. Expected: schema error, nothing created. Remove the file.
- [ ] **Step 5: `export VOT_API_KEY=<a random string>`, `/vot-serve gemma4-12b-qat`.** Expected: `gpu-t4`, ready within 30 min, the `curl` with the Bearer header answers; a request without it gets 401; `az containerapp show --name vot-gemma4-12b-qat --resource-group rg-vot --query properties.configuration.ingress.ipSecurityRestrictions` lists the `caller` rule with this machine's IP. If vLLM fails in fp16 on T4, set `gpu_memory_gb: 80` in the preset, destroy, serve again on `gpu-a100`.
- [ ] **Step 6: `/vot-destroy gemma4-12b-qat`.** Expected: the app is gone, the environment remains.
- [ ] **Step 7: Fix the reference, commit**

```bash
git add skills presets
git commit -m "fix(stack-guide): aca verified live"
```

---

### Task 10: Review, PR, merge, first release

- [ ] **Step 1:** Dispatch a fresh reviewer sub-agent (most capable model) over `fix/live-acceptance` against `main`, with the spec as the requirement; fix its findings; the same reviewer re-checks until it returns none.
- [ ] **Step 2:** Push; the PR body lists the live results of Tasks 8–9 and the review outcome. Merge only on the maintainer's go.
- [ ] **Step 3:** On the maintainer's request only: `git tag v0.1.0 && git push origin v0.1.0`; watch `release.yml` open, merge and tag the release PR; confirm `plugin.json` on `main` reads `0.1.0` and the GitHub release exists.
- [ ] **Step 4:** On the maintainer's go, submit `https://github.com/using-system/vllm-on-tap/blob/main/plugin.json` to otelyssey through its plugin submission issue (spec section 12); admission is the reviewer's call.
