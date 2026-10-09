# 缠论指标脚本详档（ind_chanlun_* + KlineDBAPI）

## 信号定义（用户定稿）

- **缠论v3**（2026-08-12）：v2 改进——向上笔内**跳过开头阴线、从第一条阳线开始出多**，连续出多直到出现阴线；向下笔内从第一条阴线开始出空直到出现阳线（多空对称镜像）。
- **缠论v2**：向上笔从笔起点一直出多直到遇第一根阴线停止；向下笔对称（从笔起点出空直到遇阳线）。
- 信号 CSV 列 = date, signal(1/-1/0), lag；通用模式脚本输出每标的一个 `<标的>_chan_v3.csv`。

## INTERVAL_CFG（v3 脚本内映射，vnpy interval → chan 参数）

| interval | chan code 前缀 | KL_TYPE | lag k_max | lag granularity |
|---|---|---|---|---|
| mn | (无) | K_MON | 48 | M |
| w | (无) | K_WEEK | 60 | W |
| d | (无) | K_DAY | 15 | D |
| 4h | 4h. | K_DAY | 15 | D |
| 2h | 2h. | K_DAY | 15 | D |
| 1h | m60. | K_DAY | 15 | D |
| 30m | m30. | K_DAY | 15 | D |
| 15m | m15. | K_DAY | 15 | D |
| 5m | m5. | K_DAY | 15 | D |
| 1m | m1. | K_DAY | 15 | D |

- 周/月线：脚本与 KlineDBAPI._load 都按 `resample("W-FRI")` / `resample("ME")` 聚合（必须一致，否则笔 idx 对不上）。
- 4H/分钟线喂 **K_DAY**（不聚合）；GC=F 4H 是每天 4 根带时分，指数"4H"实为每天 1 根纯日期。

## ind_chanlun_common.py 核心坑（2026-08-13 实测）

- **双 load bug**：CChan 构造（trigger_step=False）即自动全量加载，**勿再显式 chan.load()**——喂两遍导致 KLine/笔数翻倍、笔结构错乱。
- `bi.get_begin_klu()` 返回 CKLine_Unit，其 `.idx` = 原始 K 线行索引（非合并后 KLine 索引）。
- `chan_bi_signal(df, code, k_type, begin_time=None, end_time=None)`：begin/end 传 CChan 截断重算（--start-time/--end-time 必须同步传，否则全量笔 idx 超出截断 df）。
- **lag = 窗口扫描模式（用户定义，勿以周期为中心逐 T 扫描）**：全量算信号 → 窗口 [w, w+L-1]（L=100）从左到右滑 → 周期 i 信号首次在右端 R 窗口与全量一致 → lag[i]=R-i（观测日=R）；前 L 周期作废；未确认 → k_max+1 哨兵。4H 带时间序列 begin/end 必须保留时分（end_fmt 按 t0 有无时分选择），否则窗口为空。
- k_max：日线/4H=15，周线=60，月线=48（周/月确认滞后=笔剩余长度，可达 50+ 周期）。
- 周/月线信号必须喂真聚合数据（K_WEEK→W-FRI、K_MON→ME），日线当周/月线喂会信号全错（2026-08-13 已修复）。

## chan.py 使用机制（非 pip 包，源码即用）

- chan.py **没有** setup.py/pyproject.toml/requirements.txt，pip 装不了；作者设计 = clone 即用（README/quick_guide 均无安装步骤）。`chan.py/` 目录是 8-12 从 /tmp 固化的源码副本（GitHub: qschen/chan.py），不在 venv 也不在仓库。
- 用法：`sys.path.insert(0, "<chan.py目录>")` 后**顶层 import**：`from Chan import CChan`（Chan.py 是顶层模块文件，不是包）、`from ChanConfig import CChanConfig`、`from Common.CEnum import KL_TYPE`；内部模块全是顶层绝对导入，目录进 sys.path 整棵依赖树即可跑。

## --chan-repo 动态指定 chan.py 位置（2026-08-14 加）

