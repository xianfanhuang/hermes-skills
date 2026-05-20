#!/usr/bin/env python3
"""
CRCL 实时缠论模拟交易 - Tiger 模拟盘

使用 Tiger API 获取历史K线 + 模拟盘下单
使用 SmartDataRouter 获取实时行情 (Finnhub → iTick → Tiger)

功能:
- 获取 CRCL 日线/5分钟K线数据 (Tiger)
- 获取 CRCL 实时报价 (Finnhub，市场收盘时用 Tiger 收盘价)
- 基于缠论分析生成交易信号
- 通过 Tiger 模拟盘执行下单

使用方式:
    python3 crcl_tiger_trader.py --once      # 单次扫描
    python3 crcl_tiger_trader.py --loop      # 持续监控（每5分钟）
    python3 crcl_tiger_trader.py --buy 10    # 手动买入10股
    python3 crcl_tiger_trader.py --sell 10   # 手动卖出10股
"""

import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# Tiger SDK
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import Language, OrderType

# Smart Data Router (智能路由)
sys.path.insert(0, str(Path(__file__).parent.parent / "data"))
try:
    from smart_data_router import SmartDataRouter, AssetType, TaskType, create_router
    ROUTER_AVAILABLE = True
except ImportError:
    ROUTER_AVAILABLE = False
    logger.warning("SmartDataRouter not available, using Tiger only")

# czsc 扩展层
try:
    from czsc import CZSC, RawBar, Freq
    from czsc_extension import CzscExtension, analyze_multi_level
    CZSC_AVAILABLE = True
except ImportError:
    CZSC_AVAILABLE = False
    logger.warning("CzscExtension not available")

# 风控引擎
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from risk_engine import RiskEngine, RiskAlert
    RISK_AVAILABLE = True
except ImportError:
    RISK_AVAILABLE = False
    logger.warning("RiskEngine not available")

# 反思引擎
try:
    from reflection_engine import ReflectionEngine
    REFLECTION_AVAILABLE = True
except ImportError:
    REFLECTION_AVAILABLE = False
    logger.warning("ReflectionEngine not available")

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / 'crcl_tiger.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 常量
PORTFOLIO_PATH = Path(__file__).parent / "crcl_portfolio_tiger.json"
TIGER_ID = "20159412"
TIGER_PRIVATE_KEY = """MIICXAIBAAKBgQCQsk07H1czwJy5Gfm9GH2iahHEX3Hhej6y8FW7Hvd9X9jTqxoxFi45aMPFXU7nAx9Ki/gYQlYeXjpCu5RMUHboaz29iBlXmq0gFd6/CdB1LEPbua5V5/kUP53ETbKo0RFjm+fWHxYE6QMpMyW6amP2ASyygSs23aAxYnLZboq5vwIDAQABAoGAXr0/r/w/PlVYyCFn0RXd/J9ybp8Hk1hVARg3KcOGzAIbl8up5IXfUht0Qx9q7/qtXEP09v1IIa4Ue2kSGj18/IhEDla3+EMs24pQ9xnRPgwnzsQkfwNTerGwnxvrM+iHl/IH0AKL0kBPs56JsIIP5VZMd3xNK4xiVTzZIRcRVRECQQDGdrrM6qkomFPw8YRjIO7DuM1IG7ec2PVHX/zYMgCkfYBCsz+DjsopKLjEGms3IqHlSwzB5GLq/z1iHBf8IM/tAkEAuqUn91dmOgSsUJIbuAVN/FtoGcIKe0SYybX3BDsPE6295XR70XMhnrTjx0wIsiANzgC1JZC8PdxB1pxUyx0C2wJBALeao9prxa8OramcZlOm5f0f/JoXOljaxqAPh0UjjUCf8obCeaHl+dT2HWke382UNp6APf8qoPCyzUD0qKPSX0kCQE7WJ/V/wzxKcQZvUKoAA5rOeUA4B/ldVjQNWlM9Jvcm8gkTlKE5wj+pJHUwFpQ2md4jymAdrIVsnZqq2d4ZWPUCQFesxYFPfPv2xnonihe7zqsFAz0pD3E5Ks/F3sdUZk4s/A9Zf1rzxS2XsQtqHgl08L0u340m+YbtTlz/Lyq0mLI=="""
LIVE_ACCOUNT = "1406653"
SIM_ACCOUNT = "21409378833585169"


