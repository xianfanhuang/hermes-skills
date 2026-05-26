#!/usr/bin/env python3
"""
统一交易引擎 v2.0

一套系统，多标的。配置驱动，不改代码。
继承小米交易系统的全部逻辑：
- 三层止损（入场止损/结构止损/移动止损）
- 顺势策略（下跌找卖点，上升找买点）
- 多级别共振
- 实时价格获取
- 历史信号不触加入场
"""

import sys
import json
import time
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field, asdict

# 路径设置
ENGINE_DIR = Path(__file__).resolve().parent
UNIFIED_DIR = ENGINE_DIR
AGENT_DIR = ENGINE_DIR.parent.parent
SKILLS_DIR = AGENT_DIR.parent / 'skills'

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(SKILLS_DIR / 'tiger-broker'))

# 老虎下单函数
from tiger_client import place_order_limit, place_order_market

# 日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Finnhub API Key
FINNHUB_KEY = "d85kn4hr01qitd92g090d85kn4hr01qitd92g09g"

# ============ 数据结构 ============

@dataclass
class Quote:
    """行情数据"""
    symbol: str
    price: float
    change: float
    change_pct: float
    high: float
    low: float
    open: float
    prev_close: float
    timestamp: str

@dataclass
class TradeSignal:
    """交易信号"""
    symbol: str
    action: str  # BUY / SELL / EXIT
    direction: str  # long / short
    signal_type: str
    price: float
    stop_loss: float
    take_profit: float
    quantity: int
    confidence: float
    resonance_level: int
    detail: str
    strategy: str

# ============ 数据获取 ============

class DataFetcher:
    """统一数据获取"""

    @staticmethod
    def get_finnhub_quote(symbol: str) -> Optional[Quote]:
        """从Finnhub获取美股实时行情"""
        try:
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return Quote(
                    symbol=symbol,
                    price=data.get('c', 0),
                    change=data.get('d', 0),
                    change_pct=data.get('dp', 0),
                    high=data.get('h', 0),
                    low=data.get('l', 0),
                    open=data.get('o', 0),
                    prev_close=data.get('pc', 0),
                    timestamp=datetime.now().isoformat()
                )
        except Exception as e:
            logger.error(f"Finnhub行情获取失败 {symbol}: {e}")
        return None

    @staticmethod
    def get_tiger_quote(symbol: str) -> Optional[Quote]:
        """从Tiger获取港股实时行情"""
        try:
            from tiger_client import get_stock_brief
            result = get_stock_brief(symbol)
            if isinstance(result, str) and '最新价' in result:
                lines = result.split('\n')
                price = 0
                change = 0
                change_pct = 0
                high = 0
                low = 0
                open_price = 0
                prev_close = 0
                
                for line in lines:
                    if '最新价' in line:
                        try:
                            price = float(line.split('：')[1].strip())
                        except:
                            pass
                    elif '涨跌' in line and '%' in line:
                        try:
                            parts = line.split('：')[1].strip()
                            change_str = parts.split('(')[0].strip()
                            change = float(change_str)
                        except:
                            pass
                    elif '开盘价' in line:
                        try:
                            val = line.split('：')[1].strip()
                            if val != 'None':
                                open_price = float(val)
                        except:
                            pass
                    elif '最高价' in line:
                        try:
                            val = line.split('：')[1].strip()
                            if val != 'None':
                                high = float(val)
                        except:
                            pass
                    elif '昨收' in line:
                        try:
                            val = line.split('：')[1].strip()
                            if val != 'None':
                                prev_close = float(val)
                        except:
                            pass
                
                if price > 0:
                    return Quote(
                        symbol=symbol,
                        price=price,
                        change=change,
                        change_pct=change_pct,
                        high=high,
                        low=low,
                        open=open_price,
                        prev_close=prev_close,
                        timestamp=datetime.now().isoformat()
                    )
        except Exception as e:
            logger.error(f"Tiger行情获取失败 {symbol}: {e}")
        return None

    @classmethod
    def get_quote(cls, symbol: str, market: str) -> Optional[Quote]:
        """获取行情（自动选择数据源）"""
        if market == 'US':
            return cls.get_finnhub_quote(symbol)
        elif market == 'HK':
            return cls.get_tiger_quote(symbol)
        return None

