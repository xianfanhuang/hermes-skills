"""
缠论特征提取器 — 将 czsc 分析结果转为固定长度向量

输入：czsc 的 RawBar / BI / FX 等对象
输出：numpy 向量，可直接存入向量引擎

这是"可插拔"的另一层：
- CZSCFeatureExtractor: 基于 czsc 库的特征提取
- 手工特征工程版本可自行替换
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class ChanlunFeatures:
    """缠论特征向量"""
    vector: np.ndarray          # 特征向量
    dim_names: list[str]        # 每维的名称（便于调试）

    def __len__(self):
        return len(self.vector)


# 特征维度定义
FEATURE_DIMS = [
    # 笔特征（8维）
    "bi_count",            # 笔数量
    "bi_avg_slope",        # 笔平均斜率
    "bi_slope_std",        # 笔斜率标准差
    "bi_avg_length",       # 笔平均长度（K线数）
    "bi_up_ratio",         # 上涨笔占比
    "bi_max_amplitude",    # 最大笔幅
    "bi_min_amplitude",    # 最小笔幅
    "bi_amplitude_std",    # 笔幅标准差

    # 中枢特征（6维）
    "zs_count",            # 中枢数量
    "zs_avg_height",       # 中枢平均高度
    "zs_avg_duration",     # 中枢平均持续时间
    "zs_overlap_ratio",    # 中枢重叠度
    "zs_max_level",        # 最大中枢级别
    "zs_transition_prob",  # 中枢转移概率

    # 背驰特征（4维）
    "bc_count",            # 背驰次数
    "bc_avg_strength",     # 平均背驰强度
    "bc_last_direction",   # 最后一次背驰方向（1=顶, -1=底, 0=无）
    "bc_reliability",      # 背驰可靠度

    # 成交量特征（4维）
    "vol_avg",             # 平均成交量
    "vol_trend",           # 成交量趋势（斜率）
    "vol_ratio_last5",     # 近5日量比
    "vol_price_corr",      # 量价相关性

    # 形态特征（4维）
    "pattern_momentum",    # 动量指标
    "pattern_volatility",  # 波动率
    "pattern_trend_str",   # 趋势强度
    "pattern_range_ratio", # 振幅比
]

DIMENSION = len(FEATURE_DIMS)  # 26维


def extract_features_from_czsc(bars: list, bi_list: list, fx_list: list, zs_list: list) -> ChanlunFeatures:
    """
    从 czsc 分析结果提取特征向量

    Args:
        bars: RawBar 列表
        bi_list: 笔列表
        fx_list: 分型列表
        zs_list: 中枢列表

    Returns:
        ChanlunFeatures 对象
    """
    import numpy as np

    vec = np.zeros(DIMENSION, dtype=np.float32)

    # --- 笔特征 ---
    if bi_list:
        slopes = [getattr(bi, 'slope', 0) or 0 for bi in bi_list]
        lengths = [getattr(bi, 'length', 0) or 0 for bi in bi_list]
        amplitudes = [abs(getattr(bi, 'power', 0) or 0) for bi in bi_list]
        up_count = sum(1 for bi in bi_list if getattr(bi, 'direction', 0) == 1)

        vec[0] = len(bi_list)
        vec[1] = np.mean(slopes) if slopes else 0
        vec[2] = np.std(slopes) if len(slopes) > 1 else 0
        vec[3] = np.mean(lengths) if lengths else 0
        vec[4] = up_count / len(bi_list) if bi_list else 0.5
        vec[5] = max(amplitudes) if amplitudes else 0
        vec[6] = min(amplitudes) if amplitudes else 0
        vec[7] = np.std(amplitudes) if len(amplitudes) > 1 else 0

    # --- 中枢特征 ---
    if zs_list:
        heights = [getattr(zs, 'high', 0) - getattr(zs, 'low', 0) for zs in zs_list]
        durations = [getattr(zs, 'length', 0) or 0 for zs in zs_list]

        vec[8] = len(zs_list)
        vec[9] = np.mean(heights) if heights else 0
        vec[10] = np.mean(durations) if durations else 0
        vec[11] = 0  # 重叠度需额外计算
        vec[12] = max(getattr(zs, 'level', 1) for zs in zs_list) if zs_list else 0
        vec[13] = 0  # 转移概率需额外计算

    # --- 背驰特征 ---
    bc_list = [fx for fx in fx_list if getattr(fx, 'fx_mark', '') in ('d', 'g')]
    if bc_list:
        vec[14] = len(bc_list)
        vec[15] = 0  # 强度需额外计算
        last_fx = bc_list[-1]
        vec[16] = 1 if getattr(last_fx, 'fx_mark', '') == 'g' else -1
        vec[17] = 0.5  # 可靠度默认值

    # --- 成交量特征 ---
    if bars:
        vols = [bar.vol for bar in bars if hasattr(bar, 'vol') and bar.vol]
        if vols:
            vec[18] = np.mean(vols)
            if len(vols) > 1:
                x = np.arange(len(vols))
                vec[19] = np.polyfit(x, vols, 1)[0] if len(vols) > 2 else 0
            vec[20] = np.mean(vols[-5:]) / np.mean(vols) if len(vols) >= 5 and np.mean(vols) > 0 else 1.0
            # 量价相关性
            prices = [bar.close for bar in bars if hasattr(bar, 'close')]
            if len(prices) == len(vols) and len(prices) > 2:
                vec[21] = np.corrcoef(prices, vols)[0, 1] if not np.isnan(np.corrcoef(prices, vols)[0, 1]) else 0

    # --- 形态特征 ---
    if bars:
        closes = [bar.close for bar in bars if hasattr(bar, 'close')]
        if len(closes) > 1:
            returns = np.diff(closes) / closes[:-1]
            vec[22] = np.mean(returns)  # 动量
            vec[23] = np.std(returns)   # 波动率
            # 趋势强度：线性回归斜率
            x = np.arange(len(closes))
            slope = np.polyfit(x, closes, 1)[0] if len(closes) > 2 else 0
            vec[24] = slope / np.mean(closes) if np.mean(closes) > 0 else 0
            vec[25] = (max(closes) - min(closes)) / np.mean(closes) if np.mean(closes) > 0 else 0

    return ChanlunFeatures(vector=vec, dim_names=FEATURE_DIMS)


def normalize_features(features_list: list[ChanlunFeatures]) -> list[np.ndarray]:
    """
    Z-Score 标准化特征向量

    Args:
        features_list: ChanlunFeatures 列表

    Returns:
        标准化后的向量列表
    """
    if not features_list:
        return []

    vectors = np.array([f.vector for f in features_list], dtype=np.float32)
    mean = np.mean(vectors, axis=0)
    std = np.std(vectors, axis=0)
    std[std < 1e-10] = 1.0  # 避免除零

    normalized = (vectors - mean) / std
    return [v for v in normalized]
