---
name: manage-hermes-node
description: Use when a Node/npm CLI package behaves differently inside Hermes than in the user's own terminal — a global CLI that works in a Hermes terminal but is missing in iTerm, or the reverse, an `npm install -g` that lands somewhere unexpected, `node`/`npm`/`npx` resolving to a version nobody chose, an EBADENGINE from `npm ci`, or any question about which Node Hermes uses and where its global packages go. Explains the two independent Node environments (Hermes-managed `~/.hermes/node/` versus system/Homebrew `/opt/homebrew/bin`), drives the ordered "which npm am I actually using, and where will the package go" procedure, and names the destructive operations never to run.
---

# Manage Hermes Node and npm

Hermes ships (manages) its own Node.js runtime at `~/.hermes/node/`, and that is **a second,
independent environment** from the user's Homebrew node at `/opt/homebrew/bin/node`. Nothing
synchronises them. Which `npm` a given shell invokes decides where a global package lands and which
terminals can see it — and that one question answers nearly every complaint this skill exists for.

> Note verified **2026-08-18** against the source at `~/.hermes/hermes-agent/`, machine macOS Apple
> Silicon. Re-checked live on **2026-09-30**; anything marked *measured* below is real output from
> that date, not a restatement of the note.

## The two environments

| | Hermes-managed | system / Homebrew |
|---|---|---|
| root | `~/.hermes/node/` | `/opt/homebrew/bin/node` → `/opt/homebrew/Cellar/node/23.7.0/bin/node` |
| `node` | 22.22.3 | 23.7.0 |
| `npm` | 10.9.8 | 10.9.2 |
| global binaries land in | `~/.hermes/node/bin` | `/opt/homebrew/bin` |
| on the user's PATH (`~/.zshrc`)? | only through the `~/.local/bin` links | yes, directly |

All six values *measured 2026-09-30* (`ls -l /opt/homebrew/bin/node`,
`zsh -lic 'node --version; npm --version'`). The managed pair is what Hermes' own runtime and its
`terminal` tool use; the Homebrew pair is what the user's own iTerm uses.

## Step 1 — which npm is this shell actually using?

Run these in the terminal that *has* the problem, never in the abstract:

```bash
which -a node npm npx     # first hit wins — that is the one in effect
npm config get prefix     # where the next `npm install -g` would write
```

*Measured 2026-09-30*, same machine, two shells:

```bash
# the Hermes terminal tool (Desktop-injected PATH)
$ which -a node | head -1
/Users/maxim/.hermes/node/bin/node
$ npm --version ; npm config get prefix
10.9.8
/Users/maxim/.hermes/node

# the user's own login shell (zsh -lic)
$ node --version ; npm --version ; npm config get prefix
v22.22.3        # via ~/.local/bin/node → ~/.hermes/node/bin/node
10.9.2          # /opt/homebrew/bin/npm
/opt/homebrew
```

Two shells, two different npm, one machine. That is why "works for me, not for you" is a real answer
here rather than a dodge — and why the first step is always to identify the shell.

## Step 2 — map the first hit onto where the package will land

The note's comparison table, verbatim:

| 用哪个 npm | 全局包装到 | iTerm 可见? | Hermes terminal 可见? |
|---|---|---|---|
| Homebrew npm（`/opt/homebrew/bin/npm`） | `/opt/homebrew/bin` | ✅ | ✅ |
| Hermes managed npm（默认） | `~/.hermes/node/bin` | ❌ | ✅ |
| Hermes managed npm（重定向后） | `~/.local/bin` | ✅（.zshrc 有） | ❌ |

Read the third row as **the design, not the current state**. The redirect would be written by
`~/.hermes/node/etc/npmrc` holding `prefix=~/.local` — and *measured 2026-09-30* that file still does
not exist:

```bash
$ ls -la ~/.hermes/node/etc
ls: /Users/maxim/.hermes/node/etc: No such file or directory
```

So a `npm install -g` run through the managed npm lands in `~/.hermes/node/bin`, a directory the
user's own shell never sees. The note's worked example — the `arkcli` install — is still sitting
there:

```bash
$ ls -l ~/.hermes/node/bin
lrwxr-xr-x  arkcli -> ../lib/node_modules/@volcengine/ark-cli/scripts/run.js
```

