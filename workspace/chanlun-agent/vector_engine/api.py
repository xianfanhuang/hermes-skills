"""
高级 API — 一行调用完成特征提取 + 向量检索

用法：
    from vector_engine.api import VectorSearchAPI

    api = VectorSearchAPI(backend="faiss")

    # 构建索引
    api.build_from_bars(symbol="SH600000", bars_list=windowed_bars, bi_list=bi_list, ...)

    # 检索相似走势
    results = api.find_similar(current_bars, current_bi_list, ..., top_k=10)

    # 统计后续涨跌
    stats = api.analyze_returns(results)
"""

from dataclasses import dataclass
from typing import Any

import numpy as np

from .base import SearchResult, VectorEngine
from .factory import create_vector_engine
from .feature_extractor import (
    DIMENSION,
    ChanlunFeatures,
    extract_features_from_czsc,
    normalize_features,
)


@dataclass
class ReturnStats:
    """相似走势后续收益统计"""
    count: int
    avg_return_5d: float         # 平均5日收益率
    avg_return_10d: float        # 平均10日收益率
    win_rate_5d: float           # 5日胜率
    win_rate_10d: float          # 10日胜率
    avg_max_drawdown: float      # 平均最大回撤
    best_return: float           # 最佳收益
    worst_return: float          # 最差收益


class VectorSearchAPI:
    """向量检索高级 API"""

    def __init__(self, backend: str = "faiss", **engine_kwargs):
        self.engine: VectorEngine = create_vector_engine(backend, **engine_kwargs)
        self._all_features: list[ChanlunFeatures] = []

    def build_from_bars(
        self,
        symbol: str,
        windows: list[dict[str, Any]],
    ) -> None:
        """
        从多段行情窗口构建索引

        Args:
            symbol: 标的代码
            windows: 窗口列表，每个窗口包含：
                {
                    "bars": list[RawBar],
                    "bi_list": list[BI],
                    "fx_list": list[FX],
                    "zs_list": list[ZhongShu],
                    "start_date": str,
                    "end_date": str,
                    "label": str,           # 可选标签
                    "return_5d": float,     # 后5日收益率
                    "return_10d": float,    # 后10日收益率
                    "max_drawdown": float,  # 后续最大回撤
                }
        """
        from .base import VectorRecord

        records = []
        for w in windows:
            feat = extract_features_from_czsc(
                w["bars"], w["bi_list"], w.get("fx_list", []), w.get("zs_list", [])
            )
            self._all_features.append(feat)

            record_id = f"{symbol}_{w['start_date']}_{w['end_date']}"
            records.append(VectorRecord(
                id=record_id,
                vector=feat.vector,
                metadata={
                    "symbol": symbol,
                    "start_date": w["start_date"],
                    "end_date": w["end_date"],
                    "label": w.get("label", ""),
                    "return_5d": w.get("return_5d", 0),
                    "return_10d": w.get("return_10d", 0),
                    "max_drawdown": w.get("max_drawdown", 0),
                }
            ))

        # 标准化后构建索引
        if self._all_features:
            normalized = normalize_features(self._all_features)
            for i, v in enumerate(normalized):
                records[i].vector = v

        self.engine.build_index(records)

    def find_similar(
        self,
        bars: list,
        bi_list: list,
        fx_list: list = None,
        zs_list: list = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """
        检索与当前走势最相似的历史走势

        Returns:
            SearchResult 列表，包含相似走势和元数据
        """
        feat = extract_features_from_czsc(bars, bi_list, fx_list or [], zs_list or [])
        # 标准化查询向量（使用已有向量的统计量）
        query = feat.vector
        if self._all_features:
            vectors = np.array([f.vector for f in self._all_features], dtype=np.float32)
            mean = np.mean(vectors, axis=0)
            std = np.std(vectors, axis=0)
            std[std < 1e-10] = 1.0
            query = (query - mean) / std

        return self.engine.search(query, top_k)

    def analyze_returns(self, results: list[SearchResult]) -> ReturnStats:
        """
        统计相似走势的后续收益

        Args:
            results: find_similar 返回的结果

        Returns:
            ReturnStats 收益统计
        """
        if not results:
            return ReturnStats(0, 0, 0, 0, 0, 0, 0, 0)

        ret5 = [r.record.metadata.get("return_5d", 0) for r in results]
        ret10 = [r.record.metadata.get("return_10d", 0) for r in results]
        dd = [r.record.metadata.get("max_drawdown", 0) for r in results]

        return ReturnStats(
            count=len(results),
            avg_return_5d=np.mean(ret5),
            avg_return_10d=np.mean(ret10),
            win_rate_5d=sum(1 for r in ret5 if r > 0) / len(ret5),
            win_rate_10d=sum(1 for r in ret10 if r > 0) / len(ret10),
            avg_max_drawdown=np.mean(dd),
            best_return=max(ret10 + ret5),
            worst_return=min(ret10 + ret5),
        )

    def save(self, path: str) -> None:
        self.engine.save(path)

    def load(self, path: str) -> None:
        self.engine.load(path)

    def stats(self) -> dict:
        return self.engine.stats()
