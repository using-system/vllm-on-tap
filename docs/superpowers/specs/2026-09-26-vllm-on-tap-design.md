# vllm-on-tap — design

Date: 2026-09-26. Status: approved section by section in conversation; this
document is the written spec to review before the implementation plan.

## 1. Purpose

vllm-on-tap is an agent plugin that serves a vLLM **preset** on an
**environment** and tears it down again, from three commands a coding agent
runs: configure an environment, serve a preset, destroy it. Building and
destroying is meant to be cheap and repeatable — "vLLM on tap".

Success for v1: a builtin Gemma 4 preset configured, served, answering one
chat request and destroyed, end to end, on `local-vllm-metal`
(`gemma4-e4b-qat`) and on `aca` (`gemma4-12b-qat`), with its traces seen in
an OTLP collector at least once.

Out of scope for v1: an image registry (ACR), a model-weight cache, metrics
export, an OpenTelemetry Collector of our own, several replicas or
autoscaling, any engine other than vLLM.

## 2. Principles

- **Agent Plugins native, no APM.** The repository root is the plugin:
  `plugin.json` in the Agent Plugins 1.0.0 format and `skills/`. The
  Agent Plugins spec keeps commands, agents and hooks outside its portable
  v1 format (spec 1.0.0, "commands, hooks, agents, rules, and LSP servers
  … are outside the v1 format"), so every command is a skill.
- **No agent, no MCP server, no scripts.** The work is sequential and
  conversational; the CLIs (`vllm`, `docker`, `az`) do it. The guides state
  the exact commands; the model runs them.
- **A command routes to a guide and restates none of it.** A command skill
  names the guide and the section to read; the command lines live in the
  guide, once.
- **No secret is ever written.** Environments and presets hold resource
  names and environment-variable names, never a value. Access goes through
  `az login` and environment variables.
- **English only** in every committed file.

## 3. Repository layout

```
vllm-on-tap/
├── plugin.json
├── skills/
│   ├── vot-config/SKILL.md
│   ├── vot-serve/SKILL.md
│   ├── vot-destroy/SKILL.md
│   ├── stack-guide/
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── local-vllm.md
│   │       ├── local-vllm-metal.md
│   │       ├── local-vllm-docker.md
│   │       └── aca.md
│   ├── load-preset/SKILL.md
│   └── vllm-guide/SKILL.md
├── presets/
│   ├── schema.json
│   ├── gemma4-12b-qat.yaml
│   ├── gemma4-e4b-qat.yaml
│   └── gemma4-e2b-qat.yaml
├── .github/workflows/
│   ├── ci.yml
│   └── release.yml
├── cliff.toml
├── CHANGELOG.md
├── README.md
└── LICENSE            # MIT
```

`plugin.json`:

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

The user's repository carries the plugin's state under `.vot/`:

| Path | Committed | Content |
|---|---|---|
| `.vot/environments/<name>.yaml` | yes | one environment (section 5) |
| `.vot/presets/<name>.yaml` | yes | a custom preset (section 4) |
| `.vot/config.yaml` | no (gitignored) | `current: <environment name>` |
| `.vot/run/` | no (gitignored) | local run state: `vot-<preset>.pid`, `vot-<preset>.log` |

`/vot-config` adds the two gitignored paths to the repository's `.gitignore`
the first time it writes `.vot/`.

## 4. Presets

A preset states what vLLM serves, never where or how it is hosted: no image,
region, port or resource name.

```yaml
name: gemma4-e4b-qat
description: Gemma 4 E4B instruction-tuned (4.5B effective parameters), Google's QAT 4-bit weights (compressed-tensors, w4a16); MLX 4-bit on local-vllm-metal
model: google/gemma-4-E4B-it-qat-w4a16-ct
served_model_name: gemma4-e4b
gpu_memory_gb: 16
vllm_args:
  --max-model-len: 16384
  --gpu-memory-utilization: 0.90
env: []
stacks:
  local-vllm-metal:
    model: mlx-community/gemma-4-e4b-it-4bit
    vllm_args:
      --language-model-only: true
```

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | the preset's name; equals the file name without `.yaml` |
| `description` | no | one line |
| `model` | yes | Hugging Face repository id served by vLLM |
| `served_model_name` | no | the name clients send in the OpenAI API `model` field; defaults to `name` |
| `gpu_memory_gb` | no | the smallest GPU memory the preset runs on |
| `vllm_args` | no | flags passed as-is to `vllm serve`, one per key; a `true` value is a bare flag |
| `env` | no | names of environment variables the preset needs (`HF_TOKEN` for a gated model) |
| `stacks.<stack type>` | no | per stack type, overrides of `model`, `vllm_args` (merged key by key) and `gpu_memory_gb` only |

`presets/schema.json` (JSON Schema) states this table; CI validates every
builtin preset against it and `load-preset` validates a custom one against
it before use.

**Resolution** (`load-preset`): `.vot/presets/<name>.yaml` first — a custom
preset shadows a builtin of the same name — then
`https://raw.githubusercontent.com/using-system/vllm-on-tap/main/presets/<name>.yaml`.
A name found in neither lists the presets available on both sides. The
stack type's `stacks.<type>` block is merged into the preset after
resolution.

**Gemma 4 12B QAT notes.** The weights are not gated (Apache-2.0), so the
preset needs no token. vllm-metal runs MLX weights, hence the
`local-vllm-metal` overrides of the E2B and E4B presets; the 12B MLX
checkpoint generates garbage under vllm-metal 0.30.0, so the 12B preset
is NVIDIA-only.

## 5. Environments

```yaml
name: azure-sweden
stack: aca
otlp_endpoint: https://otel.example.com:4317
config:
  subscription: <subscription name>
  location: swedencentral
  resource_group: rg-vot
  environment: vot-env
  api_key_env: VOT_API_KEY
```

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | the environment's name; equals the file name without `.yaml` |
| `stack` | yes | `local-vllm`, `local-vllm-metal`, `local-vllm-docker` or `aca` |
| `otlp_endpoint` | no | when set, vLLM exports its traces there (section 7) |
| `config` | yes | the stack type's fields, listed by its reference |

`config` per stack type:

| Stack type | Fields |
|---|---|
| `local-vllm` | `port` (default 8000) |
| `local-vllm-metal` | `port` (default 8000) |
| `local-vllm-docker` | `port` (default 8000), `image` (optional, overrides the pinned image) |
| `aca` | `subscription`, `location`, `resource_group`, `environment`, `api_key_env` (default `VOT_API_KEY`), `image` (optional) |

## 6. Commands

### `/vot-config`

1. Lists the environments in `.vot/environments/` and offers: create one,
   update one, or make one current.
2. On create, asks the stack type and reads that type's reference in
   `stack-guide`.
3. Checks the type's tools; when one is missing, shows its official install
   command and runs it only on the user's yes. Never installs silently;
   never runs `az login` for the user.
4. Asks the `config` fields, with the defaults above.
5. `aca` only — prepares what is slow and durable so that serving only
   creates the app: the resource group, the Container Apps environment and
   its serverless A100 GPU workload profile (`gpu-a100`). Each resource is
   reused when it exists, created on the user's yes otherwise. A missing GPU
   quota is reported with the way to request it, and does not block saving
   the environment.
6. Asks `otlp_endpoint` (optional). On `aca`, warns when it names
   `localhost` or a private address the container cannot reach.
7. Writes the file, makes the environment current, prints a summary.

### `/vot-serve <preset>`

1. Reads the current environment (none → routes to `/vot-config`).
2. Resolves the preset through `load-preset` and merges `stacks.<type>`.
   Without a preset name, lists the available presets.
3. Reads the stack's reference.
4. Checks that `vot-<preset>` does not exist yet; when it does, offers to
   destroy it first or to keep it and stop.
5. Starts vLLM (section 8), adding the tracing flags when the environment
   has an `otlp_endpoint` (section 7).
6. Waits until `GET /v1/models` lists the `served_model_name`, within the
   stack reference's time bound; on timeout, shows the last log lines and
   leaves the unit in place for the user to inspect or destroy.
7. Prints the endpoint and a ready-to-paste `curl` chat request; on `aca`,
   states that billing runs until `/vot-destroy`.

### `/vot-destroy <preset>`

1. Reads the current environment and the stack's reference.
2. Destroys the unit `vot-<preset>` (section 8). A unit that does not exist
   is reported, not an error.

## 7. Traces over OTLP

Traces only: vLLM exports OTLP traces natively (`--otlp-traces-endpoint`);
its metrics are a Prometheus `/metrics` endpoint with no OTLP export
(vllm-project/vllm#30252, closed not planned), and v1 adds no collector.

When the environment has `otlp_endpoint`, `/vot-serve` passes
`--otlp-traces-endpoint <otlp_endpoint>`. vLLM defaults to gRPC; when the
endpoint is OTLP/HTTP (port 4318 or a `/v1/traces` path), it also sets
`OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf` and passes the full URL
ending in `/v1/traces` (vLLM hands the value to the exporter verbatim),
appending the path when the environment's value lacks it. `OTEL_SERVICE_NAME` is
set to `vot-<preset>`. The flags and their prerequisites (the OpenTelemetry
packages in the local install) are `vllm-guide`'s.

## 8. Stacks

A served preset is one unit named `vot-<preset>`: a process, a container or
a Container App. Destroy finds it by that name.

| Stack | Serve | Destroy |
|---|---|---|
| `local-vllm` | `vllm serve <model> --host 127.0.0.1 --port <port> --served-model-name <name> <vllm_args>` in the background; PID in `.vot/run/vot-<preset>.pid`, output in `.vot/run/vot-<preset>.log` | stop the PID, remove its `.vot/run/` files |
| `local-vllm-metal` | the same with vllm-metal's `vllm` and the MLX model | the same |
| `local-vllm-docker` | `docker run -d --name vot-<preset> --gpus all --ipc=host -p 127.0.0.1:<port>:8000 -v ~/.cache/huggingface:/root/.cache/huggingface <image> --model <model> …` | `docker rm -f vot-<preset>` |
| `aca` | `az containerapp create --name vot-<preset> --yaml` in the environment (the YAML carries vLLM's flags, which `--args` cannot): the pinned `vllm/vllm-openai` image pulled from Docker Hub, the `gpu-a100` serverless profile (a preset needing more than 80 GB is refused), external ingress on port 8000 restricted to the caller's public IP, one fixed replica (min = max = 1), the API key stored as a Container App secret and passed to vLLM as `VLLM_API_KEY` | `az containerapp delete --name vot-<preset> --yes`; the Container Apps environment and its GPU profiles stay |

Decisions carried by this table:

- **No ACR** in v1: `aca` pulls `vllm/vllm-openai` from Docker Hub.
- **No weight cache**: weights download from Hugging Face at each start;
  `HF_TOKEN` is passed only when the preset lists it.
- **One fixed replica on ACA**, no scale-to-zero: a cold start (image and
  weights) outlasts an HTTP request's timeout, so a first request after
  scale-to-zero would fail. Billing runs while the app exists.
- **An API key and an IP restriction on ACA**: the ingress is public. The
  key's value comes from the variable named by `api_key_env`; it is never
  written to a file. vLLM's key covers `/v1`, `/v2`, `/inference` and
  `/cohere` only (other routes such as `/invocations` stay open), so the
  ingress also admits only the serving machine's public IP.
- **Local stacks listen on 127.0.0.1 only**, with no key.
- **Image pins**: the docker and aca references pin `vllm/vllm-openai` to
  the vLLM release current at implementation (v0.30.0 on 2026-09-26); an
  environment's `image` overrides it.

## 9. Skills

**`stack-guide`** — `SKILL.md` states the contract every reference follows,
one section each, in this order: *Prerequisites and install*, *Config
fields*, *Prepare* (`aca` only), *Serve*, *Ready when*, *Destroy*, *Traps*.
A reference is a list: each command with its whole flag surface, one line
per trap, no prose explaining a command.

**`load-preset`** — the preset format and its schema, the resolution order,
the `stacks.<type>` merge, the validation, and the list of builtin presets.

**`vllm-guide`** — the vLLM capabilities a preset or a serve needs:
`--max-model-len`, `--gpu-memory-utilization`, quantization,
`--tensor-parallel-size`, `--dtype`, `--api-key`, tracing
(`--otlp-traces-endpoint`, the protocol variable, the OpenTelemetry
packages), and the OpenAI-compatible API (`/v1/models`,
`/v1/chat/completions`) — each entry linked to vLLM's documentation.

**`vot-config`, `vot-serve`, `vot-destroy`** — the steps of section 6, each
routing to the guide and section it needs.

## 10. Verification

CI (`ci.yml`, on pull requests and pushes to `main`), all actions pinned by
commit SHA:

- `plugin.json` validates against the Agent Plugins 1.0.0 schema;
- every `presets/*.yaml` validates against `presets/schema.json`, and its
  `name` equals its file name;
- every `skills/*/SKILL.md` has a frontmatter with `name` (equal to its
  directory) and `description`.

Live acceptance (section 1) on `local-vllm-metal` and `aca`. `local-vllm`
and `local-vllm-docker` need a Linux machine with an NVIDIA GPU; until one
runs them, their references are written from vLLM's documentation and
marked "not yet verified live" at their top.

## 11. Versioning and release

Tag-driven, the oddyssey way, adapted:

1. Pushing a strict `vX.Y.Z` tag is the release order (`release.yml`,
   `on: push: tags: ["v*"]`, one release at a time).
2. Job `prepare`, holding no secret: derives the version from the tag
   (strict semver gate), regenerates `CHANGELOG.md` with git-cliff for that
   version, sets `plugin.json`'s `version`, and hands the changed files on
   as an artifact.
3. Job `release`, the only one holding the App token and running no project
   code: opens the release PR as the **oddyssey-release** GitHub App
   (installed on this repository; `vars.RELEASE_APP_CLIENT_ID`,
   `secrets.RELEASE_APP_PRIVATE_KEY`), so CI runs on it; waits for its
   checks; squash-merges it; re-points the tag at the merge commit; creates
   the GitHub release with the changelog section as notes.

`plugin.json`'s version on `main` is therefore always the released one,
which is what a marketplace following the plugin (otelyssey) reads.
The first release is `v0.1.0`; the plugin stays in `0.x` until `aca` and
`local-vllm-metal` are verified live. PR titles follow Conventional Commits
(they are the changelog). No release is cut without the maintainer's
request. The `main` ruleset must let the App merge the release PR and the
workflow's `GITHUB_TOKEN` re-point the tag — a ruleset change the
maintainer makes.

## 12. Listing

Once `v0.1.0` is out and verified, the plugin is submitted to otelyssey
through its submission issue (its relevance rests on the OTLP trace export,
`instrumentation`; admission is the reviewer's call, not assumed), and to
the external lists the maintainer chooses.
