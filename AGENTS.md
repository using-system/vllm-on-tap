# AGENTS.md

## Working conventions

Never commit on the default branch: branch first, named
`type/short-description` (`fix/azure-readiness`, `docs/presets-guide`).
Commit messages, PR titles and issue titles all follow
[Conventional Commits](https://www.conventionalcommits.org/) —
`type(scope): lowercase imperative description`. The PR title becomes the
squash commit and the changelog line, and drives the version (`feat:` →
minor, `fix:`/others → patch): **never add a `!` or `BREAKING CHANGE`
marker without discussing it first** — it triggers a major release. One
logical change per PR. **Every PR references an existing issue**
(`Closes #N` in the body): the issue carries the problem and its
discussion, the PR carries the change; open the issue first when none
exists. When the implementation deviates from what the issue specified,
record each amended choice as a comment on that issue — what changed and
why — before opening the PR.

## English only

Every committed artifact is written in English, whatever language the
conversation uses: skills, presets, docs, code, comments, commit messages,
PR and issue text, labels.

## No secrets, anywhere

Never write tokens, API keys, credentials or connection strings into
anything committed or published: skills, presets, `.vot/` examples,
issues, PR text. Refer to access material by environment-variable name
only (`VOT_API_KEY`, `HF_TOKEN`); a secret's value never appears in a
file, a command line or the conversation. The same holds for real
identifiers copied from a live system — subscription, tenant and resource
names or GUIDs, account names, public IPs: replace them with an obviously
fake placeholder (`<subscription name>`, `Contoso`, `203.0.113.7`) before
writing them down, including in a bug repro or a log excerpt.

## Run what CI runs before a PR

Before opening or updating a PR, run what `.github/workflows/ci.yml` runs
(the workflow is canonical if this list ever drifts):

- `uv run --no-project --with pytest --with pyyaml pytest -q tests`
- `uvx check-jsonschema --schemafile https://agent-plugins.org/schemas/1.0.0/plugin.schema.json plugin.json`
- `uvx check-jsonschema --schemafile presets/schema.json presets/*.yaml`
- `uv run --no-project --with pyyaml python .github/scripts/check_repo.py .`

A change to a workflow also validates it:
`uvx check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/*.yml`.

## A separate reviewer sub-agent checks the branch before its PR

No branch reaches a PR on its author's judgment alone. Before a PR is
opened, and again before every push that updates one, the coding agent
that made the change dispatches a **separate reviewer sub-agent** — a
fresh context on the most capable model the host offers, never the author
re-reading its own diff — over the branch's whole diff against `main`,
with the issue it closes as the spec. Each round of fixes goes back to
the **same reviewer** until it returns no finding. The PR body records
what the review found and what changed for it. The review never replaces
the CI checks above, nor the **explicit go** of the maintainer: the push,
the PR and the merge each wait for it, and a go with a question attached
is not a go.

## Verified live means verified live

A stack reference or a preset is "verified" only after a real run on that
stack: configure, serve, one chat request answered, destroy. Until then
the reference says so at its top ("Not yet verified live") and the README
does not claim otherwise. A change that alters what a stack runs —
a command, a flag, an image, a GPU profile — is re-verified live before
its PR, or its PR states that it was not.

## Cloud runs cost money

A serve on a cloud stack starts a billed GPU. Start one only on the
maintainer's go, and destroy it as soon as the run it was started for is
over — a crash loop keeps billing, so a failed start is destroyed too.
Durable resources (a resource group, a Container Apps environment) are
created by `/vot-config` and removed only by the maintainer.

## The README is user documentation

`README.md` explains what the plugin does and how to use it — never how a
stack runs inside, and never a list that grows with the content: it names
no preset and restates no stack command. The commands live in the skills,
once; the README points at them.

## Builtin presets

A preset is data: the model, its `vllm serve` flags, and per-stack
overrides. Adding or changing a builtin preset under `presets/` updates
the builtin table of `skills/load-preset/SKILL.md` in the same change and
nothing else. What depends on a model belongs in its preset, never in a
stack reference.

## Releases only on request

A release is cut by the maintainer's `/publish` command, only when the
maintainer asks for it — never on an agent's own initiative.

## Title and label every issue

Issue titles follow Conventional Commits, like commit messages and PR
titles (`feat(azure): ...`, `fix(stack-guide): ...`, `docs(readme): ...`).
Every issue gets a type label (`bug`, `enhancement`, `documentation`);
add the stack's label when it concerns one stack (`azure`,
`local-vllm-metal`, ... — create it when missing). When closing an issue
as not planned, add the `wontfix` label and close with a comment stating
why.
