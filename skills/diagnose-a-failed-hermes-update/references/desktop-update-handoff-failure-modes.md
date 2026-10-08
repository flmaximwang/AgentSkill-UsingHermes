# Desktop 更新 hand-off：状态、退出码、只读探针

## 状态都在哪

| 产物 | 路径 | 怎么读 |
|---|---|---|
| hand-off 日志 | `$HERMES_HOME/logs/desktop-update-handoff.log` | 每次尝试追加一段，段末是 `hermes update exit code: N` |
| 更新 marker | `$HERMES_HOME/.hermes-update-in-progress` | 活的声明。正文：`pid` / `started_at` / `ct:<创建时间>` / `delegate:<pid> ct:<ct>` / `run:<id>` |
| marker 互斥 sidecar | `<marker>.lock` | 只创建一次、永不删除 —— **不是**「有更新在跑」的证据 |
| checkout 锁 | `<git common dir>/hermes-update.lock` | flock。文件里的字节是上一个持有者的身份，进程退出后还在 —— 判活看 flock，不看字节 |
| 结果文件 | `$HERMES_HOME/.hermes-update-result.json` | `ok`/`exit_code`/`manual`/`message`/`warnings`；下次 Desktop 启动用它弹对话框 |
| 收据 | `$HERMES_HOME/logs/update_receipts/latest.json` 与每次一个文件 | `outcome`（`success`/`partial`/`interrupted`/`failed`）、`exit_code`、`stages` |

`$HERMES_HOME` 是 hand-off 自己推出来的（变量没设时取安装根的上一级），所以 marker 在 checkout 旁边，
不在 checkout 里面。

## 退出码有两层，别混

`hermes update exit code: N` 是**子进程**的：`0` 已提交；`2` 被拒（见下面那条分支）；`130` 在提交点之后被
打断；其它非零是真失败，原因在同段上面那几行输出里。

**hand-off 自己的**码才会写进 `.hermes-update-result.json` 的 `exit_code`、并在下次启动的对话框里出现：
`2` 被拒；`3` 安装 launcher 或安装根缺失/不可用；`4` Desktop 没在等待时间内退出（默认 150 s，什么都没改）；
`8` checkout 停在没并进目标分支的分支上，重试也没用；`70` daemon 没能认领 marker（Desktop 保持开着）；
`129`–`143` hand-off 自己被打断（HUP/INT/QUIT/TERM）。

已提交但**后续步骤**失败的更新，保持 `ok:true` 加一条 warning —— 既不要报成「更新失败」，也不要报成
「还在老版本」。

## 只读探针（下任何结论之前先跑）

```bash
PYTHONPATH=<checkout> <checkout>/venv/bin/python - <<'PY'
from hermes_cli.update_lock import (read_live_update, checkout_lock_held,
                                    update_marker_path, checkout_lock_path)
print("marker:", update_marker_path(), update_marker_path().exists())
print("live update:", read_live_update())
print("checkout lock:", checkout_lock_path(), "held:", checkout_lock_held())
PY
```

marker 不存在、`read_live_update() is None`、`checkout_lock_held() is False` ⇒ 现场干净，重跑能过。不要用
`checkout_lock_held()` 轮询「盯」锁：它每次都真的抢一次锁。

## `exit code: 2`：真并发，还是 hand-off 拒绝了自己

1. 从 `Another Hermes update is already running (… process <pid>)` 里取出 pid。
2. 它是 update 子进程的活祖先，或 `HERMES_UPDATE_HANDOFF_PID`？真有外部更新占着 —— 等它。
3. 它是**兄弟** —— hand-off 自己 fork 出来的进程（marker custodian 就是个 fork，是同一个 hand-off pid
   的子进程）？那就是子进程没能接受自家 hand-off 的声明。这是 marker 协议的缺陷，不是卡住的锁：再点一次
   Update 结果一样，在代码变之前每次都会一样。别写成「过会儿重试」。

要查的失败类别是**两边写法不一致的身份**：一边写身份行（shell 的 `marker.sh::proc_ct`，macOS 上读
`ps -o lstart` 并截到整秒），另一边判它（`update_lock.py::_incarnation` —— 认自己 pid 给 5 ms，认别人给
2 s）。整秒记录与毫秒真值差 0–1 s，5 ms 的判据永远不成立，于是进程把自己那行 `delegate:` 读成陌生人。

## 配方：在活 marker 之外，用真代码证明判定

不要叙述「代码走了哪个分支」——在临时目录里造一个 marker，跑真函数，把判定打出来。几秒钟，而且这正是
汇报需要的证据。

