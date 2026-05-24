# 集成模块 (Integration)

连接 DataHub 和 MacroAnalyzer，实现自动化的宏观经济分析流程。

## 功能

- **自动数据获取**: 从 DataHub 的 13 个数据源获取宏观经济数据
- **智能指标提取**: 从原始数据中提取关键经济指标（GDP、通胀、失业率、利率等）
- **完整分析流程**: 自动执行经济周期判断、利率差分析、资产吸引力评估
- **持仓匹配度分析**: 分析当前持仓与推荐配置的偏差，提供调仓建议
- **格式化报告**: 生成易读的中文分析报告

## 快速开始

```bash
cd ~/Documents/git/maybe/tools/integration
python3 macro_integrator.py
```

## 输出示例

```
================================================================================
宏观经济数据集成分析 - 演示
================================================================================

步骤 1: 从 DataHub 获取宏观经济数据
  数据源总数: 13
  成功获取: 5
  数据项总数: 121

步骤 2: 提取经济指标
  gdp_growth: 2.5
  inflation: 3.2
  unemployment: 4.1
  interest_rate: 5.5

步骤 3: 执行宏观经济分析
  当前周期: EXPANSION
  置信度: 70%

步骤 4: 生成报告
  报告已保存到: macro_report.txt
```

## 数据源

集成模块使用 DataHub 配置的以下数据源：

### RSS 数据源
- Federal Reserve (美联储)
- ECB (欧洲央行)
- BOJ (日本央行)
- BLS (美国劳工统计局)
- BEA (美国经济分析局)
- ForexLive (外汇新闻)
- OilPrice (油价新闻)
- SCMP (南华早报)

### YFinance 数据源
- yfinance_gold (黄金价格)
- yfinance_oil (原油价格)
- yfinance_fx (外汇汇率)
- yfinance_indices (股指)
- yfinance_news (财经新闻)

## 经济指标提取

集成模块会从原始数据中自动提取以下经济指标：

| 指标 | 数据来源 | 提取方法 |
|------|---------|---------|
| GDP 增长率 | BEA RSS | 从新闻标题和内容提取数字 |
| 通胀率 (CPI) | BLS RSS | 从 CPI 相关新闻提取 |
| 失业率 | BLS RSS | 从就业报告提取 |
| 基准利率 | Federal Reserve RSS | 从利率决议新闻提取 |
| 股市趋势 | yfinance_indices | 分析价格变动方向 |
| 商品趋势 | yfinance_gold/oil | 分析价格变动方向 |
| 通胀预期 | 新闻数据源 | 关键词分析 |

## 使用方法

### 基本使用

```python
from macro_integrator import MacroDataIntegrator

# 创建集成器
integrator = MacroDataIntegrator(
    datahub_config_path="../datahub/config/sources.yaml"
)

# 执行分析（使用示例持仓）
from macro_analyzer.portfolio_alignment import Holding
from macro_analyzer.asset_attractiveness import AssetClass

holdings = [
    Holding(AssetClass.STOCKS, "AAPL", "苹果", 50000),
    Holding(AssetClass.BONDS, "TLT", "国债", 20000),
    Holding(AssetClass.CASH, "CASH", "现金", 15000),
]

report = integrator.analyze(holdings=holdings)
formatted_report = integrator.generate_report(report)

print(formatted_report)
```

### 自定义持仓

```python
from macro_integrator import MacroDataIntegrator
from macro_analyzer.portfolio_alignment import Holding
from macro_analyzer.asset_attractiveness import AssetClass

integrator = MacroDataIntegrator("../datahub/config/sources.yaml")

# 定义你的持仓
holdings = [
    Holding(AssetClass.STOCKS, "VTI", "美股ETF", 100000),
    Holding(AssetClass.BONDS, "BND", "债券ETF", 50000),
    Holding(AssetClass.REAL_ESTATE, "VNQ", "房地产ETF", 30000),
    Holding(AssetClass.COMMODITIES, "GLD", "黄金ETF", 20000),
    Holding(AssetClass.CASH, "CASH", "现金", 40000),
]

# 执行分析
report = integrator.analyze(holdings=holdings)

# 查看匹配度
alignment = report['portfolio_alignment']
print(f"匹配度评分: {alignment['alignment_score']}/100")
print("\n调仓建议:")
for rec in alignment['recommendations']:
    print(f"  {rec}")
```

## 分析报告结构

生成的报告包含以下部分：

### 1. 经济周期分析
- 当前周期阶段（复苏/扩张/滞胀/衰退）
- 置信度评分
- 推荐资产类别

### 2. 利率差分析
- 各货币对利率差
- 换汇建议（推荐/不推荐/强烈不推荐）
- 风险等级

### 3. 资产吸引力排名
- 各类资产的吸引力评分
- 市场趋势指示器
- 推荐理由

### 4. 持仓匹配度分析
- 整体匹配度评分
- 过度配置的资产
- 低配置的资产
- 具体调仓建议

## 配置说明

### 数据源配置

数据源配置文件位于 `../datahub/config/sources.yaml`，可以添加或删除数据源。

### 默认指标值

当某些指标无法从数据源提取时，集成模块会使用以下默认值：

```python
gdp_growth: 2.5%      # GDP 增长率
inflation: 3.2%       # 通胀率
unemployment: 4.1%    # 失业率
interest_rate: 5.5%   # 基准利率
```

这些默认值反映了当前（2026年）的典型经济状况，可以根据实际情况调整。

## 输出文件

- **控制台输出**: 完整的分析过程和结果
- **macro_report.txt**: 格式化的分析报告
- **raw_data**: 原始获取的数据（存储在内存中）

## 故障排除

### 数据源获取失败

如果某些数据源获取失败，检查：
1. 网络连接是否正常
2. 数据源 URL 是否可访问
3. RSS 源是否有效
4. YFinance API 是否可用

### 指标提取不准确

如果提取的指标不准确，可以：
1. 调整提取逻辑中的正则表达式
2. 修改关键词列表
3. 使用默认值替代

### 分析报告不符合预期

如果分析报告不符合预期，可以：
1. 检查输入的经济指标是否正确
2. 调整持仓配置
3. 查看 MacroAnalyzer 的文档了解分析逻辑

## 下一步

- [ ] 实现更精确的指标提取算法
- [ ] 添加历史数据对比功能
- [ ] 集成 Maybe Finance 自动读取持仓
- [ ] 添加 OpenClaw Skill 支持
- [ ] 实现定时任务（每日自动分析）
- [ ] 添加飞书推送功能

## 依赖

- Python 3.8+
- datahub (DataHub 数据源管理模块)
- macro_analyzer (宏观经济分析模块)
- feedparser (RSS 解析)
- yfinance (Yahoo Finance 数据)

## 许可证

MIT License
