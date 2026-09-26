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

The repository root is the plugin. Install it through a marketplace that
lists it, or try it straight from a clone:

```
claude --plugin-dir <path to the clone>
```

## Use

- `/vot-config` - create or switch the current environment (which stack,
  where, how to reach it).
- `/vot-serve <preset>` - serve a preset on the current environment.
- `/vot-destroy <preset>` - tear it down again.

## Stacks

An environment targets one stack:

- `local-vllm` - a background `vllm serve` process on this machine.
- `local-vllm-metal` - the same, through vLLM's Apple Silicon (MLX) build.
- `local-vllm-docker` - a `vllm/vllm-openai` container on this machine.
- `azure` - an Azure Container Apps environment in which each serve
  provisions a Container App with a serverless GPU, on demand, and each
  destroy removes it. An optional storage account caches the Hugging Face
  model weights and vLLM's compiled graphs, so a preset's later serves
  start faster.

Planned, not supported in this version yet:

- `kubernetes` - vLLM served through KServe on a cluster with GPU nodes,
  on premises or in the cloud (AKS, EKS, GKE...), through a `kubectl`
  already configured for it.
- `aws` - an Amazon ECS service on GPU instances, with EFS as the cache.
- `gcp` - a Google Cloud Run service with a GPU, with a Cloud Storage
  volume as the cache.

## Presets

A preset names a model and its `vllm serve` flags, not where it runs. The
builtin presets live in [`presets/`](presets/); `/vot-serve` with no
argument lists them. Add your own under `.vot/presets/<name>.yaml`,
validated against [`presets/schema.json`](presets/schema.json); a custom
preset of the same name shadows the builtin one.

## Traces

vLLM exports traces (not metrics) over OTLP. Set `otlp_endpoint` on an
environment and every preset served on it exports its request traces
there.

## Cost and exposure

On `azure`, the Container App bills for as long as it exists - there is no
scale-to-zero, so `/vot-destroy` is how the billing stops. Its ingress is
public but restricted to the serving machine's public IP, and requests
must carry an API key that `/vot-serve` generates and stores as the app's
secret - nothing to export beforehand; the `curl` it prints reads the key
back with `az`.

## License

[MIT](LICENSE)
