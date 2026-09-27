# vllm-on-tap

An [Agent Plugins](https://agent-plugins.org) plugin that serves a vLLM
model preset on demand and tears it down again - locally (Linux, Apple
Silicon or Docker) or on Azure Container Apps serverless GPUs, with
Kubernetes (KServe), AWS (ECS) and GCP (Cloud Run) planned. Configure
an environment once, then serve and destroy any preset in it from two
commands. vLLM on tap.

## What it does

Serves a vLLM preset - a named model and its `vllm serve` flags - on a
configured environment, waits until it answers OpenAI-compatible chat
requests, and tears it down again on request. When the environment names
an OTLP endpoint, the served vLLM exports its request traces there.

## Install

vllm-on-tap is listed in the [otelyssey marketplace](https://github.com/using-system/otelyssey/blob/main/marketplace/vllm-on-tap/README.md),
which gives the install commands for each agent CLI (Claude Code, GitHub
Copilot CLI, Codex CLI...).

## Use

- `/vot-config` - create or switch the current environment (which stack,
  where, how to reach it).
- `/vot-serve <preset>` - serve a preset on the current environment.
- `/vot-destroy <preset>` - tear it down again.
- `/vot-instrument-preset <request>` - create or edit a custom preset.

## Stacks

An environment targets one stack:

- `local-vllm` - a background `vllm serve` process on this machine.
- `local-vllm-metal` - the same, through vLLM's Apple Silicon (MLX) build.
- `local-vllm-docker` - a `vllm/vllm-openai` container on this machine.
- `azure` - a serverless GPU Container App per serve, in a resource group
  where vllm-on-tap creates or discovers the Container Apps environment, an
  optional storage that caches the model weights, and an optional
  OpenTelemetry Collector that sends the traces to Application Insights.

Planned, not supported in this version yet:

- `kubernetes` - vLLM served through KServe on a cluster with GPU nodes,
  on premises or in the cloud (AKS, EKS, GKE...), through a `kubectl`
  already configured for it.
- `aws` - an Amazon ECS service on GPU instances, with EFS as the cache.
- `gcp` - a Google Cloud Run service with a GPU, with a Cloud Storage
  volume as the cache.

## Presets

A preset names a model and its `vllm serve` flags, not where it runs. The
builtin presets in [`presets/`](presets/) are few and only examples;
`/vot-serve` with no argument lists them. For your own needs, write a
custom preset with `/vot-instrument-preset`: it lands in
`.vot/presets/<name>.yaml`, validated against
[`presets/schema.json`](presets/schema.json), and shadows a builtin preset
of the same name.

## Traces

vLLM exports traces (not metrics) over OTLP. Set `otlp_endpoint` on an
environment and every preset served on it exports its request traces
there.

## License

[MIT](LICENSE)
