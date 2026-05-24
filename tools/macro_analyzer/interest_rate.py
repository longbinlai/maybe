"""
利率差分析器

分析不同国家/地区的利率差异，为换汇决策提供依据。

主要功能：
1. 计算利率差（Interest Rate Differential）
2. 评估换汇收益（考虑汇率变动）
3. 提供换汇建议
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class Currency(Enum):
    """支持的货币"""
    USD = "USD"  # 美元
    CNY = "CNY"  # 人民币
    JPY = "JPY"  # 日元
    EUR = "EUR"  # 欧元
    GBP = "GBP"  # 英镑
    AUD = "AUD"  # 澳元
    HKD = "HKD"  # 港币


@dataclass
class InterestRateInfo:
    """利率信息"""
    currency: Currency
    rate: float  # 年化利率 (%)
    central_bank: str  # 央行名称
    last_update: Optional[str] = None  # 最后更新时间


@dataclass
class RateDifferentialAnalysis:
    """利率差分析结果"""
    from_currency: Currency
    to_currency: Currency
    rate_differential: float  # 利率差 (%)
    annual_benefit: float  # 年化收益 (%)
    recommendation: str
    risk_level: str  # low, medium, high
    reasoning: str


class InterestRateAnalyzer:
    """利率差分析器"""

    # 默认利率数据（需要定期更新）
    DEFAULT_RATES = {
        Currency.USD: InterestRateInfo(Currency.USD, 5.50, "Federal Reserve"),
        Currency.CNY: InterestRateInfo(Currency.CNY, 3.45, "People's Bank of China"),
        Currency.JPY: InterestRateInfo(Currency.JPY, 0.10, "Bank of Japan"),
        Currency.EUR: InterestRateInfo(Currency.EUR, 4.50, "European Central Bank"),
        Currency.GBP: InterestRateInfo(Currency.GBP, 5.25, "Bank of England"),
        Currency.AUD: InterestRateInfo(Currency.AUD, 4.35, "Reserve Bank of Australia"),
        Currency.HKD: InterestRateInfo(Currency.HKD, 5.75, "Hong Kong Monetary Authority"),
    }

    def __init__(self):
        self.rates: Dict[Currency, InterestRateInfo] = self.DEFAULT_RATES.copy()

    def update_rate(self, currency: Currency, rate: float, central_bank: Optional[str] = None):
        """更新利率数据"""
        if currency in self.rates:
            self.rates[currency].rate = rate
            if central_bank:
                self.rates[currency].central_bank = central_bank
        else:
            self.rates[currency] = InterestRateInfo(currency, rate, central_bank or "Unknown")

    def calculate_rate_differential(
        self,
        from_currency: Currency,
        to_currency: Currency
    ) -> float:
        """计算利率差"""
        if from_currency not in self.rates or to_currency not in self.rates:
            raise ValueError(f"缺少货币利率数据: {from_currency.value} 或 {to_currency.value}")

        from_rate = self.rates[from_currency].rate
        to_rate = self.rates[to_currency].rate

        # 利率差 = 目标货币利率 - 源货币利率
        return to_rate - from_rate

    def analyze(
        self,
        from_currency: Currency,
        to_currency: Currency,
        holding_period_years: float = 1.0
    ) -> RateDifferentialAnalysis:
        """分析换汇收益"""
        rate_diff = self.calculate_rate_differential(from_currency, to_currency)

        # 年化收益 = 利率差 * 持有年数
        annual_benefit = rate_diff * holding_period_years

        # 生成建议
        recommendation, risk_level, reasoning = self._generate_recommendation(
            from_currency, to_currency, rate_diff, annual_benefit
        )

        return RateDifferentialAnalysis(
            from_currency=from_currency,
            to_currency=to_currency,
            rate_differential=rate_diff,
            annual_benefit=annual_benefit,
            recommendation=recommendation,
            risk_level=risk_level,
            reasoning=reasoning
        )

    def _generate_recommendation(
        self,
        from_currency: Currency,
        to_currency: Currency,
        rate_diff: float,
        annual_benefit: float
    ) -> tuple[str, str, str]:
        """生成换汇建议"""
        # 利率差阈值
        significant_diff = 2.0  # 2% 以上认为显著
        very_significant_diff = 3.0  # 3% 以上认为非常显著

        if rate_diff > very_significant_diff:
            recommendation = "强烈推荐换汇"
            risk_level = "low"
            reasoning = (
                f"利率差 {rate_diff:.2f}% 非常显著。"
                f"从 {from_currency.value} 换到 {to_currency.value} 可获得更高利息收益。"
                f"年化收益约 {annual_benefit:.2f}%。"
                f"风险较低，但需注意汇率波动风险。"
            )
        elif rate_diff > significant_diff:
            recommendation = "建议换汇"
            risk_level = "medium"
            reasoning = (
                f"利率差 {rate_diff:.2f}% 较为显著。"
                f"从 {from_currency.value} 换到 {to_currency.value} 可获得更高利息收益。"
                f"年化收益约 {annual_benefit:.2f}%。"
                f"中等风险，需关注汇率波动和央行政策变化。"
            )
        elif rate_diff > 0:
            recommendation = "可考虑换汇"
            risk_level = "medium"
            reasoning = (
                f"利率差 {rate_diff:.2f}% 较小。"
                f"从 {from_currency.value} 换到 {to_currency.value} 可获得略高利息收益。"
                f"年化收益约 {annual_benefit:.2f}%。"
                f"收益有限，汇率波动可能抵消利息收益。"
            )
        elif rate_diff > -significant_diff:
            recommendation = "不建议换汇"
            risk_level = "medium"
            reasoning = (
                f"利率差 {rate_diff:.2f}% 为负且较小。"
                f"从 {from_currency.value} 换到 {to_currency.value} 利息收益会降低。"
                f"年化损失约 {abs(annual_benefit):.2f}%。"
                f"除非有汇率升值预期，否则不建议换汇。"
            )
        else:
            recommendation = "强烈不建议换汇"
            risk_level = "high"
            reasoning = (
                f"利率差 {rate_diff:.2f}% 显著为负。"
                f"从 {from_currency.value} 换到 {to_currency.value} 会显著降低利息收益。"
                f"年化损失约 {abs(annual_benefit):.2f}%。"
                f"除非有强烈汇率升值预期，否则不应换汇。"
            )

        return recommendation, risk_level, reasoning

    def get_all_rate_differentials(self, base_currency: Currency) -> List[RateDifferentialAnalysis]:
        """获取相对于基准货币的所有利率差"""
        analyses = []
        for currency in self.rates.keys():
            if currency != base_currency:
                analysis = self.analyze(base_currency, currency)
                analyses.append(analysis)

        # 按利率差排序（从高到低）
        analyses.sort(key=lambda x: x.rate_differential, reverse=True)
        return analyses

    def format_analysis(self, analysis: RateDifferentialAnalysis) -> str:
        """格式化分析结果"""
        lines = [
            f"=== 利率差分析 ===",
            f"从: {analysis.from_currency.value} → 到: {analysis.to_currency.value}",
            f"利率差: {analysis.rate_differential:+.2f}%",
            f"年化收益: {analysis.annual_benefit:+.2f}%",
            f"建议: {analysis.recommendation}",
            f"风险等级: {analysis.risk_level}",
            f"说明: {analysis.reasoning}",
        ]
        return "\n".join(lines)
