---
name: obsidian-theme-development
description: "Use when developing or publishing an Obsidian theme."
version: 1.0.0
metadata:
  domains: [obsidian, css, electron, theme-publishing]
  related_skills: [obsidian, macos-computer-use, github-pr-workflow]
---

# Obsidian Theme Development & Maintenance

Maxim's theme is **Workbench** (floating sidebars + print-optimised layout), repo
`~/Repositories/Obsidian-Workbench-CSS`. Official docs: `docs.obsidian.md` → Themes →
Build a theme / Submit your theme.

## Repo shape and build

- `src/**/*.css` (nested, `@import`ed) → **`theme.css`**, built by PostCSS:
  `postcss-import-ext-glob` + `postcss-import` + a local `postcss-collect-settings.js`.
- `npm run build` == `postcss src/main.css -o theme.css`. `theme.css` is a build artifact
  (thousands of lines) — never hand-edit it, edit `src/` and rebuild.
- `postcss-collect-settings.js` hoists every `/* @settings ... */` YAML comment found in
  `src/` to the **top** of `theme.css`, because Style Settings scans the built file. So
  `@settings` blocks live beside the CSS they configure but land in one block after build.
- `manifest.json`: `name` / `version` / `author` / `minAppVersion`. `minAppVersion` means
  "Obsidian older than this cannot install the theme" — raise it only when the theme really
  uses newer CSS, or it cuts off users.
- Test/dev vaults: `VaultExample/` (store demo; `obsidian-style-settings`, `better-export-pdf`) and
  **`tests/VaultTest/`** — the only vault the regression suite may drive, never a real vault. Wire it
  with `./tests/VaultTest/link-theme.sh` (+ `link-plugins.sh` for the export plugin). `npm test` is the
  offline tier (artifact freshness vs `src/**`, import graph, Style Settings contract, print invariants,
  audit-tool baseline, release surface) and must stay green with no app running; `npm run test:live`
  adds computed-style and real-PDF checks via `./tests/VaultTest/run-test-vault.sh`, which opens a
  **throwaway profile** so a running window is untouched. `tests/README.md` documents both, with the
  measured numbers. A vault's `.obsidian/appearance.json` `cssTheme` must equal the theme
  folder name actually present under `.obsidian/themes/` — `VaultExample` spent a while naming a theme
  (`Obsidian-Workbench-CSS`) that no folder matched and shipping no theme dir at all, i.e. it rendered
  with the default theme while looking set up. See `references/demo-vault-and-store-assets.md`.
- Keep `src/*.css.bak*` out of the tree: agents read `.bak` files as source.
- `@import-glob` warns once per empty file it matches and once per glob that matches no directory
  (`mobile/**` with no `mobile/`). Treat a warning-free `npm run build` as the baseline: those
  warnings are the only signal that a placeholder or a glob went stale, and they are cheap to keep at 0.

## Verification loop (applies to every change)

1. **Load the built file, never a copy.** Symlink the repo root (it already contains both
   `manifest.json` and `theme.css`) into `<dev-vault>/.obsidian/themes/<Name>/`.
   Prove the link is live before trusting observations:
   `md5 -q theme.css` vs `md5 -q <dev-vault>/.obsidian/themes/<Name>/theme.css`.
   Equal hashes only prove "not stale"; an identical pair right after editing `src/` without a
   rebuild is the signature of hand-copying, i.e. you are looking at old CSS.
2. **Judge CSS from rendered pixels, never from reading selectors.** Produce an artifact —
   a screenshot of the Obsidian window, or a print PDF converted to PNG — and look at it.
   Reading CSS is how you reach plausible-but-wrong conclusions.
3. **Only a seeing agent can close this loop.** For visual iteration use a path with
   screenshots + vision (Hermes `computer_use` on the Obsidian window; PNG → `vision_analyze`).
   A terminal-only coding agent is the "hand" for mechanical work (refactors, build scripts,
   release chores); give it the constraining rules through `AGENTS.md`, not visual judgement.
   `AGENTS.md` at the repo root is the right carrier (Codex/Cursor read it).
