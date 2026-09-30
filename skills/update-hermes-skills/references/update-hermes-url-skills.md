# Updating raw-URL skills (`Source: url`)

The minimal install route: `hermes skills install "<raw URL to SKILL.md>"` records the **URL itself** as
the identifier and keeps no revision — so unlike every other source it can never take a fast path, and
its `check` status is the one that lies by omission.

Measured lock entry (this machine, 2026-09-30):

```json
"respond-to-questions": {
  "source": "url",
  "identifier": "https://raw.githubusercontent.com/flmaximwang/AgentSkill-StructuredResponse/main/skills/respond-to-questions/SKILL.md",
  "trust_level": "community", "scan_verdict": "safe",
  "content_hash": "sha256:712eb90365eb772a",
  "install_path": "secretary/respond-to-questions",
  "files": ["SKILL.md"],
  "metadata": {
    "url": "https://raw.githubusercontent.com/flmaximwang/AgentSkill-StructuredResponse/main/skills/respond-to-questions/SKILL.md",
    "source_url": "https://raw.githubusercontent.com/flmaximwang/AgentSkill-StructuredResponse/main/skills/respond-to-questions/SKILL.md",
    "awaiting_name": false
  }
}
```

No `source_revision` anywhere: `check` must download every time (measured 2.1 s — the bundle is one
file). What that download does with the result is where the trouble lives.

## `unavailable` is not "no update" — it is "the fetch was blocked"

The status table in `SKILL.md` lists `unavailable` as its own row for exactly this reason. The chain,
source-verified:

1. `check` fetches an entry **only from adapters matching its recorded source** — the docstring at
   `tools/skills_hub_install.py:270-273` spells out why (a same-named skill from another registry must
   never silently satisfy the fetch). A missing adapter therefore reports `unavailable` as well;
2. `UrlSource` inherits `GuardedFetchMixin`, so its download goes through the hub's guarded HTTP GET
   (`tools/skills_hub_models.py:163-167`);
3. the guard resolves the hostname and rejects private / benchmark IP ranges before the request
   (`tools/url_safety.py`);
4. the fetch returns `None`, no bundle is produced, and the row is reported `unavailable`
   (`tools/skills_hub_install.py:309-319`).

On a machine behind a fake-IP TUN proxy, step 3 rejects a perfectly public hostname, and the error text
names an address rather than the config key:

```
Blocked request to private/internal address: raw.githubusercontent.com -> 198.18.0.8
Blocked unsafe Skills Hub URL: https://raw.githubusercontent.com/.../SKILL.md
```

…while the `check` table says only:

```
│ respond-to-questions │ url │ unavailable │
```

## The fix — declare the proxy's fake-IP ranges (this is the supported switch)

`tools/url_safety.py:183-214` exists for Mihomo/Clash-style fake-IP proxies; the ranges go in the
profile config, and **both** families must be declared — IPv4 alone still fails when the AAAA record is
what the resolver returns:

```yaml
security:
  fake_ip_ranges:
    - 198.18.0.0/15      # IPv4 fake-ip
    - 2001:2::/48        # IPv6 fake-ip — with only the line above, 2001:2::13 is still blocked
```

Ranges that overlap RFC1918 / loopback / CGNAT are dropped silently (`_FAKE_IP_UNDECLARABLE_NETWORKS`,
`tools/url_safety.py:131-135`), so a declaration that "does nothing" is usually a declaration the guard
refused.

Measured state of this machine, before and after (2026-09-30):

```
$ hermes config get security.fake_ip_ranges
  - 198.18.0.0/15
  - 2001:2::/48

$ hermes skills check respond-to-questions          # url source
│ respond-to-questions │ url │ update_available │   # 2.1 s — real status, previously `unavailable`
$ hermes skills check respond-to-requirements       # url source
│ respond-to-requirements │ url │ up_to_date │      # 2.2 s
```

The same guard covers `web_extract`, platform attachment downloads and the browser relay, so this one
config change fixes all of them at once. Two rules when it is *not* fixed:

- **never report `unavailable` as "already current"** — it carries no information about the upstream
  content at all;
- **do not reinstall to "repair" it** — the skill on disk is fine; the fetch path is what is broken.

A sibling fix, when the repository supports it: reinstall through a three-segment identifier so the
entry's source becomes `skills.sh` (GitHub API, no SSRF pre-check). That is a **reinstall, not an
update** — the lock entry is rewritten and you now maintain a whole directory rather than one file.
Take it only when you actually want the directory (see below).

## Floating refs — the price of URL-sourced updates

The identifier is the URL you installed from, verbatim. Installing from `/main/` therefore means: any
push upstream becomes `update_available`, and `hermes skills update <name>` pulls it. There is no
version to roll back to, and the URL route has no commit pin to compare against. If reproducibility
matters, install from a commit or tag URL instead. (Inferred from the identifier being stored verbatim
and `current_revision` not applying here — not measured by pushing to an upstream repo.)

## What an update can refresh — and what it silently skips

The URL route installs `SKILL.md` plus the files its body **explicitly references**. Measured contrast
on the same skill: 3 files via the URL route (`SKILL.md`, `assets/eval_review.html`, and a schema file
of its own under a `references/` directory) versus 18 via the tap/identifier route — the difference
being every file the body never mentions.

Two consequences for updates:

- **an update can only ever refresh that same minimal set** — a repository that ships scripts the body
  does not reference stays incomplete no matter how often you update;
- **adding a file inside the installed directory makes every update skip.** `_has_local_edits` hashes
  the whole directory (`hermes_cli/skills_hub.py:887-897`), so one extra file means
  `Skipping: <name> — you have local edits`, and `--force` would delete that file along with the
  replacement.

If the skill genuinely needs its directory, reinstall it through the identifier route
(`references/update-hermes-skill-sh-skills.md`) and keep edits outside the installed tree.

## Related traps from the same route

- **The URL must be a raw one.** A `github.com/.../blob/...` link is claimed by the URL source because
  its path ends in `.md`; the HTML page is fetched and scanned as the skill, which lands `DANGEROUS` and
  cannot be forced. Use `raw.githubusercontent.com`, and a URL with the ref segment present (a missing
  `main`/`HEAD` is a plain 404). Details in the sibling `install-hermes-skills`.
- **A single-file install has no `files` safety net.** `files: ["SKILL.md"]` means integrity covers one
  file; anything else in the directory is invisible to both the lock and the update.
