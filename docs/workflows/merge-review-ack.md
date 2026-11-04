---
description:
  Companion to merge.yaml that turns an approving review into a base-context merge attempt, for fork and same-repo PRs
  alike.
---

# `merge-review-ack.yaml`

**Reusable Merge Review Ack.** The required companion to [`merge.yaml`](merge.md). Its only job is to **complete
successfully when a PR is approved**. That completion fires `merge.yaml`'s `workflow_run` trigger in the base
repository, where the App token can be minted and the merge attempted.

!!! abstract "At a glance"

    - **Caller triggers:** `pull_request_review` (`submitted`)
    - **Caller grants:** nothing (`permissions: {}`)
    - **Secrets:** none
    - **Caller name must be:** `Merge Review Ack`, the name `merge.yaml`'s caller lists in `workflow_run.workflows`

## Why it exists

An approval only arrives as the `pull_request_review` event, and that event has two problems for `merge.yaml`:

1. It **attaches a check run to the PR**. Subscribing `merge.yaml` to it would leave a list of skipped merge jobs on
   every PR.
2. On a **fork PR** it carries **no secrets**, so it could never mint the App token.

Instead, this tiny workflow listens for the review. Its single `ack` job runs only when
`github.event.review.state == 'approved'`. Any other review leaves the run `skipped`, which `merge.yaml` ignores. When
it completes, `merge.yaml`'s `merge-on-review-completed` job runs from `workflow_run` in base context, with secrets, and
asks ff-merge to merge.

So fork and same-repo PRs behave the same way, including the case where the approval is the **last** thing to happen
because CI was already green. The `ack` job is the **only** check the merge system adds to a PR. It does nothing
privileged: ff-merge still checks approval, every check, the arming label and a genuine fast-forward again.

See [Fast-forward merging](../concepts/fast-forward-merge.md) for the full event flow.

## Requirements

- [`merge.yaml`](merge.md) installed, with `Merge Review Ack` in its caller's `workflow_run.workflows`.
- The caller workflow named exactly `Merge Review Ack`, or the `workflow_run` list updated to match.

## Interface

--8<-- "build/workflow-docs/merge-review-ack/interface.md"

## Permissions

--8<-- "build/workflow-docs/merge-review-ack/permissions.md"

## Caller

```yaml title=".github/workflows/merge-review-ack.yaml"
--8<-- "examples/merge-review-ack.yaml"
```

## Jobs and pinned actions

--8<-- "build/workflow-docs/merge-review-ack/jobs.md"

--8<-- "build/workflow-docs/merge-review-ack/actions.md"
