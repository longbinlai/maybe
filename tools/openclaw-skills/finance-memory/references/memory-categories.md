# Memory Categories

## Active Categories

### investment_decision
Decision reasoning, context, expectations.
```bash
memory add -c investment_decision \
  --content "<why: reasoning, market context, expected outcome>" \
  -m security=<TICKER> -m direction=<buy|sell> -m confidence=<1-10> \
  -m expected_outcome="<target>" -m market_context="<conditions>"
```

### lesson_learned
What worked, what didn't, actionable takeaways.
```bash
memory add -c lesson_learned \
  --content "<what happened, what we learned, what to do next time>" \
  -m context="<trigger>" -m applicable_when="<conditions>"
```

### market_view
Opinions on markets, sectors, trends.
```bash
memory add -c market_view \
  --content "<view on specific market/sector/trend>"
```

### investment_style
Risk tolerance, preferences, behavioral patterns.
```bash
memory add -c investment_style \
  --content "<observation about investment behavior>"
```

### family_goal
Long-term objectives and milestones.
```bash
memory add -c family_goal \
  --content "<goal description, timeline, progress>" \
  -m goal_type=<education|retirement|house|travel|emergency> \
  -m target_amount=<amount> -m target_date=<YYYY-MM-DD>
```

### weekly_review
Weekly portfolio review. Generated every Sunday 20:00.

### monthly_review
Monthly deep analysis. Generated on 1st of each month 20:00.

## Deprecated Categories (Do NOT Use)

- `portfolio_insight` → Was storing objective data. Use Maybe instead.
- `allocation_strategy` → Was storing policy rules. Use family_policy.yaml instead.
- `market_event` → Was storing market data. Use DataHub instead.

## Golden Rule

**If Maybe can answer it, don't store it in Mem0.**

Mem0 is for: WHY we decided, WHAT we learned, HOW we behave.
Maybe is for: WHAT we own, HOW MUCH it's worth, WHEN we traded.
