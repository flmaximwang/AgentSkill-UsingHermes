# git-annex: layout and storage model (answering "where does my data live")

Use when the question is structural rather than a command: where the bytes live, what "进 git / 进 annex"
means, whether files sit inside or outside the initialized repo, how many copies are on disk.

## The tree to draw (single-directory repository)

```
<repo>/                          <- working tree: the files the user opens and names
|-- <data dirs>/                 <- human names; locked = symlink into .git/annex/objects
`-- .git/                        <- created by git init
    |-- objects/                 <- commits, trees, blobs of the pointer/symlink entries
    |-- index                    <- staging: path -> key
    |-- refs/                    <- branch history
    |-- annex/objects/<hash>/    <- CONTENT STORE: the bytes, named by content hash
    `-- (git-annex branch)       <- location log: which repo/disk holds each key
```

- Two layers, and naming them by path is the whole answer: git keeps ~100-byte **pointers**
  (path -> key); the content store keeps the **bytes**.
- Everything the tool manages must be **inside the working tree**: `git annex add <path>` accepts only
  paths in the repo. There is no configuration that relocates the content store — its path is
  `<gitdir>/annex/objects`; only the hash layout (tuning) is settable, and only at `init`.
- Old versions accumulate in the content store, not in git: reclaim with
  `git annex unused --used-refspec '+refs/heads/main'` then `git annex dropunused <n|range>`.
  Narrow the refspec — remote-tracking and git-annex-synced refs still reach the old commits and
  hide the unused list. Reclaiming drops the ability to roll back to those versions.

## Layout decision, in the order to say it

1. Data lives **inside** the initialized repo; the bytes then sit in `<gitdir>/annex/objects`.
2. `git init --separate-git-dir=<path>` moves only the **git directory**; the content follows it.
   Both directions work: worktree = data dir with the git dir elsewhere, or worktree = the names dir
   with the git dir = the data dir. After `git annex init` the worktree's `.git` entry is converted
   from a text file (`gitdir: <abs path>`) into a **relative symlink** (`<worktree>/.git -> ../<gitdir>`),
   so the pair survives being moved or renamed together.
   A git dir nested inside its own worktree works but shows as `?? <dir>/` in `git status` — keep the
   two directories siblings.
3. One directory needs no flag at all: `git init` + `git annex init`, nothing to move. Recommend it
   unless the names and the bytes genuinely belong on different paths (different volume, different
   backup/sync policy).

## "Is it storing two copies?"

| mode | worktree entry | bytes on disk |
|---|---|---|
| locked (default) | symlink; size shown = target path string (hundreds of bytes) | one, in `.git/annex/objects` |
| `annex.addunlocked true` | real file | two: worktree + content store |
| unlocked + `annex.thin true` | real file hardlinked to the object | one (hardlinks only on filesystems that support them) |

- Verify, do not assert: `ls -l <file>` (`l` = symlink = single copy), `find <dir> -type l | wc -l` vs
  `-type f | wc -l`, `du -sh .git/annex`.
- Identical content is stored once (key = content hash), so re-adding the same file costs nothing.

## Why `git status` goes clean right after an add

`git annex add` stages each path as a symlink (locked) or a pointer file (unlocked), then the commit
records it — git tracks the **link**, never the bytes. Clean tree = "links unchanged, no paths added or
removed". Content corruption is invisible to git and is what `git annex fsck` is for. New files dropped
into an annexed directory still show as `??` until `git annex add <file>`; editing an annexed file is
`git annex unlock` -> edit -> `git annex add` -> commit (which adds a content version, reclaimable as above).

## Splitting the rule for an app-managed tree

An app that rewrites its own metadata on every edit (asset/photo libraries writing `metadata.json`,
`tags.json`, `mtime.json`, thumbnails) fails against locked symlinks: writes return `Permission denied`.

- Keep the small text/JSON in git, annex the rest:
  `git annex config --set annex.largefiles 'exclude=*.json'` (verified expression; the JSON stays a real,
  writable file, everything else goes to annex).