- 指标脚本支持 `--chan-repo <路径>`：sys.path 必须在 import 前就位 → 脚本顶部 `_early_chan_repo()` 先扫 argv，兜底顺序：`--chan-repo` 参数 > 环境变量 `CHAN_REPO` > 默认 `/Applications/InvestAdvisor/chan.py`；realpath 后写 `os.environ["CHAN_REPO"]`（供 ind_chanlun_common 等同步读取）+ `sys.path.insert(0, 仓库目录)` + `insert(0, 父目录)`。
- `ind_chanlun_common.py` 用 `os.environ.get("CHAN_REPO", 默认)` 取代硬编码路径（不设环境变量时行为不变，bi/v2 脚本不受影响）。
- 验证：传错误路径应报 `ModuleNotFoundError: No module named 'Common'`（证明参数生效）。

## KlineDBAPI 架构（chan.py 数据源）

- **加载机制**：`data_src="custom:文件名.类名"` → `Chan.py` 里 `importlib.import_module(f"DataAPI.{文件名}")`——`import_module` 先查 `sys.modules`，所以**可从仓库外注入，chan.py 零改动**。
- **归属（用户 2026-08-14 原则：自定义源代码不放第三方仓库）**：KlineDBAPI.py 唯一一份在用户仓库 `🧠 System/多空信号验证/指标计算/KlineDBAPI.py`；chan.py/DataAPI/ 内无副本。注入链：`ind_chanlun_common.py` / `ind_chanlun.py` 里 `import KlineDBAPI; sys.modules["DataAPI.KlineDBAPI"] = KlineDBAPI` → CChan 的 import_module 命中缓存。chan.py 升级/重装/重新 clone 均不影响我们的适配层。
- 该文件用**绝对导入** `from DataAPI.CommonStockAPI import CCommonStockApi`（chan.py 在 sys.path 时可用）；勿改回相对导入（离开包结构会失败）。勿在 chan.py 仓库内留任何自定义副本（用户明确反对"自己的源码放在别人仓库里"）。
- **双角色**：脚本层调 `KlineDBAPI._read_raw()` 拿 df（做 --start/end 过滤、周/月重采样、输出对齐）；缠论引擎层由 CChan 实例化 KlineDBAPI 类经 `get_kl_data()` 逐根取数（分型/笔/线段的数据源）——脚本"自己提取 df"≠数据源没用，两条路共享 `_RAW_CACHE`（脚本先读 → 缓存 → chan 内部命中，不重复读库）。验证探针：`scripts/prove_kline_api.py`（给 get_kl_data 加计数器，证明缠论引擎消费数 == 脚本 df 行数）。
- **双结构自动识别**（_read_raw）：连接后查 sqlite_master——有 `dbbardata` 表 = vnpy.db（dbbardata + adj_factor 前复权）；否则 = kline.db 旧表（daily/index_daily/fund_daily/kline_4h/stk_mins_30m/gold_daily，daily 个股同样前复权）。
- **模块级 DB 可覆盖**：`import KlineDBAPI; KlineDBAPI.DB = path`（指标脚本 --database 用）；⚠️ **换库必须 `_RAW_CACHE.clear()`**（缓存按 code 键，不清会串库）。
- code 前缀约定：GC=F→(GC=F,SGE,4h)；XAU→(XAU,SGE,d)；idx.x→指数 d；stk.x→个股 d 前复权；m30./m15./m5./m60./m1.→分钟；4h./2h.→4H/2H；裸 ts_code 兜底按个股 d。前复权黑名单 000001/000300/399001/399006/000688（指数无因子，merge 全 NaN → f=1.0）。
- 读取层清洗：open>high/close<low 脏数据用 `high=max(open,high,close)`、`low=min(open,low,close)` 修正（缠论时间单调性/价格校验严格）。
- 指数 4H 是每天 1 根（纯日期），GC=F 4H 每天 4 根带时分——两者喂缠论都正常，但语义不同。

## 验证口径

- 新参数模式输出 vs 旧 signals CSV 对拍：`--start-time` 截断起点两周内可能有少量差异（数据积累期/笔起点效应，0.8% 量级属正常）；其余应完全一致。
- 个股前复权验证：kline.db 与 vnpy.db 读同一标的应行数、收盘价完全一致（迁移零差异）。
