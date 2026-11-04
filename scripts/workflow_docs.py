#!/usr/bin/env python3
# Copyright 2026 BitWise Media Group Ltd
# SPDX-License-Identifier: MIT

"""Render the reference fragments the docs site embeds, straight from the workflows.

Every reusable workflow in .github/workflows/ (everything except the self-* callers)
gets a directory of Markdown fragments under build/workflow-docs/<name>/:

  interface.md   -- workflow_call inputs, secrets and outputs
  permissions.md -- the permission ceiling the caller must grant (union over jobs)
  jobs.md        -- each job, what it needs, its permissions and its `if:` gate
  actions.md     -- every pinned action the workflow runs, with its version comment

plus build/workflow-docs/index.md, the at-a-glance catalogue table. The hand-written
pages under docs/workflows/ include these with `--8<--`, so the facts most likely to
drift -- inputs, defaults, permissions, action pins -- are never copied by hand.

The script also enforces the docs contract: every reusable workflow must have a page
at docs/workflows/<name>.md listed in zensical.toml's nav, and every page there must
correspond to a workflow. A missing or orphaned page fails the build.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
DOCS = ROOT / "docs" / "workflows"
OUT = ROOT / "build" / "workflow-docs"

LEVELS = {"none": 0, "read": 1, "write": 2}
USES = re.compile(r"uses:\s*([\w.-]+/[\w./-]+)@([0-9a-f]{40})(?:\s*#\s*(\S+))?")


def cell(text: object) -> str:
    """Flatten text into a single Markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


def default(spec: dict) -> str:
    if "default" not in spec:
        return "—"
    value = spec["default"]
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if value == "":
        return '`""`'
    return f"`{value}`"


def trigger(doc: dict) -> dict:
    # PyYAML follows YAML 1.1, where a bare `on` key parses as boolean True.
    on = doc.get("on", doc.get(True)) or {}
    return on.get("workflow_call") or {}


def job_permissions(job: dict, workflow_level: object) -> dict[str, str]:
    perms = job.get("permissions", workflow_level)
    if perms in (None, {}):
        return {}
    if isinstance(perms, str):
        # read-all / write-all shorthands; none of the library's workflows use them,
        # but render them honestly rather than as an empty grant.
        return {"(all scopes)": perms.removesuffix("-all")}
    return {k: str(v) for k, v in perms.items()}


def permission_list(perms: dict[str, str]) -> str:
    if not perms:
        return "none"
    return ", ".join(f"`{k}: {v}`" for k, v in sorted(perms.items()))


def interface(call: dict) -> str:
    out: list[str] = []

    inputs = call.get("inputs") or {}
    out.append("### Inputs\n")
    if inputs:
        out.append("| Input | Type | Required | Default | Description |")
        out.append("| ----- | ---- | -------- | ------- | ----------- |")
        for name, spec in inputs.items():
            spec = spec or {}
            out.append(
                f"| `{name}` | {spec.get('type', 'string')} | {'**yes**' if spec.get('required') else 'no'} "
                f"| {default(spec)} | {cell(spec.get('description', ''))} |"
            )
    else:
        out.append("None — the caller passes no `with:` block.")
    out.append("")

    secrets = call.get("secrets") or {}
    out.append("### Secrets\n")
    if secrets:
        out.append("| Secret | Required | Description |")
        out.append("| ------ | -------- | ----------- |")
        for name, spec in secrets.items():
            spec = spec or {}
            out.append(
                f"| `{name}` | {'**yes**' if spec.get('required') else 'no'} | {cell(spec.get('description', ''))} |"
            )
    else:
        out.append("None — the caller passes no `secrets:` block.")
    out.append("")

    outputs = call.get("outputs") or {}
    if outputs:
        out.append("### Outputs\n")
        out.append("| Output | Description |")
        out.append("| ------ | ----------- |")
        for name, spec in outputs.items():
            out.append(f"| `{name}` | {cell((spec or {}).get('description', ''))} |")
        out.append("")

    return "\n".join(out)


def ceiling(doc: dict) -> dict[str, str]:
    """The union of every job's permissions: what GitHub demands of the caller."""
    union: dict[str, str] = {}
    for job in (doc.get("jobs") or {}).values():
        for scope, level in job_permissions(job, doc.get("permissions")).items():
            if LEVELS.get(level, 0) > LEVELS.get(union.get(scope, "none"), 0):
                union[scope] = level
    return union


