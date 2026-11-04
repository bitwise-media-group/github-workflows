---
description: How caller permissions, job permissions and GitHub App tokens fit together across the library.
---

# Permissions & tokens

## The caller sets the ceiling

A reusable workflow can never have more access than the caller grants. GitHub works out a reusable workflow's
permissions **when the run starts**, as the **union of every job's `permissions:`**, and it **ignores `if:`** while
doing so. Two things follow:

- The caller must grant every scope that any job declares, including jobs that will be skipped. `release.yaml` is the
  usual example: a repository with no `.goreleaser.yaml` must still grant `id-token`, `attestations`,
  `artifact-metadata` and `packages`.
- Missing a scope doesn't fail a single job. It fails the **whole run at startup** (`startup_failure`), with no jobs
  created and no re-run button.

Each workflow page shows the exact grant, generated from the workflow file. The
[catalogue](../workflows/index.md#at-a-glance) lists them side by side.

## Least privilege inside

Every reusable workflow sets `permissions: {}` at the top and grants each **job** only what it uses. When a job runs, it
receives its own narrower grant, not the caller's whole ceiling. In `release.yaml`, for example, the `release-please`
job never holds `id-token: write` even though the caller grants it.

## GitHub App tokens

Some work can't be done with `GITHUB_TOKEN` at all:

| Need                                                        | Why `GITHUB_TOKEN` can't                                              | App          |
| ----------------------------------------------------------- | --------------------------------------------------------------------- | ------------ |
| move `main` past branch protection, preserving signatures   | it isn't a ruleset bypass actor                                       | FF Merge     |
| trigger `workflow_run` automation from a release PR push    | GitHub suppresses events from `GITHUB_TOKEN` pushes (recursion guard) | FF Merge     |
| push a Homebrew cask to another repository                  | it's scoped to the current repository                                 | FF Merge     |
| write an organisation Projects v2 board                     | it has no organisation-project scope                                  | Project Sync |
| run Renovate with verified API commits and automerge bypass | it's short-lived per run and isn't a bypass actor                     | Renovate     |

These workflows mint a **short-lived installation token** with
[`actions/create-github-app-token`](https://github.com/actions/create-github-app-token) inside the job that needs it:

- **Down-scoped:** each mint requests only the `permission-*` scopes that step uses. `merge.yaml`'s sweep lister, for
  example, asks only for `pull-requests: read`.
- **Narrowed to repositories** where that makes sense: the Homebrew tap token covers only the tap, and the Renovate
  token covers only the calling repository.
- **Expires within the hour** and is revoked when the job ends. There is no PAT to rotate or to expire mid-release.

Because the App token does the privileged work, the callers of `merge.yaml`, `merge-review-ack.yaml`,
`add-to-project.yaml` and `renovate.yaml` grant **nothing** (`permissions: {}`).

## Naming convention

Every App-backed workflow takes the same names:

- input **`app-client-id`** ← an org **variable** (`vars.<APP>_CLIENT_ID`)
- secret **`app-private-key`** ← an org **secret** (`secrets.<APP>_PRIVATE_KEY`)

Older callers in the organisation may still use `client-id` / `app-key` or `app-id` / `FF_APP_ID`. Rename them when
moving them onto these workflows. The org setup for each App is in [GitHub Apps & secrets](../setup/apps.md).
