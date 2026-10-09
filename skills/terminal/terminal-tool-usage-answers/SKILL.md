---
name: terminal-tool-usage-answers
description: Use when asked how a tool works or is set up, where a setting lives, or why its layout behaves that way.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags:
      - terminal
      - cli
      - tui
      - usage
      - pty
      - verification
    related_skills:
      - tui-widgets
      - computer-use
---

# Terminal / CLI tool usage answers

Scope: answering "how do I use this tool" (keys, options, basic usage) and "where is that setting" for terminal programs and for installed GUI apps, plus verifying what an interactive program REALLY does when the docs are not enough.

## When to Use
- The user asks how a terminal program works: keys, options, "basic usage", "how do I get out of X".
- A TUI opens by accident (git commit without `-m`, `crontab -e`, `visudo`) and the user needs the exit path.
- You must verify what an interactive program really does — prompts it prints, side effects of a key, version-specific defaults — instead of trusting memory or a blog post.
- You are about to advise an editor/tool for editing long or structured files and need to know its wrap/justify behavior.
- The user cannot find a setting in an installed GUI app ("找不到设置", "where do I change X") — read that installed copy (config, release notes, binary strings, translations), never answer from memory or from another version's docs.
- The setting lives in **macOS System Settings** ("怎么关掉 X 功能", "这个开关在哪") — that is not an installed app: identify the pane extension, confirm it on this machine, then deep-link it so the user is looking at the right pane. Recipe: `references/macos-system-settings-panes.md`.
- The user's complaint names a surface ("背景", "底色", "theme") that several settings could own, and you must pick the one that is actually wrong before answering.

## Answer shape (do this first)
- One sentence of mechanism ("every command is a Ctrl combo; `^` means Ctrl"), then examples. The examples ARE the deliverable: the command line + the exact text that appears on screen + the next key to press.
- If the answer moves or locks the user's real files, run the layout in a scratch copy FIRST and lead with the measured consequence — where the bytes end up, what turns read-only, the one command that shows it (`du -sk`, `ls -l`, inode compare) — before any steps. Then number the steps and stop before the first step that touches bulk data, asking for that step's output before continuing. When the user has already named the design (e.g. "repo goes in the other folder"), state that choice's measured consequence and do not re-open it as a menu of alternatives. That scratch-copy measurement is your own check, not the reply: once the design is settled and the user is mid-execution, lead with the numbered commands and one line of expected output — a pushback like "不用帮我测试，直接告诉我怎么做" means drop the probes from the answer entirely, not run them quietly; a handover ("让我自己操作，不要替我操作") means stop running commands against their files at all — read-only inspections included — and answer with the commands they will type.
- Name the concrete parts — `git` directory, working tree, object store (`.git/annex/objects`), symlink — and never a metaphor. An analogy maps two real paths onto two invented nouns, so the user must guess which real path each noun stands for; you will get the mapping corrected (twice, in the session this rule came from) and then be told to drop metaphors entirely ("严禁用比喻"). For "what does this flag do", quote the tool's own wording (the `git-init` man page on `--separate-git-dir`) plus the one command that shows the result.
- "What does 进 / 不进 actually mean" and "where does the data live" are MODEL questions, not options questions: draw the literal tree of the directory (working-tree files -> `.git/index` -> `.git/objects` -> `.git/annex/objects` -> the location-log branch), define each word by the path it names, then give the single structural rule that resolves it — the tool splits a ~100-byte pointer per path from the bytes, so "git grows" and "the content store grows" are two different costs, and only one of them is reclaimable. Say which. Confusion about a two-layer tool is usually the user pricing the wrong layer.
- When the request is a mirror of a design you already gave ("把你的步骤反一下"), answer with the swapped commands and only the extra step the mirror forces, one clause of consequence per directory. Re-deriving the whole scheme reads as complication ("好像弄得很复杂") — the user has already accepted the scheme and is asking for one edit.
- Order by what the user will actually do: open / edit / save / exit -> how to GET OUT -> search -> cut-paste -> traps. 3–6 examples. A "basic usage" question is not a research project.
- Always include the escape hatches, asked or not: quit without saving, cancel the current prompt, and the family's classic trap (e.g. `^S` is not save in pico-class editors).
- Quote the tool's own prompt strings verbatim (`Save modified buffer (ANSWERING "No" WILL DESTROY CHANGES) ?`): the literal string is what the user recognizes on screen.
- Close with complete statements: what was measured, and explicitly what is still unexplained. Never present a guess as verified.
- Do NOT escalate to binary/source probing while the tool's key menu, `-?`, `--help` or man page already answers the question. Escalate only when the answer hinges on a version-specific default, or the user asks whether it *really* does X.
- If a probe is already running and the user pushes back ("is this really that complicated?", "just give me examples"), kill it — backgrounded process included — and answer from what is already in hand.

