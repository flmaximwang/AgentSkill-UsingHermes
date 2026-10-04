# 路由盲测：新增本 skill 的那一轮

测量时刻 2026-10-04。这一轮的目的是回答一个问题：**加了这个新头部之后，本包既有 skill 有没有被抢题。**

## 方法与材料

- 候选表：本包全部 skill（19 个）的 `name` + `description`，含本 skill 自己
- 题面：本包 10 个既有 skill 的 `test-prompts.json`（**逐字冻结**，26 条）+ 本 skill 的 4 条正例 + 1 条诱饵 = 31 题
- 判官：2 个独立子代理（`delegate_task`，读同一份材料文件，题面无正负标签），各输出 `P<n> -> skill-name`
- 判据：① 既有题面**一题都没被本 skill 抢走**；② 4 条正例落到本 skill；③ 诱饵落到 `maintain-hermes-gateway`

## 结果

| 判据 | 结果 |
|---|---|
| 两判官逐行一致 | **是**（36/36；材料里每题出现过两次，见下面的坑 1） |
| 既有 26 条题面被本 skill 抢走 | **0 条** |
| 本 skill 正例命中 | 8/8（两组副本各 4/4） |
| 诱饵落到 `maintain-hermes-gateway` | 2/2 |

既有残差 3 条，全部落在别的头部名下，**不是本 skill 造成的**（按包的口径另开一轮）：

- `P11` gold=`hermes-session-routing-forensics` → `maintain-hermes-profiles`（「两个 profile 的 bot 抢同一个频道会怎样」）
- `P25` gold=`maintain-hermes-skills` → `evolve-hermes-skills`
- `P28` gold=`remove-hermes-skills` → `install-hermes-skills`

## 逐题矩阵（判官 picks 解析所得，未手抄）

```
  P1 既有题面       gold=author-a-skill-in-a-pack-repo            picks=author-a-skill-in-a-pack-repo
  P2 既有题面       gold=author-a-skill-in-a-pack-repo            picks=author-a-skill-in-a-pack-repo
  P3 既有题面       gold=author-a-skill-in-a-pack-repo            picks=author-a-skill-in-a-pack-repo
  P4 既有题面       gold=dispatch-work-to-another-profile         picks=dispatch-work-to-another-profile
  P5 既有题面       gold=dispatch-work-to-another-profile         picks=dispatch-work-to-another-profile
  P6 既有题面       gold=dispatch-work-to-another-profile         picks=dispatch-work-to-another-profile
  P7 既有题面       gold=evolve-hermes-skills                     picks=evolve-hermes-skills
  P8 既有题面       gold=evolve-hermes-skills                     picks=evolve-hermes-skills
  P9 既有题面       gold=hermes-session-routing-forensics         picks=hermes-session-routing-forensics
 P10 既有题面       gold=hermes-session-routing-forensics         picks=hermes-session-routing-forensics
 P11 既有题面       gold=hermes-session-routing-forensics         picks=maintain-hermes-profiles
 P12 既有题面       gold=install-hermes-skill-from-a-profile      picks=install-hermes-skill-from-a-profile
 P13 既有题面       gold=install-hermes-skill-from-a-profile      picks=install-hermes-skill-from-a-profile
 P14 既有题面       gold=install-hermes-skill-from-a-profile      picks=install-hermes-skill-from-a-profile
 P15 既有题面       gold=install-hermes-skills                    picks=install-hermes-skills
 P16 既有题面       gold=install-hermes-skills                    picks=install-hermes-skills
 P17 本 skill 正例 gold=leave-and-rejoin-a-discord-thread        picks=leave-and-rejoin-a-discord-thread
 P18 本 skill 正例 gold=leave-and-rejoin-a-discord-thread        picks=leave-and-rejoin-a-discord-thread
 P19 本 skill 正例 gold=leave-and-rejoin-a-discord-thread        picks=leave-and-rejoin-a-discord-thread
 P20 本 skill 正例 gold=leave-and-rejoin-a-discord-thread        picks=leave-and-rejoin-a-discord-thread
 P21 诱饵         gold=leave-and-rejoin-a-discord-thread        picks=maintain-hermes-gateway
 P22 既有题面       gold=load-external-skill-index                picks=load-external-skill-index
 P23 既有题面       gold=load-external-skill-index                picks=load-external-skill-index
 P24 既有题面       gold=load-external-skill-index                picks=load-external-skill-index
 P25 既有题面       gold=maintain-hermes-skills                   picks=evolve-hermes-skills
 P26 既有题面       gold=maintain-hermes-skills                   picks=maintain-hermes-skills
 P27 既有题面       gold=maintain-hermes-skills                   picks=maintain-hermes-skills
 P28 既有题面       gold=remove-hermes-skills                     picks=install-hermes-skills
 P29 既有题面       gold=remove-hermes-skills                     picks=remove-hermes-skills
 P30 既有题面       gold=update-hermes-skills                     picks=update-hermes-skills
 P31 既有题面       gold=update-hermes-skills                     picks=update-hermes-skills
 P32 本 skill 正例 gold=leave-and-rejoin-a-discord-thread        picks=leave-and-rejoin-a-discord-thread
 P33 本 skill 正例 gold=leave-and-rejoin-a-discord-thread        picks=leave-and-rejoin-a-discord-thread
 P34 本 skill 正例 gold=leave-and-rejoin-a-discord-thread        picks=leave-and-rejoin-a-discord-thread
 P35 本 skill 正例 gold=leave-and-rejoin-a-discord-thread        picks=leave-and-rejoin-a-discord-thread
 P36 诱饵         gold=maintain-hermes-gateway                  picks=maintain-hermes-gateway
```

## 这一轮暴露的两个坑

1. **旧题集的 glob 会把新技能自己的题收进去**：材料脚本按 `skills/*/test-prompts.json` 取"既有题面"，而此刻新技能目录已经存在 →
   我的 5 条正例/诱饵被投放了两次（`P17–P21` 与 `P32–P36`）。判官结果不受影响（同一题两次都落在同一答案），但**统计口径会错**：
   第一次算出的"既有题面 31 条"其实是 26 条，而"自己的正例"被混在旧题集里当成"没被抢走"的既有题。做法：旧题集 glob 显式排除本技能目录，
   或者合并后按题面文本去重再统计。
2. **闸不读意图**：把两台机器的代理来源写成 markdown 表格后，一个单元格里「进程 env」正好紧挨着表格的竖线，命中
   `dump_all_env`（high, exfiltration）—— 那条规则的字面形态就是 `env` 后面紧跟一个竖线。整份 skill 因此从 `safe` 掉到
   `caution`（community 源就要 `--force` 才能装）。改成「进程环境变量」即回到 `safe`。教训：**引用这条形态的说明文字本身也会命中**，
   所以要描述它、不要复现它。同理 `127.0.0.1:<port>` 会各留一条 medium `hardcoded_ip_port`（medium 单独不改变
   verdict，**接受，不改**）。

## 接受的代价

- 4 条 medium `hardcoded_ip_port`（两处本机/远端代理端口）保留：它们是这台机器/这台 NAS 的实测事实，改掉就失真。
- 3 条既有残差留给各自头部的那一轮；本 skill 不为此特化头部。
