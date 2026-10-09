#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证探针：证明缠论 CChan 内部通过 KlineDBAPI.get_kl_data() 逐根取数。

背景：指标脚本里 `df = KlineDBAPI._read_raw(code)` 是"脚本层"拿数据（做
--start/end-time 过滤、周/月重采样、输出对齐）；缠论引擎"引擎层"由 CChan
实例化 KlineDBAPI 类并经 get_kl_data() 逐根消费 K 线——两条路共享 _RAW_CACHE。
本探针给 get_kl_data 加计数器，断言引擎消费数 == 脚本 df 行数。

用法：
  /Applications/InvestAdvisor/venv/bin/python prove_kline_api.py [DB路径] [code] [start]

依赖：sys.path 需含指标计算目录（脚本同目录有 KlineDBAPI.py）与 chan.py 目录。
"""
import os
import sys

CHAN_REPO = os.environ.get("CHAN_REPO", "/Applications/InvestAdvisor/chan.py")
sys.path.insert(0, CHAN_REPO)
os.environ["CHAN_REPO"] = CHAN_REPO
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # 指标计算/ 目录

import pandas as pd  # noqa: E402

from Common.CEnum import KL_TYPE  # noqa: E402
import KlineDBAPI  # noqa: E402（用户仓库模块；ind_chanlun_common 会做 sys.modules 注入）

DB = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Documents/Obsidian/wangfanlin2_Investment/💾 Database/vnpy.db")
CODE = sys.argv[2] if len(sys.argv) > 2 else "000001.SH"
START = sys.argv[3] if len(sys.argv) > 3 else "2026-01-01"

# --- 1. 给 get_kl_data 加计数器 ---
orig = KlineDBAPI.KlineDBAPI.get_kl_data
counter = {"n": 0}


def counting(self):
    for u in orig(self):
        counter["n"] += 1
        yield u


KlineDBAPI.KlineDBAPI.get_kl_data = counting

# --- 2. 脚本侧拿 df（时间过滤后）---
KlineDBAPI.DB = DB
df = KlineDBAPI._read_raw(CODE)
df = df[df["t"] >= pd.Timestamp(START)].reset_index(drop=True)
print(f"脚本侧 df: {len(df)} 根 ({START} 起)")

# --- 3. 跑缠论（内部实例化 KlineDBAPI 并逐根取数）---
from ind_chanlun_common import chan_bi_signal  # noqa: E402

bi = chan_bi_signal(df, CODE, KL_TYPE.K_DAY, begin_time=START, end_time=None)
n_sig = int((bi != None).sum())  # noqa: E711

print(f"缠论引擎侧: get_kl_data() 被消费 {counter['n']} 根 K 线")
print(f"           → 产出 {n_sig} 个有笔方向的周期 (df 共 {len(df)} 行)")
ok = counter["n"] == len(df)
print(f"结论: 引擎消费({counter['n']}) == 脚本 df({len(df)}) → "
      f"{'✅ 缠论确实通过 KlineDBAPI 取数' if ok else '⚠️ 数量不符，检查数据源注入'}")
sys.exit(0 if ok else 1)
