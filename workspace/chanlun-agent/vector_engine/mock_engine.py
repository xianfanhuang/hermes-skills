"""Mock 后端 — 测试用，不依赖任何外部库"""

import numpy as np
from .base import SearchResult, VectorEngine, VectorRecord


class MockEngine(VectorEngine):
    """内存向量引擎，用于测试和开发"""

    def __init__(self, dimension: int = 64):
        self.dimension = dimension
        self._records: list[VectorRecord] = []

    def build_index(self, records: list[VectorRecord]) -> None:
        self._records = list(records)

    def search(self, query: np.ndarray, top_k: int = 10) -> list[SearchResult]:
        if not self._records:
            return []

        # 暴力余弦相似度计算
        q = query / (np.linalg.norm(query) + 1e-10)
        scored = []
        for r in self._records:
            v = r.vector / (np.linalg.norm(r.vector) + 1e-10)
            score = float(np.dot(q, v))
            scored.append(SearchResult(record=r, score=(score + 1) / 2))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def add(self, record: VectorRecord) -> None:
        self._records.append(record)

    def save(self, path: str) -> None:
        pass  # Mock 不持久化

    def load(self, path: str) -> None:
        pass

    def stats(self) -> dict:
        return {"backend": "mock", "total": len(self._records)}
