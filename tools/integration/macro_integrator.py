"""
集成模块 - 连接 DataHub 和 MacroAnalyzer

自动从 DataHub 获取宏观经济数据，传递给 MacroAnalyzer 进行分析
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加 datahub 和 macro_analyzer 项目目录到路径
tools_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tools_dir / "datahub"))  # datahub 项目根目录
sys.path.insert(0, str(tools_dir))  # tools 目录，用于导入 macro_analyzer

from datahub import SourceRegistry
from macro_analyzer import MacroAnalyzer
from macro_analyzer.portfolio_alignment import Holding
from macro_analyzer.asset_attractiveness import AssetClass


class MacroDataIntegrator:
    """宏观经济数据集成器"""
    
    def __init__(self, datahub_config_path: str):
        """
        初始化集成器
        
        Args:
            datahub_config_path: DataHub 配置文件路径
        """
        self.registry = SourceRegistry(config_path=datahub_config_path)
        self.analyzer = MacroAnalyzer()
        self.raw_data = {}
        
    def fetch_macro_data(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        从 DataHub 获取宏观经济数据
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            原始数据字典
        """
        print("=" * 80)
        print("步骤 1: 从 DataHub 获取宏观经济数据")
        print("=" * 80)
        
        # 获取所有数据源
        results = self.registry.fetch_all(use_cache=use_cache)
        
        # 存储原始数据
        self.raw_data = results
        
        # 统计
        total_sources = len(results)
        success_sources = sum(1 for r in results.values() if r.status == 'success')
        total_items = sum(len(r.items) for r in results.values())
        
        print(f"\n数据获取完成:")
        print(f"  数据源总数: {total_sources}")
        print(f"  成功获取: {success_sources}")
        print(f"  数据项总数: {total_items}")
        
        return results
    
    def extract_economic_indicators(self) -> Dict[str, Any]:
        """
        从原始数据中提取经济指标
        
        Returns:
            经济指标字典
        """
        print("\n" + "=" * 80)
        print("步骤 2: 提取经济指标")
        print("=" * 80)
        
        indicators = {
            'gdp_growth': None,
            'inflation': None,
            'unemployment': None,
            'interest_rate': None,
            'stock_market_trend': 'stable',
            'bond_yield_trend': 'stable',
            'commodity_trend': 'stable',
            'real_estate_trend': 'stable',
            'inflation_expectation': 'stable',
        }
        
        # 从各个数据源提取指标
        for source_name, result in self.raw_data.items():
            if result.status != 'success':
                continue
                
            # 根据数据源类型提取不同指标
            if 'bea' in source_name.lower():  # GDP 数据
                indicators['gdp_growth'] = self._extract_gdp_growth(result.items)
                
            elif 'bls' in source_name.lower():  # 就业和通胀数据
                cpi, unemployment = self._extract_bls_data(result.items)
                if cpi is not None:
                    indicators['inflation'] = cpi
                if unemployment is not None:
                    indicators['unemployment'] = unemployment
                    
            elif 'federal_reserve' in source_name.lower():  # 利率数据
                indicators['interest_rate'] = self._extract_interest_rate(result.items)
                
            elif 'yfinance_indices' in source_name.lower():  # 股指数据
                indicators['stock_market_trend'] = self._extract_market_trend(result.items)
                
            elif 'yfinance_gold' in source_name.lower() or 'yfinance_oil' in source_name.lower():
                indicators['commodity_trend'] = self._extract_commodity_trend(result.items)
            
            # 从新闻中提取通胀预期
            if 'news' in source_name.lower() or 'forexlive' in source_name.lower():
                inflation_exp = self._extract_inflation_expectation(result.items)
                if inflation_exp != 'stable':
                    indicators['inflation_expectation'] = inflation_exp
        
        # 使用默认值填充未获取的指标（用于演示）
        if indicators['gdp_growth'] is None:
            indicators['gdp_growth'] = 2.5  # 默认值
        if indicators['inflation'] is None:
            indicators['inflation'] = 3.2  # 默认值
        if indicators['unemployment'] is None:
            indicators['unemployment'] = 4.1  # 默认值
        if indicators['interest_rate'] is None:
            indicators['interest_rate'] = 5.5  # 默认值
        
        # 打印提取的指标
        print("\n提取的经济指标:")
        for key, value in indicators.items():
            if value is not None:
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: (未获取)")
        
        return indicators
    
    def _extract_gdp_growth(self, items: List) -> Optional[float]:
        """从 BEA 数据提取 GDP 增长率"""
        # 这里需要根据实际数据格式实现
        # 示例：从新闻标题或内容中提取数字
        for item in items[:5]:  # 只看最新 5 条
            text = f"{item.title} {item.content}".lower()
            if 'gdp' in text and ('growth' in text or 'percent' in text):
                # 简单提取：假设文本中有 "X.X%" 格式
                import re
                matches = re.findall(r'(\d+\.?\d*)\s*%', text)
                if matches:
                    return float(matches[0])
        return None
    
    def _extract_bls_data(self, items: List) -> tuple:
        """从 BLS 数据提取 CPI 和失业率"""
        cpi = None
        unemployment = None
        
        for item in items[:10]:
            text = f"{item.title} {item.content}".lower()
            
            # 提取 CPI
            if 'cpi' in text or 'consumer price' in text:
                import re
                matches = re.findall(r'(\d+\.?\d*)\s*%', text)
                if matches and cpi is None:
                    cpi = float(matches[0])
            
            # 提取失业率
            if 'unemployment' in text:
                import re
                matches = re.findall(r'(\d+\.?\d*)\s*%', text)
                if matches and unemployment is None:
                    unemployment = float(matches[0])
        
        return cpi, unemployment
    
    def _extract_interest_rate(self, items: List) -> Optional[float]:
        """从美联储数据提取利率"""
        for item in items[:5]:
            text = f"{item.title} {item.content}".lower()
            if 'rate' in text and ('percent' in text or '%' in text):
                import re
                matches = re.findall(r'(\d+\.?\d*)\s*(?:percent|%)', text)
                if matches:
                    # 取最大的数字作为利率
                    rates = [float(m) for m in matches if float(m) < 20]
                    if rates:
                        return max(rates)
        return None
    
    def _extract_market_trend(self, items: List) -> str:
        """从股指数据提取市场趋势"""
        if not items:
            return 'stable'
        
        # 检查最新的几个数据项
        positive_count = 0
        negative_count = 0
        
        for item in items[:5]:
            text = f"{item.title} {item.content}".lower()
            
            # 简单的关键词分析
            if any(word in text for word in ['up', 'gain', 'rise', 'higher', 'positive']):
                positive_count += 1
            elif any(word in text for word in ['down', 'loss', 'fall', 'lower', 'negative']):
                negative_count += 1
        
        if positive_count > negative_count + 1:
            return 'up'
        elif negative_count > positive_count + 1:
            return 'down'
        else:
            return 'stable'
    
    def _extract_commodity_trend(self, items: List) -> str:
        """从商品数据提取趋势"""
        # 类似市场趋势提取
        return self._extract_market_trend(items)
    
    def _extract_inflation_expectation(self, items: List) -> str:
        """从新闻数据提取通胀预期"""
        if not items:
            return 'stable'
        
        # 检查最新的几个数据项
        up_count = 0
        down_count = 0
        
        for item in items[:10]:
            text = f"{item.title} {item.content}".lower()
            
            # 检查通胀相关关键词
            if 'inflation' in text or 'cpi' in text or 'price' in text:
                if any(word in text for word in ['rise', 'increase', 'higher', 'up', 'surge']):
                    up_count += 1
                elif any(word in text for word in ['fall', 'decrease', 'lower', 'down', 'drop']):
                    down_count += 1
        
        if up_count > down_count + 2:
            return 'up'
        elif down_count > up_count + 2:
            return 'down'
        else:
            return 'stable'
    
    def analyze(self, holdings: Optional[List[Holding]] = None, 
                use_cache: bool = True) -> Dict[str, Any]:
        """
        执行完整的宏观经济分析
        
        Args:
            holdings: 持仓列表（可选）
            use_cache: 是否使用缓存
            
        Returns:
            分析报告
        """
        # 步骤 1: 获取数据
        self.fetch_macro_data(use_cache=use_cache)
        
        # 步骤 2: 提取指标
        indicators = self.extract_economic_indicators()
        
        # 步骤 3: 执行分析
        print("\n" + "=" * 80)
        print("步骤 3: 执行宏观经济分析")
        print("=" * 80)
        
        report = self.analyzer.analyze(
            gdp_growth=indicators['gdp_growth'],
            inflation=indicators['inflation'],
            unemployment=indicators['unemployment'],
            interest_rate=indicators['interest_rate'],
            stock_market_trend=indicators['stock_market_trend'],
            bond_yield_trend=indicators['bond_yield_trend'],
            commodity_trend=indicators['commodity_trend'],
            real_estate_trend=indicators['real_estate_trend'],
            inflation_expectation=indicators['inflation_expectation'],
            holdings=holdings,
        )
        
        # 添加原始指标到报告
        report['raw_indicators'] = indicators
        
        print("\n分析完成！")
        
        return report
    
    def generate_report(self, report: Dict[str, Any]) -> str:
        """
        生成格式化报告
        
        Args:
            report: 分析报告
            
        Returns:
            格式化的报告文本
        """
        print("\n" + "=" * 80)
        print("步骤 4: 生成报告")
        print("=" * 80)
        
        formatted = self.analyzer.format_report(report)
        
        print("\n报告生成完成！")
        
        return formatted


def main():
    """主函数 - 演示集成流程"""
    print("\n" + "=" * 80)
    print("宏观经济数据集成分析 - 演示")
    print("=" * 80)
    print()
    
    # 配置文件路径
    config_path = Path(__file__).parent.parent / "datahub" / "config" / "sources.yaml"
    
    # 创建集成器
    integrator = MacroDataIntegrator(str(config_path))
    
    # 示例持仓（可选）
    holdings = [
        Holding(AssetClass.STOCKS, "AAPL", "苹果", 50000),
        Holding(AssetClass.BONDS, "TLT", "国债", 20000),
        Holding(AssetClass.CASH, "CASH", "现金", 15000),
    ]
    
    # 执行分析
    report = integrator.analyze(holdings=holdings, use_cache=True)
    
    # 生成报告
    formatted_report = integrator.generate_report(report)
    
    # 打印报告
    print("\n")
    print(formatted_report)
    
    # 保存报告
    output_file = Path(__file__).parent / "macro_report.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(formatted_report)
    
    print(f"\n报告已保存到: {output_file}")


if __name__ == "__main__":
    main()