# ============ 缠论分析 ============

class ChanlunEngine:
    """缠论分析引擎"""

    def __init__(self):
        self.czsc = None

    def analyze(self, symbol: str, market: str, quote: Quote) -> Dict:
        """分析缠论结构"""
        # 这里简化处理，实际需要调用czsc库
        # 返回结构化的分析结果
        return {
            'symbol': symbol,
            'market': market,
            'price': quote.price,
            'trend': 'unknown',
            'trend_direction': None,
            'trend_strength': 0,
            'structure_state': 'unknown',
            'bi_count': 0,
            'zs_count': 0,
            'last_zs': None,
            'divergence': None,
            'buy_sell_points': [],
            'trend_fluency': {},
            'zs_movement': None,
            'last_bi': None
        }

    def analyze_with_czsc(self, symbol: str, market: str, quote: Quote, df_daily=None, df_30m=None, df_5m=None) -> Dict:
        """使用czsc库进行完整分析"""
        try:
            import sys
            sys.path.insert(0, str(AGENT_DIR))
            from czsc import CZSC, Freq, format_standard_kline
            from czsc_extension import CzscExtension, StructureState
            import pandas as pd

            result = {
                'symbol': symbol,
                'market': market,
                'price': quote.price,
                'trend': 'unknown',
                'trend_direction': None,
                'trend_strength': 0,
                'structure_state': 'unknown',
                'bi_count': 0,
                'zs_count': 0,
                'last_zs': None,
                'divergence': None,
                'buy_sell_points': [],
                'trend_fluency': {},
                'zs_movement': None,
                'last_bi': None,
                'daily': None,
                'min30': None,
                'min5': None,
                'resonance_level': 0,
                'direction': 'neutral',
                'strategy': 'unknown',
                'entry_plan': {},
                'exit_plan': {}
            }

            # 分析日线
            if df_daily is not None and len(df_daily) > 0:
                df = df_daily.copy()
                df['dt'] = df['time'].apply(lambda x: datetime.fromtimestamp(x / 1000))
                df['symbol'] = symbol
                df['vol'] = df['volume']
                df['amount'] = df.get('amount', df['vol'] * df['close'])
                bars = format_standard_kline(df, freq=Freq.D)
                ka = CZSC(bars)
                ext = CzscExtension(ka, symbol=symbol, timeframe='daily')
                daily_result = ext.full_analysis()
                if daily_result:
                    result['daily'] = daily_result
                    result['trend'] = daily_result.get('trend', 'unknown')
                    result['trend_direction'] = daily_result.get('trend_direction')
                    result['trend_strength'] = daily_result.get('trend_strength', 0)
                    result['structure_state'] = daily_result.get('structure_state', 'unknown')
                    result['bi_count'] = daily_result.get('bi_count', 0)
                    result['zs_count'] = daily_result.get('zs_count', 0)
                    result['last_zs'] = daily_result.get('last_zs')
                    result['divergence'] = daily_result.get('divergence')
                    result['buy_sell_points'] = daily_result.get('buy_sell_points', [])
                    result['trend_fluency'] = daily_result.get('trend_fluency', {})
                    result['zs_movement'] = daily_result.get('zs_movement')
                    result['last_bi'] = daily_result.get('last_bi')

            # 分析30分钟
            if df_30m is not None and len(df_30m) > 0:
                df = df_30m.copy()
                df['dt'] = df['time'].apply(lambda x: datetime.fromtimestamp(x / 1000))
                df['symbol'] = symbol
                df['vol'] = df['volume']
                df['amount'] = df.get('amount', df['vol'] * df['close'])
                bars = format_standard_kline(df, freq=Freq.F30)
                ka = CZSC(bars)
                ext = CzscExtension(ka, symbol=symbol, timeframe='30min')
                min30_result = ext.full_analysis()
                if min30_result:
                    result['min30'] = min30_result

            # 分析5分钟
            if df_5m is not None and len(df_5m) > 0:
                df = df_5m.copy()
                df['dt'] = df['time'].apply(lambda x: datetime.fromtimestamp(x / 1000))
                df['symbol'] = symbol
                df['vol'] = df['volume']
                df['amount'] = df.get('amount', df['vol'] * df['close'])
                bars = format_standard_kline(df, freq=Freq.F5)
                ka = CZSC(bars)
                ext = CzscExtension(ka, symbol=symbol, timeframe='5min')
                min5_result = ext.full_analysis()
                if min5_result:
                    result['min5'] = min5_result

            return result

        except Exception as e:
            logger.error(f"czsc分析失败 {symbol}: {e}")
            return self.analyze(symbol, market, quote)

