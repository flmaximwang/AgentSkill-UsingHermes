# Global npm installs — the two prefixes, and what deleting links costs

Read this when the question is "where did my global CLI go?" or "can I just install it with the
`npm` I have?". The first half is the map; the second half is the measured cost of editing the
`~/.local/bin` links.

## The two prefixes

The note's comparison table, verbatim:

| 用哪个 npm | 全局包装到 | iTerm 可见? | Hermes terminal 可见? |
|---|---|---|---|
| Homebrew npm（`/opt/homebrew/bin/npm`） | `/opt/homebrew/bin` | ✅ | ✅ |
| Hermes managed npm（默认） | `~/.hermes/node/bin` | ❌ | ✅ |
| Hermes managed npm（重定向后） | `~/.local/bin` | ✅（.zshrc 有） | ❌ |

Row 3 requires the `~/.hermes/node/etc/npmrc` redirect, which is **not active on this machine**
(*measured 2026-09-30* — see the bootstrap reference). So in practice only rows 1 and 2 occur here.

## What using the Homebrew npm costs

**结论：可以跑，且是设计首选路径**。Homebrew node v23.7.0 ≥ 仓库 `engines.node: >=22.22.0`。风险：

1. **版本不受控**：`brew upgrade node` 随时升大版本；Hermes 只在自己固定的版本上测试
2. **npm 版本带外**：仓库 `engines.npm` 为 `"<11.10.0 || >=11.17.0"`（排除 11.10.0–11.16.x）。本机
   Homebrew npm 10.9.2 当前在范围内，但 brew 升级后可能落入排除带 → 配 `engine-strict` 的 `npm ci` 会报
   EBADENGINE
3. **全局包生命周期绑定 brew**：`brew uninstall`/relink node 会连带破坏全局 CLI
4. Hermes 自己的操作传显式 `--prefix`，不受影响（install.sh 注释）

**Re-verified 2026-09-30** against the current `package.json:64-66`:

```json
"engines": {
  "node": "^22.22.0 || ^24.11.0 || >=26.0.0",
  "npm": "<11.10.0 || >=11.17.0"
}
```

The `npm` band is byte-for-byte the note's exclusion range, so risk 2 is a standing property of the
repo, not a stale figure. Measured Homebrew npm `10.9.2` sits inside it today; the managed npm
(`10.9.8`) also sits inside it. This is the failure to name when a user reports an `EBADENGINE` after
a `brew upgrade`.

## Practical recommendations

The note, verbatim:

- **个人日常全局 CLI** → 用 Homebrew npm 装（`/opt/homebrew/bin` 两个环境都可见）
- **Hermes 运行时的 node** → 保持托管版不动，两者互不干扰
- **恢复重定向设计**（让 managed npm 装到可见位置）:
  ```bash
  mkdir -p ~/.hermes/node/etc && echo 'prefix=/Users/maxim/.local' > ~/.hermes/node/etc/npmrc
  ```
- **警告**：未来 Hermes 升级托管 node（install.sh 已固定 `NODE_VERSION="26"`，当前是 22）时，若重定向未
  生效，`~/.hermes/node/bin` 下所有全局包会被清空

## The `~/.local/bin` links — mechanism

`~/.local/bin` 里的 `node`/`npm`/`npx` 是安装器创建的**符号链接**（→ `~/.hermes/node/bin/...`），机制见
`_nb_get_link_dir()`（macOS 非 root → `$HOME/.local/bin`）。install.sh 同时往 `.zshrc` 写入
`export PATH="$HOME/.local/bin:$PATH"`，让用户 shell 能访问托管 node。

The `.zshrc` half is re-verified 2026-09-30 — the line is at `~/.zshrc:150`, and line 158 appends the
same directory a second time:

```bash
# Hermes Agent — ensure ~/.local/bin is on PATH
export PATH="$HOME/.local/bin:$PATH"
```

Current contents of the directory (*measured 2026-09-30*, `ls -l ~/.local/bin`) — note that the
deletion experiment below has since been extended:

```
node       -> /Users/maxim/.hermes/node/bin/node
npm-hermes -> /Users/maxim/.hermes/node/bin/npm
npx-hermes -> /Users/maxim/.hermes/node/bin/npx
```

There is no `npm` and no `npx` link any more; the user renamed its surviving copies `npm-hermes` /
`npx-hermes`. The `node` link is still there, which is exactly the note's "仍托管" row.

## Why deleting `~/.local/bin/npm` does not touch Hermes itself

The note's four reasons, verbatim:

1. Desktop 运行时 PATH 由 `backend-env.ts` 构造，**不含 `~/.local/bin`** → Hermes 进程里的 node/npm 从不
   经过该目录
2. Python 侧（`hermes_constants.py`）按绝对路径解析 `$HERMES_HOME/node/bin/{node,npm,npx}`，不走 PATH 搜索
3. 删的只是链接；托管树本体 `~/.hermes/node/bin/npm` 完好
4. Hermes 自己的 npm 操作显式调用托管 npm（带 `--prefix`），不依赖用户 PATH

Reason 1 needs one caveat on this machine: *measured 2026-09-30*, the `terminal` tool's PATH **does**
contain `~/.local/bin`, but only **after** the managed entries
(`~/.hermes/node/bin` → `~/.hermes/tools/node-26.7.0-darwin-arm64/bin` → `~/.local/bin` →
`/opt/homebrew/bin`). So Hermes is protected by ordering plus reasons 2–4, not by the directory's
absence. The conclusion is unchanged; the mechanism is "earlier wins", and a user who reorders their
PATH can move that boundary.

## After deletion — the measured effect on this machine

The note's measured table, verbatim:

| 命令（iTerm） | 删除前 | 删除后 |
|---|---|---|
| `npm` | `~/.local/bin/npm` → 托管 npm | 回落 `/opt/homebrew/bin/npm`（10.9.2） |
| `node` | `~/.local/bin/node` → 托管 22.22.3 | **仍**托管 22.22.3（链接还在） |
| 全局包装到 | `~/.hermes/node/bin`（iTerm 不可见） | `/opt/homebrew/bin`（两环境可见）✅ |

**Re-verified 2026-09-30** in the user's real login shell (`zsh -lic`), which reproduces the
"删除后" column exactly:

```bash
$ node --version ; npm --version ; npm config get prefix ; npm root -g
v22.22.3
10.9.2
/opt/homebrew
/opt/homebrew/lib/node_modules
```

→ node 22.22.3 + npm 10.9.2 混搭完全兼容；若想彻底统一 Homebrew 一套，删掉剩余链接：

```bash
rm ~/.local/bin/node ~/.local/bin/npx
```

That last command is the user's decision to make, explicitly — it is the point at which iTerm stops
seeing the managed node entirely. Note it also becomes a no-op for `npx` on the current machine, since
that link is already gone.

## Do not delete these

⚠️ **别删的链接**：`cua-driver`（Hermes computer_use 驱动）、`hermes`/`hermes-acp`（CLI 入口包装）

They sit in the same directory and look like the same kind of object, but they are not Node links —
`cua-driver` points into `/Applications/CuaDriver.app`, and `hermes` / `hermes-acp` are the CLI entry
wrappers (*measured 2026-09-30* in `ls -l ~/.local/bin`). Removing them breaks computer_use and the
command the user types to start Hermes.

If the goal is instead "let the managed npm install somewhere iTerm can see", use the redirect in the
bootstrap reference — do not go on deleting links.
