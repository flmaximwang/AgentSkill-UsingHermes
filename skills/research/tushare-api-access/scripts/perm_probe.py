"""Tushare Pro 权限差分探测：推断当前账号实际积分档位。

用法:
    /Applications/TradingRazer2/bin/python perm_probe.py [YYYYMMDD]

不带日期则自动取最近交易日。逐接口打印 PASS/FAIL：
- 全 PASS 2000 档 + 全 FAIL 5000 档对照 => 账号 = 2000 档
- 能调通的接口（如 fund_daily）实际门槛即 = 2000 档，文档写 5000 属滞后

需要环境变量 TUSHARE_TOKEN。
"""
import os
import sys
from datetime import date, timedelta

import tushare as ts

token = os.environ.get("TUSHARE_TOKEN")
if not token:
    raise SystemExit("TUSHARE_TOKEN 未设置")

pro = ts.pro_api(token)

d = sys.argv[1] if len(sys.argv) > 1 else None
if not d:
    end = date.today().strftime("%Y%m%d")
    start = (date.today() - timedelta(days=40)).strftime("%Y%m%d")
    cal = pro.trade_cal(exchange="SSE", start_date=start, end_date=end)
    days = cal[cal["is_open"] == 1]["cal_date"].tolist()
    d = days[-1]
    print(f"auto trade_date = {d}")

tests = {
    # 2000 档对照（应 PASS）
    "fund_daily  (文档写5000/实测2000档)": lambda: pro.fund_daily(ts_code="510300.SH", trade_date=d),
    "index_daily (文档写2000档)": lambda: pro.index_daily(ts_code="000001.SH", trade_date=d),
    "moneyflow   (2000档)": lambda: pro.moneyflow(ts_code="000001.SZ", trade_date=d),
    "hsgt_top10  (2000档)": lambda: pro.hsgt_top10(trade_date=d),
    # 5000+ 档对照（通常 FAIL）
    "sw_daily    (5000档对照)": lambda: pro.sw_daily(ts_code="801010.SI", start_date=d, end_date=d),
    "limit_list_d(5000档对照)": lambda: pro.limit_list_d(trade_date=d),
    "cyq_chips   (5000档对照)": lambda: pro.cyq_chips(ts_code="000001.SZ", trade_date=d),
}

for name, fn in tests.items():
    try:
        df = fn()
        print(f"PASS  {name}: {len(df)} rows")
    except Exception as e:
        msg = str(e).replace("\n", " ")[:120]
        print(f"FAIL  {name}: {msg}")
