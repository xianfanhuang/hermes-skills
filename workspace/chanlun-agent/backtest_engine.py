#!/usr/bin/env python3
"""
BacktestEngine - 回测→反思→改进闭环

功能：
1. 历史数据回测缠论策略
2. 自动反思每笔交易
3. 生成参数优化建议
4. 更新 RGB 知识库

Author: Trading Assistant
Version: 1.0.0
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("BacktestEngine")

# 项目根目录
PROJECT_DIR = Path(__file__).parent
REPORTS_DIR = PROJECT_DIR / "reports" / "backtest"


class BacktestResult:
    """回测结果"""

    def __init__(self):
        self.trades: List[Dict] = []
        self.equity_curve: List[float] = []
        self.initial_capital: float = 10000
        self.final_capital: float = 10000
        self.max_drawdown: float = 0
        self.win_rate: float = 0
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.avg_win: float = 0
        self.avg_loss: float = 0
        self.profit_factor: float = 0
        self.sharpe_ratio: float = 0
        self.start_date: str = ""
        self.end_date: str = ""
        self.symbol: str = ""
        self.strategy: str = ""

    def calculate_stats(self):
        """计算统计数据"""
        self.total_trades = len(self.trades)
        if self.total_trades == 0:
            return

        wins = [t for t in self.trades if t.get('pnl', 0) > 0]
        losses = [t for t in self.trades if t.get('pnl', 0) <= 0]

        self.winning_trades = len(wins)
        self.losing_trades = len(losses)
        self.win_rate = self.winning_trades / self.total_trades

        self.avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        self.avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0

        total_win = sum(t['pnl'] for t in wins)
        total_loss = abs(sum(t['pnl'] for t in losses))
        self.profit_factor = total_win / total_loss if total_loss > 0 else float('inf')

        # 最大回撤
        if self.equity_curve:
            peak = self.equity_curve[0]
            max_dd = 0
            for eq in self.equity_curve:
                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak
                if dd > max_dd:
                    max_dd = dd
            self.max_drawdown = max_dd

        self.final_capital = self.equity_curve[-1] if self.equity_curve else self.initial_capital

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'strategy': self.strategy,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_capital': self.initial_capital,
            'final_capital': round(self.final_capital, 2),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate * 100, 1),
            'avg_win': round(self.avg_win, 2),
            'avg_loss': round(self.avg_loss, 2),
            'profit_factor': round(self.profit_factor, 2),
            'max_drawdown': round(self.max_drawdown * 100, 2),
            'trades': self.trades[-20:],  # 只保留最近20笔
        }


class BacktestEngine:
    """回测引擎"""

    def __init__(self, initial_capital: float = 10000, risk_per_trade: float = 0.03):
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def run_backtest(self, symbol: str, bars_list: list,
                     strategy_name: str = "czsc_extension") -> BacktestResult:
        """
        运行回测

        Args:
            symbol: 品种代码
            bars_list: RawBar 列表
            strategy_name: 策略名称

        Returns:
            BacktestResult
        """
        from czsc import CZSC
        import sys
        sys.path.insert(0, str(PROJECT_DIR / "data"))
        from czsc_extension import CzscExtension

        result = BacktestResult()
        result.symbol = symbol
        result.strategy = strategy_name
        result.initial_capital = self.initial_capital

        capital = self.initial_capital
        position = None  # {entry_price, quantity, entry_idx, direction}
        equity_curve = [capital]

        # 逐根K线回测
        window = 100  # czsc 需要至少100根K线来计算
        for i in range(window, len(bars_list)):
            # 获取历史窗口
            window_bars = bars_list[i - window:i + 1]
            current_bar = bars_list[i]
            current_price = current_bar.close

            # czsc 分析
            try:
                ka = CZSC(window_bars)
                ext = CzscExtension(ka, symbol=symbol, timeframe='daily')
                analysis = ext.analyze_all()
            except Exception:
                equity_curve.append(capital)
                continue

            best_signal = analysis.get('best_signal')

            # 持仓管理
            if position is None:
                # 无持仓，寻找买入信号
                if best_signal and best_signal.get('direction') == 'LONG':
                    # 计算仓位
                    stop_loss = best_signal.get('stop_loss', current_price * 0.97)
                    risk_per_share = abs(current_price - stop_loss)
                    if risk_per_share > 0:
                        risk_amount = capital * self.risk_per_trade
                        quantity = int(risk_amount / risk_per_share)
                        quantity = min(quantity, int(capital * 0.5 / current_price))
                        quantity = max(quantity, 1)

                        position = {
                            'entry_price': current_price,
                            'quantity': quantity,
                            'entry_idx': i,
                            'direction': 'long',
                            'stop_loss': stop_loss,
                            'signal_type': best_signal.get('type', 'unknown'),
                            'signal_reason': best_signal.get('reason', ''),
                            'signal_strength': best_signal.get('strength', 0),
                        }

            else:
                # 有持仓，检查卖出条件
                should_sell = False
                sell_reason = ""

                # 1. 止损
                if current_price < position['stop_loss']:
                    should_sell = True
                    sell_reason = f"止损触发 ({position['stop_loss']:.2f})"

                # 2. 持仓超过20根K线（时间止损）
                elif i - position['entry_idx'] > 20:
                    if current_price <= position['entry_price']:
                        should_sell = True
                        sell_reason = f"时间止损 ({i - position['entry_idx']}根K线)"

                # 3. 信号反转
                elif best_signal and best_signal.get('direction') == 'SHORT':
                    should_sell = True
                    sell_reason = "信号反转"

                # 4. 目标止盈（如果信号设置了目标）
                elif best_signal and best_signal.get('target'):
                    target = best_signal['target']
                    if current_price >= target:
                        should_sell = True
                        sell_reason = f"达到目标 {target:.2f}"

                if should_sell:
                    pnl = (current_price - position['entry_price']) * position['quantity']
                    pnl_pct = (current_price / position['entry_price'] - 1) * 100
                    capital += pnl

                    trade = {
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'quantity': position['quantity'],
                        'pnl': round(pnl, 2),
                        'pnl_pct': round(pnl_pct, 2),
                        'entry_idx': position['entry_idx'],
                        'exit_idx': i,
                        'bars_held': i - position['entry_idx'],
                        'signal_type': position['signal_type'],
                        'signal_reason': position['signal_reason'],
                        'signal_strength': position['signal_strength'],
                        'sell_reason': sell_reason,
                        'entry_date': str(bars_list[position['entry_idx']].dt),
                        'exit_date': str(current_bar.dt),
                    }
                    result.trades.append(trade)
                    position = None

            equity_curve.append(capital)

        # 如果回测结束还有持仓，强制平仓
        if position:
            last_price = bars_list[-1].close
            pnl = (last_price - position['entry_price']) * position['quantity']
            pnl_pct = (last_price / position['entry_price'] - 1) * 100
            capital += pnl

            trade = {
                'entry_price': position['entry_price'],
                'exit_price': last_price,
                'quantity': position['quantity'],
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2),
                'entry_idx': position['entry_idx'],
                'exit_idx': len(bars_list) - 1,
                'bars_held': len(bars_list) - 1 - position['entry_idx'],
                'signal_type': position['signal_type'],
                'signal_reason': position['signal_reason'],
                'sell_reason': '回测结束强制平仓',
                'entry_date': str(bars_list[position['entry_idx']].dt),
                'exit_date': str(bars_list[-1].dt),
            }
            result.trades.append(trade)

        result.equity_curve = equity_curve
        result.start_date = str(bars_list[0].dt)
        result.end_date = str(bars_list[-1].dt)
        result.calculate_stats()

        return result

    def run_and_reflect(self, symbol: str, bars_list: list,
                        strategy_name: str = "czsc_extension") -> Dict:
        """
        回测 + 自动反思 + RGB 更新

        Args:
            symbol: 品种代码
            bars_list: RawBar 列表
            strategy_name: 策略名称

        Returns:
            {result, reflections, rule_updates}
        """
        # 1. 运行回测
        result = self.run_backtest(symbol, bars_list, strategy_name)

        reflections = []
        rule_updates = []

        # 2. 对每笔交易生成反思
        try:
            import sys
            sys.path.insert(0, str(PROJECT_DIR))
            from rgb_updater import RGBUpdater
            updater = RGBUpdater()

            for trade in result.trades:
                reflection_path = updater.record_trade_reflection(trade, analysis={})
                reflections.append(reflection_path)

            # 3. 生成规则更新
            stats = updater.get_stats()
            rule_updates.append(stats)

        except Exception as e:
            logger.warning(f"反思/RBG更新失败: {e}")

        # 4. 保存回测报告
        report_path = REPORTS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{symbol}.json"
        report_path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

        # 5. 生成回测摘要
        summary = self._generate_summary(result)

        return {
            'result': result.to_dict(),
            'summary': summary,
            'reflections': reflections,
            'rule_updates': rule_updates,
            'report_path': str(report_path),
        }

    def _generate_summary(self, result: BacktestResult) -> str:
        """生成回测摘要"""
        return f"""📊 回测报告: {result.symbol} ({result.strategy})

