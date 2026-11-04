---
description: How this library tests, versions and releases itself, and the rules for changing a reusable workflow.
---

# Maintaining this library

## Repository layout

| Path                                                               | What it is                                                                         |
| ------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `.github/workflows/<name>.yaml`                                    | the **reusable workflows**, the shipped product (`workflow_call` only)             |
| `.github/workflows/self-*.yaml`                                    | this repository's own callers, which dogfood the library by local path             |
| `examples/<name>.yaml`                                             | the copy-paste callers consumers start from, embedded in these docs                |
| `examples/codeql-config.yaml`                                      | the CodeQL config for repositories with a bundled `dist/`                          |
| `.github/zizmor.yaml`, `.github/actionlint.yaml`                   | lint config for the workflows                                                      |
| `.mise/`                                                           | the shared [toolchain](https://github.com/bitwise-media-group/toolchain) submodule |
| `docs/`, `overrides/`, `zensical.toml`, `scripts/workflow_docs.py` | this site                                                                          |

## Dogfooding

Each reusable workflow has a `self-*` caller that runs it **by local path** (`uses: $/.github/workflows/<name>.yaml`),
so this repository always runs the current definition rather than a release:

| Caller                       | Runs                    | Notes                                                                         |
| ---------------------------- | ----------------------- | ----------------------------------------------------------------------------- |
| `self-ci.yaml`               | `ci.yaml`               | `lint` and `build` (the docs site). There is no `test` task, so it's skipped  |
| `self-security.yaml`         | `security.yaml`         | `languages: actions`, because the `package.json` is tooling only, plus zizmor |
| `self-release.yaml`          | `release.yaml`          | no `.goreleaser.yaml`; the `docs` job publishes this site; `vanity-tags`      |
| `self-merge.yaml`            | `merge.yaml`            | `workflow_run` on CI, Security Analysis and Merge Review Ack                  |
| `self-merge-review-ack.yaml` | `merge-review-ack.yaml` |                                                                               |
| `self-merge-notice.yaml`     | `merge-notice.yaml`     |                                                                               |
| `self-add-to-project.yaml`   | `add-to-project.yaml`   |                                                                               |
| `self-renovate.yaml`         | `renovate.yaml`         | also this repository's own dependency automation (action SHAs, `.mise` tag)   |

A PR that changes a reusable workflow therefore runs the changed version in its own checks wherever the trigger allows.
For behaviour that only a consumer exercises, such as GoReleaser, Go CodeQL or coverage, point a real consumer's caller
at your branch or commit (`@your-branch`) in a throwaway PR there.

## Commit types decide releases

release-please versions the library from Conventional Commits, so the **type** decides whether consumers get a change:

- A change to a **reusable workflow** or its **example** is `feat:` (new capability) or `fix:` (bug fix, or maintenance
  such as a pinned action bump). **Never `ci:`**: release-please ignores it, and consumers would stay on the old
  version.
- **`ci:`** is only for this repository's own automation: the `self-*` callers and the config they read
  (`.github/zizmor.yaml`, `.github/codeql/`, `release-please-config.json`, …).
- **`docs:`** for this site and other prose. It cuts no release.

## Releasing

`self-release.yaml` runs on every push to `main`. Merging the release PR cuts `vX.Y.Z`, moves `vX` and `vX.Y`, publishes
this site to GitHub Pages, and rewrites the version comment on every `examples/*.yaml` `uses:` line (`extra-files` in
`release-please-config.json`).

## Checklist for a workflow change

1. Edit the reusable workflow and keep its header comment accurate.
2. Update its `examples/` caller if triggers, inputs, secrets or permissions changed.
3. Update its page in `docs/workflows/`, and any concept page the change affects. See [Working on the docs](docs.md).
4. Run `mise run fmt`, `mise run lint` and `mise run build`.
5. Commit as `feat:` or `fix:` (`feat!:` if callers must change).
