# Transaction Recording Workflow

## Overview

When user describes a financial event (buy, sell, interest received, salary, etc.), create a transaction in Maybe Finance with auto-tagging.

## Flow

### Step 1 — Parse user input

Extract: account name, amount, transaction name, date (default: today), nature (income/expense).

### Step 2 — Query available tags

```bash
maybe tags --json
```

### Step 3 — Auto-match tag

Use the rules in `auto-tag-rules.md` to match the best tag based on transaction name and context.

### Step 4 — Create transaction

```bash
maybe add-transaction \
  -a "<account_name>" \
  -d "<date>" \
  -m <amount> \
  -n "<name>" \
  --tag "<tag1>" \
  --tag "<tag2>" \
  --nature <income|expense>
```

### Step 5 — Confirm

```
✅ 已创建交易:
   账户: 海外储蓄账户
   日期: 2026-06-20
   金额: 100
   名称: 银行利息
   标签: 利息 (自动匹配, 置信度: 95%)
   类型: income
```

## Transfers Between Accounts

When user describes a fund redemption or transfer:

```
User: "我从理财账户A中卖掉了价值为500000的基金，这笔钱会打到活期账户A"
```

Create TWO transactions:

```bash
# Outflow from source
maybe add-transaction -a "理财账户A" -d "2026-06-20" -m 500000 -n "基金赎回" --tag "投资" --nature expense

# Inflow to destination
maybe add-transaction -a "活期账户A" -d "2026-06-20" -m 500000 -n "基金赎回到账" --tag "投资" --nature income
```

## Low Confidence Handling

If auto-tag confidence < 70%:
- Create transaction WITHOUT tag
- Explain why: "交易名称过于通用，无法确定合适的标签"
- Suggest manual tagging
