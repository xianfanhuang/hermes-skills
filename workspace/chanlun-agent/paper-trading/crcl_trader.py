#!/usr/bin/env python3
"""
CRCL 缠论自主交易系统

特性:
- 缠论一二三类买卖点识别
- 考夫曼自适应均线 (KAMA) 趋势过滤
- 力度对比背驰判断
- ATR跟踪止损
- 自主执行模拟交易

使用方式:
    python3 crcl_trader.py --once     # 单次扫描
    python3 crcl_trader.py --loop     # 持续监控
"""

import sys
import json
import time
import numpy as np
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from chanlun_perception import ChanlunPerception

# ============================================================
# 数据结构
# ============================================================

@dataclass
class KAMAState:
    """考夫曼自适应均线状态"""
    value: float
    direction: float  # 方向
    efficiency_ratio: float  # 效率比
    smoothing_constant: float  # 平滑常数
    trend: str  # up/down/flat

@dataclass
class StrengthRatio:
    """力度对比"""
    amplitude_ratio: float  # 幅度比
    velocity_ratio: float  # 速度比
    volume_ratio: float  # 成交量比
    composite: float  # 综合力度比
    signal: str  # strong_divergence/weak_divergence/consolidation/trend_continue

@dataclass
class BuySellPoint:
    """买卖点"""
    type: str  # buy1/buy2/buy3/sell1/sell2/sell3
    price: float
    confidence: float  # 0-100
    strength_ratio: float
    kama_trend: str
    reason: str
    timestamp: str

@dataclass
class Position:
    """持仓"""
    symbol: str
    direction: str  # long/short
    entry_price: float
    shares: int
    cost: float
    stop_loss: float
    trailing_stop: float
    target: float
    entry_time: str
    entry_reason: str
    max_price: float  # 持仓期间最高价（多头）
    min_price: float  # 持仓期间最低价（空头）

@dataclass
class Portfolio:
    """账户"""
    initial_capital: float
    cash: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    positions: List[Position]
    trade_log: List[Dict]
    kama_state: Optional[KAMAState]
    last_update: str

# ============================================================
# KAMA 计算
# ============================================================

class KAMACalculator:
    """考夫曼自适应均线"""
    
    def __init__(self, period: int = 10, fast_sc: float = 0.6667, slow_sc: float = 0.0645):
        self.period = period
        self.fast_sc = fast_sc
        self.slow_sc = slow_sc
        self.prev_kama = None
        self.prices = []
    
    def update(self, price: float) -> KAMAState:
        """更新KAMA"""
        self.prices.append(price)
        
        if len(self.prices) < self.period + 1:
            # 数据不足，使用SMA
            self.prev_kama = np.mean(self.prices)
            return KAMAState(
                value=self.prev_kama,
                direction=0,
                efficiency_ratio=0,
                smoothing_constant=0,
                trend='flat'
            )
        
        # 计算方向（价格变化）
        direction = abs(price - self.prices[-self.period - 1])
        
        # 计算波动率（价格路径）
        volatility = sum(abs(self.prices[i] - self.prices[i-1]) 
                        for i in range(-self.period, 0))
        
        # 效率比
        er = direction / volatility if volatility > 0 else 0
        
        # 平滑常数
        sc = (er * (self.fast_sc - self.slow_sc) + self.slow_sc) ** 2
        
        # KAMA
        if self.prev_kama is None:
            self.prev_kama = price
        kama = self.prev_kama + sc * (price - self.prev_kama)
        
        # 趋势判断
        trend = 'up' if kama > self.prev_kama else ('down' if kama < self.prev_kama else 'flat')
        
        state = KAMAState(
            value=kama,
            direction=price - self.prev_kama,
            efficiency_ratio=er,
            smoothing_constant=sc,
            trend=trend
        )
        
        self.prev_kama = kama
        return state

# ============================================================
# 力度对比计算
# ============================================================