```bash
W=$(mktemp -d); MARKER="$W/.hermes-update-in-progress"
MY_PID=$$; . <checkout>/scripts/desktop-update/marker.sh   # 真的那个 proc_ct 写入方
# 「hand-off」：先 fork 一个 custodian，再起将要判定的子进程（与生产一样，是兄弟）
( trap '' TERM; CUSTODIAN_PID="$(exec sh -c 'echo "$PPID"')"; echo "$CUSTODIAN_PID" > "$W/c.pid"; sleep 60 ) &
C=$!; sleep 0.4; OWNER=$(cat "$W/c.pid"); OWNER_CT=$(proc_ct "$OWNER")
rm -f "$W/go"
( while [ ! -e "$W/go" ]; do sleep 0.05; done
  exec <checkout>/venv/bin/python -u "$W/probe.py" "$MARKER" ) &   # exec：pid 才真的是 delegate
CHILD=$!; sleep 0.4
printf '%s\n%s\nct:%s\ndelegate:%s ct:%s\n' "$OWNER" "$(date +%s)" "$OWNER_CT" "$CHILD" "$(proc_ct "$CHILD")" > "$MARKER"
: > "$W/go"; wait "$CHILD"
kill -9 "$C" 2>/dev/null; wait "$C" 2>/dev/null; rm -rf "$W"
```

`probe.py`：

```python
import os, sys
from pathlib import Path
from hermes_cli.update_lock import _read_marker, _live_partners, UpdateLock, describe_holder, process_create_time
m = _read_marker(Path(sys.argv[1]))
print(m.pid, m.create_time, m.delegate_pid, m.delegate_create_time)
print("owner_live", m.owner_live(), "delegate_live", m.delegate_live(), "partners", _live_partners(m))
lock = UpdateLock(path=Path(sys.argv[1]), install_root=None)   # None：绝不碰真的 checkout 锁
print("is_partner(owner)", lock._is_partner(m.pid))
print("acquire", lock.acquire(), lock.holder)
print(describe_holder(lock.holder))
```

- **只动 delegate 的创建时间做 A/B**：用 shell 的 `proc_ct` 写（整秒）→ `delegate_live()` 为 False、
  `acquire()` 被拒并把 **owner** 报成持有者；用代码自己的写法（`_identity_line(pid)`，3 位小数）写同一个值
  → `delegate_live()` 为 True、`acquire()` 正常接管。唯一差别是精度 —— 所以它是证明，不是故事。
- **判定进程要 `exec`，不要只丢后台**：子 shell 再 fork 一个 python，pid 就变了，marker 里写的是没人拥有的
  pid，复现出来的 bug 会消失。
- 保持 `install_root=None`、marker 路径在临时目录：探针不能碰活 marker，也不能碰真的 checkout 锁。

## macOS 上给探针设硬上限

- 本机没有 GNU `timeout`。要给命令硬上限就包一层：`perl -e 'alarm 60; exec @ARGV' <命令...>`。
- 这个 checkout 是部分克隆：`git log -S`、`git show`、带路径的 `git log` 会按需联网取 blob，可能跑几分钟。
  设上限，或者先用 commit message 的 grep 与工作树把结论立起来。
- 在「稍后要 kill 并 wait」的辅助进程上**不要** `trap '' TERM`：TERM 被忽略，wait 会一直阻塞到它自己的
  sleep 结束，整个探针挂死。用 `kill -9`，或者让它自己退出。

## 修它，以及修完之后怎么核

终端里的 `hermes update` 自己认领 marker、不走 hand-off，所以 hand-off 那条腿坏了它照样能跑：⌘Q 退出
Desktop，然后 `hermes update --yes --gateway --branch main`。它要跑几分钟并重启 gateway —— 也就是你正在
汇报的这个 bot，所以先问。这一次的日志里不会出现 `hand-off start:` 段和 marker 行（没走 hand-off）。

核验：跑上面的只读探针，再查 checkout 自己的 git 历史：

```bash
git -C <checkout> fetch --quiet origin main
git -C <checkout> log --oneline --date=short HEAD..origin/main -- hermes_cli/update_lock.py scripts/desktop-update/
```

部分克隆上判某个提交是不是祖先，用 `git rev-list HEAD | grep -c '^<sha>'`，别用 `merge-base --is-ancestor`
（缺对象时会给出假 NO）。另外：本地直接改身份判据也能解开 Desktop 那条腿且不用重启 gateway，代价是工作区
留一个未提交改动（下次更新会把它 stash 走）。详细的上游核验见 `verify-whether-an-upstream-fix-landed`。