- Or annex everything and make the worktree real files: `git annex config --set annex.addunlocked true`,
  accepting the double storage. Already-locked files convert with `git annex unlock <path>`.
- Order matters: `addunlocked` is global, so annex the bulk read-only tree first (locked, one copy),
  then set `addunlocked` before annexing the app-managed tree.
- Writing the rule explicitly: `git annex config --set annex.largefiles 'include=*'` is the visible form
  of the default (everything to annex). Dotfiles are still not annexed by default — not even with
  `include=*` — so exclude `.DS_Store`/`Icon\r` via `.gitignore`; the pattern `Icon?` matches the
  CR-suffixed filename, while a literal `Icon\r` line in `.gitignore` does not (git strips the trailing CR).
- **Dot-dir contents are git-owned, and that decides what can ever be reclaimed.** Anything under a dot
  directory (Drive's `.ts/` temp dirs, `.obsidian/`) lands in **git** even with `include=*`: `git ls-tree`
  shows mode `100644` and `git annex lookupkey <path>` answers nothing. So `git annex unused` can never
  list it — that is the answer to "I deleted them, why doesn't unused show them" — and deleting it frees
  **nothing**: git keeps removed blobs reachable from history, and only a history rewrite purges them,
  while annex content becomes reclaimable with `unused` + `dropunused`. Check `git ls-tree`'s mode before
  promising that any deleted file's space comes back.
- Set the rule before the first bulk `add` and read it back (`git annex config --get <key>`) — see
  SKILL.md "Validate the exact string before you teach it" for why an unrunnable value is accepted silently.

## Moving annexed files (and proving the move invented nothing)

- Rename with `git mv -- <src> <dst>` inside the repo, then commit. The bytes do not move: the key is
  unchanged, so the content store gains nothing. What breaks is the **relative symlink target** whenever
  the path depth changes, and git-annex's `pre-commit` hook rewrites it during that commit — the commit
  prints `fix <new path> ok` per file. Plain `cp` is the wrong tool: it writes a second, un-annexed real
  file and the copy stops being tracked.
- **`git mv` is convenience, not a requirement** — plain `mv` is the same rename, and "must it be git mv?"
  deserves that answer plus the two traps plain `mv` leaves open:
  1. **A depth change breaks the link until you commit.** The stale relative target
     (`../../../.git/annex/objects/…`) is left in place, so the file reads as missing until the commit's
     hook rewrites it. To make it usable immediately, stage first, then fix: `git add <new path>` →
     `git annex fix <path>`. `git annex fix` on an unstaged path fails
     (`Did you forget to 'git add'?` / `fix: 1 failed`) — staging is its precondition, not an extra.
  2. **Stage both sides.** `git add <new path>` alone leaves the old path tracked: after the commit
     `git ls-tree -r` still lists it while the worktree no longer has it. Use `git add -A <dirs>`.
  A rename inside one directory needs no fix at all (same depth ⇒ same relative target). What `git mv`
  buys: one command for worktree + index, a refusal when the destination exists or the source is
  untracked, and no way to forget trap 2.
- Verify with two independent reads, never by eye:
  1. `find <new tree> -type l ! -exec test -e {} \; -print | wc -l` must be 0 (no broken links), and a
     sample file's `getsize()` must return its real size.
  2. Compare the **content-key multisets** before/after: `git ls-tree -r <rev>` → for mode-`120000`
     entries `git cat-file blob <sha>` returns the target text → regex out `SHA256E-s<size>--<hash>.<ext>`.
     "Keys present only after" must be empty (nothing invented); keys present only before are the parts
     deliberately left behind (thumbnails, metadata records, other assets).
- Which files move is a decision, not a detail — original asset vs its thumbnail vs the library's
  metadata record — and the leftover half is what the old tool then shows as broken. Say which ones you
  are moving before moving them.

## Proving two paths hold the same content

`git cat-file -p HEAD:<path>` prints a tracked symlink's target string, which contains the key
(`…/SHA256E-s<size>--<hash>.<ext>/…`); for a path that is only staged, use `:<path>` (the index) instead.
Equal keys ⇒ identical bytes, so renaming a duplicate into place adds nothing to the content store —
this clears a batch of renamed or duplicated files without re-hashing gigabytes, and it is the check that
makes a mass rename safe. The size and hash in a key describe the content, not the file name.

## Reading an old version, or restoring a deleted path

Annex content outlives the deletion of its path, and outlives the commit that removed it — until its
`unused` entries are dropped. Three moves, in order:

1. **Do not reset the history to get a subtree back.** "Roll back to the commit before the deletion" is
the wrong shape whenever later commits hold work worth keeping (a reorganization, a rename). Restore the
paths instead; the history stays intact.
2. `git restore --source=<rev> -- '<pathspec>'` writes back only the matching paths, recreating missing
   parent directories — verified with the whole directory already deleted — and leaves the index alone
   unless `--staged` is added. A glob pathspec narrows a bulk restore to one file kind:
   `git restore --source=<rev> -- '<lib>/images/*.info/metadata.json'` returns the app's records without
   the thumbnails or the library-level file. Restored entries are untracked until `git add`.
3. Reading the bytes of an old version takes one extra hop: for a locked file `git show <rev>:<path>`
   prints the **pointer** (the symlink target), not the content. Resolve it —
   `cat ".git/annex/objects/${tgt#*objects/}"` — and it works only while the content is undropped.
   Therefore: confirm or finish any recovery **before** `git annex dropunused`; dropping first leaves the
   restored paths as broken links.

## The `git-annex` branch vs your work branches (and what a sync moves)

Use for "why is that a separate branch", "I have several branches — there is still only one `git-annex`
branch, right?", "the two refs are not the same commit, do I need to fetch?".

- Object-wise it is an ordinary branch: one ref, `refs/heads/git-annex`, pointing at ordinary commits. But its
  history is **unrelated** to yours (`git merge-base main git-annex` finds no common ancestor; the two root
  commits differ) and it is never checked out — absent from the worktree and from `git log`/`git status`
  unless you name it. Only `git annex` commands read and write it.
- **One per repository, not one per branch** (measured: two work branches ⇒ `refs/heads` still holds a single
  `git-annex`). It stores state keyed by content, never file names: hash-directory `*.log` location logs plus
  top-level `uuid.log` / `config.log` / `activity.log` (`remote.log` appears only once a special remote
  exists; a remote that is just another git repo keeps its UUID in `.git/config`'s `remote.<name>.annex-uuid`).
  The name → key pointers live in each branch's own tree, so the same bytes under two names or two branches are
  one key, one object in the content store, one log entry.
- That sharing is also why `unused` judges "used" across **all** refs (work branches, tags, remote-tracking,
  `synced/*`) plus the index: a `git rm` + commit whose old commit is still reachable from a remote-tracking ref
  reports 0 unused until the refspec is narrowed.
- Refs each command actually moves (measured: scratch repo + bare remote): `git annex sync <remote>` pushes the
  **current branch plus the `git-annex` branch** (leaving a `synced/git-annex` on the remote) and not the
  branches/tags you made yourself; a plain `git push` carries the current branch but not the `git-annex` branch,
  which is why the bare-remote recipe names both refs explicitly. So "sync, then also `git push`?" is normally
  "no", and the exception is exactly your own extra branches and tags.
- Two copies of that branch at **different commits** is the normal state, not damage: each machine commits its
  own `update`, the log files merge by concatenation with per-line timestamps, and *any* annex command
  union-merges in the remote-tracking copies on its own (running `git annex log` prints
  `(merging <remote>/git-annex into git-annex...)` and moves the local tip forward). Report a real gap only when
  the **content** disagrees: `git merge-base --is-ancestor` for direction plus a read of the key's log lines —
  never a hash comparison. Repair with `git annex merge` (not `git merge` on that branch) or `git annex sync`.
- `unused --used-refspec` judgment: default ≡ `+refs/*:+HEAD` (remote-tracking refs and tags count as "used";
  `reflog` is opt-in), elements are **colon**-separated, and the space-written form is accepted but means
  something else entirely — see SKILL.md "Validate the exact string before you teach it".
