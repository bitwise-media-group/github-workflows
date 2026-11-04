---
description:
  Signature-preserving fast-forward merge — /merge now, or /auto-merge once approved and green — with a GitHub App
  token.
---

# `merge.yaml`

**Reusable Merge.** Merges pull requests by **fast-forward**, so the commit objects on `main` are the ones the author
signed. GitHub's merge button rewrites them. Two flows share one workflow:

- **`/merge`**: a maintainer comments on an approved, green PR and it merges **now**.
- **`/auto-merge`** (or the `auto-merge` label): arms the PR so it merges **as soon as** it is approved and every
  required check is green.

Both run [`bitwise-media-group/ff-merge`](https://github.com/bitwise-media-group/ff-merge) with a short-lived "FF Merge"
App token. ff-merge checks write access, approval, all checks and a genuine fast-forward again before it moves the ref.

!!! abstract "At a glance"

    - **Caller triggers:** `issue_comment` (`created`), `workflow_run` (`completed`) for your CI workflows plus
      `Merge Review Ack`, and an hourly `schedule`
    - **Caller grants:** nothing (`permissions: {}`). The App token does the work.
    - **Secrets:** `app-private-key` (`FF_MERGE_PRIVATE_KEY`)
    - **Companion:** [`merge-review-ack.yaml`](merge-review-ack.md) is required for auto-merge on approval

The whole system, including why it avoids PR-attached events, is explained in
[Fast-forward merging](../concepts/fast-forward-merge.md).

## How it works

Each trigger is routed to exactly one job by `github.event_name` (inside a reusable workflow, `github.event` is the
caller's event):

| Event                                                   | Job                          | Does                                                                         |
| ------------------------------------------------------- | ---------------------------- | ---------------------------------------------------------------------------- |
| `issue_comment` = `/merge` from an org member           | `manual`                     | merge now (`require-approval`, `maintainer-only` per inputs)                 |
| `issue_comment` = `/auto-merge` from an org member      | `arm`                        | add the label, post a confirmation, try a merge (best effort)                |
| `workflow_run` completed **successfully** from a PR run | `merge-on-checks`            | resolve the branch's open PR, attempt the merge if armed                     |
| `workflow_run` completed **successfully** from a review | `merge-on-review-completed`  | the same, triggered by [`Merge Review Ack`](merge-review-ack.md) on approval |
| `schedule`                                              | `sweep-prep` → `sweep-merge` | list every armed open PR and attempt each one, one at a time                 |

Details that matter:

- **Comment gating.** `/merge` and `/auto-merge` act only on an exact comment body from an `OWNER`, `MEMBER` or
  `COLLABORATOR`. This only filters noise before a token is minted. ff-merge checks write access again itself.
- **The label is the armed state.** A `/auto-merge` comment is ephemeral, so the `arm` job adds the `auto-merge` label
  (creating it if needed), and every automatic path passes `require-label`. Remove the label to cancel. A label added by
  hand also arms the PR, but there is no `labeled` trigger, so it merges on the next `workflow_run` or sweep.
- **Automatic paths always require approval.** `require-approval: true` and `maintainer-only: false` are fixed on `arm`,
  `merge-on-checks`, `merge-on-review-completed` and the sweep. The inputs only change `/merge`.
- **Declines don't fail runs.** Automatic attempts use `continue-on-error`. "Not approved yet" or "checks pending" is
  normal, and the next event retries.
- **One ref move at a time.** Every job shares the concurrency group `ff-merge-<repo>` (queued, never cancelled), and
  the sweep matrix runs with `max-parallel: 1`.
- **Least-privilege tokens.** Each job mints a token with only what ff-merge needs: `contents`, `pull-requests`,
  `issues` (closing linked issues) and `workflows` (moving a ref whose commits touch workflow files) as write; `checks`
  and `statuses` as read; and `administration: read` only for `/merge`'s maintainer check. The sweep's list step reads
  pull requests only.

### Renovate PRs are squashed, not fast-forwarded

Renovate never rebases its branches onto the base (`rebaseWhen: conflicted`), so they are almost never fast-forwardable.
For authors in `squash-authors` (default `bitwise-renovate[bot]`), ff-merge **squash-merges via the API** instead. That
needs only a conflict-free branch and produces a GitHub-signed (`web-flow`) commit that satisfies the
required-signatures ruleset. The org Renovate preset arms the updates it doesn't automerge itself (majors, `0.x`) with
the `auto-merge` label, so a breaking-change PR merges as soon as a human approves it.

## Requirements

- The **"FF Merge" GitHub App** installed on the repository and listed as a **bypass actor** on `main`'s ruleset, with
  the org variable `FF_MERGE_CLIENT_ID` and secret `FF_MERGE_PRIVATE_KEY`. See
  [GitHub Apps & secrets](../setup/apps.md#ff-merge).
- **Branch protection that requires a review**, so an approval sets the PR's review decision.
- **[`merge-review-ack.yaml`](merge-review-ack.md)** installed, with `Merge Review Ack` in the caller's
  `workflow_run.workflows` list.
- Every required workflow listed in `workflow_run.workflows` **by its `name:`**. The last one to finish triggers the
  attempt, and ff-merge checks the full status rollup.

A `/merge`-only repository can trigger on `issue_comment` alone and skip the review-ack companion.

## Interface

--8<-- "build/workflow-docs/merge/interface.md"

## Permissions

--8<-- "build/workflow-docs/merge/permissions.md"

## Caller

```yaml title=".github/workflows/merge.yaml"
--8<-- "examples/merge.yaml"
```

## Jobs and pinned actions

--8<-- "build/workflow-docs/merge/jobs.md"

--8<-- "build/workflow-docs/merge/actions.md"

## Troubleshooting

`/merge` does nothing : The comment must be **exactly** the command, from an org owner, member or collaborator, on a
pull request (not an issue).

ff-merge reports "not fast-forwardable" : Rebase the branch onto the base, re-sign, and push. CI re-runs and an armed PR
retries automatically.

An armed PR is approved and green but hasn't merged : Check that `Merge Review Ack` and every CI workflow are listed in
the caller's `workflow_run.workflows`, using the workflows' **names**. The hourly sweep is the backstop.

The release PR only merges on the hour : The release PR was pushed with `GITHUB_TOKEN`, which emits no `workflow_run`
events. Pass the FF Merge App to [`release.yaml`](release.md#requirements).

Merging a PR that edits `.github/workflows/` is refused : The App needs the **Workflows** permission on its
installation. The token asks for `workflows: write`, but can't exceed what the installation was granted.
