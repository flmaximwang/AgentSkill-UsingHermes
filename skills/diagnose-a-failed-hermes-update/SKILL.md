---
name: diagnose-a-failed-hermes-update
description: "当 Hermes 更新失败（Desktop 的 Update / 退出码 2 / 更新完没变化）要排查时用：先钉住失败在哪一层、只读探针钉现场，最后只给一条能跑通的命令。不负责「上游修了没」（verify-whether-an-upstream-fix-landed），也不负责 Desktop 的插件面板坏了（maintain-hermes-desktop-app）。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, update, troubleshooting, forensics, macos]
    related_skills: [maintain-hermes-desktop-app, verify-whether-an-upstream-fix-landed, maintain-hermes-gateway]
---

# 排查一次失败的 Hermes 更新

Desktop 点 Update 报错、hand-off 日志里 `exit code: 2`、「更新跑完没变化」——都先按这套只读判据把状态钉死，
再谈原因；最后只给一条能跑通的命令。

## When to Use（触发与边界）

- 「Hermes 更新失败 / Desktop 更新报错」，或用户直接给出 `~/.hermes/logs/desktop-update-handoff.log`。
- 日志里出现 `Another Hermes update is already running (… process N)`、`hermes update exit code: 2`、
  `Update incomplete — gateway auto-restart failed`。
- 「点了更新没反应」「跑完了但还是老版本」。

不适用（各走各的兄弟技能）：

- 问「上游最新提交有没有修掉这个问题」→ `verify-whether-an-upstream-fix-landed`（rev-list 判祖先、
  符号 grep、部分克隆上的取数顺序都在那里，直接照抄）。
- Desktop 的插件、面板、连线坏了（`Plugin not found` 404、pane 空转）→ `maintain-hermes-desktop-app`。
- 更新本身跑完了、是平台侧的 bot 连不上/收不到消息 → `maintain-hermes-gateway`。

## 流程

### Step 1 · 钉住失败发生在哪一层

Desktop 的 Update 按钮自己不更新：它从 checkout 里起 `scripts/desktop-update/posix.sh`，这个脚本等 App
退出、跑 `hermes update`、再换 bundle 并重开 App。它每跑一次就往
`$HERMES_HOME/logs/desktop-update-handoff.log` 追加一段，段末是 `hermes update exit code: N`；用户在对话框
里看到的是 `$HERMES_HOME/.hermes-update-result.json`。

先读三样，再谈原因：

1. 日志**最后一段**（`hand-off start:` 到 `exit code:`），以及 hand-off 自己打的行：
   `adopted/claimed update marker`、`update marker names its custodian pid …`、
   `update marker names … as its delegate`、`running: … hermes update …`、`retrying once`。它们说明它
   走到了哪一步。
2. 现在到底有没有更新在跑：只读探针（Step 2）。
3. `$HERMES_HOME/logs/update_receipts/latest.json` 的 `outcome` / `exit_code` / `stages`。hand-off 连
   `hermes update` 都没起起来时，这里不会出现新记录 —— 这本身就是一条判据。

### Step 2 · 只读探针：marker 与 checkout 锁

```bash
PYTHONPATH=<checkout> <checkout>/venv/bin/python - <<'PY'
from hermes_cli.update_lock import (read_live_update, checkout_lock_held,
                                    update_marker_path, checkout_lock_path)
print("marker:", update_marker_path(), update_marker_path().exists())
print("live update:", read_live_update())
print("checkout lock:", checkout_lock_path(), "held:", checkout_lock_held())
PY
```

两个「看起来是状态、其实不是」的东西，最容易把人带偏：

- `<marker>.lock`（marker 的互斥 sidecar）只创建一次、**永不删除**，它在不在跟有没有更新跑无关。
- `<git common dir>/hermes-update.lock` 里的 pid/ct 是**上一个持有者**留下的字节，它退出后照样留着。
  判活在不在要看 flock（`checkout_lock_held()` / `flock -n`），**不要读文件内容当证据**。

marker 不存在 + `read_live_update()` 为 None + `checkout_lock_held()` 为 False ⇒ 现场干净，下一次尝试能跑
通。也别拿 `checkout_lock_held()` 反复轮询来「盯」锁：每次调用会真的去抢一次锁，和正在启动的更新互抢。

### Step 3 · `exit code: 2`：真并发，还是 hand-off 拒绝了自己

日志里的 `hermes update exit code: N` 是**子进程**的码：`0` 已提交；`2` 被拒；`130` 在提交点之后被打断；
其它非零是真失败，原因在它上面那段输出里。`2` 是最常见的报法，而它**多数不是**真有另一个更新：

1. 从 `… already running (… process <pid>)` 里取出 pid。
2. 它是 update 子进程的活祖先，或等于 `HERMES_UPDATE_HANDOFF_PID` ⇒ 真有外部更新占着，等它。
3. 它是**兄弟进程**（hand-off 自己 fork 的 marker custodian 就是个 fork，表现为同一个 hand-off pid 的
   子进程）⇒ 子进程认不出「这是我自己家的更新」。这是 marker 协议的缺陷，不是卡住的锁：**再点一次
   Update 会同样失败**，别跟用户说「等等再试」。

