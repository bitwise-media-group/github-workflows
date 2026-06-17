# github-workflows

Reusable [GitHub Actions workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows) for Bitwise
Media Group repositories. Each consuming repo keeps a thin **caller** workflow that owns its triggers and calls one of
these by `uses:`, so CI, CodeQL, release, and the fast-forward `/merge` flow live in one place instead of being
copy-pasted per repo.

Copy a caller from [`examples/`](examples/) into your repo's `.github/workflows/`, then pin it (see
[Pinning](#pinning)).

## Catalog

All reusable workflows live in [`.github/workflows/`](.github/workflows/) and are `workflow_call`-only. Every external
action is pinned to a full commit SHA; Dependabot keeps the pins fresh.

| Workflow                                         | Platform | What it does                                                                                                     |
| ------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------------------------- |
| [`ci.yaml`](#ciyaml)                             | any      | canonical Makefile gates (lint/build/test) per job, toolchains by detection, Codecov upload                      |
| [`codeql.yaml`](#codeqlyaml)                     | any      | CodeQL over actions + go (autobuild) + javascript-typescript, language matrix by detection                       |
| [`release.yaml`](#releaseyaml)                   | any      | release-please (two-pass) → GoReleaser (if `.goreleaser.yaml`) or `dist/` rebuild + verify; optional vanity tags |
| [`merge.yaml`](#mergeyaml)                       | any      | signature-preserving fast-forward merge — `/merge` now, or `/auto-merge` (comment/label) when approved + green   |
| [`merge-notice.yaml`](#merge-noticeyaml)         | any      | posts a one-time "this repo merges via `/merge`" comment on new PRs                                              |
| [`dependabot-merge.yaml`](#dependabot-mergeyaml) | any      | auto-approves Dependabot minor/patch PRs and fast-forwards them once CI is green                                 |

Each workflow below lists its inputs, secrets, and the permission ceiling the **caller** must grant — a reusable
workflow's jobs cannot exceed the permissions of the job that calls them. The snippet is the minimal caller; follow the
link beneath it for the fully-commented version.

### `ci.yaml`

_Any repo._ Runs the canonical Makefile gates — `lint`, `build`, `test` — as one parallel job each, sets up only the
toolchains the repo has (a root `go.mod` → Go, `package.json` → Node), and uploads coverage to Codecov from a job
isolated from PR-built code. An opt-in `e2e` job runs `make e2e`. A caller may add product-specific jobs (e.g.
`integration`) alongside the `ci` job.

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

### `codeql.yaml`

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
    uses: bitwise-media-group/github-workflows/.github/workflows/codeql.yaml@v2
```

Full example: [`examples/codeql.yaml`](examples/codeql.yaml).

### `release.yaml`

_Any repo._ Runs release-please (two-pass), then branches by detection: a repo with a `.goreleaser.yaml` runs GoReleaser
(archives, checksums, SBOMs, cosign signatures, optional Homebrew cask, SLSA attestation); every other repo rebuilds via
`make build` and verifies a committed `dist/`. With `vanity-tags: true` it also moves the floating major and minor tags
(`v1` and `v1.1`).

- **Inputs:** `go-version-file` (default `go.mod`), `node-version-file` (default `.node-version`), `vanity-tags`
  (default `false`; move the floating `v1` / `v1.1` tags — set it for Actions/reusable repos whose consumers pin `@v1`).
- **Secrets:** `homebrew-tap-token` — optional; only needed if `.goreleaser.yaml` publishes a Homebrew cask to another
  repo (`secrets.HOMEBREW_TAP_GITHUB_TOKEN`).
- **Permissions (caller grants):** `contents: write`, `issues: write`, `pull-requests: write`; plus `id-token: write`,
  `attestations: write`, `artifact-metadata: write` for the GoReleaser path only (drop them if you have no
  `.goreleaser.yaml`).

```yaml
on:
  push:
    branches: [main]
permissions:
  contents: write
  issues: write
  pull-requests: write
  id-token: write # GoReleaser path only
  attestations: write # GoReleaser path only
  artifact-metadata: write # GoReleaser path only
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
- **Triggers (the caller owns all four):** `issue_comment` (`created`) drives `/merge` and arms `/auto-merge`;
  `pull_request` (`labeled`) arms via label; `pull_request_review` (`submitted`) and `workflow_run` (`completed`,
  listing your CI workflow name(s)) attempt the auto-merge once approved and green. A `/merge`-only repo can trigger
  just `issue_comment`. None of the triggers run PR code, and none use `pull_request_target`.
- **Fork PRs:** only `issue_comment` and `workflow_run` carry base-context secrets on a fork, so the label-arm and
  review jobs are gated to same-repo PRs. Arm a fork PR with `/auto-merge` (it merges via that attempt or
  `workflow_run`), or just use `/merge`.

```yaml
on:
  issue_comment:
    types: [created]
  pull_request:
    types: [labeled]
  pull_request_review:
    types: [submitted]
  workflow_run:
    workflows: ["CI"] # your CI workflow name(s) — all that must be green
    types: [completed]
permissions: {}
jobs:
  merge:
    uses: bitwise-media-group/github-workflows/.github/workflows/merge.yaml@v2
    with:
      app-client-id: ${{ vars.FF_MERGE_CLIENT_ID }}
    secrets:
      app-private-key: ${{ secrets.FF_MERGE_PRIVATE_KEY }}
```

Full example: [`examples/merge.yaml`](examples/merge.yaml).

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

_Any repo._ Auto-approves Dependabot **minor and patch** PRs, then fast-forwards them into the base branch once CI is
green — using the same signature-preserving `ff-merge` action as [`merge.yaml`](#mergeyaml). Major updates are never
approved, so they wait for a human. Both the approval and the merge are done with the "FF Merge" App token, so approval
works regardless of the org "Allow GitHub Actions to approve pull requests" setting (that only restricts
`GITHUB_TOKEN`). Requires a
[`.github/dependabot.yaml`](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates) so
Dependabot opens PRs, and branch protection that requires PR review (so the approval sets the review decision) — the
same assumption as the `/merge` flow.

- **Inputs:** `app-client-id` (required; `vars.FF_MERGE_CLIENT_ID`), `update-types` (optional; JSON array of Dependabot
  update types, default `["version-update:semver-patch", "version-update:semver-minor"]`).
- **Secrets:** `app-private-key` — required (`secrets.FF_MERGE_PRIVATE_KEY`).
- **Permissions (caller grants):** none — the App token does the privileged work, so the caller job sets
  `permissions: {}`.
- **Triggers (the caller owns both):** `pull_request_target` (`opened`/`reopened`/`synchronize`) to approve on open, and
  `workflow_run` (`completed`) listing your CI workflow name(s) to fast-forward once they finish green. `check_suite` is
  _not_ used — GitHub does not fire it for a repo's own Actions CI.

```yaml
on:
  pull_request_target:
    types: [opened, reopened, synchronize]
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

## Consumer contracts

The reusable workflows stay free of per-repo configuration by assuming a small contract. The **Makefile is the language
boundary** — every repo provides the same canonical targets and the workflows just run `make <target>`, setting up
toolchains from the files at the repo root:

- **Makefile targets** — `lint` (all check-mode static analysis: `prettier --check`, markdownlint, and for Go `go vet` /
  `govulncheck`), `build`, `test` (emitting `coverage/cobertura-coverage.xml`, optionally `coverage/junit.xml`), and
  `e2e`. Stub any that don't apply as a no-op (`build: ; @:`) so `make <target>` always succeeds; coverage is optional.
- **Toolchain detection** — `setup-go` runs only when a **root `go.mod`** exists; `setup-node` (and `npm ci`) only when
  `package.json` exists. A tools-only `go.work` + `tools/go.mod` (for `go tool addlicense`) is universal dev tooling, so
  it is **not** a Go-product signal — only a root `go.mod` is.
- **CodeQL** — scans `actions` always, `go` (autobuild, `setup-go` from `go-version-file`) when a root `go.mod` exists,
  and `javascript-typescript` when `package.json` exists. A repo with a bundled `dist/` should pass
  `config-file: ./.github/codeql/codeql-config.yaml` (copy [`examples/codeql-config.yaml`](examples/codeql-config.yaml))
  to exclude it.
- **Release** — `release-please-config.json` + `.release-please-manifest.json`; a `.goreleaser.yaml`
  (`release-type: go`, `draft: true`) selects the GoReleaser path, otherwise the publish path rebuilds via `make build`
  and verifies a committed `dist/`. Set `vanity-tags: true` to move the floating `v1` / `v1.1` tags.

A caller may mix a reusable-workflow job with normal jobs — e.g. a Go CLI keeps its product-specific `integration` /
`e2e` jobs in the same `ci.yaml` that calls the reusable `ci.yaml`.

## Pinning

The examples reference `@v2`, the floating major tag, which moves to each release in the v2.x line (a matching minor tag
`@v2.1` moves too). Pin to a release tag (`@v2.1.0`) or a full commit SHA for stricter supply-chain guarantees;
Dependabot can bump either. Avoid `@main` except for short-lived testing.

## Fast-forward merge: org setup

`merge.yaml` (the `/merge` + auto-merge flows) and `dependabot-merge.yaml` drive the `bitwise-media-group/ff-merge`
action; `merge-notice.yaml` posts the companion convention reminder. The one-time org setup (the "FF Merge" GitHub App,
its ruleset bypass, and the `FF_MERGE_CLIENT_ID` variable + `FF_MERGE_PRIVATE_KEY` secret) is documented in
[`bitwise-media-group/ff-merge`](https://github.com/bitwise-media-group/ff-merge).

> **Note on App input names.** This library's contract is input `app-client-id` + secret `app-private-key`, backed by
> `vars.FF_MERGE_CLIENT_ID` / `secrets.FF_MERGE_PRIVATE_KEY`. Existing callers across the org currently use inconsistent
> names (`client-id`/`app-key`, or `app-id`/`app-key` with `FF_APP_ID`/`FF_APP_KEY`); align them to the names above when
> migrating to these reusable workflows.

## Testing changes

This repo dogfoods its own reusable workflows by local path: `self-ci.yaml` calls `ci.yaml` (which detects node only —
there is no root `go.mod` — and runs the canonical `make` gates) and `self-release.yaml` calls `release.yaml` (the
publish path, moving the vanity tags). `self-codeql.yaml` stays a bespoke `actions`-only scan: the library has no
compilable Go and no JS/TS product source, so the reusable `codeql.yaml` would add an empty `javascript-typescript` leg
from its tooling-only `package.json`. The `/merge` + auto-merge flows (`self-merge.yaml`), the merge notice
(`self-merge-notice.yaml`), and Dependabot auto-merge (`self-dependabot-merge.yaml`, which keeps the reusable workflows'
action pins fresh) dogfood the rest. Validate a change to a reusable workflow by temporarily pointing a real consumer's
caller at a feature branch or SHA (`@your-branch`) and opening a PR there.

## Releasing this repo

`self-release.yaml` calls the reusable `release.yaml` (`release-type: simple`, `vanity-tags: true`) on pushes to `main`;
merging the release PR cuts `vX.Y.Z` and moves the floating major and minor tags (`v2`, `v2.1`). Consumers pin to those
tags.
