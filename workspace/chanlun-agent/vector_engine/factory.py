"""工厂函数 — 一行切换后端"""

from .base import VectorEngine


def create_vector_engine(backend: str = "faiss", **kwargs) -> VectorEngine:
    """
    创建向量引擎实例

    Args:
        backend: "faiss" | "milvus" | "mock"
        **kwargs: 传给具体引擎的参数

    Returns:
        VectorEngine 实例

    示例：
        engine = create_vector_engine("faiss", dimension=64, metric="cosine")
        engine = create_vector_engine("mock")  # 测试用
    """
    backend = backend.lower()

    if backend == "faiss":
        from .faiss_engine import FAISSEngine
        return FAISSEngine(**kwargs)
    elif backend == "milvus":
        raise NotImplementedError("Milvus 后端待实现，当前可用: faiss, mock")
    elif backend == "mock":
        from .mock_engine import MockEngine
        return MockEngine(**kwargs)
    else:
        raise ValueError(f"未知后端: {backend}，可选: faiss, mock")
