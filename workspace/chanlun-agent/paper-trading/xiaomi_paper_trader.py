#!/usr/bin/env python3
"""
小米(01810)实时模拟交易系统 v2.0

核心升级：智能级别确立 v2.0
- 结构状态驱动：趋势锁级别 / 盘整放大 / 转折缩小
- 多级别共振：日线→30分钟→5分钟
- 预交易扫描：开盘前确认今日策略
- 分级进场预案：一买/二买/类二买 + 级别确认
- 结构出场预案：中枢止盈 / 结构止损 / 移动止损
- 流畅度分析：凡强趋必然浅回调

Usage:
    python3 xiaomi_paper_trader.py --monitor      # 启动实时监控
    python3 xiaomi_paper_trader.py --pre-scan      # 盘前扫描（确定今日策略）
    python3 xiaomi_paper_trader.py --status        # 查看状态
    python3 xiaomi_paper_trader.py --report        # 生成报告
"""

import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field, asdict

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / 'xiaomi_trader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Tiger SDK
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import Language, OrderType

# 缠论扩展 v2.0
from czsc import CZSC, Freq, format_standard_kline
from czsc_extension import CzscExtension, StructureState
import pandas as pd

# 密钥配置
TIGER_ID = "20159412"
TIGER_PRIVATE_KEY = """MIICXAIBAAKBgQCQsk07H1czwJy5Gfm9GH2iahHEX3Hhej6y8FW7Hvd9X9jTqxoxFi45aMPFXU7nAx9Ki/gYQlYeXjpCu5RMUHboaz29iBlXmq0gFd6/CdB1LEPbua5V5/kUP53ETbKo0RFjm+fWHxYE6QMpMyW6amP2ASyygSs23aAxYnLZboq5vwIDAQABAoGAXr0/r/w/PlVYyCFn0RXd/J9ybp8Hk1hVARg3KcOGzAIbl8up5IXfUht0Qx9q7/qtXEP09v1IIa4Ue2kSGj18/IhEDla3+EMs24pQ9xnRPgwnzsQkfwNTerGwnxvrM+iHl/IH0AKL0kBPs56JsIIP5VZMd3xNK4xiVTzZIRcRVRECQQDGdrrM6qkomFPw8YRjIO7DuM1IG7ec2PVHX/zYMgCkfYBCsz+DjsopKLjEGms3IqHlSwzB5GLq/z1iHBf8IM/tAkEAuqUn91dmOgSsUJIbuAVN/FtoGcIKe0SYybX3BDsPE6295XR70XMhnrTjx0wIsiANzgC1JZC8PdxB1pxUyx0C2wJBALeao9prxa8OramcZlOm5f0f/JoXOljaxqAPh0UjjUCf8obCeaHl+dT2HWke382UNp6APf8qoPCyzUD0qKPSX0kCQE7WJ/V/wzxKcQZvUKoAA5rOeUA4B/ldVjQNWlM9Jvcm8gkTlKE5wj+pJHUwFpQ2md4jymAdrIVsnZqq2d4ZWPUCQFesxYFPfPv2xnonihe7zqsFAz0pD3E5Ks/F3sdUZk4s/A9Zf1rzxS2XsQtqHgl08L0u340m+YbtTlz/Lyq0mLI=="""
SIM_ACCOUNT = "21409378833585169"

# 风控参数
RISK_PER_TRADE = 0.02  # 单笔2%
MAX_DAILY_LOSS = 0.06  # 日最大6%
MAX_CONSECUTIVE_LOSSES = 3  # 连亏3笔熔断
COOLDOWN_MINUTES = 60  # 熔断冷却时间

# 文件路径
TRADE_LOG = Path(__file__).parent / "xiaomi_trades.json"
PORTFOLIO_FILE = Path(__file__).parent / "xiaomi_portfolio.json"


# ============ 数据结构 ============

@dataclass
class MultiLevelAnalysis:
    """多级别共振分析结果"""
    daily: Dict       # 日线分析
    min30: Dict       # 30分钟分析
    min5: Dict        # 5分钟分析
    resonance: bool   # 是否共振
    resonance_level: int  # 共振级别 0/1/2/3
    direction: str    # long/short/neutral
    strategy: str     # trend_follow/range_wait/reversal_ready
    entry_plan: Dict  # 进场预案
    exit_plan: Dict   # 出场预案
    detail: str


@dataclass
class TradeSignal:
    """交易信号"""
    action: str       # BUY/SELL
    direction: str    # long/short
    signal_type: str  # buy1/buy2/buy3/shock_buy/sell1/sell2/sell3/shock_sell
    price: float
    stop_loss: float
    take_profit: float
    quantity: int
    confidence: float
    resonance_level: int
    entry_plan: Dict
    exit_plan: Dict
    detail: str