## Local ground truth before guessing
1. Identity/version: `TERM=xterm <tool> -version`. Wrapper distros alias names both ways (a `pico` may be GNU nano, a `nano` may be real Pico), so trust the banner, not `which`.
2. Option table: `<tool> -?` (pico prints its full table this way), `-h`, `--help`.
3. Embedded strings: `strings -a <binary> | grep -E "^ -[a-zA-Z]"` for the option array; for the help body, do a byte search (`open(path,'rb').read().find(b'<help headline>')`) and dump the following few KB — it holds the key list and the exact prompt strings.
4. The program's own key menu is the primary doc: pico-class editors print their key list on the bottom two lines and full help under `^G`.

## Validate the exact string before you teach it
The tool's identity and `--help` are not enough: manuals, blog posts and *doc-distilled skills* carry syntax the installed version rejects. Ground-truth the literal string.
- Run the candidate through the tool's own validator. git-annex: `git annex matchexpression '<expr>'` accepts or rejects an expression and touches no data; then `git annex config --get <key>` to read back what was actually stored. Other families: `--dry-run`, a `validate`/`check`/`--syntax-check` subcommand, a `parse` mode.
- The tool's matcher is the arbiter, not the manual: the git-annex manual's own example `largerthan(500kb)` is rejected by 10.20260901 (`Parse failure: bad size`); sizes must use `=`, e.g. `largerthan=500kb` (units case-insensitive). Same failure hit `wanted` preferred-content expressions.
- A bad value often does not fail where it is set — git-annex stores it, then throws an uncaught exception on the *next* `add`. Verify in the order: set → read back → try it on ONE file.
- When the wrong command came from a skill, fix that skill's text in its source repo in the same session and reinstall/update the copy; routing around it in the answer leaves the next session to hit it again. Grep the whole skill directory for the bad string before committing — `test-prompts.json`'s `expected_behavior` usually quotes the command verbatim, so a missed copy keeps re-teaching the rejected syntax to the skill's own regression run. Verify the installed copy afterwards (`grep -rn`), not just the push.
- The installed tree is never where that fix goes. An edit made in a profile's installed copy of a hub-installed skill is a dead end: `check` then reports `update_available` although the copy is *ahead*, `update` skips it as "kept your local edits", and the obvious repair (`--force`) rmtree-replaces the directory and deletes the edit. Edit the clone, commit by pathspec, push, then `hermes skills update <name> --force` — which *still* prints `kept your local edits` (the skip verdict is the recorded hash, not whether the two trees now agree) but proceeds and re-records the lock. Say which copy you touched when reporting the fix.
- **Before back-porting a fix into the clone, read the whole diff — the drift is usually not all yours.** An
  installed copy touched by earlier sessions carries edits you never made; back-porting only your own hunk and
  then running a forced update deletes theirs. `diff -r <clone>/skills/<name> <profile>/skills/<category>/<name>`
  is the list of what must land in the clone, byte-identically, before any `--force`.
- **A list-valued option has a separator, and a wrong separator is often accepted silently.** `git annex
  unused --used-refspec '+refs/heads/*:-refs/remotes/*'` takes colon-separated `+`/`-` elements (the default
  is equivalent to `+refs/*:+HEAD`); written space-separated, the whole string becomes one literal ref, the
  glob never matches, the used-set empties — and the command then reports content that is still referenced
  from another branch as orphaned (measured: 1 entry expected, 2 reported, the extra one a key in live use).
  No validator fires. For any option taking a list, expression or refspec, run the wrong-separator and
  wrong-quoting variant too and state what it silently means.

