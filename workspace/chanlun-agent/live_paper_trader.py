#!/usr/bin/env python3
"""
Live Paper Trading Simulation - 实时交易模拟

功能：
1. 实时获取多周期K线（daily/30min/5min）
2. 智能确定缠论交易级别
3. 多级别共振分析
4. 支持做多/做空（单边）
5. 风控引擎实时监控
6. 自动反思 + RGB知识库更新

Author: Trading Assistant
Version: 1.0.0
"""

import sys
import os
import json
import time
import logging
from typing import Tuple
from datetime import datetime, timedelta
from pathlib import Path

# 项目路径
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR / "data"))
sys.path.insert(0, str(PROJECT_DIR / "paper-trading"))

from czsc import CZSC, RawBar, Freq
from czsc_extension import CzscExtension
from rgb_updater import RGBUpdater
from crcl_tiger_trader import TigerClient, create_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_DIR / "paper-trading" / "live_sim.log", encoding='utf-8'),
    ]
)
logger = logging.getLogger("LiveSim")

# ==================== 配置 ====================

CONFIG = {
    'symbol': 'CRCL',
    'direction': 'auto',  # auto=智能确定, long=只做多, short=只做空
    'initial_capital': 100000,  # Tiger模拟盘$1M，这里用10万测试
    'risk_per_trade': 0.03,  # 单笔风险3%
    'max_position_pct': 0.50,  # 最大仓位50%
    'stop_loss_pct': 0.03,  # 止损3%
    'time_stop_bars': 12,  # 时间止损12根K线
    'max_daily_loss_pct': 0.08,  # 日最大亏损8%
    'consecutive_loss_limit': 3,  # 连亏3笔熔断
    'cooldown_minutes': 60,  # 熔断冷却60分钟
    'scan_interval': 300,  # 扫描间隔300秒(5分钟)
    'enable_short': True,  # 允许做空
}