4. **Never mutate an app he is using behind his back — but once he hands it over, run the loop
   end to end yourself.** Quitting/relaunching his daily Obsidian with a debug flag is his call while
   it is running: ask, or hand him the command with the expected output. The moment he says he has quit
   it ("you do the rest", "reduce what I have to do"), take the whole loop — launch with the debug port,
   drive CDP, run the exports, and **relaunch his normal window (no debug port) when finished**, then
   report that state as verified. Best of all, do the work in a throwaway profile and never touch his
   app (see `references/demo-vault-and-store-assets.md`).
5. Put new tooling in `tools/` inside the theme repo and leave it **untracked** unless he asks
   to commit it.

## Shipping a build into the local vaults

Every vault under `~/Documents` and `~/org_zsqlab/Obsidian` can hold an install of this theme, and those
copies **drift** — hashes measured across them belonged to four different builds, so "the vault has the
theme" says nothing about which version. Run `scripts/sync-theme-to-vaults.py` (dry run by default,
`--apply` to write, `--install-missing` for vaults without the theme): it finds vaults by walking the roots
for `.obsidian/`, hashes every install against the fresh build, backs up what it replaces, and re-verifies
every copy at the end. Rules behind it, each of which cost time when violated:

- **Never overwrite a symlinked install.** The dev vaults symlink the repo (Verification loop §1);
  replacing the link with a copy silently ends hot-reload and creates a second source of truth. Skip it and
  report such installs as already live.
- **Compare content hashes, never size or mtime** — `shutil.copy2` preserves the source mtime, so a freshly
  synced file can look older than the file it replaced.
- **Installing is not activating.** Copying `theme.css` + `manifest.json` into a vault that has no theme dir
  must leave `.obsidian/appearance.json` untouched (the personal travel/investment vaults run the default
  theme and stay that way until he asks).
- Match installs by the manifest `name` **and** the folder name; a vault may hold the theme under a different
  folder name.
- Before telling him "no vault-side commit needed", verify it: `git -C <vault> ls-files --error-unmatch
  .obsidian/themes/<Name>/theme.css` (`.obsidian/` is usually untracked, but that is a fact to check).
- **Do not imply a running window picked the file up.** A window already running when you wrote the file
  cannot be inspected from outside (CDP needs `--remote-debugging-port` at launch), so report "verified on
  disk, live reload unverified" — unless you launched/relaunched it yourself, which is the preferred path
  once he has handed the app over (Verification loop §4).

Repo landing convention (his instruction): **three commits, in this order** — config/docs (`AGENTS.md`,
`.gitignore`) → `tools/` → the `src/**` change *together with* the rebuilt `theme.css` artifact. When the
work is several independent themes (parallel workstreams) he accepts **3–5 commits by theme**, and every
commit can still ship a *self-consistent* artifact: stage it in a temp tree — `git archive HEAD | tar -x -C
/tmp/stage`, overlay that stage's `src/` files, run the build there, copy the resulting `theme.css` in — so
no commit ever has `src/` newer than its `theme.css`. (Landing the artifact once in the final src commit is
acceptable but must be stated in the report as a deviation.) Subjects in
English conventional-commit form (repo history is English). Push only on request, and confirm the remote
actually moved with `git ls-remote origin main` — push output alone is not verification.

## Print / PDF testing

Read `references/print-and-pdf-pipeline.md` before touching any `@media print` rule: it holds the
three rendering pipelines, the app's own print CSS, and the measured traps. Run `scripts/cdp.py`
(live full copy, with an extra HTML-diff subcommand: `tools/print-harness/cdp.py` in the repo).

Three traps to know before starting:

- **Printing with no `.print` element in the DOM renders a blank page** — Obsidian's app.css has
  `body > :not(.print) { display: none !important }` inside its print block.
- **Under print-media emulation `outerHTML` is byte-identical to screen media.** Only computed
  style and layout change, so compare `getComputedStyle` or rendered pixels; diffing HTML text
  returns "0 differences" and tells you nothing.
