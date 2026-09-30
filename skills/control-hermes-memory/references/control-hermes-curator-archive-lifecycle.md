# The curator: archive lifecycle, commands, cleanup

`.archive/` is the curator's retirement store. Skills there are out of the prompt but still on
disk, and every entry is a `mv` away from being live again. Nothing in this file is a routine
housekeeping step — it is the reference for when the user asks about the archive itself.

## Command map

| command | does |
|---|---|
| `hermes curator status` | thresholds + active/stale/archived/unmanaged counts, last run summary |
| `hermes curator usage` | per-skill usage telemetry with provenance (what drives the age decisions) |
| `hermes curator list-archived` | names currently in `.archive/` |
| `hermes curator restore <name>` | move one back into the live tree |
| `hermes curator pin <name>` / `unpin` | exclude a skill from all automatic transitions |
| `hermes curator archive <name>` | hand-archive (what `actor: agent` records mean) |
| `hermes curator prune --days N [--dry-run] [-y]` | bulk-archive skills idle ≥ N days |
| `hermes curator purge --days N [--dry-run] [-y]` | **delete** archived skills older than N days |
| `hermes curator adopt <name>` | hand an unmanaged skill to the curator (it can then be staled) |
| `hermes curator backup` / `rollback` | manual snapshot / restore of `~/.hermes/skills/` |

`--days 0` means *disabled* for both prune and purge (a falsy TTL is read as "off"), not
"everything"; `--days 1` is the way to say "all of it". Always `--dry-run` first and read the
list back.

## Diagnosis before touching the archive

```bash
cat ~/.hermes/skills/.curator_state          # paused? last_run_at? run_count?
python3 - <<'EOF'
import json, collections
recs = [json.loads(l) for l in open('/Users/maxim/.hermes/skills/.curator_ledger.jsonl') if l.strip()]
a = [r for r in recs if r.get('action') == 'archive']
print(len(a), collections.Counter(r.get('actor') for r in a))
print(collections.Counter(r['ts'][:10] for r in a))
EOF
```

Bulk dates clustered a week apart are automatic curator cycles; a stray single date is a hand
archive. `evidence: {}` on an archive record means no usage data was attached — the decision
came from age, not from a recorded reason.

## Purging the archive (destructive, user-requested only)

1. Tarball the archive yourself — it is fast and independent of curator state:
   `tar -czf ~/.hermes/backups/skills-archive-$(date +%Y%m%d-%H%M%S).tar.gz -C ~/.hermes/skills .archive`
   then `tar -tzf <tarball> | wc -l` to prove it is non-empty.
2. `hermes curator purge --days 1 --dry-run` — confirm the list is what the user asked for.
3. Run it in the **background** or with a raised timeout: purge snapshots the whole skills
   tree first, and a 180 s foreground call can be killed part-way (it deletes incrementally, so
   a kill leaves a half-emptied archive, not a rollback).
4. Finish the remainder and verify with both of:
   `hermes curator list-archived` → `no archived skills`,
   `hermes curator status` → `archived 0`.

Count the archived population two ways and say which you used: directories under `.archive/`
versus `SKILL.md` files found under it (e.g. via `search_files (target='files')`). An archived
umbrella skill can carry a nested second `SKILL.md`, so the two numbers legitimately differ —
report the pair rather than a single "N skills".

## Restore fallback without the CLI

The archived layout is **flat** — the directory name is the skill name, its original category is
not recorded — so `mv ~/.hermes/skills/.archive/<name> ~/.hermes/skills/<category>/` works, and
the skill is live again on the next session (no config entry needed; `.archive/` membership was
the only thing hiding it). Collisions get a `-YYYYMMDDHHMMSS` suffix, so restore by the exact
directory name `list-archived` prints, not by the skill's frontmatter name.
