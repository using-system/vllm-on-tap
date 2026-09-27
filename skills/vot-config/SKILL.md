---
name: vot-config
description: Create, update or select a vllm-on-tap environment - its stack type (local-vllm, local-vllm-metal, local-vllm-docker, azure), its config and its optional OTLP traces endpoint - checking and offering to install the tools it needs, and on azure preparing the resource group, the Container Apps environment, its GPU profiles and an optional cache storage account. Use when the user wants to configure where presets are served.
---

# /vot-config

State lives in the user's repository under `.vot/`:
`.vot/environments/<name>.yaml` (committed) and `.vot/config.yaml`
(`current: <name>`, gitignored). Never write a secret into either.

1. **Gitignore.** Ensure the repository's `.gitignore` contains
   `.vot/config.yaml` and `.vot/run/`, appending whichever is missing
   (every run, idempotent).
2. **Choose.** List `.vot/environments/*.yaml` (name, stack) and the current
   one; offer: create one, update one, or make one current (then go to step 8).
   A `stack: aca` is the earlier name of `azure`: use `azure`. An environment
   of a planned stack type (`kubernetes`, `aws`, `gcp`) cannot be updated or
   made current: say it is not supported in this version.
3. **Stack type.** On create: ask the name and the stack type
   (`local-vllm`, `local-vllm-metal`, `local-vllm-docker`, `azure`; `kubernetes`,
   `aws` and `gcp` are listed as planned, not selectable - a user who names
   one is told it is not supported in this version and asked again). Read
   the stack-guide skill's reference for that type.
4. **Tools.** Run stack-guide's common prerequisite check plus that
   reference's *Prerequisites and install* checks. For a missing tool, show
   its install command and run it only on the user's yes; what is the
   user's (a driver, `az login`) is stated, never done.
5. **Config.** Ask the reference's *Config fields*, showing the defaults.
6. **Prepare.** When the reference has a *Prepare* section, run it.
7. **Traces.** When the reference's *Config fields* say the config gives
   the traces endpoint, `otlp_endpoint` is neither asked nor written, and
   dropped when present. Otherwise ask `otlp_endpoint` (optional, empty to
   skip); on `azure`, warn when it names `localhost` or a private address.
8. **Write.** On create or update, write `.vot/environments/<name>.yaml`:

   ```yaml
   name: <name>
   stack: <stack type>
   otlp_endpoint: <url>        # omitted when empty
   config:
     <field>: <value>
   ```

   Always, including make-current: write `.vot/config.yaml` with
   `current: <name>`, and print a summary: the environment, its stack, its
   config, whether traces are exported (and where).
