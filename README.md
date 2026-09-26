# vllm-on-tap

An [Agent Plugins](https://agent-plugins.org) plugin that serves a vLLM
model preset on demand and tears it down again - locally, on Apple
Silicon, in Docker, or on Azure Container Apps serverless GPUs. Configure
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
- `/vot-serve gemma4-12b-qat` - serve a preset on the current environment.
- `/vot-destroy gemma4-12b-qat` - tear it down again.

## Stacks

An environment targets one of four stacks:

- `local-vllm` - a background `vllm serve` process on this machine.
- `local-vllm-metal` - the same, through vLLM's Apple Silicon (MLX) build.
- `local-vllm-docker` - a `vllm/vllm-openai` container on this machine.
- `aca` - an Azure Container App with a serverless GPU workload profile.

None of the four stacks is verified live yet. `local-vllm` and
`local-vllm-docker` also need a Linux machine with an NVIDIA GPU;
`local-vllm-metal` and `aca` are verified as Tasks 8 and 9 land.

## Presets

A preset names a model and its `vllm serve` flags, not where it runs. The
builtin preset is `gemma4-12b-qat` (Gemma 4 12B, Google's QAT 4-bit
weights). Add your own under `.vot/presets/<name>.yaml`, validated against
[`presets/schema.json`](presets/schema.json); a custom preset of the same
name shadows the builtin one.

## Traces

vLLM exports traces (not metrics) over OTLP. Set `otlp_endpoint` on an
environment and every preset served on it exports its request traces
there.

## Cost and exposure

On `aca`, the Container App bills for as long as it exists - there is no
scale-to-zero, so `/vot-destroy` is how the billing stops. Its ingress is
public but restricted to the serving machine's public IP, and requests
must carry the API key from the environment variable it names (default
`VOT_API_KEY`).

## License

[MIT](LICENSE)
