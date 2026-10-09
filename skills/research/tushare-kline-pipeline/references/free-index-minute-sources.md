# 免费指数分钟线数据源实测矩阵（2026-08-16 全面复测）

背景：sina_index_source.py 当时因东财被代理挡死而退到新浪新接口（上限 1023 根 ≈ 4.2 交易日）。
本次因评估 QuantDash 软文方案，把全部候选免费源逐一实测，发现老接口可把 5m+ 深度提升 5 倍。

## 各源实测结果

| 源 | 接口 | 指数 1m | 历史上限 | 备注 |
|---|---|---|---|---|
| **新浪新接口**（现用） | `quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData` | ✅ | **1023 根** ≈4.2 交易日 | 直连可用；datalen>1023 返回空数组（不是截断） |
| **新浪老接口** ⭐ | `money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData` | ❌ scale=1 返回空 | 5m/15m/30m/60m **5000 根**（5m≈20交易日、60m≈1.4年） | 直连可用；datalen≥10000 返回 5001 根封顶；**不支持 1m** |
| **腾讯 mkline** | `ifzq.gtimg.cn/appstock/app/kline/mkline?param=sh000001,m1,,N` | ✅ | **800 根** ≈3.3 交易日 | count=800 是最大值；**count>800 反常回退 320 根**；无 start/end 参数 |
| 腾讯 fqkline | `web.ifzq.gtimg.cn/appstock/app/fqkline/get` | ❌ m1 返回 0 | day 支持起止日期 | 日线可用；分钟周期不支持 |
| 东财 push2his | `push2his.eastmoney.com/api/qt/stock/kline/get`（klt=1, beg/end） | ✅ 理论 | 深 | 本机网络层被断：直连 RemoteDisconnected、代理 ProxyError、数字前缀镜像(1./21.)也断 → 不可用，勿反复重试 |
| baostock | `query_history_k_data_plus`（frequency=5/15/30/60） | 文档未支持 1 | — | 本机登录连不上服务器（login 超时/Broken pipe）；代码格式 sh.000001；需 login()，进程只 login 一次 |
| 搜狐 hisHq | `q.stock.sohu.com/hisHq`（code=zs_000001） | — | — | period=1/1m/60 均不支持（"period type non-existent" / 503） |
| **Ashare** | mpquant/Ashare 单文件库（GitHub 直下，不在 PyPI；PyPI 的 ashares 是第三方封装） | ✅ | = 底层源上限 | 1m 走腾讯 mkline(800)，5m+ 走新浪老接口(5000)，日线走新浪 240m/腾讯 fqkline；双内核自动切换；**无超越底层源的能力** |

## 关键结论

1. **指数 1m 免费天花板 ≈ 1023 根**（新浪新接口），腾讯 800 根次之；免费源都共享这两个底层源，突破不了。
2. 指数 1m 要更久历史：**每日增量累积**（每天收盘拉最新 1023 根 upsert 进库，跑一个月 = 一个月历史）——正是现有 sync_bars 增量模式，零新代码。
3. 5m+ 深度提升：改用新浪老接口一次拿 5000 根（5m≈20交易日、60m≈1.4年），比新接口深 5 倍。落地方案：sina_index_source.py 中 5m+ 切老接口、1m 保持新接口。
4. **Ashare 无魔法**——封装腾讯 + 新浪老接口，1m 上限反而低于新浪新接口。要"试试某行情库"时先看它底层封装的源，再决定是否值得装。
5. 时间戳语义：新浪新旧接口 + 腾讯 mkline 均返回 bar **结束**时间（15:00 收盘），与 vnpy 天然一致，无需 +1min 对齐。

## QuantDash 评估结论（用户转来的腾讯云文章方案）

- 腾讯云开发者社区**商业软文**：同一作者 46 篇文章全是推广 QuantDash；商业 SaaS 需注册 API key（quantdash.net/dashboard/keys/）。
- 文档只覆盖 A股/美股/港股**个股**分钟线（1m/5m/15m/30m/60m），**全文无指数示例、无指数支持证据**。
- GitHub 仓库存疑：`jakobildstad/QuantDash` 是本地回测平台（React+FastAPI），与文章宣称的 quantdash-net 组织不符。
- 结论：不采用。商业软文 + 无指数证据 + 开源仓库存疑，不符合"只用成熟开源、只写适配层"原则。

## 方法论备忘

用户评估数据源提案时，期望把**所有候选免费源都实测一遍**（如"还有 baostock, ashare 都试一下"），而不是只评估文章方案本身——实测矩阵比文章结论更有价值。命名注意：`ashare` ≠ `akshare`，前者是 mpquant/Ashare 单文件库。
