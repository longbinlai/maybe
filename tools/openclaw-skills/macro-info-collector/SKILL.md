---
name: macro-info-collector
description: "收集和整理宏观经济信息，生成清晰的信息摘要并推送到飞书。不做投资建议，只做信息展示。"
metadata:
  {
    "openclaw":
      {
        "emoji": "📈",
        "requires": { "bins": ["python3"], "env": [] },
        "install":
          [
            {
              "id": "datahub-dep",
              "kind": "shell",
              "command": "cd /Users/longbinlai/Documents/git/maybe/tools/datahub && pip install -e .",
              "label": "Install DataHub dependency",
            },
          ],
      },
  }
---

# Macro Info Collector

收集和整理宏观经济信息，生成清晰易读的信息摘要，通过飞书推送。

**重要：这是一个信息收集工具，不是投资顾问。**

## 核心理念

- ✅ **做什么**：收集、整理、展示宏观经济信息
- ❌ **不做什么**：提供投资建议、判断经济周期、推荐资产配置

## 信息展示原则

1. **客观数据**：展示原始数据，不做主观判断
2. **趋势对比**：显示变化趋势（日/周/月对比）
3. **关键指标**：突出最重要的指标
4. **易于阅读**：简洁、结构化、一目了然
5. **保留元数据**：**必须保留每条信息的来源和原始链接**

## 翻译和整理规则（重要）

当处理新闻信息时，**必须遵守以下规则**：

### ✅ 必须保留的信息
- **信息源名称**（如：美联储、ForexLive、OilPrice、南华早报等）
- **原始链接**（完整的 URL）
- **日期信息**（新闻发布日期）
- **摘要**（如果有）

### ✅ 可以做的操作
- 翻译新闻标题（英文→中文）
- 整理格式（添加 emoji、分隔符等）
- 分类汇总（按主题分组）
- 添加趋势说明（↑↓→）

### ❌ 禁止的操作
- **不得删除来源信息**
- **不得删除原始链接**
- **不得简化掉链接**（如"详见原文"）
- **不得合并多条新闻时丢失元数据**

### 📝 正确的格式示例

```
1. [05/24] 美联储5月会议纪要显示官员对通胀表示担忧
   来源：美联储
   链接：https://www.federalreserve.gov/monetarypolicy/files/...
   摘要：多位官员认为当前利率水平可能维持更长时间...

2. [05/24] 美元兑日元升至158.50，创34年新高
   来源：ForexLive
   链接：https://www.forexlive.com/news/usdjpy-rises-to-15850...
```

### ❌ 错误的格式示例（不要这样做）

```
1. 美联储官员对通胀表示担忧
   （缺少：日期、来源、链接）

2. 美元兑日元创34年新高
   （缺少：日期、来源、链接、具体数值）
```

## 记忆管理规则（重要）

本工具收集的信息必须写入 MEMORY.md，以便后续分析和决策。

### 每日早报流程

当执行每日早报（每天 8:00）时：

1. **收集宏观新闻**
   - 运行 `collect_macro_info.py`
   - 获取过去 24 小时的重要新闻

2. **写入 MEMORY.md**
   - 追加到 `## 市场事件` 部分
   - 使用 MEMORY.md 中定义的标准模板格式
   - 每条事件必须包含：类别、市场、关键数据、情绪、影响板块、相关性、来源、链接
   - **状态** 设为 `monitoring`（等待观察）

3. **生成早报**
   - 翻译新闻标题
   - 整理格式（添加 emoji、分隔符）
   - **保留所有元数据**（来源、链接、日期）
   - **不给操作建议**，只展示客观信息

4. **推送到飞书**
   - 使用飞书机器人推送
   - 格式清晰易读

### 示例：写入 MEMORY.md

```markdown
### 2026-05-26: 美联储加息 50bp
- **类别**: policy
- **市场**: 债券、股票、美元
- **关键数据**: 加息 50bp（预期 25bp）
- **情绪**: hawkish
- **影响板块**: bonds, growth_stocks, real_estate
- **相关性**: high
- **来源**: 美联储
- **链接**: https://www.federalreserve.gov/...
- **我们的行动**: 无（等待观察）
- **状态**: monitoring
```

### 示例：生成早报

```
📈 宏观经济早报 - 2026-05-26

【重要事件】
🔴 美联储加息 50bp（超出预期，预期 25bp）
   来源：美联储
   链接：https://www.federalreserve.gov/...
🟡 鲍威尔讲话：通胀仍需控制，未来可能继续加息
   来源：美联储
   链接：https://www.federalreserve.gov/...

【你的持仓影响】
⚠️ TLT（债券ETF）：可能下跌 3-5%
⚠️ VNQ（房地产ETF）：可能下跌 2-3%
🟢 GLD（黄金ETF）：可能上涨 2-4%

【历史参考】
• 2024-03-15（加息50bp）：债券下跌3.2%，黄金上涨5.1%
• 2023-07-20（加息25bp）：债券下跌1.8%，黄金上涨2.3%

周日晚上的周度回顾将给出具体操作建议。
```

