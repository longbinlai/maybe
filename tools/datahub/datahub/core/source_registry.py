"""
数据源注册中心

管理所有数据源的生命周期，提供统一的访问接口
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_source import BaseDataSource, DataSourceResult, DataItem


class SourceRegistry:
    """
    数据源注册中心
    
    功能：
    - 从配置文件加载数据源
    - 管理数据源生命周期
    - 提供统一的数据获取接口
    - 结果缓存和持久化
    """
    
    def __init__(self, config_path: str = None, cache_dir: str = None):
        self.sources: Dict[str, BaseDataSource] = {}
        self.config_path = config_path
        self.cache_dir = Path(cache_dir) if cache_dir else None
        
        if config_path:
            self.load_from_config(config_path)
    
    def load_from_config(self, config_path: str):
        """从YAML配置加载数据源"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 导入数据源类（避免循环导入）
        from ..sources.rss_source import RSSSource
        from ..sources.yfinance_source import YFinanceSource
        
        source_types = {
            'rss': RSSSource,
            'yfinance': YFinanceSource,
        }
        
        for source_name, source_config in config.get('sources', {}).items():
            source_type = source_config.get('type')
            if source_type not in source_types:
                print(f"⚠️  未知数据源类型: {source_type} ({source_name})")
                continue
            
            source_class = source_types[source_type]
            source = source_class(source_name, source_config)
            
            if source.enabled:
                self.register(source)
                print(f"✅ 已加载: {source_name} ({source_type})")
    
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
    
    def fetch_all(self, use_cache: bool = True, cache_ttl: int = 3600, concurrency: int = 4) -> Dict[str, DataSourceResult]:
        """
        获取所有数据源的数据

        Args:
            use_cache: 是否使用缓存
            cache_ttl: 缓存有效期（秒）
            concurrency: 并发数（1=顺序执行，>1=并发执行）

        Returns:
            Dict[source_name, DataSourceResult]
        """
        if concurrency <= 1 or len(self.sources) <= 1:
            # 顺序执行
            results = {}
            for source_name, source in self.sources.items():
                result = self._fetch_single(source_name, source, use_cache, cache_ttl)
                results[source_name] = result
            return results

        # 并发执行
        results = {}
        print(f"⚡ 并发获取数据（workers={min(concurrency, len(self.sources))}）...")

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_name = {
                executor.submit(self._fetch_single, name, source, use_cache, cache_ttl): name
                for name, source in self.sources.items()
            }

            for future in as_completed(future_to_name):
                source_name = future_to_name[future]
                try:
                    result = future.result()
                    results[source_name] = result
                except Exception as e:
                    print(f"❌ {source_name}: {str(e)}")
                    source = self.sources[source_name]
                    results[source_name] = DataSourceResult(
                        source_name=source_name,
                        source_type=source.__class__.__name__,
                        category=source.category,
                        status='failed',
                        error=str(e)
                    )

        return results

    def _fetch_single(self, source_name: str, source: BaseDataSource, use_cache: bool = True, cache_ttl: int = 3600) -> DataSourceResult:
        """
        获取单个数据源的数据（线程安全）

        Args:
            source_name: 数据源名称
            source: 数据源实例
            use_cache: 是否使用缓存
            cache_ttl: 缓存有效期（秒）

        Returns:
            DataSourceResult
        """
        try:
            # 检查缓存
            if use_cache and self.cache_dir:
                cached = self._load_from_cache(source_name, cache_ttl)
                if cached:
                    print(f"📦 {source_name}: 使用缓存")
                    return cached

            # 获取新数据
            print(f"🔄 {source_name}: 获取数据...")
            result = source.fetch()

            # 保存到缓存
            if self.cache_dir and result.status == 'success':
                self._save_to_cache(source_name, result)

            return result

        except Exception as e:
            print(f"❌ {source_name}: {str(e)}")
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
        
        print(f"💾 报告已保存: {output}")
    
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
