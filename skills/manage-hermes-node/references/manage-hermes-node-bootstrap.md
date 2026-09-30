# How Hermes picks its Node, injects PATH, and redirects the npm prefix

This is the install/repair-time machinery behind the two-environment model in `SKILL.md`. Read it when
the question is "which node does Hermes use, and why is the Homebrew one ignored?" rather than "where
did my package go?" (that is the global-npm reference).

## 1. Node selection order — first hit wins

Policy as defined in the header comment of `scripts/lib/node-bootstrap.sh` (note, 2026-08-18):

1. PATH 上**已有的现代 node**（`>= HERMES_NODE_MIN_VERSION`，默认 20）
2. `~/.hermes/node/`（之前 Hermes 托管安装的）
3. fnm / proto / nvm（尊重用户已有的版本管理器）
4. Termux `pkg` / macOS **Homebrew**
5. 兜底：从 nodejs.org 下载固定版本 tarball 解压到 `~/.hermes/node/`

→ **"用全局 npm" 在设计上就是第一优先**，只要版本达标。

The consequence to state out loud to a user: a Homebrew node that satisfies the minimum version is not
a workaround — it is *the intended first choice* at install time. The managed tree at level 2 is what
exists when no qualifying node was found on PATH, or when a previous Hermes run created it.

## 2. Desktop runtime PATH injection, and the shading it causes

`apps/desktop/electron/backend-env.ts` → `buildDesktopBackendPath()` (note, 2026-08-18):

```
PATH = ~/.hermes/node/bin + ~/.hermes/node + venv/bin + 当前 PATH + /opt/homebrew/bin ...
```

→ **Desktop 后端（含 terminal 工具的 shell）里 `node`/`npm` 永远解析到托管版（v22.22.3）**，即使
Homebrew node 23.7.0 存在也被遮蔽。用户自己的 iTerm 终端则不受影响（不读这套 env）。

That is the whole reason a version question has two answers on one machine: the shading happens at PATH
construction, not at any config switch, so there is nothing for the user to "turn off".

**Measured 2026-09-30** (read-only): the `terminal` tool's first `which -a node` hit is
`/Users/maxim/.hermes/node/bin/node`, and `npm --version` in that shell prints `10.9.8` while the login
shell prints `10.9.2`. The shading is live on this machine.

### What the current source looks like (2026-09-30)

The note's citations no longer resolve against the checkout, though the behaviour has not changed —
worth knowing before you go looking for `buildDesktopBackendPath`:

- `grep -n buildDesktopBackendPath apps/desktop/electron/backend-env.ts` → no match. The exported
  builder is now `buildDesktopBackendEnv`, which composes `POSIX_SANE_PATH_ENTRIES`
  (`/opt/homebrew/bin`, `/opt/homebrew/sbin`, `/usr/local/sbin`, `/usr/local/bin`, `/usr/sbin`,
  `/usr/bin`, `/sbin`, `/bin`) and scrubs `PYTHONPATH`/`PYTHONHOME`; its doc comment says *"Everything
  else — managed tool PATHs, browser paths, node — is composed in-process by pm when the backend spawns
  tools."*
- `scripts/lib/node-bootstrap.sh` does not exist in `~/.hermes/hermes-agent`; `scripts/install.sh`
  line 5 states heavy dependencies (tool binaries, browsers, node) are *"pm's job"*.
- `hermes_constants.py:489-493` `find_node_executable` — *"Read PM's selected Node/npm/npx, then a
  user-owned PATH toolchain. […] Discovery never installs, probes, repairs, or activates the retired
  ``HERMES_HOME/node`` layout."*
- `hermes_constants.py:428-431` `iter_hermes_node_dirs()` still yields `$HERMES_HOME/node/bin` (and
  `$HERMES_HOME/node` on Windows) — matching the note's absolute-path claim below.

So: cite the note's file names as the note's history, cite the lines above as the current text, and
never claim `buildDesktopBackendPath` exists in the checkout you are actually looking at.

