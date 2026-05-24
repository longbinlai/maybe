"""
宏观经济分析模块 - 主入口

提供完整的宏观经济分析流程：
1. 经济周期判断
2. 利率差分析（换汇决策）
3. 资产吸引力评估
4. 持仓匹配度分析
"""

from .economic_cycle import EconomicCycleAnalyzer, EconomicCycle
from .interest_rate import InterestRateAnalyzer, Currency
from .asset_attractiveness import AssetAttractivenessAnalyzer, AssetClass
from .portfolio_alignment import PortfolioAlignmentAnalyzer, Holding
from typing import List, Dict, Any


class MacroAnalyzer:
    """宏观经济综合分析器"""

    def __init__(self):
        self.cycle_analyzer = EconomicCycleAnalyzer()
        self.rate_analyzer = InterestRateAnalyzer()
        self.asset_analyzer = AssetAttractivenessAnalyzer()
        self.alignment_analyzer = PortfolioAlignmentAnalyzer()

    def analyze(
        self,
        gdp_growth: float = None,
        inflation: float = None,
        unemployment: float = None,
        interest_rate: float = None,
        stock_market_trend: str = "stable",
        bond_yield_trend: str = "stable",
        commodity_trend: str = "stable",
        real_estate_trend: str = "stable",
        inflation_expectation: str = "stable",
        holdings: List[Holding] = None,
    ) -> Dict[str, Any]:
        """
        执行完整的宏观经济分析

        Args:
            gdp_growth: GDP 增长率 (%)
            inflation: 通胀率 (%)
            unemployment: 失业率 (%)
            interest_rate: 基准利率 (%)
            stock_market_trend: 股票市场趋势 ("up", "down", "stable")
            bond_yield_trend: 债券收益率趋势
            commodity_trend: 大宗商品趋势
            real_estate_trend: 房地产趋势
            inflation_expectation: 通胀预期
            holdings: 当前持仓列表

        Returns:
            完整的分析报告
        """
        # 1. 分析经济周期
        self.cycle_analyzer.set_indicators(
            gdp_growth=gdp_growth,
            inflation=inflation,
            unemployment=unemployment,
            interest_rate=interest_rate,
        )
        cycle_analysis = self.cycle_analyzer.analyze()

        # 2. 分析利率差（换汇建议）
        rate_analyses = self.rate_analyzer.get_all_rate_differentials(Currency.USD)

        # 3. 分析资产吸引力
        self.asset_analyzer.set_market_condition(
            stock_market_trend=stock_market_trend,
            bond_yield_trend=bond_yield_trend,
            commodity_trend=commodity_trend,
            real_estate_trend=real_estate_trend,
            inflation_expectation=inflation_expectation,
        )
        asset_attractiveness = self.asset_analyzer.analyze(cycle_analysis.cycle)

        # 4. 分析持仓匹配度（如果有持仓数据）
        alignment_analysis = None
        if holdings:
            self.alignment_analyzer.set_holdings(holdings)
            alignment_analysis = self.alignment_analyzer.analyze(cycle_analysis)

        # 5. 生成综合报告
        report = {
            "economic_cycle": {
                "cycle": cycle_analysis.cycle.value,
                "confidence": cycle_analysis.confidence,
                "reasoning": cycle_analysis.reasoning,
                "recommended_assets": cycle_analysis.recommended_assets,
            },
            "interest_rate_analysis": [
                {
                    "from": ra.from_currency.value,
                    "to": ra.to_currency.value,
                    "rate_differential": ra.rate_differential,
                    "annual_benefit": ra.annual_benefit,
                    "recommendation": ra.recommendation,
                    "risk_level": ra.risk_level,
                }
                for ra in rate_analyses
            ],
            "asset_attractiveness": [
                {
                    "asset_class": aa.asset_class.value,
                    "score": aa.score,
                    "trend": aa.trend,
                    "reasoning": aa.reasoning,
                }
                for aa in asset_attractiveness
            ],
            "portfolio_alignment": None,
        }

        if alignment_analysis:
            report["portfolio_alignment"] = {
                "alignment_score": alignment_analysis.alignment_score,
                "deviations": {
                    k.value: v for k, v in alignment_analysis.deviations.items()
                },
                "over_weighted": [a.value for a in alignment_analysis.over_weighted],
                "under_weighted": [a.value for a in alignment_analysis.under_weighted],
                "recommendations": alignment_analysis.recommendations,
                "reasoning": alignment_analysis.reasoning,
            }

        return report

    def format_report(self, report: Dict[str, Any]) -> str:
        """格式化分析报告"""
        lines = [
            "=" * 60,
            "宏观经济综合分析报告",
            "=" * 60,
            "",
        ]

        # 1. 经济周期
        cycle = report["economic_cycle"]
        lines.extend([
            "【1. 经济周期分析】",
            f"当前周期: {cycle['cycle'].upper()}",
            f"置信度: {cycle['confidence']}%",
            f"分析: {cycle['reasoning']}",
            f"推荐资产: {', '.join(cycle['recommended_assets'])}",
            "",
        ])

        # 2. 利率差分析（只显示前 3 个）
        lines.append("【2. 利率差分析（换汇建议）】")
        for ra in report["interest_rate_analysis"][:3]:
            lines.append(
                f"  {ra['from']} → {ra['to']}: "
                f"利率差 {ra['rate_differential']:+.2f}%, "
                f"{ra['recommendation']} ({ra['risk_level']}风险)"
            )
        lines.append("")

        # 3. 资产吸引力（只显示前 3 个）
        lines.append("【3. 资产吸引力排名】")
        for i, aa in enumerate(report["asset_attractiveness"][:3], 1):
            trend_emoji = {"up": "📈", "down": "📉", "stable": "➡️"}.get(aa["trend"], "➡️")
            lines.append(
                f"  {i}. {aa['asset_class'].upper()}: "
                f"{aa['score']:.0f}分 {trend_emoji}"
            )
        lines.append("")

        # 4. 持仓匹配度（如果有）
        if report["portfolio_alignment"]:
            alignment = report["portfolio_alignment"]
            lines.extend([
                "【4. 持仓匹配度分析】",
                f"匹配度评分: {alignment['alignment_score']:.0f}/100",
                f"分析: {alignment['reasoning']}",
            ])

            if alignment["over_weighted"]:
                lines.append(f"过度配置: {', '.join(a.upper() for a in alignment['over_weighted'])}")
            if alignment["under_weighted"]:
                lines.append(f"低配置: {', '.join(a.upper() for a in alignment['under_weighted'])}")

            if alignment["recommendations"]:
                lines.append("\n调仓建议:")
                for rec in alignment["recommendations"]:
                    lines.append(f"  {rec}")
        else:
            lines.extend([
                "【4. 持仓匹配度分析】",
                "未提供持仓数据，跳过此分析",
            ])

        lines.extend(["", "=" * 60])

        return "\n".join(lines)


# 便捷函数
def analyze_macro(
    gdp_growth: float = None,
    inflation: float = None,
    unemployment: float = None,
    **kwargs
) -> Dict[str, Any]:
    """
    便捷的宏观经济分析函数

    Example:
        report = analyze_macro(
            gdp_growth=2.5,
            inflation=3.2,
            unemployment=4.1,
            stock_market_trend="up",
        )
    """
    analyzer = MacroAnalyzer()
    return analyzer.analyze(
        gdp_growth=gdp_growth,
        inflation=inflation,
        unemployment=unemployment,
        **kwargs
    )
