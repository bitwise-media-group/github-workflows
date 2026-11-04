---
description: Adds newly opened issues to the org's Projects v2 Roadmap board with a short-lived Project Sync App token.
---

# `add-to-project.yaml`

**Reusable Add to Project.** Adds the triggering issue or pull request to a shared organisation **Projects v2** board,
the org Roadmap, so new issues from every repository end up on one board.

!!! abstract "At a glance"

    - **Caller triggers:** `issues` (`opened`), or any event that carries an issue or PR
    - **Caller grants:** nothing (`permissions: {}`)
    - **Secrets:** `app-private-key` (`ADD_TO_PROJECT_PRIVATE_KEY`)
    - **Org setup:** the "Project Sync" App, installed on all repositories

## How it works

`GITHUB_TOKEN` can't write to an **organisation-level** project, so the single `add` job:

1. mints a short-lived installation token from the **Project Sync** App, with only `organization-projects: write`,
   `issues: read` and `pull-requests: read`;
2. hands it to [`actions/add-to-project`](https://github.com/actions/add-to-project), which resolves the issue's node ID
   and adds it to `project-url`, optionally filtered by `labeled` / `label-operator`.

Organisation permissions come with the installation token, so the token isn't narrowed to specific repositories. The App
does have to be installed on the repository whose issue fired the caller.

In this organisation the caller is copied to every repository by `org-config.sh workflows-sync` in
[`github-settings`](https://github.com/bitwise-media-group/github-settings), so new repositories get it without anyone
adding it by hand.

## Requirements

- The **Project Sync** GitHub App: organisation **Projects** read/write, repository **Issues** and **Pull requests**
  read, installed on **all repositories**. It's exposed as the org variable `ADD_TO_PROJECT_CLIENT_ID` and secret
  `ADD_TO_PROJECT_PRIVATE_KEY`. See [GitHub Apps & secrets](../setup/apps.md#project-sync).
- The project URL, `https://github.com/orgs/<org>/projects/<n>`.

## Interface

--8<-- "build/workflow-docs/add-to-project/interface.md"

## Permissions

--8<-- "build/workflow-docs/add-to-project/permissions.md"

## Caller

```yaml title=".github/workflows/add-to-project.yaml"
--8<-- "examples/add-to-project.yaml"
```

## Jobs and pinned actions

--8<-- "build/workflow-docs/add-to-project/jobs.md"

--8<-- "build/workflow-docs/add-to-project/actions.md"

## Troubleshooting

The token step fails : The Project Sync App isn't installed on this repository, or the client ID and key don't match.
Install it on all repositories and check the org variable and secret.

`Resource not accessible by integration` : The App lacks organisation **Projects: read and write**, or the project
belongs to a different organisation.
