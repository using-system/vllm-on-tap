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
