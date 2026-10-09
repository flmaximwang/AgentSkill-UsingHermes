---
name: repo-structure-spec
description: Use when deriving or enforcing a repo's organisation spec.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [documentation, conventions, vault, repository, spec]
    related_skills: [obsidian, hermes-profile-housekeeping]
---

# Repository organisation specs

Deriving how a repository is *actually* organised and writing it down as a spec. The class is any
root holding many sibling project directories — an Obsidian vault of lab projects, a monorepo of
pipelines, a shared data tree — where the user asks to 归纳 the organisation rules.

The deliverable is a spec, not a survey: rules a future session can execute against, plus a file
tree showing where each rule bites.

## When to Use

- "归纳其中的项目组织规范" / "write down the organisation rules of `<root>`".
- A repository has grown without a conventions doc and the user wants one.
- A repository's own per-project READMEs must be checked against the filesystem.
- "看看目前的项目有什么不符合规范的，规范化一下" / bring ONE project in line with a spec that already
  exists (§4).
- A heavy artifact under an ignored directory has to be retired, converted or purged — "将
  `<Backup>/Inventories-<NN>` 解压为 json", the follow-up "我用 Git 追踪以后将它删除", "把这个压缩包从 git
  history 里清掉". This arrives phrased as a file task, not a spec task: §5 (what text comes out of it,
  where the rest goes) and §7 (removing the blob from history).
- "先迁移 Records" / move one project's records out of the older bucket layout into the
  current-generation record layout (`Logs/<YYYY>/<MM>/<DD>/<Type>-<NNN>/`) — §4, with the mapping,
  numbering and frontmatter recipe in `references/normalisation-pass.md`.
- "整理 Protocols" / "根据 Protocol 演进历史更新 series 和 v" — dissolve the container folder into one
  folder per protocol and derive the `- Series<N>.v<M>` names from the *citations in the records*, not
  from taste: §4 + `references/normalisation-pass.md`.
- A directory class is declared deprecated ("`Inventory` 已经弃用，删除相关引用") — delete the organ **and**
  its references, then say where the authority moved to: §4 + `references/normalisation-pass.md`.

## 1. Derive first, write second

1. **Enumerate and count before writing a single rule.** Run `scripts/survey-layout.py <root>`: it
   prints a per-project presence matrix of candidate top-level dirs, the frequency of each, and a
   classification of record folders. Those counts are the spec's evidence; they are also what
   exposes claimed-versus-actual (step 3).
2. **Find the authoritative rules file and hash every copy.** Repos of this shape usually carry a
   rules doc copied into each project (`Dashboard/Rules/工作规范.md`, `CONTRIBUTING.md`, `AGENTS.md`).
   Read one in full, then compare copies by hash: identical hashes mean the rules are a **per-project
   snapshot whose edits do not propagate** — state that in the spec, or a later session will edit one
   copy believing it applied everywhere.
