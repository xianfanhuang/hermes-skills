"""
向量引擎实战演示 — 缠论 + FAISS 相似走势检索

场景：输入当前股票的缠论分析结果，检索历史上最相似的走势，统计后续涨跌概率
"""

import numpy as np
from vector_engine import create_vector_engine, VectorRecord

# ============================================================
# 模拟数据（实际场景替换为 czsc 真实分析结果）
# ============================================================

def simulate_bars(n=50, trend="up"):
    """模拟K线数据"""
    bars = []
    base = 10.0
    for i in range(n):
        if trend == "up":
            change = np.random.normal(0.005, 0.02)
        elif trend == "down":
            change = np.random.normal(-0.005, 0.02)
        else:
            change = np.random.normal(0, 0.015)
        base *= (1 + change)
        bars.append({
            "close": base,
            "vol": np.random.uniform(1e6, 5e6),
        })
    return bars

def bars_to_vector(bars):
    """简易特征提取（演示用，实际用 feature_extractor）"""
    closes = [b["close"] for b in bars]
    vols = [b["vol"] for b in bars]
    returns = np.diff(closes) / closes[:-1]

    vec = np.zeros(26, dtype=np.float32)
    vec[0] = len(bars)  # bi_count placeholder
    vec[1] = np.mean(returns)  # 平均收益
    vec[2] = np.std(returns)   # 波动率
    vec[3] = len(bars)  # 长度
    vec[4] = sum(1 for r in returns if r > 0) / len(returns)  # 上涨比例
    vec[5] = max(returns)  # 最大涨幅
    vec[6] = min(returns)  # 最大跌幅
    vec[7] = np.std(returns)  # 收益标准差
    vec[18] = np.mean(vols)  # 平均成交量
    vec[22] = np.mean(returns)  # 动量
    vec[23] = np.std(returns)  # 波动率
    # 趋势强度
    x = np.arange(len(closes))
    vec[24] = np.polyfit(x, closes, 1)[0] / np.mean(closes)
    vec[25] = (max(closes) - min(closes)) / np.mean(closes)
    return vec

# ============================================================
# 构建历史数据库
# ============================================================
print("📊 构建历史走势向量数据库...")

np.random.seed(42)
history_records = []

# 模拟100段历史走势
for i in range(100):
    trend = np.random.choice(["up", "down", "range"])
    bars = simulate_bars(50, trend)
    vec = bars_to_vector(bars)

    # 模拟后续收益（上升趋势后续偏正，下降趋势偏负）
    if trend == "up":
        ret5 = np.random.normal(0.03, 0.02)
        ret10 = np.random.normal(0.05, 0.03)
    elif trend == "down":
        ret5 = np.random.normal(-0.03, 0.02)
        ret10 = np.random.normal(-0.05, 0.03)
    else:
        ret5 = np.random.normal(0, 0.02)
        ret10 = np.random.normal(0, 0.03)

    history_records.append(VectorRecord(
        id=f"HIST_{i:03d}_{trend}",
        vector=vec,
        metadata={
            "trend": trend,
            "return_5d": float(ret5),
            "return_10d": float(ret10),
            "max_drawdown": float(np.random.uniform(0, 0.05)),
        }
    ))

# ============================================================
# 构建索引
# ============================================================
engine = create_vector_engine("faiss", dimension=26, metric="cosine")
engine.build_index(history_records)
print(f"✅ 索引构建完成: {engine.stats()}")

# ============================================================
# 场景1：检索相似走势
# ============================================================
print("\n🔍 场景1：检索与当前走势最相似的历史走势")
print("=" * 50)

# 当前走势：一段上升趋势
current_bars = simulate_bars(50, "up")
current_vec = bars_to_vector(current_bars)

results = engine.search(current_vec, top_k=10)
print(f"\n当前走势特征：上升趋势，动量={current_vec[22]:.4f}，波动率={current_vec[23]:.4f}")
print(f"\n最相似的 10 段历史走势：")
print(f"{'排名':<4} {'走势ID':<20} {'相似度':<10} {'趋势':<8} {'5日收益':<10} {'10日收益':<10}")
print("-" * 62)

for i, r in enumerate(results):
    m = r.record.metadata
    print(f"{i+1:<4} {r.record.id:<20} {r.score:.4f}    {m['trend']:<8} {m['return_5d']:>+.2%}    {m['return_10d']:>+.2%}")

# ============================================================
# 场景2：收益统计分析
# ============================================================
print("\n📈 场景2：相似走势后续收益统计")
print("=" * 50)

from vector_engine.api import VectorSearchAPI

api = VectorSearchAPI(backend="faiss", dimension=26)
api.engine = engine  # 复用已有索引

stats = api.analyze_returns(results)
print(f"""
样本量：{stats.count} 段相似走势

📊 5日收益：
  平均收益：{stats.avg_return_5d:>+.2%}
  胜率：{stats.win_rate_5d:.0%}

📊 10日收益：
  平均收益：{stats.avg_return_10d:>+.2%}
  胜率：{stats.win_rate_10d:.0%}

⚠️ 风险：
  平均最大回撤：{stats.avg_max_drawdown:.2%}
  最佳收益：{stats.best_return:>+.2%}
  最差收益：{stats.worst_return:>+.2%}
""")

# ============================================================
# 场景3：持久化 & 加载
# ============================================================
print("💾 场景3：索引持久化")
engine.save("/tmp/demo_vector_index")
print("✅ 索引已保存到 /tmp/demo_vector_index")

engine2 = create_vector_engine("faiss", dimension=26)
engine2.load("/tmp/demo_vector_index")
results2 = engine2.search(current_vec, top_k=3)
print(f"✅ 加载后检索到 {len(results2)} 条结果")

print("\n🎉 演示完成！向量引擎可插拔组件工作正常。")
