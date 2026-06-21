"""
NewsAPI 数据源单元测试

使用 mock 模拟 API 响应，验证 NewsAPISource 的行为
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from datahub.sources.newsapi_source import NewsAPISource


class TestNewsAPISource(unittest.TestCase):
    """NewsAPISource 测试"""

    def _make_config(self, **overrides):
        """构建测试配置"""
        config = {
            'api_key': 'test-api-key-123',
            'endpoint': 'everything',
            'query': 'Federal Reserve OR interest rate',
            'language': 'en',
            'page_size': 10,
            'sort_by': 'publishedAt',
            'category': 'news',
            'priority': 'high',
            'enabled': True,
            'timeout': 15,
        }
        config.update(overrides)
        return config

    def test_config_parsing(self):
        """验证配置正确加载"""
        config = self._make_config()
        source = NewsAPISource('test_newsapi', config)

        self.assertEqual(source.name, 'test_newsapi')
        self.assertEqual(source.api_key, 'test-api-key-123')
        self.assertEqual(source.endpoint, 'everything')
        self.assertEqual(source.query, 'Federal Reserve OR interest rate')
        self.assertEqual(source.language, 'en')
        self.assertEqual(source.page_size, 10)
        self.assertEqual(source.sort_by, 'publishedAt')
        self.assertEqual(source.category, 'news')
        self.assertTrue(source.enabled)

    def test_config_top_headlines(self):
        """验证 top-headlines endpoint 配置"""
        config = self._make_config(endpoint='top-headlines', country='us')
        source = NewsAPISource('test_headlines', config)

        self.assertEqual(source._get_url(), 'https://newsapi.org/v2/top-headlines')
        params = source._build_params()
        self.assertEqual(params['country'], 'us')

    def test_config_env_fallback(self):
        """验证 API Key 从环境变量回退"""
        config = self._make_config()
        del config['api_key']

        with patch.dict('os.environ', {'NEWSAPI_KEY': 'env-key-456'}):
            source = NewsAPISource('test_env', config)
            self.assertEqual(source.api_key, 'env-key-456')

    def test_missing_api_key(self):
        """验证缺少 API Key 时返回 failed"""
        config = self._make_config(api_key='')

        with patch.dict('os.environ', {}, clear=True):
            source = NewsAPISource('test_no_key', config)
            result = source.fetch()

        self.assertEqual(result.status, 'failed')
        self.assertIn('API Key', result.error)

    @patch('datahub.sources.newsapi_source.requests.get')
    def test_fetch_success(self, mock_get):
        """验证成功获取数据并生成 DataItem"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'ok',
            'totalResults': 3,
            'articles': [
                {
                    'source': {'id': 'bloomberg', 'name': 'Bloomberg'},
                    'author': 'John Doe',
                    'title': 'Fed raises interest rates by 25 basis points',
                    'description': 'The Federal Reserve announced a 25bp rate hike.',
                    'url': 'https://example.com/article1',
                    'publishedAt': '2026-06-18T10:00:00Z',
                    'content': 'Full article content about monetary policy and interest rates.'
                },
                {
                    'source': {'id': 'reuters', 'name': 'Reuters'},
                    'author': 'Jane Smith',
                    'title': 'Inflation data shows cooling trend',
                    'description': 'Latest CPI data indicates inflation is slowing.',
                    'url': 'https://example.com/article2',
                    'publishedAt': '2026-06-17T14:30:00Z',
                    'content': 'Detailed analysis of inflation metrics.'
                },
                {
                    'source': {'id': 'wsj', 'name': 'Wall Street Journal'},
                    'author': None,
                    'title': 'Markets react to Fed decision',
                    'description': 'Stock markets rallied after the Fed announcement.',
                    'url': 'https://example.com/article3',
                    'publishedAt': '2026-06-18T16:00:00Z',
                    'content': 'Market analysis following Federal Reserve decision.'
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        config = self._make_config()
        source = NewsAPISource('test_success', config)
        result = source.fetch()

        self.assertIn(result.status, ('success', 'degraded'))
        self.assertEqual(len(result.items), 3)

        # 验证第一条数据
        item = result.items[0]
        self.assertEqual(item.title, 'Fed raises interest rates by 25 basis points')
        self.assertEqual(item.url, 'https://example.com/article1')
        self.assertEqual(item.metadata['news_source'], 'Bloomberg')
        self.assertEqual(item.metadata['author'], 'John Doe')
        self.assertIsNotNone(item.published)

        # 验证 API 被正确调用
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        self.assertIn('apiKey', call_kwargs.kwargs.get('params', {}))

    @patch('datahub.sources.newsapi_source.requests.get')
    def test_fetch_api_error(self, mock_get):
        """验证网络错误时返回 failed 状态"""
        mock_get.side_effect = Exception('Connection timeout')

        config = self._make_config()
        source = NewsAPISource('test_error', config)
        result = source.fetch()

        self.assertEqual(result.status, 'failed')
        self.assertIn('Connection timeout', result.error)

    @patch('datahub.sources.newsapi_source.requests.get')
    def test_fetch_http_error(self, mock_get):
        """验证 HTTP 错误时的行为"""
        import requests as req
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = req.exceptions.HTTPError('429 Too Many Requests')
        mock_get.return_value = mock_response

        config = self._make_config()
        source = NewsAPISource('test_http_error', config)
        result = source.fetch()

        self.assertEqual(result.status, 'failed')
        self.assertIn('429', result.error)

    @patch('datahub.sources.newsapi_source.requests.get')
    def test_empty_response(self, mock_get):
        """验证空文章列表时返回 degraded 状态"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'ok',
            'totalResults': 0,
            'articles': []
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        config = self._make_config()
        source = NewsAPISource('test_empty', config)
        result = source.fetch()

        self.assertEqual(result.status, 'degraded')
        self.assertEqual(len(result.items), 0)
        self.assertIn('没有获取到文章', result.error)

    @patch('datahub.sources.newsapi_source.requests.get')
    def test_api_error_status(self, mock_get):
        """验证 API 返回非 ok 状态时的处理"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'error',
            'message': 'API key is invalid'
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        config = self._make_config()
        source = NewsAPISource('test_api_err', config)
        result = source.fetch()

        self.assertEqual(result.status, 'failed')
        self.assertIn('API key is invalid', result.error)

    @patch('datahub.sources.newsapi_source.requests.get')
    def test_article_without_required_fields(self, mock_get):
        """验证缺少必填字段的文章被跳过"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'ok',
            'totalResults': 2,
            'articles': [
                {
                    'source': {'name': 'Test'},
                    'title': '',  # 空标题
                    'url': 'https://example.com/1',
                    'publishedAt': '2026-06-18T10:00:00Z',
                },
                {
                    'source': {'name': 'Test'},
                    'title': 'Valid Article',
                    'url': 'https://example.com/2',
                    'description': 'A valid article',
                    'publishedAt': '2026-06-18T10:00:00Z',
                    'content': 'Valid content here.'
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        config = self._make_config()
        source = NewsAPISource('test_skip', config)
        result = source.fetch()

        # 只有有效文章被包含
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].title, 'Valid Article')

    @patch('datahub.sources.newsapi_source.requests.get')
    def test_chinese_query(self, mock_get):
        """验证中文查询参数"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'ok',
            'totalResults': 1,
            'articles': [
                {
                    'source': {'name': '新华网'},
                    'title': '央行宣布降准50个基点',
                    'description': '中国人民银行决定下调存款准备金率。',
                    'url': 'https://example.com/cn1',
                    'publishedAt': '2026-06-18T08:00:00Z',
                    'content': '详细报道央行货币政策调整。'
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        config = self._make_config(
            query='中国经济 OR 央行 OR GDP',
            language='zh',
        )
        source = NewsAPISource('test_chinese', config)
        result = source.fetch()

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].title, '央行宣布降准50个基点')

        # 验证请求参数包含中文查询
        call_params = mock_get.call_args.kwargs.get('params', {})
        self.assertEqual(call_params['q'], '中国经济 OR 央行 OR GDP')
        self.assertEqual(call_params['language'], 'zh')


if __name__ == '__main__':
    unittest.main()
