---
description: Posts a one-time comment on new PRs explaining that the repository merges by fast-forward via /merge.
---

# `merge-notice.yaml`

**Reusable Merge Notice.** Posts one comment when a pull request opens, explaining that the repository merges by
**fast-forward**: a maintainer comments `/merge`, the merge button isn't used, and the branch must be rebased and
re-signed if it falls behind. It's optional, but it saves first-time contributors from guessing.

!!! abstract "At a glance"

    - **Caller triggers:** `pull_request_target` (`opened`)
    - **Caller grants:** `pull-requests: write`
    - **Secrets:** none. It comments with the run's `GITHUB_TOKEN`.

## How it works

The single `notice` job runs `gh pr comment` with a fixed Markdown note:

!!! note "Merging this PR"

    This repository merges by **fast-forward** so every commit keeps its original signature. The GitHub merge button is
    not used. Once this PR is approved and all checks pass, a maintainer merges it by commenting **`/merge`** on the PR.

    The branch must be up to date with `main` (rebased and re-signed) to fast-forward. If `/merge` reports it is not
    fast-forwardable, rebase onto `main` and comment `/merge` again.

### Why `pull_request_target` is safe here

`pull_request_target` runs in the base repository's context, so the notice also reaches **fork** PRs, where it's most
useful. That trigger is risky when a workflow checks out or runs PR code. This one does neither: it doesn't check out
anything, doesn't interpolate PR-controlled text, and posts a static comment with a token limited to
`pull-requests: write`. The callers carry a `zizmor: ignore[dangerous-triggers]` comment that records this reasoning.

## Requirements

None beyond the caller. Pair it with [`merge.yaml`](merge.md). The notice describes the `/merge` convention, so it only
makes sense where that flow is installed.

## Interface

--8<-- "build/workflow-docs/merge-notice/interface.md"

## Permissions

--8<-- "build/workflow-docs/merge-notice/permissions.md"

## Caller

```yaml title=".github/workflows/merge-notice.yaml"
--8<-- "examples/merge-notice.yaml"
```

## Jobs and pinned actions

--8<-- "build/workflow-docs/merge-notice/jobs.md"

--8<-- "build/workflow-docs/merge-notice/actions.md"
