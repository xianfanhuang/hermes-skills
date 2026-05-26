#!/usr/bin/env python3
"""
czsc v0.10.12 API 扩展 - 智能级别确立 + 类二买 & 中枢震荡买卖点

核心升级：结构状态驱动的级别确立
- 趋势中 → 锁定当前级别，不放大
- 盘整中 → 放大一级或不交易
- 转折中 → 缩小一级精确入场

Author: Trading Assistant
Version: 2.0.0 - 智能级别确立
"""

import czsc
from czsc import CZSC, Freq, format_standard_kline, Direction
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
import logging

logger = logging.getLogger("CzscExtension")


# ============ 数据结构 ============

@dataclass
class BuySellPoint:
    """买卖点"""
    index: int
    type: str  # buy1/buy2/buy3/sell1/sell2/sell3/shock_buy/shock_sell
    price: float
    direction: str  # up/down
    bi_index: int
    zs_range: Optional[tuple] = None
    confidence: float = 0.0


@dataclass
class ZS:
    """中枢"""
    index: int
    zg: float  # 中枢上沿
    zd: float  # 中枢下沿
    gg: float  # 最高点
    dd: float  # 最低点
    bi_indices: List[int] = field(default_factory=list)


@dataclass
class StructureState:
    """
    走势结构状态 — 智能级别确立的核心

    state:
        'trending'  — 趋势中（中枢上移/下移），锁死当前级别
        'ranging'   — 盘整中（中枢重叠），放大级别或不交易
        'turning'   — 转折中（背驰出现），缩小级别精确入场
        'unknown'   — 数据不足

    trend_direction:
        'up' / 'down' / None（盘整时无方向）

    strength:
        趋势强度 0-1，用于过滤弱信号
    """
    state: str  # trending / ranging / turning / unknown
    trend_direction: Optional[str]  # up / down / None
    strength: float  # 0-1
    zs_movement: str  # up / down / overlap / none
    divergence: Dict = field(default_factory=dict)
    zs_count: int = 0
    bi_count: int = 0
    last_zs: Optional[ZS] = None
    detail: str = ""

    def is_trending(self) -> bool:
        return self.state == 'trending'

    def is_ranging(self) -> bool:
        return self.state == 'ranging'

    def is_turning(self) -> bool:
        return self.state == 'turning'

    def should_follow_trend(self) -> bool:
        """趋势中：锁死当前级别，不放大"""
        return self.state == 'trending' and self.strength > 0.3

    def should_wait_breakout(self) -> bool:
        """盘整中：放大级别等突破，或不交易"""
        return self.state == 'ranging'

    def should_catch_reversal(self) -> bool:
        """转折中：缩小级别精确入场"""
        return self.state == 'turning' and self.divergence.get('confidence', 0) > 0.5


