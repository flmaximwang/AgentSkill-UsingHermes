# Removing raw-URL skills (`Source: url`)

The minimal install route: `hermes skills install "<raw URL to SKILL.md>"` records **the URL itself** as
the identifier, stores it in `metadata.url` / `metadata.source_url`, and usually ships exactly one file.

Measured lock entry (this machine, 2026-09-30, and reproduced in a throwaway home the same day):

```json
"respond-to-questions": {
  "source": "url",
  "identifier": "https://raw.githubusercontent.com/flmaximwang/AgentSkill-StructuredResponse/main/skills/respond-to-questions/SKILL.md",
  "trust_level": "community", "scan_verdict": "safe",
  "content_hash": "sha256:7ba6798c35780d14",
  "install_path": "respond-to-questions",
  "files": ["SKILL.md"],
  "metadata": {"url": "…/SKILL.md", "source_url": "…/SKILL.md", "awaiting_name": false}
}
```

Removal is the ordinary hub removal — `hermes skills uninstall <key> -y` — with two properties that are
specific to this source.

## The key is the SKILL.md name, not the `--name` you may have passed

`uninstall` is name-addressed, and for a URL bundle the name comes from the fetched `SKILL.md` itself:
`--name` is only consulted when that file has no usable name
(`_resolve_url_bundle_name`, `hermes_cli/skills_hub.py:525-538` — it early-returns unless
`bundle.source == "url"` **and** the bundle is nameless/`awaiting_name`). Measured:

```
$ hermes skills install "https://raw.githubusercontent.com/…/respond-to-questions/SKILL.md" --name url-remove-test -y
Installed: respond-to-questions                         # the flag was ignored — the SKILL.md carries `name:`
Files: SKILL.md
$ hermes skills uninstall url-remove-test -y
Error: 'url-remove-test' is not a hub-installed skill (may be a builtin)
$ hermes skills uninstall respond-to-questions -y
Uninstalled 'respond-to-questions' from respond-to-questions
```

…followed by an empty lock, no directory, and `2026-09-30T08:35:26Z UNINSTALL respond-to-questions
url:community n/a user_request` in `audit.log`. So read the key from the lock (or from the install
output's `Installed:` line) instead of reusing whatever name was requested at install time.

## The blocked-fetch story never applies to removal

A `url` entry is the one source whose `check` can sit at `unavailable` forever behind a fake-IP TUN proxy,
because only this adapter's fetch goes through the hub's SSRF-guarded HTTP GET. **Removal does not fetch
anything** — it resolves `install_path` from the lock and `rmtree`s it
(`tools/skills_hub_install.py:205-223`), so:

- do not tell a user "the URL is blocked, so the skill cannot be removed" — the two are unrelated;
- do not reinstall to "repair" the entry before removing it;
- if the skill should be *kept*, the blocked fetch is a different fix (declare the proxy's fake-IP ranges,
  both IPv4 and IPv6, in `security.fake_ip_ranges`) — the sibling `update-hermes-skills` →
  `references/update-hermes-url-skills.md` carries that recipe and the measured before/after.

## What dies with the entry

- **The only record of where the content came from.** The identifier *is* the URL, usually with a
  floating ref (`/main/`), and the lock keeps no revision. Copy the URL into the report or the user's note
  *before* deleting — afterwards nothing in the profile says which file this was.
- **The whole directory, not just the file the lock lists.** `files: ["SKILL.md"]` describes what was
  installed, not what removal covers: `uninstall` has no local-edit guard and removes `install_path` as it
  stands. Any file you added next to it goes too, and a single-file install has no integrity record for it
  anyway.
- **Nothing else.** The upstream raw file, the repository, and any sibling entry from the same repo are
  untouched — a repo that ships several URL-installed skills has one key per skill (measured:
  `respond-to-questions` and `respond-to-requirements` are two independent entries).

## Getting it back

An install, in one of two shapes — and the choice is the same one the install docs draw:

```bash
# a. the same URL: whatever the ref points at NOW (no version to fall back to)
hermes skills install "https://raw.githubusercontent.com/<owner>/<repo>/main/<path>/SKILL.md" -y

# b. the whole directory, if the skill needs its support files: the identifier route
hermes skills install <owner>/<repo>/<path> --category <same category> -y
```

Option (a) is the URL route again — floating ref, one file plus explicitly referenced files, and the same
`check` fragility. Option (b) installs the directory through `skills.sh`/GitHub, records
`source_url` + `source_revision`, and is the only one of the two that supports a real update fast path;
it does not need a token *if* the repo is public, and a private repo works through the profile's stored
credentials. Route detail: `install-hermes-skills` →
`references/install-hermes-skills-from-skill-sh.md`.