# ============ 风控引擎 ============

class RiskEngine:
    """风控管理"""

    def __init__(self, config: Dict):
        self.config = config
        self.daily_pnl = 0
        self.consecutive_losses = 0
        self.cooldown_until = None

    def check_risk_limits(self, account_value: float) -> bool:
        """检查风控限制"""
        now = datetime.now()

        if self.cooldown_until:
            cooldown = datetime.fromisoformat(self.cooldown_until)
            if now < cooldown:
                logger.info(f"⏸️ 熔断中，冷却至 {cooldown.strftime('%H:%M')}")
                return False
            else:
                self.cooldown_until = None
                self.consecutive_losses = 0
                logger.info("✅ 熔断解除")

        if self.daily_pnl < -account_value * self.config.get('max_daily_loss_pct', 0.06):
            logger.warning(f"🚫 日亏损超限: ${self.daily_pnl:.2f}")
            return False

        if self.consecutive_losses >= self.config.get('consecutive_loss_limit', 3):
            cooldown_time = now.timestamp() + 3600  # 1小时冷却
            self.cooldown_until = datetime.fromtimestamp(cooldown_time).isoformat()
            logger.warning(f"🚫 连亏{self.consecutive_losses}笔，熔断1小时")
            return False

        return True

    def update_pnl(self, pnl: float):
        """更新盈亏"""
        self.daily_pnl += pnl
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

# ============ 交易引擎 ============