时间: {result.start_date[:10]} ~ {result.end_date[:10]}
初始资金: ${result.initial_capital:,.2f}
最终资金: ${result.final_capital:,.2f}
收益率: {(result.final_capital / result.initial_capital - 1) * 100:+.2f}%

交易次数: {result.total_trades}
胜率: {result.win_rate * 100:.1f}%
盈利因子: {result.profit_factor:.2f}
最大回撤: {result.max_drawdown * 100:.2f}%
平均盈利: ${result.avg_win:.2f}
平均亏损: ${result.avg_loss:.2f}

{'🟢 表现良好' if result.win_rate > 0.5 and result.profit_factor > 1.5 else '🟡 需要优化' if result.profit_factor > 1 else '🔴 策略需要重新审视'}
"""


# ==================== CLI ====================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(PROJECT_DIR / "data"))
    from czsc import RawBar, Freq
    import numpy as np
    import pandas as pd

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    # 模拟数据回测
    np.random.seed(42)
    n = 500
    dates = pd.date_range('2025-01-01', periods=n, freq='D')
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    high = close + np.abs(np.random.randn(n))
    low = close - np.abs(np.random.randn(n))
    open_ = close + np.random.randn(n) * 0.5
    vol = np.random.randint(1000, 10000, n)

    bars = [RawBar(symbol='TEST', dt=dates[i], freq=Freq.D,
        open=float(open_[i]), high=float(high[i]),
        low=float(low[i]), close=float(close[i]),
        vol=float(vol[i]), amount=float(vol[i]*close[i])) for i in range(n)]

    engine = BacktestEngine(initial_capital=10000)
    result = engine.run_and_reflect('TEST', bars)

    print(result['summary'])
    print(f"反思记录: {len(result['reflections'])}个")
    print(f"报告: {result['report_path']}")
