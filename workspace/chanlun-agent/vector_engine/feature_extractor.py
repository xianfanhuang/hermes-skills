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


def _find_zhongshu(bi_list) -> list[dict]:
    """从笔列表推导中枢（至少3笔重叠区间）"""
    if len(bi_list) < 3:
        return []

    zss = []
    i = 0
    while i < len(bi_list) - 2:
        b1, b2, b3 = bi_list[i], bi_list[i+1], bi_list[i+2]

        # 计算3笔重叠区间
        overlap_high = min(b1.high, b2.high, b3.high)
        overlap_low = max(b1.low, b2.low, b3.low)

        if overlap_high > overlap_low:
            # 有重叠，形成中枢
            height = overlap_high - overlap_low
            zs = {
                'high': overlap_high,
                'low': overlap_low,
                'height': height,
                'center': (overlap_high + overlap_low) / 2,
                'bi_count': 3,
                'start_bi': i,
                'level': 1,
                'overlap_ratio': 1.0,
            }

            # 尝试扩展
            j = i + 3
            while j < len(bi_list):
                bj = bi_list[j]
                if bj.low < overlap_high and bj.high > overlap_low:
                    zs['bi_count'] += 1
                    j += 1
                else:
                    break

            # 计算重叠度（所有笔在中枢区间的占比）
            total_range = max(b.high for b in bi_list[i:j]) - min(b.low for b in bi_list[i:j])
            zs['overlap_ratio'] = height / total_range if total_range > 0 else 0

            # 中枢级别（笔数越多级别越高）
            zs['level'] = 1 + (zs['bi_count'] - 3) // 2

            zss.append(zs)
            i = j
        else:
            i += 1

    return zss


def _detect_beichi(bi_list, zss) -> list[dict]:
    """检测背驰：中枢前后同向笔力度衰减"""
    bc_list = []

    for zs in zss:
        end = zs['start_bi'] + zs['bi_count']
        if end >= len(bi_list):
            continue

        # 中枢第一笔和最后一笔
        entry_bi = bi_list[zs['start_bi']]
        exit_bi = bi_list[end - 1]

        # 离开中枢的笔
        leave_bi = bi_list[end] if end < len(bi_list) else None

        if leave_bi is None:
            continue

        # 比较同向笔力度：entry_bi vs leave_bi
        if hasattr(entry_bi, 'power') and hasattr(leave_bi, 'power'):
            entry_power = entry_bi.power
            leave_power = leave_bi.power

            if entry_power > 0 and leave_power < entry_power * 0.8:
                strength = 1 - leave_power / entry_power
                # 可靠度：基于R²和信噪比
                reliability = 0.5
                if hasattr(leave_bi, 'rsq'):
                    reliability = min(leave_bi.rsq, 1.0)
                if hasattr(leave_bi, 'power_snr'):
                    reliability = (reliability + min(leave_bi.power_snr, 1.0)) / 2

                bc_list.append({
                    'direction': str(leave_bi.direction),
                    'strength': strength,
                    'reliability': reliability,
                    'price': leave_bi.high if 'Up' in str(leave_bi.direction) else leave_bi.low,
                })

    return bc_list


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

    # --- 中枢特征（从笔推导）---
    zss = _find_zhongshu(bi_list)
    if zss:
        heights = [zs['height'] for zs in zss]
        durations = [zs['bi_count'] for zs in zss]
        overlaps = [zs['overlap_ratio'] for zs in zss]

        vec[8] = len(zss)
        vec[9] = np.mean(heights)
        vec[10] = np.mean(durations)
        vec[11] = np.mean(overlaps)
        vec[12] = max(zs['level'] for zs in zss)
        vec[13] = len(zss) / max(len(bi_list), 1)  # 中枢密度

    # --- 背驰特征（从笔力度对比推导）---
    bc_list = _detect_beichi(bi_list, zss)
    if bc_list:
        strengths = [bc['strength'] for bc in bc_list]
        vec[14] = len(bc_list)
        vec[15] = np.mean(strengths)
        vec[16] = 1 if bc_list[-1]['direction'] == 'Up' else -1
        vec[17] = np.mean([bc['reliability'] for bc in bc_list])

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
