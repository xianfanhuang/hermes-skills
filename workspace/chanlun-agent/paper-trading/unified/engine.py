#!/usr/bin/env python3
"""
统一交易引擎

一套系统，多标的。配置驱动，不改代码。

核心模块：
- 数据获取：Finnhub(美股) / Tiger(港股)
- 缠论分析：笔/中枢/背驰/买卖点
- 信号生成：多级别共振
- 风控管理：三层止损
- 下单执行：老虎模拟盘
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
            # 解析Tiger返回的字符串
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
                            # 格式: "-0.24 (-0.80%)"
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
            'bi_count': 0,
            'zs_count': 0,
            'last_zs': None,
            'divergence': None,
            'buy_sell_points': [],
            'structure_state': 'unknown'
        }

# ============ 风控引擎 ============

class RiskEngine:
    """风控管理"""

    def __init__(self, config: Dict):
        self.config = config
        self.daily_pnl = 0
        self.consecutive_losses = 0

    def check_position_size(self, price: float, quantity: int, account_value: float) -> bool:
        """检查仓位大小"""
        position_value = price * quantity
        max_position = account_value * 0.5  # 最大50%仓位
        return position_value <= max_position

    def check_daily_loss(self, pnl: float) -> bool:
        """检查日亏损限制"""
        return abs(self.daily_pnl + pnl) <= self.config.get('max_daily_loss_pct', 0.06) * 1000000

    def update_pnl(self, pnl: float):
        """更新盈亏"""
        self.daily_pnl += pnl
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

# ============ 交易引擎 ============

class TradingEngine:
    """统一交易引擎"""

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

        analysis = self.chanlun.analyze(symbol, market, quote)
        analysis['quote'] = quote
        return analysis

    def generate_signal(self, symbol: str, analysis: Dict) -> Optional[TradeSignal]:
        """生成交易信号"""
        # 这里实现信号生成逻辑
        # 基于缠论分析结果
        return None

    def execute_trade(self, signal: TradeSignal) -> bool:
        """执行交易"""
        try:
            action = 'BUY' if signal.action == 'BUY' else 'SELL'
            result = place_order_limit(
                symbol=signal.symbol,
                price=signal.price,
                quantity=signal.quantity,
                action=action
            )
            logger.info(f"✅ 交易执行: {signal.symbol} {signal.action} {signal.quantity}股 @ ${signal.price:.2f}")
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

    def check_exit(self, symbol: str, analysis: Dict) -> Optional[Dict]:
        """检查是否需要平仓"""
        pos = self.portfolio.get('positions', {}).get(symbol, {})
        if not pos or pos.get('position', 0) == 0:
            return None

        # 这里实现止损止盈检查逻辑
        return None

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

            # 检查平仓
            exit_info = self.check_exit(symbol, analysis)
            if exit_info:
                self.execute_exit(symbol, exit_info)
                continue

            # 检查入场
            signal = self.generate_signal(symbol, analysis)
            if signal:
                self.execute_trade(signal)

    def execute_exit(self, symbol: str, exit_info: Dict) -> bool:
        """执行平仓"""
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
        # 从配置中获取市场
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
