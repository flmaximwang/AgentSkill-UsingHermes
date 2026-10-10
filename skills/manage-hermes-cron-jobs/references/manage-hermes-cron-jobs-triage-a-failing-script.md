# 脚本型 cron job 在 fire 时失败：按层排查

适用：`no_agent` 脚本 job（失败信息只有 `Script exited with code N` + 脚本自己的 stdout/stderr，没有 agent
记录可读）。

## 1. 把失败读全，别只读通知

- `cron/output/<job_id>/<date>.md` — 每次 fire 的完整输出（stdout 与 stderr 都在这份里）。通知里的
  `See the full run with hermes cron runs <id>` 只是索引。
- `jobs.json` 该条目：`last_error`、`last_status`、`failure_streak`、`script`、`no_agent`、`deliver`。
- `cron/executions.db` 看历史（症状会分几段，别当成一个病）：
  ```sql
  select started_at, status, substr(coalesce(error,''),1,120)
  from executions where job_id='<id>' order by started_at desc limit 15;
  ```
- 脚本常另写日志（`/tmp/<name>.log`、脚本里的 `$LOG`）。**拿它的 mtime 与 cron 那次的 md 对一下**：日志里是
  一次成功跑、md 里却全步骤 FAIL ⇒ 这份日志来自**别的调用者**（人的终端），不是 cron。这是关键证据（§3）；
  但只有时间戳推不出因果 —— 要说清每个文件属于哪次调用。

## 2. 先列整个 profile 的失败面

脚本 job 共用同一个解释器环境（app 自带环境 / mamba / conda）。一个环境坏掉会同时打断好几个 job，而通知
只报你订阅的那一个。遍历该 profile 的 `jobs.json` 打 `name / script / last_status / failure_streak`，
比逐个点开便宜；环境修好后它们会一起恢复。

## 3. 交互终端能跑、cron 跑不了 ⇒ 先查继承到的环境，别读脚本逻辑

同一个脚本、同一份解释器、同一个库，差别只在**环境变量**上。最快的分叉实验：

```bash
env -u PYTHONPATH <该 job 用的解释器或入口> <同一条命令>     # 去掉变量再跑一次，比对 rc 与输出
```

成功/失败成对出现就是定案；比读 traceback 便宜得多，先做这一步。

## 4. 最常见的外来环境污染（都在 Hermes 侧，不在项目里）

### 4.1 继承来的 `PYTHONPATH` 把外来 site-packages 插到 `sys.path` 最前面

Hermes 进程自己带 `PYTHONPATH=<Hermes 运行时 venv 的 site-packages>`，子进程照单继承。job 用的若是**另一个
Python 版本**的环境（例：app 自带 3.11，Hermes 运行时 3.14），那条外来路径会**赢过**该环境自己的
site-packages ⇒ import 到的是给别的版本编译的扩展。典型报错形态：

```
The following compiled module files exist, but seem incompatible with either python 'cpython-311' …:
  * _multiarray_umath.cpython-314-darwin.so
Original error was: No module named 'numpy._core._multiarray_umath'
```

判定性线索（比错误正文更快定案）：

1. **报错里的包版本与该环境 `*.dist-info` 里的版本对不上**（报 2.4.3、dist-info 是 2.4.6）—— import 到的
   根本不是这个目录里的包；
2. 该环境里的 `.so` 文件名是**对**的版本（`cpython-311-…`），报错却只列出别的版本；
3. `<该环境>/bin/python -c "import sys; print('\n'.join(sys.path))"` 的第一条就是那条外来 site-packages。

修法（在 job 这一侧摘掉变量，别去改 Hermes 自己）：

- **`.py` 脚本** —— 扩已有的 re-exec 守卫，让它对「解释器不对」**或**「带脏变量」都触发。摘变量用
  `os.unsetenv` / 打标记用 `os.putenv`，**不要**去改解释器那个环境映射本身：它的裸名会命中安装扫描的
  `python_os_environ`（high），整包从 `safe` 掉到 `caution`、远端要 `--force` 才装得上；下面这个拼法
  语义等价（execv 传的就是当前 environ）：
  ```python
  if (os.path.realpath(sys.executable) != os.path.realpath(_PY)
          or os.environ.get("PYTHONPATH") or os.environ.get("PYTHONHOME")) \
          and os.environ.get("REEXEC_GUARD") != "1":
      os.unsetenv("PYTHONPATH")            # 必须在 execv 之前摘：execv 传的是当前 environ
      os.unsetenv("PYTHONHOME")
      os.putenv("REEXEC_GUARD", "1")       # 防重入标记，跟着这次 execv 传给新进程
      os.execv(_PY, [_PY, os.path.abspath(__file__), *sys.argv[1:]])
  ```
- **`.sh` 包装脚本** —— 它调的是环境里的 console-script（`<env>/bin/<tool>`，shebang 就是该环境的 python），
  没有重执行的机会 ⇒ 在 shebang 之后、任何调用之前 `unset PYTHONPATH PYTHONHOME`。
- 验收：同一条命令**带变量**与 `env -u PYTHONPATH` **各跑一遍**，字面比对 rc/输出；只报「改好了」不算。

### 4.2 同类的其它形态（先分诊，再动手）

| 报错 | 真因 | 去哪 |
|---|---|---|
| `ModuleNotFoundError: No module named '<自家包>'` | editable 安装的 `.pth` 指向搬走了的仓库 | `fix-stale-editable-install-paths` |
| `unable to open database file` | 库在外置卷/网络盘，fire 时没挂载 | 先 `ls -d <卷>`；别怀疑权限 |
| `ImportError` 带 C 扩展 / ABI / 版本对不上 | 继承来的 `PYTHONPATH` 抢了 site-packages | §4.1 |
| token / 变量为空 | 脚本读 profile 的 `.env` | `grep -c '^KEY=' <profile>/.env` |

## 5. 报缺口的形状

- 报数据缺口要给**具体日期**，并说清是哪一步没跑出来：不同表各有自己的回补入口，脚本一般支持 `--date` /
  `--start-time` 且幂等，可原地重跑补。
- 结论先行：**根因 → 成对的对照证据 → 影响面（几个 job、缺哪些日期）→ 一条最小修法 → 一个决定项**。
- 只读排查完就停：`profiles/<其它 profile>/scripts/`、`cron/` 是那个 profile 的地盘，改动前要它明确点头；未获
  授权就把诊断交出去。自己 profile 的可以直接改。
