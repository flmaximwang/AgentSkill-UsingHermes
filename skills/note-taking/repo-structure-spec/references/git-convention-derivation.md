# Deriving the version-control section of a spec

A spec of this class always needs a Git section (branch, commit granularity, commit-subject
convention, what is never committed). Never invent that section: probe one repository per project
type and write down what the repositories actually do. Run these against the projects that have a
`.git` — in a young tree that can be a minority, which is itself a finding to report.

## Probe block

```bash
# who is a repository at all (the rest are un-versioned: report the count)
for d in "$ROOT"/*/; do [ -d "$d/.git" ] && echo "$d"; done

# orientation: branch, commit count, first/last commit, remote
git -C "$P" branch --show-current
git -C "$P" rev-list --count HEAD
git -C "$P" log --reverse --format='%ad %s' --date=short | head -1
git -C "$P" remote -v                      # empty output is a finding, not a fault

# the commit-subject convention, in full — read it, do not assume Conventional Commits
git -C "$P" log --format='%s' | nl -ba

# is committing automatic? (Obsidian Git plugin state)
cat "$P/.obsidian/plugins/obsidian-git/data.json"   # autoSaveInterval: 0 => hand-written commits

# a nested repository silently untracks everything inside it
find "$P" -mindepth 2 -maxdepth 5 -name .git

# ignore reality, per path
T=$(git -C "$P" rev-parse --show-toplevel); (cd "$T" && git check-ignore -v <some/junk/path>)
git config --global --get core.excludesFile && cat "$(git config --global --get core.excludesFile)"

# what is actually tracked, by extension (find the disputed classes)
git -C "$P" ls-files | sed 's/.*\///; s/.*\.//' | sort | uniq -c | sort -rn | head -15

# the biggest tracked file — the cause of an outsized .git
git -C "$P" ls-files -z | xargs -0 -I{} du -k "{}" | sort -rn | head -6

# does the ignore rule cover the case you think it does?
git -C "$P" ls-files -- '*.asc' '*.tsv' '*.ab1' | wc -l     # lowercase data dirs stay tracked

# rule drift across projects: hash and print every ignore file
find "$ROOT" -maxdepth 2 -name .gitignore | while read f; do echo "$f $(md5 -q "$f")"; cat "$f"; done
```

Also size the excluded tree, so each `Do not commit` line carries its cost: `du -sh <heavy dirs>`
and `du -sh "$P/.git"`.

## What the spec lines look like

Derive every clause from the probes above; a clause you cannot source is a clause to drop.

- Branch and topology: one repository per project, the branch name observed, and whether a remote
exists — "history stays local, nothing is pushed" is a statement about the design, so write it as
such rather than as a misconfiguration.
- Commit granularity: one commit per work session, and say whether commits are hand-written
(`autoSaveInterval: 0`) or automatic; a plugin's default `vault backup: {{date}}` message is
evidence the repo does *not* use that message in practice — the log is the truth.
- Subject format: `<type>(<scope>): <subject>`, listing only the types and scopes that actually
occur, plus two or three real subjects as examples. Chinese subjects are normal where the notes are
Chinese; do not translate them into English in the spec.
- The nested-repository ban, when history shows it was hit — it is the one Git pitfall that silently
loses tracking for a whole subtree.
- Tracked versus excluded: text and small assets tracked; heavy data, backup archives, app
configuration directories and shell-created lock files excluded.
- The `.gitignore` blocks: in-repo file and global excludes, split exactly as the repos split them
(OS and editor junk belongs to `core.excludesFile`; a per-repo file listing `.DS_Store` is a smell).
When the per-repo files disagree, ship the union and name what each one forgot.

## Pitfalls

- **`Data`-style patterns are case-sensitive and match at any depth.** `Data` excludes a directory
  literally named `Data`, and leaves `workspace/data/` tracked. Verify with `git ls-files -- <glob>`
  before writing a rule that claims to cover "raw data"; then decide explicitly whether the lowercase
  sibling is meant to be excluded too (excluding it can cost reproducibility, so state the
  trade-off instead of silently widening the pattern).
- **Use `xargs -0 -I{}` for path lists.** Project paths carry spaces, CJK and emoji; a plain
  `xargs du` splits them and the tally is garbage.
- **A trailing quote in an extension tally is a quoting artifact, not a filename.** `git ls-files`
  quotes non-ASCII paths by default, so `82 jpeg"` means "82 JPEGs with quoted paths". Compare
  counts, never dedupe on the mangled string.
- **An outsized `.git` has one identifiable cause** — find the biggest tracked file before writing
  "binaries bloat the repo". One committed multi-hundred-MB archive is the usual answer, and naming
  it makes the ignore rule urgent rather than pedantic.
- **An ignore file that ignores the wrong thing is the point of the rule.** Report the drift
  (this repo forgets the backup directory, that one forgets the data directory) as the reason the
  union is written down, not as blame.
- **Do not promise that adding an ignore rule un-commits anything.** Files already in history stay
  there; offer the removal-and-rewrite command separately, as its own decision for the user.