## Step 3 — the answer for each case

| What the user actually wants | The answer |
|---|---|
| a global CLI visible in **both** environments | install it with the **Homebrew** npm (`/opt/homebrew/bin/npm`) — the note's design first choice |
| Hermes' own runtime left untouched | leave the managed `~/.hermes/node` scheme alone; the two environments never interact |
| to know why a CLI works in Hermes but not in iTerm | the managed npm installed it into `~/.hermes/node/bin`, which iTerm cannot see (row 2) |
| to know why a CLI exists in iTerm but Hermes' `npx` re-downloads it | the Hermes PATH puts managed `node`/`npm` first, so every `npx` re-resolves inside Hermes |
| to reach a managed-npm global tool from iTerm | the note's recovery is the `etc/npmrc` redirect — **state change, never part of a diagnostic** |
| an `EBADENGINE` from `npm ci` | the Homebrew npm drifted into the excluded band of `engines.npm` (see the global-npm reference) |

## Version shading — same command, two versions

The Desktop runtime's PATH is built by `apps/desktop/electron/backend-env.ts` →
`buildDesktopBackendPath()`, in this order:

```
PATH = ~/.hermes/node/bin + ~/.hermes/node + venv/bin + 当前 PATH + /opt/homebrew/bin ...
```

→ **Desktop 后端（含 terminal 工具的 shell）里 `node`/`npm` 永远解析到托管版（v22.22.3）**，即使
Homebrew node 23.7.0 存在也被遮蔽。用户自己的 iTerm 终端则不受影响（不读这套 env）。

Re-measured 2026-09-30 — the `terminal` tool's first `which -a node` hit is still
`/Users/maxim/.hermes/node/bin/node`, so the shading consequence holds on this machine today.

The note's citations are older than the current checkout (`scripts/lib/node-bootstrap.sh` and the
repo-root `install.sh` are gone; `backend-env.ts` no longer exports `buildDesktopBackendPath`), yet
the observed outcome — managed node first in every Hermes-spawned shell — is unchanged. The bootstrap
reference records both the note's mechanism and the current source text.

## Do not do this

- **Never delete `~/.local/bin/cua-driver`, `~/.local/bin/hermes` or `~/.local/bin/hermes-acp`.** Those are
  the computer_use driver and the CLI entry points, not Node links. Verbatim from the note:
  ⚠️ **别删的链接**：`cua-driver`（Hermes computer_use 驱动）、`hermes`/`hermes-acp`（CLI 入口包装）
- **Never `rm -rf ~/.hermes/node`** — it is the live runtime, and Hermes rebuilds that whole tree on a
  managed-Node upgrade anyway (which is precisely why the redirect design exists).
- **Do not run the `mkdir -p ~/.hermes/node/etc && echo 'prefix=…' > …/npmrc` recovery while
  diagnosing** — it silently relocates where the user's future global packages land.
- **Do not `brew upgrade node` assuming Hermes follows** — the managed runtime is versioned separately,
  and an upgrade can empty the global packages under `~/.hermes/node/bin`.
- **Do not `rm ~/.local/bin/node` (or `npx`) to "clean up"** before reading the deletion-effect table —
  that is how this machine's iTerm-visible `npm` silently became Homebrew's.

## Read next

- `references/manage-hermes-node-bootstrap.md` — runtime selection at install/repair time (5 levels,
  first hit wins), the Desktop PATH injection and its version-shading consequence, the
  `~/.hermes/node/etc/npmrc` prefix-redirect design intent, the measured fact that `etc/` is absent,
  the re-enable snippet, and the node-26 wipe warning.
- `references/manage-hermes-node-global-npm.md` — the two-prefix table, the four numbered risks of
  using the Homebrew npm (including the `engines.npm` exclusion band), the practical recommendations,
  the `~/.local/bin` symlink mechanics with the measured before/after deletion table, and the
  do-not-delete list.

## Skill Structure

<!-- Generated by Scripts -->

```
manage-hermes-node/
├── SKILL.md  (159 lines)
├── references/
│   ├── manage-hermes-node-bootstrap.md  (130 lines)
│   └── manage-hermes-node-global-npm.md  (142 lines)
└── scripts/
    └── auto-generate-skill-structure.py  (142 lines)
```

<!-- Generated by Scripts -->

