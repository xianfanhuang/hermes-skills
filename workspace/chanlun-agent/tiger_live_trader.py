#!/usr/bin/env python3
"""
Tiger Live Trader - Tiger模拟账户真实下单版本

功能：
1. 实时获取多周期K线
2. 缠论分析 + 信号生成
3. Tiger模拟账户真实下单
4. 持仓监控 + 自动平仓
5. 风控引擎

Author: Trading Assistant
Version: 1.0.0
"""

import sys
import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 项目路径
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR / "data"))
sys.path.insert(0, str(PROJECT_DIR / "paper-trading"))

from czsc import CZSC, RawBar, Freq
from czsc_extension import CzscExtension
from crcl_tiger_trader import TigerClient, create_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_DIR / "paper-trading" / "tiger_live.log", encoding='utf-8'),
    ]
)
logger = logging.getLogger("TigerLive")

# ==================== 配置 ====================

CONFIG = {
    'symbol': 'SOXS',
    'direction': 'auto',
    'risk_per_trade': 0.02,  # 杠杆ETF，风险降低到2%
    'max_position_pct': 0.30,  # 最大仓位30%
    'stop_loss_pct': 0.04,  # 止损4%
    'time_stop_bars': 12,
    'scan_interval': 300,
}

REPORTS_DIR = PROJECT_DIR / "reports" / "tiger_live"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class TigerLiveTrader:
    """Tiger 模拟账户真实交易"""

    def __init__(self, config: dict):
        self.config = config
        self.symbol = config['symbol']
        self.tiger_client = TigerClient()
        self.data_router = create_router()
        self.in_position = False
        self.position_info = None

        logger.info(f"🐯 Tiger Live Trader 初始化完成")
        logger.info(f"  品种: {self.symbol}")
        logger.info(f"  模式: Tiger模拟账户真实下单")

    def get_account_status(self):
        """获取账户状态"""
        account = self.tiger_client.get_account_info()
        positions = self.tiger_client.get_positions()

        # 检查是否有该品种的持仓
        for p in positions:
            if p.get('symbol') == self.symbol:
                self.in_position = True
                self.position_info = p
                return {
                    'has_position': True,
                    'quantity': p.get('quantity', 0),
                    'avg_cost': p.get('average_cost', 0),
                    'available_funds': account.get('available_funds', 0),
                }

        self.in_position = False
        self.position_info = None
        return {
            'has_position': False,
            'available_funds': account.get('available_funds', 0),
        }

    def get_klines(self, timeframe: str, limit: int = 200):
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
            if len(bars) < 50:
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
                    'summary': analysis.get('summary', ''),
                }
                logger.info(f"  {tf}: {results[tf]['bi_count']}笔 {results[tf]['zs_count']}中枢 | {results[tf]['direction']}")
            except Exception as e:
                logger.warning(f"  {tf}: 分析失败 - {e}")

        return results

    def determine_direction(self, analysis: dict) -> str:
        """确定交易方向"""
        daily = analysis.get('daily', {})
        m30 = analysis.get('30min', {})
        m5 = analysis.get('5min', {})

        daily_dir = daily.get('direction', 'unknown')
        m30_dir = m30.get('direction', 'unknown')

        # SOXS 是做空ETF，方向相反
        # 做多SOXS = 看空半导体
        if daily_dir == 'up' and m30_dir in ('up', 'neutral'):
            return 'long'  # 做多SOXS（看空半导体）
        elif daily_dir == 'down' and m30_dir in ('down', 'neutral'):
            return 'short'  # 做空SOXS（看多半导体）

        return 'none'

    def check_resonance(self, analysis: dict) -> tuple:
        """检查共振"""
        daily = analysis.get('daily', {})
        m30 = analysis.get('30min', {})
        m5 = analysis.get('5min', {})

        daily_dir = daily.get('direction', 'unknown')
        m30_dir = m30.get('direction', 'unknown')
        m5_dir = m5.get('direction', 'unknown')

        if daily_dir == m30_dir == 'up':
            return True, 2, "日线+30分钟共振向上"
        elif daily_dir == 'up':
            return True, 1, "日线向上"

        return False, 0, "无共振"

    def calculate_position_size(self, entry_price: float, stop_loss: float, available_funds: float) -> int:
        """计算仓位"""
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            return 0

        risk_amount = available_funds * self.config['risk_per_trade']
        quantity = int(risk_amount / risk_per_share)
        max_quantity = int(available_funds * self.config['max_position_pct'] / entry_price)

        return min(quantity, max_quantity)

    def place_buy_order(self, quantity: int, price: float):
        """下买单"""
        try:
            result = self.tiger_client.place_order(self.symbol, 'BUY', quantity, price, 'MKT')
            if result:
                logger.info(f"🟢 买单已提交: {self.symbol} x {quantity} @ ${price:.2f}")
                logger.info(f"   订单ID: {result}")
                return True
            else:
                logger.error(f"❌ 买单失败")
                return False
        except Exception as e:
            logger.error(f"❌ 买单异常: {e}")
            return False

    def place_sell_order(self, quantity: int):
        """下卖单"""
        try:
            result = self.tiger_client.place_order(self.symbol, 'SELL', quantity, None, 'MKT')
            if result:
                logger.info(f"🔴 卖单已提交: {self.symbol} x {quantity}")
                logger.info(f"   订单ID: {result}")
                return True
            else:
                logger.error(f"❌ 卖单失败")
                return False
        except Exception as e:
            logger.error(f"❌ 卖单异常: {e}")
            return False

    def run_once(self):
        """单次扫描"""
        now = datetime.now()
        logger.info("=" * 60)
        logger.info(f"📊 Tiger Live Scan | {now.strftime('%Y-%m-%d %H:%M:%S')} | {self.symbol}")

        # 获取账户状态
        account_status = self.get_account_status()
        logger.info(f"   可用资金: ${account_status['available_funds']:,.2f}")
        logger.info(f"   持仓状态: {'有' if account_status['has_position'] else '无'}")

        if account_status['has_position']:
            logger.info(f"   持仓: {account_status['quantity']}股 @ ${account_status['avg_cost']:.2f}")

        # 获取当前价格
        try:
            quote = self.data_router.get_quote(self.symbol)
            current_price = quote.price if quote and hasattr(quote, 'price') else None
        except:
            current_price = None

        if not current_price:
            logger.warning("无法获取当前价格")
            return

        logger.info(f"   当前价: ${current_price:.2f}")

        # 多周期分析
        analysis = self.analyze_all_timeframes()

        # 确定方向
        direction = self.determine_direction(analysis)
        logger.info(f"   建议方向: {direction}")

        # 检查共振
        is_resonance, level, reason = self.check_resonance(analysis)
        logger.info(f"   共振状态: {reason}")

        # 有持仓时检查是否需要平仓
        if account_status['has_position']:
            # 方向反转时平仓
            if (account_status['quantity'] > 0 and direction == 'short') or \
               (account_status['quantity'] < 0 and direction == 'long'):
                logger.info(f"🔄 方向反转，平仓")
                self.place_sell_order(abs(account_status['quantity']))
            else:
                logger.info(f"   方向一致，持仓不动")
            return

        # 无持仓，寻找入场机会
        if direction == 'none' or not is_resonance:
            logger.info("   无交易信号")
            return

        # 计算止损和仓位
        if direction == 'long':
            stop_loss = current_price * (1 - self.config['stop_loss_pct'])
        else:
            stop_loss = current_price * (1 + self.config['stop_loss_pct'])

        quantity = self.calculate_position_size(
            current_price, stop_loss, account_status['available_funds']
        )

        if quantity <= 0:
            logger.warning("   仓位计算为0，跳过")
            return

        # 执行下单
        logger.info(f"🎯 信号触发: {reason}")
        logger.info(f"   方向: {direction.upper()}")
        logger.info(f"   价格: ${current_price:.2f}")
        logger.info(f"   止损: ${stop_loss:.2f}")
        logger.info(f"   数量: {quantity}")

        if direction == 'long':
            self.place_buy_order(quantity, current_price)
        else:
            # 做空需要先检查是否支持
            logger.info("   做空订单暂不支持（需确认融券）")

    def run_loop(self, interval: int = 300):
        """持续运行"""
        logger.info(f"🚀 启动 Tiger Live 交易")
        logger.info(f"   品种: {self.symbol}")
        logger.info(f"   扫描间隔: {interval}秒")
        logger.info(f"   Ctrl+C 停止")

        while True:
            try:
                self.run_once()
                logger.info(f"   下次扫描: {interval}秒后")
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("⏹️ 用户停止")
                break
            except Exception as e:
                logger.error(f"扫描异常: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)


# ==================== CLI ====================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tiger Live Trader")
    parser.add_argument("--symbol", "-s", default="SOXS", help="品种代码")
    parser.add_argument("--interval", "-i", type=int, default=300, help="扫描间隔(秒)")
    parser.add_argument("--once", action="store_true", help="单次扫描")

    args = parser.parse_args()

    config = CONFIG.copy()
    config['symbol'] = args.symbol
    config['scan_interval'] = args.interval

    trader = TigerLiveTrader(config)

    if args.once:
        trader.run_once()
    else:
        trader.run_loop(args.interval)