### 周度回顾流程（每周日 20:00）

当执行周度回顾时：

1. **从 MEMORY.md 提取本周事件**
   - 搜索 `## 市场事件` 中本周的记录
   - 汇总宏观环境变化

2. **从 MEMORY.md 提取本周操作**
   - 搜索 `## 决策记录` 中本周的记录
   - 评估决策质量和结果

3. **生成投资建议**
   - 基于本周新闻和操作
   - 给出具体的操作建议（买/卖/持有）
   - 解释原因和预期影响

4. **写入 MEMORY.md**
   - 追加到 `## 周度回顾` 部分
   - 使用标准模板格式

5. **推送到飞书**

### 月度分析流程（每月 1 日 20:00）

当执行月度分析时：

1. **从 MEMORY.md 提取本月 4 次周度回顾**
   - 搜索 `## 周度回顾` 中本月的记录
   - 汇总本月表现

2. **分析长期趋势**
   - 从 `## 投资洞察` 提取历史规律
   - 分析宏观环境长期趋势
   - 识别结构性变化

3. **生成策略调整建议**
   - 基于长期趋势和历史教训
   - 给出资产配置调整建议
   - 给出风险管理优化建议

4. **写入 MEMORY.md**
   - 追加到 `## 月度分析` 部分
   - 如果有新的投资洞察，追加到 `## 投资洞察` 部分

5. **推送到飞书**

---

## 报告格式示例

```
📈 宏观经济信息摘要 - 2026-05-24

═══════════════════════════════════════
📊 关键指标
═══════════════════════════════════════

美国利率
  联邦基金利率：5.50% (↑ 0.25% vs 上月)
  10年期国债：4.25% (↓ 0.10% vs 上周)

汇率
  美元/人民币：7.14 (↓ 0.02 vs 昨日)
  美元/日元：156.80 (↑ 1.20 vs 昨日)
  美元/澳元：1.52 (→ 持平 vs 昨日)

大宗商品
  黄金：$3,275/oz (↑ $45 vs 上周, +1.4%)
  原油：$78.50/bbl (↓ $2.30 vs 上周, -2.8%)

═══════════════════════════════════════
📰 近期重要动态
═══════════════════════════════════════

【美联储政策】
1. [05/24] 美联储5月会议纪要显示官员对通胀表示担忧
   来源：美联储
   链接：https://www.federalreserve.gov/monetarypolicy/files/fomcminutes20260501.pdf
   
2. [05/23] 美联储暗示年内可能降息1-2次
   来源：美联储
   链接：https://www.federalreserve.gov/newsevents/speech/powell20260523a.htm

【中国经济】
3. [05/24] 5月PMI：50.2（略高于荣枯线）
   来源：南华早报
   链接：https://www.scmp.com/economy/china-economy/article/3312456/china-may-pmi
   
4. [05/23] 出口同比增长7.6%
   来源：南华早报
   链接：https://www.scmp.com/economy/china-economy/article/3312389/china-exports-may

【市场动态】
5. [05/24] 美元兑日元升至158.50，创34年新高
   来源：ForexLive
   链接：https://www.forexlive.com/news/usdjpy-rises-to-15850-34-year-high

6. [05/23] 原油价格下跌，OPEC+考虑增产
   来源：OilPrice
   链接：https://oilprice.com/Energy/Crude-Oil/OPEC-Considers-Production-Increase.html

【市场情绪】
7. [05/24] VIX恐慌指数：14.2（低位）
   来源：市场新闻
   链接：https://finance.yahoo.com/quote/^VIX
   
8. [05/24] 美元指数：104.5（稳定）
   来源：ForexLive
   链接：https://www.forexlive.com/news/dollar-index-stable-at-1045

═══════════════════════════════════════
📅 下周关注
═══════════════════════════════════════

  • 5/28 美国4月PCE物价指数
  • 5/30 美国第一季度GDP修正值
  • 6/1  中国5月官方PMI
```

## When to Use

Use when:

- 用户问"最近宏观经济怎么样"
- 用户想看"最新的市场数据"
- 用户要求"整理一下经济形势"
- 定时任务推送每日/每周信息摘要
- 用户要求"发送到飞书"

## When NOT to Use

Do not use when:

- 用户要求投资建议 → 明确说明"我不提供投资建议"
- 用户要求判断经济周期 → 只提供数据，不做判断
- 用户要求推荐资产配置 → 明确说明"这是个人决策"
- 用户要求预测市场走势 → 明确说明"无法预测"

## Hard Rules