class StrengthAnalyzer:
    """力度对比分析"""
    
    @staticmethod
    def calculate_ratio(current_amplitude: float, current_velocity: float, current_volume: float,
                       prev_amplitude: float, prev_velocity: float, prev_volume: float) -> StrengthRatio:
        """计算力度比"""
        amp_ratio = current_amplitude / prev_amplitude if prev_amplitude > 0 else 1
        vel_ratio = current_velocity / prev_velocity if prev_velocity > 0 else 1
        vol_ratio = current_volume / prev_volume if prev_volume > 0 else 1
        
        # 综合力度比（加权平均）
        composite = amp_ratio * 0.5 + vel_ratio * 0.3 + vol_ratio * 0.2
        
        # 信号判断
        if composite < 0.7:
            signal = 'strong_divergence'
        elif composite < 0.9:
            signal = 'weak_divergence'
        elif composite < 1.1:
            signal = 'consolidation'
        else:
            signal = 'trend_continue'
        
        return StrengthRatio(
            amplitude_ratio=amp_ratio,
            velocity_ratio=vel_ratio,
            volume_ratio=vol_ratio,
            composite=composite,
            signal=signal
        )

# ============================================================
# 买卖点识别
# ============================================================

class BuySellPointDetector:
    """买卖点识别器"""
    
    def __init__(self):
        self.strength_analyzer = StrengthAnalyzer()
    
    def detect(self, structures: Dict, kama_state: KAMAState, 
               strength_ratio: Optional[StrengthRatio] = None) -> List[BuySellPoint]:
        """检测买卖点"""
        points = []
        
        daily = structures.get('日线')
        if not daily:
            return points
        
        # 第一类买点：底背驰
        if daily.trend == 'down' and daily.divergence:
            if strength_ratio and strength_ratio.signal == 'strong_divergence':
                points.append(BuySellPoint(
                    type='buy1',
                    price=0,  # 需要实时价格
                    confidence=80,
                    strength_ratio=strength_ratio.composite,
                    kama_trend=kama_state.trend,
                    reason=f'日线底背驰，力度比{strength_ratio.composite:.2f}',
                    timestamp=datetime.now().isoformat()
                ))
        
        # 第二类买点：回调不破前低
        if daily.trend == 'up' and daily.last_bi_direction == '向上':
            if kama_state.trend == 'up' and kama_state.efficiency_ratio > 0.3:
                points.append(BuySellPoint(
                    type='buy2',
                    price=0,
                    confidence=70,
                    strength_ratio=strength_ratio.composite if strength_ratio else 1,
                    kama_trend=kama_state.trend,
                    reason=f'上升趋势回调，KAMA向上，ER={kama_state.efficiency_ratio:.2f}',
                    timestamp=datetime.now().isoformat()
                ))
        
        # 第三类买点：突破中枢回踩不破
        if daily.last_zs_range:
            zs_high = daily.last_zs_range[1]
            # 价格突破中枢上沿
            # 需要实时价格判断
        
        # 第一类卖点：顶背驰
        if daily.trend == 'up' and daily.divergence:
            if strength_ratio and strength_ratio.signal == 'strong_divergence':
                points.append(BuySellPoint(
                    type='sell1',
                    price=0,
                    confidence=80,
                    strength_ratio=strength_ratio.composite,
                    kama_trend=kama_state.trend,
                    reason=f'日线顶背驰，力度比{strength_ratio.composite:.2f}',
                    timestamp=datetime.now().isoformat()
                ))
        
        # 第二类卖点：反弹不破前高
        if daily.trend == 'down' and daily.last_bi_direction == '向下':
            if kama_state.trend == 'down':
                points.append(BuySellPoint(
                    type='sell2',
                    price=0,
                    confidence=70,
                    strength_ratio=strength_ratio.composite if strength_ratio else 1,
                    kama_trend=kama_state.trend,
                    reason=f'下降趋势反弹，KAMA向下',
                    timestamp=datetime.now().isoformat()
                ))
        
        return points

# ============================================================
# 交易引擎
# ============================================================

