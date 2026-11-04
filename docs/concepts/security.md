---
description:
  The hardening choices every workflow in the library shares — SHA pins, verified toolchains, trusted-trigger allowlists
  and more.
---

# Security posture

Every workflow in the library follows the same rules. This page lists them, so a reviewer can tell when a change breaks
one.

## Supply chain

- **Every action is pinned to a full commit SHA** with a version comment. This repository's zizmor config requires
  `hash-pin` for every `uses:`, and Renovate updates the SHA and comment together.
- **mise itself is pinned and checksummed.** Each `jdx/mise-action` step gives an exact mise `version` and the `sha256`
  of its linux-x64 binary.
- **Every tool is checksum-verified** against the repository's `mise.lock`, and provenance-verified where the tool
  publishes it.
- **No cache in the signing job.** `release.yaml`'s `goreleaser` job installs mise with `cache: false`, so a cache
  written by a less-trusted run can't feed signed, attested artifacts.

## Credentials

- **`persist-credentials: false` on every checkout.** No token is left in `.git/config` for a later step to pick up.
- **`permissions: {}` at the top of every workflow**, with narrow grants per job. See
  [Permissions & tokens](permissions.md).
- **Short-lived, down-scoped App tokens** instead of PATs, minted in the job that needs them.
- **Codecov isolation.** `ci.yaml` uploads coverage from a separate job whose fresh checkout never ran the PR's build.

## Triggers and injection

- **Trusted-trigger allowlist.** `release.yaml`'s `goreleaser`, `docs` and `vanity-tags` jobs run only for `push`,
  `workflow_dispatch` or `schedule`. A reusable workflow can't see how its caller is triggered, so this fails closed if
  someone wires it to `pull_request_target`.
- **No PR code in privileged contexts.** `merge.yaml` never checks out code. `merge-notice.yaml` uses
  `pull_request_target` but only posts a static comment.
- **Expressions go in through `env:`.** Caller-supplied values, such as `security.yaml`'s `languages` input, reach shell
  scripts as environment variables and never as `${{ }}` inside the script, which avoids script injection. The only
  interpolated values are `hashFiles()` digests, which can only be hex or empty.

## Releases

- **Draft until everything is done.** GoReleaser fills a draft. Attestations, the cask push and every upload must
  succeed before the release is published, because published releases are immutable.
- **SLSA build provenance** for every file in `checksums.txt` and every published image digest. Verify with
  `gh attestation verify --owner bitwise-media-group <file>`.
- **Keyless cosign** signatures through the job's OIDC identity (`id-token: write`). No signing key is stored anywhere.
- **Floating tags move last.** `vanity-tags` runs only after `goreleaser` succeeded or was skipped.

## Checking a change

`mise run lint` runs actionlint and zizmor over `.github/workflows/` **and** `examples/`. CI runs the same gate, and
`security.yaml` runs CodeQL's `actions` queries over this repository. A change that adds a step should keep to the rules
above. A change that intentionally breaks one should say why in a comment next to it, as the `zizmor: ignore[...]` lines
in the callers do.
