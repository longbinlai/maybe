---
name: earnings-monitor
description: "财报自动监控：定时检查关注股票的财报发布情况，第一时间通知飞书群。用户说'关注XX财报'、'取消关注XX'、'财报关注列表'时触发"
metadata:
  openclaw:
    emoji: "📊"
    requires:
      bins: ["python3"]
      env: []
---

# 财报自动监控

定时检查关注股票的财报日历，财报发布后第一时间通知飞书群。

## 工作原理

1. **关注列表来源**：Maybe Finance 持仓自动同步 + 手动添加的额外股票
2. **检查方式**：yfinance 财报日历 + web search 确认
3. **通知格式**：OpenClaw 卡片（含 EPS、营收、净利润等关键数据）
4. **去重机制**：状态文件记录已通知的财报，避免重复发送

## 命令

### 定时检查（cron job 使用）

```bash
# 检查财报发布情况（安静模式，发布即通知飞书）
~/pyenv/maybe/bin/python3 ~/Documents/git/maybe/tools/openclaw-skills/earnings-monitor/scripts/earnings_monitor.py --quiet

# 包含财报预告（3天内的预告也通知）
~/pyenv/maybe/bin/python3 ~/Documents/git/maybe/tools/openclaw-skills/earnings-monitor/scripts/earnings_monitor.py --quiet --notify-upcoming
```

### 交互式管理

```bash
# 添加关注股票
~/pyenv/maybe/bin/python3 ~/Documents/git/maybe/tools/openclaw-skills/earnings-monitor/scripts/earnings_monitor.py add NFLX --name "Netflix"

# 移除关注（同时加入排除列表，防止 auto-sync 重新加入）
~/pyenv/maybe/bin/python3 ~/Documents/git/maybe/tools/openclaw-skills/earnings-monitor/scripts/earnings_monitor.py remove NFLX

# 查看关注列表
~/pyenv/maybe/bin/python3 ~/Documents/git/maybe/tools/openclaw-skills/earnings-monitor/scripts/earnings_monitor.py list
```

## 意图分类

| 用户说… | 动作 |
|---------|------|
| "关注 NFLX 财报" / "帮我盯着 XX" | `add` 命令 |
| "取消关注 NFLX" / "不用看 XX 了" | `remove` 命令 |
| "财报关注列表" / "我关注了哪些股票" | `list` 命令 |
| "检查一下财报" | `check` 命令（立即执行一次） |

## 配置文件

`watchlist.yaml`:
- `auto_sync_holdings: true` — 自动从 Maybe Finance 持仓同步
- `extra_tickers` — 手动添加的关注股票
- `exclude_tickers` — 排除列表（即使持仓中有也不关注）

## 去重逻辑

- 每只股票每个季度只通知一次（状态文件 `earnings_state.json` 记录）
- 移除股票时自动加入排除列表，防止 auto-sync 重新加入
- 重新添加已被排除的股票时，自动从排除列表移除
- 状态记录 90 天后自动清理
