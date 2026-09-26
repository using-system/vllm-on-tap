---
description: Cut a vllm-on-tap release - inspect the last pushed tag, pick the bump (patch, minor, or major), then tag and push; the tag push starts the whole release pipeline
---

Cut a vllm-on-tap release. Pushing the version tag IS the release order:
the release workflow then bumps the files for exactly that version,
opens the release PR, waits for its CI, merges it, re-points the tag at
the merge commit, and creates the GitHub release.

- Arguments: $ARGUMENTS
- Expected fields (optional, free-form): the bump to apply (`patch`,
  `minor`, `major`) or an exact version (`1.8.0`). When present, skip
  the question in step 3 - the confirmation in step 4 still applies.

Steps:

1. **Preflight** - all of these must hold; stop naming the failing one
   otherwise:
   - `git fetch origin --tags --force` first, so tags and main are
     current;
   - the working tree is clean and the current branch is `main`, in
     sync with `origin/main` (not ahead, not behind);
   - read the latest version tag:
     `git tag -l 'v*' --sort=-v:refname | head -1` (no tag at all =
     first release, treat the base as v0.0.0 and say so - the first
     release is `0.1.0`, and the plugin stays in `0.x` until
     `local-vllm-metal` and `aca` are verified live);
   - check the latest tag's release run
     (`gh run list --workflow release.yml --limit 1`): if it FAILED,
     do not offer a new version - guide the recovery instead (fix
     main, then "Re-run all jobs" on that run - never a partial
     re-run, which would reuse a stale prepare artifact - or delete
     and re-push the tag). There is no environment gate on this
     workflow, so no WAITING run to route anywhere.

2. **Show what would ship**: the last tag, then
   `git log --oneline <last-tag>..origin/main`. Derive the
   recommendation from the conventional commit types: any `feat` -
   minor; else patch. Major is NEVER derived or preselected - a
   breaking release is always the user's explicit call. When a
   breaking marker (`!`) appears in the log, surface it as evidence
   that major may be warranted and let the user choose it themselves.

3. **Ask which bump to release** (unless the arguments already said):
   compute the three candidate versions from the last tag and offer
   patch / minor / major with the recommendation first, each option
   showing its resulting `vX.Y.Z`. An exact version given as argument
   must be strict `X.Y.Z` AND greater than the last tag - reject
   anything else (the workflow only gates the shape; monotonicity is
   this command's job).

4. **Confirm before firing**: show verbatim the two commands about to
   run -
   `git tag vX.Y.Z` and `git push origin vX.Y.Z` -
   and state plainly that the push starts the whole release pipeline
   (release PR, CI, auto-merge, tag re-point, GitHub release). Only on
   explicit confirmation, run both commands.

5. **Watch the run to completion**: name the tag pushed and the
   release run, then poll `gh run view <run-id> --json status,conclusion`
   (every ~20 s, in the background when possible) until the status is
   no longer `queued`/`in_progress`:
   - `completed` + `failure` - report which job failed with its log
     pointer and the step-1 recovery guidance; stop;
   - `completed` + `success` - verify: the GitHub release `vX.Y.Z`
     exists WITH notes (`gh release view vX.Y.Z`; never header-only),
     and
     `git fetch origin && git show origin/main:plugin.json | jq -r .version`
     prints `X.Y.Z`.