class XiaomiPaperTrader:
    """小米模拟交易器 v2.0 — 智能级别确立"""

    def __init__(self):
        self.symbol = "01810"
        self.name = "小米"

        # 初始化Tiger
        self.config = TigerOpenClientConfig(sandbox_debug=False)
        self.config.tiger_id = TIGER_ID
        self.config.private_key = TIGER_PRIVATE_KEY
        self.config.language = Language.zh_CN
        self.config.account = SIM_ACCOUNT

        self.quote_client = QuoteClient(self.config)
        self.trade_client = TradeClient(self.config)

        # 加载持仓和交易记录
        self.portfolio = self._load_portfolio()
        self.trades = self._load_trades()

        logger.info(f"🚀 小米模拟交易器 v2.0 启动 - 账户: {SIM_ACCOUNT}")
        logger.info(f"   当前持仓: {self.portfolio.get('position', 0)} 股")
        logger.info(f"   累计盈亏: ${self.portfolio.get('total_pnl', 0):.2f}")

    def _load_portfolio(self) -> Dict:
        if PORTFOLIO_FILE.exists():
            with open(PORTFOLIO_FILE, 'r') as f:
                return json.load(f)
        return {
            "symbol": self.symbol, "position": 0, "avg_cost": 0,
            "total_pnl": 0, "consecutive_losses": 0, "daily_pnl": 0,
            "last_trade_date": None, "cooldown_until": None,
            "current_strategy": None, "current_level": None
        }

    def _save_portfolio(self):
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(self.portfolio, f, indent=2)

    def _load_trades(self) -> List:
        if TRADE_LOG.exists():
            with open(TRADE_LOG, 'r') as f:
                return json.load(f)
        return []

    def _save_trades(self):
        with open(TRADE_LOG, 'w') as f:
            json.dump(self.trades, f, indent=2)

    def get_account_value(self) -> float:
        try:
            assets = self.trade_client.get_assets()
            if assets and len(assets) > 0:
                a = assets[0]
                seg = a.segments.get('S')
                if seg:
                    return float(seg.net_liquidation)
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
        return 1000000.0

    def _get_realtime_price(self) -> Optional[float]:
        """获取实时价格"""
        try:
            quote = self.quote_client.get_briefs([self.symbol])
            if quote and len(quote) > 0:
                return float(quote[0].latest_price)
        except Exception as e:
            logger.error(f"获取实时价格失败: {e}")
        return None

    # ============ 核心：多级别分析 ============

    def _fetch_bars(self, period: str, days: int = 60) -> Optional[pd.DataFrame]:
        """获取K线数据"""
        try:
            end_time = datetime.now()
            begin_time = end_time - timedelta(days=days)
            df = self.quote_client.get_bars(
                [self.symbol], period=period,
                begin_time=begin_time.strftime('%Y-%m-%d'),
                end_time=end_time.strftime('%Y-%m-%d')
            )
            if df is None or df.empty:
                return None
            return df
        except Exception as e:
            logger.error(f"获取{period}数据失败: {e}")
            return None

    def _analyze_level(self, df: pd.DataFrame, freq, timeframe: str) -> Optional[Dict]:
        """单级别缠论分析"""
        try:
            df = df.copy()
            df['dt'] = df['time'].apply(lambda x: datetime.fromtimestamp(x / 1000))
            df['symbol'] = self.symbol
            df['vol'] = df['volume']
            df['amount'] = df.get('amount', df['vol'] * df['close'])

            bars = format_standard_kline(df, freq=freq)
            ka = CZSC(bars)
            ext = CzscExtension(ka, symbol=self.symbol, timeframe=timeframe)

            result = ext.full_analysis()
            return result
        except Exception as e:
            logger.error(f"{timeframe}分析失败: {e}")
            return None

    def multi_level_analysis(self) -> Optional[MultiLevelAnalysis]:
        """
        多级别共振分析 — 核心方法

        逻辑：
        1. 日线确定方向和结构状态 → 策略类型
        2. 30分钟确认结构 → 买卖点
        3. 5分钟精确入场 → 触发信号
        4. 共振判断 → 进出场预案
        """
        # 获取数据（日线需要更长历史以获得足够笔和中枢）
        df_daily = self._fetch_bars('day', days=180)
        df_30m = self._fetch_bars('30min', days=15)
        df_5m = self._fetch_bars('5min', days=5)

        if df_daily is None:
            logger.warning("日线数据不足")
            return None

        # 分析各级别
        daily = self._analyze_level(df_daily, Freq.D, 'daily')
        min30 = self._analyze_level(df_30m, Freq.F30, '30min') if df_30m is not None else None
        min5 = self._analyze_level(df_5m, Freq.F5, '5min') if df_5m is not None else None

        if not daily:
            return None

        # ---- 共振判断 ----
        resonance, resonance_level, direction = self._check_resonance(daily, min30, min5)

        # ---- 策略确定（基于日线结构状态） ----
        strategy = self._determine_strategy(daily)

        # ---- 进出场预案 ----
        entry_plan = self._build_entry_plan(daily, min30, min5, strategy, direction)
        exit_plan = self._build_exit_plan(daily, min30, direction)

        detail_parts = [
            f"日线:{daily['structure_state']}({daily['trend_direction'] or '-'})",
            f"30m:{min30['structure_state'] if min30 else 'N/A'}",
            f"5m:{min5['structure_state'] if min5 else 'N/A'}",
            f"共振:{resonance_level}级",
            f"策略:{strategy}",
            f"方向:{direction}"
        ]

        return MultiLevelAnalysis(
            daily=daily,
            min30=min30 or {},
            min5=min5 or {},
            resonance=resonance,
            resonance_level=resonance_level,
            direction=direction,
            strategy=strategy,
            entry_plan=entry_plan,
            exit_plan=exit_plan,
            detail=' | '.join(detail_parts)
        )

    def _check_resonance(self, daily: Dict, min30: Optional[Dict], min5: Optional[Dict]) -> tuple:
        """
        多级别共振检查

        共振级别：
        - 3级：日线+30分钟+5分钟 同方向 → 强信号
        - 2级：日线+30分钟 同方向 → 中等信号
        - 1级：仅日线方向明确 → 弱信号
        - 0级：无共振 → 不交易
        """
        daily_dir = daily.get('trend_direction')
        if not daily_dir:
            return False, 0, 'neutral'

        level = 1  # 日线有方向 = 1级
        direction = 'long' if daily_dir == 'up' else 'short'

        if min30:
            min30_dir = min30.get('trend_direction')
            if min30_dir == daily_dir:
                level = 2

                if min5:
                    min5_dir = min5.get('trend_direction')
                    if min5_dir == daily_dir:
                        level = 3

        resonance = level >= 2
        return resonance, level, direction

    def _determine_strategy(self, daily: Dict) -> str:
        """
        确定交易策略（基于智能级别 v2.0 + 顺势原则）

        核心：先判趋势方向，再找顺势机会
        - trending down → trend_follow_short（顺势做空）
        - trending up → trend_follow_long（顺势做多）
        - ranging → range_wait（盘整等待）
        - turning → reversal_ready（转折准备）
        """
        state = daily.get('structure_state', 'unknown')
        trend_dir = daily.get('trend_direction')

        if state == 'trending':
            if trend_dir == 'down':
                return 'trend_follow_short'  # 下降趋势→顺势做空
            elif trend_dir == 'up':
                return 'trend_follow_long'   # 上升趋势→顺势做多
        elif state == 'ranging' or daily.get('should_wait_breakout'):
            return 'range_wait'
        elif state == 'turning' and daily.get('should_catch_reversal'):
            return 'reversal_ready'
        elif state == 'turning':
            return 'reversal_observe'

        return 'unknown'

    def _build_entry_plan(self, daily: Dict, min30: Optional[Dict],
                          min5: Optional[Dict], strategy: str, direction: str) -> Dict:
        """
        构建进场预案（顺势原则）

        核心逻辑：
        - 下跌趋势 → 找卖点做空（反弹到中枢上沿+顶背驰）
        - 上升趋势 → 找买点做多（回调到中枢下沿+底背驰）
        - 盘整 → 不交易
        """
        plan = {
            'strategy': strategy,
            'direction': direction,
            'conditions': [],
            'trigger_price': None,
            'position_pct': 0,
            'note': ''
        }

        if strategy == 'range_wait':
            plan['note'] = '盘整中，不交易'
            return plan

        # ---- 顺势做空（下跌趋势） ----
        if strategy == 'trend_follow_short':
            # 找30分钟卖点（反弹到中枢上沿+顶背驰）
            if min30:
                bsp = min30.get('buy_sell_points', [])
                sell_points = [b for b in bsp if 'sell' in b.get('type', '')]
                if sell_points:
                    best = max(sell_points, key=lambda x: x.get('confidence', 0))
                    plan['trigger_price'] = best.get('price')
                    plan['conditions'].append(f"30m卖点: {best['type']} @ {best['price']:.2f}")
                    plan['position_pct'] = 0.3
                    plan['note'] = f"顺势做空: 30分钟{best['type']}确认"
                else:
                    plan['note'] = '下跌趋势中，等待30分钟卖点'
                    plan['position_pct'] = 0.2  # 默认仓位，日线卖点可触发
            else:
                plan['note'] = '下跌趋势中，无30分钟数据'
                plan['position_pct'] = 0.2

            plan['conditions'].append(f"日线结构: {daily['structure_state']}")
            plan['conditions'].append(f"趋势方向: {daily.get('trend_direction')}")
            plan['conditions'].append(f"趋势强度: {daily.get('trend_strength', 0):.0%}")

        # ---- 顺势做多（上升趋势） ----
        elif strategy == 'trend_follow_long':
            if min30:
                bsp = min30.get('buy_sell_points', [])
                buy_points = [b for b in bsp if 'buy' in b.get('type', '')]
                if buy_points:
                    best = max(buy_points, key=lambda x: x.get('confidence', 0))
                    plan['trigger_price'] = best.get('price')
                    plan['conditions'].append(f"30m买点: {best['type']} @ {best['price']:.2f}")
                    plan['position_pct'] = 0.3
                    plan['note'] = f"顺势做多: 30分钟{best['type']}确认"

            plan['conditions'].append(f"日线结构: {daily['structure_state']}")
            plan['conditions'].append(f"趋势方向: {daily.get('trend_direction')}")

        # ---- 转折准备 ----
        elif strategy in ('reversal_ready', 'reversal_observe'):
            # 转折：需要确认反转信号
            plan['conditions'].append(f"日线背驰: {daily.get('divergence', {})}")
            plan['note'] = '转折观察中，等待确认信号'
            plan['position_pct'] = 0

        return plan

    def _build_exit_plan(self, daily: Dict, min30: Optional[Dict], direction: str) -> Dict:
        """
        构建出场预案（逻辑驱动止损止盈）

        核心原则（VAN教导）：
        - 止损 = 入场逻辑已破坏的止损
        - 止盈 = 持仓逻辑破坏的止损
        - 移动止损 = 结构演变的止损

        三层止损：
        1. 入场止损：价格突破入场逻辑破坏点
        2. 结构止损：小级别出现反向信号
        3. 移动止损：盈利后保护利润
        """
        plan = {
            'stop_loss': None,        # 入场逻辑破坏点
            'take_profit': None,      # 持仓逻辑破坏点
            'trailing_stop': None,    # 移动止损
            'structural_stop': None,  # 结构止损
            'exit_conditions': [],
            'note': ''
        }

        last_zs = daily.get('last_zs')
        if not last_zs:
            plan['note'] = '无中枢数据'
            return plan

        zs_zg = last_zs.get('zg', 0)
        zs_zd = last_zs.get('zd', 0)

        if direction == 'long':
            # ---- 做多出场 ----
            # 入场止损 = 买点被否定（价格跌破中枢下沿）
            # 逻辑：中枢下沿被跌破 → 日线上升趋势可能终结 → 必须止损
            plan['stop_loss'] = {
                'price': zs_zd * 0.995,  # 逻辑位-0.5%缓冲
                'logic_price': zs_zd,    # 逻辑位（中枢下沿）
                'type': 'entry_invalidation',
                'reason': f'uptrend可能终结: 价格跌破中枢下沿{zs_zd:.2f}'
            }
            # 持仓止盈 = 上升趋势结束（价格回到中枢上沿）
            plan['take_profit'] = {
                'price': zs_zg,
                'type': 'holding_invalidation',
                'reason': f'上升趋势结束: 价格回到{zs_zg:.2f}'
            }
            # 移动止损 = 盈利2%后止损移到入场价
            plan['trailing_stop'] = {
                'trigger_pct': 0.02,
                'action': 'move_to_entry',
                'reason': '盈利2%后保护利润'
            }
            # 结构止损 = 30分钟出现卖点
            plan['structural_stop'] = {
                'condition': '30min_sell_signal',
                'reason': '小级别结构破坏'
            }
            plan['exit_conditions'] = [
                f"入场止损: 价格跌破 {zs_zd:.2f} (买点被否定)",
                f"持仓止盈: 价格回到 {zs_zg:.2f} (上升趋势结束)",
                "移动止损: 盈利2%后止损移到入场价",
                "结构止损: 30分钟出现卖点"
            ]

        else:
            # ---- 做空出场 ----
            # 入场止损 = 卖点被否定（价格突破中枢上沿）
            # 逻辑：中枢上沿被突破 → 日线下跌趋势可能终结 → 必须止损
            # 实盘需要小缓冲（0.5%），但逻辑位是中枢上沿
            plan['stop_loss'] = {
                'price': zs_zg * 1.005,  # 逻辑位+0.5%缓冲
                'logic_price': zs_zg,    # 逻辑位（中枢上沿）
                'type': 'entry_invalidation',
                'reason': f'downtrend可能终结: 价格突破中枢上沿{zs_zg:.2f}'
            }
            # 持仓止盈 = 下跌趋势结束（价格回到中枢下沿）
            plan['take_profit'] = {
                'price': zs_zd,
                'type': 'holding_invalidation',
                'reason': f'下跌趋势结束: 价格回到{zs_zd:.2f}'
            }
            # 移动止损 = 盈利2%后止损移到入场价
            plan['trailing_stop'] = {
                'trigger_pct': 0.02,
                'action': 'move_to_entry',
                'reason': '盈利2%后保护利润'
            }
            # 结构止损 = 30分钟出现买点
            plan['structural_stop'] = {
                'condition': '30min_buy_signal',
                'reason': '小级别结构破坏'
            }
            plan['exit_conditions'] = [
                f"入场止损: 价格突破 {zs_zg:.2f} (shock_sell被否定)",
                f"持仓止盈: 价格回到 {zs_zd:.2f} (下跌趋势结束)",
                "移动止损: 盈利2%后止损移到入场价",
                "结构止损: 30分钟出现买点"
            ]

        return plan

    def _check_position_exit(self, analysis: MultiLevelAnalysis) -> Optional[Dict]:
        """
        检查持仓是否需要平仓

        三层检查：
        1. 入场止损：价格突破入场逻辑破坏点
        2. 持仓止盈：价格回到持仓逻辑破坏点
        3. 结构止损：小级别出现反向信号
        """
        if self.portfolio['position'] == 0:
            return None

        current_price = analysis.daily.get('last_bi', {}).get('high', 0) or 30.0
        entry_price = self.portfolio.get('avg_cost', 0)
        direction = self.portfolio.get('current_direction', 'short')
        exit_plan = analysis.exit_plan

        if not exit_plan:
            return None

        # ---- 1. 入场止损检查 ----
        stop_loss = exit_plan.get('stop_loss', {})
        if stop_loss and stop_loss.get('price'):
            sl_price = stop_loss['price']
            if direction == 'short' and current_price >= sl_price:
                return {
                    'reason': '入场止损',
                    'detail': stop_loss.get('reason', ''),
                    'price': current_price,
                    'stop_price': sl_price
                }
            elif direction == 'long' and current_price <= sl_price:
                return {
                    'reason': '入场止损',
                    'detail': stop_loss.get('reason', ''),
                    'price': current_price,
                    'stop_price': sl_price
                }

        # ---- 2. 持仓止盈检查 ----
        take_profit = exit_plan.get('take_profit', {})
        if take_profit and take_profit.get('price'):
            tp_price = take_profit['price']
            if direction == 'short' and current_price <= tp_price:
                return {
                    'reason': '持仓止盈',
                    'detail': take_profit.get('reason', ''),
                    'price': current_price,
                    'stop_price': tp_price
                }
            elif direction == 'long' and current_price >= tp_price:
                return {
                    'reason': '持仓止盈',
                    'detail': take_profit.get('reason', ''),
                    'price': current_price,
                    'stop_price': tp_price
                }

        # ---- 3. 结构止损检查（30分钟反向信号） ----
        structural_stop = exit_plan.get('structural_stop', {})
        if structural_stop and analysis.min30:
            min30_bsp = analysis.min30.get('buy_sell_points', [])
            condition = structural_stop.get('condition', '')

            if condition == '30min_buy_signal':
                # 做空持仓，30分钟出现买点 → 结构破坏
                buy_signals = [b for b in min30_bsp if 'buy' in b.get('type', '')]
                if buy_signals:
                    best = max(buy_signals, key=lambda x: x.get('confidence', 0))
                    return {
                        'reason': '结构止损',
                        'detail': f"30分钟买点: {best['type']} @ {best['price']:.2f}",
                        'price': current_price,
                        'stop_price': best['price']
                    }
            elif condition == '30min_sell_signal':
                # 做多持仓，30分钟出现卖点 → 结构破坏
                sell_signals = [b for b in min30_bsp if 'sell' in b.get('type', '')]
                if sell_signals:
                    best = max(sell_signals, key=lambda x: x.get('confidence', 0))
                    return {
                        'reason': '结构止损',
                        'detail': f"30分钟卖点: {best['type']} @ {best['price']:.2f}",
                        'price': current_price,
                        'stop_price': best['price']
                    }

        # ---- 4. 移动止损检查 ----
        trailing = exit_plan.get('trailing_stop', {})
        if trailing and entry_price > 0:
            trigger_pct = trailing.get('trigger_pct', 0.02)
            if direction == 'short':
                profit_pct = (entry_price - current_price) / entry_price
                if profit_pct >= trigger_pct:
                    # 盈利达标，移动止损到入场价
                    if current_price >= entry_price:
                        return {
                            'reason': '移动止损',
                            'detail': f"盈利{profit_pct:.1%}后价格回到入场价",
                            'price': current_price,
                            'stop_price': entry_price
                        }
            elif direction == 'long':
                profit_pct = (current_price - entry_price) / entry_price
                if profit_pct >= trigger_pct:
                    if current_price <= entry_price:
                        return {
                            'reason': '移动止损',
                            'detail': f"盈利{profit_pct:.1%}后价格回到入场价",
                            'price': current_price,
                            'stop_price': entry_price
                        }

        return None

    # ============ 预交易扫描 ============

    def pre_scan(self) -> Optional[TradeSignal]:
        """
        盘前扫描 — 确定今日策略

        输出：
        1. 今日策略（趋势跟随/盘整等待/转折准备）
        2. 共振级别
        3. 进出场预案
        4. 是否有交易信号
        """
        logger.info("=" * 60)
        logger.info("📋 盘前扫描 — 智能级别 v2.0")
        logger.info("=" * 60)

        analysis = self.multi_level_analysis()
        if not analysis:
            logger.warning("分析失败")
            return None

        # 输出分析结果（趋势方向先行）
        trend_dir = analysis.daily.get('trend_direction', '?')
        trend_label = '⬇️下跌趋势' if trend_dir == 'down' else '⬆️上升趋势' if trend_dir == 'up' else '➡️盘整'

        logger.info(f"\n📊 日线大趋势: {trend_label}")
        logger.info(f"   结构状态: {analysis.daily.get('structure_state', 'N/A')}")
        logger.info(f"   趋势强度: {analysis.daily.get('trend_strength', 0):.0%}")
        logger.info(f"   中枢运动: {analysis.daily.get('zs_movement', 'N/A')}")

        logger.info(f"\n📊 多级别共振:")
        logger.info(f"   30分钟: {analysis.min30.get('structure_state', 'N/A')}")
        logger.info(f"   5分钟: {analysis.min5.get('structure_state', 'N/A')}")
        logger.info(f"   共振级别: {analysis.resonance_level}级")
        logger.info(f"   顺势方向: {analysis.direction}")
        logger.info(f"   策略: {analysis.strategy}")

        # 流畅度
        fluency = analysis.daily.get('trend_fluency', {})
        if fluency:
            logger.info(f"\n📈 趋势流畅度:")
            logger.info(f"   流畅度: {fluency.get('fluency', 0):.0%}")
            logger.info(f"   流畅: {'✅' if fluency.get('is_smooth') else '❌'}")
            logger.info(f"   详情: {fluency.get('detail', '')}")

        # 买卖点
        logger.info(f"\n🎯 买卖点:")
        daily_bsp = analysis.daily.get('buy_sell_points', [])
        if daily_bsp:
            for b in daily_bsp:
                logger.info(f"   日线: {b['type']} @ {b['price']:.2f} 置信度{b['confidence']:.0%}")
        else:
            logger.info("   日线: 无买卖点")

        if analysis.min30:
            min30_bsp = analysis.min30.get('buy_sell_points', [])
            if min30_bsp:
                for b in min30_bsp:
                    logger.info(f"   30分钟: {b['type']} @ {b['price']:.2f} 置信度{b['confidence']:.0%}")

        # 进出场预案
        logger.info(f"\n📋 进场预案:")
        ep = analysis.entry_plan
        logger.info(f"   策略: {ep.get('strategy')}")
        logger.info(f"   方向: {ep.get('direction')}")
        logger.info(f"   仓位: {ep.get('position_pct', 0):.0%}")
        for c in ep.get('conditions', []):
            logger.info(f"   条件: {c}")
        logger.info(f"   说明: {ep.get('note', '')}")

        logger.info(f"\n📋 出场预案:")
        xp = analysis.exit_plan
        sl = xp.get('stop_loss', {})
        tp = xp.get('take_profit', {})
        if sl and isinstance(sl, dict):
            logger.info(f"   入场止损: {sl.get('price', 0):.2f} ({sl.get('reason', '')})")
        if tp and isinstance(tp, dict):
            logger.info(f"   持仓止盈: {tp.get('price', 0):.2f} ({tp.get('reason', '')})")
        for c in xp.get('exit_conditions', []):
            logger.info(f"   {c}")

        # 生成信号
        signal = self._generate_signal(analysis)
        if signal:
            logger.info(f"\n🎯 交易信号:")
            logger.info(f"   动作: {signal.action}")
            logger.info(f"   类型: {signal.signal_type}")
            logger.info(f"   价格: {signal.price:.2f}")
            logger.info(f"   止损: {signal.stop_loss:.2f}")
            logger.info(f"   止盈: {signal.take_profit:.2f}")
            logger.info(f"   数量: {signal.quantity}")
            logger.info(f"   置信度: {signal.confidence:.0%}")
        else:
            logger.info(f"\n⏳ 无交易信号")

        # 保存策略到portfolio
        self.portfolio['current_strategy'] = analysis.strategy
        self.portfolio['current_level'] = analysis.resonance_level
        self._save_portfolio()

        return signal

    def _generate_signal(self, analysis: MultiLevelAnalysis) -> Optional[TradeSignal]:
        """
        根据多级别分析生成交易信号（顺势原则）

        核心逻辑：
        - 下跌趋势 → 找卖点做空
        - 上升趋势 → 找买点做多
        - 盘整/转折 → 不交易
        """
        # 不满足共振条件
        if analysis.resonance_level < 2:
            return None

        # 盘整不交易
        if analysis.strategy == 'range_wait':
            return None

        direction = analysis.direction  # 'long' or 'short'
        strategy = analysis.strategy

        daily_bsp = analysis.daily.get('buy_sell_points', [])
        min30_bsp = analysis.min30.get('buy_sell_points', []) if analysis.min30 else []

        best_point = None
        source = ''
        action = ''

        # ---- 下跌趋势：找卖点做空 ----
        if direction == 'short' and strategy == 'trend_follow_short':
            # 先找30分钟卖点（实时信号）
            sell_points_30 = [b for b in min30_bsp if 'sell' in b.get('type', '')]
            if sell_points_30:
                best_point = max(sell_points_30, key=lambda x: x.get('confidence', 0))
                source = '30min'

            # 日线卖点只作为参考，不直接触发入场
            # 历史信号已经走完的不能用

            action = 'SELL'  # 做空 = SELL

        # ---- 上升趋势：找买点做多 ----
        elif direction == 'long' and strategy == 'trend_follow_long':
            # 先找30分钟买点（实时信号）
            buy_points_30 = [b for b in min30_bsp if 'buy' in b.get('type', '')]
            if buy_points_30:
                best_point = max(buy_points_30, key=lambda x: x.get('confidence', 0))
                source = '30min'

            # 日线买点只作为参考，不直接触发入场

            action = 'BUY'

        if not best_point:
            return None

        # 仓位计算 — 使用实时价格，不是历史信号价格
        account_value = self.get_account_value()
        entry_pct = analysis.entry_plan.get('position_pct', 0.2)
        # 获取实时价格
        current_price = self._get_realtime_price()
        if not current_price:
            current_price = analysis.daily.get('last_bi', {}).get('high', 0) or 30.0
        position_value = account_value * entry_pct
        quantity = int(position_value / current_price / 100) * 100  # 港股100股一手

        if quantity <= 0:
            return None

        # 出场参数 — 止损止盈基于实时价格计算
        exit_plan = analysis.exit_plan
        sl = exit_plan.get('stop_loss', {})
        tp = exit_plan.get('take_profit', {})
        stop_loss = sl.get('price', current_price * 0.97) if isinstance(sl, dict) else current_price * 0.97
        take_profit = tp.get('price', current_price * 1.05) if isinstance(tp, dict) else current_price * 1.05

        return TradeSignal(
            action=action,
            direction=direction,
            signal_type=best_point['type'],
            price=current_price,  # 实时价格入场，不是历史信号价格
            stop_loss=stop_loss,
            take_profit=take_profit,
            quantity=quantity,
            confidence=best_point.get('confidence', 0.6),
            resonance_level=analysis.resonance_level,
            entry_plan=analysis.entry_plan,
            exit_plan=analysis.exit_plan,
            detail=f"{source} {best_point['type']} | 共振{analysis.resonance_level}级 | {strategy} | {direction}"
        )

    # ============ 实时监控 ============

    def check_risk_limits(self) -> bool:
        """检查风控限制"""
        now = datetime.now()

        if self.portfolio.get('cooldown_until'):
            cooldown = datetime.fromisoformat(self.portfolio['cooldown_until'])
            if now < cooldown:
                logger.info(f"⏸️ 熔断中，冷却至 {cooldown.strftime('%H:%M')}")
                return False
            else:
                self.portfolio['cooldown_until'] = None
                self.portfolio['consecutive_losses'] = 0
                logger.info("✅ 熔断解除")

        if self.portfolio['daily_pnl'] < -self.get_account_value() * MAX_DAILY_LOSS:
            logger.warning(f"🚫 日亏损超限: ${self.portfolio['daily_pnl']:.2f}")
            return False

        if self.portfolio['consecutive_losses'] >= MAX_CONSECUTIVE_LOSSES:
            cooldown_time = now.timestamp() + COOLDOWN_MINUTES * 60
            self.portfolio['cooldown_until'] = datetime.fromtimestamp(cooldown_time).isoformat()
            logger.warning(f"🚫 连亏{MAX_CONSECUTIVE_LOSSES}笔，熔断{COOLDOWN_MINUTES}分钟")
            self._save_portfolio()
            return False

        return True

    def execute_trade(self, signal: TradeSignal) -> bool:
        """执行交易"""
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"💰 执行交易: {signal.action} {signal.direction}")
            logger.info(f"   类型: {signal.signal_type}")
            logger.info(f"   价格: ${signal.price:.2f}")
            logger.info(f"   数量: {signal.quantity}")
            logger.info(f"   止损: ${signal.stop_loss:.2f}")
            logger.info(f"   止盈: ${signal.take_profit:.2f}")
            logger.info(f"   共振: {signal.resonance_level}级")
            logger.info(f"{'='*50}")

            # 模拟执行（不实际下单）
            trade = {
                'time': datetime.now().isoformat(),
                'action': signal.action,
                'direction': signal.direction,
                'type': signal.signal_type,
                'price': signal.price,
                'quantity': signal.quantity,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'resonance_level': signal.resonance_level,
                'confidence': signal.confidence,
                'detail': signal.detail
            }
            self.trades.append(trade)
            self._save_trades()

            if signal.action == 'BUY':
                self.portfolio['position'] = signal.quantity
                self.portfolio['avg_cost'] = signal.price
                self.portfolio['current_strategy'] = signal.entry_plan.get('strategy')
                self.portfolio['current_direction'] = 'long'
                self.portfolio['entry_time'] = datetime.now().isoformat()
            elif signal.action == 'SELL':
                self.portfolio['position'] = signal.quantity
                self.portfolio['avg_cost'] = signal.price
                self.portfolio['current_strategy'] = signal.entry_plan.get('strategy')
                self.portfolio['current_direction'] = 'short'
                self.portfolio['entry_time'] = datetime.now().isoformat()

            self._save_portfolio()
            logger.info("✅ 交易执行完成（模拟）")
            return True

        except Exception as e:
            logger.error(f"交易执行失败: {e}")
            return False

    def execute_exit(self, exit_info: Dict) -> bool:
        """执行平仓"""
        try:
            position = self.portfolio.get('position', 0)
            entry_price = self.portfolio.get('avg_cost', 0)
            exit_price = exit_info.get('price', 0)
            direction = self.portfolio.get('current_direction', 'short')

            # 计算盈亏
            if direction == 'short':
                pnl = (entry_price - exit_price) * position
            else:
                pnl = (exit_price - entry_price) * position

            logger.info(f"\n{'='*50}")
            logger.info(f"🔔 平仓信号: {exit_info['reason']}")
            logger.info(f"   详情: {exit_info.get('detail', '')}")
            logger.info(f"   方向: {direction}")
            logger.info(f"   入场价: ${entry_price:.2f}")
            logger.info(f"   平仓价: ${exit_price:.2f}")
            logger.info(f"   数量: {position}")
            logger.info(f"   盈亏: ${pnl:.2f}")
            logger.info(f"{'='*50}")

            # 更新portfolio
            self.portfolio['total_pnl'] += pnl
            self.portfolio['daily_pnl'] += pnl
            self.portfolio['position'] = 0
            self.portfolio['avg_cost'] = 0
            self.portfolio['current_direction'] = None

            # 连亏统计
            if pnl < 0:
                self.portfolio['consecutive_losses'] += 1
            else:
                self.portfolio['consecutive_losses'] = 0

            # 记录交易
            trade = {
                'time': datetime.now().isoformat(),
                'action': 'EXIT',
                'direction': direction,
                'reason': exit_info['reason'],
                'detail': exit_info.get('detail', ''),
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': position,
                'pnl': pnl
            }
            self.trades.append(trade)
            self._save_trades()
            self._save_portfolio()

            logger.info("✅ 平仓完成（模拟）")
            return True

        except Exception as e:
            logger.error(f"平仓执行失败: {e}")
            return False

    def run_monitor(self):
        """实时监控循环 — v2.0 多级别共振（顺势原则）"""
        logger.info("=" * 60)
        logger.info("🚀 小米实时模拟交易系统 v2.1 启动")
        logger.info("   核心原则: 大级别定方向，小级别找机会")
        logger.info("   智能级别确立: ✅")
        logger.info("   多级别共振: 日线→30分钟→5分钟")
        logger.info("   顺势交易: 下跌做空 / 上升做多")
        logger.info("=" * 60)

        # 首次预扫描
        self.pre_scan()

        while True:
            try:
                if not self.check_risk_limits():
                    time.sleep(60)
                    continue

                # 多级别分析
                analysis = self.multi_level_analysis()
                if not analysis:
                    time.sleep(60)
                    continue

                current_price = self._get_realtime_price() or analysis.daily.get('last_bi', {}).get('high', 0) or 30.0
                strategy = analysis.strategy

                # 获取具体参数
                last_zs_d = analysis.daily.get('last_zs', {})
                last_bi_d = analysis.daily.get('last_bi', {})
                div_d = analysis.daily.get('divergence', {})
                fluency = analysis.daily.get('trend_fluency', {})
                strength = analysis.daily.get('trend_strength', 0)

                # 中枢和背驰参数
                zs_zg = last_zs_d.get('zg', 0)
                zs_zd = last_zs_d.get('zd', 0)
                bi_dir = last_bi_d.get('direction', '?')
                bi_high = last_bi_d.get('high', 0)
                bi_low = last_bi_d.get('low', 0)
                div_type = div_d.get('type', '无')
                div_conf = div_d.get('confidence', 0)
                flu_val = fluency.get('fluency', 0)

                # 30分钟参数
                m30_state = analysis.min30.get('structure_state', 'N/A') if analysis.min30 else 'N/A'
                m30_zs = analysis.min30.get('last_zs', {}) if analysis.min30 else {}
                m30_zg = m30_zs.get('zg', 0)
                m30_zd = m30_zs.get('zd', 0)

                # 5分钟参数
                m5_state = analysis.min5.get('structure_state', 'N/A') if analysis.min5 else 'N/A'

                # 详细日志（趋势方向先行）
                trend_dir = analysis.daily.get('trend_direction', '?')
                trend_label = '⬇️下跌趋势' if trend_dir == 'down' else '⬆️上升趋势' if trend_dir == 'up' else '➡️盘整'
                strategy = analysis.strategy

                logger.info(
                    f"⏳ {datetime.now().strftime('%H:%M')} "
                    f"价格:${current_price:.2f}\n"
                    f"   🔴 日线大趋势: {trend_label} "
                    f"结构:{analysis.daily.get('structure_state')} "
                    f"中枢[{zs_zd:.2f},{zs_zg:.2f}] "
                    f"强度{strength:.0%}\n"
                    f"   📊 趋势分析: 背驰:{div_type}({div_conf:.0%}) "
                    f"流畅{flu_val:.0%} "
                    f"笔{bi_dir} H:{bi_high:.2f} L:{bi_low:.2f}\n"
                    f"   🎯 策略:{strategy} "
                    f"方向:{analysis.direction} "
                    f"共振:{analysis.resonance_level}级\n"
                    f"   📈 30m: {m30_state} 中枢[{m30_zd:.2f},{m30_zg:.2f}] "
                    f"5m: {m5_state}"
                )

                # ---- 持仓检查：止损止盈 ----
                if self.portfolio['position'] > 0:
                    exit_info = self._check_position_exit(analysis)
                    if exit_info:
                        logger.info(f"\n🔔 触发平仓: {exit_info['reason']}")
                        self.execute_exit(exit_info)
                    else:
                        entry_price = self.portfolio.get('avg_cost', 0)
                        direction = self.portfolio.get('current_direction', 'short')
                        if direction == 'short':
                            pnl_pct = (entry_price - current_price) / entry_price * 100
                        else:
                            pnl_pct = (current_price - entry_price) / entry_price * 100
                        logger.info(f"   💰 持仓中: {direction} @ ${entry_price:.2f} → ${current_price:.2f} ({pnl_pct:+.1f}%)")

                # ---- 新信号检查 ----
                else:
                    signal = self._generate_signal(analysis)
                    if signal:
                        logger.info(f"\n🎯 发现交易信号! {signal.detail}")
                        self.execute_trade(signal)

                time.sleep(300)  # 5分钟扫描

            except KeyboardInterrupt:
                logger.info("\n👋 监控已停止")
                break
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                time.sleep(60)

    # ============ 状态和报告 ============

    def show_status(self):
        """显示当前状态"""
        print("=" * 60)
        print(f"📊 小米 {self.symbol} 交易状态 v2.0")
        print("=" * 60)
        print(f"持仓: {self.portfolio.get('position', 0)} 股")
        print(f"成本: ${self.portfolio.get('avg_cost', 0):.2f}")
        print(f"累计盈亏: ${self.portfolio.get('total_pnl', 0):.2f}")
        print(f"日盈亏: ${self.portfolio.get('daily_pnl', 0):.2f}")
        print(f"连亏: {self.portfolio.get('consecutive_losses', 0)} 笔")
        print(f"当前策略: {self.portfolio.get('current_strategy', 'N/A')}")
        print(f"共振级别: {self.portfolio.get('current_level', 'N/A')}")
        print(f"交易记录: {len(self.trades)} 笔")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='小米模拟交易系统 v2.0')
    parser.add_argument('--monitor', action='store_true', help='启动实时监控')
    parser.add_argument('--pre-scan', action='store_true', help='盘前扫描')
    parser.add_argument('--status', action='store_true', help='查看状态')
    parser.add_argument('--report', action='store_true', help='生成报告')
    args = parser.parse_args()

    trader = XiaomiPaperTrader()

    if args.pre_scan:
        trader.pre_scan()
    elif args.status:
        trader.show_status()
    elif args.report:
        trader.show_status()
    elif args.monitor:
        trader.run_monitor()
    else:
        trader.pre_scan()