class TigerClient:
    """Tiger API 客户端封装"""

    def __init__(self, account: str = SIM_ACCOUNT):
        self.account = account
        self.config = TigerOpenClientConfig(sandbox_debug=False)
        self.config.tiger_id = TIGER_ID
        self.config.private_key = TIGER_PRIVATE_KEY
        self.config.language = Language.zh_CN
        self.config.account = account

        self.quote_client = QuoteClient(self.config)
        self.trade_client = TradeClient(self.config)
        logger.info(f"🐯 Tiger 客户端初始化成功 - 账户: {account}")

    def get_account_info(self) -> Dict:
        """获取账户信息"""
        assets = self.trade_client.get_assets()
        if assets and len(assets) > 0:
            a = assets[0]
            seg = a.segments.get('S')
            if seg:
                return {
                    'net_liquid_value': seg.net_liquidation,
                    'available_funds': seg.available_funds,
                    'cash': seg.cash,
                    'buying_power': seg.equity_with_loan * 2 if seg.equity_with_loan else 0,
                    'unrealized_pnl': 0,
                    'realized_pnl': 0,
                }
        return {}

    def get_positions(self) -> List[Dict]:
        """获取持仓"""
        positions = self.trade_client.get_positions()
        result = []
        if positions:
            for p in positions:
                result.append({
                    'symbol': p.contract.symbol,
                    'quantity': p.quantity,
                    'average_cost': p.average_cost,
                    'market_value': p.market_value,
                    'unrealized_pnl': p.unrealized_pnl,
                })
        return result

    def get_daily_bars(self, symbol: str = "CRCL", limit: int = 30) -> Optional[any]:
        """获取日线数据"""
        try:
            bars = self.quote_client.get_bars([symbol], period="day", limit=limit)
            if bars is not None and not bars.empty:
                return bars
            return None
        except Exception as e:
            logger.error(f"获取日线失败: {e}")
            return None

    def get_realtime_quote(self, symbol: str = "CRCL") -> Optional[Dict]:
        """
        获取实时报价 (通过 SmartDataRouter)

        路由逻辑:
        - 美股盘中 → Finnhub (实时)
        - 美股收盘后 → Tiger (最后收盘价)
        - 港股 → Tiger (免费L2实时)
        """
        if ROUTER_AVAILABLE:
            try:
                router = create_router()
                quote = router.get_quote(symbol, AssetType.US_STOCK, TaskType.REALTIME_QUOTE)
                if quote:
                    return {
                        'price': quote.price,
                        'prev_close': quote.prev_close,
                        'change': quote.change,
                        'change_pct': quote.change_pct,
                        'provider': quote.provider,
                        'is_realtime': quote.is_realtime,
                        'timestamp': quote.timestamp,
                    }
            except Exception as e:
                logger.warning(f"Router quote failed, fallback to Tiger: {e}")

        # Fallback: Tiger 最后收盘价
        try:
            bars = self.get_daily_bars(symbol, limit=2)
            if bars is not None and len(bars) >= 2:
                last = bars.iloc[-1]
                prev = bars.iloc[-2]
                price = float(last['close'])
                prev_close = float(prev['close'])
                return {
                    'price': price,
                    'prev_close': prev_close,
                    'change': price - prev_close,
                    'change_pct': (price - prev_close) / prev_close * 100 if prev_close else 0,
                    'provider': 'tiger_close',
                    'is_realtime': False,
                }
        except Exception as e:
            logger.error(f"Tiger fallback quote failed: {e}")
        return None

    def get_kline_from_router(self, symbol: str = "CRCL", period: str = "day",
                               limit: int = 100) -> List:
        """
        通过 SmartDataRouter 获取K线数据

        Args:
            symbol: 品种代码
            period: K线周期 (day/5min/30min)
            limit: 数量

        Returns:
            KLine 列表
        """
        if ROUTER_AVAILABLE:
            try:
                router = create_router()
                klines = router.get_kline(symbol, AssetType.US_STOCK,
                                          period=period, limit=limit)
                if klines:
                    return klines
            except Exception as e:
                logger.warning(f"Router kline failed: {e}")

        # Fallback: Tiger
        try:
            if period == 'day':
                bars = self.get_daily_bars(symbol, limit=limit)
            else:
                bars = self.get_intraday_bars(symbol, period=period, limit=limit)

            if bars is not None and not bars.empty:
                from types import SimpleNamespace
                result = []
                for _, row in bars.iterrows():
                    result.append(SimpleNamespace(
                        time=str(row.get('datetime', row.name)),
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=float(row.get('vol', row.get('volume', 0))),
                    ))
                return result
        except Exception as e:
            logger.error(f"Tiger kline fallback failed: {e}")

        return []

    def get_intraday_bars(self, symbol: str = "CRCL", period: str = "5min", limit: int = 50) -> Optional[any]:
        """获取分钟线数据"""
        try:
            bars = self.quote_client.get_bars([symbol], period=period, limit=limit)
            if bars is not None and not bars.empty:
                return bars
            return None
        except Exception as e:
            logger.error(f"获取{period}线失败: {e}")
            return None

    def place_order(self, symbol: str, action: str, quantity: int, price: float = None, order_type: str = "MKT") -> Optional[str]:
        """
        下单
        
        Args:
            symbol: 股票代码
            action: BUY 或 SELL
            quantity: 数量
            price: 限价（限价单时需要）
            order_type: MKT 市价单 / LMT 限价单
        
        Returns:
            订单ID 或 None
        """
        try:
            from tigeropen.trade.domain.contract import Contract
            contract = Contract(symbol=symbol, currency='USD', exchange='SMART')

            if order_type == "MKT":
                order = self.trade_client.create_order(
                    contract=contract,
                    action=action,
                    order_type=OrderType.MKT,
                    quantity=quantity,
                    time_in_force='day',
                    outside_rth=True
                )
            else:  # LMT
                order = self.trade_client.create_order(
                    contract=contract,
                    action=action,
                    order_type=OrderType.LMT,
                    quantity=quantity,
                    limit_price=price,
                    time_in_force='day',
                    outside_rth=True
                )

            result = self.trade_client.place_order(order)
            if result:
                order_id = order.order_id
                logger.info(f"✅ 订单提交成功: {action} {quantity} {symbol} @ {order_type} - OrderID: {order_id}")
                return str(order_id)
            else:
                logger.error(f"❌ 订单提交失败")
                return None
        except Exception as e:
            logger.error(f"❌ 下单异常: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        try:
            result = self.trade_client.cancel_order(order_id)
            logger.info(f"✅ 订单取消成功: {order_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 取消订单失败: {e}")
            return False

    def get_orders(self) -> List[Dict]:
        """获取今日订单"""
        orders = self.trade_client.get_orders()
        result = []
        if orders:
            for o in orders:
                result.append({
                    'order_id': o.order_id,
                    'symbol': o.contract.symbol,
                    'action': o.action,
                    'quantity': o.quantity,
                    'filled': o.filled,
                    'status': o.status,
                    'order_type': o.order_type,
                    'limit_price': o.limit_price,
                })
        return result


class ChanlunAnalyzer:
    """缠论分析器"""

    @staticmethod
    def find_pivots(df, lookback=3):
        """寻找分型（顶底）"""
        highs = df['high'].values
        lows = df['low'].values
        n = len(df)

        top_pivots = []  # 顶分型
        bot_pivots = []  # 底分型

        for i in range(lookback, n - lookback):
            # 顶分型: 当前高点 > 前后高点
            if highs[i] > max(highs[i-lookback:i]) and highs[i] > max(highs[i+1:i+lookback+1]):
                top_pivots.append((i, highs[i]))
            # 底分型: 当前低点 < 前后低点
            if lows[i] < min(lows[i-lookback:i]) and lows[i] < min(lows[i+1:i+lookback+1]):
                bot_pivots.append((i, lows[i]))

        return top_pivots, bot_pivots

    @staticmethod
    def find_bi(pivots, direction='up'):
        """构建笔（连接顶底分型）"""
        bi_list = []
        if len(pivots) < 2:
            return bi_list

        for i in range(len(pivots) - 1):
            start_idx, start_val = pivots[i]
            end_idx, end_val = pivots[i + 1]

            if direction == 'up' and end_val > start_val:
                bi_list.append({
                    'start': (start_idx, start_val),
                    'end': (end_idx, end_val),
                    'direction': 'up',
                    'length': end_val - start_val,
                })
            elif direction == 'down' and end_val < start_val:
                bi_list.append({
                    'start': (start_idx, start_val),
                    'end': (end_idx, end_val),
                    'direction': 'down',
                    'length': start_val - end_val,
                })

        return bi_list

    @staticmethod
    def find_zhongshu(bi_list):
        """寻找中枢（至少3笔重叠）"""
        zs_list = []
        if len(bi_list) < 3:
            return zs_list

        for i in range(len(bi_list) - 2):
            bi1 = bi_list[i]
            bi2 = bi_list[i + 1]
            bi3 = bi_list[i + 2]

            # 计算重叠区间
            highs = [max(bi1['start'][1], bi1['end'][1]),
                     max(bi2['start'][1], bi2['end'][1]),
                     max(bi3['start'][1], bi3['end'][1])]
            lows = [min(bi1['start'][1], bi1['end'][1]),
                    min(bi2['start'][1], bi2['end'][1]),
                    min(bi3['start'][1], bi3['end'][1])]

            zs_high = min(highs)
            zs_low = max(lows)

            if zs_high > zs_low:
                zs_list.append({
                    'high': zs_high,
                    'low': zs_low,
                    'start_idx': bi1['start'][0],
                    'end_idx': bi3['end'][0],
                })

        return zs_list

    @staticmethod
    def check_divergence(bi_list, prices):
        """检查背驰"""
        if len(bi_list) < 2:
            return False, ""

        last_bi = bi_list[-1]
        prev_bi = bi_list[-2]

        if last_bi['direction'] == 'down':
            # 底背驰: 价格新低但力度减弱
            if last_bi['end'][1] < prev_bi['end'][1]:
                if last_bi['length'] < prev_bi['length'] * 0.8:
                    return True, "底背驰"
        elif last_bi['direction'] == 'up':
            # 顶背驰: 价格新高但力度减弱
            if last_bi['end'][1] > prev_bi['end'][1]:
                if last_bi['length'] < prev_bi['length'] * 0.8:
                    return True, "顶背驰"

        return False, ""

    @staticmethod
    def analyze(df, timeframe='daily'):
        """
        完整缠论分析
        
        Returns:
            dict: 分析结果
        """
        if df is None or len(df) < 10:
            return None

        top_pivots, bot_pivots = ChanlunAnalyzer.find_pivots(df)
        up_bi = ChanlunAnalyzer.find_bi(bot_pivots + top_pivots, 'up')
        down_bi = ChanlunAnalyzer.find_bi(top_pivots + bot_pivots, 'down')
        all_bi = sorted(up_bi + down_bi, key=lambda x: x['start'][0])

        zhongshu = ChanlunAnalyzer.find_zhongshu(all_bi)
        has_divergence, divergence_type = ChanlunAnalyzer.check_divergence(all_bi, df['close'].values)

        # 当前价格
        current_price = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2] if len(df) > 1 else current_price

        # 判断趋势
        trend = "neutral"
        if len(zhongshu) > 0:
            zs = zhongshu[-1]
            if current_price > zs['high']:
                trend = "up"
            elif current_price < zs['low']:
                trend = "down"
            else:
                trend = "range"

        # 最后一笔方向
        last_bi_direction = all_bi[-1]['direction'] if all_bi else "unknown"

        return {
            'timeframe': timeframe,
            'current_price': current_price,
            'prev_close': prev_close,
            'change_pct': (current_price - prev_close) / prev_close * 100,
            'trend': trend,
            'bi_count': len(all_bi),
            'zs_count': len(zhongshu),
            'last_bi_direction': last_bi_direction,
            'has_divergence': has_divergence,
            'divergence_type': divergence_type,
            'last_zs': zhongshu[-1] if zhongshu else None,
            'top_pivots': top_pivots[-3:] if top_pivots else [],
            'bot_pivots': bot_pivots[-3:] if bot_pivots else [],
        }