- **永远不提供投资建议**：只展示信息，不说"应该买/卖"
- **永远不判断经济周期**：不输出"现在是扩张期/衰退期"
- **永远不推荐资产配置**：不说"建议增加股票/减少债券"
- **永远不预测市场**：不说"市场即将上涨/下跌"
- **数据必须准确**：如果数据源失败，明确报告错误
- **保持客观中立**：使用中性语言，避免主观判断

## Command Reference

### 收集和整理信息

```bash
# 收集所有宏观经济数据
python3 scripts/collect_macro_info.py

# 生成信息摘要（不发送）
python3 scripts/collect_macro_info.py --summary

# 生成并发送到飞书
python3 scripts/collect_macro_info.py --send-feishu

# 只收集特定类别
python3 scripts/collect_macro_info.py --category rates
python3 scripts/collect_macro_info.py --category fx
python3 scripts/collect_macro_info.py --category commodities
python3 scripts/collect_macro_info.py --category news
```

### 定时任务

```bash
# 每日早报（工作日 8:00）
openclaw cron add \
  --name "macro-daily-briefing" \
  --schedule "0 8 * * 1-5" \
  --command "python3 scripts/collect_macro_info.py --send-feishu" \
  --description "每日宏观经济信息摘要"

# 每周总结（周五 17:00）
openclaw cron add \
  --name "macro-weekly-summary" \
  --schedule "0 17 * * 5" \
  --command "python3 scripts/collect_macro_info.py --weekly --send-feishu" \
  --description "每周宏观经济信息总结"
```

## Data Sources

通过 DataHub 收集以下数据：

### 利率数据
- 美联储利率决议 (Federal Reserve RSS)
- 欧洲央行利率决议 (ECB RSS)
- 日本央行利率决议 (BOJ RSS)
- 美国国债收益率 (YFinance)

### 汇率数据
- 美元/人民币 (YFinance: USDCNY=X)
- 美元/日元 (YFinance: USDJPY=X)
- 美元/澳元 (YFinance: USDAUD=X)
- 欧元/美元 (YFinance: EURUSD=X)

### 大宗商品
- 黄金 (YFinance: GC=F)
- 原油 (YFinance: CL=F)
- 铜 (YFinance: HG=F)

### 经济指标
- GDP 增长率 (BEA RSS)
- CPI 通胀率 (BLS RSS)
- 失业率 (BLS RSS)
- PMI (新闻源)

### 市场动态
- 股指 (YFinance: ^GSPC, ^DJI, ^IXIC, 000001.SS)
- 新闻 (RSS feeds)

## Workflow

### 每日信息摘要

```bash
# 1. 收集数据（自动缓存）
python3 scripts/collect_macro_info.py

# 2. 生成摘要
python3 scripts/collect_macro_info.py --summary

# 3. 发送到飞书
python3 scripts/collect_macro_info.py --send-feishu
```

### 用户请求信息

用户："最近宏观经济怎么样？"

```bash
# 1. 收集最新数据
python3 scripts/collect_macro_info.py

# 2. 生成摘要并展示
python3 scripts/collect_macro_info.py --summary
```

然后回复：
```
这是最新的宏观经济信息：

[显示信息摘要]

请注意：这是信息展示，不是投资建议。具体决策请结合个人情况。
```

### 定时推送

配置 cron 任务后，系统会自动：
1. 每天 8:00 收集数据
2. 生成信息摘要
3. 推送到飞书

## Error Handling

| Error | Cause | Action |
|---|---|---|
| DataHub 连接失败 | 数据源不可用 | 报告错误，使用缓存数据（如果有） |
| 飞书发送失败 | 配置错误 | 报告错误，建议检查配置 |
| 数据缺失 | 某些数据源无数据 | 在报告中明确标注"暂无数据" |
| 网络超时 | 网络问题 | 重试一次，仍失败则报告错误 |

## Configuration

### 飞书配置

在 `config/feishu.yaml` 中配置：

```yaml
feishu:
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
  # 或使用飞书机器人 API
  app_id: "cli_xxx"
  app_secret: "xxx"
  chat_id: "oc_xxx"
```

### 数据源配置

使用 DataHub 的配置文件：
`/Users/longbinlai/Documents/git/maybe/tools/datahub/config/sources.yaml`

## 与 Maybe Finance 的关系

这个 skill 专注于**宏观经济信息**，而 `maybe` skill 专注于**家庭财务数据**。

两者可以配合使用：
- `macro-info-collector`：外部环境信息
- `maybe`：内部财务状况

用户可以根据这两方面信息，自己做出决策。

## 设计哲学

> "好的工具提供清晰的信息，让人类做出明智的决策。"

我们相信：
1. 人类比算法更擅长复杂的财务决策
2. 清晰的信息比自动化的建议更有价值
3. 客观的数据比主观的判断更可靠

因此，我们：
- ✅ 收集全面的数据
- ✅ 整理成易读的格式
- ✅ 突出关键信息
- ❌ 不做投资建议
- ❌ 不判断经济周期
- ❌ 不推荐资产配置
