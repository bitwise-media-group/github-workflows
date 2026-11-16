---
description: Every reusable workflow in the library, with its required inputs, secrets and caller permissions.
---

# Catalogue

Every reusable workflow lives in
[`.github/workflows/`](https://github.com/bitwise-media-group/github-workflows/tree/main/.github/workflows) and triggers
only on `workflow_call`. The `self-*` files beside them are this repository's own callers, which
[dogfood](../reference/maintaining.md#dogfooding) the library. Every external action is pinned to a full commit SHA, and
Renovate keeps those pins current.

| Workflow                                       | What it does                                                                                                                                                                                   |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`ci.yaml`](ci.md)                             | Runs the repo's `lint`, `build`, `test` and `docs-build` mise tasks as parallel jobs, verifies a committed `dist/`, uploads to Codecov                                                         |
| [`security.yaml`](security.md)                 | CodeQL over `actions`, plus `go` and `javascript-typescript` when detected; zizmor when the repo opts in                                                                                       |
| [`release.yaml`](release.md)                   | release-please, then the `release` task (GoReleaser, signed, notarized, attested, or any build + registry publish) and/or a Zensical docs deploy (per release or per push), then floating tags |
| [`merge.yaml`](merge.md)                       | Signature-preserving fast-forward merge: `/merge` now, or `/auto-merge` once approved and green                                                                                                |
| [`merge-review-ack.yaml`](merge-review-ack.md) | Companion to `merge.yaml` that turns an approving review into a merge attempt, fork PRs included                                                                                               |
| [`merge-notice.yaml`](merge-notice.md)         | Posts a one-time "this repo merges via `/merge`" comment on new PRs                                                                                                                            |
| [`add-to-project.yaml`](add-to-project.md)     | Adds new issues to the org's Projects v2 Roadmap board with a GitHub App token                                                                                                                 |
| [`renovate.yaml`](renovate.md)                 | Runs the org's Renovate bot against just this repo: on its schedule, checkbox ticks, and as soon as its PRs go green                                                                           |

## At a glance

Generated from the workflow files at build time:

--8<-- "build/workflow-docs/index.md"

"Caller grants" is the union of every job's permissions. GitHub requires the caller to grant all of it, even for jobs
that end up skipped. See [Permissions & tokens](../concepts/permissions.md).

## Platform

Every workflow runs on `ubuntu-latest` by default, and each takes a `runs-on` input to change that. None needs a macOS
or Windows runner, including [macOS notarization](../setup/macos-notarization.md), which GoReleaser's embedded quill
does from Linux. A repository whose tasks need macOS itself (a Swift package built against AVFoundation or AppKit)
passes `runs-on: macos-latest` to `ci.yaml`, `security.yaml` and `release.yaml`.

| Runner                       | Where it works                                                                                                                                                     |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Linux x64 (`ubuntu-latest`)  | everywhere: the default                                                                                                                                            |
| macOS arm64 (`macos-latest`) | every job except `renovate.yaml` and `security.yaml`'s `zizmor` (both run Docker containers); no image builds (a root `Dockerfile`) in `ci.yaml` or `release.yaml` |
| Linux arm64                  | every job a Linux x64 runner runs, provided `mise.lock` pins linux-arm64 (the shared toolchain's does)                                                             |
| Intel macOS                  | the jobs that install no mise, such as the `merge*`, `add-to-project`, `release-please` and `vanity-tags` jobs                                                     |
| Windows                      | only `add-to-project.yaml` and `merge-review-ack.yaml`; every other job has bash `run:` steps                                                                      |

Each `jdx/mise-action` step pins the mise version and verifies the binary for the runner's platform against the
release's signed packslip, so one step serves every runner. What limits the platform is `mise.lock`: tools install with
`--locked`, so a platform needs lock entries. The shared toolchain's lock covers linux-x64, linux-arm64 and macos-arm64,
which is why Intel macOS can't run the mise jobs. The `zizmor` job ignores `runs-on` and stays on `ubuntu-latest`.
`renovate.yaml` honours it but needs a Linux runner with Docker, such as a self-hosted ARC runner.
