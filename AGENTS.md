# Agent instructions

Repository-specific conventions for agents (and humans) working here. Machine-wide and personal instruction files still
apply; this layers the repo rules on top.

## What this repository is

`github-workflows` is BitWise Media Group's library of **reusable** GitHub Actions workflows. The product is the
callable workflows in `.github/workflows/` — the ones other repositories invoke via
`uses: bitwise-media-group/github-workflows/.github/workflows/<name>.yaml@<ref>` — together with the copy-paste callers
under `examples/`. release-please versions this library straight from the Conventional Commit history, so the commit
**type** decides whether consumers ever receive a change.

## Commit types

Pick the type by **who the change reaches**, not by which directory the file lives in:

- **Reusable workflows** — everything in `.github/workflows/` _except_ the `self-*` files, plus their `examples/`
  callers — are the shipped product. A change to one is a `feat:` (new capability) or `fix:` (bug fix, or a maintenance
  change such as bumping a pinned action SHA that you want consumers to pick up). **Never use `ci:` for these** —
  release-please ignores `ci:`, so the change would never be released and every consumer would stay pinned to the old
  version.
- **`ci:` is reserved for this repo's own automation** — the `self-*` workflows in `.github/workflows/` and the
  supporting config they depend on (`.github/dependabot.yaml`, `.github/codeql/`, `release-please-config.json`, …).
  These must _not_ cut a library release, which is exactly why `ci:` (and `chore:`) fit them.
- `docs:`, `build:`, `chore:`, `refactor:`, `test:` keep their usual meanings for changes that don't alter a reusable
  workflow's behaviour (license headers, tooling, prose, …).

In short: if a change alters what a **consumer's** workflow run does, it's `feat:`/`fix:`; if it only affects how
**this** repository builds, tests, releases, or maintains itself, it's `ci:`/`chore:`/`build:`.

## Documentation site

`https://oss.bitwisemedia.uk/github-workflows/` is a [Zensical](https://zensical.org) site that documents every reusable
workflow: what it does, how it works, and what a consumer needs for it. It is part of the product, so **keep it in step
with the workflows in the same change**. A workflow change without its docs update is incomplete.

- **Layout:** `zensical.toml` (config + nav), `pyproject.toml` + `uv.lock`, hand-written pages in `docs/`, theme in
  `overrides/` + `docs/stylesheets/extra.css` (copied from the toolchain / flux-containers sites), and the generator
  `scripts/workflow_docs.py`.
- **Generated, never hand-copied:** `scripts/workflow_docs.py` renders each workflow's inputs, secrets, outputs, caller
  permissions (the union over jobs), jobs + `if:` conditions and pinned actions from the YAML into
  `build/workflow-docs/` (git-ignored). The pages include those fragments, and the live `examples/*.yaml` callers, with
  `--8<--`. Never paste an input table, permission block, action pin or caller example into a page.
- **Hand-written, so you must update it:** when a change alters a workflow's behaviour (a job, step, condition,
  detection signal, requirement, org prerequisite or failure mode), update in the same commit:
  - `docs/workflows/<name>.md`, especially its _How it works_, _Requirements_ and _Troubleshooting_ sections, and its
    `description` front matter (it feeds the landing card);
  - the summary row in `docs/workflows/index.md`;
  - any concept or setup page the change touches: `docs/concepts/mise-contract.md` (tasks, detection signals),
    `docs/concepts/permissions.md` and `docs/setup/apps.md` (scopes, Apps, secrets),
    `docs/concepts/fast-forward-merge.md` (the merge trio), `docs/concepts/security.md` (hardening rules),
    `docs/setup/macos-notarization.md` (signing), `docs/reference/maintaining.md` (the `self-*` callers, release flow).
- **A new reusable workflow** needs `docs/workflows/<name>.md` (copy an existing page as the template) and a
  `{ "<name>.yaml" = "workflows/<name>.md" }` entry under _Workflows_ in `zensical.toml`'s nav. A renamed or removed one
  needs its page and nav entry renamed or removed. The generator **fails the build** on a missing page, a missing nav
  entry, or an orphaned page.
- **Don't hard-code release numbers** in prose (`vX.Y.Z`, not `v8.1.0`). The embedded examples already carry the current
  version, and release-please rewrites it.
- **README.md** still carries the long-form catalog. When you change a workflow's documented contract, keep the README's
  section for it consistent with the site.
- **Build:** `mise run docs-build` (generator + `zensical build` into `site/`); `mise run serve` previews on
  `http://localhost:8007`. `mise run build` is the same build and runs in CI, so a broken page fails the PR.
- **Publishing:** there is no separate docs workflow. `self-release.yaml` → `release.yaml`'s `docs` job detects
  `zensical.toml` and deploys on every release, so the site always describes the latest release. A `docs:` commit goes
  live with the next `feat:`/`fix:` release.
- **Commit type:** docs-only changes are `docs:`. Docs updated alongside a workflow change ride in that change's
  `feat:`/`fix:` commit.

## Before committing

Always run `mise run pr` before creating a commit (the root `Makefile` is a thin forwarder, so `make pr` works too). It
injects license headers, auto-fixes and formats markdown, then lints — the same gate CI enforces — so running it first
keeps the tree clean and avoids a follow-up "fix lint"/"fix formatting" commit. Only commit once `mise run pr` passes
and you have staged everything it changed. The tools (prettier, markdownlint-cli2, addlicense, actionlint, zizmor) are
pinned by the shared toolchain submodule at `.mise/`
([`bitwise-media-group/toolchain`](https://github.com/bitwise-media-group/toolchain)), loaded natively as
`.mise/config.toml`; `git submodule update --init` then `mise install` fetches them. At toolchain v3.0.0 `mise run pr`
ends by running `./commit.sh` if one exists, so an agent must run `mise run fmt`, `mise run lint` and `mise run build`
(the docs site) instead of `pr`.
