"""
优先级调度器

按优先级顺序获取数据源：
1. Phase 1 (critical): 股指、风险指标
2. Phase 2 (important): 汇率、商品、中国ETF、央行新闻
3. Phase 3 (standard): 持仓股价、经济新闻
4. Phase 4 (best_effort): 新闻（允许降级）

YF 数据源串行执行（避免限速）
RSS/NewsAPI 数据源并发执行（不同服务器）

Fallback 机制：
- 同一 fallback_group 内的源按 fallback_priority 排序
- 高优先级失败时，自动尝试低优先级
- 只要组内有一个成功就停止尝试下一个
"""

from typing import Dict, List, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


# 优先级映射（数字越小优先级越高）
CATEGORY_PRIORITY = {
    # Phase 1: Critical (股指、风险指标)
    "market": 1,
    "risk": 1,

    # Phase 2: Important (汇率、商品、中国ETF、央行新闻)
    "forex": 2,
    "commodity": 2,
    "china_etf": 2,
    "central_bank": 2,

    # Phase 3: Standard (持仓股价、经济新闻)
    "stock_prices": 3,
    "economic_data": 3,

    # Phase 4: Best Effort (新闻)
    "news": 4,
    "market_news": 4,
    "china": 4,
    "rates": 4,
    "indicators": 4,
}


class PriorityScheduler:
    """优先级调度器"""

    def __init__(self, yf_concurrency: int = 1, rss_concurrency: int = 4):
        """
        Args:
            yf_concurrency: YF 数据源并发数（建议 1，避免限速）
            rss_concurrency: RSS/NewsAPI 数据源并发数（建议 4）
        """
        self.yf_concurrency = yf_concurrency
        self.rss_concurrency = rss_concurrency

    def group_by_priority(self, sources: Dict) -> Dict[int, List[Tuple[str, object]]]:
        """
        按优先级分组数据源

        Returns:
            {priority: [(name, source), ...]}
        """
        groups = {}

        for name, source in sources.items():
            # 获取 category
            category = getattr(source, 'category', 'unknown')

            # 特殊处理持仓股价（动态源）
            if name.startswith('yfinance_holdings'):
                priority = CATEGORY_PRIORITY.get('stock_prices', 3)
            else:
                priority = CATEGORY_PRIORITY.get(category, 5)

            if priority not in groups:
                groups[priority] = []
            groups[priority].append((name, source))

        return groups

    def sort_by_priority(self, groups: Dict[int, List]) -> List[Tuple[int, List]]:
        """按优先级排序"""
        return sorted(groups.items(), key=lambda x: x[0])

    def execute_phase(
        self,
        phase_name: str,
        sources: List[Tuple[str, object]],
        fetch_func,
        yf_sources: set
    ) -> Dict:
        """
        执行单个阶段的获取

        Args:
            phase_name: 阶段名称
            sources: [(name, source), ...]
            fetch_func: 获取函数 (name, source) -> result
            yf_sources: YF 数据源名称集合

        Returns:
            {name: result, ...}
        """
        results = {}

        # 分离 YF 和 RSS 源
        yf_items = [(n, s) for n, s in sources if n in yf_sources]
        rss_items = [(n, s) for n, s in sources if n not in yf_sources]

        print(f"\n{'='*60}")
        print(f"📍 {phase_name}")
        print(f"{'='*60}")

        # YF 源串行执行
        if yf_items:
            print(f"\n  🔄 YF 源 (串行, concurrency={self.yf_concurrency})")
            for name, source in yf_items:
                print(f"    - {name}...")
                results[name] = fetch_func(name, source)

        # RSS 源并发执行（支持 fallback）
        if rss_items:
            print(f"\n  ⚡ RSS/NewsAPI 源 (并发, concurrency={self.rss_concurrency})")
            
            # 按 fallback_group 分组
            fallback_groups = {}
            no_fallback = []
            
            for name, source in rss_items:
                group = getattr(source, 'fallback_group', None)
                if group:
                    if group not in fallback_groups:
                        fallback_groups[group] = []
                    priority = getattr(source, 'fallback_priority', 999)
                    fallback_groups[group].append((priority, name, source))
                else:
                    no_fallback.append((name, source))
            
            # 处理有 fallback 的组
            for group_name, items in fallback_groups.items():
                # 按 fallback_priority 排序
                items.sort(key=lambda x: x[0])
                print(f"    🔄 Fallback group: {group_name}")
                
                success = False
                for priority, name, source in items:
                    if success:
                        # 已经成功，跳过后续
                        print(f"      ⏭️  {name} (skipped, already have data)")
                        results[name] = None
                        continue
                    
                    print(f"      - {name} (priority={priority})...")
                    result = fetch_func(name, source)
                    results[name] = result
                    
                    # 检查是否成功
                    if result and result.status in ['success', 'degraded']:
                        print(f"      ✅ {name}")
                        success = True
                    else:
                        print(f"      ❌ {name}, trying next...")
            
            # 处理没有 fallback 的源（并发执行）
            if no_fallback:
                with ThreadPoolExecutor(max_workers=self.rss_concurrency) as executor:
                    future_to_name = {
                        executor.submit(fetch_func, name, source): name
                        for name, source in no_fallback
                    }

                    for future in as_completed(future_to_name):
                        name = future_to_name[future]
                        try:
                            results[name] = future.result()
                            print(f"    ✅ {name}")
                        except Exception as e:
                            print(f"    ❌ {name}: {e}")
                            results[name] = None

        return results

    def schedule(
        self,
        sources: Dict,
        fetch_func,
        yf_sources: set = None
    ) -> Dict:
        """
        按优先级调度获取

        Args:
            sources: {name: source, ...}
            fetch_func: 获取函数
            yf_sources: YF 数据源名称集合

        Returns:
            {name: result, ...}
        """
        if yf_sources is None:
            yf_sources = {n for n, s in sources.items()
                         if s.__class__.__name__ == 'YFinanceSource'}

        print("\n" + "="*60)
        print("🚀 开始优先级调度")
        print("="*60)

        start_time = datetime.now()

        # 按优先级分组
        groups = self.group_by_priority(sources)
        sorted_groups = self.sort_by_priority(groups)

        # 按阶段执行
        all_results = {}

        for priority, items in sorted_groups:
            phase_name = f"Phase {priority} (priority={priority})"
            phase_results = self.execute_phase(
                phase_name, items, fetch_func, yf_sources
            )
            all_results.update(phase_results)

        # 打印汇总
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n{'='*60}")
        print(f"✅ 调度完成 (耗时 {elapsed:.1f}s)")
        print(f"{'='*60}")

        success = sum(1 for r in all_results.values() if r is not None)
        total = len(all_results)
        print(f"成功: {success}/{total}")

        return all_results
