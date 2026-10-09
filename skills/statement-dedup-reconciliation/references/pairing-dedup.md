# 配对去重：诊断与修复对照表

适用：账户勾稽报「不一致，差 X —— 有流水被跳过但未在别处入账，必须查」。
逐账户银行勾稽明细在账本「配对与问题」表；`book` / `month` 会把不平静的打到控制台。

## 诊断脚本骨架

临时放 `/tmp`，不进仓库。

```python
import os, sys
os.chdir("<项目根>"); sys.path.insert(0, "<项目根>")
from collections import Counter
from Scripts import paths
from Scripts.books import book, period_of
from Scripts.money import money
from Scripts.parsers import normalize_dir
from Scripts.rules import load_map, load_yaml

period, acct = sys.argv[1], sys.argv[2]
records, errors, per_file, dups = normalize_dir(paths.RUNNING_ACCOUNT_DIR)
cfg, rules = load_map("Config/account_map.yaml")
coa = {str(i["code"]): i for g in load_yaml("Config/chart_of_accounts.yaml").get("accounts", {}).values() for i in g}
res = book(records, cfg, rules, coa, duplicates=dups)

flow, booked = Counter(), Counter()
for r in records:
    if r.get("账户") == acct and period_of(r.get("日期")) == period:
        d = "+" if r["收支"] == "in" else ("-" if r["收支"] == "out" else "o")
        flow[(str(money(r["金额"])), d)] += 1
for e in res["entries"]:
    if (e.get("凭证日期") or "")[:7] != period:
        continue
    for ln in e["行"]:
        if (ln.get("明细") or "") != acct:
            continue
        if float(ln.get("借方金额") or 0) > 0:
            booked[(str(money(ln["借方金额"])), "+")] += 1
        if float(ln.get("贷方金额") or 0) > 0:
            booked[(str(money(ln["贷方金额"])), "-")] += 1
print("记账多:", dict(booked - flow))
print("记账少:", dict(flow - booked))
```

**注意**：这里刻意**不带日期**。带上日期后，跨日期的同笔（提现到账差 1 天、退款延迟入账）
会同时出现在「多」和「少」里，把一处差报成两处，方向也会看反。

## 看跳过原因（比读代码猜快）

```python
skip = {(str(s.get("源文件")), str(s.get("源行号"))): str(s.get("_pair_skip") or s.get("_no_entry"))
        for s in res["skipped"]}
# 对目标流水：k = (源文件, 源行号)，print(skip.get(k)) → 它在哪一步、以什么理由被跳过
```

配对函数按顺序单独调用（`pair_jd_duplicates → pair_internal_transfers → pair_card_funded →
pair_own_account_transfers`）并打印中间结果，能直接看出是哪一步把目标流水拿走的。

## 五类根因

| 症状 | 根因 | 修法 |
|---|---|---|
| 平台侧「退款-…」两侧各记一次 | 退款配对只认 `收支 == "in"`，而账单把退款标成 `neutral` | 放宽成 `in ("in", "neutral")` |
| 平台侧提现/退出行配到了另一家渠道的银行流水 | 只按同额+同日配，没有渠道约束 | 配对前按「支付宝↔支付宝、财付通/微信↔微信」过滤 |
| 银行侧「转给本人另一张卡」的划转被平台配对抢走 | 它进了 `bank_in` / `bank_out` 池 | 建池时排掉 `own_account_item()` 命中的行 |
| 平台侧「转出到银行卡」（neutral）永远配不上 | 只去 `bank_out` 找对手，而它是流入 | 该分支去 `bank_in` 找 |
| 两头都跳过、钱凭空消失 | 配对规则各跑一遍、互相看不见对方跳了什么（断链） | 收紧各自条件；**不要**加兜底 |

## 断链链条长什么样

```
银行侧 B（提现到账）   ← 被 pair_internal_transfers 跳过，理由「平台侧 P 会入账」
平台侧 P（小荷包-转出）← 被 pair_card_funded 跳过，理由「另一笔银行流水会入账」
```

B 的对手是 P、P 的对手是另一个人 —— 谁都没入账。判据就是「渠道不一致」：
P 是支付宝的行，却配到了银行侧写着「财付通-理财通赎回」的那笔。

## 修复节奏

1. 一处只改一个条件；
2. 改完立刻重跑，记下差数变化；
3. 差数只减不增才算修对，变差就回退这一处；
4. 同一类差可能分散在多期，看全部期间。

反面教材：通用兜底「跳过的记录若找不到未跳过的同额对手，就放回来入账」—— 判据太宽，
一次运行误救 1,770 笔，凭证数翻倍、勾稽差从 12 处变 32 处。回退，改走一处一根因。

## 验收

- 逐账户银行勾稽全部「一致」；
- 统计表两条勾稽都为 0；
- 待分类为 0；
- `check --workbook <账本>` 结论「通过」。
