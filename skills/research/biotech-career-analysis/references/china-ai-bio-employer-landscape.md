# Chinese AI-bio / computational-biology employers, by city

Use when the user asks "which companies doing <field> have a base in city X" (usually as a
job-search input). This file is the *method* plus a verified inventory as of 2026-09; extend the
inventory rather than creating a new file per city.

## Method (order matters)

1. **Search in Chinese, by capability not by buzzword**: `<城市> AI制药`, `<城市> 计算生物学 公司`,
   `<城市> 蛋白质设计 招聘`, `<城市> 生物信息 公司 招聘`. Add `<城市> AI for Science` to catch
   materials/chemistry-adjacent companies the user may still want.
2. **Verify the legal entity, not the brand.** Search hits give 工商全称 + 注册地址 (企查查/爱企查
   blocks appear in plain web results). A brand name is not a location.
3. **Distinguish parent from site.** A city entry can be a *research center or subsidiary* of a
   company headquartered elsewhere (e.g. 杭州剂泰生命科技 = 北京剂泰的杭州研发中心;
   深势（杭州）科技 = 深势科技子公司). Both are legitimate answers — say which one it is.
4. **Split companies from research institutes.** Institutes (国家实验室/省实验室/大学/中科院所/企业
   研究院) hire PhDs and postdocs with published 待遇 numbers and are often the best fit for a
   method-development direction, but they are not companies — list them in a separate block.
5. **Record negative findings explicitly** — which famous names have NO base there. This is
   usually the most time-saving part of the answer.
6. **Postings go stale.** A hiring-platform snippet (猎聘/BOSS直聘) is a weak signal; the company
   site's 加入我们/招聘官网 and the 事业单位 job boards (高校人才网/国聘) are current. Label each
   row by evidence strength and say plainly that hiring status was not re-verified row by row.

## Traps

- **Same-name unrelated company.** A search for a well-known AI-pharma brand can return a local
  electronics firm with the same characters (e.g. 杭州晶泰电子科技有限公司 ≠ 晶泰科技). Check 工商全称.
- **Grouping by company name hides the work nature.** Sort by what the site actually computes:
  AI-pharma platforms (small molecule), AI4Bio molecular design (protein/nucleic acid), synbio +
  computational enzyme engineering, omics/bioinformatics services, medical-imaging AI. A protein
  person's fit differs sharply across these five buckets.
- **Do not infer lab direction from the PI name alone** — confirm via the group's own site/page.

## Hangzhou inventory (verified 2026-09)

Companies, computational/synbio core with dry-wet loop:

| Name | Site | Focus |
|------|------|-------|
| 恩和科技 / Bota Bio | 杭州医药港·和达药谷4期22幢（钱塘区） | dedicated "计算生物学" team + Biofoundry; enzyme engineering, SAION AI physical-AI platform |
| 英灵殿科技（杭州） | 西湖区三墩镇浙滨西源大厦（浙大紫金港旁） | Baker Lab founders; AlloDesign multimodal molecular design; own high-throughput wet lab |
| 力文所 Levinthal | 萧山区宁围街道金帝·新道蓝谷1幢2层 | AI co-evolution-driven protein design |
| 德睿智药 MindRank | 钱塘区白杨街道科技园路2号 | AI pharma; Molecule Pro + Molecule Dance (protein dynamics) |

AI-pharma / platform companies: 剂泰科技（杭州剂泰生命科技，滨江，AI 纳米递送，北京剂泰研发中心）｜
碳硅智慧（浙大侯廷军组衍生，DrugFlow/BioFlow，电话 0571 段）｜高维医药（余杭，高维生物学+AI 药物设计，
小分子与蛋白质药物）｜生奥信息 SanOmics（AI 制药软件）｜晨伫科技（计算生物学+AI 药物设计）｜
深势（杭州）科技（AI4S 子公司）｜深度原理 Deep Principle（滨江/萧山，AI for Chemistry/Materials —
不是生物，但同属 AI4S）。

Omics / bioinformatics services: 景杰生物（钱塘区乔新路500号医药港小镇二期8号楼，蛋白质组学 + 生物信息与
人工智能平台，招生信分析科学家）｜西湖欧米 Westlake Omics（西湖区转塘云梦路1号3幢，郭天南创立，
AI 蛋白质组学）｜联川生物（测序+生信服务）｜星源未来（原瑞普基因，精准医疗+AI 大数据）。

Medical-imaging AI / molecular diagnostics: 迪英加科技（余杭仓前，AI+病理）｜德适生物（02526.HK，
染色体核型 AI + 医学影像大模型）｜健培科技（钱塘）｜杰毅生物（mNGS）｜杭州艾普佳臻（在招生信工程师）。

Research institutes (separate track, hire PhDs/postdocs): 之江实验室·生命科学计算研究中心
（余杭文一西路2880号；蛋白语言模型、基因组基础模型）｜西湖大学/西湖实验室（卢培龙蛋白质设计实验室；
西湖人工智能药物设计核心实验室；工学院 AI-BT-Chem 酶工程）｜良渚实验室（浙大，余杭文一西路1369号）｜
中科院杭州医学研究所（医学人工智能中心）｜浙江大学智能创新药物研究院（钱塘）｜浙大杭州国际科创中心
（萧山建设三路733号）｜杭州华大生命科学研究院（紫金港科技城）｜阿里达摩院（基因智能/AI for Science）。

Negative findings: 晶泰科技、深势科技总部、分子之心、百图生科、英矽智能 — no Hangzhou base at time
of check.