## 3. The Python side resolves Node by absolute path, not by PATH search

The note's point (`hermes_constants.py`): Python code composes `$HERMES_HOME/node/bin/{node,npm,npx}`
directly instead of searching the user's PATH. Re-verified 2026-09-30 at `hermes_constants.py:428-431`
(`iter_hermes_node_dirs`) and `:435` (`{"npm": ["npm.cmd", "npm.exe", "npm"], "npx": […], "node":
["node.exe", "node"]}`), plus `:527-531` `with_hermes_node_path()` composing npm's environment without
provisioning. This is why deleting a `~/.local/bin` link can never break Hermes' own tooling — the
lookup never walks that directory.

## 4. npm prefix redirection — design intent

From `node-bootstrap.sh` → `_nb_configure_npm_prefix` + `install.sh` 注释 476-484 行 (note):

- managed npm 的全局前缀应通过 `~/.hermes/node/etc/npmrc` 写 `prefix=~/.local` 重定向到 `~/.local/bin`
  （该目录在用户 PATH 上）
- 原因：`~/.hermes/node` 不在用户 PATH 上，且**每次 Node 升级会被整个 `rm -rf` 删除重建**
- ⚠️ 本机现状（2026-08）：`~/.hermes/node/etc/` **不存在** → 重定向未生效 → `npm install -g` 落到
  `~/.hermes/node/bin`（例如 arkcli 事件）

The design is therefore *stateless protection*: because the redirect would put global binaries in a
directory Hermes never deletes, an upgrade of the managed runtime would not take the user's global CLIs
with it. Without the `npmrc`, they live inside the tree that gets wiped.

**Re-verified 2026-09-30** — the redirect is still not active on this machine:

```bash
$ ls -la ~/.hermes/node/etc
ls: /Users/maxim/.hermes/node/etc: No such file or directory
$ npm config get prefix          # in the Hermes terminal
/Users/maxim/.hermes/node
$ ls -l ~/.hermes/node/bin
arkcli -> ../lib/node_modules/@volcengine/ark-cli/scripts/run.js
lark-cli -> ../lib/node_modules/@larksuite/cli/scripts/run.js
mmdc    -> ../lib/node_modules/@mermaid-js/mermaid-cli/src/cli.js
```

Those three symlinks are the evidence: global packages installed through the managed npm, in a
directory the user's own shell does not search.

## 5. Re-enabling the redirect — and the warning that comes with it

The note's recovery snippet, verbatim:

```bash
mkdir -p ~/.hermes/node/etc && echo 'prefix=/Users/maxim/.local' > ~/.hermes/node/etc/npmrc
```

and the note's warning, verbatim:

- **警告**：未来 Hermes 升级托管 node（install.sh 已固定 `NODE_VERSION="26"`，当前是 22）时，若重定向未
  生效，`~/.hermes/node/bin` 下所有全局包会被清空

Treat the snippet as a **state change owned by the user**, not as a diagnostic step. It changes where
every future `npm install -g` through the managed npm writes, and it does not move the packages that
are already in `~/.hermes/node/bin`.

The node-26 part of that warning is no longer hypothetical on this machine: *measured 2026-09-30*,
`~/.hermes/tools/` now contains `node-26.7.0-darwin-arm64` and `npm-12.0.2-darwin-arm64`, while
`~/.hermes/node/bin/node` is still 22.22.3. Two Node trees, one redirect still missing — exactly the
configuration the note flags.

## Not carried over

- `scripts/lib/node-bootstrap.sh`, the repo-root `install.sh`, `_nb_configure_npm_prefix` and
  `_nb_get_link_dir` could not be re-opened: none of those paths exist in the current code root
  (checked 2026-09-30). Their citations here are the note's, preserved as history — not values this
  pass verified.
- The note's `install.sh:476-484` comment range is likewise unverifiable from the current checkout.
