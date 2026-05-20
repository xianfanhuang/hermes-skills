#!/usr/bin/env python3
"""
czsc v0.10.12 API 扩展 - 类二买 & 中枢震荡买卖点

czsc 原生 API 只有：bi_list, fx_list, finished_bis, signals
中枢需要自算，买卖点需要自建

Author: Trading Assistant
Version: 1.0.0
"""

import czsc
from czsc import CZSC, Freq, format_standard_kline
from typing import List, Dict, Optional
from dataclasses import dataclass
import pandas as pd
import logging

logger = logging.getLogger("CzscExtension")


@dataclass
class BuySellPoint:
    """买卖点"""
    index: int
    type: str  # 类型：buy1/buy2/buy3/sell1/sell2/sell3/shock_buy/shock_sell
    price: float
    direction: str  # up/down
    bi_index: int  # 对应的笔序号
    zs_range: Optional[tuple] = None  # 中枢区间
    confidence: float = 0.0  # 置信度 0-1


@dataclass
class ZS:
    """中枢"""
    index: int
    zg: float  # 中枢上沿
    zd: float  # 中枢下沿
    gg: float  # 最高点
    dd: float  # 最低点
    bi_indices: List[int]  # 包含的笔序号


class CzscExtension:
    """czsc v0.10.12 扩展 - 类二买 & 中枢震荡"""

    def __init__(self, ka: CZSC):
        self.ka = ka
        self.bi_list = ka.bi_list
        self.fx_list = ka.fx_list
        self._zs_list: Optional[List[ZS]] = None
        self._buy_sell_points: Optional[List[BuySellPoint]] = None

    # ============ 中枢计算 ============

    def calc_zs_list(self) -> List[ZS]:
        """计算中枢列表"""
        if self._zs_list is not None:
            return self._zs_list

        zs_list = []
        bi_list = self.bi_list

        if len(bi_list) < 3:
            self._zs_list = zs_list
            return zs_list

        i = 0
        zs_index = 0
        while i < len(bi_list) - 2:
            bi1 = bi_list[i]
            bi2 = bi_list[i + 1]
            bi3 = bi_list[i + 2]

            # 计算重叠区间
            overlap_high = min(bi1.high, bi2.high, bi3.high)
            overlap_low = max(bi1.low, bi2.low, bi3.low)

            if overlap_high > overlap_low:
                # 有重叠，形成中枢
                gg = max(bi1.high, bi2.high, bi3.high)
                dd = min(bi1.low, bi2.low, bi3.low)

                zs = ZS(
                    index=zs_index,
                    zg=overlap_high,
                    zd=overlap_low,
                    gg=gg,
                    dd=dd,
                    bi_indices=[i, i+1, i+2]
                )
                zs_list.append(zs)
                zs_index += 1

                # 尝试扩展中枢
                j = i + 3
                while j < len(bi_list):
                    bi_j = bi_list[j]
                    # 如果后续笔与中枢有重叠，扩展中枢
                    if bi_j.low < overlap_high and bi_j.high > overlap_low:
                        zs.bi_indices.append(j)
                        gg = max(gg, bi_j.high)
                        dd = min(dd, bi_j.low)
                        zs.gg = gg
                        zs.dd = dd
                        j += 1
                    else:
                        break

                i = j
            else:
                i += 1

        self._zs_list = zs_list
        return zs_list

    # ============ 买卖点检测 ============

    def detect_buy_sell_points(self) -> List[BuySellPoint]:
        """检测买卖点"""
        if self._buy_sell_points is not None:
            return self._buy_sell_points

        points = []
        zs_list = self.calc_zs_list()
        bi_list = self.bi_list

        if not zs_list or len(bi_list) < 5:
            self._buy_sell_points = points
            return points

        for zs in zs_list:
            # 类二买检测
            bsp = self._detect_second_buy(zs, bi_list)
            if bsp:
                points.append(bsp)

            # 中枢震荡买点检测
            bsp = self._detect_shock_buy(zs, bi_list)
            if bsp:
                points.append(bsp)

            # 中枢震荡卖点检测
            bsp = self._detect_shock_sell(zs, bi_list)
            if bsp:
                points.append(bsp)

        self._buy_sell_points = points
        return points

    def _detect_second_buy(self, zs: ZS, bi_list) -> Optional[BuySellPoint]:
        """
        类二买检测
        
        条件：
        1. 前面有上升趋势（至少2个中枢）
        2. 回调到中枢上沿附近
        3. 回调不破中枢下沿
        4. 回调笔数 <= 3
        """
        zs_list = self._zs_list or []
        
        # 需要至少2个中枢
        if len(zs_list) < 2:
            return None

        # 检查是否有上升趋势的前一个中枢
        prev_zs = None
        for z in zs_list:
            if z.index < zs.index and z.zg > zs.zg:
                prev_zs = z
                break

        if not prev_zs:
            return None

        # 检查最后一笔是否回调到中枢上沿附近
        last_bi = bi_list[-1]
        if last_bi.direction == "down":
            # 回调到中枢上沿附近（±5%）
            tolerance = (zs.zg - zs.zd) * 0.2
            if abs(last_bi.low - zs.zg) < tolerance:
                # 不破中枢下沿
                if last_bi.low > zs.zd:
                    return BuySellPoint(
                        index=len(bi_list) - 1,
                        type="buy2",
                        price=last_bi.low,
                        direction="up",
                        bi_index=len(bi_list) - 1,
                        zs_range=(zs.zd, zs.zg),
                        confidence=0.7
                    )
        return None

    def _detect_shock_buy(self, zs: ZS, bi_list) -> Optional[BuySellPoint]:
        """
        中枢震荡买点检测
        
        条件：
        1. 价格触及中枢下沿
        2. 有底分型确认
        3. 在中枢区间内
        """
        if len(bi_list) < 3:
            return None

        last_bi = bi_list[-1]
        
        # 向下笔触及中枢下沿
        if last_bi.direction == "down":
            tolerance = (zs.zg - zs.zd) * 0.15
            if abs(last_bi.low - zs.zd) < tolerance:
                # 在中枢区间内
                if last_bi.low >= zs.dd:
                    return BuySellPoint(
                        index=len(bi_list) - 1,
                        type="shock_buy",
                        price=last_bi.low,
                        direction="up",
                        bi_index=len(bi_list) - 1,
                        zs_range=(zs.zd, zs.zg),
                        confidence=0.6
                    )
        return None

    def _detect_shock_sell(self, zs: ZS, bi_list) -> Optional[BuySellPoint]:
        """
        中枢震荡卖点检测
        
        条件：
        1. 价格触及中枢上沿
        2. 有顶分型确认
        3. 在中枢区间内
        """
        if len(bi_list) < 3:
            return None

        last_bi = bi_list[-1]
        
        # 向上笔触及中枢上沿
        if last_bi.direction == "up":
            tolerance = (zs.zg - zs.zd) * 0.15
            if abs(last_bi.high - zs.zg) < tolerance:
                # 在中枢区间内
                if last_bi.high <= zs.gg:
                    return BuySellPoint(
                        index=len(bi_list) - 1,
                        type="shock_sell",
                        price=last_bi.high,
                        direction="down",
                        bi_index=len(bi_list) - 1,
                        zs_range=(zs.zd, zs.zg),
                        confidence=0.6
                    )
        return None

    # ============ 趋势判断 ============

    def judge_trend(self) -> str:
        """
        判断趋势
        - up: 中枢逐步上移
        - down: 中枢逐步下移
        - neutral: 中枢震荡
        """
        zs_list = self.calc_zs_list()
        if len(zs_list) < 2:
            return "neutral"

        # 比较最近两个中枢
        last_zs = zs_list[-1]
        prev_zs = zs_list[-2]

        if last_zs.zg > prev_zs.zg and last_zs.zd > prev_zs.zd:
            return "up"
        elif last_zs.zg < prev_zs.zg and last_zs.zd < prev_zs.zd:
            return "down"
        else:
            return "neutral"

    # ============ 背驰检测 ============

    def detect_divergence(self) -> Dict:
        """
        背驰检测
        比较最后一笔与前一笔的力度
        """
        bi_list = self.bi_list
        if len(bi_list) < 3:
            return {"divergence": False, "type": None}

        last_bi = bi_list[-1]
        prev_bi = bi_list[-2]
        prev_prev_bi = bi_list[-3]

        # 计算笔力度（简化：用振幅 * K线数）
        last_bars = len(last_bi.bars) if hasattr(last_bi, 'bars') and hasattr(last_bi.bars, '__len__') else 1
        prev_bars = len(prev_bi.bars) if hasattr(prev_bi, 'bars') and hasattr(prev_bi.bars, '__len__') else 1
        last_strength = abs(last_bi.high - last_bi.low) * last_bars
        prev_strength = abs(prev_bi.high - prev_bi.low) * prev_bars

        # 底背驰：向下笔创新低但力度减弱
        if last_bi.direction == "down" and prev_bi.direction == "down":
            if last_bi.low < prev_bi.low and last_strength < prev_strength * 0.8:
                return {
                    "divergence": True,
                    "type": "bottom",
                    "current_strength": last_strength,
                    "previous_strength": prev_strength,
                    "ratio": last_strength / prev_strength if prev_strength > 0 else 0
                }

        # 顶背驰：向上笔创新高但力度减弱
        if last_bi.direction == "up" and prev_bi.direction == "up":
            if last_bi.high > prev_bi.high and last_strength < prev_strength * 0.8:
                return {
                    "divergence": True,
                    "type": "top",
                    "current_strength": last_strength,
                    "previous_strength": prev_strength,
                    "ratio": last_strength / prev_strength if prev_strength > 0 else 0
                }

        return {"divergence": False, "type": None}

    # ============ 综合分析 ============

    def full_analysis(self) -> Dict:
        """完整分析"""
        zs_list = self.calc_zs_list()
        bsp_list = self.detect_buy_sell_points()
        trend = self.judge_trend()
        divergence = self.detect_divergence()

        return {
            "bi_count": len(self.bi_list),
            "zs_count": len(zs_list),
            "trend": trend,
            "divergence": divergence,
            "buy_sell_points": [
                {
                    "type": bsp.type,
                    "price": bsp.price,
                    "direction": bsp.direction,
                    "confidence": bsp.confidence,
                    "zs_range": bsp.zs_range
                }
                for bsp in bsp_list
            ],
            "last_zs": {
                "zg": zs_list[-1].zg,
                "zd": zs_list[-1].zd,
                "gg": zs_list[-1].gg,
                "dd": zs_list[-1].dd
            } if zs_list else None,
            "last_bi": {
                "direction": self.bi_list[-1].direction,
                "high": self.bi_list[-1].high,
                "low": self.bi_list[-1].low
            } if self.bi_list else None
        }


# ============ 测试 ============

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from chanlun_perception import ChanlunPerception

    p = ChanlunPerception()
    klines = p.get_kline_data('CRCL', 'US', '1d', limit=200)

    if klines:
        df = pd.DataFrame(klines)
        df['dt'] = pd.to_datetime(df['timestamp'])
        df['symbol'] = 'CRCL'
        df['amount'] = df['vol'] * df['close']
        df = df[['dt', 'symbol', 'open', 'high', 'low', 'close', 'vol', 'amount']].copy()

        bars = format_standard_kline(df, freq=Freq.D)
        ka = CZSC(bars)

        ext = CzscExtension(ka)
        result = ext.full_analysis()

        print("=" * 60)
        print("📊 CRCL 缠论扩展分析")
        print("=" * 60)
        print(f"笔数: {result['bi_count']}")
        print(f"中枢数: {result['zs_count']}")
        print(f"趋势: {result['trend']}")
        print(f"背驰: {result['divergence']}")
        print(f"买卖点: {result['buy_sell_points']}")
        if result['last_zs']:
            print(f"最后中枢: [{result['last_zs']['zd']:.2f}, {result['last_zs']['zg']:.2f}]")
