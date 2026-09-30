# Updating skills.sh / GitHub-tap skills — and the `npx skills` CLI next to them

The source that `hermes skills update` handles best. A three-segment identifier
(`owner/repo/path`) is usually resolved by the **skills.sh** adapter — which is a GitHub fetch wearing a
relabelled badge — and a custom **tap** install records source `github`. Both land in `GitHubSource`,
and that is what makes them special among the five hub sources:

> **Source: skills.sh is not where the content came from.** For everything real, read
> `metadata.source_url` in the lock: it is a `https://github.com/<owner>/<repo>/tree/<commit>/<path>`
> URL, and `metadata.source_revision` carries the same commit. Those two fields are what let `check`
> answer without downloading anything.

Measured lock entry (this machine, 2026-09-30):

```json
"install-hermes-skills": {
  "source": "skills.sh",
  "identifier": "skills-sh/flmaximwang/AgentSkill-UsingHermes/skills/install-hermes-skills",
  "trust_level": "community", "scan_verdict": "safe",
  "content_hash": "sha256:9d28f98f0c1efa3b",
  "install_path": "hermes/install-hermes-skills",
  "metadata": {
    "source_url": "https://github.com/flmaximwang/AgentSkill-UsingHermes/tree/e9cac54831fec7957b57e74b2e721058770ac839/skills/install-hermes-skills",
    "source_revision": "e9cac54831fec7957b57e74b2e721058770ac839",
    "detail_url": "https://skills.sh/flmaximwang/AgentSkill-UsingHermes/skills/install-hermes-skills",
    "repo_url": "https://github.com/flmaximwang/AgentSkill-UsingHermes"
  },
  "files": 6, "scan_provenance": {"scanner_version": "skills-guard-v7"}
}
```

`github` (tap) entries carry the same two fields and nothing else (`anthropics/skills/skills/
skill-creator` → `source_url` + `source_revision: 8a1541c4…`). No other source does this:
`clawhub` and `official` entries have `metadata: {}`, and `url` entries store only the URL they were
fetched from. See the Cost table in `SKILL.md`.

## The update loop, and what one real run looks like

```bash
hermes skills check <name>      # read-only; expect `up_to_date` or `update_available`
hermes skills update <name>     # apply; add --force only to overwrite local edits
hermes skills check <name>      # confirm it flipped to up_to_date
```

Measured end to end on 2026-09-30, updating this repo's own `install-hermes-skills` after the upstream
repository had moved on:

```
$ hermes skills update install-hermes-skills
Updating: install-hermes-skills        # revision eb7dd5c… → e9cac54…, resolved from the lock's source
Scan: install-hermes-skills  Verdict: SAFE          # scanner skills-guard-v7
  MEDIUM  supply_chain  references/install-hermes-skills-from-github.md:270
  LOW     persistence   references/install-hermes-skills-from-github.md:371
Updated 1 skill(s).
$ hermes skills check install-hermes-skills
│ install-hermes-skills │ skills.sh │ up_to_date │        # 0 update(s) available, 11.6 s
```

What the run proves, beyond "it worked":

- **the revision moved** (`eb7dd5c… → e9cac54…`) and `content_hash` became `sha256:9d28f98f0c1efa3b`;
- **6 files on disk, matching the lock's 6-item `files` list** — the whole tree was replaced;
- **deletions propagate**: the previous version shipped a `scripts/auto-generate-skill-structure.py`
  that upstream had since removed, and the installed copy lost it too (the rendered `Skill Structure`
  block lost that node, and `SKILL.md` went 171 → 169 lines);
- **`community` + `safe` needed no `--force`** — a first install of the same skill also needed none;
- the two findings are the same two the first install reported (a `git clone` example in the tool's own
  reference docs, and a `~/.hermes/config.yaml` path) — an update does **not** re-gate on them, because
  `do_update` calls `do_install(..., force=True)` internally;
- new content is visible to a running session only after `/reload-skills` or a session restart.

## Cost

Every `check` here is a GitHub API round trip even on the fast path: `current_revision` compares the
lock's `source_revision` against the tree's current revision, and only a match short-circuits the
download (`tools/skills_hub_github.py:300`, consumed at `tools/skills_hub_install.py:302-308`).
Measured: `github` 3.3 s, `skills.sh` 9.5–11.9 s per skill. So check named skills, not the whole lock.

## When an update is skipped — one self-authored file poisons the whole bundle

