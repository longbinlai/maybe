"""
数据源注册中心

管理所有数据源的生命周期，提供统一的访问接口
"""

import sys
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_source import BaseDataSource, DataSourceResult, DataItem
from .history_store import HistoryStore


# 全局安静模式标志（供 SourceRegistry 使用）
_QUIET_MODE = False


def set_registry_quiet_mode(quiet: bool):
    """设置 SourceRegistry 的安静模式"""
    global _QUIET_MODE
    _QUIET_MODE = quiet


def _registry_print(msg: str):
    """进度信息始终输出到 stderr（不污染 stdout），安静模式时完全静默"""
    if not _QUIET_MODE:
        print(msg, file=sys.stderr)


class SourceRegistry:
    """
    数据源注册中心
    
    功能：
    - 从配置文件加载数据源
    - 管理数据源生命周期
    - 提供统一的数据获取接口
    - 结果缓存和持久化
    """
    
    def __init__(self, config_path: str = None, cache_dir: str = None,
                 history_store: HistoryStore = None, enable_history: bool = True):
        self.sources: Dict[str, BaseDataSource] = {}
        self.config_path = config_path
        self.cache_dir = Path(cache_dir) if cache_dir else None

        # 历史数据存储（PostgreSQL）
        # 可以传入已有实例，或自动创建（连接失败时 graceful degrade）
        if history_store is not None:
            self.history_store = history_store
        elif enable_history:
            try:
                self.history_store = HistoryStore()
            except Exception:
                self.history_store = None
        else:
            self.history_store = None

        if config_path:
            self.load_from_config(config_path)
    
    def load_from_config(self, config_path: str):
        """从YAML配置加载数据源"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 导入数据源类（避免循环导入）
        from ..sources.rss_source import RSSSource
        from ..sources.yfinance_source import YFinanceSource
        from ..sources.newsapi_source import NewsAPISource

        source_types = {
            'rss': RSSSource,
            'yfinance': YFinanceSource,
            'newsapi': NewsAPISource,
        }
        
        for source_name, source_config in config.get('sources', {}).items():
            source_type = source_config.get('type')
            if source_type not in source_types:
                _registry_print(f"⚠️  未知数据源类型: {source_type} ({source_name})")
                continue

            source_class = source_types[source_type]
            source = source_class(source_name, source_config)

            if source.enabled:
                self.register(source)
                _registry_print(f"✅ 已加载: {source_name} ({source_type})")
    
    def register(self, source: BaseDataSource):
        """注册数据源"""
        self.sources[source.name] = source
    
    def unregister(self, source_name: str):
        """注销数据源"""
        if source_name in self.sources:
            del self.sources[source_name]
    
    def get_source(self, source_name: str) -> Optional[BaseDataSource]:
        """获取数据源"""
        return self.sources.get(source_name)
    
    def list_sources(self) -> List[str]:
        """列出所有数据源"""
        return list(self.sources.keys())
    
    def fetch_all(self, use_cache: bool = True, cache_ttl: int = 3600, concurrency: int = 4,
                  yf_concurrency: int = 1, use_priority: bool = True, quiet: bool = False) -> Dict[str, DataSourceResult]:
        """
        获取所有数据源的数据

        策略（use_priority=True 时）：
        - 按优先级分组：Phase 1 (股指/风险) → Phase 2 (汇率/商品) → Phase 3 (持仓股价) → Phase 4 (新闻)
        - YF 源串行执行（避免 Yahoo 限速）
        - RSS/NewsAPI 源并发执行（不同服务器）

        策略（use_priority=False 时）：
        - YF 源串行执行
        - RSS/NewsAPI 源并发执行

        Args:
            use_cache: 是否使用缓存
            cache_ttl: 默认缓存有效期（秒）
            concurrency: RSS/NewsAPI 并发数
            yf_concurrency: YF 源并发数（建议 1，避免限速）
            use_priority: 是否使用优先级调度
            quiet: 安静模式（True 时进度信息输出到 stderr）

        Returns:
            Dict[source_name, DataSourceResult]
        """
        # 清理过期缓存
        if self.cache_dir:
            self._prune_cache(cache_ttl)

        # 定义获取函数（供调度器调用）
        def fetch_func(name, source):
            return self._fetch_single(name, source, use_cache, default_cache_ttl=cache_ttl)

        # 识别 YF 源
        yf_sources = {name for name, source in self.sources.items()
                      if source.__class__.__name__ == 'YFinanceSource'}

        if use_priority:
            # 使用优先级调度器
            from .priority_scheduler import PriorityScheduler, set_quiet_mode

            # 设置安静模式（同时传播到 registry 和 scheduler）
            set_quiet_mode(quiet)
            set_registry_quiet_mode(quiet)

            scheduler = PriorityScheduler(
                yf_concurrency=yf_concurrency,
                rss_concurrency=concurrency
            )
            return scheduler.schedule(
                sources=self.sources,
                fetch_func=fetch_func,
                yf_sources=yf_sources
            )
        else:
            # 原有逻辑：YF 串行，其他并发
            results = {}

            yfinance_sources = {n: s for n, s in self.sources.items() if n in yf_sources}
            other_sources = {n: s for n, s in self.sources.items() if n not in yf_sources}

            # Phase 1: YF 串行
            if yfinance_sources:
                for name, source in yfinance_sources.items():
                    _registry_print(f"🔄 {name}: 获取数据...")
                    results[name] = fetch_func(name, source)

            # Phase 2: RSS/NewsAPI 并发
            if other_sources:
                if concurrency <= 1 or len(other_sources) <= 1:
                    for name, source in other_sources.items():
                        results[name] = fetch_func(name, source)
                else:
                    workers = min(concurrency, len(other_sources))
                    _registry_print(f"⚡ 并发获取 RSS/NewsAPI 数据（workers={workers}）...")

                    with ThreadPoolExecutor(max_workers=workers) as executor:
                        future_to_name = {
                            executor.submit(fetch_func, name, source): name
                            for name, source in other_sources.items()
                        }

                        for future in as_completed(future_to_name):
                            source_name = future_to_name[future]
                            try:
                                results[source_name] = future.result()
                            except Exception as e:
                                _registry_print(f"❌ {source_name}: {str(e)}")
                                source = self.sources[source_name]
                                results[source_name] = DataSourceResult(
                                    source_name=source_name,
                                    source_type=source.__class__.__name__,
                                    category=source.category,
                                    status='failed',
                                    error=str(e)
                                )

            return results

    def _fetch_single(self, source_name: str, source: BaseDataSource, use_cache: bool = True, default_cache_ttl: int = 3600) -> DataSourceResult:
        """
        获取单个数据源的数据（线程安全）

        缓存策略：
        - 优先使用源级别的 cache_ttl 配置，否则用默认值
        - fetch 成功：写入缓存
        - fetch 失败但有过期缓存：回退到旧数据（标记 degraded）
        - fetch 失败且无缓存：返回 failed

        Args:
            source_name: 数据源名称
            source: 数据源实例
            use_cache: 是否使用缓存
            default_cache_ttl: 默认缓存有效期（秒）

        Returns:
            DataSourceResult
        """
        # 每个源可以配置自己的 cache_ttl
        ttl = source.cache_ttl if source.cache_ttl is not None else default_cache_ttl

        try:
            # 检查缓存
            if use_cache and self.cache_dir:
                cached = self._load_from_cache(source_name, ttl)
                if cached:
                    _registry_print(f"📦 {source_name}: 使用缓存")
                    return cached

            # 获取新数据
            _registry_print(f"🔄 {source_name}: 获取数据...")
            fetch_start = datetime.now()
            result = source.fetch()
            fetch_duration_ms = int((datetime.now() - fetch_start).total_seconds() * 1000)

            # 保存到缓存
            if self.cache_dir and result.status == 'success':
                self._save_to_cache(source_name, result)

            # 写入历史存储（PostgreSQL）
            if self.history_store and self.history_store.available:
                if result.status == 'success' and result.items:
                    self.history_store.save_items(source_name, result.items)
                self.history_store.log_fetch(
                    source_name, result.status, len(result.items),
                    duration_ms=fetch_duration_ms,
                    error=result.error
                )

            # fetch 失败，尝试回退到过期缓存
            if result.status == 'failed' and self.cache_dir:
                stale = self._load_from_cache(source_name, ttl=999999999)  # 忽略过期
                if stale:
                    _registry_print(f"♻️  {source_name}: 回退到过期缓存 (status → degraded)")
                    stale.status = 'degraded'
                    stale.error = f"Fetch failed ({result.error}), using stale cache"
                    return stale

            return result

        except Exception as e:
            _registry_print(f"❌ {source_name}: {str(e)}")

            # 异常时也尝试回退到过期缓存
            if self.cache_dir:
                stale = self._load_from_cache(source_name, ttl=999999999)
                if stale:
                    _registry_print(f"♻️  {source_name}: 回退到过期缓存 (status → degraded)")
                    stale.status = 'degraded'
                    stale.error = f"Exception ({e}), using stale cache"
                    return stale

            return DataSourceResult(
                source_name=source_name,
                source_type=source.__class__.__name__,
                category=source.category,
                status='failed',
                error=str(e)
            )
    
    def fetch_by_category(self, category: str) -> Dict[str, DataSourceResult]:
        """按类别获取数据"""
        results = {}
        for source_name, source in self.sources.items():
            if source.category == category:
                try:
                    result = source.fetch()
                    results[source_name] = result
                except Exception as e:
                    results[source_name] = DataSourceResult(
                        source_name=source_name,
                        source_type=source.__class__.__name__,
                        category=source.category,
                        status='failed',
                        error=str(e)
                    )
        return results
    
    def generate_report(self, results: Dict[str, DataSourceResult]) -> Dict[str, Any]:
        """生成汇总报告"""
        total_sources = len(results)
        success_count = sum(1 for r in results.values() if r.status == 'success')
        degraded_count = sum(1 for r in results.values() if r.status == 'degraded')
        failed_count = sum(1 for r in results.values() if r.status == 'failed')
        
        # 按类别统计
        by_category = {}
        for result in results.values():
            if result.category not in by_category:
                by_category[result.category] = {
                    'total': 0,
                    'success': 0,
                    'items_count': 0,
                }
            by_category[result.category]['total'] += 1
            if result.status == 'success':
                by_category[result.category]['success'] += 1
            by_category[result.category]['items_count'] += len(result.items)
        
        # 收集所有数据项
        all_items = []
        for result in results.values():
            if result.status == 'success':
                all_items.extend(result.items)
        
        # 生成报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_sources': total_sources,
                'success': success_count,
                'degraded': degraded_count,
                'failed': failed_count,
                'success_rate': (success_count / total_sources * 100) if total_sources > 0 else 0,
            },
            'by_category': by_category,
            'total_items': len(all_items),
            'sources': {name: result.to_dict() for name, result in results.items()},
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any], output_path: str):
        """保存报告到文件"""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        _registry_print(f"💾 报告已保存: {output}")
    
    def _load_from_cache(self, source_name: str, ttl: int) -> Optional[DataSourceResult]:
        """从缓存加载数据"""
        if not self.cache_dir:
            return None
        
        cache_file = self.cache_dir / f"{source_name}.json"
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            fetched_at = datetime.fromisoformat(data['fetched_at'])
            if (datetime.now() - fetched_at).total_seconds() > ttl:
                return None
            
            # 重建 DataSourceResult
            items = [
                DataItem(
                    id=item['id'],
                    source=item['source'],
                    category=item['category'],
                    title=item['title'],
                    content=item['content'],
                    url=item['url'],
                    published=datetime.fromisoformat(item['published']),
                    metadata=item.get('metadata', {})
                )
                for item in data.get('items', [])
            ]
            
            return DataSourceResult(
                source_name=data['source_name'],
                source_type=data['source_type'],
                category=data['category'],
                status=data['status'],
                items=items,
                fetched_at=fetched_at
            )
        except Exception:
            return None
    
    def _save_to_cache(self, source_name: str, result: DataSourceResult):
        """保存数据到缓存"""
        if not self.cache_dir:
            return

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / f"{source_name}.json"

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

    def _prune_cache(self, default_ttl: int = 3600, max_files: int = 50):
        """
        清理过期缓存文件

        策略：
        1. 删除超过 TTL 的文件（每个源可配置自己的 TTL）
        2. 如果文件数超过 max_files，删除最旧的文件

        Args:
            default_ttl: 默认缓存有效期（秒）
            max_files: 最大缓存文件数
        """
        if not self.cache_dir or not self.cache_dir.exists():
            return

        cache_files = list(self.cache_dir.glob("*.json"))
        if not cache_files:
            return

        now = datetime.now()
        removed = 0

        # Phase 1: 删除过期文件
        for cache_file in cache_files:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                source_name = cache_file.stem
                fetched_at = datetime.fromisoformat(data.get('fetched_at', now.isoformat()))

                # 使用源级别的 TTL（如果配置了）
                source = self.sources.get(source_name)
                ttl = (source.cache_ttl if source and source.cache_ttl is not None
                       else default_ttl)

                age_seconds = (now - fetched_at).total_seconds()
                if age_seconds > ttl:
                    cache_file.unlink()
                    removed += 1

            except Exception:
                # 文件损坏或无法解析，直接删除
                try:
                    cache_file.unlink()
                    removed += 1
                except Exception:
                    pass

        if removed > 0:
            _registry_print(f"🗑️  缓存清理: 删除 {removed} 个过期文件")

        # Phase 2: 如果文件数仍然超过限制，删除最旧的
        cache_files = list(self.cache_dir.glob("*.json"))
        if len(cache_files) > max_files:
            # 按修改时间排序，删除最旧的
            cache_files.sort(key=lambda f: f.stat().st_mtime)
            excess = len(cache_files) - max_files
            for f in cache_files[:excess]:
                try:
                    f.unlink()
                    _registry_print(f"🗑️  缓存清理: 删除多余文件 {f.name}")
                except Exception:
                    pass