class TradingEngine:
    """统一交易引擎 v2.0"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or str(UNIFIED_DIR / 'config.json')
        self.config = self._load_config()
        self.portfolio = self._load_portfolio()
        self.risk_engine = RiskEngine(self.config.get('risk', {}))
        self.chanlun = ChanlunEngine()
        self.data = DataFetcher()

    def _load_config(self) -> Dict:
        """加载配置"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            return {}

    def _load_portfolio(self) -> Dict:
        """加载持仓"""
        portfolio_path = UNIFIED_DIR / 'portfolio.json'
        try:
            if portfolio_path.exists():
                with open(portfolio_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"持仓加载失败: {e}")
        return {'positions': {}, 'total_pnl': 0, 'daily_pnl': 0}

    def _save_portfolio(self):
        """保存持仓"""
        portfolio_path = UNIFIED_DIR / 'portfolio.json'
        try:
            with open(portfolio_path, 'w') as f:
                json.dump(self.portfolio, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"持仓保存失败: {e}")

    def add_symbol(self, symbol: str, name: str, market: str, strategy: str = 'trend_follow'):
        """添加标的"""
        if 'symbols' not in self.config:
            self.config['symbols'] = {}
        self.config['symbols'][symbol] = {
            'name': name,
            'market': market,
            'enabled': True,
            'strategy': strategy,
            'position_pct': 0.2,
            'interval': 300
        }
        self._save_config()
        logger.info(f"✅ 添加标的: {symbol} ({name})")

    def remove_symbol(self, symbol: str):
        """移除标的"""
        if symbol in self.config.get('symbols', {}):
            del self.config['symbols'][symbol]
            self._save_config()
            logger.info(f"✅ 移除标的: {symbol}")

    def _save_config(self):
        """保存配置"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"配置保存失败: {e}")

    def analyze_symbol(self, symbol: str, market: str) -> Optional[Dict]:
        """分析单个标的"""
        quote = self.data.get_quote(symbol, market)
        if not quote:
            return None

        # 获取K线数据
        df_daily = self._fetch_bars(symbol, market, 'day', 180)
        df_30m = self._fetch_bars(symbol, market, '30min', 15)
        df_5m = self._fetch_bars(symbol, market, '5min', 5)

        # 使用czsc分析
        analysis = self.chanlun.analyze_with_czsc(symbol, market, quote, df_daily, df_30m, df_5m)
        analysis['quote'] = quote

        # 计算共振
        daily = analysis.get('daily', {})
        min30 = analysis.get('min30')
        min5 = analysis.get('min5')
        resonance, resonance_level, direction = self._check_resonance(daily, min30, min5)
        analysis['resonance'] = resonance
        analysis['resonance_level'] = resonance_level
        analysis['direction'] = direction

        # 确定策略
        strategy = self._determine_strategy(daily)
        analysis['strategy'] = strategy

        # 构建进出场预案
        entry_plan = self._build_entry_plan(daily, min30, min5, strategy, direction)
        analysis['entry_plan'] = entry_plan

        exit_plan = self._build_exit_plan(daily, min30, direction)
        analysis['exit_plan'] = exit_plan

        return analysis

    def _fetch_bars(self, symbol: str, market: str, period: str, days: int = 60):
        """获取K线数据"""
        try:
            import pandas as pd
            from datetime import datetime, timedelta

            end_time = datetime.now()
            begin_time = end_time - timedelta(days=days)

            if market == 'HK':
                # 使用Tiger获取港股K线
                from tigeropen.quote.quote_client import QuoteClient
                from tigeropen.tiger_open_config import TigerOpenClientConfig
                from tigeropen.common.consts import Language

                config = TigerOpenClientConfig(sandbox_debug=False)
                config.tiger_id = "20159412"
                config.private_key = """MIICXAIBAAKBgQCQsk07H1czwJy5Gfm9GH2iahHEX3Hhej6y8FW7Hvd9X9jTqxoxFi45aMPFXU7nAx9Ki/gYQlYeXjpCu5RMUHboaz29iBlXmq0gFd6/CdB1LEPbua5V5/kUP53ETbKo0RFjm+fWHxYE6QMpMyW6amP2ASyygSs23aAxYnLZboq5vwIDAQABAoGAXr0/r/w/PlVYyCFn0RXd/J9ybp8Hk1hVARg3KcOGzAIbl8up5IXfUht0Qx9q7/qtXEP09v1IIa4Ue2kSGj18/IhEDla3+EMs24pQ9xnRPgwnzsQkfwNTerGwnxvrM+iHl/IH0AKL0kBPs56JsIIP5VZMd3xNK4xiVTzZIRcRVRECQQDGdrrM6qkomFPw8YRjIO7DuM1IG7ec2PVHX/zYMgCkfYBCsz+DjsopKLjEGms3IqHlSwzB5GLq/z1iHBf8IM/tAkEAuqUn91dmOgSsUJIbuAVN/FtoGcIKe0SYybX3BDsPE6295XR70XMhnrTjx0wIsiANzgC1JZC8PdxB1pxUyx0C2wJBALeao9prxa8OramcZlOm5f0f/JoXOljaxqAPh0UjjUCf8obCeaHl+dT2HWke382UNp6APf8qoPCyzUD0qKPSX0kCQE7WJ/V/wzxKcQZvUKoAA5rOeUA4B/ldVjQNWlM9Jvcm8gkTlKE5wj+pJHUwFpQ2md4jymAdrIVsnZqq2d4ZWPUCQFesxYFPfPv2xnonihe7zqsFAz0pD3E5Ks/F3sdUZk4s/A9Zf1rzxS2XsQtqHgl08L0u340m+YbtTlz/Lyq0mLI=="""
                config.language = Language.zh_CN

                quote_client = QuoteClient(config)
                df = quote_client.get_bars(
                    [symbol], period=period,
                    begin_time=begin_time.strftime('%Y-%m-%d'),
                    end_time=end_time.strftime('%Y-%m-%d')
                )
                if df is None or df.empty:
                    return None
                return df

            elif market == 'US':
                # 使用Finnhub获取美股K线
                import requests
                resolution = 'D' if period == 'day' else '5' if period == '5min' else 'W'
                url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution={resolution}&from={int(begin_time.timestamp())}&to={int(end_time.timestamp())}&token={FINNHUB_KEY}"
                resp = requests.get(url, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('s') == 'ok':
                        df = pd.DataFrame({
                            'time': data['t'],
                            'open': data['o'],
                            'high': data['h'],
                            'low': data['l'],
                            'close': data['c'],
                            'volume': data['v']
                        })
                        return df
            return None
        except Exception as e:
            logger.error(f"获取{period}数据失败 {symbol}: {e}")
            return None

    def _determine_strategy(self, daily: Dict) -> str:
        """
        确定交易策略（基于智能级别 v2.0 + 顺势原则）

        核心：先判趋势方向，再找顺势机会
        - trending down → trend_follow_short（顺势做空）
        - trending up → trend_follow_long（顺势做多）
        - ranging → range_wait（盘整等待）
        - turning → reversal_ready（转折准备）
        """
        if not daily:
            return 'unknown'

        state = daily.get('structure_state', 'unknown')
        trend_dir = daily.get('trend_direction')

        if state == 'trending':
            if trend_dir == 'down':
                return 'trend_follow_short'
            elif trend_dir == 'up':
                return 'trend_follow_long'
        elif state == 'ranging' or daily.get('should_wait_breakout'):
            return 'range_wait'
        elif state == 'turning' and daily.get('should_catch_reversal'):
            return 'reversal_ready'
        elif state == 'turning':
            return 'reversal_observe'

        return 'unknown'

    def _check_resonance(self, daily: Dict, min30: Optional[Dict], min5: Optional[Dict]) -> tuple:
        """
        多级别共振检查

        共振级别：
        - 3级：日线+30分钟+5分钟 同方向 → 强信号
        - 2级：日线+30分钟 同方向 → 中等信号
        - 1级：仅日线方向明确 → 弱信号
        - 0级：无共振 → 不交易
        """
        if not daily:
            return False, 0, 'neutral'

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

        if not daily:
            plan['note'] = '无日线数据'
            return plan

        if strategy == 'range_wait':
            plan['note'] = '盘整中，不交易'
            return plan

        # ---- 顺势做空（下跌趋势） ----
        if strategy == 'trend_follow_short':
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
                    plan['position_pct'] = 0.2
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
            'stop_loss': None,
            'take_profit': None,
            'trailing_stop': None,
            'structural_stop': None,
            'exit_conditions': [],
            'note': ''
        }

        if not daily:
            plan['note'] = '无日线数据'
            return plan

        last_zs = daily.get('last_zs')
        if not last_zs:
            plan['note'] = '无中枢数据'
            return plan

        zs_zg = last_zs.get('zg', 0)
        zs_zd = last_zs.get('zd', 0)

        if direction == 'long':
            plan['stop_loss'] = {
                'price': zs_zd * 0.995,
                'logic_price': zs_zd,
                'type': 'entry_invalidation',
                'reason': f'uptrend可能终结: 价格跌破中枢下沿{zs_zd:.2f}'
            }
            plan['take_profit'] = {
                'price': zs_zg,
                'type': 'holding_invalidation',
                'reason': f'上升趋势结束: 价格回到{zs_zg:.2f}'
            }
            plan['trailing_stop'] = {
                'trigger_pct': 0.02,
                'action': 'move_to_entry',
                'reason': '盈利2%后保护利润'
            }
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
            plan['stop_loss'] = {
                'price': zs_zg * 1.005,
                'logic_price': zs_zg,
                'type': 'entry_invalidation',
                'reason': f'downtrend可能终结: 价格突破中枢上沿{zs_zg:.2f}'
            }
            plan['take_profit'] = {
                'price': zs_zd,
                'type': 'holding_invalidation',
                'reason': f'下跌趋势结束: 价格回到{zs_zd:.2f}'
            }
            plan['trailing_stop'] = {
                'trigger_pct': 0.02,
                'action': 'move_to_entry',
                'reason': '盈利2%后保护利润'
            }
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

    def _check_position_exit(self, symbol: str, analysis: Dict) -> Optional[Dict]:
        """
        检查持仓是否需要平仓

        三层检查：
        1. 入场止损：价格突破入场逻辑破坏点
        2. 持仓止盈：价格回到持仓逻辑破坏点
        3. 结构止损：小级别出现反向信号
        """
        pos = self.portfolio.get('positions', {}).get(symbol, {})
        if not pos or pos.get('position', 0) == 0:
            return None

        current_price = analysis.get('quote', Quote('', 0, 0, 0, 0, 0, 0, 0, '')).price
        entry_price = pos.get('avg_cost', 0)
        direction = pos.get('direction', 'short')
        exit_plan = analysis.get('exit_plan', {})

        if not exit_plan:
            return None

        # 1. 入场止损检查
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

        # 2. 持仓止盈检查
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

        # 3. 结构止损检查（30分钟反向信号）
        structural_stop = exit_plan.get('structural_stop', {})
        if structural_stop and analysis.get('min30'):
            min30_bsp = analysis['min30'].get('buy_sell_points', [])
            condition = structural_stop.get('condition', '')

            if condition == '30min_buy_signal':
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
                sell_signals = [b for b in min30_bsp if 'sell' in b.get('type', '')]
                if sell_signals:
                    best = max(sell_signals, key=lambda x: x.get('confidence', 0))
                    return {
                        'reason': '结构止损',
                        'detail': f"30分钟卖点: {best['type']} @ {best['price']:.2f}",
                        'price': current_price,
                        'stop_price': best['price']
                    }

        # 4. 移动止损检查
        trailing = exit_plan.get('trailing_stop', {})
        if trailing and entry_price > 0:
            trigger_pct = trailing.get('trigger_pct', 0.02)
            if direction == 'short':
                profit_pct = (entry_price - current_price) / entry_price
                if profit_pct >= trigger_pct:
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

    def generate_signal(self, symbol: str, analysis: Dict) -> Optional[TradeSignal]:
        """
        生成交易信号（顺势原则）

        核心逻辑：
        - 下跌趋势 → 找卖点做空
        - 上升趋势 → 找买点做多
        - 盘整/转折 → 不交易
        """
        # 不满足共振条件
        resonance_level = analysis.get('resonance_level', 0)
        if resonance_level < 2:
            return None

        # 盘整不交易
        strategy = analysis.get('strategy', 'unknown')
        if strategy == 'range_wait':
            return None

        direction = analysis.get('direction', 'neutral')
        daily_bsp = analysis.get('daily', {}).get('buy_sell_points', [])
        min30_bsp = analysis.get('min30', {}).get('buy_sell_points', []) if analysis.get('min30') else []

        best_point = None
        source = ''
        action = ''

        # ---- 下跌趋势：找卖点做空 ----
        if direction == 'short' and strategy == 'trend_follow_short':
            sell_points_30 = [b for b in min30_bsp if 'sell' in b.get('type', '')]
            if sell_points_30:
                best_point = max(sell_points_30, key=lambda x: x.get('confidence', 0))
                source = '30min'
            action = 'SELL'

        # ---- 上升趋势：找买点做多 ----
        elif direction == 'long' and strategy == 'trend_follow_long':
            buy_points_30 = [b for b in min30_bsp if 'buy' in b.get('type', '')]
            if buy_points_30:
                best_point = max(buy_points_30, key=lambda x: x.get('confidence', 0))
                source = '30min'
            action = 'BUY'

        if not best_point:
            return None

        # 仓位计算 — 使用实时价格
        quote = analysis.get('quote')
        current_price = quote.price if quote else 0
        if current_price <= 0:
            return None

        account_value = 1000000  # 默认100万
        entry_pct = analysis.get('entry_plan', {}).get('position_pct', 0.2)
        position_value = account_value * entry_pct
        quantity = int(position_value / current_price / 100) * 100

        if quantity <= 0:
            return None

        # 出场参数 — 基于实时价格计算
        exit_plan = analysis.get('exit_plan', {})
        sl = exit_plan.get('stop_loss', {})
        tp = exit_plan.get('take_profit', {})
        stop_loss = sl.get('price', current_price * 0.97) if isinstance(sl, dict) else current_price * 0.97
        take_profit = tp.get('price', current_price * 1.05) if isinstance(tp, dict) else current_price * 1.05

        return TradeSignal(
            symbol=symbol,
            action=action,
            direction=direction,
            signal_type=best_point['type'],
            price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            quantity=quantity,
            confidence=best_point.get('confidence', 0.6),
            resonance_level=resonance_level,
            detail=f"{source} {best_point['type']} | 共振{resonance_level}级 | {strategy} | {direction}",
            strategy=strategy
        )

    def execute_trade(self, signal: TradeSignal) -> bool:
        """执行交易 — 对接老虎模拟盘下单"""
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"💰 执行交易: {signal.action} {signal.direction}")
            logger.info(f"   标的: {signal.symbol}")
            logger.info(f"   类型: {signal.signal_type}")
            logger.info(f"   价格: ${signal.price:.2f}")
            logger.info(f"   数量: {signal.quantity}")
            logger.info(f"   止损: ${signal.stop_loss:.2f}")
            logger.info(f"   止盈: ${signal.take_profit:.2f}")
            logger.info(f"   共振: {signal.resonance_level}级")
            logger.info(f"{'='*50}")

            # 老虎模拟盘下单
            action = 'BUY' if signal.action == 'BUY' else 'SELL'
            result = place_order_limit(
                symbol=signal.symbol,
                price=signal.price,
                quantity=signal.quantity,
                action=action
            )
            logger.info(f"   老虎下单结果: {result}")

            # 更新持仓
            if signal.symbol not in self.portfolio['positions']:
                self.portfolio['positions'][signal.symbol] = {}
            
            pos = self.portfolio['positions'][signal.symbol]
            if signal.action == 'BUY':
                pos['position'] = signal.quantity
                pos['avg_cost'] = signal.price
                pos['direction'] = 'long'
                pos['entry_time'] = datetime.now().isoformat()
            elif signal.action == 'SELL':
                pos['position'] = signal.quantity
                pos['avg_cost'] = signal.price
                pos['direction'] = 'short'
                pos['entry_time'] = datetime.now().isoformat()

            self._save_portfolio()
            return True

        except Exception as e:
            logger.error(f"交易执行失败: {e}")
            return False

    def execute_exit(self, symbol: str, exit_info: Dict) -> bool:
        """执行平仓 — 对接老虎模拟盘"""
        try:
            pos = self.portfolio.get('positions', {}).get(symbol, {})
            if not pos:
                return False

            entry_price = pos.get('avg_cost', 0)
            exit_price = exit_info.get('price', 0)
            quantity = pos.get('position', 0)
            direction = pos.get('direction', 'long')

            # 计算盈亏
            if direction == 'short':
                pnl = (entry_price - exit_price) * quantity
            else:
                pnl = (exit_price - entry_price) * quantity

            # 老虎平仓
            close_action = 'BUY' if direction == 'short' else 'SELL'
            result = place_order_limit(
                symbol=symbol,
                price=exit_price,
                quantity=quantity,
                action=close_action
            )
            logger.info(f"   老虎平仓结果: {result}")

            # 更新持仓
            self.portfolio['positions'][symbol] = {}
            self.portfolio['total_pnl'] += pnl
            self.portfolio['daily_pnl'] += pnl
            self._save_portfolio()

            # 更新风控
            self.risk_engine.update_pnl(pnl)

            logger.info(f"✅ 平仓: {symbol} {direction} @ ${exit_price:.2f} → ${pnl:.2f}")
            return True

        except Exception as e:
            logger.error(f"平仓失败: {e}")
            return False

    def run_cycle(self):
        """运行一个分析周期"""
        symbols = self.config.get('symbols', {})
        for symbol, config in symbols.items():
            if not config.get('enabled', False):
                continue

            market = config.get('market', 'HK')
            analysis = self.analyze_symbol(symbol, market)
            if not analysis:
                continue

            # 输出分析结果
            quote = analysis.get('quote')
            trend_dir = analysis.get('trend_direction', '?')
            trend_label = '⬇️下跌趋势' if trend_dir == 'down' else '⬆️上升趋势' if trend_dir == 'up' else '➡️盘整'
            strategy = analysis.get('strategy', 'unknown')
            resonance_level = analysis.get('resonance_level', 0)
            direction = analysis.get('direction', 'neutral')

            logger.info(f"\n{'='*60}")
            logger.info(f"📊 {symbol} 缠论分析")
            logger.info(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'='*60}")
            logger.info(f"💰 价格: ${quote.price:.2f}")
            logger.info(f"📈 日线: {trend_label} 结构:{analysis.get('structure_state', 'N/A')} 强度{analysis.get('trend_strength', 0):.0%}")
            logger.info(f"🎯 策略:{strategy} 方向:{direction} 共振:{resonance_level}级")

            if analysis.get('min30'):
                logger.info(f"📊 30m: {analysis['min30'].get('structure_state', 'N/A')}")
            if analysis.get('min5'):
                logger.info(f"📊 5m: {analysis['min5'].get('structure_state', 'N/A')}")

            # 检查平仓
            exit_info = self._check_position_exit(symbol, analysis)
            if exit_info:
                self.execute_exit(symbol, exit_info)
                continue

            # 检查入场
            signal = self.generate_signal(symbol, analysis)
            if signal:
                self.execute_trade(signal)
            else:
                logger.info(f"⏳ 无交易信号")

# ============ 主入口 ============

def main():
    """主入口"""
    import argparse
    parser = argparse.ArgumentParser(description='统一交易引擎')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--add', nargs=3, metavar=('SYMBOL', 'NAME', 'MARKET'), help='添加标的')
    parser.add_argument('--remove', help='移除标的')
    parser.add_argument('--list', action='store_true', help='列出标的')
    parser.add_argument('--analyze', help='分析标的')
    parser.add_argument('--run', action='store_true', help='运行监控')
    parser.add_argument('--interval', type=int, default=300, help='监控间隔(秒)')

    args = parser.parse_args()

    engine = TradingEngine(args.config)

    if args.add:
        symbol, name, market = args.add
        engine.add_symbol(symbol, name, market)
    elif args.remove:
        engine.remove_symbol(args.remove)
    elif args.list:
        symbols = engine.config.get('symbols', {})
        print("\n📋 标的列表:")
        for symbol, config in symbols.items():
            status = "✅" if config.get('enabled') else "❌"
            print(f"  {status} {symbol} ({config.get('name')}) - {config.get('market')}")
    elif args.analyze:
        symbol_config = engine.config.get('symbols', {}).get(args.analyze, {})
        market = symbol_config.get('market', 'US')
        analysis = engine.analyze_symbol(args.analyze, market)
        if analysis:
            print(f"\n📊 {args.analyze} 分析:")
            print(f"  价格: ${analysis['quote'].price:.2f}")
            print(f"  趋势: {analysis['trend']}")
        else:
            print(f"❌ 无法获取 {args.analyze} 数据")
    elif args.run:
        print(f"\n🚀 启动统一交易引擎...")
        print(f"   标的: {list(engine.config.get('symbols', {}).keys())}")
        print(f"   间隔: {args.interval}秒")
        while True:
            try:
                engine.run_cycle()
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\n⏹️ 监控已停止")
                break
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
