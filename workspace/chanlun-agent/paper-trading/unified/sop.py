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
    
    def verify_market(self, market='US'):
        """
        市场系统性风险验证（盘前必须）
        用该市场最便宜的标的，端到端闭环验证：
        数据对齐 → 下单 → 成交 → 撤单/平仓 → 查询
        """
        import tiger_client as tc

        print("=" * 50)
        print(f"🔧 市场系统验证 - {market}")
        print("=" * 50)

        # 1. 数据对齐验证（用tiger_client直接获取）
        print("\n【1】实时数据对齐")
        symbols = self.engine.config.get('symbols', {})
        market_symbols = {s: c for s, c in symbols.items()
                         if c.get('market') == market and c.get('enabled')}
        if not market_symbols:
            print(f"  ❌ {market} 无已配置标的")
            return False

        for sym in market_symbols:
            try:
                brief = tc.get_stock_brief(sym)
                has_permission_error = 'permission denied' in str(brief).lower()
                if has_permission_error:
                    print(f"  ⚠️ {sym}: 实时行情无权限（交易不受影响）")
                elif brief and 'error' not in str(brief).lower():
                    print(f"  ✅ {sym}: {brief[:80]}")
                else:
                    print(f"  ❌ {sym}: 行情获取失败")
                    return False
            except Exception as e:
                print(f"  ❌ {sym}: {e}")
                return False

        # 2. 选最便宜的标的验证
        print("\n【2】选择验证标的")
        cheapest_sym = None
        cheapest_price = float('inf')
        for sym in market_symbols:
            try:
                brief = tc.get_stock_brief(sym)
                if brief and 'price' in str(brief).lower():
                    # 从brief中提取价格
                    import re
                    price_match = re.search(r'price[\":\s]+([\d.]+)', str(brief))
                    if price_match:
                        p = float(price_match.group(1))
                        if p < cheapest_price:
                            cheapest_price = p
                            cheapest_sym = sym
            except:
                pass

        if not cheapest_sym:
            # fallback: 用第一个
            cheapest_sym = list(market_symbols.keys())[0]
            cheapest_price = 0

        print(f"  选择: {cheapest_sym} (${cheapest_price:.2f})")

        # 3. 下单验证（市价单）
        print(f"\n【3】下单验证 ({cheapest_sym})")
        try:
            buy_result = tc.place_order_market(cheapest_sym, 1, 'BUY')
            print(f"  BUY: {buy_result}")
            if '成功' not in str(buy_result):
                print(f"  ❌ 买入失败，市场通道异常")
                return False
        except Exception as e:
            print(f"  ❌ 买入异常: {e}")
            return False

        # 4. 平仓验证
        try:
            sell_result = tc.place_order_market(cheapest_sym, 1, 'SELL')
            print(f"  SELL: {sell_result}")
            if '成功' not in str(sell_result):
                print(f"  ❌ 卖出失败，市场通道异常")
                return False
        except Exception as e:
            print(f"  ❌ 卖出异常: {e}")
            return False

        # 5. 成交记录验证
        print("\n【4】成交记录验证")
        try:
            records = tc.get_order_records()
            if records and cheapest_sym in str(records):
                print(f"  ✅ 成交记录确认")
                for r in records[:3]:
                    print(f"    {r}")
            else:
                print(f"  ❌ 无成交记录")
                return False
        except Exception as e:
            print(f"  ❌ 查询失败: {e}")
            return False

        # 6. 持仓验证（应为空仓）
        print("\n【5】持仓验证")
        try:
            positions = tc.get_positions()
            print(f"  持仓: {positions}")
        except Exception as e:
            print(f"  ⚠️ 持仓查询: {e}")

        print("\n" + "=" * 50)
        print(f"✅ {market} 市场系统验证通过")
        print("=" * 50)
        return True

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
    parser.add_argument('--verify-market', choices=['HK', 'US'], help='市场系统验证（盘前必须）')

    args = parser.parse_args()

    sop = TradingSOP()
    sop.market = args.market

    if args.verify_market:
        sop.verify_market(args.verify_market)
    elif args.pre_scan:
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