`_has_local_edits` hashes **the whole installed directory** (`hermes_cli/skills_hub.py:887-897`), so a
single file you added anywhere inside it makes every future update skip. Measured on this machine while
looking at `paper2agent`:

```
recorded    : sha256:c20a6094082b688a
on disk     : sha256:a402940d576fcc75
local_edits : True        # _has_local_edits() re-run, skills_hub.py:852 in that build
```

The file responsible was a self-authored skill (`paper2skill-delivery-checks`, `author: Hermes Agent`)
sitting **inside** the installed bundle. Consequences:

```
$ hermes skills update paper2agent
Skipping: paper2agent — you have local edits (update would overwrite them).
$ hermes skills update paper2agent --force
# …which replaces the bundle wholesale, deleting the self-authored skill too.
```

The remedy is structural, not a flag: **keep self-authored skills outside any hub-installed
directory** (its own `<category>/<name>/`, not nested in a bundle). Then the bundle stays pristine and
`update` stays plain. If the bundle *is* nested in a tree you author, expect to reinstall rather than
update.

## Nested sub-skill trees

One install can bring several `SKILL.md` files if the fetched directory has sub-directories with their
own. The hub identity stays single — the parent — and the children show up in `list` as `local`:

```
$ hermes skills list
paper2agent        |             | skills.sh | community | enabled
paper2agent-paper  | paper2agent | local     | local     | enabled
paper2mcp          | paper2agent | local     | local     | enabled
paper2skill        | paper2agent | local     | local     | enabled
```

So `hermes skills update paper2agent` moves all four, `hermes skills uninstall paper2agent -y` removes
all four (measured: no leftovers on disk), and no child is separately updatable. Updating a child by
name is not a thing — it has no lock entry.

## Private repositories

The three-segment route reads the repository through the GitHub API using the profile's stored
credentials, so a **private** repo installs and updates normally — the `Source:` badge still says
`skills.sh`. Measured on this user's private skill repos: `inspect` may report
`Could not find '<identifier>' in any source.` when the anonymous probe 404s, while `install` of the
same identifier succeeds (the bundle arrives, `meta=None`). Do not treat that inspect failure as "the
skill does not exist" for a private repo; check `hermes skills list` / the lock afterwards.

## The workflow that keeps these skills updatable

Push to the upstream repo, then `hermes skills update <name>`. Never edit the installed copy to make a
change: that instantly converts the skill into "local edits", and every later update skips it until
someone passes `--force` — at which point the edit is gone. The repository is the edit surface; the
installed copy is a read-only follower pinned to a commit.

## The `npx skills` CLI — same registry, a different updater

`npx skills add <owner>/<repo> --skill <name>` (the command a skills.sh page offers) installs through
the skills CLI, **not** the hub. Hermes is a first-class target of that CLI (`skillsDir:
".hermes/skills"`), but the bookkeeping is its own:

| | `hermes skills` hub | `npx skills` CLI |
|---|---|---|
| lock | `<HERMES_HOME>/skills/.hub/lock.json` | `~/.agents/.skill-lock.json` |
| update | `hermes skills update <name>` | `npx skills update -g -y` |
| change detection | bundle `content_hash` | commit hash (`skillFolderHash`) |
| canonical copy | the installed dir | `~/.agents/skills/<name>`, then a copy or a symlink into the agent dir |

Measured: `hermes skills check cangjie-skill` for an npx-installed copy → `No hub-installed skills to
check.` — the hub genuinely cannot see it. The CLI's own updater can: a clean run prints
`✓ All global skills are up to date`, and after corrupting the recorded hash to zeros it reported
`Found 1 global update(s) → ✓ Updated cangjie-skill` and rewrote the true hash `874eb414…` — so it
compares by commit and really re-downloads.

**Sandbox trap, measured the hard way.** The CLI resolves its target as

```js
const hermesHome = process.env.HERMES_HOME?.trim() || join(home, ".hermes");   // cli.mjs:1400
```

so pointing `HOME` at a scratch directory does **not** sandbox it — with `HERMES_HOME` still aimed at
the real profile, an `npx skills add` wrote a 367-file repository copy into the live
`~/.hermes/skills/`. Set `HERMES_HOME` when you need isolation. To keep such a skill current on a
schedule, run `npx skills update -g -y` (cron or a Hermes cron job) — `hermes skills update` is never
the right tool for it.
