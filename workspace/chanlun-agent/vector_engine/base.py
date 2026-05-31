"""向量引擎基类 — 所有后端实现必须遵守的契约"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class VectorRecord:
    """一条向量记录"""
    id: str                        # 唯一标识（如 "SH600000_20240101_20240115"）
    vector: np.ndarray             # 向量
    metadata: dict[str, Any] = field(default_factory=dict)
    # metadata 示例：
    # {
    #   "symbol": "SH600000",
    #   "start_date": "2024-01-01",
    #   "end_date": "2024-01-15",
    #   "label": "上升趋势",
    #   "return_5d": 0.032,       # 后5日收益率
    #   "return_10d": 0.058,      # 后10日收益率
    #   "max_drawdown": -0.015,   # 后续最大回撤
    # }


@dataclass
class SearchResult:
    """检索结果"""
    record: VectorRecord
    score: float                   # 相似度分数（0~1，越大越相似）


class VectorEngine(ABC):
    """向量引擎抽象基类"""

    @abstractmethod
    def build_index(self, records: list[VectorRecord]) -> None:
        """构建索引"""
        ...

    @abstractmethod
    def search(self, query: np.ndarray, top_k: int = 10) -> list[SearchResult]:
        """检索最相似的 top_k 条记录"""
        ...

    @abstractmethod
    def add(self, record: VectorRecord) -> None:
        """增量添加一条记录"""
        ...

    @abstractmethod
    def save(self, path: str) -> None:
        """持久化索引到磁盘"""
        ...

    @abstractmethod
    def load(self, path: str) -> None:
        """从磁盘加载索引"""
        ...

    @abstractmethod
    def stats(self) -> dict:
        """返回索引统计信息"""
        ...
