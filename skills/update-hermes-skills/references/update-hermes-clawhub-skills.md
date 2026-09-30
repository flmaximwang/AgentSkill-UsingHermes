# Updating ClawHub (`@publisher/slug`) skills

ClawHub is the third-party registry Hermes reaches through the `clawhub` adapter
(`tools/skills_hub_clawhub.py`, `BASE_URL = https://clawhub.ai/api/v1`). Its identifiers look like
`@<publisher>/<slug>`, its trust level is **always `community`** (the adapter's own docstring says why),
and its update path has one property the other sources do not have:

> **A ClawHub entry cannot tell a version bump from a different skill wearing the same slug.** The lock
> stores no revision and no version — only the slug and publisher — so `update` compares bundle bytes
> and nothing else. Read the frontmatter before accepting an update.

Measured lock entry (this machine, 2026-09-30) — note `metadata: {}`:

```json
"cangjie-skill": {
  "source": "clawhub",
  "identifier": "@terrybenedict0515/cangjie-skill",
  "trust_level": "community", "scan_verdict": "safe",
  "content_hash": "sha256:a868d31f16b2b1c3",
  "install_path": "agent-evolution/cangjie-skill",
  "files": 21
}
```

`clawhub/skillopt` and the `official/*` entries have `metadata: {}` as well. Compare `skills.sh` /
`github` entries, which record `source_url` + `source_revision`.

## Consequence 1 — every check is a full download

`current_revision` is implemented only by `GitHubSource` (`tools/skills_hub_github.py:300`); the base
class returns `""` (`tools/skills_hub_models.py:154-157`), and a fast path would additionally need a
recorded revision, which ClawHub never writes. So each `check` re-resolves the newest version
(`_resolve_latest_version`, `skills_hub_clawhub.py:357-370`), re-downloads the ZIP, and re-hashes it.
Measured: `hermes skills check cangjie-skill` → `up_to_date` in **8.9 s**. Scope checks by name.

## Consequence 2 — the version is in the package, not in the lock

The installed directory carries a `_meta.json` the adapter wrote at fetch time. Measured:

```
$ cat ~/.hermes/skills/agent-evolution/cangjie-skill/_meta.json
{"ownerId": "kn73v3qf2r4dbre319rz829p0d82msxd", "slug": "cangjie-skill",
 "version": "1.0.0", "publishedAt": 1781784343470}
```

So to answer "what version do I have, and what is upstream now", read `_meta.json` and then ask the
registry: `GET https://clawhub.ai/api/v1/skills/<slug>` (`stats.versions`, `updatedAt`). The lock will
not tell you.

## The lineage trap — compare the frontmatter, not the slug

The measured case this reference exists for: `cangjie-skill` on ClawHub is **not** the same skill as the
GitHub repository of that name.

| | ClawHub `@terrybenedict0515/cangjie-skill` | GitHub `kangarooking/cangjie-skill` |
|---|---|---|
| frontmatter `name` | `book2skill` | `cangjie-skill` |
| version | `2.0.0` | `cangjie-skill: 2.5.0` |
| author line | 花叔 AlchainHust (原版) · mac-openclaw-manager (改造版) | kangarooking |
| files | `methodology/` present, **no `scripts/`, no `templates/`** | ships `scripts/cangjie.py`, `methodology/03b-…` |
| size | `SKILL.md` 184 lines | `SKILL.md` 184 lines — **230 lines of diff** |

Same slug, same line count, different skill. Rule: after an update, compare the frontmatter `name` and
`version`. **A changed `name` is a different lineage, not a new version** — treat that update as a
replacement decision (and keep a copy if the old one is what you wanted).

## The three-names problem, and which name the commands take

A ClawHub skill has up to three names: the registry display name, the frontmatter `name`, and the
slug (which becomes the lock key and the install directory). Measured on `cangjie-skill`:
`hermes skills list` renders it as `book2skill | local | local | enabled` — because it matches by
frontmatter name, so the hub entry looks unmanaged — while `hermes skills check cangjie-skill` works
(`clawhub | up_to_date`). So:

- **hub commands (`check`, `update`, `audit`, `uninstall`) take the lock key** — the slug;
- **the agent's own skill list takes the frontmatter `name`**.

Renaming the directory/lock key to match the frontmatter is a real option but a separate decision; back
up the lock first.

## Update mechanics — the shared ones

Nothing ClawHub-specific happens on update: `do_update` runs the standard sequence (check →
local-edits test → `do_install(..., force=True, source_id="clawhub")`), so a ClawHub skill is skipped
when locally edited, needs `--force` to be overwritten, is replaced as a whole directory, and updates
with the security gate bypassed but the scan re-recorded. Two registry-specific notes:

- **the publisher segment is load-bearing**: slugs can be ambiguous across publishers (the API returns
  `409 AMBIGUOUS_SKILL_SLUG`, and the adapter disambiguates with `?owner=`, `skills_hub_clawhub.py:139`),
  so the recorded `@publisher` is exactly what a check will query again;
- **hard size limit** `ZIP_DOWNLOAD_MAX_BYTES = 25 MiB` (`:70`), and the catalog walk budget is 12 s
  (`:69`) — search across the registry is unreliable, so drive updates from the known identifier.

## Do not confuse a ClawHub install with an `npx skills` install

They look alike from the outside — both can produce a directory that `hermes skills list` calls `local`
— but only the hub-installed one has a lock entry. `npx skills` installs are updated by
`npx skills update -g -y`; see `references/update-hermes-skill-sh-skills.md`.