class TradingEngine:
    """交易引擎"""
    
    def __init__(self, symbol: str, initial_capital: float = 10000):
        self.symbol = symbol
        self.perception = ChanlunPerception()
        self.kama = KAMACalculator(period=10)
        self.detector = BuySellPointDetector()
        self.portfolio = Portfolio(
            initial_capital=initial_capital,
            cash=initial_capital,
            equity=initial_capital,
            realized_pnl=0,
            unrealized_pnl=0,
            positions=[],
            trade_log=[],
            kama_state=None,
            last_update=datetime.now().isoformat()
        )
        self.price_history = []
        self.atr_period = 14
        self.atr_multiplier = 2.0
        self.portfolio_path = Path(__file__).parent / "crcl_portfolio_live.json"
    
    def calculate_atr(self, prices: List[float], period: int = 14) -> float:
        """计算ATR"""
        if len(prices) < period + 1:
            return 0
        
        true_ranges = []
        for i in range(-period, 0):
            high_low = abs(prices[i] - prices[i-1])
            true_ranges.append(high_low)
        
        return np.mean(true_ranges)
    
    def update_trailing_stop(self, current_price: float):
        """更新跟踪止损"""
        for pos in self.portfolio.positions:
            if pos.direction == 'long':
                # 多头：更新最高价，跟踪止损上移
                if current_price > pos.max_price:
                    pos.max_price = current_price
                    atr = self.calculate_atr(self.price_history)
                    new_stop = current_price - atr * self.atr_multiplier
                    if new_stop > pos.trailing_stop:
                        pos.trailing_stop = new_stop
                        print(f'  📈 跟踪止损上移: ${pos.trailing_stop:.2f}')
            
            elif pos.direction == 'short':
                # 空头：更新最低价，跟踪止损下移
                if current_price < pos.min_price:
                    pos.min_price = current_price
                    atr = self.calculate_atr(self.price_history)
                    new_stop = current_price + atr * self.atr_multiplier
                    if new_stop < pos.trailing_stop:
                        pos.trailing_stop = new_stop
                        print(f'  📉 跟踪止损下移: ${pos.trailing_stop:.2f}')
    
    def check_stop_loss(self, current_price: float) -> Optional[str]:
        """检查止损"""
        for pos in self.portfolio.positions:
            if pos.direction == 'long':
                if current_price <= pos.trailing_stop:
                    return 'stop_loss_long'
            elif pos.direction == 'short':
                if current_price >= pos.trailing_stop:
                    return 'stop_loss_short'
        return None
    
    def execute_buy(self, price: float, reason: str, buy_type: str):
        """执行买入"""
        # 计算仓位（风险3%）
        risk_pct = 0.03
        atr = self.calculate_atr(self.price_history)
        stop_loss = price - atr * self.atr_multiplier
        
        risk_per_share = price - stop_loss
        if risk_per_share <= 0:
            risk_per_share = price * 0.03
        
        max_risk = self.portfolio.equity * risk_pct
        shares = int(max_risk / risk_per_share) if risk_per_share > 0 else 0
        shares = min(shares, int(self.portfolio.cash / price))
        
        if shares <= 0:
            print(f'  ❌ 资金不足，无法买入')
            return
        
        cost = shares * price
        self.portfolio.cash -= cost
        
        position = Position(
            symbol=self.symbol,
            direction='long',
            entry_price=price,
            shares=shares,
            cost=cost,
            stop_loss=stop_loss,
            trailing_stop=stop_loss,
            target=price * 1.06,
            entry_time=datetime.now().isoformat(),
            entry_reason=reason,
            max_price=price,
            min_price=price
        )
        self.portfolio.positions.append(position)
        
        trade = {
            'time': datetime.now().isoformat(),
            'action': 'BUY',
            'type': buy_type,
            'price': price,
            'shares': shares,
            'cost': cost,
            'stop_loss': stop_loss,
            'reason': reason
        }
        self.portfolio.trade_log.append(trade)
        
        print(f'\n🟢 买入 {buy_type}:')
        print(f'  价格: ${price:.2f}')
        print(f'  数量: {shares} 股')
        print(f'  成本: ${cost:.2f}')
        print(f'  止损: ${stop_loss:.2f}')
        print(f'  目标: ${price * 1.06:.2f}')
        print(f'  原因: {reason}')
    
    def execute_sell(self, price: float, reason: str, sell_type: str):
        """执行卖出"""
        if not self.portfolio.positions:
            print(f'  ❌ 无持仓可卖')
            return
        
        pos = self.portfolio.positions[0]
        proceeds = pos.shares * price
        pnl = proceeds - pos.cost
        pnl_pct = ((price - pos.entry_price) / pos.entry_price) * 100
        
        self.portfolio.cash += proceeds
        self.portfolio.realized_pnl += pnl
        self.portfolio.positions.remove(pos)
        
        trade = {
            'time': datetime.now().isoformat(),
            'action': 'SELL',
            'type': sell_type,
            'price': price,
            'shares': pos.shares,
            'proceeds': proceeds,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason
        }
        self.portfolio.trade_log.append(trade)
        
        emoji = '🔴' if pnl < 0 else '🟢'
        print(f'\n{emoji} 卖出 {sell_type}:')
        print(f'  价格: ${price:.2f}')
        print(f'  数量: {pos.shares} 股')
        print(f'  盈亏: ${pnl:.2f} ({pnl_pct:+.2f}%)')
        print(f'  原因: {reason}')
    
    def analyze_and_trade(self):
        """分析并交易"""
        print(f'\n{"="*60}')
        print(f'📊 {self.symbol} 缠论自主交易')
        print(f'⏰ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        print(f'{"="*60}')
        
        # 获取行情
        quote = self.perception.get_quote(self.symbol, 'US')
        if not quote:
            print('❌ 获取行情失败')
            return
        
        current_price = quote.get('price', 0)
        if current_price <= 0:
            print('❌ 价格无效')
            return
        
        print(f'\n💰 当前价格: ${current_price:.2f}')
        
        # 更新价格历史
        self.price_history.append(current_price)
        
        # 更新KAMA
        kama_state = self.kama.update(current_price)
        self.portfolio.kama_state = kama_state
        print(f'📈 KAMA: ${kama_state.value:.2f} (趋势: {kama_state.trend}, ER: {kama_state.efficiency_ratio:.2f})')
        
        # 缠论分析
        structures = self.perception.analyze_symbol(self.symbol, 'US', ['日线'])
        daily = structures.get('日线')
        
        if daily:
            print(f'\n📉 日线结构:')
            print(f'  趋势: {daily.trend}')
            print(f'  笔: {daily.bi_count} | 中枢: {daily.zs_count}')
            if daily.last_zs_range:
                print(f'  中枢区间: [{daily.last_zs_range[0]:.2f}, {daily.last_zs_range[1]:.2f}]')
            print(f'  最后一笔: {daily.last_bi_direction}')
            print(f'  背驰: {"是 ⚠️" if daily.divergence else "否"}')
        
        # 检查止损
        stop_signal = self.check_stop_loss(current_price)
        if stop_signal:
            print(f'\n⚠️ 触发止损: {stop_signal}')
            self.execute_sell(current_price, f'触发跟踪止损 ${self.portfolio.positions[0].trailing_stop:.2f}', 'trailing_stop')
            self.save_portfolio()
            return
        
        # 更新跟踪止损
        self.update_trailing_stop(current_price)
        
        # 检测买卖点
        points = self.detector.detect(structures, kama_state)
        
        # 执行交易
        has_position = len(self.portfolio.positions) > 0
        
        for point in points:
            point.price = current_price
            
            if point.type.startswith('buy') and not has_position:
                # 买入条件：KAMA趋势向上 + 缠论买点
                if kama_state.trend == 'up' and kama_state.efficiency_ratio > 0.2:
                    self.execute_buy(current_price, point.reason, point.type)
                    has_position = True
                    break
                elif point.confidence >= 80:
                    # 高置信度买点，忽略KAMA
                    self.execute_buy(current_price, point.reason, point.type)
                    has_position = True
                    break
            
            elif point.type.startswith('sell') and has_position:
                # 卖出条件：缠论卖点
                if point.confidence >= 70:
                    self.execute_sell(current_price, point.reason, point.type)
                    has_position = False
                    break
        
        # 无信号时的状态
        if not points:
            print(f'\n📡 信号: 无明确买卖点，继续观察')
        
        # 更新权益
        if self.portfolio.positions:
            pos = self.portfolio.positions[0]
            self.portfolio.unrealized_pnl = (current_price - pos.entry_price) * pos.shares
        else:
            self.portfolio.unrealized_pnl = 0
        
        self.portfolio.equity = self.portfolio.cash + self.portfolio.unrealized_pnl
        self.portfolio.last_update = datetime.now().isoformat()
        
        # 打印账户状态
        print(f'\n💰 账户:')
        print(f'  权益: ${self.portfolio.equity:.2f}')
        print(f'  可用: ${self.portfolio.cash:.2f}')
        print(f'  持仓盈亏: ${self.portfolio.unrealized_pnl:.2f}')
        print(f'  已实现盈亏: ${self.portfolio.realized_pnl:.2f}')
        
        if self.portfolio.positions:
            pos = self.portfolio.positions[0]
            pnl = (current_price - pos.entry_price) * pos.shares
            pnl_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100
            print(f'\n💼 持仓:')
            print(f'  方向: {pos.direction}')
            print(f'  入场价: ${pos.entry_price:.2f}')
            print(f'  当前盈亏: ${pnl:.2f} ({pnl_pct:+.2f}%)')
            print(f'  跟踪止损: ${pos.trailing_stop:.2f}')
            print(f'  目标: ${pos.target:.2f}')
        
        # 保存
        self.save_portfolio()
    
    def save_portfolio(self):
        """保存账户"""
        data = {
            'initial_capital': self.portfolio.initial_capital,
            'cash': self.portfolio.cash,
            'equity': self.portfolio.equity,
            'realized_pnl': self.portfolio.realized_pnl,
            'unrealized_pnl': self.portfolio.unrealized_pnl,
            'positions': [asdict(p) for p in self.portfolio.positions],
            'trade_log': self.portfolio.trade_log[-50:],  # 保留最近50条
            'kama_state': asdict(self.portfolio.kama_state) if self.portfolio.kama_state else None,
            'last_update': self.portfolio.last_update
        }
        
        with open(self.portfolio_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_portfolio(self):
        """加载账户"""
        if self.portfolio_path.exists():
            with open(self.portfolio_path, 'r') as f:
                data = json.load(f)
            
            self.portfolio.initial_capital = data.get('initial_capital', 10000)
            self.portfolio.cash = data.get('cash', 10000)
            self.portfolio.equity = data.get('equity', 10000)
            self.portfolio.realized_pnl = data.get('realized_pnl', 0)
            self.portfolio.unrealized_pnl = data.get('unrealized_pnl', 0)
            self.portfolio.trade_log = data.get('trade_log', [])
            self.portfolio.last_update = data.get('last_update', '')
            
            # 加载持仓
            self.portfolio.positions = []
            for pos_data in data.get('positions', []):
                self.portfolio.positions.append(Position(**pos_data))
            
            # 加载KAMA状态
            kama_data = data.get('kama_state')
            if kama_data:
                self.portfolio.kama_state = KAMAState(**kama_data)
                self.kama.prev_kama = kama_data.get('value')

# ============================================================
# 主程序
# ============================================================

def run_once():
    """单次扫描"""
    engine = TradingEngine('CRCL')
    engine.load_portfolio()
    engine.analyze_and_trade()

def run_loop(interval: int = 300):
    """持续监控"""
    print('🚀 启动 CRCL 缠论自主交易系统...')
    print(f'   扫描间隔: {interval}秒')
    print(f'   KAMA周期: 10')
    print(f'   ATR跟踪止损: 2倍ATR')
    print(f'   仓位风险: 3%')
    print('   按 Ctrl+C 停止')
    
    engine = TradingEngine('CRCL')
    engine.load_portfolio()
    
    while True:
        try:
            engine.analyze_and_trade()
            print(f'\n⏳ 下次扫描: {interval}秒后...')
            time.sleep(interval)
        except KeyboardInterrupt:
            print('\n🛑 交易系统已停止')
            break
        except Exception as e:
            print(f'\n❌ 错误: {e}')
            import traceback
            traceback.print_exc()
            time.sleep(60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CRCL 缠论自主交易系统")
    parser.add_argument("--once", action="store_true", help="单次扫描")
    parser.add_argument("--loop", action="store_true", help="持续监控")
    parser.add_argument("--interval", type=int, default=300, help="扫描间隔（秒）")
    
    args = parser.parse_args()
    
    if args.loop:
        run_loop(args.interval)
    else:
        run_once()
