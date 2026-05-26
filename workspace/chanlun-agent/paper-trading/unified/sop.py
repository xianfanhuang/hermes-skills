#!/usr/bin/env python3
"""
交易SOP自动化运行器
盘前→盘中→盘后全流程
"""

import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'skills' / 'tiger-broker'))
sys.path.insert(0, str(Path(__file__).parent))

from engine import TradingEngine, UNIFIED_DIR

class TradingSOP:
    """交易SOP自动化"""
    
    def __init__(self):
        self.engine = TradingEngine()
        self.market = 'HK'  # 默认港股
    
    def run_pre_scan(self):
        """盘前扫描"""
        print("=" * 50)
        print(f"📋 盘前扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 50)
        
        # 1. 检查持仓
        print("\n【1】持仓检查")
        positions = self.engine.portfolio.get('positions', {})
        if positions:
            for symbol, pos in positions.items():
                if pos.get('position', 0) > 0:
                    print(f"  {symbol}: {pos['position']}股 均价{pos.get('avg_cost', 0)}")
        else:
            print("  无持仓")
        
        # 2. 分析每个标的
        print("\n【2】缠论分析")
        symbols = self.engine.config.get('symbols', {})
        for symbol, config in symbols.items():
            if not config.get('enabled', False):
                continue
            
            market = config.get('market', 'HK')
            analysis = self.engine.analyze_symbol(symbol, market)
            
            if not analysis:
                print(f"  {symbol}: 分析失败")
                continue
            
            quote = analysis.get('quote')
            trend_dir = analysis.get('trend_direction', '?')
            trend_label = '⬇️下跌趋势' if trend_dir == 'down' else '⬆️上升趋势' if trend_dir == 'up' else '➡️盘整'
            strategy = analysis.get('strategy', 'unknown')
            
            print(f"\n  {symbol} {config.get('name', '')}")
            print(f"  价格: ${quote.price:.2f}")
            print(f"  趋势: {trend_label}")
            print(f"  策略: {strategy}")
            
            # 生成信号
            try:
                signal = self.engine.generate_signal(symbol, analysis)
                if signal:
                    print(f"  信号: {signal.action} {signal.direction}")
                    print(f"  止损: ${signal.stop_loss:.2f}")
                    print(f"  止盈: ${signal.take_profit:.2f}")
                else:
                    print(f"  信号: 无")
            except Exception as e:
                print(f"  信号生成失败: {e}")
        
        print("\n" + "=" * 50)
    
    def run_monitor_cycle(self):
        """运行一个监控周期"""
        print(f"\n{'='*50}")
        print(f"🔍 监控周期 - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*50}")
        
        # 运行引擎
        self.engine.run_cycle()
        
        # 显示订单记录
        print("\n📋 最近订单:")
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'skills' / 'tiger-broker'))
            from tiger_client import get_order_records
            records = get_order_records(5)
            for r in records:
                print(f"  {r}")
        except Exception as e:
            print(f"  获取订单失败: {e}")
    
    def run_post_summary(self):
        """盘后总结"""
        print("=" * 50)
        print(f"📊 盘后总结 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 50)
        
        # 1. 检查持仓
        print("\n【1】持仓检查")
        positions = self.engine.portfolio.get('positions', {})
        if positions:
            for symbol, pos in positions.items():
                if pos.get('position', 0) > 0:
                    print(f"  {symbol}: {pos['position']}股 均价{pos.get('avg_cost', 0)}")
        else:
            print("  无持仓")
        
        # 2. 今日交易统计
        print("\n【2】今日交易")
        trades = self.engine.trades
        today = datetime.now().strftime('%Y-%m-%d')
        today_trades = [t for t in trades if t.get('time', '').startswith(today)]
        
        if today_trades:
            print(f"  交易笔数: {len(today_trades)}")
            total_pnl = sum(t.get('pnl', 0) for t in today_trades)
            print(f"  总盈亏: ${total_pnl:.2f}")
        else:
            print("  今日无交易")
        
        # 3. 订单记录
        print("\n【3】订单记录")
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'skills' / 'tiger-broker'))
            from tiger_client import get_order_records
            records = get_order_records(10)
            for r in records:
                print(f"  {r}")
        except Exception as e:
            print(f"  获取订单失败: {e}")
        
        # 4. 风控状态
        print("\n【4】风控状态")
        risk = self.engine.risk_engine
        print(f"  日盈亏: ${risk.daily_pnl:.2f}")
        print(f"  连续亏损: {risk.consecutive_losses}次")
        
        print("\n" + "=" * 50)
    
    def run_full_cycle(self, interval=300):
        """运行完整周期"""
        print("🚀 交易SOP启动")
        print(f"  市场: {self.market}")
        print(f"  间隔: {interval}秒")
        
        # 盘前扫描
        self.run_pre_scan()
        
        # 等待开盘
        now = datetime.now()
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        
        if now < market_open:
            wait_seconds = (market_open - now).total_seconds()
            print(f"\n⏳ 等待开盘: {wait_seconds/60:.0f}分钟")
            time.sleep(wait_seconds)
        
        # 盘中监控
        print("\n📈 开盘监控")
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        while datetime.now() < market_close:
            self.run_monitor_cycle()
            time.sleep(interval)
        
        # 盘后总结
        self.run_post_summary()


def main():
    parser = argparse.ArgumentParser(description='交易SOP自动化')
    parser.add_argument('--pre-scan', action='store_true', help='盘前扫描')
    parser.add_argument('--monitor', action='store_true', help='盘中监控')
    parser.add_argument('--post-summary', action='store_true', help='盘后总结')
    parser.add_argument('--full', action='store_true', help='完整周期')
    parser.add_argument('--interval', type=int, default=300, help='监控间隔(秒)')
    parser.add_argument('--market', choices=['HK', 'US'], default='HK', help='市场')
    
    args = parser.parse_args()
    
    sop = TradingSOP()
    sop.market = args.market
    
    if args.pre_scan:
        sop.run_pre_scan()
    elif args.monitor:
        sop.run_monitor_cycle()
    elif args.post_summary:
        sop.run_post_summary()
    elif args.full:
        sop.run_full_cycle(args.interval)
    else:
        # 默认运行监控周期
        sop.run_monitor_cycle()


if __name__ == "__main__":
    main()
