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

Preset environment (every type): each name in the preset's `env` must be
exported in the user's shell (`printenv <NAME>` prints a value) - refuse
naming the missing one - and is passed to vLLM by name, never by value in a
file or on a command line.
