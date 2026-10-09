#!/usr/bin/env bash
# Post-rewrite check for one path that was removed from a git repo's history (read-only).
# Usage: verify_blob_purge.sh <path-in-repo> [repo-dir] [old-blob-id]
# Prints every number the report needs; see references/heavy-artifact-retirement.md §7.
set -uo pipefail

p=${1:?usage: verify_blob_purge.sh <path-in-repo> [repo-dir] [old-blob-id]}
repo=${2:-.}
old_blob=${3:-}

if ! git -C "$repo" rev-parse --git-dir >/dev/null 2>&1; then
  echo "not a git repo: $repo" >&2; exit 2
fi
cd "$repo" || exit 2
base=$(basename "$p")

echo "repo            : $(pwd)"
echo "commits         : $(git rev-list --count HEAD)"
echo "tracked files   : $(git ls-files | wc -l | tr -d ' ')"
echo ".git size       : $(du -sh .git | cut -f1)"
printf 'in HEAD         : '; git cat-file -e "HEAD:$p" 2>/dev/null && echo YES || echo no
echo "commits touching: $(git log --all --oneline -- "$p" | wc -l | tr -d ' ')"
echo "objects named   : $(git rev-list --objects --all | grep -c -- "$base")  (0 = purged)"
printf 'old blob size   : '
if [ -n "$old_blob" ]; then git cat-file -s "$old_blob" 2>&1 | head -1; else echo "skipped (no blob id given)"; fi
echo "reflog lines    : $(git reflog 2>/dev/null | wc -l | tr -d ' ')  (0 = undo is gone)"
printf 'worktree file   : '; [ -e "$p" ] && echo "present ($(wc -c < "$p" | tr -d ' ') B)" || echo absent
printf 'ignore rule     : '; git check-ignore -v "$p" 2>/dev/null || echo "NOT IGNORED - add the heavy directory to .gitignore"
echo "fsck            :"
git fsck --no-progress 2>&1 | head -5
