---
description:
  Runs the org's self-hosted Renovate bot against just the calling repo — on its own schedule and instantly on dashboard
  or PR checkbox ticks.
---

# `renovate.yaml`

**Reusable Renovate.** Runs the org's self-hosted [Renovate](https://docs.renovatebot.com/) bot against **only the
calling repository**. It uses the same "Renovate" App, the same bot-side config and the same org preset as the org-wide
bot from [`renovate-config`](https://github.com/bitwise-media-group/renovate-config). Each repository gets its own
schedule, and its runs happen in parallel with every other repository's, instead of waiting for one org-wide loop that
grows with each repository.

!!! abstract "At a glance"

    - **Caller triggers:** hourly `schedule`, `workflow_dispatch`, `issues` (`edited`), `pull_request` (`edited`)
    - **Caller grants:** nothing (`permissions: {}`)
    - **Secrets:** `app-private-key` (`RENOVATE_PRIVATE_KEY`)
    - **Org setup:** the "Renovate" App installed on the repo, and the repo excluded from the org-wide bot

## How it works

### Which events run it

| Event                     | Runs when                                                                               |
| ------------------------- | --------------------------------------------------------------------------------------- |
| `schedule`                | always                                                                                  |
| `workflow_dispatch`       | always (forward `dry-run` / `log-level` for a debug run)                                |
| `issues` (`edited`)       | a **human** edited the **body** of the bot's **Dependency Dashboard** issue             |
| `pull_request` (`edited`) | a **human** edited the **body** of a bot-opened PR whose branch starts with `renovate/` |

Ticking a checkbox (rebase/retry this PR, create rate-limited PRs, …) edits the body, so Renovate runs **immediately**
instead of on the next hour. Renovate's own rewrites come from a `Bot` sender and are filtered out, so a run never
triggers the next one. Edits to any other issue or PR skip the job.

### The run

1. Mints an App token scoped to **this repository only**, with the permissions Renovate uses: `contents`, `workflows`,
   `pull-requests`, `issues` and `statuses` as write; `checks`, `administration` and `vulnerability-alerts` as read.
2. Checks out the **config repository** (`config-repository@config-ref`) into `renovate-config/` and passes
   `config-file` to Renovate unchanged. A policy change there reaches every repository on its next run.
3. Restores Renovate's **repository cache** and hands it to the container's uid `12021`.
4. Runs [`renovatebot/github-action`](https://github.com/renovatebot/github-action) with `RENOVATE_AUTODISCOVER=false`
   and `RENOVATE_REPOSITORIES=<this repo>`. Environment variables override the config file, so the run is pinned to the
   caller.
5. Returns the cache to the runner user and **saves it only on `schedule` / `workflow_dispatch`**. An `issues` run gets
   a read-only cache token, and a `pull_request` run would save under the PR's ref, where later runs can't restore it.

Runs are serialised per repository (`renovate-<repo>`, queued, never cancelled), because parallel runs would race on
branch pushes and automerge.

### The merge model

This is the org bot's model, unchanged. Commits go through the GitHub API, so they show as **Verified** and satisfy the
required-signatures ruleset. The App is a bypass actor on the pull-request ruleset, so Renovate squash-merges its own
green, in-policy PRs. Renovate automerges **at most one PR per base branch per run**, so the hourly cron also sets merge
throughput. Updates it won't automerge (majors, `0.x`) get the `auto-merge` label and go through
[`merge.yaml`](merge.md#renovate-prs-are-squashed-not-fast-forwarded) once approved.

## Requirements

- The **"Renovate" GitHub App** installed on the repository, exposed as the org variable `RENOVATE_CLIENT_ID` and secret
  `RENOVATE_PRIVATE_KEY`. See [GitHub Apps & secrets](../setup/apps.md#renovate).
- The repository **removed from the org-wide bot**: excluded in its `autodiscoverFilter`, or that loop retired. Two bots
  on one repository race on branches and automerge.
- A **public** config repository. The token is scoped to the caller, and it can read only public repositories beyond
  that.

## Interface

--8<-- "build/workflow-docs/renovate/interface.md"

## Permissions

--8<-- "build/workflow-docs/renovate/permissions.md"

## Caller

```yaml title=".github/workflows/renovate.yaml"
--8<-- "examples/renovate.yaml"
```

The `pull_request` (`edited`) trigger leaves a skipped job on every PR body edit that isn't a Renovate checkbox. That's
the cost of reacting to the checkbox at all.

## Jobs and pinned actions

--8<-- "build/workflow-docs/renovate/jobs.md"

--8<-- "build/workflow-docs/renovate/actions.md"

## Troubleshooting

Ticking a checkbox doesn't start a run : Check that the caller has the `issues` / `pull_request` `edited` triggers.
Edits by bots and edits that don't change the body (title, labels) are ignored on purpose.

`cache write denied` : Non-scheduled runs can't write the cache, which is why the save step only runs on `schedule` and
`workflow_dispatch`. The cache catches up on the next scheduled run.

Two Renovate PRs for the same update : The org-wide bot is still processing this repository. Exclude it from
`autodiscoverFilter`.

A dry run : Dispatch the workflow with `dry-run: full` and `log-level: debug` to log what Renovate would do without
writing anything.
