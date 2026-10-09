---
name: hermes-projects
description: "Use when editing a Hermes Project's folder list."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Hermes, Projects, Workspaces, Desktop, CLI]
    category: autonomous-ai-agents
    related_skills: [session-librarian, gateway-operations, protein-design-pipeline-conventions]
---

# Hermes Projects (named multi-folder workspaces)

A Hermes **Project** is a named workspace row set — a name, a slug, and a list of
folders. It groups desktop sessions in the sidebar and can bind a kanban board. Its
state is a SQLite DB, NOT a directory.

## When to Use

- "Add / remove this repo from the <X> project", "which folders does project Y hold",
  "make Z the primary folder", "delete the folder I added to the <X> project".
- Any request that names a project while pointing at the desktop app, the sidebar, or a
  repo path that is also a folder of a project.
- Before answering, run Step 0: the same word "project" can mean a git repo or a design
  pipeline, and answering the wrong layer is the failure mode this skill exists to stop.

## Step 0 — Disambiguate what "project" means (do this first)

The same word names three unrelated things in this user's world:

| Meaning | Tell in the request | Right tool |
|---|---|---|
| Hermes Project (workspace row) | desktop app, sidebar, 项目, which repos a project holds | `hermes project ...` CLI / `projects.db` |
| Git repo (e.g. `Repositories/BioRazer`) | commit, push, .gitignore, tracked | `git rm -r` / plain `rm -rf` |
| Design pipeline (`pipelines/pipeline-a.b.c`) | steps, main.sh, worktrees | protein-design-pipeline-conventions |

If the request is genuinely ambiguous ("how do I delete the folder in the BioRazer
project?" while cwd is that repo), ask which layer in one line — **do not answer the
repo version.** Answering a neighbouring question confidently is the failure mode here;
the correct answer was three CLI verbs away and the git answer was not merely
incomplete but wrong.

## Step 1 — Enumerate the real state before proposing anything

```bash
hermes -p <profile> project list          # add --all to include archived
hermes -p <profile> project show <slug>   # id, primary, every folder
```

Need ordering or timestamps (which folder is primary, which was added when), read the
DB directly:

```bash
sqlite3 "$HOME/.hermes/profiles/<profile>/projects.db" \
  "SELECT path, is_primary, datetime(added_at,'unixepoch','localtime') \
   FROM project_folders WHERE project_id='<p_xxxx>' ORDER BY added_at;"
```

Report the folder list these reads actually return, not a generic how-to.

## Step 2 — Mutate with the CLI (`hermes project`)

| Verb | Effect |
|---|---|
| `create <name> [folders...] [--slug --primary --board --use]` | New project; first folder argument becomes primary |
| `add-folder <project> <path> [--label L] [--primary]` | Add a repo/folder |
| `remove-folder <project> <path>` | Drop the folder from the project |
| `set-primary <project> <path>` | Folder must already be in the project |
| `rename <project> <name>` / `use [project]` / `archive` / `restore` / `bind-board [slug]` | Project-level ops |

`<project>` accepts id or slug. The agent-facing `desktop_project` tool only
creates / switches / lists projects — folder edits are CLI-only.

## Step 3 — Verify

```bash
hermes -p <profile> project show <slug>
```

The changed folder line is gone / present. Removal prints `Removed <path> from <slug>`;
a folder that is not in the project returns `folder not in project: <path>` with a
non-zero exit — not a silent no-op, so check it.

## Pitfalls

- **Always pass `-p <profile>`.** Project state is per-profile
  (`projects_db_path()` = `get_hermes_home()/projects.db`). Inside a Hermes-spawned
  shell `HERMES_HOME` already points at the active profile, so a bare
  `hermes project ...` *looks* right there and writes the **default** profile's DB from
  the user's own terminal. Same command, wrong DB, no error.
- **`remove-folder` deletes a DB row, not a directory.** Files on disk are untouched
  (`DELETE FROM project_folders ...`). Never phrase it as deleting the folder, and never
  follow it with `rm -rf` unless both were asked for.
- **Removing the primary silently repoints it** to `ORDER BY added_at ASC LIMIT 1`. Folders
  added in one batch share the same `added_at` second, so which one wins is an arbitrary
  SQLite tie-break. Re-run `project show` and fix with `set-primary` if it picked wrong.
- **The desktop app cannot remove a folder.** The project dialog renders the folder list
  with remove buttons only in create mode, and the renderer calls `projects.add_folder`
  but never `projects.remove_folder` — though the backend RPC exists (other clients may
  differ). Verify before asserting: grep the desktop source for `projects.remove_folder` /
  `removeFolder`. After a CLI change the renderer's cached `projects.list` still shows the
  old list until a refresh/reopen.
- **Paths are normalized** (abspath + expanduser + trailing-separator strip), so `~/x`,
  a relative path, and a trailing-`/` form all match. On default APFS a case-only
  difference is the same entry.
- **One folder can belong to several projects.** The key is `(project_id, path)`, so
  removing it from one project leaves the others untouched — say that instead of implying
  the repo left Hermes entirely.
- **A folder is not the session grouping.** Sessions attach to one folder via
  `projects.move_*`; deleting a folder row does not move or delete those sessions. Check
  `project show` + the sidebar before promising an outcome.

## Working style for this user

- Give the command, the expected output, and the verification command — he runs mutating
  commands himself. Offer to run it, don't run it unasked.
- Cite the source that proves a behavior claim (`hermes_cli/projects_db.py:334` beats "it
  deletes the row"). He checks.
- End with the real state: which folders exist now, what changed, what to run next.

## Where the truth lives (the running install's source tree)

- `hermes_cli/projects_db.py` — schema (`projects`, `project_folders`, `project_meta`,
  `discovered_repos`), `add_folder` / `remove_folder` / `set_primary` / path normalization.
- `hermes_cli/projects_cmd.py` — the `hermes project` parser, verbs, printed output strings.
- `tui_gateway/methods_projects.py` + `tui_gateway/contracts/projects_pets.py` — the RPC
  surface the desktop and TUI call.
- `apps/desktop/src/store/projects.ts`, `apps/desktop/src/app/chat/sidebar/project-dialog.tsx`
  — which RPCs the desktop actually issues, and dialog modes.