def permissions(doc: dict) -> str:
    union = ceiling(doc)
    if not union:
        return (
            "The caller grants **nothing** — set `permissions: {}` on the calling workflow. "
            "No job here uses its `GITHUB_TOKEN` for anything privileged.\n"
        )
    lines = ["```yaml", "permissions:"]
    lines += [f"  {scope}: {level}" for scope, level in sorted(union.items())]
    lines.append("```")
    return (
        "GitHub validates a reusable workflow's permissions as the **union of every job**, ignoring `if:`, so the "
        "caller must grant all of these even when the jobs that need them are skipped:\n\n" + "\n".join(lines) + "\n"
    )


def jobs(doc: dict) -> str:
    rows = ["| Job | Needs | `GITHUB_TOKEN` permissions |", "| --- | ----- | -------------------------- |"]
    gates: list[str] = []
    for name, job in (doc.get("jobs") or {}).items():
        needs = job.get("needs") or []
        if isinstance(needs, str):
            needs = [needs]
        rows.append(
            f"| `{name}` | {', '.join(f'`{n}`' for n in needs) or '—'} "
            f"| {permission_list(job_permissions(job, doc.get('permissions')))} |"
        )
        if "if" in job:
            gates.append(f"{name}:\n  {' '.join(str(job['if']).split())}")
    text = "\n".join(rows) + "\n"
    if gates:
        text += '\n??? info "Job conditions (`if:`), verbatim"\n\n    ```yaml\n'
        for gate in gates:
            text += "".join(f"    {line}\n" for line in gate.splitlines())
        text += "    ```\n"
    return text


def actions(source: str) -> str:
    seen: dict[tuple[str, str], str] = {}
    for action, sha, version in USES.findall(source):
        seen.setdefault((action, sha), version or "—")
    if not seen:
        return "This workflow runs no third-party actions.\n"
    rows = ["| Action | Version | Commit |", "| ------ | ------- | ------ |"]
    for (action, sha), version in sorted(seen.items()):
        repo = "/".join(action.split("/")[:2])
        rows.append(f"| [`{action}`](https://github.com/{repo}) | {version} | `{sha[:12]}` |")
    return "\n".join(rows) + "\n"


def nav_pages(config: dict) -> set[str]:
    pages: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, str):
            pages.add(node)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)

    walk(config.get("project", {}).get("nav", []))
    return pages


def main() -> int:
    workflows = sorted(p for p in WORKFLOWS.glob("*.yaml") if not p.name.startswith("self-"))
    names = {p.stem for p in workflows}
    nav = nav_pages(tomllib.loads((ROOT / "zensical.toml").read_text()))

    errors: list[str] = []
    for name in sorted(names):
        if not (DOCS / f"{name}.md").is_file():
            errors.append(f"{name}.yaml has no page: add docs/workflows/{name}.md")
        if f"workflows/{name}.md" not in nav:
            errors.append(f'{name}.yaml is not in the nav: add {{ "{name}.yaml" = "workflows/{name}.md" }} to zensical.toml')
    for page in sorted(DOCS.glob("*.md")):
        if page.stem != "index" and page.stem not in names:
            errors.append(f"docs/workflows/{page.name} documents no reusable workflow (renamed or removed?)")
    if errors:
        for error in errors:
            print(f"workflow_docs: {error}", file=sys.stderr)
        return 1

    catalogue = [
        "| Workflow | Required inputs | Secrets | Caller grants |",
        "| -------- | --------------- | ------- | ------------- |",
    ]
    for path in workflows:
        source = path.read_text()
        doc = yaml.safe_load(source)
        call = trigger(doc)
        target = OUT / path.stem
        target.mkdir(parents=True, exist_ok=True)
        (target / "interface.md").write_text(interface(call))
        (target / "permissions.md").write_text(permissions(doc))
        (target / "jobs.md").write_text(jobs(doc))
        (target / "actions.md").write_text(actions(source))

        required = [f"`{k}`" for k, v in (call.get("inputs") or {}).items() if (v or {}).get("required")]
        secrets = [
            f"`{k}`" + ("" if (v or {}).get("required") else " (optional)")
            for k, v in (call.get("secrets") or {}).items()
        ]
        catalogue.append(
            f"| [`{path.name}`]({path.stem}.md) | {', '.join(required) or '—'} | {', '.join(secrets) or '—'} "
            f"| {permission_list(ceiling(doc))} |"
        )

    (OUT / "index.md").write_text("\n".join(catalogue) + "\n")
    print(f"workflow_docs: rendered {len(workflows)} workflows into {OUT.relative_to(ROOT)}/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
