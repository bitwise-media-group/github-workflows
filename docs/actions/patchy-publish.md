---
description:
  Publish a repository's patchy build artifacts on its release pipeline as immutable edge builds, and promote the newest
  edge build when a release is cut. Registries and signing come from org variables.
---

# `patchy-publish`

**A composite action**, not a reusable workflow, for repositories whose products are OCI artifacts built with
[`patchy build`](https://oss.bitwisemedia.uk/patchy/supply-chain/build/): container images and Flux manifests. It runs
in a job of the repository's own release workflow, after [`release.yaml`](../workflows/release.md):

| The release run…    | `mode`    | What it publishes                                                                                  |
| ------------------- | --------- | -------------------------------------------------------------------------------------------------- |
| cut no release      | `edge`    | every entry, built and signed as `<next version>-edge.<UTC yyyymmddhhmmss>.g<short commit>`        |
| cut release `X.Y.Z` | `promote` | `vX.Y.Z`, added to the newest `X.Y.Z-edge.*` build of every entry; nothing is rebuilt or re-signed |

Every tag is immutable, and a channel is its newest build: consumers follow edge with semver `>=0.0.0-0` filtered to
`^[0-9]+[.][0-9]+[.][0-9]+-edge[.][0-9]{14}[.]g[0-9a-f]{7,40}$`, and stable with `>=0.0.0`. An edge build is based on
the **next** version, read from the open release pull request, so `1.3.2` < `1.4.0-edge.*` < `1.4.0`. With no release
pending, it bumps the last release's patch.

## Why an action, not a reusable workflow

Keyless signatures are only as specific as the identity in their certificate. A job's Fulcio identity is the workflow
that defines it, and a reusable workflow's identity is the reusable workflow itself: this repository is public, so any
repository on GitHub can call it and sign as `github-workflows/.github/workflows/release.yaml`. A composite action
leaves the job's identity alone, so artifacts are signed as the publishing repository's own workflow:

```text
https://github.com/<org>/<repo>/.github/workflows/release.yaml@refs/heads/main
```

Only repositories in the org can produce that identity, so a consumer trusting every repository in the org verifies the
subject `^https://github\.com/<org>/[^/]+/\.github/workflows/release\.yaml@refs/heads/main$`, and one trusting a subset
narrows `[^/]+` (`aip-[^/]+`).

## Configuration, not commits

Nothing org- or cloud-specific is committed. The action writes the registries and the signing config to
`~/.config/patchy/config.yaml`, a config layer beneath the repository's `patchy.yaml`, which carries only its `build:`
block. `patchy build --dry-run`, which CI runs through the toolchain's `build` task, needs no registries at all.

| Input                                                         | From                                                      | Effect                                                         |
| ------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------- |
| `google-registry`                                             | `vars.PLATFORM_REGISTRY`                                  | the `google` registry; empty skips Google                      |
| `google-workload-identity-provider`, `google-service-account` | `vars.GCP_WIF_PROVIDER`, `vars.GCP_MANIFEST_PUBLISHER_SA` | the Workload Identity Federation login                         |
| `aws-registry`                                                | `vars.AWS_PLATFORM_REGISTRY`                              | the `aws` registry; empty skips AWS                            |
| `aws-role`, `aws-region`                                      | `vars.AWS_MANIFEST_PUBLISHER_ROLE`, `vars.AWS_REGION`     | the OIDC role login                                            |
| `signing-kms-key`                                             | `vars.SIGNING_KMS_KEY`                                    | sign with `gcpkms://…` or `awskms:///…`; empty signs keylessly |

Adding a cloud is a matter of setting its variables. The registry URLs never appear in the run: they are masked in the
logs, and the job summary names each registry (`<google>`, `<aws>`) instead.

### Restricting a KMS key to some repositories

With `signing-kms-key`, the trust boundary is who may use the key. Grant it through a condition on the job's GitHub OIDC
claims, so only the release workflow on the default branch of the chosen repositories can sign:

- **Google Cloud:** a dedicated Workload Identity Federation provider whose attribute condition admits only those jobs,
  for example:

  ```text
  assertion.repository_owner_id == "<org id>"
  && assertion.repository.startsWith("<org>/aip-")
  && assertion.job_workflow_ref == assertion.repository + "/.github/workflows/release.yaml@refs/heads/main"
  ```

  Map an attribute only that provider sets, and grant `signerVerifier` on the key to that attribute's principal set, not
  to the whole pool.

- **AWS:** IAM trust policies only see `aud` and `sub`, so customise the repositories' OIDC subject template to include
  `repository_owner_id`, `repository` and `job_workflow_ref`, and match it with `StringLike` in the signing role's trust
  policy (`…repository:<org>/aip-*:job_workflow_ref:<org>/aip-*/.github/workflows/release.yaml@refs/heads/main`).
  Customising the template changes `sub` for every workflow in those repositories, so update their other trust policies
  at the same time.

## Promotion safety

Before promoting, the action resolves the build it would promote for every entry (`patchy build promote --dry-run`) and
checks that the commit it was built from (its revision annotation) has the same tree as the release commit under the
entry's path. A release commit only bumps versions and the changelog, so this holds unless an edge build is missing or
stale, and then the promotion fails instead of releasing something else. The build's signature must also verify under
the configured signing before the tag is added. The caller's job runs in a `patchy-publish` concurrency group, so an
edge build never races a promotion.

## Example

```yaml title="examples/release-patchy.yaml"
--8<-- "examples/release-patchy.yaml"
```
