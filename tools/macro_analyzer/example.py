#!/usr/bin/env python3
"""
宏观经济分析模块 - 使用示例

演示如何使用 MacroAnalyzer 进行完整的宏观经济分析
"""

import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer import MacroAnalyzer
from portfolio_alignment import Holding
from asset_attractiveness import AssetClass


def example_1_basic_analysis():
    """示例 1: 基本宏观经济分析（无持仓）"""
    print("=" * 60)
    print("示例 1: 基本宏观经济分析")
    print("=" * 60)
    print()

    analyzer = MacroAnalyzer()

    # 设置经济指标（模拟当前美国经济状况）
    report = analyzer.analyze(
        gdp_growth=2.5,  # GDP 增长 2.5%
        inflation=3.2,  # 通胀 3.2%
        unemployment=4.1,  # 失业率 4.1%
        interest_rate=5.5,  # 基准利率 5.5%
        stock_market_trend="up",  # 股市上涨
        commodity_trend="stable",  # 大宗商品稳定
        inflation_expectation="down",  # 通胀预期下降
    )

    # 格式化输出
    formatted_report = analyzer.format_report(report)
    print(formatted_report)
    print()


def example_2_with_holdings():
    """示例 2: 带持仓的完整分析"""
    print("=" * 60)
    print("示例 2: 带持仓的完整分析")
    print("=" * 60)
    print()

    analyzer = MacroAnalyzer()

    # 定义当前持仓
    holdings = [
        Holding(
            asset_class=AssetClass.STOCKS,
            ticker="AAPL",
            name="苹果股票",
            value=50000,  # $50,000
        ),
        Holding(
            asset_class=AssetClass.STOCKS,
            ticker="MSFT",
            name="微软股票",
            value=30000,  # $30,000
        ),
        Holding(
            asset_class=AssetClass.BONDS,
            ticker="TLT",
            name="长期国债 ETF",
            value=20000,  # $20,000
        ),
        Holding(
            asset_class=AssetClass.CASH,
            ticker="CASH",
            name="现金",
            value=15000,  # $15,000
        ),
        Holding(
            asset_class=AssetClass.GOLD,
            ticker="GLD",
            name="黄金 ETF",
            value=5000,  # $5,000
        ),
    ]

    # 设置经济指标（模拟滞胀环境）
    report = analyzer.analyze(
        gdp_growth=0.5,  # GDP 增长缓慢
        inflation=5.5,  # 高通胀
        unemployment=5.2,  # 失业率较高
        interest_rate=5.5,
        stock_market_trend="down",  # 股市下跌
        commodity_trend="up",  # 大宗商品上涨
        inflation_expectation="up",  # 通胀预期上升
        holdings=holdings,
    )

    # 格式化输出
    formatted_report = analyzer.format_report(report)
    print(formatted_report)
    print()


def example_3_recession_scenario():
    """示例 3: 衰退情景分析"""
    print("=" * 60)
    print("示例 3: 衰退情景分析")
    print("=" * 60)
    print()

    analyzer = MacroAnalyzer()

    # 定义持仓（偏向股票，不适合衰退期）
    holdings = [
        Holding(AssetClass.STOCKS, "SPY", "标普 500 ETF", 60000),
        Holding(AssetClass.STOCKS, "QQQ", "纳斯达克 ETF", 30000),
        Holding(AssetClass.BONDS, "BND", "综合债券 ETF", 10000),
    ]

    # 设置经济指标（模拟衰退环境）
    report = analyzer.analyze(
        gdp_growth=-1.5,  # GDP 负增长
        inflation=1.8,  # 低通胀
        unemployment=6.5,  # 高失业率
        interest_rate=3.5,  # 降息
        stock_market_trend="down",
        bond_yield_trend="down",  # 收益率下降
        commodity_trend="down",
        inflation_expectation="down",
        holdings=holdings,
    )

    # 格式化输出
    formatted_report = analyzer.format_report(report)
    print(formatted_report)
    print()


def example_4_recovery_scenario():
    """示例 4: 复苏情景分析"""
    print("=" * 60)
    print("示例 4: 复苏情景分析")
    print("=" * 60)
    print()

    analyzer = MacroAnalyzer()

    # 定义持仓（偏向债券和现金，不适合复苏期）
    holdings = [
        Holding(AssetClass.BONDS, "TLT", "长期国债 ETF", 40000),
        Holding(AssetClass.CASH, "CASH", "现金", 30000),
        Holding(AssetClass.GOLD, "GLD", "黄金 ETF", 20000),
        Holding(AssetClass.STOCKS, "SPY", "标普 500 ETF", 10000),
    ]

    # 设置经济指标（模拟复苏环境）
    report = analyzer.analyze(
        gdp_growth=3.5,  # GDP 强劲增长
        inflation=1.5,  # 低通胀
        unemployment=4.8,  # 失业率下降
        interest_rate=2.5,  # 低利率
        stock_market_trend="up",  # 股市上涨
        bond_yield_trend="up",  # 收益率上升
        commodity_trend="stable",
        inflation_expectation="stable",
        holdings=holdings,
    )

    # 格式化输出
    formatted_report = analyzer.format_report(report)
    print(formatted_report)
    print()


def main():
    """运行所有示例"""
    print("\n")
    print("*" * 60)
    print("*" + " " * 58 + "*")
    print("*" + "  宏观经济分析模块 - 使用示例".center(50) + "  *")
    print("*" + " " * 58 + "*")
    print("*" * 60)
    print("\n")

    example_1_basic_analysis()
    example_2_with_holdings()
    example_3_recession_scenario()
    example_4_recovery_scenario()

    print("=" * 60)
    print("所有示例运行完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
