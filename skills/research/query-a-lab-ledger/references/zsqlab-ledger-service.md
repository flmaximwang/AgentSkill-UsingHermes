# zsqlab 台账服务：拓扑与「把库搬出去」

本文件只讲**这套 Dolt 服务本身**（进程、数据目录、库清单、备份/推送）。查询口径与身份通道仍看
SKILL.md 的 Step 1–5，本文件不改变「只读、只到定义层」的交付约定。

## 1 · 拓扑（本机实测，快照口径）

- 进程：`dolt sql-server --data-dir /Users/org_zsqlab/Dolt -H 127.0.0.1 -P 13308 -l info`。
- **数据目录是多库容器，不是单个 Dolt 库**：`/Users/org_zsqlab/Dolt` 下有全局 `.dolt/`、`.doltcfg/`、
  `config.yaml`、`dolt.log`、`dolt.pid`，**每个库是它的一个子目录**（各自带 `.dolt/`）。
- 库清单要当场取（台账是活的）：`for d in <data-dir>/*/; do cd "$d" && dolt status; done`。
  在数据目录**根**上跑 `dolt status` 不是「一个库」，别把根目录当库、也别把 4 个库当一个库。
- 已见到的库（快照，用前重取）：`plasmid-backbone` / `zsqlab05` / `zsqlab08` / `zsqlab10`。
  `zsqlab10` = 库存/实体/盒位那张表族（`entity_*` / `stock_*` / `box_*` / `checks`）——用户说
  「Inventory」时多半指它。
- 查表/视图/数据一律走 SQL（SKILL.md Step 1 的 `dolt --host 127.0.0.1 --port 13308 --no-tls sql`），
  不要靠读数据目录里的文件猜 schema。

## 2 · remote 与 backup 都是 per-数据库的

没有「整目录一次推」这回事：4 个库要各自 `dolt remote add` / `dolt backup add`。
用户问「台账怎么推到 remote / 怎么备份」时，先问清是**哪个库**，别默认一个答案覆盖全部。

## 3 · 服务器在跑也能 CLI push（dolt 2.3.5 实测）

- 在正被 `dolt sql-server` 占着的 data-dir 上，`dolt remote add origin file://<dir>` 与
  `dolt push -u origin main` **都成功**。→ 备份活动台账**不需要停机**。
- 官方文档里「不能 push 到被运行中 sql-server 锁定的数据目录」说的是**接收侧**（SSH transfer 要拿那把锁），
  不是发送侧。别把它读成「服务器在跑就不能推」。
- 三步：`dolt add -A && dolt commit -m '…'` → 配 remote → `dolt push -u origin main`。
  判停点：输出 `* [new branch] main -> main`；`Everything up-to-date` = 没有新提交（多半是**忘了 commit**）。
  验证要读回 `dolt remote -v` 与 `dolt branch -a` 里的 `remotes/origin/main`，别只看「没报错」。

## 4 · push 与 backup 不是一回事

- `dolt push` 只送**该分支的当前提交**：未提交改动、其它分支都不含。
- 要含工作集的全库快照：`dolt backup add <名> <url>` + `dolt backup sync <名>`；
  `dolt backup restore <url> <新目录>` 连未提交时写入的行一起恢复。
- 用户问的是「备份」而你说「push 一下」时，先声明这个差别再动手。

## 5 · 用私有 Git 仓库当 remote（本机已具备的条件）

```bash
cd /Users/org_zsqlab/Dolt/<库>
dolt remote add origin git@github.com:<owner>/<repo>.git   # 用 SSH URL
dolt push -u origin main
```

- **必须用 SSH URL**：`gh repo create` 留下的是 https origin，裸 `git push`/`dolt push` 会卡在凭据提示。
- 硬前置：目标 git 仓库**必须已有至少一个 commit**。空 bare 仓库会报
  `git remote has no branches: cannot push to "…"; initialize the repository with an initial branch/commit first`。
- Dolt 只写 `refs/dolt/data`（实测另加 `refs/heads/__dolt_remote_info__`），**不动** `refs/heads/main`
  → 同一个仓库里放 Dolt 数据与普通文件互不干扰。
- DoltHub 路线要先 `dolt login`（生成密钥对并在网页绑定）；`dolt creds ls` 空 = 这台机器还没登录过。

## 6 · 推到 NAS（`ssh://` remote，端到端实测通过）

