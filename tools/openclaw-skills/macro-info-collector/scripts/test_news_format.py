#!/usr/bin/env python3
"""
快速测试新闻显示格式
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.collect_macro_info import MacroInfoCollector

# 创建模拟数据
mock_data = {
    "rates": {"fed_funds_rate": 5.50, "treasury_10y": 4.25},
    "fx": {"USDCNY": 7.24, "USDJPY": 157.5},
    "commodities": {"gold": 2650.50, "oil": 78.30},
    "indices": {
        "SP500": {"price": 5980.5, "change_pct": 0.85},
        "DJI": {"price": 44520.3, "change_pct": 0.62},
        "NASDAQ": {"price": 19120.8, "change_pct": 1.25},
        "Russell2000": {"price": 2380.2, "change_pct": 0.95},
        "HangSeng": {"price": 20150.6, "change_pct": -0.45},
        "Shanghai": {"price": 3320.8, "change_pct": 0.32},
        "Shenzhen": {"price": 10580.5, "change_pct": 0.58},
        "CSI300": {"price": 3890.2, "change_pct": 0.42},
        "Nikkei225": {"price": 39250.8, "change_pct": -0.18},
        "FTSE100": {"price": 8280.5, "change_pct": 0.25},
        "DAX": {"price": 19850.3, "change_pct": 0.68},
        "STI": {"price": 3680.2, "change_pct": 0.15},
    },
    "news": [
        {
            "title": "Fed signals potential rate cut in September as inflation cools",
            "source": "forexlive",
            "url": "https://forexlive.com/example1",
            "date": "05/24",
            "summary": "Federal Reserve officials indicated they may begin cutting interest rates in September if inflation continues to trend downward toward the 2% target. Markets rallied on the news."
        },
        {
            "title": "USD/CNY breaks above 7.25 as China economy shows weakness",
            "source": "forexlive",
            "url": "https://forexlive.com/example2",
            "date": "05/24",
            "summary": "The Chinese yuan weakened past the 7.25 level against the dollar as economic data from China disappointed. Manufacturing PMI came in below expectations."
        },
        {
            "title": "Oil prices surge on OPEC+ production cut extension",
            "source": "oilprice",
            "url": "https://oilprice.com/example1",
            "date": "05/24",
            "summary": "Crude oil prices jumped 3% after OPEC+ announced they would extend production cuts through the end of the year. Brent crude topped $82 per barrel."
        },
        {
            "title": "China's tech sector faces new regulatory crackdown",
            "source": "scmp",
            "url": "https://scmp.com/example1",
            "date": "05/24",
            "summary": "Chinese regulators announced new restrictions on tech companies, targeting data privacy and anti-monopoly concerns. Major tech stocks fell in response."
        },
        {
            "title": "ECB holds rates steady, signals caution on cuts",
            "source": "ecb",
            "url": "https://ecb.europa.eu/example1",
            "date": "05/24",
            "summary": "The European Central Bank kept interest rates unchanged and warned against premature rate cuts, citing persistent inflation pressures in the services sector."
        },
        {
            "title": "US jobless claims drop to lowest level in 3 months",
            "source": "market_news",
            "url": "https://finance.yahoo.com/example1",
            "date": "05/24",
            "summary": "Weekly jobless claims fell to 215,000, well below the expected 225,000, indicating a resilient labor market despite economic uncertainty."
        },
        {
            "title": "Gold hits new record high on geopolitical tensions",
            "source": "market_news",
            "url": "https://finance.yahoo.com/example2",
            "date": "05/24",
            "summary": "Gold prices reached a new all-time high of $2,680 per ounce as investors sought safe-haven assets amid escalating tensions in the Middle East."
        },
        {
            "title": "Bank of Japan maintains ultra-loose policy",
            "source": "boj",
            "url": "https://boj.or.jp/example1",
            "date": "05/24",
            "summary": "The Bank of Japan kept its negative interest rate policy unchanged and maintained its yield curve control framework, disappointing markets expecting a policy shift."
        },
    ]
}

# 创建 collector 实例
collector = MacroInfoCollector()
collector.data = mock_data
collector.summary = collector._generate_summary()

# 生成报告
report = collector.format_report()

# 只显示新闻部分
lines = report.split('\n')
in_news = False
for line in lines:
    if '📰 【近期重要动态】' in line:
        in_news = True
    if in_news:
        print(line)
        if '⚠️  免责声明' in line:
            break

print("\n" + "="*60)
print("新闻数量:", len(mock_data["news"]))
print("="*60)
