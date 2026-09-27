---
name: stack-guide
description: How vllm-on-tap runs vLLM on each stack type, supported or planned - one reference per type with its prerequisites, config fields, serve, readiness, destroy and traps. Read the current stack type's reference only.
---

# stack-guide

One reference per stack type in `references/<stack type>.md`. Read only the
current environment's type. The stack type `aca` of an earlier version is
`azure`: read it as `azure`, and write `azure` on the next write of the
environment.

A planned type's reference only says it is planned and has none of the
sections below - tell the user the type is not supported
in this version, and stop.

Every supported reference has these sections, in this order:

- **Prerequisites and install** - the tools the type needs, how to check
  them, and each one's official install command (run only on the user's yes).
- **Config fields** - the `config` keys of an environment of this type, with defaults.
- **Prepare** - what `/vot-config` creates once (optional).
- **Serve** - numbered checks, run in their written order and stopping at the first refusal (the "already served" one leads to the destroy-or-stop question), then the exact command that starts unit `vot-<preset>`.
- **API key** - how requests authenticate and where the key is read from
  (optional).
- **Ready when** - the readiness check and its time bound; poll across
  several bounded tool calls (each under the host's tool-call limit, e.g.
  5 min), never one long loop.
- **Destroy** - the exact command that removes unit `vot-<preset>`.
- **Traps** - one line each.

Common prerequisite (every type): `uvx --version` succeeds - install
`brew install uv` or the official script
https://docs.astral.sh/uv/getting-started/installation/ (on the user's yes).

Placeholders used in the references: `<preset>` (the preset name),
`<model>`, `<served name>`, `<vllm args>` (the merged `vllm_args` rendered
as `--flag value`, `true` as `--flag`, `false` omitted; on a shell command
line each value is single-quoted, `--flag '<value>'`, and in a JSON array
each value is a JSON-encoded string, so a JSON value such as
`{"method":"mtp"}` passes intact; a `'` inside a value is written `'\''`
in both cases, since a reference's JSON array may itself be single-quoted
in the shell), `<port>` and the
other `config` fields by their key, plus the placeholders a reference
defines itself. `[...]` marks a
part included only when its condition applies, without the brackets.

Tracing (every type): when the environment has `otlp_endpoint`, or the
reference's *Serve* checks resolved one, add
`--otlp-traces-endpoint <otlp_endpoint>` to `<vllm args>` and set
`OTEL_SERVICE_NAME=vot-<preset>` and
`OTEL_RESOURCE_ATTRIBUTES=<resource attributes>` in vLLM's environment,
where `<resource attributes>` is
`vot.preset=<preset>,vot.model=<model>,vot.stack=<stack type>`, each
value percent-encoded outside `A-Za-z0-9._~/-` (`<model>` after the
preset's per-stack override).
For an OTLP/HTTP
endpoint (port 4318 or a `/v1/traces` path) also set
`OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf` and pass the full URL
ending in `/v1/traces`, appending that path when the environment's value
lacks it (vllm-guide's *Traces over OTLP*).

Preset environment (every type): each name in the preset's `env` must be
exported in the user's shell (`printenv <NAME>` prints a value) - refuse
naming the missing one - and is passed to vLLM by name, never by value in a
file or on a command line.
