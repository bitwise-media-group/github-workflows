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

## Before committing

Always run `make pr` before creating a commit. It injects license headers, auto-fixes and formats markdown, then lints —
the same gate CI enforces — so running it first keeps the tree clean and avoids a follow-up "fix lint"/"fix formatting"
commit. Only commit once `make pr` passes and you have staged everything it changed.
