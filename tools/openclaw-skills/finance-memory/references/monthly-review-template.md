# Monthly Review Template

## Trigger
1st of each month 20:00 via cron job.

## Steps

1. **Query all weekly reviews this month:**
   ```bash
   memory list -c weekly_review
   ```

2. **Query Maybe for monthly performance:**
   ```bash
   maybe balance-sheet --json
   maybe income-statement --start-date <month-start> --json
   maybe holdings --json
   ```

3. **Analyze:**
   - Decision success rate
   - Patterns and style observations
   - Strategy adjustments needed

4. **Write to Mem0:**
   ```bash
   memory add -c monthly_review \
     --content "本月整体+X.X%，跑赢/跑输基准。决策成功率XX%。风格观察：...。建议：..." \
     -m month=<YYYY-MM> \
     -m portfolio_change=<+X.X%> \
     -m decision_success_rate=<XX%> \
     -m style_observations="<insights>" \
     -m strategy_adjustments="<recommendations>"
   ```

5. **Push report to Feishu** (if configured)
