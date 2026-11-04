---
description:
  One-time organisation setup for the GitHub Apps, variables and secrets the privileged workflows mint tokens from.
---

# GitHub Apps & secrets

The privileged workflows authenticate as **GitHub Apps**, not with `GITHUB_TOKEN` or a PAT. Each App is set up once for
the organisation and exposed as an org **variable** (the client ID) and an org **secret** (the private key). After that,
a new repository only needs the App installed on it.

| App          | Used by                                                                                     | Variable                   | Secret                       |
| ------------ | ------------------------------------------------------------------------------------------- | -------------------------- | ---------------------------- |
| FF Merge     | [`merge.yaml`](../workflows/merge.md); optionally [`release.yaml`](../workflows/release.md) | `FF_MERGE_CLIENT_ID`       | `FF_MERGE_PRIVATE_KEY`       |
| Project Sync | [`add-to-project.yaml`](../workflows/add-to-project.md)                                     | `ADD_TO_PROJECT_CLIENT_ID` | `ADD_TO_PROJECT_PRIVATE_KEY` |
| Renovate     | [`renovate.yaml`](../workflows/renovate.md)                                                 | `RENOVATE_CLIENT_ID`       | `RENOVATE_PRIVATE_KEY`       |

Every workflow takes them under the same names: input `app-client-id: ${{ vars.<APP>_CLIENT_ID }}` and secret
`app-private-key: ${{ secrets.<APP>_PRIVATE_KEY }}`.

## FF Merge

Moves `main` for the fast-forward merge flows. It also authors release PRs (so their pushes trigger `workflow_run`
automation) and pushes Homebrew casks.

- **Repository permissions:** Contents read/write, Pull requests read/write, Issues read/write, Workflows read/write,
  Checks read, Commit statuses read, Administration read.
- **Install** on every repository that uses `merge.yaml`, and on the Homebrew tap repository if any release publishes a
  cask.
- **Ruleset bypass:** add the App to the bypass list of `main`'s ruleset, so it can move the ref past the pull-request
  requirement.

The full walk-through lives with the action it drives:
[`bitwise-media-group/ff-merge`](https://github.com/bitwise-media-group/ff-merge).

## Project Sync

Writes issues and PRs into the organisation Roadmap board.

- **Organisation permissions:** Projects read/write.
- **Repository permissions:** Issues read, Pull requests read.
- **Install** on **all repositories**. The token is minted in the repository whose issue fired the workflow.

## Renovate

Runs the self-hosted Renovate bot, org-wide or per repository.

- **Repository permissions** (what `renovate.yaml` asks for): Contents, Workflows, Pull requests, Issues and Commit
  statuses read/write; Checks, Administration and Dependabot alerts read.
- **Install** on every repository that Renovate manages.
- **Ruleset bypass** on the pull-request ruleset, so Renovate can squash-merge its own green, in-policy PRs.
- The bot-side config lives in [`renovate-config`](https://github.com/bitwise-media-group/renovate-config). That
  repository's README covers the App in full.

## Setting the variable and secret

The private key must be the full PEM. Set both values at org level, visible to all repositories (or to the selected
repositories that use the App):

```sh
org=bitwise-media-group
gh variable set FF_MERGE_CLIENT_ID --org "$org" --visibility all --body "<client id>"
gh secret set FF_MERGE_PRIVATE_KEY --org "$org" --visibility all < ff-merge.private-key.pem
```

`gh secret set --org` needs the `admin:org` scope: run `gh auth refresh -h github.com -s admin:org` first.

## macOS notarization secrets

`release.yaml` also reads five **secrets** (not an App) to sign and notarize darwin binaries. They are org secrets
scoped to the repositories that notarize. See [macOS notarization](macos-notarization.md).
