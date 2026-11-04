---
description: How callers pin the library by commit SHA, how releases are versioned, and how Renovate keeps pins current.
---

# Pinning & upgrades

## Pin by full commit SHA

Every `uses:` in a caller pins the library to a **full commit SHA**, with the release it stands for in a trailing
comment:

```yaml
jobs:
  ci:
    uses: bitwise-media-group/github-workflows/.github/workflows/ci.yaml@<40-hex-sha> # vX.Y.Z
```

That is the org policy for every action, first-party included. A tag can be moved and a SHA can't, so the pinned code is
exactly what was reviewed. This repository's `.github/zizmor.yaml` enforces it by setting zizmor's `unpinned-uses` audit
to `hash-pin` for every action. A consumer that ships the same config gets the same check from
[`security.yaml`](../workflows/security.md).

The examples ship with an all-zeros placeholder SHA (`@0000…0000 # vX.Y.Z`). Replace it before the caller can run:

```sh
git ls-remote https://github.com/bitwise-media-group/github-workflows refs/tags/vX.Y.Z
```

Avoid `@main` except for short-lived testing. It runs whatever merged last, without review on your side.

## The `x-release-please-version` marker

Each example's `uses:` line ends in `# x-release-please-version`. That marker is for **this** repository's release
automation: release-please rewrites the version comment in every release PR, so the examples always name the release
they document. In a copied caller it does nothing. Keep it or drop it.

## Versioning

release-please versions the library from its Conventional Commit history:

- `feat:` → minor release, `fix:` → patch release, `feat!:` or a `BREAKING CHANGE:` footer → major release.
- `docs:`, `ci:`, `chore:` and friends cut no release.

Each release creates `vX.Y.Z` and moves the floating `vX` and `vX.Y` tags (`vanity-tags: true` in this repository's own
release caller). Consumers still pin the SHA. The floating tags exist for tools and humans that resolve them.

The [changelog](https://github.com/bitwise-media-group/github-workflows/blob/main/CHANGELOG.md) lists every release.

## Staying current with Renovate

The org Renovate preset ([`renovate-config`](https://github.com/bitwise-media-group/renovate-config)) recognises a SHA
pin with a version comment. When this library cuts a release, Renovate opens a PR in each consumer that moves the SHA
and the comment together. Patch and minor bumps follow the preset's automerge policy. A major bump is armed with the
`auto-merge` label and lands once a maintainer approves it. See [`merge.yaml`](../workflows/merge.md).

## Upgrading across a major

Majors are rare and their release notes say what a caller has to change, usually a renamed input or a new required
permission. A required permission matters most: GitHub checks a reusable workflow's permissions when the run starts, so
a caller that grants too little fails before any job runs (a `startup_failure`). Compare your caller against the current
example. Each workflow page shows its required permissions, generated from the workflow itself.
