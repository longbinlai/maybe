---
name: datahub
description: "Manage and query macroeconomic data sources: RSS feeds, Yahoo Finance, NewsAPI, central banks."
---

# DataHub - 宏观经济数据源管理

管理和查询宏观经济数据源，支持 RSS 订阅、Yahoo Finance 和 NewsAPI。

## 功能

- 管理 20+ 个宏观经济数据源（央行、经济指标、外汇、大宗商品、市场指数）
- 自动获取、验证、缓存数据
- PostgreSQL 历史数据存储与全文搜索
- 数据源健康监控与执行日志

## 调用方式

```bash
# 获取所有数据源
datahub-cli fetch-all

# 获取单个数据源
datahub-cli fetch federal_reserve

# 列出所有数据源
datahub-cli list

# 测试数据源连接
datahub-cli test

# 查看缓存状态
datahub-cli status

# 查询历史数据（PostgreSQL）
datahub-cli history --stats
datahub-cli history --source federal_reserve --last 30d
datahub-cli history --keyword "美联储"

# 查看执行日志
datahub-cli history --logs

# 清理过期数据
datahub-cli cleanup --dry-run
datahub-cli cleanup
```

## 参数说明

### history 子命令

| 参数 | 说明 |
|------|------|
| `--stats` | 显示存储统计信息 |
| `--logs` | 显示执行日志 |
| `--source <name>` | 按数据源过滤 |
| `--category <cat>` | 按类别过滤 |
| `--keyword <kw>` | 全文搜索 |
| `--from <date>` --to <date>` | 时间范围查询 |
| `--last <Nd/Nw/Nm>` | 最近 N 天/周/月 |
| `--limit <N>` | 限制返回条数 |

### cleanup 子命令

| 参数 | 说明 |
|------|------|
| `--dry-run` | 预览模式，不实际删除 |
| `--source <name>` | 只清理指定数据源 |
| `--days <N>` | 自定义保留天数 |

## 输出格式示例

```
================================================================================
数据获取摘要
================================================================================

总计数据源: 20
成功: 18 (90.0%)
降级: 1
失败: 1
总数据项: 350
```

## 使用场景

- 用户需要了解宏观经济数据源状态
- 定时获取宏观经济数据
- 查询历史数据和执行日志
- 管理数据源配置

## 依赖

- Python 3.8+ (~/pyenv/maybe/bin/python3)
- datahub 包（已安装到 ~/pyenv/maybe）
- PostgreSQL（历史数据存储，通过 Docker compose 运行）
