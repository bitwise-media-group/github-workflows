---
description: Every reusable workflow in the library, with its required inputs, secrets and caller permissions.
---

# Catalogue

Every reusable workflow lives in
[`.github/workflows/`](https://github.com/bitwise-media-group/github-workflows/tree/main/.github/workflows) and triggers
only on `workflow_call`. The `self-*` files beside them are this repository's own callers, which
[dogfood](../reference/maintaining.md#dogfooding) the library. Every external action is pinned to a full commit SHA, and
Renovate keeps those pins current.

| Workflow                                       | What it does                                                                                                             |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| [`ci.yaml`](ci.md)                             | Runs the repo's `lint`, `build` and `test` mise tasks as parallel jobs, verifies a committed `dist/`, uploads to Codecov |
| [`security.yaml`](security.md)                 | CodeQL over `actions`, plus `go` and `javascript-typescript` when detected; zizmor when the repo opts in                 |
| [`release.yaml`](release.md)                   | release-please, then GoReleaser (signed, notarized, attested) and/or a Zensical docs deploy, then floating tags          |
| [`merge.yaml`](merge.md)                       | Signature-preserving fast-forward merge: `/merge` now, or `/auto-merge` once approved and green                          |
| [`merge-review-ack.yaml`](merge-review-ack.md) | Companion to `merge.yaml` that turns an approving review into a merge attempt, fork PRs included                         |
| [`merge-notice.yaml`](merge-notice.md)         | Posts a one-time "this repo merges via `/merge`" comment on new PRs                                                      |
| [`add-to-project.yaml`](add-to-project.md)     | Adds new issues to the org's Projects v2 Roadmap board with a GitHub App token                                           |
| [`renovate.yaml`](renovate.md)                 | Runs the org's Renovate bot against just this repo, on its own schedule and on dashboard checkbox ticks                  |

## At a glance

Generated from the workflow files at build time:

--8<-- "build/workflow-docs/index.md"

"Caller grants" is the union of every job's permissions. GitHub requires the caller to grant all of it, even for jobs
that end up skipped. See [Permissions & tokens](../concepts/permissions.md).

## Platform

Every workflow runs on `ubuntu-latest`. None needs a macOS or Windows runner, including
[macOS notarization](../setup/macos-notarization.md), which GoReleaser's embedded quill does from Linux.
