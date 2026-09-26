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
   skill's *OpenAI API* `curl` filled in (on `aca`, with the reference's
   `<auth header>`, which fetches the key from the app - never print the
   key); on `aca`, repeat that billing runs until `/vot-destroy <preset>`.