要查的失败类别是**两边写法不一致的身份**：一边写身份行（shell 的 `marker.sh::proc_ct`，macOS 走
`ps -o lstart` 截到整秒），另一边判它（`update_lock.py::_incarnation`：认自己的 pid 只给 5 ms，认别人给
2 s）。整秒记录与毫秒真值差 0–1 s，5 ms 的判据永远不成立，于是进程把自己的 `delegate:` 行读成陌生人。
判据要拿**真代码实测**，A/B 配方见 references。

### Step 4 · 能不能现在跑通、要不要跑

终端里起的 `hermes update` 自己占 marker、完全不经过 hand-off，所以 hand-off 那条腿坏了它照样能跑：先
⌘Q 退出 Desktop，再 `hermes update --yes --gateway --branch main`。

**跑之前先问。** 它会重启 gateway —— 也就是你正在汇报的这个会话所在的 bot —— 自己的回复可能中途死掉。
诊断只读，这一步是改动：要么交回用户执行，要么先说明再后台跑。跑之前先核「上游是否已修」
（`verify-whether-an-upstream-fix-landed`），别承诺一个升不上去的升级。

## 实测基线（2026-10-08 · macOS 26.6.2 · checkout `05eecbcd97` = v0.21.5 · default profile）

触发这次排查的实例，三个数放在一起就是判据：

- `~/.hermes/logs/desktop-update-handoff.log` 第 854–865 行：marker 第 1 行是 hand-off fork 的 custodian
  `pid 17798`，delegate 行写 `pid 18077 ct:1791455308.000`（**整秒**），而 18077 的真实创建时间是
  `1791455308.181`（psutil 实测）⇒ `delegate_live()` 判 False ⇒ `_is_partner(17798)` False ⇒ exit 2。
- A/B 实测（真代码 + 临时 marker，同一棵进程树）：delegate 的 ct 用 shell `proc_ct` 写（整秒）→
  `acquire()` False、holder 报成 **owner**（那个兄弟进程）；用 `_identity_line(pid)` 写（3 位小数）→
  `acquire()` True。唯一变量是精度 ⇒ 它是判据，不是故事。
- 上游修复 `a28a5d03a9`（2026-10-08，"a whole-second marker creation time in our own second is still us"）
  给 `_incarnation` 加了整秒容差；该实例的 HEAD `05eecbcd97` **不含**它 ⇒ 更新一次即可拿到。

**这是快照不是常量**：日志行号、pid、ct、HEAD 每次都会变；复查时按 Step 1–3 重测，别照抄上面的数字。

## 汇报形状（这个用户）

1. 一句话结论放最前：偶发还是确定性失败、失败在哪一层。
2. 根因链每条挂一行证据（日志行号 / 命令输出），并说明排除了什么。
3. 给**一条**能跑通的命令 + 它的代价（几分钟、会断线）。
4. 只提一个问题（跑不跑），不一次抛多个待决项。
5. 没实测的推断标明是推断；不要用自洽的推断链覆盖用户亲眼所见的现象。

## 检查点

| 触发 | 动作 |
|---|---|
| 准备动手跑 `hermes update` 修它 | STOP 先问：它会重启 gateway（正是你汇报所在的 bot），回复可能中途死掉 |
| 想用 `checkout_lock_held()` 轮询「盯」锁 | STOP：它每次真抢一次锁，和正在启动的更新互抢 |
| 想断言「更新一下就好」 | 先核上游是否已修（`verify-whether-an-upstream-fix-landed`）；没修就别这么承诺 |
| 想给本地 checkout 打补丁解开 Desktop 那条腿 | 可行但说清代价（工作区留未提交改动，下次更新会 stash 走）；优先走终端更新 |

## 黑名单（每条都在实况里踩过）

- 别拿 `<git common dir>/hermes-update.lock` 的**字节**当「有更新在跑」的证据：那是上一个持有者的身份，
  退出后照样留着。
- 别把 `exit code: 2` 一律读成「真有并发在跑」，那会让你给出「等等再试」这种错建议。
- 别读「marker 文件在不在」下结论；缺了 marker 也可能是活得正欢的更新（它可能先占锁后发布，或已经收尾）。
- 别用自洽的推断链覆盖用户亲眼所见的现象；不确定就去看现场。
- 别把「诊断」写成一串并行任务：这个用户的形状是结论 + 一条命令 + 一个问题。

## Support files

- `references/desktop-update-handoff-failure-modes.md` — 状态都在哪、两层退出码对照、只读探针、用真代码
  复现 marker 判定的 A/B 配方、macOS 上给命令设硬上限的写法、修完之后怎么核。
- 上游是否已修：`verify-whether-an-upstream-fix-landed`（另一个 skill，只读核验）。

## Skill Structure

<!-- Generated by Scripts -->

```
diagnose-a-failed-hermes-update/
├── SKILL.md  (157 lines)
├── test-prompts.json  (27 lines)
├── test-results.md  (55 lines)
└── references/
    └── desktop-update-handoff-failure-modes.md  (122 lines)
```

<!-- Generated by Scripts -->