用户给的往往不是 URL，而是「主机/路径」的直觉写法。**先把它补成合法 URL 再动手**，缺一段路径
前缀也会安静地建成另一个 remote。

```bash
# 0) 目标目录必须先存在（见下面第 1 条）
ssh wangfanlin1@10.10.74.242 'mkdir -p /volume1/homes/wangfanlin1/dolt-remotes/<库>.dolt'
# 1) 路径要写远端主机上的**绝对路径**；主机登录信息走调用侧的 ~/.ssh/config，不需要 --user
cd /Users/org_zsqlab/Dolt/<库>
dolt remote add nas ssh://wangfanlin1@10.10.74.242/volume1/homes/wangfanlin1/dolt-remotes/<库>.dolt
# 2) 远端没把 dolt 放进 sshd 的 PATH，所以每次连它都要指一次远端二进制
DOLT_SSH_EXEC_PATH=/volume1/homes/wangfanlin1/bin/dolt dolt push -u nas main
# 3) 读回验证：clone 出来看数据是否真的在
dolt clone "ssh://wangfanlin1@10.10.74.242/volume1/…/<库>.dolt" /tmp/<库>-check
```

1. **`ssh://` 的目标目录必须已存在**：目录不存在时 push 报
   `could not be accessed; repository not found at <path>`。空目录即可，**不必** `dolt init`
   （`file://` 会自动建目录，`ssh://` 不会——两者行为不同，别互相类推）。
2. **裸 `host/path` 不能当 remote**：没有 scheme 时 Dolt 按默认前缀当 `https://…` 处理，结果是接不上的
   HTTPS remotesapi；主机+路径必须显式写成 `ssh://`。
3. **远端要有一个 `dolt` 可执行**（SSH remote 是 Dolt 在远端跑 `transfer`，没有常驻服务进程）。
   装法：官方静态二进制解到 `$HOME/bin/dolt`（DSM 上可行，见 `administer-a-synology-nas`）。
4. **远端 sshd 的 PATH 一般不含 `$HOME/bin`**（DSM 实测 `/usr/bin:/bin:/usr/sbin:/sbin`），
   于是报 `sh: dolt: command not found`。用官方给的 `DOLT_SSH_EXEC_PATH=<远端绝对路径>`（另有
   `DOLT_SSH_COMMAND`，等价于 git 的 `GIT_SSH_COMMAND`）——**不要**为这一步去要 root；
   要免环境变量只能把它装进 `/usr/bin`，那需要用户自己 sudo。
5. **远端目录不能在同步 share 里**：这套 share 由 Synology Drive 双向同步，remote 的 chunk 文件
   每次 push 都变，会被同步回 Mac 并可能撞出冲突副本。放 NAS home（实测不同步）。详见
   `administer-a-synology-nas` 的同步 share 探测法。
6. 远端目录里看到的是 remote 存储本身（`manifest`、`LOCK`、`*.darc`）——**它不是一个能就地查询的库**：
   往一个已有 Dolt 库目录 push，数据确实进去了，但那个目录自己的 `dolt log` / 表**看不出来**，
   只能靠 `clone`/`pull` 取回。所以别把「推送目标」同时当工作库。

## 7 · 灾备：光有 push/backup 恢复不出完整 server

把库搬走之外，还要一并带走：数据目录里的 `config.yaml`、全局 Dolt 配置目录（`DOLT_ROOT_PATH`，默认 `~/.dolt`）、
`mysql` 库里的用户授权（`mysqldump mysql --flush-privileges --insert-ignore -uroot > dump.sql`）、
各库 `.dolt/repo_state.json`，以及**分支权限表** `dolt_branch_control` / `dolt_branch_namespace`
（push 与 `dolt backup` 都**不会**自动带上，要单独导出）。

## Pitfalls

- 别在数据目录根上找表：根不是库，库是它的子目录。
- 别把「push 成功」当成「台账已备份」：push 不含未提交改动与其它分支。
- 别在同一库上同时改 script 与远程配置还以为互不影响：remote 配置写在库的 `.dolt/repo_state.json` 里，
  它属于「随库一起备份」的东西。
- 别在**没有先跑通一条真链路**时把命令交出去：给用户的每条命令都应当是当场 `remote add → push → clone 读回`
  跑过的形态；远端缺二进制、目录不存在、路径少一段这类问题只有真跑才会现形。