class CRCLTrader:
    """CRCL 缠论交易器"""

    def __init__(self, account: str = SIM_ACCOUNT):
        self.client = TigerClient(account)
        self.portfolio = self.load_portfolio()

        # 初始化风控引擎
        self.risk_engine = None
        if RISK_AVAILABLE:
            try:
                self.risk_engine = RiskEngine(store=None, config={
                    'technical_stop_pct': 0.03,
                    'time_stop_bars': 8,
                    'time_stop_reduce_pct': 0.5,
                    'max_loss_per_trade': 0.03,
                    'max_daily_loss': 0.08,
                    'consecutive_loss_limit': 3,
                    'halt_duration_minutes': 60,
                })
                logger.info("✅ 风控引擎已初始化")
            except Exception as e:
                logger.warning(f"风控引擎初始化失败: {e}")

        # 初始化反思引擎
        self.reflection_engine = None
        if REFLECTION_AVAILABLE:
            try:
                self.reflection_engine = ReflectionEngine(store=None)
                logger.info("✅ 反思引擎已初始化")
            except Exception as e:
                logger.warning(f"反思引擎初始化失败: {e}")

    def load_portfolio(self) -> Dict:
        """加载投资组合"""
        if PORTFOLIO_PATH.exists():
            with open(PORTFOLIO_PATH, 'r') as f:
                return json.load(f)

        # 初始化投资组合
        return {
            "account": {
                "name": "CRCL Tiger 模拟交易",
                "created_at": datetime.now().isoformat(),
                "initial_capital": 10000,
                "currency": "USD",
            },
            "positions": [],
            "trade_log": [],
            "signals": [],
            "last_analysis": None,
        }

    def save_portfolio(self):
        """保存投资组合"""
        import enum
        class CzscEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, enum.Enum):
                    return str(obj)
                if hasattr(obj, 'to_dict'):
                    return obj.to_dict()
                return super().default(obj)

        with open(PORTFOLIO_PATH, 'w') as f:
            json.dump(self.portfolio, f, indent=2, ensure_ascii=False, cls=CzscEncoder)

    def analyze(self) -> Dict:
        """执行缠论分析（czsc 扩展层 + 旧版分析器）"""
        logger.info("📊 开始 CRCL 缠论分析...")

        # 获取日线数据
        daily_bars = self.client.get_daily_bars("CRCL", limit=30)
        daily_analysis = ChanlunAnalyzer.analyze(daily_bars, 'daily')

        # 获取5分钟数据
        min5_bars = self.client.get_intraday_bars("CRCL", period="5min", limit=50)
        min5_analysis = ChanlunAnalyzer.analyze(min5_bars, '5min')

        # 获取30分钟数据
        min30_bars = self.client.get_intraday_bars("CRCL", period="30min", limit=50)
        min30_analysis = ChanlunAnalyzer.analyze(min30_bars, '30min')

        result = {
            'timestamp': datetime.now().isoformat(),
            'daily': daily_analysis,
            'min30': min30_analysis,
            'min5': min5_analysis,
        }

        # czsc 扩展层分析（如果可用）
        if CZSC_AVAILABLE:
            czsc_result = self._czsc_analyze()
            result['czsc'] = czsc_result

        self.portfolio['last_analysis'] = result
        self.save_portfolio()

        return result

    def _czsc_analyze(self) -> Dict:
        """czsc 扩展层分析（多级别共振）"""
        from czsc_extension import CzscExtension, analyze_multi_level
        from czsc import CZSC, RawBar, Freq
        from datetime import datetime as dt_parser

        bars_dict = {}

        for period, limit in [('day', 100), ('5min', 200), ('30min', 200)]:
            try:
                klines = self.client.get_kline_from_router("CRCL", period=period, limit=limit)
                if not klines:
                    continue

                bars = []
                for k in klines:
                    try:
                        d = dt_parser.strptime(k.time[:10], '%Y-%m-%d')
                    except:
                        d = dt_parser.now()
                    bars.append(RawBar(
                        symbol='CRCL', dt=d, freq=Freq.D,
                        open=k.open, high=k.high, low=k.low, close=k.close,
                        vol=float(k.volume), amount=float(k.volume * k.close),
                    ))

                timeframe_name = 'daily' if period == 'day' else period
                bars_dict[timeframe_name] = bars
                logger.info(f"  czsc {timeframe_name}: {len(bars)} bars loaded")

            except Exception as e:
                logger.warning(f"  czsc {period} failed: {e}")

        # 多级别联立分析
        if bars_dict:
            result = analyze_multi_level(bars_dict, symbol='CRCL')
            if result:
                best_type = result.get('best_signal', {}).get('type', '无') if result.get('best_signal') else '无'
                logger.info(f"  多级别分析完成，最佳信号: {best_type}")
            return result or {}

        return {}

    def generate_signal(self, analysis: Dict) -> Optional[Dict]:
        """
        基于缠论分析生成交易信号

        信号逻辑（优先级）:
        1. czsc 多级别共振信号（最高优先级）
        2. czsc 背驰/类二买/震荡买卖点
        3. 旧版信号（日线趋势+5分钟背驰）
        4. 止损信号 + 风控引擎
        """
        daily = analysis.get('daily')
        min5 = analysis.get('min5')
        czsc_analysis = analysis.get('czsc', {})

        # 获取当前价格
        current_price = None
        if daily:
            current_price = daily.get('current_price')
        if not current_price and czsc_analysis:
            for tf in ['daily', '30min', '5min']:
                tf_data = czsc_analysis.get('results', {}).get(tf, {})
                if tf_data:
                    current_price = tf_data.get('last_price')
                    if current_price:
                        break
        if not current_price:
            return None

        has_position = len(self.portfolio['positions']) > 0

        # ====== 信号1: czsc 多级别共振（最高优先级） ======
        if czsc_analysis:
            best = czsc_analysis.get('best_signal')
            if best and not best.get('filtered'):
                sig_type = best.get('type', '')
                direction = best.get('direction', '')

                if direction == 'LONG' and not has_position:
                    stop_loss = best.get('stop_loss', current_price * 0.97)
                    target = best.get('target', current_price * 1.06)

                    # 风控检查
                    risk_alerts = self._check_risk({
                        'entry_price': current_price, 'direction': 'long',
                    }, current_price)
                    if any(a.action == 'close_all' for a in risk_alerts):
                        logger.warning(f"风控阻止开多: {[a.message for a in risk_alerts]}")
                        return None

                    return {
                        'type': 'BUY',
                        'strength': best.get('strength', 0.5),
                        'reason': f"czsc {sig_type}: {best.get('reason', '')}",
                        'entry': current_price,
                        'stop_loss': stop_loss,
                        'target': target,
                        'confidence': int(best.get('confidence', 0.5) * 100),
                        'czsc_level': best.get('level', 'L2'),
                        'timestamp': datetime.now().isoformat(),
                    }

                elif direction == 'SHORT' and has_position:
                    return {
                        'type': 'SELL',
                        'strength': best.get('strength', 0.5),
                        'reason': f"czsc {sig_type}: {best.get('reason', '')}",
                        'entry': current_price,
                        'czsc_level': best.get('level', 'L2'),
                        'timestamp': datetime.now().isoformat(),
                    }

        # ====== 信号2: 旧版信号（日线趋势+5分钟背驰） ======
        if daily and min5:
            if daily.get('trend') == 'up' and min5.get('last_bi_direction') == 'up' and not has_position:
                if min5.get('has_divergence') and min5.get('divergence_type') == '底背驰':
                    return {
                        'type': 'BUY', 'strength': 'STRONG',
                        'reason': f"日线上升趋势 + 5分钟底背驰确认",
                        'entry': current_price,
                        'stop_loss': current_price * 0.97,
                        'target': current_price * 1.06,
                        'confidence': 80,
                        'timestamp': datetime.now().isoformat(),
                    }

            if daily.get('trend') == 'up' and daily.get('last_zs') and not has_position:
                zs_high = daily['last_zs']['high']
                if current_price > zs_high * 1.02:
                    return {
                        'type': 'BUY', 'strength': 'MEDIUM',
                        'reason': f"突破日线中枢上沿 {zs_high:.2f}",
                        'entry': current_price,
                        'stop_loss': zs_high,
                        'target': current_price * 1.08,
                        'confidence': 65,
                        'timestamp': datetime.now().isoformat(),
                    }

            if has_position and min5.get('has_divergence') and min5.get('divergence_type') == '顶背驰':
                return {
                    'type': 'SELL', 'strength': 'STRONG',
                    'reason': f"5分钟顶背驰确认",
                    'entry': current_price,
                    'stop_loss': current_price * 1.03,
                    'target': current_price * 0.95,
                    'confidence': 75,
                    'timestamp': datetime.now().isoformat(),
                }

        # ====== 信号3: 止损 + 风控引擎 ======
        if has_position:
            pos = self.portfolio['positions'][0]
            stop_loss_price = pos.get('stop_loss', 0)

            # 价格止损
            if stop_loss_price and current_price < stop_loss_price:
                return {
                    'type': 'SELL', 'strength': 'STOP_LOSS',
                    'reason': f"跌破止损位 {stop_loss_price:.2f}",
                    'entry': current_price,
                    'confidence': 100,
                    'timestamp': datetime.now().isoformat(),
                }

            # 风控引擎
            risk_alerts = self._check_risk(pos, current_price)
            for alert in risk_alerts:
                if alert.action == 'close_all':
                    return {
                        'type': 'SELL', 'strength': 'RISK',
                        'reason': alert.message,
                        'entry': current_price,
                        'confidence': 95,
                        'timestamp': datetime.now().isoformat(),
                    }
                elif alert.action == 'reduce_half':
                    return {
                        'type': 'REDUCE', 'strength': 'RISK',
                        'reason': alert.message,
                        'entry': current_price,
                        'reduce_pct': 0.5,
                        'confidence': 80,
                        'timestamp': datetime.now().isoformat(),
                    }

        return None

    def _check_risk(self, trade: Dict, current_price: float,
                    zs_range: tuple = None, bars_held: int = 0) -> list:
        """调用风控引擎"""
        if not self.risk_engine:
            return []
        try:
            return self.risk_engine.check_all(trade, current_price, zs_range, bars_held)
        except Exception as e:
            logger.warning(f"风控检查失败: {e}")
            return []
    def execute_signal(self, signal: Dict) -> bool:
        """执行交易信号"""
        if not signal:
            return False

        signal_type = signal['type']
        current_price = signal['entry']

        # 计算仓位大小（固定风险比例）
        account_info = self.client.get_account_info()
        net_value = account_info.get('net_liquid_value', 0)
        risk_per_trade = 0.03  # 3% 风险
        stop_loss_pct = abs(current_price - signal.get('stop_loss', current_price * 0.97)) / current_price

        if stop_loss_pct > 0:
            position_size = int((net_value * risk_per_trade) / (current_price * stop_loss_pct))
            position_size = min(position_size, int(net_value * 0.5 / current_price))  # 最大 50% 仓位
            position_size = max(position_size, 1)  # 最少 1 股
        else:
            position_size = 1

        logger.info(f"📊 信号执行: {signal_type} {position_size} CRCL @ {current_price:.2f}")
        logger.info(f"   原因: {signal['reason']}")
        logger.info(f"   止损: {signal.get('stop_loss', 'N/A')}")
        logger.info(f"   目标: {signal.get('target', 'N/A')}")

        if signal_type == 'BUY':
            order_id = self.client.place_order("CRCL", "BUY", position_size, order_type="MKT")
            if order_id:
                self.portfolio['positions'].append({
                    'symbol': 'CRCL',
                    'quantity': position_size,
                    'entry_price': current_price,
                    'entry_time': datetime.now().isoformat(),
                    'stop_loss': signal.get('stop_loss'),
                    'target': signal.get('target'),
                    'order_id': order_id,
                })
                self.portfolio['trade_log'].append({
                    'type': 'BUY',
                    'symbol': 'CRCL',
                    'quantity': position_size,
                    'price': current_price,
                    'order_id': order_id,
                    'reason': signal['reason'],
                    'timestamp': datetime.now().isoformat(),
                })
                self.save_portfolio()
                logger.info(f"✅ 买入订单已提交: {order_id}")
                return True

        elif signal_type == 'SELL':
            if self.portfolio['positions']:
                pos = self.portfolio['positions'][0]
                quantity = pos['quantity']
                order_id = self.client.place_order("CRCL", "SELL", quantity, order_type="MKT")
                if order_id:
                    pnl = (current_price - pos['entry_price']) * quantity
                    pnl_pct = (current_price / pos['entry_price'] - 1) * 100

                    self.portfolio['trade_log'].append({
                        'type': 'SELL',
                        'symbol': 'CRCL',
                        'quantity': quantity,
                        'price': current_price,
                        'order_id': order_id,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': signal['reason'],
                        'timestamp': datetime.now().isoformat(),
                    })
                    self.portfolio['positions'] = []
                    self.save_portfolio()
                    logger.info(f"✅ 卖出订单已提交: {order_id} | 盈亏: ${pnl:+.2f} ({pnl_pct:+.2f}%)")

                    # 自动反思
                    if self.reflection_engine:
                        try:
                            trade_data = {
                                'symbol': 'CRCL',
                                'direction': 'short',
                                'entry_price': pos['entry_price'],
                                'exit_price': current_price,
                                'pnl': pnl,
                                'pnl_pct': pnl_pct,
                                'signal_type': signal.get('reason', 'N/A'),
                            }
                            reflection = self.reflection_engine.generate_post_trade_reflection(trade_data)
                            logger.info(f"📝 自动反思:\n{reflection}")
                        except Exception as e:
                            logger.warning(f"反思生成失败: {e}")

                    return True

        return False

    def run_once(self):
        """单次扫描"""
        logger.info("="*60)
        logger.info("🐯 CRCL 缠论模拟交易 - 单次扫描")
        logger.info("="*60)

        # 账户信息
        account = self.client.get_account_info()
        logger.info(f"💰 账户净值: ${account.get('net_liquid_value', 0):,.2f}")
        logger.info(f"💰 可用资金: ${account.get('available_funds', 0):,.2f}")

        # 持仓信息
        positions = self.client.get_positions()
        if positions:
            for p in positions:
                logger.info(f"📦 持仓: {p['symbol']} {p['quantity']}股 @ ${p['average_cost']:.2f}")
        else:
            logger.info("📦 当前无持仓")

        # 实时报价 (SmartDataRouter)
        rt_quote = self.client.get_realtime_quote("CRCL")
        if rt_quote:
            rt_tag = "🟢 实时" if rt_quote['is_realtime'] else "🔴 收盘价"
            logger.info(f"\n💡 实时报价: ${rt_quote['price']:.2f} ({rt_quote['change_pct']:+.2f}%) [{rt_tag}] via {rt_quote['provider']}")

        # 缠论分析
        analysis = self.analyze()
        daily = analysis.get('daily', {})
        min5 = analysis.get('min5', {})

        if daily:
            logger.info(f"\n📊 日线分析:")
            logger.info(f"   当前价: ${daily.get('current_price', 0):.2f}")
            logger.info(f"   趋势: {daily.get('trend', 'N/A')}")
            logger.info(f"   笔数量: {daily.get('bi_count', 0)}")
            logger.info(f"   中枢数量: {daily.get('zs_count', 0)}")
            logger.info(f"   最后一笔: {daily.get('last_bi_direction', 'N/A')}")
            if daily.get('last_zs'):
                zs = daily['last_zs']
                logger.info(f"   最新中枢: [{zs['low']:.2f}, {zs['high']:.2f}]")

        if min5:
            logger.info(f"\n📊 5分钟分析:")
            logger.info(f"   当前价: ${min5.get('current_price', 0):.2f}")
            logger.info(f"   趋势: {min5.get('trend', 'N/A')}")
            logger.info(f"   最后一笔: {min5.get('last_bi_direction', 'N/A')}")
            logger.info(f"   背驰: {min5.get('has_divergence', False)} {min5.get('divergence_type', '')}")

        # 生成信号
        signal = self.generate_signal(analysis)
        if signal:
            logger.info(f"\n🔔 交易信号:")
            logger.info(f"   类型: {signal['type']}")
            logger.info(f"   强度: {signal['strength']}")
            logger.info(f"   原因: {signal['reason']}")
            logger.info(f"   信心: {signal['confidence']}%")

            # 自动执行信号
            self.execute_signal(signal)
        else:
            logger.info("\n💤 无交易信号")

        logger.info("="*60)
        return analysis

    def run_loop(self, interval: int = 300):
        """持续监控"""
        logger.info("🔄 启动持续监控模式...")
        while True:
            try:
                self.run_once()
                logger.info(f"⏳ 等待 {interval} 秒后下次扫描...")
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("🛑 用户中断，停止监控")
                break
            except Exception as e:
                logger.error(f"❌ 监控异常: {e}")
                time.sleep(60)  # 出错后等1分钟再试

    def manual_buy(self, quantity: int, price: float = None):
        """手动买入"""
        order_type = "LMT" if price else "MKT"
        order_id = self.client.place_order("CRCL", "BUY", quantity, price, order_type)
        if order_id:
            logger.info(f"✅ 手动买入订单已提交: {order_id}")
            return order_id
        return None

    def manual_sell(self, quantity: int, price: float = None):
        """手动卖出"""
        order_type = "LMT" if price else "MKT"
        order_id = self.client.place_order("CRCL", "SELL", quantity, price, order_type)
        if order_id:
            logger.info(f"✅ 手动卖出订单已提交: {order_id}")
            return order_id
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description='CRCL 缠论模拟交易 - Tiger 模拟盘')
    parser.add_argument('--once', action='store_true', help='单次扫描')
    parser.add_argument('--loop', action='store_true', help='持续监控')
    parser.add_argument('--interval', type=int, default=300, help='监控间隔（秒）')
    parser.add_argument('--buy', type=int, help='手动买入数量')
    parser.add_argument('--sell', type=int, help='手动卖出数量')
    parser.add_argument('--price', type=float, help='限价（配合 --buy/--sell）')
    parser.add_argument('--account', default=SIM_ACCOUNT, help='账户（默认模拟盘）')
    args = parser.parse_args()

    trader = CRCLTrader(args.account)

    if args.buy:
        trader.manual_buy(args.buy, args.price)
    elif args.sell:
        trader.manual_sell(args.sell, args.price)
    elif args.loop:
        trader.run_loop(args.interval)
    else:
        trader.run_once()


if __name__ == "__main__":
    main()