class CzscExtension:
    """czsc v0.10.12 扩展 - 智能级别确立 + 买卖点"""

    def __init__(self, ka: CZSC, symbol: str = "", timeframe: str = ""):
        self.ka = ka
        self.bi_list = ka.bi_list
        self.fx_list = ka.fx_list
        self.symbol = symbol
        self.timeframe = timeframe
        self._zs_list: Optional[List[ZS]] = None
        self._buy_sell_points: Optional[List[BuySellPoint]] = None
        self._structure_state: Optional[StructureState] = None

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

            overlap_high = min(bi1.high, bi2.high, bi3.high)
            overlap_low = max(bi1.low, bi2.low, bi3.low)

            if overlap_high > overlap_low:
                gg = max(bi1.high, bi2.high, bi3.high)
                dd = min(bi1.low, bi2.low, bi3.low)

                zs = ZS(
                    index=zs_index,
                    zg=overlap_high,
                    zd=overlap_low,
                    gg=gg,
                    dd=dd,
                    bi_indices=[i, i + 1, i + 2]
                )
                zs_list.append(zs)
                zs_index += 1

                j = i + 3
                while j < len(bi_list):
                    bi_j = bi_list[j]
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

    # ============ 智能级别确立：结构状态分析 ============

    def get_structure_state(self) -> StructureState:
        """
        核心方法：判断当前走势结构状态

        逻辑：
        1. 中枢上移/下移 → 趋势
        2. 中枢重叠 → 盘整
        3. 背驰出现 → 转折（优先级最高，覆盖前两项）
        4. 综合评估趋势强度

        Returns:
            StructureState 实例
        """
        if self._structure_state is not None:
            return self._structure_state

        zs_list = self.calc_zs_list()
        bi_list = self.bi_list
        bi_count = len(bi_list)
        zs_count = len(zs_list)

        # 数据不足
        if zs_count < 1 or bi_count < 5:
            self._structure_state = StructureState(
                state='unknown',
                trend_direction=None,
                strength=0.0,
                zs_movement='none',
                zs_count=zs_count,
                bi_count=bi_count,
                detail="数据不足，无法判断结构"
            )
            return self._structure_state

        last_zs = zs_list[-1]

        # Step 1: 分析中枢运动
        zs_movement, movement_detail = self._analyze_zs_movement(zs_list)

        # Step 2: 检测背驰
        divergence = self._detect_divergence_enhanced(bi_list)

        # Step 3: 计算趋势强度
        strength = self._calc_trend_strength(zs_list, bi_list, zs_movement)

        # Step 4: 确定最终状态（背驰优先）
        if divergence.get('detected') and divergence.get('confidence', 0) > 0.5:
            # 背驰出现 = 转折，但需要确认是否在趋势末端
            state = 'turning'
            trend_dir = None
            detail = f"转折: {divergence.get('type', '')}背驰, 置信度{divergence.get('confidence', 0):.1%}"
        elif zs_movement == 'up':
            state = 'trending'
            trend_dir = 'up'
            detail = f"上升趋势: {movement_detail}, 强度{strength:.1%}"
        elif zs_movement == 'down':
            state = 'trending'
            trend_dir = 'down'
            detail = f"下降趋势: {movement_detail}, 强度{strength:.1%}"
        elif zs_movement == 'overlap':
            state = 'ranging'
            trend_dir = None
            detail = f"盘整: {movement_detail}"
        else:
            state = 'unknown'
            trend_dir = None
            detail = "无法判断"

        self._structure_state = StructureState(
            state=state,
            trend_direction=trend_dir,
            strength=strength,
            zs_movement=zs_movement,
            divergence=divergence,
            zs_count=zs_count,
            bi_count=bi_count,
            last_zs=last_zs,
            detail=detail
        )

        logger.debug(f"[{self.symbol}/{self.timeframe}] 结构: {detail}")
        return self._structure_state

    def _analyze_zs_movement(self, zs_list: List[ZS]) -> Tuple[str, str]:
        """
        分析中枢运动方向

        Returns:
            (movement_type, detail_str)
            movement_type: 'up' / 'down' / 'overlap' / 'none'
        """
        if len(zs_list) < 2:
            return 'none', '仅1个中枢，无法判断方向'

        last = zs_list[-1]
        prev = zs_list[-2]

        # 中枢上移：当前中枢下沿 > 前一中枢下沿 且 当前中枢上沿 > 前一中枢上沿
        if last.zd > prev.zd and last.zg > prev.zg:
            gap_pct = (last.zd - prev.zd) / prev.zd * 100
            return 'up', f"中枢上移 {gap_pct:+.1f}% (前[{prev.zd:.2f},{prev.zg:.2f}]→现[{last.zd:.2f},{last.zg:.2f}])"

        # 中枢下移
        if last.zd < prev.zd and last.zg < prev.zg:
            gap_pct = (last.zd - prev.zd) / prev.zd * 100
            return 'down', f"中枢下移 {gap_pct:+.1f}% (前[{prev.zd:.2f},{prev.zg:.2f}]→现[{last.zd:.2f},{last.zg:.2f}])"

        # 中枢重叠 = 盘整
        overlap_high = min(last.zg, prev.zg)
        overlap_low = max(last.zd, prev.zd)
        if overlap_high > overlap_low:
            overlap_pct = (overlap_high - overlap_low) / (last.zg - last.zd) * 100 if (last.zg - last.zd) > 0 else 0
            return 'overlap', f"中枢重叠 {overlap_pct:.0f}% ([{prev.zd:.2f},{prev.zg:.2f}]∩[{last.zd:.2f},{last.zg:.2f}])"

        # 不重叠但方向不明确
        return 'none', "中枢关系不明确"

    def _detect_divergence_enhanced(self, bi_list) -> Dict:
        """
        增强版背驰检测

        检测三类背驰：
        1. 趋势背驰：同向两笔创新高/低但力度减弱
        2. 盘整背驰：中枢震荡中力度递减
        3. 小级别背驰：最后一笔内部力度衰减

        Returns:
            {
                'detected': bool,
                'type': 'top' / 'bottom' / None,
                'confidence': 0-1,
                'detail': str
            }
        """
        if len(bi_list) < 3:
            return {'detected': False, 'type': None, 'confidence': 0, 'detail': '笔数不足'}

        last_bi = bi_list[-1]
        prev_bi = bi_list[-2]
        prev_prev_bi = bi_list[-3]

        # 计算笔力度：振幅 × K线数（MACD面积的简化版）
        def bi_strength(bi):
            bars_count = len(bi.bars) if hasattr(bi, 'bars') and hasattr(bi.bars, '__len__') else 1
            amplitude = abs(bi.high - bi.low)
            return amplitude * bars_count

        last_str = bi_strength(last_bi)
        prev_str = bi_strength(prev_bi)

        # ---- 底背驰：向下笔创新低但力度减弱 ----
        if last_bi.direction == Direction.Down and prev_bi.direction == Direction.Down:
            if last_bi.low < prev_bi.low:
                ratio = last_str / prev_str if prev_str > 0 else 1.0
                if ratio < 0.8:
                    confidence = min(0.9, 0.5 + (0.8 - ratio))
                    return {
                        'detected': True,
                        'type': 'bottom',
                        'confidence': confidence,
                        'ratio': ratio,
                        'detail': f"底背驰: 新低${last_bi.low:.2f}<${prev_bi.low:.2f}, 力度比{ratio:.2f}"
                    }

        # ---- 顶背驰：向上笔创新高但力度减弱 ----
        if last_bi.direction == Direction.Up and prev_bi.direction == Direction.Up:
            if last_bi.high > prev_bi.high:
                ratio = last_str / prev_str if prev_str > 0 else 1.0
                if ratio < 0.8:
                    confidence = min(0.9, 0.5 + (0.8 - ratio))
                    return {
                        'detected': True,
                        'type': 'top',
                        'confidence': confidence,
                        'ratio': ratio,
                        'detail': f"顶背驰: 新高${last_bi.high:.2f}>${prev_bi.high:.2f}, 力度比{ratio:.2f}"
                    }

        # ---- 盘整背驰：中枢内震荡力度递减 ----
        zs_list = self._zs_list or []
        if zs_list:
            last_zs = zs_list[-1]
            # 找中枢内的笔
            zs_bis = [bi_list[i] for i in last_zs.bi_indices if i < len(bi_list)]
            if len(zs_bis) >= 4:
                # 比较前半段和后半段的力度
                mid = len(zs_bis) // 2
                first_half_str = sum(bi_strength(b) for b in zs_bis[:mid])
                second_half_str = sum(bi_strength(b) for b in zs_bis[mid:])
                if first_half_str > 0 and second_half_str / first_half_str < 0.7:
                    return {
                        'detected': True,
                        'type': 'shock_exhaustion',
                        'confidence': 0.6,
                        'ratio': second_half_str / first_half_str,
                        'detail': f"盘整力度衰减: 后半段/前半段={second_half_str/first_half_str:.2f}"
                    }

        return {'detected': False, 'type': None, 'confidence': 0, 'detail': '无背驰'}

    def _calc_trend_strength(self, zs_list: List[ZS], bi_list, zs_movement: str) -> float:
        """
        计算趋势强度 0-1

        因素：
        1. 中枢移动幅度（越大越强）
        2. 中枢移动一致性（连续上移/下移越多越强）
        3. 笔的斜率一致性
        4. 最后一笔是否加速
        """
        if zs_movement not in ('up', 'down'):
            return 0.0

        strength = 0.0

        # 因素1：中枢移动幅度（权重0.3）
        if len(zs_list) >= 2:
            last = zs_list[-1]
            prev = zs_list[-2]
            move_pct = abs(last.zd - prev.zd) / prev.zd if prev.zd > 0 else 0
            # 5%以上的移动算强
            strength += min(0.3, move_pct * 3)

        # 因素2：连续中枢方向一致性（权重0.3）
        if len(zs_list) >= 3:
            consistent = 0
            for i in range(len(zs_list) - 1, 0, -1):
                if zs_movement == 'up' and zs_list[i].zd > zs_list[i-1].zd:
                    consistent += 1
                elif zs_movement == 'down' and zs_list[i].zd < zs_list[i-1].zd:
                    consistent += 1
                else:
                    break
            strength += min(0.3, consistent * 0.15)

        # 因素3：笔方向一致性（权重0.2）
        if len(bi_list) >= 5:
            recent_bis = bi_list[-5:]
            if zs_movement == 'up':
                up_bis = [b for b in recent_bis if b.direction == Direction.Up]
                down_bis = [b for b in recent_bis if b.direction == Direction.Down]
                if up_bis and down_bis:
                    avg_up = sum(abs(b.high - b.low) for b in up_bis) / len(up_bis)
                    avg_down = sum(abs(b.high - b.low) for b in down_bis) / len(down_bis)
                    if avg_up > avg_down:
                        strength += 0.2 * min(1.0, avg_up / avg_down - 0.5)
            else:
                up_bis = [b for b in recent_bis if b.direction == Direction.Up]
                down_bis = [b for b in recent_bis if b.direction == Direction.Down]
                if up_bis and down_bis:
                    avg_up = sum(abs(b.high - b.low) for b in up_bis) / len(up_bis)
                    avg_down = sum(abs(b.high - b.low) for b in down_bis) / len(down_bis)
                    if avg_down > avg_up:
                        strength += 0.2 * min(1.0, avg_down / avg_up - 0.5)

        # 因素4：最后一笔加速度（权重0.2）
        if len(bi_list) >= 3:
            last_str = abs(bi_list[-1].high - bi_list[-1].low)
            prev_str = abs(bi_list[-2].high - bi_list[-2].low)
            if prev_str > 0:
                accel = last_str / prev_str
                if (zs_movement == 'up' and bi_list[-1].direction == Direction.Up) or \
                   (zs_movement == 'down' and bi_list[-1].direction == Direction.Down):
                    if accel > 1.2:
                        strength += min(0.2, (accel - 1.0) * 0.1)

        return min(1.0, strength)

    def calc_trend_fluency(self) -> Dict:
        """
        趋势流畅度分析 — VAN的核心洞察

        核心原则：凡强趋必然浅回调，不论多空。
        流畅趋势 = 小级别长时间延续 = 主力目标

        流畅度指标：
        1. 回调深度（最核心）— 强趋必然浅回调，这是本质特征
        2. 中枢重叠度（越低越流畅）— 中枢之间不重叠=强趋势
        3. 笔方向一致性（越高越流畅）— 同向笔占比
        4. 中枢上移/下移连续性（越连续越流畅）
        5. 时间跨度（流畅趋势可以持续很久）

        Returns:
            {
                'fluency': 0-1,  # 流畅度
                'is_smooth': bool,  # 是否流畅
                'continuation_bars': int,  # 趋势持续K线数
                'zs_overlap_ratio': float,  # 中枢重叠比例（越低越好）
                'pullback_depth': float,  # 平均回调深度（越浅越好）
                'direction_consistency': float,  # 方向一致性
                'detail': str
            }
        """
        zs_list = self.calc_zs_list()
        bi_list = self.bi_list

        if len(zs_list) < 2 or len(bi_list) < 5:
            return {
                'fluency': 0.0,
                'is_smooth': False,
                'continuation_bars': 0,
                'zs_overlap_ratio': 1.0,
                'pullback_depth': 1.0,
                'direction_consistency': 0.0,
                'detail': '数据不足'
            }

        # ---- 1. 中枢重叠度 ----
        # 流畅趋势的中枢之间应该不重叠或重叠很小
        overlap_count = 0
        total_pairs = len(zs_list) - 1
        for i in range(total_pairs):
            curr = zs_list[i + 1]
            prev = zs_list[i]
            # 中枢重叠：当前下沿 < 前一上沿
            if curr.zd < prev.zg and curr.zg > prev.zd:
                overlap_ratio = (min(curr.zg, prev.zg) - max(curr.zd, prev.zd)) / (curr.zg - curr.zd) if (curr.zg - curr.zd) > 0 else 1
                overlap_count += overlap_ratio

        zs_overlap_ratio = overlap_count / total_pairs if total_pairs > 0 else 1.0

        # ---- 2. 回调深度 ----
        # 流畅趋势中，回调笔应该浅（不破前中枢上沿或只破一点）
        pullback_depths = []
        for i, bi in enumerate(bi_list):
            if bi.direction == Direction.Down and i > 0:
                # 回调深度 = 回调幅度 / 前面上涨幅度
                prev_up = bi_list[i - 1]
                if prev_up.direction == Direction.Up and prev_up.high > prev_up.low:
                    pullback = (prev_up.high - bi.low) / (prev_up.high - prev_up.low)
                    pullback_depths.append(min(pullback, 2.0))

        avg_pullback = sum(pullback_depths) / len(pullback_depths) if pullback_depths else 1.0

        # ---- 3. 笔方向一致性 ----
        # 流畅趋势中，同向笔应该占主导
        trend_dir = 'up' if zs_list[-1].zd > zs_list[-2].zd else 'down'
        if trend_dir == 'up':
            trend_bis = sum(1 for b in bi_list[-8:] if b.direction == Direction.Up)
            total_bis = min(8, len(bi_list))
        else:
            trend_bis = sum(1 for b in bi_list[-8:] if b.direction == Direction.Down)
            total_bis = min(8, len(bi_list))

        direction_consistency = trend_bis / total_bis if total_bis > 0 else 0

        # ---- 4. 时间跨度 ----
        continuation_bars = len(bi_list)

        # ---- 综合流畅度 ----
        # 权重：回调浅(40%, 最核心) + 中枢不重叠(25%) + 方向一致(20%) + 中枢连续(15%)
        # VAN原则：凡强趋必然浅回调，不论多空
        fluency = 0.0

        # 回调浅（最核心指标，权重40%）
        # 强趋势中回调笔幅度 < 上涨笔幅度的50% = 浅回调
        pullback_score = max(0, 1.0 - avg_pullback / 1.0) if avg_pullback < 1.0 else max(0, 0.5 - avg_pullback / 4)
        fluency += pullback_score * 0.40

        # 中枢不重叠（重叠越少越好，权重25%）
        fluency += max(0, 1.0 - zs_overlap_ratio) * 0.25

        # 方向一致（权重20%）
        fluency += direction_consistency * 0.20

        # 中枢连续上移/下移（权重15%）
        consistent_zs = 0
        for i in range(len(zs_list) - 1, 0, -1):
            if trend_dir == 'up' and zs_list[i].zd > zs_list[i-1].zd:
                consistent_zs += 1
            elif trend_dir == 'down' and zs_list[i].zd < zs_list[i-1].zd:
                consistent_zs += 1
            else:
                break
        zs_consistency = min(1.0, consistent_zs / 3)  # 3个连续中枢=满分
        fluency += zs_consistency * 0.15

        fluency = min(1.0, fluency)
        is_smooth = fluency > 0.5

        detail_parts = []
        detail_parts.append(f"中枢重叠{zs_overlap_ratio:.0%}")
        detail_parts.append(f"回调深度{avg_pullback:.1%}")
        detail_parts.append(f"方向一致{direction_consistency:.0%}")
        detail_parts.append(f"连续{consistent_zs}中枢")

        if is_smooth:
            detail = f"流畅趋势 ✅ ({', '.join(detail_parts)})"
        else:
            detail = f"不流畅 ⚠️ ({', '.join(detail_parts)})"

        return {
            'fluency': fluency,
            'is_smooth': is_smooth,
            'continuation_bars': continuation_bars,
            'zs_overlap_ratio': zs_overlap_ratio,
            'pullback_depth': avg_pullback,
            'direction_consistency': direction_consistency,
            'trend_direction': trend_dir,
            'consistent_zs_count': consistent_zs,
            'detail': detail,
        }

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

        # 一买检测：趋势末端背驰
        bsp = self._detect_first_buy(zs_list, bi_list)
        if bsp:
            points.append(bsp)

        # 一卖检测
        bsp = self._detect_first_sell(zs_list, bi_list)
        if bsp:
            points.append(bsp)

        for zs in zs_list:
            # 类二买
            bsp = self._detect_second_buy(zs, bi_list)
            if bsp:
                points.append(bsp)

            # 三买
            bsp = self._detect_third_buy(zs, bi_list)
            if bsp:
                points.append(bsp)

            # 中枢震荡买卖点
            bsp = self._detect_shock_buy(zs, bi_list)
            if bsp:
                points.append(bsp)

            bsp = self._detect_shock_sell(zs, bi_list)
            if bsp:
                points.append(bsp)

        self._buy_sell_points = points
        return points

    def _detect_first_buy(self, zs_list: List[ZS], bi_list) -> Optional[BuySellPoint]:
        """
        一买检测：下降趋势末端底背驰

        条件：
        1. 至少2个中枢下移
        2. 最后一笔向下创新低
        3. 底背驰
        """
        if len(zs_list) < 2 or len(bi_list) < 3:
            return None

        # 检查是否有下降趋势
        if not (zs_list[-1].zd < zs_list[-2].zd and zs_list[-1].zg < zs_list[-2].zg):
            return None

        last_bi = bi_list[-1]
        if last_bi.direction != Direction.Down:
            return None

        # 检查背驰
        divergence = self._detect_divergence_enhanced(bi_list)
        if divergence.get('detected') and divergence.get('type') == 'bottom':
            return BuySellPoint(
                index=len(bi_list) - 1,
                type="buy1",
                price=last_bi.low,
                direction="up",
                bi_index=len(bi_list) - 1,
                zs_range=(zs_list[-1].zd, zs_list[-1].zg),
                confidence=divergence.get('confidence', 0.6)
            )
        return None

    def _detect_first_sell(self, zs_list: List[ZS], bi_list) -> Optional[BuySellPoint]:
        """
        一卖检测：上升趋势末端顶背驰
        """
        if len(zs_list) < 2 or len(bi_list) < 3:
            return None

        if not (zs_list[-1].zd > zs_list[-2].zd and zs_list[-1].zg > zs_list[-2].zg):
            return None

        last_bi = bi_list[-1]
        if last_bi.direction != Direction.Up:
            return None

        divergence = self._detect_divergence_enhanced(bi_list)
        if divergence.get('detected') and divergence.get('type') == 'top':
            return BuySellPoint(
                index=len(bi_list) - 1,
                type="sell1",
                price=last_bi.high,
                direction="down",
                bi_index=len(bi_list) - 1,
                zs_range=(zs_list[-1].zd, zs_list[-1].zg),
                confidence=divergence.get('confidence', 0.6)
            )
        return None

    def _detect_third_buy(self, zs: ZS, bi_list) -> Optional[BuySellPoint]:
        """
        三买检测：回调不进中枢

        条件：
        1. 上升趋势中
        2. 回调的低点 > 中枢上沿
        3. 随后的向上笔确认
        """
        zs_list = self._zs_list or []
        if len(zs_list) < 2:
            return None

        # 检查是否在上升趋势
        if not (zs.zd > (zs_list[zs.index - 1].zd if zs.index > 0 else 0)):
            return None

        # 找中枢后的笔
        last_bi_idx = zs.bi_indices[-1] if zs.bi_indices else 0
        after_bis = [b for i, b in enumerate(bi_list) if i > last_bi_idx]

        if len(after_bis) < 2:
            return None

        # 第一笔向下（离开中枢），第二笔向上（回调）
        leave_bi = after_bis[0]
        back_bi = after_bis[1]

        if leave_bi.direction == Direction.Up and back_bi.direction == Direction.Down:
            # 回调不进中枢
            if back_bi.low > zs.zg:
                return BuySellPoint(
                    index=bi_list.index(back_bi) if back_bi in bi_list else len(bi_list) - 1,
                    type="buy3",
                    price=back_bi.low,
                    direction="up",
                    bi_index=len(bi_list) - 1,
                    zs_range=(zs.zd, zs.zg),
                    confidence=0.75
                )
        return None

    def _detect_second_buy(self, zs: ZS, bi_list) -> Optional[BuySellPoint]:
        """类二买检测"""
        zs_list = self._zs_list or []
        if len(zs_list) < 2:
            return None

        prev_zs = None
        for z in zs_list:
            if z.index < zs.index and z.zg > zs.zg:
                prev_zs = z
                break

        if not prev_zs:
            return None

        last_bi = bi_list[-1]
        if last_bi.direction == Direction.Down:
            tolerance = (zs.zg - zs.zd) * 0.2
            if abs(last_bi.low - zs.zg) < tolerance and last_bi.low > zs.zd:
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
        """中枢震荡买点"""
        if len(bi_list) < 3:
            return None

        last_bi = bi_list[-1]
        if last_bi.direction == Direction.Down:
            tolerance = (zs.zg - zs.zd) * 0.15
            if abs(last_bi.low - zs.zd) < tolerance and last_bi.low >= zs.dd:
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
        """中枢震荡卖点"""
        if len(bi_list) < 3:
            return None

        last_bi = bi_list[-1]
        if last_bi.direction == Direction.Up:
            tolerance = (zs.zg - zs.zd) * 0.15
            if abs(last_bi.high - zs.zg) < tolerance and last_bi.high <= zs.gg:
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

    # ============ 兼容旧接口 ============

    def judge_trend(self) -> str:
        """兼容旧接口：返回 up/down/neutral"""
        state = self.get_structure_state()
        return state.trend_direction or "neutral"

    def detect_divergence(self) -> Dict:
        """兼容旧接口"""
        state = self.get_structure_state()
        d = state.divergence
        return {
            "divergence": d.get('detected', False),
            "type": d.get('type'),
            "confidence": d.get('confidence', 0),
            "detail": d.get('detail', '')
        }

    def full_analysis(self) -> Dict:
        """完整分析"""
        state = self.get_structure_state()
        zs_list = self.calc_zs_list()
        bsp_list = self.detect_buy_sell_points()
        fluency = self.calc_trend_fluency()

        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "bi_count": state.bi_count,
            "zs_count": state.zs_count,
            "structure_state": state.state,
            "trend_direction": state.trend_direction,
            "trend_strength": state.strength,
            "trend_fluency": fluency,
            "zs_movement": state.zs_movement,
            "divergence": state.divergence,
            "detail": state.detail,
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
            } if self.bi_list else None,
            "should_follow_trend": state.should_follow_trend(),
            "should_wait_breakout": state.should_wait_breakout(),
            "should_catch_reversal": state.should_catch_reversal(),
        }


