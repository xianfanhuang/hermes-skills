#!/usr/bin/env python3
"""
CzscExtension v1.0 - czsc v0.10.12 扩展层

基于 czsc 核心输出（bi_list/fx_list），实现应用层信号识别：
- 中枢（zhongshu）计算
- 类二买识别
- 中枢震荡买卖点
- 分型成交量过滤
- 特殊形态识别（奔走型中枢、三角形收敛）
- 多级别共振

核心原则：不修改 czsc 源码，基于其输出结果进行二次分析。

Author: Trading Assistant
Version: 1.0.0
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("CzscExtension")


@dataclass
class ZhongShu:
    """中枢"""
    high: float          # 中枢上沿 (ZG)
    low: float           # 中枢下沿 (ZD)
    sdt: str             # 开始时间
    edt: str             # 结束时间
    bi_count: int = 0    # 包含笔数量
    direction: str = ""  # 方向 (up/down/neutral)
    level: str = "L1"    # 级别

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def range_pct(self) -> float:
        return self.range / self.mid * 100 if self.mid else 0

    def to_dict(self) -> Dict:
        return {
            'high': self.high,
            'low': self.low,
            'sdt': str(self.sdt),
            'edt': str(self.edt),
            'bi_count': self.bi_count,
            'direction': str(self.direction),
            'level': self.level,
            'mid': self.mid,
            'range': self.range,
        }


@dataclass
class Signal:
    """交易信号"""
    type: str             # 信号类型
    direction: str        # LONG/SHORT
    strength: float       # 强度 0-1
    price: float          # 触发价格
    stop_loss: float = 0  # 止损价
    target: float = 0     # 目标价
    reason: str = ""      # 原因
    confidence: float = 0 # 信心度 0-1
    level: str = "L2"     # 级别 (L1=观察, L2=操作, L3=强信号)
    filtered: bool = False
    filtered_reason: str = ""

    def to_dict(self) -> Dict:
        return {
            'type': self.type,
            'direction': self.direction,
            'strength': self.strength,
            'price': self.price,
            'stop_loss': self.stop_loss,
            'target': self.target,
            'reason': self.reason,
            'confidence': self.confidence,
            'level': self.level,
            'filtered': self.filtered,
            'filtered_reason': self.filtered_reason,
        }


class CzscExtension:
    """
    czsc v0.10.12 扩展层

    基于 czsc 核心输出，实现应用层信号识别。

    使用方式:
        ka = CZSC(bars)  # czsc 核心分析
        ext = CzscExtension(ka)
        signals = ext.analyze_all()
    """

    def __init__(self, ka, symbol: str = "", timeframe: str = "daily"):
        """
        Args:
            ka: czsc.CZSC 对象
            symbol: 品种代码
            timeframe: 时间周期 (daily/30min/5min)
        """
        self.ka = ka
        self.symbol = symbol
        self.timeframe = timeframe

        # 从 czsc 提取核心数据
        self.bi_list = ka.bi_list or []
        self.fx_list = ka.fx_list or []
        self.bars = ka.bars_raw or []

        # 最新价格
        self.last_price = self.bars[-1].close if self.bars else 0

        # 计算中枢
        self.zs_list = self._calc_zhongshu()

    # ==================== 中枢计算 ====================

    def _calc_zhongshu(self) -> List[ZhongShu]:
        """
        计算中枢

        规则：至少3笔有重叠区域构成中枢
        - 取连续3笔的重叠区间
        - ZG = min(笔1高, 笔2高, 笔3高) 中的较低者
        - ZD = max(笔1低, 笔2低, 笔3低) 中的较高者
        - 如果 ZG > ZD，则构成中枢
        """
        if len(self.bi_list) < 3:
            return []

        zhongshus = []
        i = 0

        while i < len(self.bi_list) - 2:
            bi1 = self.bi_list[i]
            bi2 = self.bi_list[i + 1]
            bi3 = self.bi_list[i + 2]

            # 计算重叠区间
            highs = [bi1.high, bi2.high, bi3.high]
            lows = [bi1.low, bi2.low, bi3.low]

            zg = min(highs)  # 中枢上沿
            zd = max(lows)   # 中枢下沿

            if zg > zd:
                # 构成中枢，尝试延伸
                bi_count = 3
                end_idx = i + 2

                # 检查后续笔是否也在中枢内
                for j in range(i + 3, len(self.bi_list)):
                    bi = self.bi_list[j]
                    # 笔的高低点与中枢有重叠
                    if bi.low < zg and bi.high > zd:
                        bi_count += 1
                        end_idx = j
                    else:
                        break

                # 计算方向
                first_bi = self.bi_list[i]
                last_bi = self.bi_list[end_idx]
                if last_bi.high > first_bi.high:
                    direction = "up"
                elif last_bi.low < first_bi.low:
                    direction = "down"
                else:
                    direction = "neutral"

                zs = ZhongShu(
                    high=zg,
                    low=zd,
                    sdt=str(bi1.sdt),
                    edt=str(self.bi_list[end_idx].edt),
                    bi_count=bi_count,
                    direction=direction,
                )
                zhongshus.append(zs)

                i = end_idx + 1
            else:
                i += 1

        return zhongshus

    # ==================== 类二买识别 ====================

    def detect_like_second_buy(self) -> Optional[Signal]:
        """
        类二买识别

        定义：中枢震荡中的第二次买点（不破前低）

        条件：
        1. 存在中枢
        2. 当前价格在中枢下沿附近（±2%）
        3. 最近的向下笔不创新低
        4. 出现底分型确认
        """
        if not self.zs_list or len(self.bi_list) < 4:
            return None

        last_zs = self.zs_list[-1]
        zs_low = last_zs.low
        zs_high = last_zs.high

        # 检查是否在中枢下沿附近
        distance_pct = abs(self.last_price - zs_low) / zs_low if zs_low else 1
        if distance_pct > 0.02:
            return None

        # 获取最近的向下笔
        down_bis = [bi for bi in self.bi_list[-6:] if bi.direction == '向下']
        if len(down_bis) < 2:
            return None

        # 检查是否不创新低
        if down_bis[-1].low >= down_bis[-2].low * 0.998:
            # 检查是否有底分型
            if self._has_bottom_fx():
                return Signal(
                    type="like_second_buy",
                    direction="LONG",
                    strength=0.65,
                    price=self.last_price,
                    stop_loss=zs_low * 0.97,
                    target=zs_high,
                    reason=f"类二买：中枢下沿{zs_low:.2f}附近+不创新低+底分型确认",
                    confidence=0.65,
                    level="L2",
                )

        return None

    # ==================== 中枢震荡买卖点 ====================

    def detect_shock_points(self) -> List[Signal]:
        """
        中枢震荡买卖点

        上沿附近 → 卖出信号
        下沿附近 → 买入信号
        """
        signals = []

        if not self.zs_list:
            return signals

        last_zs = self.zs_list[-1]
        zs_low = last_zs.low
        zs_high = last_zs.high
        zs_mid = last_zs.mid

        # 靠近上沿 → 卖
        if abs(self.last_price - zs_high) / zs_high < 0.015:
            # 确认有顶分型
            if self._has_top_fx():
                signals.append(Signal(
                    type="shock_sell",
                    direction="SHORT",
                    strength=0.6,
                    price=self.last_price,
                    stop_loss=zs_high * 1.01,
                    target=zs_mid,
                    reason=f"中枢上沿{zs_high:.2f}附近+顶分型确认，震荡做空",
                    confidence=0.6,
                    level="L2",
                ))

        # 靠近下沿 → 买
        if abs(self.last_price - zs_low) / zs_low < 0.015:
            # 确认有底分型
            if self._has_bottom_fx():
                signals.append(Signal(
                    type="shock_buy",
                    direction="LONG",
                    strength=0.6,
                    price=self.last_price,
                    stop_loss=zs_low * 0.99,
                    target=zs_high,
                    reason=f"中枢下沿{zs_low:.2f}附近+底分型确认，震荡做多",
                    confidence=0.6,
                    level="L2",
                ))

        return signals

    # ==================== 标准背驰检测 ====================

    def detect_divergence(self) -> Optional[Signal]:
        """
        标准背驰检测

        基于 MACD 面积比较：
        - 底背驰：价格创新低，MACD 面积不创新低
        - 顶背驰：价格创新高，MACD 面积不创新高
        """
        if len(self.bi_list) < 6:
            return None

        recent_bis = self.bi_list[-6:]

        # 底背驰检测
        down_bis = [bi for bi in recent_bis if bi.direction == '向下']
        if len(down_bis) >= 2:
            last_down = down_bis[-1]
            prev_down = down_bis[-2]

            # 价格创新低
            if last_down.low <= prev_down.low:
                # 比较力度（power 字段）
                last_power = getattr(last_down, 'power', 0) or 0
                prev_power = getattr(prev_down, 'power', 0) or 0

                if last_power < prev_power * 0.8:  # 力度衰减
                    return Signal(
                        type="bottom_divergence",
                        direction="LONG",
                        strength=0.7,
                        price=self.last_price,
                        stop_loss=last_down.low * 0.97,
                        target=last_down.high,
                        reason=f"底背驰：价格新低{last_down.low:.2f}，力度衰减{last_power:.1f}<{prev_power:.1f}",
                        confidence=0.7,
                        level="L2",
                    )

        # 顶背驰检测
        up_bis = [bi for bi in recent_bis if bi.direction == '向上']
        if len(up_bis) >= 2:
            last_up = up_bis[-1]
            prev_up = up_bis[-2]

            # 价格创新高
            if last_up.high >= prev_up.high:
                last_power = getattr(last_up, 'power', 0) or 0
                prev_power = getattr(prev_up, 'power', 0) or 0

                if last_power < prev_power * 0.8:
                    return Signal(
                        type="top_divergence",
                        direction="SHORT",
                        strength=0.7,
                        price=self.last_price,
                        stop_loss=last_up.high * 1.03,
                        target=last_up.low,
                        reason=f"顶背驰：价格新高{last_up.high:.2f}，力度衰减{last_power:.1f}<{prev_power:.1f}",
                        confidence=0.7,
                        level="L2",
                    )

        return None

    # ==================== 分型成交量过滤 ====================

    def filter_by_volume(self, signal: Signal, min_ratio: float = 1.0) -> Signal:
        """
        分型成交量过滤

        放量分型优先，低量分型降级

        Args:
            signal: 原始信号
            min_ratio: 最低成交量比率（相对于20周期均量）
        """
        if not self.bars:
            return signal

        # 计算20周期均量
        recent_volumes = [bar.vol for bar in self.bars[-20:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 1

        # 当前K线成交量
        current_volume = self.bars[-1].vol if self.bars else 0

        if avg_volume > 0:
            ratio = current_volume / avg_volume
            if ratio < min_ratio:
                signal.level = "L1"  # 降级为观察级
                signal.filtered = True
                signal.filtered_reason = f"低成交量({ratio:.1f}x均量)，信号降级"
                signal.strength *= 0.7
                signal.confidence *= 0.7

        return signal

    # ==================== 特殊形态识别 ====================

    def detect_special_forms(self) -> List[Dict]:
        """
        特殊形态识别

        - 奔走型中枢：中枢区间逐步上移/下移
        - 三角形收敛：中枢区间逐步缩小
        """
        forms = []

        if len(self.zs_list) < 2:
            return forms

        recent_zs = self.zs_list[-3:] if len(self.zs_list) >= 3 else self.zs_list[-2:]

        # 奔走型中枢（上移）
        if len(recent_zs) >= 2:
            if all(recent_zs[i].low < recent_zs[i+1].low for i in range(len(recent_zs)-1)):
                forms.append({
                    "type": "running_zs_up",
                    "description": "奔走型中枢（上移）",
                    "implication": "多头强势，回调做多",
                    "direction": "LONG",
                })

            # 奔走型中枢（下移）
            if all(recent_zs[i].low > recent_zs[i+1].low for i in range(len(recent_zs)-1)):
                forms.append({
                    "type": "running_zs_down",
                    "description": "奔走型中枢（下移）",
                    "implication": "空头强势，反弹做空",
                    "direction": "SHORT",
                })

            # 三角形收敛
            if all(recent_zs[i].range > recent_zs[i+1].range for i in range(len(recent_zs)-1)):
                forms.append({
                    "type": "triangle_converge",
                    "description": "三角形收敛",
                    "implication": "变盘在即，等待突破方向",
                    "direction": "NEUTRAL",
                })

        return forms

    # ==================== 多级别共振 ====================

    def check_resonance(self, higher_ext: 'CzscExtension') -> Optional[Signal]:
        """
        多级别共振检查

        大级别定方向，小级别定入场

        Args:
            higher_ext: 更大级别的 CzscExtension 对象
        """
        if not higher_ext.bi_list or not self.bi_list:
            return None

        higher_bi = higher_ext.bi_list[-1]
        current_bi = self.bi_list[-1]

        # 大级别向上 + 当前级别回调 = 做多共振
        if higher_bi.direction == '向上' and current_bi.direction == '向下':
            return Signal(
                type="resonance_long",
                direction="LONG",
                strength=0.8,
                price=self.last_price,
                reason=f"多级别共振：大级别向上+当前级别回调",
                confidence=0.8,
                level="L3",
            )

        # 大级别向下 + 当前级别反弹 = 做空共振
        if higher_bi.direction == '向下' and current_bi.direction == '向上':
            return Signal(
                type="resonance_short",
                direction="SHORT",
                strength=0.8,
                price=self.last_price,
                reason=f"多级别共振：大级别向下+当前级别反弹",
                confidence=0.8,
                level="L3",
            )

        return None

    # ==================== 综合分析 ====================

    def analyze_all(self, min_volume_ratio: float = 0.8,
                    higher_ext: 'CzscExtension' = None) -> Dict:
        """
        综合分析，生成所有信号

        Args:
            min_volume_ratio: 最低成交量比率
            higher_ext: 更大级别的 CzscExtension 对象（用于多级别共振）

        Returns:
            分析结果字典
        """
        signals = []

        # 1. 标准背驰
        divergence = self.detect_divergence()
        if divergence:
            signals.append(divergence)

        # 2. 类二买
        like_second = self.detect_like_second_buy()
        if like_second:
            signals.append(like_second)

        # 3. 中枢震荡买卖点
        shock_points = self.detect_shock_points()
        signals.extend(shock_points)

        # 4. 多级别共振
        if higher_ext:
            resonance = self.check_resonance(higher_ext)
            if resonance:
                signals.append(resonance)

        # 5. 成交量过滤
        for sig in signals:
            self.filter_by_volume(sig, min_ratio=min_volume_ratio)

        # 6. 特殊形态
        special_forms = self.detect_special_forms()

        # 7. 选择最佳信号（未过滤的、强度最高的）
        valid_signals = [s for s in signals if not s.filtered]
        best_signal = max(valid_signals, key=lambda s: s.strength) if valid_signals else None

        # 8. 生成摘要
        summary = self._generate_summary(signals, best_signal, special_forms)

        return {
            'signals': [s.to_dict() for s in signals],
            'best_signal': best_signal.to_dict() if best_signal else None,
            'zhongshus': [z.to_dict() for z in self.zs_list],
            'bi_list': [{'direction': str(bi.direction), 'high': bi.high, 'low': bi.low,
                         'sdt': str(bi.sdt), 'edt': str(bi.edt)} for bi in self.bi_list],
            'special_forms': special_forms,
            'summary': summary,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'last_price': self.last_price,
        }

    # ==================== 辅助方法 ====================

    def _has_bottom_fx(self) -> bool:
        """检查最近是否有底分型"""
        if not self.fx_list:
            return False
        last_fx = self.fx_list[-1]
        return last_fx.mark == 'd'  # d = 底分型

    def _has_top_fx(self) -> bool:
        """检查最近是否有顶分型"""
        if not self.fx_list:
            return False
        last_fx = self.fx_list[-1]
        return last_fx.mark == 'g'  # g = 顶分型

    def _generate_summary(self, signals: List[Signal], best_signal: Optional[Signal],
                          special_forms: List[Dict]) -> str:
        """生成分析摘要"""
        parts = []

        # 基本信息
        parts.append(f"品种: {self.symbol}")
        parts.append(f"周期: {self.timeframe}")
        parts.append(f"当前价: {self.last_price:.2f}")
        parts.append(f"笔数: {len(self.bi_list)}")
        parts.append(f"中枢数: {len(self.zs_list)}")

        # 中枢信息
        if self.zs_list:
            last_zs = self.zs_list[-1]
            parts.append(f"最新中枢: [{last_zs.low:.2f}, {last_zs.high:.2f}]")

        # 信号信息
        if best_signal:
            parts.append(f"最佳信号: {best_signal.type} ({best_signal.direction})")
            parts.append(f"  强度: {best_signal.strength:.2f}")
            parts.append(f"  信心: {best_signal.confidence:.2f}")
            parts.append(f"  原因: {best_signal.reason}")
        else:
            parts.append("无有效信号")

        # 特殊形态
        if special_forms:
            for form in special_forms:
                parts.append(f"形态: {form['description']} → {form['implication']}")

        return "\n".join(parts)


# ==================== 便捷函数 ====================

def analyze_symbol(ka, symbol: str = "", timeframe: str = "daily",
                   min_volume_ratio: float = 0.8, higher_ext=None) -> Dict:
    """
    快捷分析函数

    Args:
        ka: czsc.CZSC 对象
        symbol: 品种代码
        timeframe: 时间周期
        min_volume_ratio: 最低成交量比率
        higher_ext: 更大级别的 CzscExtension 对象

    Returns:
        分析结果字典
    """
    ext = CzscExtension(ka, symbol=symbol, timeframe=timeframe)
    return ext.analyze_all(min_volume_ratio=min_volume_ratio, higher_ext=higher_ext)


def analyze_multi_level(bars_dict: Dict[str, list], symbol: str = "",
                        min_volume_ratio: float = 0.8) -> Dict:
    """
    多级别联立分析

    大级别定方向，小级别定入场

    Args:
        bars_dict: {'daily': bars, '30min': bars, '5min': bars}
        symbol: 品种代码
        min_volume_ratio: 最低成交量比率

    Returns:
        多级别分析结果
    """
    from czsc import CZSC

    results = {}
    extensions = {}

    # 按周期从大到小排序
    timeframe_order = ['daily', '30min', '5min']
    sorted_keys = [k for k in timeframe_order if k in bars_dict]

    # 先计算所有级别的基础分析
    for tf in sorted_keys:
        bars = bars_dict[tf]
        if not bars or len(bars) < 10:
            continue
        ka = CZSC(bars)
        ext = CzscExtension(ka, symbol=symbol, timeframe=tf)
        extensions[tf] = ext

    # 多级别共振分析：大级别作为 higher_ext 传给小级别
    for i, tf in enumerate(sorted_keys):
        if tf not in extensions:
            continue

        # 找更大级别
        higher_ext = None
        for j in range(i - 1, -1, -1):
            if sorted_keys[j] in extensions:
                higher_ext = extensions[sorted_keys[j]]
                break

        results[tf] = extensions[tf].analyze_all(
            min_volume_ratio=min_volume_ratio,
            higher_ext=higher_ext,
        )

    # 生成综合摘要
    summary_parts = [f"品种: {symbol}", "多级别联立分析:"]
    all_signals = []

    for tf in sorted_keys:
        if tf in results:
            r = results[tf]
            summary_parts.append(f"\n【{tf}】")
            summary_parts.append(f"  笔数: {len(r.get('bi_list', []))} | 中枢: {len(r.get('zhongshus', []))}")
            for sig in r.get('signals', []):
                summary_parts.append(f"  {sig['type']} ({sig['direction']}) 强度={sig['strength']:.2f}")
                all_signals.append(sig)

    # 汇总最佳信号
    valid_signals = [s for s in all_signals if not s.get('filtered', False)]
    best = max(valid_signals, key=lambda s: s['strength']) if valid_signals else None

    if best:
        summary_parts.append(f"\n最佳信号: {best['type']} ({best['direction']}) 强度={best['strength']:.2f}")
    else:
        summary_parts.append("\n无有效信号")

    return {
        'results': results,
        'best_signal': best,
        'summary': '\n'.join(summary_parts),
        'symbol': symbol,
    }


# ==================== CLI 测试 ====================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/workspace/projects/workspace/chanlun-agent/data')

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    from czsc import CZSC, RawBar, Freq
    import pandas as pd
    import numpy as np

    # 生成模拟数据
    np.random.seed(42)
    n = 200
    dates = pd.date_range('2026-01-01', periods=n, freq='D')
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    high = close + np.abs(np.random.randn(n))
    low = close - np.abs(np.random.randn(n))
    open_ = close + np.random.randn(n) * 0.5
    vol = np.random.randint(1000, 10000, n)

    bars = [RawBar(symbol='TEST', dt=dates[i], freq=Freq.D,
        open=float(open_[i]), high=float(high[i]),
        low=float(low[i]), close=float(close[i]),
        vol=float(vol[i]), amount=float(vol[i]*close[i])) for i in range(n)]

    ka = CZSC(bars)

    print("\n📊 CzscExtension 测试")
    print("=" * 60)

    ext = CzscExtension(ka, symbol="TEST", timeframe="daily")
    result = ext.analyze_all()

    print(f"\n{result['summary']}")

    if result['signals']:
        print(f"\n信号列表:")
        for sig in result['signals']:
            status = "🔴 过滤" if sig['filtered'] else "🟢 有效"
            print(f"  {status} {sig['type']} ({sig['direction']}) 强度={sig['strength']:.2f} 信心={sig['confidence']:.2f}")
            print(f"     {sig['reason']}")

    if result['special_forms']:
        print(f"\n特殊形态:")
        for form in result['special_forms']:
            print(f"  {form['description']} → {form['implication']}")
