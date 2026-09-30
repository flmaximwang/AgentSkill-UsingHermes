# Repo structure → identifier routing

The *link* does not decide the identifier form — the **repo's structure** does. Classify first, then
convert. Two of the four types below cannot be served by the form a reader would guess from the URL.

## Classify

**In the GUI** (for a user who has no terminal):

1. The repo home lists the root entries — a `SKILL.md` there means a root skill exists; no `SKILL.md`
   means the identifier must point into a subdirectory.
2. Click the candidate directories: `skills/<name>/SKILL.md` per subdir, or `examples/<name>/SKILL.md`
   for a repo that ships sample skills beside its own.
3. `t` (or *Go to file*) opens `github.com/<owner>/<repo>/find/<branch>`, a search over the whole tree —
   type `SKILL.md` and every location is listed. That page fetches its listing client-side
   (`/tree-list/<branch>` answers 400 to a plain `curl`), so this step happens in the browser.

**On the CLI** (authoritative, and the only route when the repo is private):

```bash
gh api "repos/<owner>/<repo>/git/trees/HEAD?recursive=1" \
  --jq '.tree[] | select(.type=="blob") | .path' | grep -F "SKILL.md"
```

Keep `select(.type=="blob")` — the tree also carries directory entries, and a directory named
`…/SKILL.md` would otherwise show up as a hit.

## The four types

| Type | Listing shape | Measured example |
|---|---|---|
| **1 single-skill** | one bare `SKILL.md`, no directory | 1 hit |
| **2 root skill + children** | bare `SKILL.md` first, then one or more `…/<x>/SKILL.md` | 16 hits (root 1 + `examples/` 15); 212 tree entries / 38.6 MB |
| **3 aggregate** | every hit under `skills/<name>/` (may nest further) | 4 hits, all under `skills/<agent>/` |
| **4 non-standard / deep** | anything else: `benchmarks/…`, names unrelated to the skill, root plus scattered children | 36 hits (root 1 + deep `benchmarks/…`) |

## Convert, per type

| Type | Link you hold | Feed | Measured result |
|---|---|---|---|
| 1 | `github.com/<owner>/<repo>` | `<owner>/<repo>/` (trailing slash: empty path = repo root, and `_skill_file_path('')` resolves to `SKILL.md` by design) | installs, but the "skill directory" is the whole repo |
| 1 | `…/tree/<ref>/SKILL.md` | same trailing-slash form (two segments are refused) | — |
| 2 | `github.com/<owner>/<repo>` | **no identifier expresses the root skill** → raw URL: `https://raw.githubusercontent.com/<owner>/<repo>/<ref>/SKILL.md` (rewrite `blob/` out of the page URL) | 3 files / 52 KB (the `SKILL.md` plus the files its body references) |
| 2 | `…/tree/<ref>/examples/<x>` | `<owner>/<repo>/examples/<x>` | installs, but that is a **child** skill |
| 2 | `<owner>/<repo>/` | avoid | 93–117 s fetch+scan, whole repo (156 files / 33.69 MB), `CAUTION` → `BLOCKED` on 29 findings, one HIGH `exfiltration` from the repo's own `.github/scripts/` |
| 3 | `…/tree/<ref>/skills/<name>` | strip `https://github.com/`, strip `tree/<ref>`, strip the trailing `/SKILL.md` → `<owner>/<repo>/skills/<name>` | full directory, pinned to a commit; claimed by the skills.sh adapter (`Source: skills.sh`) |
| 3 | `github.com/<owner>/<repo>` | list the hits first — one `SKILL.md` per installable target | — |
| 4 | any directory link | `<owner>/<repo>/<path-to-that-directory>` | works, including deep paths; root skill of such a repo goes via raw URL |
| any | third segment ending `/SKILL.md` | invalid | `Could not find '<id>' in any source.` — the path is appended with `/SKILL.md`, giving `…/SKILL.md/SKILL.md` |

## Rules that hold across all types

- **The third segment is the skill DIRECTORY, and it is "the rest of the identifier".** Splitting is
  `identifier.split("/", 2)`, so slashes past the second one stay inside the third segment — a literal
  four-slash identifier is still the normal three-part form, and only the *first two* segments are
  meaningful for the repo.
- **`owner/repo/` (trailing slash) always means "the skill directory is the repo root"** — legal in
  every type, but the bundle then includes every file except names starting with `.` or ending `.pyc`.
  The dotfile skip tests the *basename*, so `.github/scripts/x.py` ships (and can be what the scan
  flags). `owner/repo/.` is rejected outright: `Unsafe skill name: .`.
- **A `blob/…` page URL is never usable** — the url adapter claims any path ending `.md`, so the HTML
  page becomes the "skill" and is scored dangerous (not overridable).
- **The raw-URL route ships only `SKILL.md` plus body-referenced files** under
  `references/ templates/ scripts/ assets/` — right for a root skill, wrong for a skill whose body
  links other trees (it installs as a dangling shell).
- **Bundle size is a property of the fetched directory, not of the skill's intent**: root-layout repos
  drag examples, assets, promo material and CI scripts into the scan.

## Fallbacks

- **Raw URL** — any type, when you have the `SKILL.md` raw address. Smallest bundle; needs the host's
  fake-IP blocks declared (`security.fake_ip_ranges`, IPv4 *and* IPv6) or the CLI reports a misleading
  "Could not find … in any source".
- **Manual copy** — private repos, oversized repos, or when only part of the tree is wanted:
  clone, then `cp -R <clone>/<dir> <HERMES_HOME>/skills/[<category>/]<name>/`. No lock entry, so
  `check` / `update` / `uninstall` never see it.
