"""FAISS 后端 — 本地向量检索，零部署"""

import json
from pathlib import Path

import faiss
import numpy as np

from .base import SearchResult, VectorEngine, VectorRecord


class FAISSEngine(VectorEngine):
    """基于 FAISS 的本地向量引擎"""

    def __init__(self, dimension: int = 64, metric: str = "cosine"):
        """
        Args:
            dimension: 向量维度
            metric: "cosine"（余弦相似度）或 "l2"（欧氏距离）
        """
        self.dimension = dimension
        self.metric = metric
        self._index: faiss.IndexFlat | None = None
        self._records: list[VectorRecord] = []

    def build_index(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        self.dimension = len(records[0].vector)
        self._records = list(records)

        vectors = np.array([r.vector for r in records], dtype=np.float32)

        if self.metric == "cosine":
            # FAISS IndexFlatIP 需要归一化向量才能做余弦相似度
            faiss.normalize_L2(vectors)
            self._index = faiss.IndexFlatIP(self.dimension)
        else:
            self._index = faiss.IndexFlatL2(self.dimension)

        self._index.add(vectors)

    def search(self, query: np.ndarray, top_k: int = 10) -> list[SearchResult]:
        if self._index is None or self._index.ntotal == 0:
            return []

        q = np.array([query], dtype=np.float32)
        if self.metric == "cosine":
            faiss.normalize_L2(q)

        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(q, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            # cosine: score 范围 [-1, 1]，转为 [0, 1]
            s = (float(score) + 1) / 2 if self.metric == "cosine" else float(score)
            results.append(SearchResult(record=self._records[idx], score=s))
        return results

    def add(self, record: VectorRecord) -> None:
        v = np.array([record.vector], dtype=np.float32)
        if self.metric == "cosine":
            faiss.normalize_L2(v)
        if self._index is None:
            if self.metric == "cosine":
                self._index = faiss.IndexFlatIP(self.dimension)
            else:
                self._index = faiss.IndexFlatL2(self.dimension)
        self._index.add(v)
        self._records.append(record)

    def save(self, path: str) -> None:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(p / "index.faiss"))
        meta = [
            {"id": r.id, "metadata": r.metadata, "vector": r.vector.tolist()}
            for r in self._records
        ]
        (p / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    def load(self, path: str) -> None:
        p = Path(path)
        self._index = faiss.read_index(str(p / "index.faiss"))
        meta = json.loads((p / "meta.json").read_text())
        self._records = [
            VectorRecord(id=m["id"], vector=np.array(m["vector"], dtype=np.float32), metadata=m["metadata"])
            for m in meta
        ]

    def stats(self) -> dict:
        return {
            "backend": "faiss",
            "metric": self.metric,
            "dimension": self.dimension,
            "total": self._index.ntotal if self._index else 0,
        }
