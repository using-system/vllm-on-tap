# Contributing to vllm-on-tap

Thanks for helping make vLLM presets easy to serve and tear down.
Issues, preset additions, stack fixes and docs are all welcome.

## Contributing with a coding agent

This project is built for coding agents, and contributing through one is
the expected path. Agents read [AGENTS.md](AGENTS.md): it carries the
working conventions (branches, Conventional Commits, an issue per PR),
the CI checks to run before a PR, the reviewer sub-agent, and the
English-only and no-secrets rules. Point your agent at the repository
root so it picks the file up, and review what it produced before
pushing: **you remain responsible for everything your agent commits,
opens or comments under your name.**

## The two-minute orientation

The repository root is an [Agent Plugins](https://agent-plugins.org/)
plugin:

| Where | What |
| --- | --- |
| `plugin.json` | The plugin manifest (Agent Plugins 1.0.0). Its `version` is set by the release workflow. |
| `skills/` | The product: the `vot-config`, `vot-serve` and `vot-destroy` commands, and the guides they route to (`stack-guide` with one reference per stack, `load-preset`, `vllm-guide`). Markdown a coding agent executes - a wording change is a behavior change. |
| `presets/` | The builtin presets and their `schema.json`. |
| `tests/`, `.github/scripts/` | The repository check CI runs, and its tests. |
| `.vot/environments/` | The repository's own environments (`azure` on the `azure` stack, `mac` on `local-vllm-metal`), so a live run of a change starts from `/vot-serve`. No real identifier: `azure` uses the logged-in `az` subscription. |
| `docs/superpowers/` | The design spec and the implementation plan of v0.1 - the design record. |

## Building and testing

What CI runs, from the repository root (`.github/workflows/ci.yml` is
canonical if they ever disagree):

```bash
uv run --no-project --with pytest --with pyyaml pytest -q tests
uvx check-jsonschema --schemafile https://agent-plugins.org/schemas/1.0.0/plugin.schema.json plugin.json
uvx check-jsonschema --schemafile presets/schema.json presets/*.yaml
uv run --no-project --with pyyaml python .github/scripts/check_repo.py .
```

## Pull requests

- **Every PR references an existing issue** (`Closes #N` in the body);
  open the issue first when none exists. When the implementation
  deviates from the issue, record each amended choice as a comment on
  the issue before opening the PR.
- **The PR title is the release note.** We squash-merge with the PR
  title as the commit message, and versions follow
  [Conventional Commits](https://www.conventionalcommits.org/): `feat:`
  -> minor, `fix:`/others -> patch. Use
  `type(scope): lowercase imperative description`.
- **Never add a `!` or `BREAKING CHANGE` marker** without discussing it
  first: it triggers a major release.
- **A change to what a stack runs is verified live** (configure, serve,
  a chat request, destroy) before its PR, or the PR says it was not.
- CI must be green. One logical change per PR.

## Issues

Use the issue forms (bug / feature): the bug form's confirmed-vs-observed
status is the house style. Questions and open ideas belong in
[Discussions](https://github.com/using-system/vllm-on-tap/discussions).

## Security

Vulnerabilities go through
[private reporting](https://github.com/using-system/vllm-on-tap/security/advisories/new),
never a public issue; scope and expectations are in
[SECURITY.md](SECURITY.md). Never paste an API key, a token or a real
subscription identifier into an issue, a PR or a committed `.vot/`
example.

## Trying your changes end to end

Load your working copy into a coding agent in a scratch repository -
for example `claude --plugin-dir /path/to/your/clone` - then run
`/vot-config`, `/vot-serve <preset>` and `/vot-destroy <preset>` on the
stack you changed. A cloud stack bills while a preset is served: destroy
it as soon as the run is over.
