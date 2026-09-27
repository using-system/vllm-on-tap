---
name: vot-instrument-preset
description: Create or edit a vllm-on-tap custom preset in .vot/presets/ from a free-form request - a model of interest, a Hugging Face link, a GPU, a constraint. Use when the user wants a preset written or changed; the argument is the request.
---

# /vot-instrument-preset <request>

Write or update `.vot/presets/<name>.yaml` so it serves what the user asks
for. The format, the resolution and the validation are the load-preset
skill's; the `vllm serve` flags are the vllm-guide skill's. Read both, then
work it out from the request and the model's Hugging Face page.

- Write only under `.vot/presets/`; builtin presets are never edited here.
  Editing a builtin means a custom copy of the same name, which shadows it.
- The preset validates against the schema before you finish.