REPORTS_DIR = PROJECT_DIR / "reports" / "live_sim"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class LivePaperTrader:
    """实时交易模拟"""

    def __init__(self, config: dict):
        self.config = config
        self.symbol = config['symbol']
        self.capital = config['initial_capital']
        self.position = None  # {direction, entry_price, quantity, entry_time, stop_loss, signal_type}
        self.trade_history = []
        self.daily_pnl = 0
        self.consecutive_losses = 0
        self.cooldown_until = None

        # 引擎
        self.rgb_updater = RGBUpdater()
        self.tiger_client = TigerClient()
        self.data_router = create_router()

        # 状态文件
        self.state_file = PROJECT_DIR / "paper-trading" / "live_sim_state.json"
        self._load_state()

        logger.info(f"🦞 实时交易模拟初始化完成")
        logger.info(f"  品种: {self.symbol}")
        logger.info(f"  方向: {config['direction']}")
        logger.info(f"  资金: ${self.capital:,.2f}")
        logger.info(f"  风险: {config['risk_per_trade']*100}%/笔")
        logger.info(f"  做空: {'✅' if config['enable_short'] else '❌'}")

    def _load_state(self):
        """加载状态"""
        if self.state_file.exists():
            try:
                state = json.loads(self.state_file.read_text())
                self.position = state.get('position')
                self.trade_history = state.get('trade_history', [])
                self.daily_pnl = state.get('daily_pnl', 0)
                self.consecutive_losses = state.get('consecutive_losses', 0)
                if state.get('cooldown_until'):
                    self.cooldown_until = datetime.fromisoformat(state['cooldown_until'])
                logger.info(f"  状态已加载: 持仓={'有' if self.position else '无'}, 历史交易={len(self.trade_history)}笔")
            except Exception as e:
                logger.warning(f"  状态加载失败: {e}")

    def _save_state(self):
        """保存状态"""
        state = {
            'symbol': self.symbol,
            'position': self.position,
            'trade_history': self.trade_history[-50:],  # 保留最近50笔
            'daily_pnl': self.daily_pnl,
            'consecutive_losses': self.consecutive_losses,
            'cooldown_until': self.cooldown_until.isoformat() if self.cooldown_until else None,
            'last_update': datetime.now().isoformat(),
        }
        self.state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))

    def get_klines(self, timeframe: str, limit: int = 200) -> list:
        """获取K线数据"""
        try:
            if timeframe == 'daily':
                df = self.tiger_client.get_daily_bars(self.symbol, limit=limit)
            elif timeframe in ('5min', '30min'):
                df = self.tiger_client.get_intraday_bars(self.symbol, period=timeframe, limit=limit)
            else:
                return []

            if df is None or df.empty:
                return []

            bars = []
            for _, row in df.iterrows():
                ts = row.get('time', 0)
                if isinstance(ts, (int, float)) and ts > 1e12:
                    dt = datetime.fromtimestamp(ts / 1000)
                else:
                    dt = datetime.now()

                bars.append(RawBar(
                    symbol=self.symbol,
                    dt=dt,
                    freq=Freq.D if timeframe == 'daily' else Freq.F5,
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    vol=float(row.get('vol', row.get('volume', 0))),
                    amount=float(row.get('amount', 0)),
                ))
            return bars
        except Exception as e:
            logger.error(f"获取K线失败: {e}")
            return []

    def analyze_all_timeframes(self) -> dict:
        """多周期分析"""
        results = {}

        for tf in ['daily', '30min', '5min']:
            bars = self.get_klines(tf, limit=200)
            if len(bars) < 100:
                logger.warning(f"  {tf}: 数据不足 ({len(bars)}根)")
                continue

            try:
                ka = CZSC(bars)
                ext = CzscExtension(ka, symbol=self.symbol, timeframe=tf)
                analysis = ext.analyze_all()

                results[tf] = {
                    'bi_count': len(ext.bi_list),
                    'zs_count': len(ext.zs_list),
                    'direction': ext.zs_list[-1].direction if ext.zs_list else 'unknown',
                    'signals': analysis.get('signals', []),
                    'best_signal': analysis.get('best_signal'),
                    'special_forms': analysis.get('special_forms', []),
                    'summary': analysis.get('summary', ''),
                    'bars': bars,
                    'ka': ka,
                    'ext': ext,
                }
                logger.info(f"  {tf}: {results[tf]['bi_count']}笔 {results[tf]['zs_count']}中枢")
            except Exception as e:
                logger.warning(f"  {tf}: 分析失败 - {e}")

        return results

    def determine_trading_direction(self, analysis: dict) -> dict:
        """
        智能级别确立 — 结构状态驱动

        核心逻辑：
        1. 趋势中 → 锁定当前级别，不放大，跟着趋势走
        2. 盘整中 → 放大级别看方向，或不交易
        3. 转折中 → 缩小级别精确入场

        Returns:
            {
                'direction': 'long'/'short'/'none',
                'strategy': 'follow_trend'/'wait_breakout'/'catch_reversal',
                'primary_tf': 'daily'/'30min'/'5min',  # 主级别
                'reason': str,
                'structure': {tf: StructureState}
            }
        """
        daily = analysis.get('daily', {})
        m30 = analysis.get('30min', {})
        m5 = analysis.get('5min', {})

        # 获取各级别结构状态
        daily_state = daily.get('ext', None)
        m30_state = m30.get('ext', None)
        m5_state = m5.get('ext', None)

        daily_struct = daily_state.get_structure_state() if daily_state else None
        m30_struct = m30_state.get_structure_state() if m30_state else None
        m5_struct = m5_state.get_structure_state() if m5_state else None

        # 数据不足时的降级处理
        if not daily_struct:
            return {'direction': 'none', 'strategy': 'none', 'primary_tf': None,
                    'reason': '数据不足', 'structure': {}}

        structure_info = {}
        for tf, s in [('daily', daily_struct), ('30min', m30_struct), ('5min', m5_struct)]:
            if s:
                structure_info[tf] = {
                    'state': s.state,
                    'direction': s.trend_direction,
                    'strength': s.strength,
                    'detail': s.detail
                }

        # ===== 策略选择 =====

        # 策略1: 日线趋势中 → 锁死级别，跟趋势
        if daily_struct.should_follow_trend():
            direction = 'long' if daily_struct.trend_direction == 'up' else 'short'

            # 检查小级别是否有同向确认（不要求必须，但加分）
            m5_confirms = False
            if m5_struct and m5_struct.trend_direction == daily_struct.trend_direction:
                m5_confirms = True

            reason = f"趋势跟随: 日线{daily_struct.detail}"
            if m5_confirms:
                reason += f" + 5分钟确认"

            return {
                'direction': direction,
                'strategy': 'follow_trend',
                'primary_tf': '5min',  # 趋势中用小级别精确入场
                'reason': reason,
                'structure': structure_info,
                'resonance_level': 3 if m5_confirms else 2,
            }

        # 策略2: 日线转折中 → 缩小级别精确入场
        if daily_struct.should_catch_reversal():
            div = daily_struct.divergence
            if div.get('type') == 'bottom':
                direction = 'long'
            elif div.get('type') == 'top':
                direction = 'short'
            else:
                direction = 'none'

            if direction != 'none':
                return {
                    'direction': direction,
                    'strategy': 'catch_reversal',
                    'primary_tf': '30min',  # 转折用中级别确认
                    'reason': f"反转捕捉: {div.get('detail', '')}",
                    'structure': structure_info,
                    'resonance_level': 1,
                }

        # 策略3: 日线盘整 → 看30分钟方向
        if daily_struct.should_wait_breakout():
            if m30_struct and m30_struct.is_trending():
                direction = 'long' if m30_struct.trend_direction == 'up' else 'short'
                return {
                    'direction': direction,
                    'strategy': 'range_breakout',
                    'primary_tf': '30min',
                    'reason': f"盘整突破: 30分钟{m30_struct.detail}",
                    'structure': structure_info,
                    'resonance_level': 1,
                }

            # 30分钟也盘整 → 看5分钟
            if m5_struct and m5_struct.is_trending():
                direction = 'long' if m5_struct.trend_direction == 'up' else 'short'
                return {
                    'direction': direction,
                    'strategy': 'range_scalp',
                    'primary_tf': '5min',
                    'reason': f"盘整内短线: 5分钟{m5_struct.detail}",
                    'structure': structure_info,
                    'resonance_level': 1,
                }

            # 都盘整 → 不交易
            return {
                'direction': 'none',
                'strategy': 'wait',
                'primary_tf': None,
                'reason': f"日线盘整，30分钟/5分钟无方向，等待",
                'structure': structure_info,
                'resonance_level': 0,
            }

        # 降级：用信号数量判断
        all_sigs = daily.get('signals', []) + m30.get('signals', []) + m5.get('signals', [])
        long_sigs = sum(1 for s in all_sigs if s.get('direction') == 'LONG' and not s.get('filtered'))
        short_sigs = sum(1 for s in all_sigs if s.get('direction') == 'SHORT' and not s.get('filtered'))

        if long_sigs >= 2 and long_sigs > short_sigs:
            return {'direction': 'long', 'strategy': 'signal_fallback', 'primary_tf': '30min',
                    'reason': f"信号降级: {long_sigs}个多头信号", 'structure': structure_info, 'resonance_level': 1}
        elif short_sigs >= 2 and short_sigs > long_sigs:
            return {'direction': 'short', 'strategy': 'signal_fallback', 'primary_tf': '30min',
                    'reason': f"信号降级: {short_sigs}个空头信号", 'structure': structure_info, 'resonance_level': 1}

        return {'direction': 'none', 'strategy': 'none', 'primary_tf': None,
                'reason': '无明确方向', 'structure': structure_info, 'resonance_level': 0}

    def check_resonance(self, analysis: dict, direction: str, strategy_result: dict = None) -> Tuple[bool, int, str]:
        """
        结构感知的共振检查

        跟随趋势策略 → 要求多级别同向
        反转捕捉策略 → 只需背驰确认
        盘整突破策略 → 只需突破方向确认
        """
        if strategy_result:
            resonance_level = strategy_result.get('resonance_level', 0)
            strategy = strategy_result.get('strategy', 'none')
            reason = strategy_result.get('reason', '')

            if strategy == 'follow_trend':
                # 趋势跟随：需要至少2级共振
                if resonance_level >= 2:
                    return True, resonance_level, f"趋势共振: {reason}"
                return False, resonance_level, f"趋势共振不足: {reason}"

            elif strategy == 'catch_reversal':
                # 反转捕捉：有背驰就行
                return True, 1, f"反转信号: {reason}"

            elif strategy in ('range_breakout', 'range_scalp'):
                # 盘整突破/短线：单级别确认即可
                return True, 1, f"盘整信号: {reason}"

            elif strategy == 'signal_fallback':
                return True, 1, f"信号降级: {reason}"

        # 降级到旧逻辑
        daily = analysis.get('daily', {})
        m30 = analysis.get('30min', {})
        m5 = analysis.get('5min', {})
        daily_dir = daily.get('direction', 'unknown')
        m30_dir = m30.get('direction', 'unknown')
        m5_dir = m5.get('direction', 'unknown')
        dir_map = {'up': 'long', 'down': 'short', 'unknown': 'none'}

        if dir_map.get(daily_dir) == direction and dir_map.get(m30_dir) == direction and dir_map.get(m5_dir) == direction:
            return True, 3, f"三级共振: 日线{daily_dir}+30分{m30_dir}+5分{m5_dir}"
        if dir_map.get(daily_dir) == direction and dir_map.get(m30_dir) == direction:
            return True, 2, f"两级共振: 日线{daily_dir}+30分{m30_dir}"
        if dir_map.get(m30_dir) == direction and dir_map.get(m5_dir) == direction:
            return True, 2, f"两级共振: 30分{m30_dir}+5分{m5_dir}"
        if dir_map.get(daily_dir) == direction:
            return True, 1, f"单级别: 日线{daily_dir}"

        return False, 0, f"无共振"

    def check_cooldown(self) -> bool:
        """检查是否在冷却期"""
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            remaining = (self.cooldown_until - datetime.now()).seconds // 60
            logger.warning(f"⏸️ 冷却中，剩余 {remaining} 分钟")
            return True
        return False

    def check_daily_loss_limit(self) -> bool:
        """检查日亏损限制"""
        if self.daily_pnl < 0 and abs(self.daily_pnl) > self.capital * self.config['max_daily_loss_pct']:
            logger.warning(f"🚫 日亏损超限: ${self.daily_pnl:.2f}")
            return True
        return False

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """计算仓位大小"""
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            return 0

        risk_amount = self.capital * self.config['risk_per_trade']
        quantity = int(risk_amount / risk_per_share)
        max_quantity = int(self.capital * self.config['max_position_pct'] / entry_price)

        return min(quantity, max_quantity)

    def generate_signal(self, analysis: dict, direction: str, strategy_result: dict = None) -> dict:
        """
        生成交易信号 — 结构感知止损

        止损逻辑根据策略不同：
        - 趋势跟随 → 止损在当前级别中枢外沿（宽止损，让利润跑）
        - 反转捕捉 → 止损在背驰极值（精确止损）
        - 盘整突破 → 止损在中枢内沿（紧止损，快速验证）
        """
        daily = analysis.get('daily', {})
        m30 = analysis.get('30min', {})
        m5 = analysis.get('5min', {})

        # 获取当前价格
        current_price = None
        for tf in ['5min', '30min', 'daily']:
            if tf in analysis and analysis[tf].get('bars'):
                current_price = analysis[tf]['bars'][-1].close
                break

        if not current_price:
            return None

        strategy = strategy_result.get('strategy', 'signal_fallback') if strategy_result else 'signal_fallback'
        primary_tf = strategy_result.get('primary_tf', '5min') if strategy_result else '5min'

        # ===== 结构感知止损 =====
        stop_loss = None

        if strategy == 'follow_trend':
            # 趋势跟随：止损在5分钟中枢下沿（用小级别，大利润空间）
            m5_ext = m5.get('ext', None)
            if m5_ext and hasattr(m5_ext, 'calc_zs_list'):
                m5_zs = m5_ext.calc_zs_list()
                if m5_zs:
                    if direction == 'long':
                        stop_loss = m5_zs[-1].zd
                    else:
                        stop_loss = m5_zs[-1].zg

            # 兜底：日线中枢
            if stop_loss is None:
                daily_ext = daily.get('ext', None)
                if daily_ext and hasattr(daily_ext, 'calc_zs_list'):
                    daily_zs = daily_ext.calc_zs_list()
                    if daily_zs:
                        stop_loss = daily_zs[-1].zd if direction == 'long' else daily_zs[-1].zg

        elif strategy == 'catch_reversal':
            # 反转捕捉：止损在背驰极值（最精确）
            daily_struct = daily.get('ext', None)
            if daily_struct:
                state = daily_struct.get_structure_state() if hasattr(daily_struct, 'get_structure_state') else None
                if state and state.divergence.get('detected'):
                    # 底背驰止损在最低点下方，顶背驰在最高点上方
                    if direction == 'long':
                        # 找最近的向下笔低点
                        bi_list = daily_struct.bi_list
                        if bi_list:
                            stop_loss = min(b.low for b in bi_list[-3:] if b.direction == 'down')
                            stop_loss = stop_loss * 0.98  # 给2%缓冲
                    else:
                        bi_list = daily_struct.bi_list
                        if bi_list:
                            stop_loss = max(b.high for b in bi_list[-3:] if b.direction == 'up')
                            stop_loss = stop_loss * 1.02

        elif strategy in ('range_breakout', 'range_scalp'):
            # 盘整突破：止损在中枢内沿（紧止损）
            if primary_tf == '30min':
                m30_ext = m30.get('ext', None)
                if m30_ext and hasattr(m30_ext, 'calc_zs_list'):
                    m30_zs = m30_ext.calc_zs_list()
                    if m30_zs:
                        if direction == 'long':
                            stop_loss = m30_zs[-1].zd  # 中枢下沿
                        else:
                            stop_loss = m30_zs[-1].zg  # 中枢上沿
            else:
                m5_ext = m5.get('ext', None)
                if m5_ext and hasattr(m5_ext, 'calc_zs_list'):
                    m5_zs = m5_ext.calc_zs_list()
                    if m5_zs:
                        stop_loss = m5_zs[-1].zd if direction == 'long' else m5_zs[-1].zg

        # 兜底止损
        if stop_loss is None:
            stop_loss = current_price * (1 - self.config['stop_loss_pct']) if direction == 'long' \
                else current_price * (1 + self.config['stop_loss_pct'])

        # 止损不能超过最大止损比例
        max_stop_pct = self.config['stop_loss_pct'] * 1.5  # 最多1.5倍默认止损
        if direction == 'long':
            stop_loss = max(stop_loss, current_price * (1 - max_stop_pct))
        else:
            stop_loss = min(stop_loss, current_price * (1 + max_stop_pct))

        # 计算仓位
        quantity = self.calculate_position_size(current_price, stop_loss)
        if quantity <= 0:
            return None

        return {
            'type': 'BUY' if direction == 'long' else 'SELL_SHORT',
            'direction': direction,
            'price': current_price,
            'stop_loss': stop_loss,
            'quantity': quantity,
            'strategy': strategy,
            'primary_tf': primary_tf,
            'reason': strategy_result.get('reason', '') if strategy_result else '',
            'stop_loss_pct': abs(current_price - stop_loss) / current_price * 100,
            'analysis': {tf: {
                'bi_count': analysis[tf].get('bi_count', 0),
                'zs_count': analysis[tf].get('zs_count', 0),
                'direction': analysis[tf].get('direction', 'unknown'),
                'structure': strategy_result.get('structure', {}).get(tf, {}).get('state', '') if strategy_result else '',
            } for tf in analysis},
        }

    def execute_signal(self, signal: dict) -> bool:
        """执行交易信号"""
        if not signal:
            return False

        direction = signal['direction']
        price = signal['price']
        quantity = signal['quantity']
        stop_loss = signal['stop_loss']

        # 检查是否有反向持仓需要平仓
        if self.position and self.position['direction'] != direction:
            logger.info(f"🔄 平仓反向持仓: {self.position['direction']}")
            self.close_position(price, "方向反转")

        # 开仓
        self.position = {
            'direction': direction,
            'entry_price': price,
            'quantity': quantity,
            'entry_time': datetime.now().isoformat(),
            'stop_loss': stop_loss,
            'signal_type': signal['reason'],
            'signal_analysis': signal.get('analysis', {}),
        }

        emoji = "🟢" if direction == 'long' else "🔴"
        logger.info(f"{emoji} 开仓: {direction.upper()} {self.symbol} @ ${price:.2f} x {quantity}")
        logger.info(f"   止损: ${stop_loss:.2f}")

        self._save_state()
        return True

    def close_position(self, current_price: float, reason: str):
        """平仓"""
        if not self.position:
            return

        pos = self.position
        direction = pos['direction']
        entry_price = pos['entry_price']
        quantity = pos['quantity']

        # 计算盈亏
        if direction == 'long':
            pnl = (current_price - entry_price) * quantity
        else:
            pnl = (entry_price - current_price) * quantity

        pnl_pct = pnl / (entry_price * quantity) * 100

        # 更新统计
        self.capital += pnl
        self.daily_pnl += pnl
        self.trade_history.append({
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': current_price,
            'quantity': quantity,
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
            'reason': reason,
            'entry_time': pos['entry_time'],
            'exit_time': datetime.now().isoformat(),
        })

        emoji = "✅" if pnl > 0 else "❌"
        logger.info(f"{emoji} 平仓: {direction.upper()} {self.symbol}")
        logger.info(f"   入场: ${entry_price:.2f} → 出场: ${current_price:.2f}")
        logger.info(f"   盈亏: ${pnl:.2f} ({pnl_pct:+.2f}%) | 原因: {reason}")

        # 连续亏损检查
        if pnl < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.config['consecutive_loss_limit']:
                self.cooldown_until = datetime.now() + timedelta(minutes=self.config['cooldown_minutes'])
                logger.warning(f"🚫 连亏{self.consecutive_losses}笔，熔断至 {self.cooldown_until.strftime('%H:%M')}")
        else:
            self.consecutive_losses = 0

        # 自动反思
        try:
            trade_data = {
                'symbol': self.symbol,
                'direction': direction,
                'entry_price': entry_price,
                'exit_price': current_price,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'reason': reason,
                'signal_type': pos.get('signal_type', 'unknown'),
            }
            self.rgb_updater.record_trade_reflection(trade_data, analysis=pos.get('signal_analysis', {}))
            logger.info("📝 反思已记录")
        except Exception as e:
            logger.warning(f"反思记录失败: {e}")

        self.position = None
        self._save_state()

    def check_position_risk(self, current_price: float):
        """检查持仓风险"""
        if not self.position:
            return

        pos = self.position
        direction = pos['direction']
        stop_loss = pos['stop_loss']

        # 止损检查
        if direction == 'long' and current_price < stop_loss:
            self.close_position(current_price, f"止损触发 (${stop_loss:.2f})")
            return

        if direction == 'short' and current_price > stop_loss:
            self.close_position(current_price, f"止损触发 (${stop_loss:.2f})")
            return

        # 移动止损（盈利超过2%后）
        if direction == 'long':
            profit_pct = (current_price - pos['entry_price']) / pos['entry_price']
            if profit_pct > 0.02:
                new_stop = current_price * 0.98  # 移动到当前价下方2%
                if new_stop > pos['stop_loss']:
                    pos['stop_loss'] = new_stop
                    logger.info(f"📈 移动止损: ${new_stop:.2f}")
                    self._save_state()

        elif direction == 'short':
            profit_pct = (pos['entry_price'] - current_price) / pos['entry_price']
            if profit_pct > 0.02:
                new_stop = current_price * 1.02  # 移动到当前价上方2%
                if new_stop < pos['stop_loss']:
                    pos['stop_loss'] = new_stop
                    logger.info(f"📉 移动止损: ${new_stop:.2f}")
                    self._save_state()

    def run_once(self):
        """单次扫描"""
        now = datetime.now()
        logger.info("=" * 60)
        logger.info(f"📊 实时扫描 | {now.strftime('%Y-%m-%d %H:%M:%S')} | {self.symbol}")
        logger.info(f"   资金: ${self.capital:,.2f} | 持仓: {'有' if self.position else '无'} | 日盈亏: ${self.daily_pnl:.2f}")

        # 冷却检查
        if self.check_cooldown():
            return

        # 日亏损检查
        if self.check_daily_loss_limit():
            return

        # 获取当前价格
        current_price = None
        try:
            quote = self.data_router.get_quote(self.symbol)
            if quote:
                current_price = quote.price if hasattr(quote, 'price') else None
        except:
            pass

        if not current_price:
            logger.warning("无法获取当前价格")
            return

        logger.info(f"   当前价: ${current_price:.2f}")

        # 持仓风险检查
        self.check_position_risk(current_price)

        # 如果有持仓，检查是否需要平仓
        if self.position:
            pos = self.position
            direction = pos['direction']

            # 多周期分析（检查反转信号）
            analysis = self.analyze_all_timeframes()
            strategy_result = self.determine_trading_direction(analysis)
            new_direction = strategy_result['direction']

            # 方向反转 → 平仓
            if (direction == 'long' and new_direction == 'short') or \
               (direction == 'short' and new_direction == 'long'):
                self.close_position(current_price, f"方向反转: {direction}→{new_direction} | {strategy_result['reason']}")
            else:
                logger.info(f"   持仓方向 {direction} 与市场方向 {new_direction} 一致，继续持有")
                return

        # 无持仓，寻找入场机会
        analysis = self.analyze_all_timeframes()

        # 智能级别确立
        strategy_result = self.determine_trading_direction(analysis)
        direction = strategy_result['direction']
        strategy = strategy_result['strategy']

        logger.info(f"   🧠 结构分析: {strategy_result['reason']}")
        logger.info(f"   📊 策略: {strategy} | 主级别: {strategy_result.get('primary_tf', 'N/A')}")

        # 输出各级别结构状态
        for tf, info in strategy_result.get('structure', {}).items():
            logger.info(f"      {tf}: {info['state']} {info.get('direction', '')} 强度{info.get('strength', 0):.0%} | {info.get('detail', '')}")

        if direction == 'none':
            logger.info(f"   不交易: {strategy_result['reason']}")
            return

        # 配置限制
        if self.config['direction'] != 'auto':
            if self.config['direction'] == 'long' and direction != 'long':
                logger.info(f"   配置限制只做多，当前方向 {direction}，跳过")
                return
            if self.config['direction'] == 'short' and direction != 'short':
                logger.info(f"   配置限制只做空，当前方向 {direction}，跳过")
                return

        if not self.config['enable_short'] and direction == 'short':
            logger.info("   做空未启用，跳过")
            return

        # 检查共振（结构感知）
        is_resonance, level, reason = self.check_resonance(analysis, direction, strategy_result)
        if not is_resonance:
            logger.info(f"   无共振: {reason}")
            return

        logger.info(f"   🔔 共振信号: {reason} (级别{level})")

        # 生成信号（结构感知止损）
        signal = self.generate_signal(analysis, direction, strategy_result)
        if not signal:
            logger.info("   信号生成失败")
            return

        signal['reason'] = f"{reason} | 策略:{strategy} | 止损:{signal['stop_loss_pct']:.1f}%"

        logger.info(f"   📈 信号: {signal['type']} @ ${signal['price']:.2f}")
        logger.info(f"      止损: ${signal['stop_loss']:.2f} ({signal['stop_loss_pct']:.1f}%)")
        logger.info(f"      数量: {signal['quantity']}股")

        # 执行
        self.execute_signal(signal)

    def run_loop(self, interval: int = 300):
        """持续运行"""
        logger.info(f"🚀 启动实时交易模拟")
        logger.info(f"   扫描间隔: {interval}秒")
        logger.info(f"   Ctrl+C 停止")

        while True:
            try:
                self.run_once()
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("⏹️ 用户停止")
                break
            except Exception as e:
                logger.error(f"扫描异常: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)

        # 退出时平仓
        if self.position:
            logger.info("退出时强制平仓...")
            try:
                quote = self.data_router.get_quote(self.symbol)
                price = quote.price if quote and hasattr(quote, 'price') else self.position['entry_price']
                self.close_position(price, "系统退出")
            except:
                pass

        self._print_summary()

    def _print_summary(self):
        """打印总结"""
        total = len(self.trade_history)
        wins = sum(1 for t in self.trade_history if t['pnl'] > 0)
        losses = total - wins

        logger.info("\n" + "=" * 60)
        logger.info("📊 交易模拟总结")
        logger.info("=" * 60)
        logger.info(f"总交易: {total}笔")
        logger.info(f"胜率: {wins/total*100:.1f}%" if total > 0 else "胜率: N/A")
        logger.info(f"总盈亏: ${sum(t['pnl'] for t in self.trade_history):.2f}")
        logger.info(f"最终资金: ${self.capital:,.2f}")
        logger.info("=" * 60)

        # 保存报告
        report = {
            'symbol': self.symbol,
            'config': self.config,
            'total_trades': total,
            'winning_trades': wins,
            'losing_trades': losses,
            'win_rate': round(wins/total*100, 1) if total > 0 else 0,
            'total_pnl': round(sum(t['pnl'] for t in self.trade_history), 2),
            'final_capital': round(self.capital, 2),
            'trades': self.trade_history,
        }

        report_path = REPORTS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.symbol}.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        logger.info(f"报告已保存: {report_path}")


# ==================== CLI ====================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Live Paper Trading Simulation")
    parser.add_argument("--symbol", "-s", default="CRCL", help="品种代码")
    parser.add_argument("--direction", "-d", default="auto", choices=["auto", "long", "short"], help="交易方向")
    parser.add_argument("--interval", "-i", type=int, default=300, help="扫描间隔(秒)")
    parser.add_argument("--once", action="store_true", help="单次扫描")

    args = parser.parse_args()

    config = CONFIG.copy()
    config['symbol'] = args.symbol
    config['direction'] = args.direction
    config['scan_interval'] = args.interval

    trader = LivePaperTrader(config)

    if args.once:
        trader.run_once()
    else:
        trader.run_loop(args.interval)
