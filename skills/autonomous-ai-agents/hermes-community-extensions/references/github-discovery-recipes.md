# Discovery recipes — GitHub + Skills Hub

Copy-paste recipes for finding community Hermes profiles/skills. All GitHub calls work unauthenticated
(low rate limit — batch candidates into one script instead of one call per repo).

## R1 — Repo search (indexes, collections, themed packs)

```bash
python3 - <<'EOF'
import json, urllib.request, urllib.parse
def search(q, per=20):
    url = "https://api.github.com/search/repositories?q=" + urllib.parse.quote(q) + f"&sort=stars&per_page={per}"
    req = urllib.request.Request(url, headers={'User-Agent':'hermes','Accept':'application/vnd.github+json'})
    return json.load(urllib.request.urlopen(req, timeout=30))
for it in search("hermes agent profile <domain terms>").get('items', []):
    print(it['full_name'], '|', it['stargazers_count'], '|', (it['description'] or '')[:100])
EOF
```

Use several query shapes: `hermes profile <domain>`, `hermes agent profile gallery`, `hermes profile
packs`, plus the English role names from Step 1. Result counts of 0 usually mean the vocabulary is
wrong, not that the artifact is missing.

## R2 — Recursive tree + client-side keyword filter (the payload recipe)

One call returns every path in the repo; filter locally. This is what finds a profile nested inside a
100+ profile pack.

```python
import json, urllib.request
def api(url):
    req = urllib.request.Request(url, headers={'User-Agent':'hermes','Accept':'application/vnd.github+json'})
    return json.load(urllib.request.urlopen(req, timeout=40))

kw = ["account","financ","bookkeep","tax","cfo","audit","ledger","会计","财务"]
for repo in REPOS:
    for br in ("main", "master"):
        try:
            t = api(f"https://api.github.com/repos/{repo}/git/trees/{br}?recursive=1")
            hits = [e['path'] for e in t['tree'] if any(k in e['path'].lower() for k in kw)]
            print(repo, br, len(t['tree']), 'paths,', len(hits), 'hits'); [print('  ', h) for h in hits[:40]]
            break
        except Exception as e:
            if br == "master": print(repo, 'ERR', e)
```

A directory listing (`/contents/<dir>`) tells you names one level at a time; the recursive tree tells you
WHERE the artifact is — prefer it whenever you are surveying, not browsing.

## R3 — Read decisive files exactly

```python
import urllib.request
txt = urllib.request.urlopen(
    "https://raw.githubusercontent.com/<owner>/<repo>/main/<path>", timeout=40).read().decode()
```

Read the manifest (`distribution.yaml`), `SOUL.md` head, `README.md`, and `install.py`'s command
construction — `grep -n "profile install\|subprocess\|\.yaml"` over the raw text shows how a pack
delegates to `hermes profile install`.

## R4 — Which manifest keys does the RUNNING build actually parse?

```bash
# keys the installed build understands (source of truth, not docs)
grep -n "data.get(\"\|_str(data" ~/.hermes/hermes-agent/hermes_cli/profile_distribution.py | head -30
```

`DistributionManifest.from_dict` reads `name, version, description, hermes_requires, author, license,
env_requires, distribution_owned` — anything else in a repo's `distribution.yaml` (e.g. `preload_skills`)
is ignored without error. State a manifest feature as working only after this check.

## R5 — Skills Hub search

```bash
COLUMNS=200 hermes skills search accounting      # full Identifier column, Trust column
hermes skills inspect <identifier>               # preview before install
hermes -p <profile> skills install <identifier>  # per-profile: skills are NOT global
```

Trust levels seen: `official` (first-party families, e.g. the finance model/excel skills) and
`community` (everything mirrored from clawhub / lobehub / skills.sh / browse-sh). Community entries
include Chinese-language bookkeeping skills (feishu bookkeeping, OCR→voucher→statements, tax) that no
git-profile search will ever surface — search the hub in both languages.

## R6 — Known source families (DRIFT-PRONE — re-verify before quoting)

These existed and were inspected; treat as starting points, never as a catalogue to answer from without
re-checking, and never as authority about what is currently installable:

| Source | Shape |
|---|---|
| Profile-distribution collections on GitHub (`hermes-profiles`, `hermes-profile-packs`, agent-profile-index repos) | packs of many `profiles/<role>/` dirs, each optionally with `distribution.yaml`; some ship their own `install.py` with `--profiles … --dry-run/--yes` |
| Gallery/index repos | markdown index + `registry.json`; entries carry trust level and status (`seed`, `candidate`, `listed`) |
| Skills Hub mirrors of other ecosystems (clawhub, lobehub, skills.sh, browse-sh) | single skills, including non-English domain packs |
| Vendor knowledge-work plugin ports (e.g. finance plugin trees converted for other agents) | skill bundles, not Hermes distributions — need conversion before `hermes skills install` |

When reporting from this table, say which entries were verified in THIS session and which came from
prior notes.
