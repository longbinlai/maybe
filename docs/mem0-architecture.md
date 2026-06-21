# Mem0 Memory Architecture - Final State

## Core Principle: Clear Separation of Concerns

**Maybe Finance = Single Source of Truth for ALL objective financial data**
- Current and historical account balances
- Net worth (time series)
- Holdings and positions (with cost basis, current prices)
- Transaction records (all buys/sells with dates/prices)
- Exchange rates (current and historical)
- Asset/liability analysis

**Mem0 = Subjective wisdom that Maybe cannot capture**
- Decision reasoning (WHY we bought/sold)
- Lessons learned (what worked, what didn't)
- Investment preferences and style
- Behavioral patterns
- Family goals and milestones
- Reviews and reflections

## Memory Cleanup Results

### Before Cleanup (27 memories)
- ❌ 16 objective financial data memories (account balances, net worth, holdings)
- ❌ 6 system configuration memories (tech stack, cron jobs, etc.)
- ⚠️ 5 investment preferences (wrong category: allocation_strategy)

### After Cleanup (5 memories)
- ✅ 5 pure subjective wisdom memories (investment_style category)
  1. Conservative risk preference with target allocation
  2. Single securities constraint (<15% of portfolio)
  3. Feishu push notification levels (urgent/noteworthy/etc.)
  4. 5 alert trigger conditions (allocation drift, market moves, etc.)
  5. Silent rules (intraday <1%, only high-relevance news)

## Active Memory Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| `investment_decision` | WHY we bought/sold, context, expectations | "Bought Tencent because AI business strong, expect +15% in 90d, confidence 7/10" |
| `lesson_learned` | What worked, what didn't, takeaways | "Reducing tech stocks during Fed hawkish signals avoided 12% drawdown" |
| `market_view` | Opinions on markets, sectors, trends | "Long-term bullish on A-shares, HK stocks at historical lows" |
| `investment_style` | Risk tolerance, preferences, patterns | "Conservative style, don't like frequent trading, tend to add on dips" |
| `family_goal` | Long-term objectives and milestones | "Save 2M for education in 3 years, current progress 78%" |
| `weekly_review` | Weekly portfolio analysis | "This week +2.3%, Tencent decision +3.2% unrealized gain" |
| `monthly_review` | Monthly deep analysis | "This month +5.2%, decision success rate 67%, increase fixed income" |

## Deprecated Categories (Do NOT Use)

- ❌ `portfolio_insight` - Was storing objective data, use Maybe instead
- ❌ `allocation_strategy` - Was storing policy rules, now migrated to investment_style
- ❌ `market_event` - Was storing market data, use DataHub instead

## Data Source Priority Rules

### When to Query Maybe (Real-time Data)
- "现在有多少钱" → `maybe snapshot`
- "账户余额" → `maybe accounts`
- "持仓情况" → `maybe holdings`
- "今天金价/汇率/股价" → `yf quote` / `maybe exchange-rates`
- "交易记录" → `maybe trades`
- "历史持仓变化" → `maybe trades` (Maybe has full history)

### When to Query Mem0 (Subjective Wisdom)
- "上次买腾讯的理由是什么" → `memory search -c investment_decision -q "腾讯 买入"`
- "我的投资风格是什么" → `memory search -c investment_style`
- "美联储加息时我们怎么应对的" → `memory search -c lesson_learned -q "美联储 加息"`
- "上周的投资回顾" → `memory list -c weekly_review`
- "有什么经验教训" → `memory list -c lesson_learned`

### When to Combine Both
- "我们的组合有什么变化" → Maybe 取当前持仓 + Mem0 取上次决策背景
- "这次操作和上次有什么不同" → Maybe 取当前交易 + Mem0 取历史决策理由
- "本月表现如何" → Maybe 取收益数据 + Mem0 取月度回顾分析

### ❌ Never Do This
- ❌ Use Mem0 to answer "现在有多少钱" (use Maybe)
- ❌ Store "腾讯持有100股，成本价380" in Mem0 (Maybe has this)
- ❌ Store "净资产 $1,457,274" in Mem0 (Maybe has this)
- ❌ Store "USD/CNY 是 7.24" in Mem0 (Maybe/DataHub has this)

## Architecture Diagram

```
User Query: "我们家现在有多少钱？"
                ↓
        Analyze Intent
                ↓
        ┌───────────────┐
        │ Objective?    │ → YES → Query Maybe Finance
        │ (balances,    │         → "Net worth: $1,457,274"
        │  holdings,    │
        │  net worth)   │
        └───────────────┘
        
User Query: "上次买腾讯的理由是什么？"
                ↓
        Analyze Intent
                ↓
        ┌───────────────┐
        │ Subjective?   │ → YES → Query Mem0
        │ (reasons,     │         → "Bought because AI business strong,
        │  lessons,     │            expect +15% in 90d, confidence 7/10"
        │  style)       │
        └───────────────┘
```

## Golden Rule

**If Maybe can answer it, don't store it in Mem0.**

Mem0 is for the wisdom that Maybe cannot capture:
- The **why** behind decisions
- The **lessons** from experience
- The **preferences** that guide behavior
- The **goals** that drive actions
- The **reflections** that improve future decisions

## Files Updated

1. ✅ `tools/openclaw-skills/family-investment/SKILL.md` - Complete rewrite with clear separation
2. ✅ `tools/openclaw-skills/maybe/SKILL.md` - Added Data Source Priority section
3. ✅ `tools/mem0-memory/cleanup_objective_data.py` - Delete 16 objective data memories
4. ✅ `tools/mem0-memory/cleanup_system_config.py` - Delete 6 system config memories
5. ✅ `tools/mem0-memory/recategorize_memories.py` - Migrate allocation_strategy → investment_style

## Next Steps

1. **Add first investment decision**: Next time user buys/sells, record the reasoning in Mem0
2. **Weekly review**: Set up cron job to generate weekly_review memories
3. **Lesson extraction**: When user reflects on decisions, extract lessons
4. **Family goals**: Ask user about long-term objectives and record them
5. **Monthly review**: Set up cron job for monthly deep analysis

## Verification Commands

```bash
# Check total memories
memory list

# Search by category
memory search -c investment_style
memory search -c investment_decision
memory search -c lesson_learned

# Search by keyword
memory search -q "腾讯 买入"
memory search -q "投资风格"

# Query Maybe for real-time data
maybe snapshot
maybe holdings
maybe accounts
```