- **A whole-page fit-shrink is content-side, and its fix must be media-less.** When everything in the
  export — including a ruler you injected — comes out ~2/3 size, an oversized view (typically a Base embed)
  made Chromium scale the whole page; cap it with rules scoped to `.print` but **not** wrapped in
  `@media print`, which measurably does not work (see the pipeline reference).

## Structural audit & neutral refactor (shrinking `src/` without changing rendering)

Depth + commands: `references/dead-css-audit.md`. Tooling lives in the repo under `tools/css-audit/`
(`analyze.js`, `extract-app-css.py`, `check-tokens.py`; `--strict` is the CI-shaped gate). Classify
**every** candidate edit as provably neutral or behavioural; only neutral ones skip the pixel loop.

- **A selector that can never match is deletable — but only when the app's own `app.css` lacks the
  class name.** Extract `app.css` from `obsidian.asar` and count. `.CodeMirror-*` and `.mod-cm5` are
  CodeMirror 5 leftovers (0 hits, while `cm-s-obsidian` 155 / `HyperMD-header` 29 / `HyperMD-with-alt` 3
  are live CM6 classes) — from the theme's own text alone they look equally plausible, and deleting the
  live ones costs rendering.
- **A declaration repeated inside one rule block**: the earlier one is already dead, delete it. Across
  *different* rule blocks the later one winning is ordinary cascade — leave it alone.
- **A referenced-but-undefined custom property** is only a bug after theme.css, `app.css` and the owning
  plugin's own stylesheet all miss (`--canvas-node-height` is the app's, `--cmdr-spacing` is Commander's).
  For the genuinely undefined ones, replace the `var()` with the literal equal to that property's `unset`
  (`background` → `transparent`, `border-color` → `currentColor`, `border-radius` → `0`, `line-height` →
  `unset`) and keep selector, position and `!important`: same cascade slot with an equivalent value is
  neutral, whereas *deleting* such a declaration lets earlier rules win and does change rendering.
- **Never "fix" an invalid `calc()` or a `var()` name that has operators inside it.** The broken
  declaration is being dropped today, so repairing it to the value you think was meant is a
  behaviour change — delete it and say why.
- Anything touching a value, merging `@media` blocks or reordering selectors is behavioural: it needs
the pixel loop, not a diff argument.

Hard gates, strongest first: (1) **byte-identical build** — build to a scratch path, `md5` against
`theme.css`, equal hashes prove a hygiene pass changed nothing; (2) **the diff contains only the
intended hunks**; (3) **an `@import`-order-preserving split of a monolith must give a zero-line diff** —
`@import` order *is* concatenation order, so a wrong ordering appears immediately as a cascade diff.

**Parallel subagents share one artifact.** `theme.css` is the single build output, so when several
agents edit different `src/` files at once each must build to its own scratch path and never write
`theme.css`; the parent rebuilds once and owns the artifact commit. State in every child's brief that
its scratch diff will include its siblings' edits, so it is accountable only for its own file set.

## Publishing / review checklist

- The community directory reads `manifest.json` at the **HEAD of the default branch** — commit it
  before submitting.
- Obsidian installs from the GitHub release whose **tag equals the manifest version**, taking
  `manifest.json` + `theme.css` from that release's assets. A tag/version mismatch is a broken
  install for every user.
- **Cutting a release** (first one included): bump `manifest.version`, commit, `git tag <version>` with the
  *bare* version as the tag name (no `v` prefix), `git push origin main --tags`, then
  `gh release create <version> theme.css manifest.json` — not a draft, not a prerelease. Attach the freshly
  built pair, never a copy lying around from an earlier build.
- **Verify a release by downloading it, not by reading the command's output**: pull the published assets
  back (`gh release download <tag>` / the `browser_download_url`), check the downloaded `manifest.json`'s
  version equals the tag and the downloaded `theme.css` md5 equals the build you actually tested. Re-check
  `git ls-remote origin refs/heads/main` against `git rev-parse HEAD` in the same pass — a push reported as
  successful is not evidence the remote moved.
- `authorUrl` in the manifest should be the GitHub account that owns the remote (read it off the remote, do
  not guess) — the store listing links there. Bumping the version also means keeping the copy **installed in
  the vaults** in sync; that is the version the app displays.
