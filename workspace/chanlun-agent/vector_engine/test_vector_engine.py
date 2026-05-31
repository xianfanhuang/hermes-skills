"""验证向量引擎可插拔组件是否正常工作"""

import numpy as np
from vector_engine import create_vector_engine, VectorRecord

# 1. 测试 Mock 引擎
print("=== Mock Engine ===")
engine = create_vector_engine("mock")

records = [
    VectorRecord(id=f"test_{i}", vector=np.random.randn(64).astype(np.float32), metadata={"return_5d": i * 0.01})
    for i in range(100)
]
engine.build_index(records)

query = np.random.randn(64).astype(np.float32)
results = engine.search(query, top_k=5)
print(f"检索到 {len(results)} 条结果")
for r in results[:3]:
    print(f"  {r.record.id} | score={r.score:.4f} | return_5d={r.record.metadata['return_5d']:.2%}")

# 2. 测试 FAISS 引擎
print("\n=== FAISS Engine ===")
engine = create_vector_engine("faiss", dimension=64, metric="cosine")
engine.build_index(records)
results = engine.search(query, top_k=5)
print(f"检索到 {len(results)} 条结果")
for r in results[:3]:
    print(f"  {r.record.id} | score={r.score:.4f}")

# 3. 测试持久化
engine.save("/tmp/test_vector_index")
engine2 = create_vector_engine("faiss", dimension=64)
engine2.load("/tmp/test_vector_index")
results2 = engine2.search(query, top_k=3)
print(f"\n持久化后检索到 {len(results2)} 条结果 ✅")

# 4. 测试增量添加
engine.add(VectorRecord(id="new_1", vector=np.random.randn(64).astype(np.float32), metadata={"return_5d": 0.05}))
print(f"增量添加后总数: {engine.stats()['total']}")

print("\n✅ 所有测试通过")