## Does command A already do what command B does?
Answer by naming the **ref/artifact set each command moves or covers**, then the one thing each misses — the
overlap is almost always partial, so a bare yes/no gets corrected next turn. Measure it in a scratch copy with
a throwaway remote; do not infer it from the subcommand names.
- `git annex sync <remote>` first commits, then runs the equivalent of `git-annex pull` followed by
  `git-annex push`, and the push half is documented as "making sure that the git-annex branch is pushed to the
  remote". So "do I still need `git push` after sync?" is **no** for the current branch and the annex state —
  while branches and tags you created with plain `git branch` / `git tag` are **not** part of it (measured: two
  sync runs, the remote's `ls-remote` still never gains them). Give both halves.
- Read the ref list off the real repo instead of the docs: `git ls-remote <remote>` for what the far side has,
  `git for-each-ref` for yours, `git merge-base --is-ancestor A B` for which direction a merge would go. A
  question shaped "the two refs are not the same commit, do I need to fetch?" is answered by naming which ref is
  ahead and what the missing information costs — not by agreeing that something is broken.
- **Decide "by design" vs "a real gap" before proposing a repair.** Some labels, refs and files are *expected*
  to differ because each side commits its own (a per-repo metadata branch, per-host state, sync journals);
  others differ because a transfer never happened. Separate them by mechanism, then verify at content level —
  ancestry for direction, a read of the actual log/record for the disagreement — because comparing hashes cannot
  distinguish the two. Say which half is actionable: the by-design half is usually one `merge`/`push` from being
  merely *tidy*, and calling it damage is what sends the user to `--force`.

## "Is X the default?" — the installed revision's man page, not the tutorial
Walkthrough/tutorial pages state behavior flatly and lag the command's own man page; a flat sentence and a
precise one can both be "in the docs" and disagree. Source the answer from `--help` / the man page of the
installed version, and carry the condition the tutorial dropped.
- **A one-sided option pair in `--help` is the tell that the default is configurable.** `git annex sync
  --help` lists both `--content` and `-g,--no-content`; the man page then says the no-content default is a
  *special case* — it holds for remotes that have no preferred content configured, and `--content`,
  `--content-of` or the `annex.synccontent` config cancels it. The flat tutorial sentence is right about
  the common case and wrong as a rule. Before generalizing any default, read the flags' help for **both**
  directions and name the config that flips it.
- Answer with the condition plus the override, never a bare yes/no: "does not transfer contents by default"
  without "unless the remote has preferred content configured" is the answer that gets corrected next turn.
- If the flat wording is what a skill you consulted quotes, say so in the answer and fix the quote where it
  lives (the clone of its source repo, per the section above) — keep the looser tutorial quote only *beside*
  the man-page quote, with the difference named, so the next session sees why the flat version is not the rule.

## "Can this be changed later?" questions
Answer with the tool's own verb, a throwaway probe, and the place the value is persisted — the persistence decides what else moves.
1. Start from the manual's SYNOPSIS, which names the exact subcommand (`git-annex describe - change description of a repository`), instead of inferring whether a setting is mutable.
2. Prove it in a scratch repo, never the user's: `git annex describe here "<new>"` → `describe here ok`, and the new name then shows in `git annex whereis` / `git annex info`.
3. Report where it is stored: the description lives in the git-annex branch's `uuid.log` (`git show git-annex:uuid.log` → `<uuid> <description> timestamp=…`), keyed by the repo UUID — so a rename touches no key, content or commit, and travels with that branch on sync.
4. Check the read path before promising one: `git annex describe` takes 2 arguments and errors on 0 or 1 (`Specify a repository and a description.`), so the current value is read via `git annex info` or the `uuid.log` blob. The same subcommand renames other repos' labels when given a remote name or uuid.
- Same shape for any unmutable-sounding setting: if the value is written into a log/branch, say so and give the command that re-reads it; if the value is fixed at creation (repo version, hash layout), say that in the same breath and name what would have to be rebuilt.

## Verifying interactive behavior
`scripts/pty_capture.py` forks a pty, sets the window size, replays a labeled keystroke script, prints the drawn screen after each step, and `repr()`s the file the program wrote. Use it only for behavior that cannot be read off the docs: save/exit prompts, what a key really does, wrap/justify side effects.
- Enter is `\r` (CR); `\n` (0x0A) is `^J`, which in pico-class editors means **Justify paragraph** — sending LF where you meant Enter silently reflows the file. Encode LF vs CR deliberately in every key script.
- Send keys with a delay and drain the pty between writes: the evidence is the transient message line, which one read at the end never sees.
- End each scenario with save + exit, then read the file with `repr()` so merged lines / added blank lines show up instead of being inferred.
- Drive TUIs with this harness, not `script -q /dev/null <cmd>` plus piped stdin: `script` blocks waiting on the pty, so the call only produces a timeout. If a probe hangs anyway, kill it instead of raising the timeout.
- Reconstruct the screen from `ESC[r;cH` addressing (the script's `--grid` mode) when the strings you need sit on the status line (row 1) or the message line (third from bottom).

## Installed GUI app: where is that setting?
The GUI equivalent of local ground truth, same rule as above: read the copy installed on this machine, and answer with the menu path as it appears in the user's UI language.
1. Config file first — it names the key behind the setting and shows the current value. Qt apps on macOS keep it at `~/.config/<app>/<app>.ini`. A value that changes between two reads is the app rewriting it while the user clicks around, not a broken read.
2. The app's own release notes (`Contents/Resources/WhatsNew.txt` and friends) settle version questions in one read: which release added or MOVED the feature, and a link to the vendor's issue/forum thread. A setting the user "cannot find" is often one that moved pages in a recent version.
3. `strings -a <binary> | grep -nE 'cb[A-Z]|<Section>/<key>|^Theme$'` gives widget names and ini keys. Widget names cluster per dialog class, and the ini keys printed beside a `DlgSettings<Page>Class` say which settings page owns the key — that is how you prove a setting lives on page X in THIS version.
4. Get the literal labels from the app's translations (`Contents/Resources/language/*.qm`): source string ↔ local label ↔ owning dialog context are adjacent, so you can quote the exact item the user will see. Never hand back the English path when the app runs in another language (read `language=` in the config to know which one). Byte-level recipe + worked example: `references/installed-gui-app-settings.md`.
5. Name the trap that makes it unfindable — typically a menu entry that exists in only one app mode (present in browser mode, absent while a single image is open). That mechanism, not the location alone, is what the user needs.
6. Shared-vendor binaries: one file often carries a sibling product's dialogs (its logo resource, "Add ... to <sibling>" strings). Cross-check any item list against this app's own release notes/forum before teaching it — a combo list lifted from the sibling's settings page is the easy wrong answer.
7. If the complaint word is ambiguous, read the config's color keys (`backColor`, `prevBackColor`, `thumbBackColor`, `fullBackColor`, …) and say which surface is actually dark, then name the page that owns that key. Do not hand back a menu of alternatives.
Prefer this static route over driving the user's live desktop (screenshots, menu clicks): the app in question is usually open and mid-edit by the person asking.

## macOS System Settings: 面板身份 → 深链 → 让用户点
System Settings 的每一页都是 ExtensionKit 扩展（不是普通 app），所以上面那套"读配置文件 / 读翻译"不适用。
1. **定面板**：`defaults domains | tr ',' '\n' | grep -iE 'Settings\.extension'` —— 域的名字就是面板 bundle id（`com.apple.Passwords-Settings.extension`）；`ls /System/Library/ExtensionKit/Extensions/` + 各自 `Contents/Info.plist` 的 `CFBundleDisplayName` 是侧边栏里显示的页名。系统自带 app 的面板不在这个目录里，而在 `*.appexlist` 指向的 `/System/Cryptexes/...`（运行时路径 `/System/Volumes/Preboot/Cryptexes/...`）：`find` 不到 Passwords 面板是正常的，去 `.appexlist` 里找。
2. **打开它**：`open "x-apple.systempreferences:<pane-bundle-id>"`，再用 `pgrep -lf LaunchArguments` 解出 base64 里的 `{"serviceName":"<bundle id>","type":2,…}` 确认落在哪一页（`type:2` = 设置页，`type:1` = 小组件）。
3. **给用户定位词**：面板自己的 `<appex>/Contents/Resources/en.lproj/*.searchTerms` 里有它在系统设置搜索框下的标题与关键词（例：`AutoFill & Passwords`，index `autofill / password manager`）。教他"在系统设置里搜这个词"比猜侧边栏层级可靠——官方的层级描述会随版本搬。
4. **判据取 Apple 官方 guide 原文**（`support.apple.com/guide/safari/autofill-ibrwa005`、`support.apple.com/guide/passwords/*`）；官方页常按 iOS 写路径（"Settings > General > AutoFill & Passwords"），macOS 上的位置必须本机核对后再报。

5. **行标签/选项名藏在共享 UI framework 的 lproj 里**，不在面板 appex 里：面板自己的 `Localizable.strings` 往往只有页面标题，整套开关名/下拉选项名/说明灰字在 `/System/Cryptexes/OS/System/Library/PrivateFrameworks/<UIFramework>.framework/Versions/A/Resources/<lang>.lproj/Localizable.strings`（Passwords 面板→`PasswordManagerUI`）。`plutil -convert json -o -` 之后按关键词 grep，一次拿到全部标签与中文译名。
6. **读得到标签，读不到语义——别用标签或第三方博客断言后果**。cryptex 里的框架只剩 `Resources/` + `_CodeSignature/`（Mach-O 在 dyld shared cache 里，磁盘上没有），`strings`/grep 拿不到控制流。能定的只有「选项集合」：全系统文案里若根本没有"不保存/不再保存"这类取值，那个下拉就**不可能**表示"不保存"；剩下的含义必须让用户在真实界面里试一次，且**测试要设计成"状态会变"**（App 里有没有多出一条记录），不要设计成"说明文字会不会变"——设置页灰字常常是静态的（实测切换选项后一字未变）。
7. **界面 → 偏好键**（值得挖）：让用户在指的那个控件上切一下，再 `find ~/Library -mmin -20 -type f -name '*.plist' | grep -iE '<关键词>'` + `plutil -p <那个 plist>` 前后对比，即可拿到域/键名/值（实测：`com.apple.Passwords` 的 `PasswordSavingBehavior`）。读 plist 文件本身，`defaults read` 可能滞后。此映射只能证明"这条设置真实存在"，不能解释语义。
8. **回答形状**：一次只给用户问的那 1–2 个控件，每个一句话说清它管**读（填充）还是写（保存）**；并列三四个面板 + 机制解释会被回「你讲了一大堆，我也没搞懂」。他已经截图给你看的面板，就只讲**这个面板里有什么、没有什么**（"你要的控件不在这里"要点名）。自己判断错了，第一句先认「我说反了」，再给修正结论。

坑：`osascript` 的 System Events 没有辅助功能授权——`keystroke` 报 `1002`，读窗口 `position/size` 报 `-1719`，所以**不要设计"脚本点开关 / 读窗口标签"的流程**；深链打开后让用户点最后一下并在回答里说明。深链会在用户屏幕上真的开一个窗口：要主动讲，并且**不要打开会列出他密码/密钥的面板再截图**。二进制 `.strings`/`.lproj` 用 `strings`/`grep` 找不到文本，要 `plutil -convert json -o - <file>`。

## Per-tool depth
- macOS System Settings 面板（扩展剖析、深链、searchTerms、osascript/TCC 权限边界、回答形状）：`references/macos-system-settings-panes.md`.
- Installed GUI app settings (config keys, release notes, binary strings, Qt translations): `references/installed-gui-app-settings.md`.
- pico-class editors (PICO 5.09 / Alpine composer): `references/pico-class-editors.md` — verified key table, full option list, exact prompt strings, measured wrap/justify behavior, `$EDITOR` escape route.
- git-annex layout and storage-model answers (one directory vs `--separate-git-dir`, locked/unlocked copy counts, why `git status` goes clean after an add, splitting the rule for app-managed trees, what dot-dirs cost and cannot reclaim, moving paths with `mv` vs `git mv`, restoring a deleted path / reading an old version, the `git-annex` branch vs your work branches and what
  `sync`/`push` each move): `references/git-annex-model-and-layout.md`.