- **The store screenshot comes from `VaultExample/`, with synthetic placeholder content only — never from a
  real vault.** He will reject a screenshot of his own notes, and a public repo cannot retract one that
  leaked lab data. Demo-vault setup, throwaway-profile capture recipe and a pre-commit checklist:
  `references/demo-vault-and-store-assets.md`.
- Needed before review: a `README.md` describing the theme, a 512×288 screenshot, a license.
- Run `stylelint-config-obsidianmd` the way obsidian-sample-theme does (`npm install` once, then
  `npm run lint`): it enforces the same CSS rules the theme review applies, far cheaper than a
  rejection round.
- Submit at `community.obsidian.md` with an Obsidian account and a linked GitHub account. Only
  the first version is submitted; later versions reach users through GitHub releases.
- Never claim the theme is published without checking: fetch
  `obsidianmd/obsidian-releases` → `community-css-themes.json` and search the theme name/author.

## Auditing / refactoring the tree

`tools/css-audit/` (in the theme repo) is the toolset; README → "Auditing the codebase" documents it.
Run the guard before claiming a cleanup is done:

- `extract-app-css.py` — pulls `app.css` out of `obsidian.asar`. **That copy is truncated and stale** (426 KB
  vs 655 KB served at runtime, with different values) — never audit against it. Use
  `fetch-app-css.py`, which asks the running app for `app://obsidian.md/app.css`.
- `check-tokens.py --strict` — must report **0 mirrors**: no file under `global/design/` may re-declare a
  custom property with the same value Obsidian already defines at the same selector context. A mirror is
  only a mirror when value **and** selector context match **and** the app's declaration is not wrapped in an
  at-rule. 312 + 69 such copies were removed once; what remains are real overrides (the theme deliberately
  pins some pre-`color-mix()` values, so expect ~60–80, not a handful).
- `verify-refactor.js <old.css> <new.css>` — the acceptance gate: reports differences as
  selectors/declarations, so every removal needs a reason and **0 added declarations** is the target.

Two proof patterns that make a refactor safe, both used on the Workbench cleanup:

1. **Splitting a monolithic CSS file is neutral iff** concatenating the slices reproduces the original
   bytes *and* the rebuilt artifact is md5-identical. Slice on line ranges, keep the `@import` order
   equal to the original concatenation order, and edit `main.css` with a full read first — it carried
   240 lines of real CSS below its `@import` list, which a glob-only assumption silently deleted.
2. **Removing a declaration is neutral iff** it is either dead by prefix, overridden later in the *same*
   block, or never matched. "Never matched" needs the class-name check above.

## Pitfalls

- **Never use `obsidian.asar`'s `app.css` as the reference — it is truncated and stale.** The live sheet
  (`fetch('app://obsidian.md/app.css')` from the running app, via `tools/css-audit/fetch-app-css.py`) is
  655 KB against the asar's 426 KB and holds different values. Auditing token mirrors against the asar copy
  made `--code-normal: var(--text-muted)` look like a byte-identical copy of the app default (the live app
  says `var(--text-normal)`), so deleting it dropped printed inline-code colour from `#5a5a5a` to `#222222`.
  The same trap applies to any “does this class exist?” question.
