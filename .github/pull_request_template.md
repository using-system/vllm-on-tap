<!-- PR title = the squash commit = the release note.
     Conventional Commits required - the rules live in AGENTS.md and CONTRIBUTING.md. -->

## What


## Why


## How to test


## Checklist

- [ ] References an existing issue (`Closes #N` above - open the issue first when none exists)
- [ ] PR title follows Conventional Commits (it becomes the squash commit and drives the version)
- [ ] No `!` / breaking marker (or it was explicitly discussed first)
- [ ] The CI checks pass locally (tests, plugin.json and presets schemas, repository check)
- [ ] A change to what a stack runs was verified live (configure, serve, a chat request, destroy) - or the PR says why not
- [ ] A builtin preset change updates the builtin table of `skills/load-preset/SKILL.md`
- [ ] A separate reviewer sub-agent reviewed the branch; its outcome is recorded below
- [ ] No secrets or real identifiers in the diff (API keys, tokens, subscription names - by variable name or placeholder only)
