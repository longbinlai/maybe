# Weekly Review Template

## Trigger
Every Sunday 20:00 via cron job.

## Steps

1. **Query Maybe for this week's performance:**
   ```bash
   maybe snapshot --json
   maybe trades --json
   ```

2. **Query Mem0 for this week's decisions:**
   ```bash
   memory list -c investment_decision
   ```

3. **Analyze:**
   - Which decisions are working (positive P&L)
   - Which decisions aren't (negative P&L)
   - Extract lessons

4. **Write to Mem0:**
   ```bash
   memory add -c weekly_review \
     --content "本周组合 +X.X%，主要贡献来自...。经验：..." \
     -m week=<YYYY-WW> \
     -m portfolio_change=<+X.X%> \
     -m decisions_count=<N> \
     -m lessons="<key takeaways>"
   ```

5. **Push summary to Feishu** (if configured)
