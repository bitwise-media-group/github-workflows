---
description: Step-by-step wiring of a repository onto the reusable workflows.
---

# Adopting the workflows

This walk-through sets up a repository with the whole library. Every step stands alone, so skip any workflow you don't
need.

## 1. Put the mise contract in place

CI, release and docs all run `mise run <task>`, so the repository needs a mise config before anything else. The usual
setup mounts the shared toolchain as a submodule, on its latest
[release](https://github.com/bitwise-media-group/toolchain/releases) tag, and includes the task file for the
repository's language:

```sh
git submodule add -b vX.Y.Z https://github.com/bitwise-media-group/toolchain.git .mise
```

```toml title="mise.toml"
[task_config]
includes = [".mise/common/tasks.toml", ".mise/archetypes/go/tasks.toml"]
```

A Markdown/YAML repository with nothing to compile includes only `common/`. Check that the canonical tasks exist with
`mise tasks ls`. CI runs `lint`, `build` and `test` when they are defined and skips any that aren't. See
[the mise contract](../concepts/mise-contract.md).

## 2. Copy the callers

Copy each caller you want from [`examples/`](https://github.com/bitwise-media-group/github-workflows/tree/main/examples)
into `.github/workflows/`, keeping the file names:

```sh
for wf in ci security release merge merge-review-ack merge-notice add-to-project renovate; do
  curl -fsSL "https://raw.githubusercontent.com/bitwise-media-group/github-workflows/main/examples/$wf.yaml" \
    -o ".github/workflows/$wf.yaml"
done
```

Change what the caller owns to suit the repository:

- **`ci.yaml`**: add `e2e: true` if the repository defines an `e2e` task, or `coverage: false` if it emits no coverage.
- **`security.yaml`**: pass `config-file` if the repository commits a bundled `dist/`, and `languages` to pin the CodeQL
  matrix.
- **`release.yaml`**: set `vanity-tags: true` for an Action or reusable-workflow repository. Drop it for binaries pinned
  to exact versions.
- **`merge.yaml`**: list **every** workflow that must pass in `workflow_run.workflows`, using each workflow's `name:`,
  plus `Merge Review Ack`.

## 3. Pin the library

Each `uses:` line in an example points at an all-zeros placeholder SHA, with the release it stands for in a trailing
comment. Replace the zeros with that release's commit:

```sh
git ls-remote https://github.com/bitwise-media-group/github-workflows refs/tags/vX.Y.Z
```

The [pinning guide](pinning.md) explains the policy and how Renovate takes over from here.

## 4. Grant the org prerequisites

| Workflow              | Needs                                                                                                            |
| --------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `merge.yaml`          | "FF Merge" App installed and in the ruleset bypass list; `FF_MERGE_CLIENT_ID` / `FF_MERGE_PRIVATE_KEY`           |
| `add-to-project.yaml` | "Project Sync" App installed; `ADD_TO_PROJECT_CLIENT_ID` / `ADD_TO_PROJECT_PRIVATE_KEY`                          |
| `renovate.yaml`       | "Renovate" App installed; `RENOVATE_CLIENT_ID` / `RENOVATE_PRIVATE_KEY`; repo out of the org bot's autodiscovery |
| `release.yaml`        | optional: the FF Merge App (auto-merged release PRs, Homebrew casks); `MACOS_*` secrets for notarization         |

The variables and secrets are org-level, so a new repository normally only needs the Apps installed on it. See
[GitHub Apps & secrets](../setup/apps.md) for the one-time org setup.

## 5. Configure the repository

- **Branch protection / rulesets** on `main` that require a pull-request review. The merge flow depends on the review
  decision.
- **Release config**: `release-please-config.json` and `.release-please-manifest.json` at the root.
- **Docs** (optional): a `zensical.toml` with `pyproject.toml` and `uv.lock`, plus **Settings → Pages → Source → GitHub
  Actions**.
- **Codecov** (optional): connect the repository in Codecov if `ci.yaml` uploads coverage.

## 6. Open a pull request

The first PR exercises CI and Security Analysis, the merge notice comment appears, and an approval followed by `/merge`
(or `/auto-merge`) lands it. Merging it to `main` runs Release, which opens the first release PR.
