---
name: buffett
description: "巴菲特投资分析框架：股票筛选、护城河评估、买卖决策、持有/卖出检验。当用户问'该不该买/卖/持有某股票'、'分析一下XX'、'护城河/估值/管理层'时触发"
metadata:
  openclaw:
    emoji: "🧠"
    requires:
      bins: ["maybe"]
      env: ["MAYBE_API_KEY"]
---

# 巴菲特投资分析框架

基于巴菲特 70 年投资智慧构建的结构化分析体系：快速筛选 → 深度分析 → 决策输出。

## Hard Rules

- **NEVER fabricate financial data.** 持仓和价格数据必须来自 `maybe` CLI 输出。
- **ALWAYS collect real data first.** 分析前先拉取持仓和价格数据。
- **NEVER give investment advice without analysis.** 每个结论必须有分析支撑。
- **read reference files before analysis.** 使用 Read 工具读取 `{baseDir}/references/xxx.md`，不可仅凭内置知识分析。

## When NOT to Use

- 用户要查余额、看持仓 → use `finance-read`
- 用户要记账、转账、更新余额 → use `finance-write`
- 用户要查当前股价、K线 → use `yfinance`
- 用户要回忆投资教训、决策复盘 → use `finance-memory`
- 用户要宏观经济早报 → use `macro-info-collector`

## 数据收集（分析前必做）

分析任何股票前，先拉取真实数据：

```bash
# 1. 查看用户持仓（找到相关股票的持仓信息）
maybe accounts --json
maybe holding list --account "<account_name>" --json

# 2. 查询当前股价
maybe quote <TICKER>

# 3. 如果分析已有持仓，计算盈亏
# 持仓成本 → from holding list output
# 当前价格 → from maybe quote
# 盈亏 = (当前价 - 成本价) × 持仓量
```

将收集到的数据填入分析框架，而非凭空假设。

---

## 分析路径

根据用户问题类型选择路径：

### 路径 A · 快速筛选（2 分钟）

> "这只股票值得深入分析吗？"

直接用 8 问检查表，无需读取参考文件。两个 "否" 需要强力理由；四个 "否" 直接放弃。

| # | 维度 | 问题 | 否 = 红旗 |
|---|------|------|-----------|
| 1 | **能力圈** | 我能用一段话解释这家公司怎么赚钱吗？ | 不能 = 圈外 |
| 2 | **持久性** | 10 年后这家公司还在且更强吗？ | 否 = 技术颠覆风险 |
| 3 | **护城河** | 竞争对手投入重金能复制其核心优势吗？ | 能 = 无护城河 |
| 4 | **定价权** | 能涨价 5-10% 而不流失大量客户吗？ | 否 = 大宗商品型生意 |
| 5 | **盈利质量** | 利润能真正转化为现金吗？ | 否 = 盈利质量存疑 |
| 6 | **负债安全** | 行业最差情景（营收 -30%）下能存活吗？ | 否 = 杠杆风险 |
| 7 | **管理层诚信** | 管理层诚实面对问题还是掩盖？ | 否 = 一票否决 |
| 8 | **合理价格** | 当前价格与内在价值的差距够大吗？ | 否 = 等待或放弃 |

> 诚信（Q7）是一票否决——其他都好也不行。

### 路径 B · 深度分析

> "完整评估这家公司"

按顺序读取参考文件：

```
必读（按序）:
  {baseDir}/references/03-business-moat.md         ← 护城河/商业模式/商誉
  {baseDir}/references/04-management-governance.md  ← 管理层/文化/治理
  {baseDir}/references/05-financial-metrics.md     ← 财务指标/所有者收益
  {baseDir}/references/06-valuation-capital.md      ← 估值/安全边际/资本配置

按需补充:
  {baseDir}/references/08-industry-playbooks.md     ← 识别行业后读对应章节
  {baseDir}/references/07-risk-behavior.md         ← 有杠杆/衍生品/价值陷阱担忧时
```

### 路径 C · 持有/卖出决策

> "该不该继续持有？" / "要不要卖？"

**必须读取** `{baseDir}/references/07-risk-behavior.md`，按四条卖出标准逐条检验：

| # | 卖出标准 | 判断 |
|---|---------|------|
| 1 | 价格严重高估？ | [是/否 + 依据] |
| 2 | 护城河被根本性破坏？ | [是/否 + 依据] |
| 3 | 管理层出现诚信问题？ | [是/否 + 依据；如是→立即卖出] |
| 4 | 有更好的投资机会？ | [是/否 + 依据] |

四条均为"否" → 继续持有。

### 路径 D · 专题问题

> 用户问某个具体概念

| 用户问… | 读取 |
|---------|------|
| 护城河/品牌/商誉 | `{baseDir}/references/03-business-moat.md` |
| 管理层/诚信/制度迫力 | `{baseDir}/references/04-management-governance.md` |
| 财报/ROIC/所有者收益 | `{baseDir}/references/05-financial-metrics.md` |
| 估值/安全边际/回购/分红 | `{baseDir}/references/06-valuation-capital.md` |
| 复利/内在价值/集中投资 | `{baseDir}/references/02-investment-philosophy.md` |
| 能力圈/逆向思维/市场先生 | `{baseDir}/references/01-thinking-frameworks.md` |
| 某个行业（保险/银行/科技等） | `{baseDir}/references/08-industry-playbooks.md` 对应章节 |

---

## 输出格式

### 飞书精简输出（默认）

适合聊天场景，4 节即可：

```
## 结论
[买入 / 不买 / 继续观察 / 持有 / 卖出] — 一句话核心理由

## 关键数据
- 当前价：$XX（来自 maybe quote）
- 持仓：XX 股 @ $XX 成本（来自 maybe holding list）
- 盈亏：+$XX (+X.X%)

## 分析要点
- 护城河：[类型] + [强/中/弱] + [拓宽/稳定/收窄]
- 管理层：[诚信评级] / [资本配置评级]
- 财务：ROIC XX% / 现金转化率 XX%
- 估值：内在价值区间 $XX-$XX，安全边际 XX%

## 卖出标准检验（持有/卖出场景必输出）
1. 价格严重高估？[是/否 + 依据]
2. 护城河破坏？[是/否 + 依据]
3. 管理层诚信问题？[是/否 + 依据]
4. 更好的机会？[是/否 + 依据]

## 主要风险（最多 3 条）
1. ...
2. ...
3. ...

## 监控指标
- 每季度检查：...
- 触发卖出信号：...
```

### 完整输出（用户要求"详细分析"时）

补充能力圈判断、关键假设（3-5 条）、综合判断，使用完整 10 节格式。读取所有必读参考文件后输出。