# ============ 测试 ============

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from chanlun_perception import ChanlunPerception

    p = ChanlunPerception()

    for symbol in ['CRCL']:
        for tf_name, tf_code in [('daily', '1d'), ('30min', '30m'), ('5min', '5m')]:
            print(f"\n{'='*60}")
            print(f"📊 {symbol} {tf_name} 缠论结构分析")
            print(f"{'='*60}")

            klines = p.get_kline_data(symbol, 'US', tf_code, limit=200)
            if not klines:
                print("  数据不足")
                continue

            df = pd.DataFrame(klines)
            df['dt'] = pd.to_datetime(df['timestamp'])
            df['symbol'] = symbol
            df['amount'] = df['vol'] * df['close']
            df = df[['dt', 'symbol', 'open', 'high', 'low', 'close', 'vol', 'amount']].copy()

            freq = Freq.D if tf_name == 'daily' else (Freq.F30 if tf_name == '30min' else Freq.F5)
            bars = format_standard_kline(df, freq=freq)
            ka = CZSC(bars)

            ext = CzscExtension(ka, symbol=symbol, timeframe=tf_name)
            result = ext.full_analysis()

            print(f"笔数: {result['bi_count']} | 中枢数: {result['zs_count']}")
            print(f"结构状态: {result['structure_state']}")
            print(f"趋势方向: {result['trend_direction']}")
            print(f"趋势强度: {result['trend_strength']:.1%}")
            print(f"中枢运动: {result['zs_movement']}")
            print(f"背驰: {result['divergence']}")
            print(f"详情: {result['detail']}")
            print(f"建议: 跟趋势={result['should_follow_trend']} | 等突破={result['should_wait_breakout']} | 捕反转={result['should_catch_reversal']}")
            if result['buy_sell_points']:
                for bsp in result['buy_sell_points']:
                    print(f"  📍 {bsp['type']}: ${bsp['price']:.2f} [{bsp['direction']}] 置信度{bsp['confidence']:.0%}")
