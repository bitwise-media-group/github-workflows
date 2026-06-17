# Security Policy

## Reporting a vulnerability

Please report vulnerabilities privately via
[GitHub Security Advisories](https://github.com/bitwise-media-group/github-workflows/security/advisories/new). Do not
open public issues for security reports.

## Threat model (summary)

This repository is the organisation's central library of **reusable workflows** (`on: workflow_call`). Each workflow is
invoked by a thin caller in a consumer repository that owns the trigger and grants the permissions; the reusable
workflow then runs inside the caller's `GITHUB_TOKEN` and secrets context. The library author cannot see or constrain
how a consumer wires the caller's trigger, so the workflows are written to be safe regardless of the calling context.
They defend against:

- **Untrusted code execution in a privileged context** — the release pipelines check out a release-please-computed tag
  and run build code (`goreleaser`, `npm run all`). GitHub Actions has no way for a reusable workflow to declare which
  trigger events may call it, so the privileged checkout-and-build jobs are gated on a positive allowlist of trusted
  triggers (`push`, `workflow_dispatch`, `schedule`). Anything else — the fork-controllable `pull_request_target`,
  `issue_comment`, and `workflow_run`, or any new event type GitHub adds later — is skipped, so the "pwn request" path
  fails closed rather than relying on the consumer wiring their caller correctly.
- **Supply-chain tampering via third-party actions** — every external action is pinned to a full commit SHA with a
  human-readable version comment, so a moved or re-pointed tag cannot change what runs.
- **Excess privilege** — workflows declare `permissions: {}` at the top level and grant the minimum scopes per job, so a
  compromised step has only the access that job needs.
- **Secret leakage across the call boundary** — secrets are passed explicitly through `workflow_call.secrets` (no
  `secrets: inherit`), and `run:` steps pass interpolated values through quoted environment variables rather than
  inlining them into the script, avoiding expression-injection.

Out of scope: a compromise of the GitHub Actions runner executing a workflow; a compromise of a consumer repository's
own secrets, PATs, or branch protections; and the trust placed in first-party `bitwise-media-group` actions referenced
by these workflows (e.g. `ff-merge`), whose own repositories are the trust anchor.

## Code scanning triage

CodeQL findings are triaged in [`security/code-scanning/index.md`](security/code-scanning/index.md), with a report per
finding recording why it was dismissed or how it was remediated.
