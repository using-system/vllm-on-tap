# Security Policy

## Supported versions

Only the latest released version of vllm-on-tap receives security fixes.

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Use
GitHub's private vulnerability reporting:
[Report a vulnerability](https://github.com/using-system/vllm-on-tap/security/advisories/new).

You can expect an acknowledgement within a few days. Relevant scope:

- the skills a coding agent executes on the user's machine and cloud
  account (a command that could leak a secret, run something unintended,
  or leave a billed resource behind);
- the exposure of a served model on `azure` (the API key and the ingress
  restriction to the caller's IP);
- the release pipeline (the GitHub App token and the release workflow).

A served endpoint's own vulnerabilities belong to
[vLLM](https://github.com/vllm-project/vllm/security) or the model's
publisher.
