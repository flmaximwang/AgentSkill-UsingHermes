---
name: consumer-product-comparison
description: "Use when comparing 2+ consumer products by specs and price."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [consumer, product-comparison, price, evidence-tiering, chinese-ecommerce]
    related_skills: [web-content-extraction, blocked-page-recovery, grounded-citations]
---

# Consumer Product Comparison (2+ concrete models)

## When to Use

User names 2+ concrete models (品牌+型号, e.g. 「比较一下 A 和 B」) and wants to know which to buy. Applies to 家电 / 3C / 音频 / 桌面设备, and generalises to any spec-driven purchase decision.

Not for: monitoring one product's price over time (that's a price-watch job), or "what should I buy under ¥X" open-ended browsing — narrow the candidates first.

## Step 0 — 先定品类，再比参数

Before pulling any spec, classify each model's **品类定位** (便携电池款 vs 桌面插电款; 一体式 vs 转盘+功放; 小腔体 vs 书架箱). If the two sit in different classes, say so up front and re-frame the axes — a head-to-head "音质" verdict across classes misleads. The class difference belongs in the 一句话结论, not in a footnote.

## Step 1 — 品牌官网优先（唯一权威层）

Fetch the manufacturer's own domain first: it carries the authoritative spec table (尺寸/输出功率/蓝牙版本/接口/续航) and the official list price, often in USD too. Brand sites are JS-light and read cleanly with `web_extract`.
Then check whether the model line has revisions — 基础版 / MK2 / 升级款 / Pro / 不同颜色 SKU. Specs, battery and price differ per revision: always state which SKU the numbers belong to, or the conclusion will not match the unit the user actually buys.

## Step 2 — 实机长测（拿官方表格不给的东西）

Sources that earn trust: 什么值得买社区长测, B站实测/续航测试, chiphell 开箱长文, 知乎非 AI 长文。
They yield 喇叭单元尺寸与阻抗、解码/主控芯片型号、电池容量与实际续航、调音合作方、供电模式（是否边充边放）—— the details that decide real-world usability. One long hands-on review beats ten listicles.

## Step 3 — 电商元数据（尺寸/重量/在售 SKU）

京东移动端商品页的 `_itemInfo` JSON 给出 SKU、店铺与箱体尺寸/毛重 —— 那是**物流口径**，不是整机尺寸/净重，写进表格必须标口径。具体 URL、UA 与解析方法见 `web-content-extraction` → `references/china-ecommerce-spec-price-extraction.md`。

## Step 4 — 价格：带日期、分渠道

- 每个价格都带 **来源 + 日期**；分开写 挂牌价 / 到手价（国补、券、活动价常差 20–40%）。
- 跨渠道价差是常态（自营 vs 第三方 vs 海外官网 vs 台湾 momo NT$）。海外与台湾价**不能当大陆价**，只作横向参考。
- 实时价抓不到时明写"未能核实实时价"，只给带日期的数据点。**绝不用挂牌价冒充到手价。**

## Step 5 — 证据分级（必须写进答复）

1. 一手官方规格表 / 官方定价
2. 实机长测（可采信，非官方）
3. 百科/词条类（无来源 → 标"未获官方证实"）
4. AI 生成/聚合内容（知乎标注「疑似 AI 生成」、搜狐/网易「本文包含人工智能生成内容」）→ 只作定性参考
5. 抓不到实时价的项 → 明说

**冲突处理**：两个来源对同一参数给出不同数值时**并列报告冲突**，不取平均、不择一当结论（AI 横评的 频响曲线 与 功率 数字经常自相矛盾）。

## 输出形态（用户期望的形状）

中文行文，保留原始英文/品牌/型号名（Syitren R200、PANDA CD-67、SC6137D）；表格表头与单位用英文：

1. **一句话结论** — 先点出品类定位差异 + 各自卖点
2. **硬参数对照表** — 每行标注来源/口径（官方 / 实测 / 百科口径未证实 / 物流箱口径）
3. **2–4 个决定性差异**，Step 1→Step 2→Step 3 形式，每个差异带具体数字（W、mAh、mm、Hz、元），禁抽象空话
4. **价格一句话** + 版本差异（基础版 / MK2）
5. **证据分级与未证实项** — 明确列出"不要采信"的来源，以及本次未能核实的项
6. **下一步选项** — 存 Obsidian 笔记 / 深挖某个轴 / 挂价格监控

听感与参数分开陈述，听感必须标来源；不写"高端大气"式形容。

## Pitfalls

- 物流箱尺寸/毛重 ≠ 整机尺寸/净重 — 电商元数据只给前者，入表必须标口径。
- 同型号不同版本（基础版 / MK2）参数、电池、价格都不同 — 先确认在售 SKU，否则结论对不上用户要买的那台。
- 百科与 AI 横评的参数会互相矛盾 — 并列冲突报告，别择一、别平均。
- 别在价格接口上耗调用次数：京东价格走 JS/登录态，直接用带日期的行情稿或搜索摘要，并标注核验状态。
- 搜索摘要常含页面渲染后的价格文本，即使该页面 curl 被反爬 — 可引用，但要标"未实时核验"。
- 官方页常只给"输出功率"不给频响 — 频响数字若来自第三方，必须标注其证据等级。
- 品类差异（电池 vs 插电、便携 vs 桌面）比单一参数更决定满意度 — 结论里先说这个，再谈参数高低。
