"""
NewsAPI 数据源实现

通过 NewsAPI.org 获取新闻数据（免费层级：100 请求/天）
"""

import os
from typing import List
from datetime import datetime
import requests

from ..core.base_source import BaseDataSource, DataSourceResult, DataItem


class NewsAPISource(BaseDataSource):
    """NewsAPI 数据源"""

    BASE_URL_EVERYTHING = 'https://newsapi.org/v2/everything'
    BASE_URL_TOP_HEADLINES = 'https://newsapi.org/v2/top-headlines'

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.api_key = config.get('api_key') or os.environ.get('NEWSAPI_KEY', '')
        self.endpoint = config.get('endpoint', 'everything')  # everything or top-headlines
        self.query = config.get('query', '')
        self.language = config.get('language', 'en')
        self.country = config.get('country', '')  # 仅 top-headlines 使用
        self.page_size = config.get('page_size', 10)
        self.sort_by = config.get('sort_by', 'publishedAt')  # relevancy, popularity, publishedAt
        self.timeout = config.get('timeout', 15)  # 默认 15 秒超时

    def _get_url(self) -> str:
        """根据 endpoint 配置获取 API URL"""
        if self.endpoint == 'top-headlines':
            return self.BASE_URL_TOP_HEADLINES
        return self.BASE_URL_EVERYTHING

    def _build_params(self) -> dict:
        """构建请求参数"""
        params = {
            'apiKey': self.api_key,
            'pageSize': self.page_size,
            'language': self.language,
        }

        if self.endpoint == 'top-headlines':
            if self.country:
                params['country'] = self.country
            if self.query:
                params['q'] = self.query
        else:
            if self.query:
                params['q'] = self.query
            params['sortBy'] = self.sort_by

        return params

    def fetch(self) -> DataSourceResult:
        """获取 NewsAPI 数据"""
        try:
            if not self.api_key:
                return DataSourceResult(
                    source_name=self.name,
                    source_type='newsapi',
                    category=self.category,
                    status='failed',
                    error='未配置 API Key：请设置 api_key 或环境变量 NEWSAPI_KEY'
                )

            url = self._get_url()
            params = self._build_params()

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # 检查 API 响应状态
            if data.get('status') != 'ok':
                error_msg = data.get('message', '未知的 API 错误')
                return DataSourceResult(
                    source_name=self.name,
                    source_type='newsapi',
                    category=self.category,
                    status='failed',
                    error=f'API 返回错误: {error_msg}'
                )

            articles = data.get('articles', [])

            if not articles:
                return DataSourceResult(
                    source_name=self.name,
                    source_type='newsapi',
                    category=self.category,
                    status='degraded',
                    error='没有获取到文章数据'
                )

            # 转换文章为 DataItem
            items = []
            for article in articles:
                item = self._parse_article(article)
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
                source_type='newsapi',
                category=self.category,
                status=status,
                items=items,
                validation=validation
            )

        except requests.exceptions.RequestException as e:
            return DataSourceResult(
                source_name=self.name,
                source_type='newsapi',
                category=self.category,
                status='failed',
                error=f'网络请求失败: {str(e)}'
            )
        except Exception as e:
            return DataSourceResult(
                source_name=self.name,
                source_type='newsapi',
                category=self.category,
                status='failed',
                error=str(e)
            )

    def _parse_article(self, article: dict) -> DataItem:
        """解析单篇文章"""
        try:
            title = article.get('title', '').strip()
            if not title:
                return None

            url = article.get('url', '')
            if not url:
                return None

            # 提取内容（优先使用 content，否则使用 description）
            content = article.get('content') or article.get('description', '')
            content = content.strip()

            # 来源信息
            source_info = article.get('source', {})
            source_name = source_info.get('name', 'Unknown')

            # 解析发布时间
            published = self._parse_date(article.get('publishedAt', ''))
            if not published:
                published = datetime.now()

            # 生成唯一 ID
            item_id = DataItem.generate_id(self.name, url, title)

            # 提取元数据
            metadata = {
                'news_source': source_name,
            }
            if article.get('author'):
                metadata['author'] = article['author']

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

        except Exception:
            return None

    def _parse_date(self, date_str: str) -> datetime:
        """解析 NewsAPI 日期格式 (ISO 8601)"""
        try:
            if not date_str:
                return None
            # NewsAPI 使用 ISO 8601 格式：2026-05-24T08:00:00Z
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            return None
