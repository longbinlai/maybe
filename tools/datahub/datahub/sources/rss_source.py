"""
RSS 数据源实现

支持标准的 RSS 2.0 和 Atom 格式
"""

from typing import List
from datetime import datetime
import feedparser
import ssl

from ..core.base_source import BaseDataSource, DataSourceResult, DataItem, ValidationResult


class RSSSource(BaseDataSource):
    """RSS 数据源"""
    
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.url = config.get('url')
        self.feed_type = config.get('feed_type', 'rss')  # rss or atom
        self.max_items = config.get('max_items', 20)
        
        # 忽略 SSL 验证（某些源需要）
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def fetch(self) -> DataSourceResult:
        """获取 RSS 数据"""
        try:
            # 解析 RSS
            feed = feedparser.parse(self.url)
            
            if not feed.entries:
                return DataSourceResult(
                    source_name=self.name,
                    source_type='rss',
                    category=self.category,
                    status='failed',
                    error='没有获取到数据'
                )
            
            # 提取数据项
            items = []
            for entry in feed.entries[:self.max_items]:
                item = self._parse_entry(entry)
                if item:
                    items.append(item)
            
            # 验证数据质量
            validation = self.validate(items)
            
            # 确定状态
            if validation.is_valid:
                status = 'success'
            elif validation.score >= 50:
                status = 'degraded'
            else:
                status = 'failed'
            
            return DataSourceResult(
                source_name=self.name,
                source_type='rss',
                category=self.category,
                status=status,
                items=items,
                validation=validation
            )
        
        except Exception as e:
            return DataSourceResult(
                source_name=self.name,
                source_type='rss',
                category=self.category,
                status='failed',
                error=str(e)
            )
    
    def _parse_entry(self, entry) -> DataItem:
        """解析单条 RSS 条目"""
        try:
            # 提取标题
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            # 提取链接
            url = entry.get('link', '')
            if not url:
                return None
            
            # 提取内容（优先使用 summary，否则使用 description）
            content = entry.get('summary', entry.get('description', ''))
            content = content.strip()
            
            # 提取发布时间
            published = self._parse_date(entry)
            if not published:
                published = datetime.now()
            
            # 生成唯一 ID
            item_id = DataItem.generate_id(self.name, url, title)
            
            # 提取元数据
            metadata = {}
            if 'author' in entry:
                metadata['author'] = entry.get('author')
            if 'tags' in entry:
                metadata['tags'] = [tag.get('term') for tag in entry.get('tags', []) if tag.get('term')]
            
            return DataItem(
                id=item_id,
                source=self.name,
                category=self.category,
                title=title,
                content=content,
                url=url,
                published=published,
                metadata=metadata
            )
        
        except Exception as e:
            return None
    
    def _parse_date(self, entry) -> datetime:
        """解析日期"""
        try:
            # 尝试使用 feedparser 的日期解析（字典格式）
            if 'published_parsed' in entry and entry['published_parsed']:
                return datetime(*entry['published_parsed'][:6])
            elif 'updated_parsed' in entry and entry['updated_parsed']:
                return datetime(*entry['updated_parsed'][:6])

            # 尝试手动解析常见格式
            date_str = entry.get('published', entry.get('updated', ''))
            if date_str:
                # 常见格式
                formats = [
                    '%a, %d %b %Y %H:%M:%S %z',
                    '%Y-%m-%dT%H:%M:%S%z',
                    '%Y-%m-%d %H:%M:%S',
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue

            return None

        except Exception:
            return None
