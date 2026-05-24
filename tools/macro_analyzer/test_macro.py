#!/usr/bin/env python3
"""
宏观经济分析模块 - 快速测试

验证所有核心功能是否正常工作
"""

import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from economic_cycle import EconomicCycleAnalyzer, EconomicCycle
from interest_rate import InterestRateAnalyzer, Currency
from asset_attractiveness import AssetAttractivenessAnalyzer
from portfolio_alignment import PortfolioAlignmentAnalyzer, Holding, AssetClass
from analyzer import MacroAnalyzer


def test_economic_cycle():
    """测试经济周期分析"""
    print("测试 1: 经济周期分析...")
    analyzer = EconomicCycleAnalyzer()
    analyzer.set_indicators(gdp_growth=2.5, inflation=3.2, unemployment=4.1)
    result = analyzer.analyze()
    
    assert result.cycle in EconomicCycle, "周期类型错误"
    assert 0 <= result.confidence <= 100, "置信度范围错误"
    assert len(result.recommended_assets) > 0, "推荐资产为空"
    
    print(f"  ✓ 周期: {result.cycle.value}, 置信度: {result.confidence}%")
    print(f"  ✓ 推荐资产: {result.recommended_assets}")
    return True


def test_interest_rate():
    """测试利率差分析"""
    print("\n测试 2: 利率差分析...")
    analyzer = InterestRateAnalyzer()
    
    # 测试 USD -> CNY
    result = analyzer.analyze(Currency.USD, Currency.CNY)
    assert result.rate_differential is not None, "利率差计算失败"
    assert result.recommendation is not None, "建议生成失败"
    
    print(f"  ✓ USD → CNY: 利率差 {result.rate_differential:+.2f}%")
    print(f"  ✓ 建议: {result.recommendation}")
    return True


def test_asset_attractiveness():
    """测试资产吸引力评估"""
    print("\n测试 3: 资产吸引力评估...")
    analyzer = AssetAttractivenessAnalyzer()
    results = analyzer.analyze(EconomicCycle.EXPANSION)
    
    assert len(results) > 0, "评估结果为空"
    assert all(0 <= r.score <= 100 for r in results), "分数范围错误"
    
    print(f"  ✓ 评估了 {len(results)} 种资产")
    print(f"  ✓ 最高分: {results[0].asset_class.value} ({results[0].score:.0f}分)")
    return True


def test_portfolio_alignment():
    """测试持仓匹配度分析"""
    print("\n测试 4: 持仓匹配度分析...")
    
    # 创建测试持仓
    holdings = [
        Holding(AssetClass.STOCKS, "AAPL", "苹果", 50000),
        Holding(AssetClass.BONDS, "TLT", "国债", 20000),
        Holding(AssetClass.CASH, "CASH", "现金", 15000),
    ]
    
    analyzer = PortfolioAlignmentAnalyzer()
    analyzer.set_holdings(holdings)
    
    # 创建周期分析结果
    cycle_analyzer = EconomicCycleAnalyzer()
    cycle_analyzer.set_indicators(gdp_growth=2.5, inflation=3.2)
    cycle_result = cycle_analyzer.analyze()
    
    result = analyzer.analyze(cycle_result)
    
    assert 0 <= result.alignment_score <= 100, "匹配度分数范围错误"
    assert result.recommendations is not None, "建议生成失败"
    
    print(f"  ✓ 匹配度评分: {result.alignment_score:.0f}/100")
    print(f"  ✓ 生成 {len(result.recommendations)} 条建议")
    return True


def test_macro_analyzer():
    """测试综合分析器"""
    print("\n测试 5: 综合分析器...")
    
    analyzer = MacroAnalyzer()
    report = analyzer.analyze(
        gdp_growth=2.5,
        inflation=3.2,
        unemployment=4.1,
        stock_market_trend="up"
    )
    
    assert "economic_cycle" in report, "缺少经济周期分析"
    assert "interest_rate_analysis" in report, "缺少利率差分析"
    assert "asset_attractiveness" in report, "缺少资产吸引力分析"
    
    print(f"  ✓ 经济周期: {report['economic_cycle']['cycle']}")
    print(f"  ✓ 利率差分析: {len(report['interest_rate_analysis'])} 条")
    print(f"  ✓ 资产吸引力: {len(report['asset_attractiveness'])} 种")
    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("宏观经济分析模块 - 快速测试")
    print("=" * 60)
    print()
    
    tests = [
        test_economic_cycle,
        test_interest_rate,
        test_asset_attractiveness,
        test_portfolio_alignment,
        test_macro_analyzer,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ✗ 测试失败: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"测试结果: {passed}/{len(tests)} 通过")
    
    if failed == 0:
        print("✓ 所有测试通过！")
    else:
        print(f"✗ {failed} 个测试失败")
    
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
