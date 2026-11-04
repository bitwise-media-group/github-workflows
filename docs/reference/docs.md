---
description: How this site is built, what is generated versus hand-written, and how to keep it current.
---

# Working on the docs

This site is built with [Zensical](https://zensical.org), using uv and the shared toolchain. Its look comes from the
[toolchain site](https://oss.bitwisemedia.uk/toolchain/): the same `docs/stylesheets/extra.css` tokens and header
partials, with a landing page in `overrides/home.html`.

```sh
mise run serve        # http://localhost:8007, live reload for docs/ edits
mise run docs-build   # render into site/
```

Both commands regenerate the workflow references first. Restart `serve` after editing a workflow to pick up the new
facts.

## Generated vs hand-written

Each page in `docs/workflows/` is hand-written prose (what the workflow does, how it works, what it needs,
troubleshooting) plus `--8<--` includes of material that must never be copied by hand:

| Include                                     | Source                                                             |
| ------------------------------------------- | ------------------------------------------------------------------ |
| `build/workflow-docs/<name>/interface.md`   | the workflow's `workflow_call` inputs, secrets and outputs         |
| `build/workflow-docs/<name>/permissions.md` | the union of its jobs' `permissions:`, which the caller must grant |
| `build/workflow-docs/<name>/jobs.md`        | its jobs, their `needs:`, permissions and `if:` conditions         |
| `build/workflow-docs/<name>/actions.md`     | every SHA-pinned action it `uses:`, with the version comment       |
| `build/workflow-docs/index.md`              | the catalogue's at-a-glance table                                  |
| `examples/<name>.yaml`                      | the copy-paste caller, embedded verbatim                           |

`scripts/workflow_docs.py` writes the `build/` fragments, which are git-ignored. `pymdownx.snippets` runs with
`check_paths`, so including a fragment that doesn't exist fails the build.

The generator also **enforces coverage**. It fails when:

- a reusable workflow (any `.github/workflows/*.yaml` except `self-*`) has no `docs/workflows/<name>.md`;
- that page isn't in `zensical.toml`'s nav under **Workflows**;
- a page in `docs/workflows/` matches no workflow, for example after a rename or removal.

## Keeping the prose current

The generated tables can't go stale, but the prose can. When a workflow's **behaviour** changes (a new job, a changed
condition, a new requirement or failure mode), update in the same change:

- its page in `docs/workflows/`, especially **How it works**, **Requirements** and **Troubleshooting**;
- [The mise contract](../concepts/mise-contract.md) if a task or detection signal changed;
- [Permissions & tokens](../concepts/permissions.md) or [GitHub Apps & secrets](../setup/apps.md) if a scope or App
  changed;
- [Fast-forward merging](../concepts/fast-forward-merge.md) for any change to the merge trio;
- the catalogue summary in `docs/workflows/index.md` and the landing card's `description` front matter.

A new reusable workflow also needs a nav entry, a page (copy an existing one as a template) and an `examples/` caller.

## Pages that embed live files

Snippet paths resolve against `docs/` and the repository root (`base_path` in `zensical.toml`), so a page can embed any
repository file, such as `.github/zizmor.yaml`, with `--8<-- "<path>"` inside a fenced block.

## Linting

Prose under `docs/` follows the house prettier and markdownlint rules (`mise run lint`). `docs/.markdownlint.yaml` turns
off the fenced-code rule because admonition and tab bodies need indentation. `site/` and `build/` are excluded.

## Publishing

There is no separate docs workflow. The site is published by this library's own
[`release.yaml`](../workflows/release.md#docs), which `self-release.yaml` calls: on every release it detects
`zensical.toml`, runs `mise run docs-build` (this repository's override, which runs the generator first) and deploys
`./site` to GitHub Pages. The site therefore always describes the **latest release**. A `docs:` commit goes live with
the next `feat:` or `fix:` release.

CI builds the site on every PR (`mise run build`), so a broken page or an undocumented workflow fails before it merges.
Pages must be set to **Settings → Pages → Source → GitHub Actions**.
