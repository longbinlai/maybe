"""
基础数据源抽象类

所有数据源必须继承此类并实现 fetch() 方法
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib
import json


@dataclass
class DataItem:
    """统一数据项结构"""
    id: str
    source: str
    category: str
    title: str
    content: str
    url: str
    published: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'source': self.source,
            'category': self.category,
            'title': self.title,
            'content': self.content,
            'url': self.url,
            'published': self.published.isoformat(),
            'metadata': self.metadata,
        }
    
    @staticmethod
    def generate_id(source: str, url: str, title: str) -> str:
        """生成唯一ID"""
        content = f"{source}:{url}:{title}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    score: float  # 0-100
    issues: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSourceResult:
    """数据源获取结果"""
    source_name: str
    source_type: str
    category: str
    status: str  # 'success', 'degraded', 'failed'
    items: List[DataItem] = field(default_factory=list)
    validation: Optional[ValidationResult] = None
    error: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_name': self.source_name,
            'source_type': self.source_type,
            'category': self.category,
            'status': self.status,
            'items_count': len(self.items),
            'items': [item.to_dict() for item in self.items],
            'validation': {
                'is_valid': self.validation.is_valid,
                'score': self.validation.score,
                'issues': self.validation.issues,
                'details': self.validation.details,
            } if self.validation else None,
            'error': self.error,
            'fetched_at': self.fetched_at.isoformat(),
        }


class BaseDataSource(ABC):
    """
    数据源基类
    
    所有数据源必须实现:
    - fetch(): 获取数据
    - validate(): 验证数据质量
    
    可选实现:
    - test_connection(): 测试连接
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.category = config.get('category', 'unknown')
        self.priority = config.get('priority', 'medium')
        self.enabled = config.get('enabled', True)
    
    @abstractmethod
    def fetch(self) -> DataSourceResult:
        """获取数据"""
        pass
    
    def validate(self, items: List[DataItem]) -> ValidationResult:
        """
        验证数据质量

        默认实现检查基本指标，子类可以覆盖
        """
        issues = []
        critical_issues = []  # 严重问题，直接导致验证失败
        score = 100
        found_keywords = []  # 初始化为空列表

        # 检查数据是否为空（最严重问题）
        if len(items) == 0:
            critical_issues.append("数据为空")
            score -= 60  # 空数据扣 60 分，确保得分 < 50
            # 空数据直接返回，不需要进一步检查
            return ValidationResult(
                is_valid=False,
                score=max(0, score),
                issues=critical_issues,
                details={
                    'items_count': 0,
                    'keywords_found': [],
                }
            )

        # 检查数据量（严重问题）
        min_items = self.config.get('validation', {}).get('min_items', 5)
        if len(items) < min_items:
            critical_issues.append(f"数据量不足: {len(items)} < {min_items}")
            score -= 20

        # 检查时效性（严重问题）
        if items:
            latest = max(item.published for item in items)
            # 处理时区问题：将 timezone-aware 转换为 naive
            if latest.tzinfo is not None:
                latest = latest.replace(tzinfo=None)
            days_old = (datetime.now() - latest).days
            max_age = self.config.get('validation', {}).get('max_age_days', 7)

            if days_old > max_age:
                critical_issues.append(f"数据过旧: {days_old}天 > {max_age}天")
                score -= 15

        # 检查关键词覆盖（严重问题）
        expected_keywords = self.config.get('validation', {}).get('keywords', [])
        if expected_keywords and items:
            all_text = ' '.join([f"{item.title} {item.content}" for item in items]).lower()
            found_keywords = [kw for kw in expected_keywords if kw.lower() in all_text]
            coverage = len(found_keywords) / len(expected_keywords) * 100

            if coverage < 50:
                critical_issues.append(f"关键词覆盖率低: {coverage:.1f}%")
                score -= 15  # 增加到 15 分

        score = max(0, score)
        # 严重问题或分数过低都导致验证失败
        is_valid = len(critical_issues) == 0 and score >= 70

        return ValidationResult(
            is_valid=is_valid,
            score=score,
            issues=critical_issues + issues,
            details={
                'items_count': len(items),
                'keywords_found': found_keywords,
            }
        )
    
    def test_connection(self) -> bool:
        """测试连接（可选）"""
        try:
            result = self.fetch()
            return result.status == 'success'
        except Exception:
            return False
