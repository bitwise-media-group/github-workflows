# github-workflows

Reusable [GitHub Actions workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows) for Bitwise
Media Group repositories. Each consuming repo keeps a thin **caller** workflow that owns its triggers and calls one of
these by `uses:`, so CI, CodeQL, release, and the fast-forward `/merge` flow live in one place instead of being
copy-pasted per repo.

Copy a caller from [`examples/`](examples/) into your repo's `.github/workflows/`, then pin it (see
[Pinning](#pinning)).

## Catalog

All reusable workflows live in [`.github/workflows/`](.github/workflows/) and are `workflow_call`-only. Every external
action is pinned to a full commit SHA; the org Renovate bot
([`bitwise-media-group/renovate-config`](https://github.com/bitwise-media-group/renovate-config)) keeps the pins fresh.

| Workflow                                         | Platform | What it does                                                                                                              |
| ------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------- |
| [`ci.yaml`](#ciyaml)                             | any      | canonical mise tasks (lint/build/test) per job, committed `dist/` verified, toolchains by detection, Codecov upload       |
| [`security.yaml`](#securityyaml)                 | any      | CodeQL over actions + go (autobuild) + javascript-typescript, language matrix by detection                                |
| [`release.yaml`](#releaseyaml)                   | any      | release-please (two-pass) → GoReleaser (if `.goreleaser.yaml`) + Zensical docs to Pages (if `zensical.toml`); vanity tags |
| [`merge.yaml`](#mergeyaml)                       | any      | signature-preserving fast-forward merge — `/merge` now, or `/auto-merge` (comment/label) when approved + green            |
| [`merge-review-ack.yaml`](#merge-review-ackyaml) | any      | companion to `merge.yaml` — lets fork PRs auto-merge promptly when approved after CI is green                             |
| [`merge-notice.yaml`](#merge-noticeyaml)         | any      | posts a one-time "this repo merges via `/merge`" comment on new PRs                                                       |
| [`dependabot-merge.yaml`](#dependabot-mergeyaml) | any      | auto-approves Dependabot minor/patch PRs and squash-merges them once CI is green                                          |
| [`dependabot-dist.yaml`](#dependabot-distyaml)   | node     | rebuilds committed `dist/` on a Dependabot PR when a bundled-dep bump made CI's dist check go red                         |
| [`add-to-project.yaml`](#add-to-projectyaml)     | any      | adds newly opened issues to a shared org Projects v2 board via a "Project Sync" App token                                 |
| [`update-tools.yaml`](#update-toolsyaml)         | any      | daily `mise lock --bump` under a release cooldown; version bumps land as one reviewed `fix(deps):` PR                     |

Each workflow below lists its inputs, secrets, and the permission ceiling the **caller** must grant — a reusable
workflow's jobs cannot exceed the permissions of the job that calls them. The snippet is the minimal caller; follow the
link beneath it for the fully-commented version.

### `ci.yaml`

_Any repo._ Runs the canonical mise tasks — `lint`, `build`, `test` — as one parallel job each, sets up only the
toolchains the repo has (a root `go.mod` → Go, `package.json` → Node), and uploads coverage to Codecov from a job
isolated from PR-built code. Tasks the repo does not define are skipped; a repo with no mise config at all fails. A repo
that commits its build output has its `dist/` verified up to date after `mise run build` (so a stale committed artifact
fails the PR). An opt-in `e2e` job runs `mise run e2e`. A caller may add product-specific jobs (e.g. `integration`)
alongside the `ci` job.

- **Inputs:** `go-version-file` (default `go.mod`), `node-version-file` (default `.node-version`),
  `cache-dependency-path` (default `go.sum`; newline-separated lockfiles to key the module cache on), `e2e` (default
  `false`).
- **Secrets:** none.
- **Permissions (caller grants):** `contents: read`.

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: ["main", "releases/*"]
permissions:
  contents: read
jobs:
  ci:
    uses: bitwise-media-group/github-workflows/.github/workflows/ci.yaml@v2
```

Full example: [`examples/ci.yaml`](examples/ci.yaml).

### `security.yaml`

_Any repo._ CodeQL analysis whose language matrix is detected at the repo root: `actions` (build-free) always, plus `go`
(via `autobuild`; `setup-go` matches `go-version-file`) when a root `go.mod` exists and `javascript-typescript`
(build-free) when `package.json` exists.

- **Inputs:** `go-version-file` (default `go.mod`), `config-file` (optional, default none; pass
  `./.github/codeql/codeql-config.yaml`, copy [`examples/codeql-config.yaml`](examples/codeql-config.yaml), to exclude a
  bundled `dist/`).
- **Secrets:** none.
- **Permissions (caller grants):** `security-events: write`, `packages: read`, `actions: read`, `contents: read`.

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: ["main", "releases/*"]
  schedule:
    - cron: "28 20 * * 4"
permissions:
  security-events: write
  packages: read
  actions: read
  contents: read
jobs:
  analyze:
    uses: bitwise-media-group/github-workflows/.github/workflows/security.yaml@v2
```

Full example: [`examples/security.yaml`](examples/security.yaml).

### `release.yaml`

_Any repo._ Runs release-please (two-pass), then branches by detection: a repo with a `.goreleaser.yaml` runs GoReleaser
(archives, checksums, SBOMs, cosign signatures, optional Homebrew cask, SLSA attestation); every other repo's release is
just the release-please cut. A repo with a `zensical.toml` also rebuilds its Zensical docs site
(`uv run zensical build`) and publishes it to GitHub Pages — gated on an actual release and keyed off config presence
exactly like the GoReleaser path, so it is independent of GoReleaser (a repo can ship binaries and docs from one
release). With `vanity-tags: true` it also moves the floating major and minor tags (`v1` and `v1.1`). A committed
`dist/` is verified for freshness in [`ci.yaml`](#ciyaml) on every PR, not at release time.

- **Inputs:** `go-version-file` (default `go.mod`), `vanity-tags` (default `false`; move the floating `v1` / `v1.1` tags
  — set it for Actions/reusable repos whose consumers pin `@v1`), `app-client-id` (optional; author the release as a
  GitHub App rather than `GITHUB_TOKEN` — `vars.FF_MERGE_CLIENT_ID`).
- **Secrets:** `homebrew-tap-token` — optional; only needed if `.goreleaser.yaml` publishes a Homebrew cask to another
  repo (`secrets.HOMEBREW_TAP_GITHUB_TOKEN`). `app-private-key` — optional; required only when `app-client-id` is set
  (`secrets.FF_MERGE_PRIVATE_KEY`).
- **Auto-merging release PRs:** set `app-client-id` + `app-private-key` (reuse the "FF Merge" App) so release-please
  authors the release PR as the App. A release PR whose branch is pushed by the default `GITHUB_TOKEN` does **not** emit
  `workflow_run` events — GitHub's recursion guard suppresses them — so [`merge.yaml`](#mergeyaml)'s auto-merge, which
  is keyed on `workflow_run`, never retriggers when its checks go green and the PR only lands on the hourly sweep.
  Authoring as the App restores the trigger. Skip both inputs if you don't auto-merge release PRs.
- **Publishing docs:** add a `zensical.toml` (plus `pyproject.toml` + `uv.lock`) at the repo root and set **Settings →
  Pages → Source → GitHub Actions**. On each release the `docs` job runs `uv run zensical build` and deploys `./site` to
  Pages. It renders `docs/` only — no language build — so a repo whose docs embed generated reference (e.g. a CLI/man
  dump) must commit that output. Nothing to configure beyond the file and the Pages source.
- **Permissions (caller grants):** `contents: write`, `issues: write`, `pull-requests: write`, `id-token: write`,
  `attestations: write`, `artifact-metadata: write`, `pages: write`. Grant all seven even without a `.goreleaser.yaml`
  or `zensical.toml`: GitHub resolves a reusable workflow's permissions as the union of every job and ignores `if:`, so
  the skipped GoReleaser job's `id-token` / `attestations` / `artifact-metadata` and the docs job's `pages` are still
  required or the run fails at startup.

```yaml
on:
  push:
    branches: [main]
permissions:
  contents: write
  issues: write
  pull-requests: write
  id-token: write # cosign keyless signing + docs Pages OIDC deploy
  attestations: write # github build-provenance attestation
  artifact-metadata: write # artifact storage record for the attestation
  pages: write # publish docs to GitHub Pages (when a zensical.toml exists)
jobs:
  release:
    uses: bitwise-media-group/github-workflows/.github/workflows/release.yaml@v2
    with:
      vanity-tags: true # for Actions/reusable repos pinned @v1
    secrets:
      homebrew-tap-token: ${{ secrets.HOMEBREW_TAP_GITHUB_TOKEN }} # optional
```

Full example: [`examples/release.yaml`](examples/release.yaml).

### `merge.yaml`

_Any repo._ Signature-preserving fast-forward merge — the manual `/merge` and the set-and-forget auto-merge in one
workflow. `/merge` merges an approved, green PR now; arming auto-merge (a `/auto-merge` comment or the `auto-merge`
label) fast-forwards it automatically the moment it is approved and every required check is green. Both run the same
`ff-merge` action with a short-lived App token (commit objects untouched, so signatures survive), and `ff-merge`
re-verifies write access, approval, all checks, and a genuine fast-forward before moving the ref. There is no GitHub
event for "all of a repo's own Actions checks finished" (GitHub does not fire `check_suite` for `GITHUB_TOKEN` runs), so
auto-merge observes completion via `workflow_run(completed)` listing every required workflow. Requires branch protection
that requires PR review. See [org setup](#fast-forward-merge-org-setup).

- **Inputs:** `app-client-id` (required; `vars.FF_MERGE_CLIENT_ID`), `merge-command` (default `/merge`), `arm-command`
  (default `/auto-merge`), `label` (default `auto-merge`), `require-approval` (default `true`), `maintainer-only`
  (default `true`).
- **Secrets:** `app-private-key` — required (`secrets.FF_MERGE_PRIVATE_KEY`).
- **Permissions (caller grants):** none — the App token does the privileged work, so the caller sets `permissions: {}`.
- **Triggers (the caller owns them):** `issue_comment` (`created`) drives `/merge` and arms `/auto-merge`;
  `workflow_run` (`completed`, listing your CI workflow name(s) plus `Merge Review Ack`) attempts the auto-merge once
  approved and green; the `schedule` sweeps armed PRs as a backstop. A `/merge`-only repo can trigger just
  `issue_comment`. Every trigger is one that does **not** attach a check run to the PR (no `pull_request`,
  `pull_request_review`, or `pull_request_target`), so the workflow leaves no skipped-job clutter on the PR's checks
  list, and none run PR code.
- **No skipped-check clutter:** because the approval signal (the PR-attached `pull_request_review` event) is captured by
  the companion [`merge-review-ack.yaml`](#merge-review-ackyaml) and re-enters via `workflow_run`, the only check this
  system adds to a PR is that companion's single `ack` job. The arm path also responds only to the `/auto-merge`
  comment; adding the `auto-merge` label by hand still arms (the label is the durable state), and the merge then happens
  on the next `workflow_run` or the scheduled sweep.
- **Fork PRs:** `issue_comment` and `workflow_run` carry base-context secrets on a fork, so fork and same-repo PRs
  auto-merge identically — arm with `/auto-merge` and an approval (routed through `merge-review-ack.yaml`) completes the
  merge. Install that companion and keep `Merge Review Ack` in the `workflow_run` list; the scheduled `sweep` backstops
  any missed trigger.

```yaml
on:
  issue_comment:
    types: [created]
  workflow_run:
    # your CI workflow name(s) — all that must be green — plus the review-ack companion
    workflows: ["CI", "Merge Review Ack"]
    types: [completed]
  schedule:
    - cron: "17 * * * *" # backstop sweep of armed PRs; tune or remove
permissions: {}
jobs:
  merge:
    uses: bitwise-media-group/github-workflows/.github/workflows/merge.yaml@v2
    with:
      app-client-id: ${{ vars.FF_MERGE_CLIENT_ID }}
    secrets:
      app-private-key: ${{ secrets.FF_MERGE_PRIVATE_KEY }}
```

Full example: [`examples/merge.yaml`](examples/merge.yaml). Pair it with
[`merge-review-ack.yaml`](#merge-review-ackyaml).

### `merge-review-ack.yaml`

_Any repo._ Required companion to [`merge.yaml`](#mergeyaml): it carries the **approval** signal for auto-merge.
`merge.yaml` deliberately subscribes to no PR-attached events (to avoid skipped-check clutter), but an approval only
exists as the PR-attached `pull_request_review` event — which also carries no secrets on a fork. This workflow's single
job completes on an approving review purely so its `workflow_run(completed)` re-enters `merge.yaml`'s
`merge-on-review-completed` job in base context, where the App token is minted and the fast-forward done. That makes
fork and same-repo PRs merge identically on approval, and it is the **only** check this merge system adds to a PR. It
does no privileged work and needs no secrets; `ff-merge` re-verifies approval, checks, label, and fast-forwardness
before moving the ref. Add `Merge Review Ack` to your `merge.yaml` caller's `workflow_run` list.

- **Inputs:** none.
- **Secrets:** none.
- **Permissions (caller grants):** none.

```yaml
on:
  pull_request_review:
    types: [submitted]
permissions: {}
jobs:
  ack:
    uses: bitwise-media-group/github-workflows/.github/workflows/merge-review-ack.yaml@v2
```

Full example: [`examples/merge-review-ack.yaml`](examples/merge-review-ack.yaml).

### `merge-notice.yaml`

_Any repo._ Posts a one-time comment on newly opened PRs explaining the repo merges via `/merge`. Uses
`pull_request_target` so the notice reaches fork PRs too.

- **Inputs:** `pr-number` — required.
- **Secrets:** none.
- **Permissions (caller grants):** `pull-requests: write`.

```yaml
on:
  pull_request_target:
    types: [opened]
permissions:
  pull-requests: write
jobs:
  notice:
    uses: bitwise-media-group/github-workflows/.github/workflows/merge-notice.yaml@v2
    with:
      pr-number: ${{ github.event.pull_request.number }}
```

Full example: [`examples/merge-notice.yaml`](examples/merge-notice.yaml).

### `dependabot-merge.yaml`

_Any repo._ Auto-approves Dependabot **minor and patch** PRs, then **squash-merges** them into the base branch once
every check on the head is green. Squash — not the fast-forward `/merge` uses — so queued Dependabot PRs merge without a
rebase (and a CI rerun) between each one; only genuinely conflicting PRs wait for Dependabot's rebase. Major updates are
never approved, so they wait for a human. Both the approval and the merge are done with the "FF Merge" App token, so
approval works regardless of the org "Allow GitHub Actions to approve pull requests" setting (that only restricts
`GITHUB_TOKEN`), and the App's ruleset bypass covers the rebase-only merge-method rule — the merge button stays dead for
everyone else. The squash commit GitHub creates is web-flow-signed and single-parent (satisfying required-signatures and
linear-history rules), titled with Dependabot's Conventional-Commit subject so release-please reads it unchanged. It
triggers only on `workflow_run` — an event that adds no check run to the PR, so it leaves no skipped-job clutter — and
reads the minor/patch-vs-major policy from the trailer in Dependabot's commit, only after verifying the head commit is
authored by `dependabot[bot]` and carries a valid signature. Requires a
[`.github/dependabot.yaml`](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates) so
Dependabot opens PRs, and branch protection that requires PR review (so the approval sets the review decision) — the
same assumption as the `/merge` flow.

- **Inputs:** `app-client-id` (required; `vars.FF_MERGE_CLIENT_ID`), `update-types` (optional; JSON array of Dependabot
  update types, default `["version-update:semver-patch", "version-update:semver-minor"]`).
- **Secrets:** `app-private-key` — required (`secrets.FF_MERGE_PRIVATE_KEY`).
- **Permissions (caller grants):** none — the App token does the privileged work, so the caller job sets
  `permissions: {}`.
- **Triggers (the caller owns it):** `workflow_run` (`completed`) listing your CI workflow name(s) — the reusable
  workflow approves and squash-merges once they finish green. No `pull_request_target` (so no skipped-check clutter);
  `check_suite` is _not_ used either — GitHub does not fire it for a repo's own Actions CI.

```yaml
on:
  workflow_run:
    workflows: ["CI"] # your CI workflow name(s) — all that must be green
    types: [completed]
permissions: {}
jobs:
  auto-merge:
    uses: bitwise-media-group/github-workflows/.github/workflows/dependabot-merge.yaml@v2
    with:
      app-client-id: ${{ vars.FF_MERGE_CLIENT_ID }}
    secrets:
      app-private-key: ${{ secrets.FF_MERGE_PRIVATE_KEY }}
```

Full example: [`examples/dependabot-merge.yaml`](examples/dependabot-merge.yaml).

### `dependabot-dist.yaml`

_Node Actions that commit `dist/`._ Closes the gap between a committed build artifact and Dependabot. A
JavaScript/TypeScript Action ships its bundled `dist/`, and `ci.yaml` fails any PR whose committed `dist/` does not
reproduce from `src/`. Dependabot bumps a bundled dependency but never runs the build task, so its PR lands with a stale
`dist/` and CI goes red — and `dependabot-merge.yaml` waits for green, so the PR sticks. When a watched CI run for a
`dependabot/` branch **fails**, this checks out the PR head, runs `mise run build`, and — only if `dist/` actually
changed — commits the rebuilt bundle back to the PR branch as the "FF Merge" App. That push re-triggers CI (an App-token
push does; a `GITHUB_TOKEN` push would be suppressed by loop-prevention), so the rerun reproduces `dist/` and goes
green. It does **not** approve or merge: the rebuild commit makes the head a non-Dependabot commit, so
`dependabot-merge.yaml` no longer auto-approves — a human approves the (production-dependency) bump and the existing App
squash-merge finishes it. Dev-only bumps that don't touch `dist/` never fail CI, never reach this workflow, and keep
auto-merging. Rebuilding runs the PR's dependency tree, so the write-capable App token is kept out of the build: it is
minted first but the checkout persists no credentials, and the token appears only in the final push step, after the
build has run.

- **Inputs:** `app-client-id` (required; `vars.FF_MERGE_CLIENT_ID`), `node-version-file` (optional, default
  `.node-version`), `paths` (optional; space-separated build-output path(s) to rebuild and commit, default `dist`).
- **Secrets:** `app-private-key` — required (`secrets.FF_MERGE_PRIVATE_KEY`).
- **Permissions (caller grants):** none — the App token does the privileged work, so the caller job sets
  `permissions: {}`.
- **Triggers (the caller owns it):** `workflow_run` (`completed`) listing your CI workflow name — the reusable workflow
  filters to failed runs on `dependabot/` branches, so green runs and pushes to `main` are ignored.

```yaml
on:
  workflow_run:
    workflows: ["CI"] # your CI workflow name
    types: [completed]
permissions: {}
jobs:
  rebuild-dist:
    uses: bitwise-media-group/github-workflows/.github/workflows/dependabot-dist.yaml@v4
    with:
      app-client-id: ${{ vars.FF_MERGE_CLIENT_ID }}
    secrets:
      app-private-key: ${{ secrets.FF_MERGE_PRIVATE_KEY }}
```

Full example: [`examples/dependabot-dist.yaml`](examples/dependabot-dist.yaml).

### `add-to-project.yaml`

_Any repo._ Adds the triggering issue (or PR) to a shared organisation **Projects v2** board — the org "Roadmap" — so
new issues from every repo collect in one place. `GITHUB_TOKEN` cannot write an org-level project, so this mints a
short-lived token from a dedicated **Project Sync** GitHub App (the same `create-github-app-token` pattern as
[`merge.yaml`](#mergeyaml)), downscoped to `organization-projects: write` plus `issues` / `pull-requests: read`, and
hands it to [`actions/add-to-project`](https://github.com/actions/add-to-project). The App must be installed on the repo
whose issue fires the caller — install it on **all repositories**. In this org the caller is fanned out to every repo by
`org-config.sh workflows-sync` in [`github-settings`](https://github.com/bitwise-media-group/github-settings).

- **Inputs:** `project-url` (required; `https://github.com/orgs/<org>/projects/<n>`), `app-client-id` (required;
  `vars.ADD_TO_PROJECT_CLIENT_ID`), `labeled` (optional; comma-separated labels to filter on), `label-operator`
  (optional; `AND` / `OR` / `NOT`, default `OR`).
- **Secrets:** `app-private-key` — required (`secrets.ADD_TO_PROJECT_PRIVATE_KEY`).
- **Permissions (caller grants):** none — the App token does the privileged work, so the caller job sets
  `permissions: {}`.
- **Triggers (the caller owns it):** `issues` (`opened`) is the usual choice; any event carrying an issue or PR works.
- **Org setup (one-time):** create a **Project Sync** App with organization **projects** read/write and repository
  **issues** + **pull requests** read, install it on all repositories, and expose it as the `ADD_TO_PROJECT_CLIENT_ID`
  variable + `ADD_TO_PROJECT_PRIVATE_KEY` secret.

```yaml
on:
  issues:
    types: [opened]
permissions: {}
jobs:
  add:
    uses: bitwise-media-group/github-workflows/.github/workflows/add-to-project.yaml@v4
    with:
      project-url: https://github.com/orgs/bitwise-media-group/projects/1
      app-client-id: ${{ vars.ADD_TO_PROJECT_CLIENT_ID }}
    secrets:
      app-private-key: ${{ secrets.ADD_TO_PROJECT_PRIVATE_KEY }}
```

Full example: [`examples/add-to-project.yaml`](examples/add-to-project.yaml).

### `update-tools.yaml`

_Any repo whose mise tools float on fuzzy selectors (`"latest"`, `"lts"`) and are locked in a root `mise.lock`._
Dependabot has no mise ecosystem, so this replaces it: `mise lock --bump` re-resolves the selectors against the newest
releases that have aged past the cooldown (`MISE_MINIMUM_RELEASE_AGE`, from `cooldown-days`) and rewrites the lockfile
only — config files are never modified. Version changes land as a single `fix(deps):` PR on a stable bot branch
(force-updated each run), so release-please cuts a patch when it merges. Only the **root** `mise.lock` is committed: in
repos that mount the shared task library as a submodule at `.mise/`, the submodule's own lockfile is never touched here
— shared-tool bumps belong to the library, which runs this same workflow itself. The bump commit is created through the
GitHub API (`createCommitOnBranch`), so GitHub signs it server-side and it lands **verified** — satisfying a
required-signatures rule that a runner-side `git commit` could never pass. Human-reviewed by design (supply-chain
sensitive): the PR is never auto-merged. Supply a GitHub App so the branch update triggers the PR's CI; with the
`GITHUB_TOKEN` fallback GitHub's recursion guard suppresses the checks.

- **Inputs:** `cooldown-days` (default `"7"`), `branch` (default `bot/update-tools`), `app-client-id` (optional; App
  that authors the bump commit so CI runs on the PR).
- **Secrets:** `app-private-key` — required when `app-client-id` is set.
- **Permissions (caller grants):** `contents: write`, `pull-requests: write`.
- **Triggers (the caller owns it):** `schedule` (daily) plus `workflow_dispatch` with a `cooldown-days` input.

```yaml
on:
  schedule:
    - cron: "0 7 * * *"
  workflow_dispatch:
permissions:
  contents: write
  pull-requests: write
jobs:
  update:
    uses: bitwise-media-group/github-workflows/.github/workflows/update-tools.yaml@v6
```

Full example: [`examples/update-tools.yaml`](examples/update-tools.yaml).

## Consumer contracts

The reusable workflows stay free of per-repo configuration by assuming a small contract. The **mise config is the
language boundary** — every repo provides the same canonical tasks and the workflows just run `mise run <task>`, setting
up toolchains from the files at the repo root:

- **mise tasks** — defined in a root `mise.toml`, or by the shared task library
  ([`bitwise-media-group/make`](https://github.com/bitwise-media-group/make)) mounted as a submodule at `.mise/`: `lint`
  (all check-mode static analysis: `prettier --check`, markdownlint, and for Go `go vet` / `govulncheck`), `build`,
  `test` (emitting `coverage/cobertura-coverage.xml`, optionally `coverage/junit.xml`), and `e2e`. Define only the tasks
  that do real work — CI discovers the task list and skips the rest; coverage is optional. A repo with no mise config
  fails CI.
- **Toolchain detection** — `setup-go` runs only when a **root `go.mod`** exists; `setup-node` only when `package.json`
  exists (the tasks install their own deps, so the workflow sets up the toolchain but does not run `npm ci`). A
  tools-only `go.work` + `tools/go.mod` (for `go tool addlicense`) is universal dev tooling, so it is **not** a
  Go-product signal — only a root `go.mod` is.
- **CodeQL** — scans `actions` always, `go` (autobuild, `setup-go` from `go-version-file`) when a root `go.mod` exists,
  and `javascript-typescript` when `package.json` exists. A repo with a bundled `dist/` should pass
  `config-file: ./.github/codeql/codeql-config.yaml` (copy [`examples/codeql-config.yaml`](examples/codeql-config.yaml))
  to exclude it.
- **Release** — `release-please-config.json` + `.release-please-manifest.json`; a `.goreleaser.yaml`
  (`release-type: go`, `draft: true`) selects the GoReleaser path, otherwise the release is just the release-please cut.
  A `zensical.toml` selects the docs path (rebuild the Zensical site and publish to Pages; needs Pages set to GitHub
  Actions and `pages: write`). Set `vanity-tags: true` to move the floating `v1` / `v1.1` tags (after GoReleaser when
  present); a committed `dist/` is verified in CI, not here.

A caller may mix a reusable-workflow job with normal jobs — e.g. a Go CLI keeps its product-specific `integration` /
`e2e` jobs in the same `ci.yaml` that calls the reusable `ci.yaml`.

## Pinning

The examples reference `@v2`, the floating major tag, which moves to each release in the v2.x line (a matching minor tag
`@v2.1` moves too). Pin to a release tag (`@v2.1.0`) or a full commit SHA for stricter supply-chain guarantees;
Dependabot and Renovate can bump either. Avoid `@main` except for short-lived testing.

## Fast-forward merge: org setup

`merge.yaml` (the `/merge` + auto-merge flows) drives the `bitwise-media-group/ff-merge` action; `dependabot-merge.yaml`
squash-merges directly with the same App token and ruleset bypass; `merge-notice.yaml` posts the companion convention
reminder. The one-time org setup (the "FF Merge" GitHub App, its ruleset bypass, and the `FF_MERGE_CLIENT_ID` variable +
`FF_MERGE_PRIVATE_KEY` secret) is documented in
[`bitwise-media-group/ff-merge`](https://github.com/bitwise-media-group/ff-merge).

> **Note on App input names.** This library's contract is input `app-client-id` + secret `app-private-key`, backed by
> `vars.FF_MERGE_CLIENT_ID` / `secrets.FF_MERGE_PRIVATE_KEY`. Existing callers across the org currently use inconsistent
> names (`client-id`/`app-key`, or `app-id`/`app-key` with `FF_APP_ID`/`FF_APP_KEY`); align them to the names above when
> migrating to these reusable workflows.

## Testing changes

This repo dogfoods its own reusable workflows by local path: `self-ci.yaml` calls `ci.yaml` (which installs the pinned
toolchain from the root `mise.toml` and runs the one task this repo defines, `lint`) and `self-release.yaml` calls
`release.yaml` (no `.goreleaser.yaml`, so just the release-please cut plus the `vanity-tags` job). `self-security.yaml`
stays a bespoke `actions`-only scan: the library has no compilable Go and no JS/TS product source, so an `actions`
CodeQL pass is the whole surface. The `/merge` + auto-merge flows (`self-merge.yaml`), its fork-PR review-ack companion
(`self-merge-review-ack.yaml`), and the merge notice (`self-merge-notice.yaml`) dogfood the rest. This repo's own
dependency automation (action SHA pins, the mise toolchain lockfile, and the `.mise` submodule tag) is the org Renovate
bot ([`bitwise-media-group/renovate-config`](https://github.com/bitwise-media-group/renovate-config)) — the reusable
`dependabot-merge.yaml` / `dependabot-dist.yaml` / `update-tools.yaml` remain for consumers still on Dependabot.
Validate a change to a reusable workflow by temporarily pointing a real consumer's caller at a feature branch or SHA
(`@your-branch`) and opening a PR there.

## Releasing this repo

`self-release.yaml` calls the reusable `release.yaml` (`release-type: simple`, `vanity-tags: true`) on pushes to `main`;
merging the release PR cuts `vX.Y.Z` and moves the floating major and minor tags (`v2`, `v2.1`). Consumers pin to those
tags.
