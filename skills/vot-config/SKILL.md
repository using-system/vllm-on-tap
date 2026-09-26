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
