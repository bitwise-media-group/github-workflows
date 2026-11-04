---
description: Why every workflow runs `mise run <task>`, which tasks it expects, and where the toolchains come from.
---

# The mise contract

The reusable workflows know nothing about Go, Node or Python. They run **mise tasks**, and the repository's mise config
decides what those tasks do and which tool versions they use. The mise config is the boundary between the workflows and
the language.

## The canonical tasks

| Task         | Run by                      | Expected to                                                                                                          |
| ------------ | --------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `lint`       | `ci.yaml`                   | all check-mode static analysis: `prettier --check`, markdownlint, `go vet`, …                                        |
| `build`      | `ci.yaml`                   | compile, or rebuild `dist/`. A committed `dist/` must match afterwards                                               |
| `test`       | `ci.yaml`                   | run tests, writing `coverage/cobertura-coverage.xml` or `coverage/coverage.out`, and optionally `coverage/junit.xml` |
| `e2e`        | `ci.yaml` with `e2e: true`  | end-to-end tests                                                                                                     |
| `release`    | `release.yaml` (GoReleaser) | `goreleaser release --clean`. The workflow appends `--draft`. Must leave the tree clean                              |
| `docs-build` | `release.yaml` (docs)       | render the Zensical site into `./site`                                                                               |

Define only the tasks that do real work. `ci.yaml` runs `mise tasks ls --name-only` and skips the rest, so there are no
no-op stubs. `release` and `docs-build` are different: a `.goreleaser.yaml` without `release`, or a `zensical.toml`
without `docs-build`, is a broken contract and fails the job.

## Where the config comes from

Most repositories mount the shared [toolchain](https://github.com/bitwise-media-group/toolchain) as a git submodule at
`.mise/`. mise loads `.mise/config.toml` natively, which brings the pinned tools, `mise.lock` checksums and settings.
The repository's root `mise.toml` picks the task files:

```toml title="mise.toml"
[task_config]
includes = [".mise/common/tasks.toml", ".mise/archetypes/go/tasks.toml"]
```

- `common/` gives every repository `fmt`, `lint` (prose, licence headers, workflows, shell, containers), `docs-build`
  and `serve`.
- An **archetype** (`go`, `node`, `python`, `swift`, `terraform`) adds the language's `build`, `test`, `release`, and so
  on.
- A repository-local task file, or `[tasks]` in `mise.toml`, can redefine any task. The last definition wins.

A repository can also skip the toolchain and define everything in a root `mise.toml`. The workflows only care that
`mise.toml` or `.mise/config.toml` exists and that the tasks resolve.

The workflows check out submodules (`submodules: true`) wherever they run tasks, so `.mise/` is always there.

## Toolchains come from the pins

There is no `setup-go`, `setup-node` or `setup-uv` anywhere in the library. Each job that runs tasks:

1. installs a **pinned mise binary** whose sha256 is checked by `jdx/mise-action`;
2. installs the repository's tools, each **verified against `mise.lock`** (`--locked` is automatic). Lazy pins such as
   goreleaser, cosign, syft and uv install the first time a task uses them;
3. caches them by config hash. The release-signing job is the exception and never uses a cache.

CI, release and a developer's laptop therefore run **identical tool versions**. Upgrading Go or a linter means bumping a
pin, usually by bumping the toolchain submodule tag, which Renovate does.

Tasks install their own project dependencies (`npm ci`, `go mod download`, `uv sync`). The workflows never do.

## Detection signals

Several workflows choose a path based on which files exist at the repository root:

| File                                        | Effect                                                                  |
| ------------------------------------------- | ----------------------------------------------------------------------- |
| `mise.toml` / `.mise/config.toml`           | required by `ci.yaml`. Without either it fails                          |
| `dist/**`                                   | `ci.yaml` checks it is unchanged after `build`                          |
| `go.mod` (root only)                        | `security.yaml` adds the `go` CodeQL leg                                |
| `package.json`                              | `security.yaml` adds the `javascript-typescript` leg                    |
| `zizmor.y{a,}ml` / `.github/zizmor.y{a,}ml` | `security.yaml` runs zizmor on the `actions` leg                        |
| `.goreleaser.y{a,}ml`                       | `release.yaml` runs the `goreleaser` job                                |
| `Dockerfile` / `Dockerfile.*`               | `release.yaml` sets up QEMU, buildx and ghcr, and attests image digests |
| `zensical.toml`                             | `release.yaml` runs the `docs` job                                      |

A `go.work` with a `tools/go.mod` (for `go tool addlicense`) is shared dev tooling. It does **not** count as Go product
code.
