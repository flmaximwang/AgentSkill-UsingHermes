# Tushare 财务接口权限实测（2026-08-30，2000 档账号）

对当前 token 逐一**最小调用**（单标的/单报告期）实测，17 个财务接口全部 PASS：

| 接口 | 最小调用 | 实测 |
|---|---|---|
| daily_basic | `pro.daily_basic(ts_code="000001.SZ", trade_date="20260827")` | PASS 1 行 |
| fina_indicator | `pro.fina_indicator(ts_code="000001.SZ", period="20260331")` | PASS |
| income | `pro.income(ts_code=.., period=..)` | PASS |
| balancesheet | `pro.balancesheet(ts_code=.., period=..)` | PASS 2 行 |
| cashflow | `pro.cashflow(ts_code=.., period=..)` | PASS |
| forecast / express | `pro.forecast(ts_code=.., period=..)` | PASS（0 行=无事件，非权限） |
| dividend | `pro.dividend(ts_code="000001.SZ")` | PASS 97 行 |
| fina_audit | `pro.fina_audit(ts_code=..)` | PASS 39 行 |
| stk_holdernumber | `pro.stk_holdernumber(ts_code=..)` | PASS 150 行 |
| fina_mainbz | `pro.fina_mainbz(ts_code=.., period=..)` | PASS |
| top10_holders / top10_floatholders | `pro.top10_holders(ts_code=.., period=..)` | PASS 10 行 |
| pledge_detail | `pro.pledge_detail(ts_code=..)` | PASS |
| pledge_stat | `pro.pledge_stat(ts_code=..)` | PASS 641 行 |
| share_float | `pro.share_float(ts_code=..)` | PASS 106 行 |
| disclosure_date | `pro.disclosure_date(ts_code=..)` | PASS 120 行 |

## 结论

- 2000 档（200 元/年）即可调全部财务接口 → 淘宝历史主源 + tushare 增量补新报告期/daily_basic
  的方案**成本已覆盖，无需升档**。
- 报「抱歉，您没有接口访问权限」= 当前档位不足；文档（doc 写某接口需 5000）与实测
  冲突时以实测为准。
- 频控 200 次/分钟：全市场 5000+ 票逐票循环必须节流（sleep），10 万次/天配额够用。
- 结合 5000 档对照（sw_daily/limit_list_d/cyq_chips 全 FAIL）→ 账号判定 = 2000 档。
- 探测模板可直接复用 `scripts/perm_probe.py` 的模式（单标的 + 最小参数）。