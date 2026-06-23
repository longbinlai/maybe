# Maybe Finance 运行时配置架构

## 原则

**代码和配置严格分离。** 安装操作（`pip install`、`openclaw skills install --force`）只覆盖代码，永不被覆盖运行时配置。

## 目录结构

```
~/.config/maybe-finance/              ← 所有运行时配置（持久化，安装不会覆盖）
├── earnings-monitor/
│   ├── watchlist.yaml                ← 股票关注列表
│   └── earnings_state.json            ← 通知状态
├── datahub/
│   └── sources.yaml                  ← 数据源配置
```

## 各组件的配置加载逻辑

### earnings_monitor.py
1. 读取 `~/.config/maybe-finance/earnings-monitor/watchlist.yaml`
2. 如果不存在，从脚本同目录的 `watchlist.example.yaml`（模板）复制一份过去
3. 状态文件 `earnings_state.json` 也存在 `~/.config/maybe-finance/earnings-monitor/`

### datahub (get_config_path)
1. 先检查 `~/.config/maybe-finance/datahub/sources.yaml`（用户自定义）
2. 如果不存在，回退到包内默认 `sources.yaml`（模板）
3. 缓存目录已经在 `~/.datahub/cache/`（正确，不需要改）

### maybe-cli
不需要配置文件（使用环境变量和 CLI 参数），无需修改。

## 安装流程

### OpenClaw skills install --force
- 覆盖: SKILL.md, scripts/*.py, watchlist.example.yaml（模板）
- 不覆盖: ~/.config/maybe-finance/ 下的任何文件

### pip install / pip install --force
- 覆盖: Python 包代码
- 不覆盖: ~/.config/maybe-finance/ 下的任何文件
- 包内 sources.yaml 是默认模板，首次运行时复制到 config 目录

## 源码仓库中的文件

### tools/openclaw-skills/earnings-monitor/
- SKILL.md
- watchlist.example.yaml   ← 模板（不是实际配置）
- scripts/earnings_monitor.py

### tools/datahub/datahub/config/
- sources.yaml             ← 默认模板（首次运行时复制到 config 目录）