- **`check-tokens.py --strict` is app-version dependent — pin the instance before trusting it.** The
  same theme reported **0 mirrors** against the app its tokens were audited on and **56 mirrors**
  against an Obsidian 1.6.7 instance: an older served `app.css` makes deliberate overrides look like
  copies of its defaults. A fresh throwaway profile resolves an *old* bundle (1.6.7 here, below the
  theme's own `minAppVersion: 1.10`), so read the app version off the instance you are measuring —
  `npm run test:live` prints it and skips that check when the instance is below `minAppVersion`.
- **A silent rendering change is only caught by rendered pixels.** For a refactor, export one real note with
  the old and the new build (`tools/print-harness/export-probe.py` → `cdp.py png` → thresholded per-page
  pixel diff) and first prove the pipeline is deterministic by exporting twice with the *same* build
  (byte-identical pages). Reading CSS, or comparing declaration text, will call this class of regression
  “neutral”. Keep a copy of the pre-change `theme.css` around; it is the comparison baseline.
- **`cdp.py` in the harness needed `suppress_origin=True`** on `websocket.create_connection`, otherwise every
  call 403s even though the README claims it is handled (Obsidian adds an `Origin` header check).
- **Spot-check one entry of a generated edit list before applying it in bulk.** A hand-written
  "duplicate, keep the later one" classifier flagged the *winning* declaration of each same-block duplicate
  instead of the dead one (CSS keeps the **last** of two identical properties); applied as-is it would have
  deleted live styling in 19 blocks. One hand-read block caught it. Read one candidate in the source, confirm
  it is really the dead side, then run the batch — the generator's own summary is not evidence.
- **The app version is per-profile, not per-install.** `Info.plist` reported 1.6.7 while his profile's window
  title reported 1.14.2 (he runs the insider channel), and a throwaway profile resolved 1.13.7 — the bundle on
  disk is only the updater's starting point, and each profile tracks its own channel. Read the version off the
  *window title of the instance you are actually driving*, and quote the running app's own stylesheet (not a
  plist) when a doc claims “verified against Obsidian X”. A demo shot taken in a fresh profile therefore shows
  a different app version than his daily one — fine for a store image, not for a compatibility claim.

- **Obsidian's CodeMirror 6 reuses CodeMirror 5 class names.** A block copied from CodeMirror 5's default
  theme is *not* wholesale dead. Check each class in the extracted `app.css` first: `.CodeMirror-*` and
  `.mod-cm5` occur **0** times (dead), while `.cm-tab`, `.cm-searching`, `.cm-fat-cursor`,
  `.cm-animate-fat-cursor`, `.cm-negative`, `.cm-positive`, `.cm-strikethrough`, `.cm-invalidchar`,
  `.cm-force-border`, `.cm-tab-wrap-hack` and `.HyperMD-*` are live. Deleting the whole block silently
  drops editor search-highlight/tab/cursor styling — 11 rules had to be restored on Workbench.
- **PostCSS preserves comments**, so "just add a note" is not output-neutral: a comment added to
  `src/main.css` changes `theme.css`. Also, `src/main.css`'s trailing-newline shape is visible in the
  artifact — deleting its last line (rather than blanking it) shifts the built file's tail.
- **`-ms-`/`-moz-`/`-o-` declarations are dead in every Obsidian runtime** (Electron, Android WebView,
  iOS WebKit) and can be deleted; `-webkit-*` must stay. `-webkit-transform` next to `transform` is an
  alias duplicate in Blink/WebKit — verify in the live app before touching it.
- **Unresolvable `var()` hooks are features, not bugs.** `--stickies-color-1/2`, `--theme-color`,
  `--p-kanban-*`, `--cmdr-spacing` (Commander plugin), `--co-radius` are override points for snippets
  and plugins; replacing them with a literal silently removes the customization point.
- **Delegating CSS edits to subagents: pre-compute everything.** Hermes subagents on this profile time
  out after ~180 s. A subagent handed "analyse and clean up this 1200-line file" burned its whole budget
  on exploration and edited nothing; two more died in the verification phase. Hand over exact line
  ranges, a frozen keep-list, and ready-made scripts — or make the edit yourself. Never let a subagent run
  `npm` (it hangs waiting on the registry).

- A theme folder named differently from `.obsidian/appearance.json`'s `cssTheme`, or from the
  symlink target, means "I already symlinked it" silently is not in effect — verify by path, not
  by memory.
- When print output surprises you, or when you need to know whether a class name / custom property still
  exists in the app, read the app's own code instead of reasoning from the theme: `scripts/extract-asar-member.py`
  pulls `app.css` out of `obsidian.asar` and `references/electron-cdp-inspection.md` covers the rest
  (protocol rules, the throwaway-browser sandbox, and `scripts/cdp-min-client.py` — a known-good
  client to run when a CDP script of your own hangs).