3. **Separate claimed from actual.** Diff each project README's directory table against the
   filesystem and report the counts ("`Reports/`, `Home/`, `Configurations/`, `Archive/` appear in 0
   of 21 projects") plus "trust the filesystem (`search_files`), not the README". A copied template
   README lists aspirational directories that were never created.
4. **Read the files that carry rules, not just the trees**: frontmatter conventions, the query/view
   filters that drive state transitions, template filename prefixes, naming formulas inside
   spreadsheets. A rule that lives in a filter expression (a view filtering on a frontmatter field
   being empty) is invisible to a directory walk and is usually the most important rule in the repo.
5. **Derive the version-control section from the repositories themselves.** Which projects are
   repos at all, the branch, the commit-subject convention actually used (`git log --format='%s'`),
   whether commits are automatic, the ignore reality (`git check-ignore -v`, the global
   `core.excludesFile`), and the size of the biggest tracked file. Commands, what each answers and
   the findings shape: `references/git-convention-derivation.md`.

### Counting traps

- **Two names for one concept** (`BacterialCulture` vs `Bacterial-Culture`, `Calender` for Calendar)
  usually means both are live. Count each; never silently normalise in the spec.
- **Auto-generated folders look like records.** A folder named only by a timestamp is an attachment
  dump. Classify a folder as a record only when it contains a note named after the folder itself.
- **Vendor and binary library dirs** (`*.library/`, `.obsidian/`, `site-packages/`) inflate counts —
  report them as excluded classes instead of traversing them.

## 2. The house format (fixed shape)

A draft written as prose plus markdown tables is rejected outright; this is the shape the user
supplies and expects:

- **Title + one-line purpose**, then a `### Project Structure` heading and one sentence stating what
  the repo must guarantee (every record findable by date and type; every sample traceable back to a
  box coordinate).
- **Nested imperative bullets, two spaces per level.** Top level: `- Gather all <unit> in \`<path>\``
  or a `Do not …` rule. Children carry naming/versioning, what every unit contains, and where its
  assets go.
- **Generic in both halves — no real project anywhere.** Naming rules use placeholders
  (`<Organization><NN>_<Keyword>_<YYYY.MM.DD>`, `pipeline-a.b.c`) and the tree uses the *same*
  placeholders under a generic root
  (`ObsidianVaultDirectory/<project>/Logs/<YYYY>/<MM>/<DD>/<Type>-<NNN>/<Type>-<NNN>.md`). Real
  project names, keywords, record titles, spreadsheet names, sample UIDs and hashes turn the spec
  back into a description of one repo; a tree of real paths is rejected as 太具体 even when the rules
  beside it are abstract. The tree must be copy-usable on any root of this shape.
  - Where the full placeholder makes every line unreadably long, define a short alias on the first
    line (`# <project> = <Organization><NN>_<Keyword>_<YYYY.MM.DD>`) and use `<project>/` below it.
  - **Domain vocabulary stays literal**: the closed sets a future session must reuse verbatim — the
    `<Type>` value list, the `@ _ ¬ ƒ %` template prefixes, `main.sh`, `workspace/data/` — are
    content, not instance names. Strip everything that names one particular thing, keep these.
- **Then `Below is the file tree`** and a single fenced block: one placeholder path per line, in the
  same generic form the rules use, with a `#` comment on the lines where a rule becomes visible — the
  gitignored data dir, the filter that drives archiving, the placeholder twin, the raw-export drop.
  The real traversal is how you learn which lines belong and how deep the nesting goes; it is not
  what you paste.
- **Close with `Things never committed to git`** (or `Things included in <dir>`) naming the excluded
  classes and their directories.
- **Version control is part of the structure, not an appendix.** A spec that never says the repo is
  managed with Git, or shows no `.gitignore`, is incomplete and will be sent back — the user reads
  it as a hole, not as out of scope. Always include: the branch, the commit granularity, the
  commit-subject convention the repo actually uses (`<type>(<scope>): <subject>` with the observed
  type and scope vocabulary, unsupported guesses omitted), whether a remote exists, and the ban on
  a nested `.git` inside the tree.
- **Show the ignore rules as fenced blocks, split by scope** — the in-repo `.gitignore` (the app's
  own directory, heavy data dirs, lock-file patterns, caches) and the global excludes file
  (`git config --global core.excludesFile`) for OS and editor junk. When several in-repo files
  disagree, write the **union** and say which repo omitted what; that disagreement is the evidence
  the rule is needed.
- **Give each exclusion its magnitude.** A `Do not commit X` rule lands only with the cost attached:
  the heavy directories' sizes, and the single biggest file that already got committed and what it
  did to `.git` (one 599 MB archive explaining most of a 678 MB `.git`).
- **Do not fold history repair into the spec.** A file already committed survives any new ignore
  rule; note it as a separate offer (with the command), never as a spec rule. Doing that separate
  job: §5.
- **Assertions, not advice.** Where the repo is deliberately inconsistent, forbid normalisation and
  give the mechanism: "`BacterialCulture-001` and `Bacterial-Culture-001` both exist — do not rename;
  renaming breaks wikilinks and the `.base` filters".
- **Prose in Chinese, proper nouns in English** (protein, strain, method and software names kept in
  their original form).

## 3. Where the spec goes

- **Always-loaded context versus depth.** A `SOUL.md` or `AGENTS.md` rides in every prompt: keep the
  condensed spec there and put the frequency tables plus the commands that produced them in a
  `README.md` in the same directory, with a one-line pointer between them. A pointer to a file that
  does not exist in that home is worse than no pointer.
- **When the destination is inside a profile**, resolve the live home from `$HERMES_HOME` and re-read
  the target before rewriting it — the user edits those files between turns. Recipe: the
  `hermes-profile-housekeeping` skill, §15 plus its profile-context-file-edits reference file.
- **Keep the user's own framing once they edit the draft** — their heading, their generic naming
  scheme, their explanation of a placeholder file. Rewrite the body around their wording rather than
  re-imposing yours, and report their wording as preserved.
- **Read their edit as a rule about abstraction level, not as a wording fix.** When they rename one
  concrete label to a generic one (a real root → `ObsidianVaultDirectory/`), they are asking for the
  same treatment everywhere the document is still concrete — apply it document-wide in that same
  turn instead of changing the one line they touched.
- **Measure the prompt cost** (`wc -l -c` before and after) and state the delta when the spec lands
  in an always-loaded file.
- **The lab RDM vault is already specified**: its distilled spec lives in this profile's `SOUL.md`
  under `## Organising a Research Data Management (RDM) Vault`, with the evidence tables in the
  profile `README.md`. Extend those two files; do not restate the conventions elsewhere.

## 4. Normalising one project against the spec (the audit direction)

The inverse of §1: the spec already exists and ONE project must be brought in line with it.

1. **Read the live repo state before assuming anything.** `git status`, `git log --oneline | wc -l`,
   `git branch -a`, `git remote -v`. The project is usually already a repo, so a request to "git init"
   really means "commit a baseline first": commit the pre-existing state (including anything you have
   already changed) under the repo's own subject convention BEFORE the first rename, then commit
   again at the end with one focused subject per logical change.
2. **Derive the findings matrix from the filesystem, never from the spec text.** Run
   `scripts/audit-project.py <project>`: record-folder classification (new-form / legacy / other),
   note-named-after-its-folder, `assets/` and `workspace/data/` presence, per-field frontmatter
   presence, every `archive-id` value, inlink counts, dangling link targets. Those counts are the
   report's evidence and the fix list. Hand-check one row before trusting the matrix.
   **The script walks `Logs/` only** — on an older-generation project (records under
   `Records/<bucket>/(<YYYY-MM-DD>) <Title>/`) it prints `record folders: 0`, and walking the whole
   tree miscounts the record notes several-fold. How to count them correctly, plus the frontmatter
   back-fill and missing-embed recipes: `references/normalisation-pass.md`.
3. **Verify the spec against the wider library before enforcing it.** A spec is written once from a
   survey and the projects then move on, so the vault is often right and the spec stale. For each
   rule about to be enforced, count current usage across the sibling projects (`<Type> Entities` vs
   `Entities`, `protocol` vs `protocols`, literal `.bak` vs `*.bak`, `Records/` time-buckets vs flat
   notes). Where library consensus contradicts the spec, fix or report the SPEC — never bend the
   project to a stale rule. Known drifts and how to check each: `references/normalisation-pass.md`.
4. **Tier the fixes and stop at the tier boundary.** Tier 1 = in-spec, no name changes, reversible:
   repo config, a stale template README, misfiled assets, missing required frontmatter keys, broken
   `adv-uri` vault names, file permission modes, junk directories. Apply those, verify, commit.
   Tier 2 = anything renaming a file/folder or moving an organ (protocol versions, record folders, a
   misplaced directory): put it to the user as ONE multi-select clarify with the evidence per item,
   and touch nothing until answered. When the answer comes back as the record-layout change
   (先迁移 Records), the old-layout → `Logs/<YYYY>/<MM>/<DD>/<Type>-<NNN>/` recipe — Type mapping,
 per-day serials, the asymmetric tag edit, the `Logs.base` to copy — is in
 `references/normalisation-pass.md`. So are the two other shapes this tier arrives in: dissolving a
 `Protocols/` container into one folder per protocol with citation-derived `- Series<N>.v<M>` names,
 and removing a directory class the user has declared deprecated (folder **and** references).
   **Order the session around the user's question, not the spec's structure.** When the same request
   also asks a data-safety question ("can the copy on the server be deleted?", "上那份能删吗"),
   answer that first, with live evidence, and **do not rename or move any path while a path-level
   comparison against an external manifest is still pending** — that comparison joins on paths, so a
   rename silently invalidates it and the user will stop the pass for exactly this reason (拆库以后
   匹配文件麻烦). Apply the no-rename tier-1 fixes, report the counts, and hold the moves.
5. **Count the inlinks before any rename.** `[[name]]` and `![[file.ext]]` resolve by basename, so a
   move that keeps the basename breaks nothing and a rename needs every referencing note updated in
   the same pass. `.base` views survive a *rename* — they filter on tags, frontmatter and UUIDs, not
   filenames — but a base that groups rows by a **tag** is coupled to the tag vocabulary: retire a
   tag root and its view goes silently empty, so its filter, and the notes carrying that tag, must be
   rewritten in the same pass. `adv-uri?…&uid=<uuid>` survives renames and moves; only its
   `vault=<name>` parameter breaks, and it breaks silently when the vault directory is renamed.
6. **Implement the user's decision even when the files contradict it, and surface the contradiction.**
   Approved wording is not overruled by your reading of the files: give the contradicting quote, say
   what the evidence supports, and hand over the single command that flips it.
7. **A clarify that times out unanswered: take the conservative branch and label it.** For a move,
   keep the basename and land in the nearest existing convention, then report the assumption and the
   alternatives not taken. Never silently pick the branch that merges content or deletes a directory.
   **The same labelling applies to a later terse directive** ("模版文件更名", "Protocols 拆",
   "`Inventory` 已经弃用"): it approves a line you already listed, so execute it instead of re-asking,
   take the conservative branch on the sub-choices still open — keep the sample code in a filename,
   flag rather than delete a sibling class the user did not name — and say in the report which branch
   you took and what the alternative was.
8. **Report findings-with-evidence plus what you did NOT change.** One table of deviations with the
   measured number behind each; one table of items deliberately left alone with the reason
   ("library-consistent", "legacy — do not convert", "awaiting your decision"). A deviation with no
   measurement behind it is not a finding. **When the user asks for a one-line answer**
   (一句话回答 / 不要检索), that line is the deliverable: answer from evidence already gathered,
   without re-running checks or appending paths and caveats — and say separately, in one clause, when
   the claim rests on a change made moments earlier and therefore still needs the live check.
9. **Leave a snapshot when the pass changes layout, not just content** — `Migration/<YYYY.MM.DD>.<NNN>/`
   with an idempotent `do_migration.py` (`--dry-run` the default, `--apply` writes) plus a `README.md`
   carrying the counts, the evidence and the undecided items; run the exact command its README
   documents before committing it. Shape and checks: `references/normalisation-pass.md`.
10. **Count embeds of files that do not exist rather than assuming them** — a view the project never
    carried renders empty in every note that embeds it; report the count and where it does exist, and
    put a copy-in to the user as a content decision.
11. **Back-filling missing required frontmatter is tier 1** — scripted, verified with `git diff
    --stat`, one commit for the uuid4 `UID` batch and a separate one for the empty-list keys.
    Insert recipe: `references/normalisation-pass.md`.
12. **Reconcile the record ids against the project's sample ledger before calling the pass done.**
    Projects whose samples live in a ledger (a Dolt library, a spreadsheet) accumulate record text
    that no longer matches the ledger's keys: prefix typos, old-style date-code ids, an id whose
    batch is not the batch held in stock. Extract every id the records mention, classify it
    (in-ledger / should be in the ledger / different batch / unresolvable / not a ledger id at all —
    design codes, purification batch numbers, data-archive numbers, placeholder codes, another
    project's ids), then converge: the ledger side takes the historical spellings as `aliases` with a
    reverse-lookup view, the record side gets the corrected key plus a visible trace block.
    Step-by-step, the acceptance queries and where the evidence lives:
    `references/record-label-reconciliation.md`. Two user rules override convenience — **ids whose
    batch numbers differ never share a key** (a batch the ledger lacks gets its own row with its
    position unknown, it is NOT aliased onto another batch), and **no unresolved id may be resolved by
    inference** (mark it position-unknown and keep the record text).

### The spec-change direction (the user redefines the spec)

A request phrased as a rule — "`A/` 和 `B/` 都合并到 `C/` 中", "不要再分类，`C/` 里平铺" — changes the
spec AND leaves every vault non-conforming. Two deliverables in one session: the spec files (§2, §3)
and the migration of the vaults in scope, committed. Elicit the layout choices with ONE multi-choice
clarify whose options quote the real paths, then execute; do not start moving while the layout is
still ambiguous.

1. **Expect these answers and offer them as the recommended option** (this user's defaults for a
   structural merge): one folder per entity, named by the entity's title *without* its version
   suffix, holding all of that entity's versions plus its assets; a category layer is **dropped**,
   never folded into the path — title and `keywords` carry it; merged-in files lose their
   `_PREFIX_`/`_pipeline-` stem and are renamed verb-object by what they do; identity moves to a tag
   `<NewRoot>/<entity name>`, applied to the notes that *reference* the entity as well as to the
   entity's own note.
2. **Map the blast radius before moving any path.** A directory that reads as a leaf is usually an
   identifier space other files depend on. Build the old→new token table first, from greps over the
   concept's *token* rather than its path: the hierarchical tag on records (one tag root was the
   "which pipeline did I run" marker on 7 records), `.base` filters matching that tag root,
   path-qualified wiki links (`[[C/Purpose/Note]]` — these do not fall back to basename), and plugin
   state under `.obsidian/` (gitignored — leave it alone). Per-token frequency is the table's
   evidence (`search_files` for the pattern; a shell count is `grep -rho '<Root>/[^ "]\+' --include='*.md'
   | sort | uniq -c`), and different spellings of one concept are separate tokens.
3. **Check that the vault's own rules doc mentions the directories at all** before offering to sync
   its per-project copies: they are often silent on structure (0 hits for every directory name), in
   which case that step is a no-op — say so instead of performing an empty edit.
4. **Move with `git mv`, destination parent created first, and verify with three independent
   reads**: the destination tree, a vault-wide `grep` for the retired token (expect only prose that
   intentionally names it), and `git show --name-status HEAD | grep -c '^R'` for the rename count.
   One commit, in the repo's own subject convention, with the file counts in the report.
5. Land the layout rules in the spec files — the `SOUL.md` tree plus the matching `README.md` section
   and a `**修订：**` line naming the sections touched — not in this skill (§3).

## 5. Retiring a heavy artifact that is already committed (the §2 "separate offer")

An archive under `Backup/` or a `Data/` blob that is **already tracked** is fixed by neither an ignore
rule (§2) nor by `rm` + commit. Two halves, agreed separately: which text comes out of it, and when
the blob leaves history.

1. **Measure before asking, and make the options carry the numbers.** The request arrives
   underspecified ("解压为 json") and the plausible outputs differ by three orders of magnitude — a
   path+hash manifest (~0.3 MB), the ledger tables alone (~0.2 MB), text inlined (~130 MB), base64 of
   everything (~1.3 GB of text nobody can diff). Census the archive first (entry count, extension ×
   count × bytes, the biggest entries, whether it is tracked, what it did to `.git`, and the sibling
   projects' tracked-file count as the norm), then ask ONE clarify whose choices quote those
   measurements, recommended first. Measured options get answered; a bare "please clarify" does not.
2. **Convert only the text-shaped ledger, and give every output its provenance.** Every `.xlsx`/`.csv`
   in the archive is not automatically a ledger — enumerate them all, convert the subset the user
   names, and name in the deliverable the ones excluded and why. One `<basename>.json` per source
   table plus a `_manifest.json`; each carries the source identity (path *inside* the archive, sha256,
   byte size) so it stays traceable with the archive gone. Rows positional (`columns` + `rows` as
   lists) so a duplicate or blank header cannot collapse a row; empty cells `null`; record how many
   trailing empty rows/columns were trimmed instead of dropping them silently. Schema, commands and
   pitfalls: `references/heavy-artifact-retirement.md`.
3. **Verify losslessness against the source, not by eye.** Re-read the archive and compare cell by
   cell, re-derive each source sha256, and report "N/N tables, 0 diffs". A conversion reported done
   without that diff is a claim, not a result. Re-runnable verifier:
   `scripts/verify_archive_table_json.py`.
4. **The heavy remainder goes outside the vault, onto durable storage** — the whole `Data/`/`Backup/`
   class never enters the repository (§2). Extract to a plain directory on another volume or a
   backup/external disk the user can browse — **never a home or system temp dir**: a `/Users/<user>/Temp`
   copy was displaced within ten minutes of being written and nothing in the logs said what did it.
   Leave a `_source.txt` stub beside the extraction (archive path, its sha256, entry count, extracted
   bytes, where the ledger JSON lives) so the copy explains itself once the archive is deleted. Prove
   the extraction with three numbers: files + dirs, bytes on disk versus the archive's summed
   uncompressed size, and `zipfile.testzip()` = every entry's CRC OK. Do not spill 1 GB of binaries
   into the vault and leave it there.
5. **Land the text in the tree by convention, not by invention.** Output under the domain directory
   named after the archive stem (`Inventory/Inventories-<NN>/`); a `_<Name>.md` directory page — the
   `_` prefix keeps it out of `.base` queries — recording source, sha256, the table list with per-table
   row counts, the JSON structure, what was NOT converted, where the remainder went, and any job left
   open. Link it from the domain index. Commit once, subject in the repo's own convention.
   **The converter script is not permanent vault content.** A committed `Toolbox/…_to_json.py` was
   deleted by the user in the very next commit — write the converter somewhere disposable (the
   profile scratch area), or, if it is committed, treat it as disposable: the directory page then
   carries a runnable recovery command (`git show <commit>:<path> > /tmp/<name>.py`) instead of a bare
   path reference to a file that may no longer exist.
6. **The blob leaves only with a history rewrite, and that is a separate agreement.** `git rm` +
   commit removes the file from the tip only; the blob stays reachable from the older commit, so
   `.git` does not shrink. Report the before and after measurement rather than implying the repo got
   smaller, and never rewrite history on your own initiative — it changes every commit hash. The
   alternative (keep the old version in history and document how to pull it back out with
   `git show <commit>:<path>`) is a legitimate answer the user has chosen before; ask, don't assume.
   Leave the pending rewrite flagged in the directory page so the next session finds the job open.
7. **When the rewrite is agreed, run it as a protected and verified operation.** Recipe, pre-flight,
   post-check table and the repairs it creates: §7 of `references/heavy-artifact-retirement.md`, with
   `scripts/verify_blob_purge.sh` for the checks. Three things it otherwise takes from you:
   `filter-repo` on a non-bare repo ends with `git reset --hard` — the artifact just removed from
   history is deleted from the working tree, so move it out first; the same tail expires the reflog,
   so there is no git-level undo; and the rewritten hashes make every commit hash quoted in the repo's
   own documents dangling, which must be re-pointed in the same pass.
8. **Deleting the source archive is a separate, evidence-backed answer.** When the user asks "can the
   copy on the server be deleted now" (上那份能删吗), do not answer from the fact that an extraction
   exists. Compare **path lists** (not counts) against a manifest taken from the source while it was
   reachable (`find . -type f -not -name '.DS_Store' | sort`), and `wc -l` the remote list first — a
   listing that silently returns nothing makes every local file look "extra" and inverts the
   conclusion. Probe the copy without the source: `unzip -t` every archive (CRC), magic bytes for large
   binaries (HDF5 = `894844460d0a1a0a`), `sips -g pixelWidth` for images. Check the manifest for `.git/`
   entries — none means the source carried no history the copy lacks; a missing `.DS_Store`-class file
   is metadata, not content. Close with the single-copy risk (one external disk left) and the final live
   check once the source is reachable: `rsync -n --delete`, expecting 0 to transfer and 0 to delete. If
   the source is unreachable, say the comparison used a stored manifest instead of implying it was live.

## Support files

- `scripts/survey-layout.py` — re-runnable survey of a multi-project root: per-project presence
  matrix, per-item frequency totals (the claimed-vs-actual check), and record-folder classification.
- `references/git-convention-derivation.md` — probing the repositories for the version-control
  section: which are repos, branch/remotes, the real commit-subject vocabulary, automation state,
  ignore reality including the global excludes file, the biggest tracked file that explains `.git`
  size, and the quoting/path traps in `git ls-files` output.
- `references/normalisation-pass.md` — depth for §4: the tier-1 command table, rename/move and
  workbook-inspection traps, and the known spec-vs-library drifts to re-check before enforcing a rule.
- `references/record-label-reconciliation.md` — depth for §4 step 12: the four-way id classification,
  the acceptance queries, the ledger-side alias / position conventions, and where a project's ledger
  evidence lives when it was never a spreadsheet.
- `scripts/audit-project.py` — re-runnable audit of ONE project: record classification, frontmatter
  presence matrix, archive-id histogram, inlink counts, dangling-link scan.
- `references/heavy-artifact-retirement.md` — §5 depth: the census commands, the output-scope decision
  table, the provenance JSON schema, the extraction + CRC proof, and the conversion pitfalls.
- `scripts/verify_archive_table_json.py` — re-runnable: re-reads each source table out of an archive
  and compares it cell by cell with the generated JSON, re-deriving source hashes.
- `scripts/verify_blob_purge.sh` — re-runnable post-rewrite check for one path: commit and tracked-file
  counts, whether the path still appears in any commit or object, `.git` size, `fsck`, reflog length,
  whether the working-tree file survived, and whether an ignore rule now covers it.
