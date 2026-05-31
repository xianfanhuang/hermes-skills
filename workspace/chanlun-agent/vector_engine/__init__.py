"""
向量引擎 — 可插拔热组件

架构：统一接口 + 多后端实现
- FAISSEngine: 本地 FAISS（默认，零部署）
- MilvusEngine: 分布式 Milvus（生产级，需部署）
- MockEngine: 测试用，不依赖任何外部库

用法：
    engine = create_vector_engine("faiss")  # 或 "milvus", "mock"
    engine.build_index(vectors, metadata)
    results = engine.search(query_vector, top_k=10)

替换后端只需改 create_vector_engine() 的参数，业务代码不变。
"""

from .base import VectorEngine, VectorRecord, SearchResult
from .factory import create_vector_engine

__all__ = ["VectorEngine", "VectorRecord", "SearchResult", "create_vector_engine"]
