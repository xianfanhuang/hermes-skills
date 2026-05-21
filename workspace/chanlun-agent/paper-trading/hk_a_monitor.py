#!/usr/bin/env python3
"""
港A实时模拟交易监控器

Usage:
    python3 hk_a_monitor.py --market hk --interval 5min
    python3 hk_a_monitor.py --market a --interval 5min
"""

import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from crcl_tiger_trader import TigerClient

# 监控品种
HK_SYMBOLS = ['00700', '03690', '01810', '09999']  # 腾讯、美团、小米、网易
A_SYMBOLS = ['510050', '510300', '159915']  # 上证50ETF、沪深300ETF、创业板ETF


def get_market_status():
    """获取当前市场状态"""
    now = datetime.now()
    hour, minute = now.hour, now.minute
    time_val = hour * 100 + minute
    
    # 港股时段 (北京时间)
    if 930 <= time_val <= 1200:
        return "hk_morning", "港股早市"
    elif 1300 <= time_val <= 1600:
        return "hk_afternoon", "港股午市"
    # A股时段
    elif 930 <= time_val <= 1130:
        return "a_morning", "A股早市"
    elif 1300 <= time_val <= 1500:
        return "a_afternoon", "A股午市"
    else:
        return "closed", "休市"


def scan_signals(client, symbols, market_name):
    """扫描缠论买点信号"""
    print(f"\n{'='*60}")
    print(f"🔍 {market_name} 缠论买点扫描 - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    signals_found = []
    
    for symbol in symbols:
        try:
            # 获取实时行情
            quote = client.get_quote(symbol)
            if not quote:
                continue
                
            current_price = quote.get('price', 0)
            
            # 获取K线数据
            from chanlun_integration import ChanlunIntegration
            chanlun = ChanlunIntegration()
            
            # 获取日线数据判断方向
            df_daily = chanlun.get_kline(symbol, period="daily", count=100)
            if df_daily is None or len(df_daily) < 50:
                continue
                
            daily_status = chanlun.analyze_daily_direction(df_daily)
            
            # 获取30分钟数据找买点
            df_30m = chanlun.get_kline(symbol, period="30min", count=100)
            if df_30m is None or len(df_30m) < 50:
                continue
                
            buy_signals = chanlun.find_buy_signals(df_30m, df_daily)
            
            # 输出结果
            direction_emoji = "📈" if daily_status['direction'] == 'up' else "📉" if daily_status['direction'] == 'down' else "➡️"
            
            if buy_signals:
                best_signal = max(buy_signals, key=lambda x: x['strength'])
                if best_signal['strength'] >= 0.5:
                    print(f"\n🎯 {symbol} | 现价: {current_price:.2f}")
                    print(f"   日线方向: {direction_emoji} {daily_status['direction']} ({daily_status['confidence']:.0%})")
                    print(f"   买点类型: {best_signal['type']} | 强度: {best_signal['strength']:.2f}")
                    print(f"   建议止损: {best_signal['suggested_stop']:.2f}")
                    signals_found.append({
                        'symbol': symbol,
                        'price': current_price,
                        'signal': best_signal,
                        'daily': daily_status
                    })
                else:
                    print(f"⏳ {symbol}: 有买点但强度不足 ({best_signal['strength']:.2f} < 0.5)")
            else:
                print(f"⏳ {symbol}: 暂无买点 | 日线: {daily_status['direction']}")
                
        except Exception as e:
            print(f"❌ {symbol}: 分析失败 - {e}")
            continue
    
    return signals_found


def main():
    parser = argparse.ArgumentParser(description='港A实时模拟交易监控')
    parser.add_argument('--market', choices=['hk', 'a', 'all'], default='all', help='市场选择')
    parser.add_argument('--interval', default='5min', help='扫描间隔')
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 港A实时模拟交易监控系统启动")
    print("="*60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 初始化Tiger客户端
    client = TigerClient()
    
    # 确定监控品种
    symbols_to_monitor = []
    if args.market in ['hk', 'all']:
        symbols_to_monitor.extend(HK_SYMBOLS)
        print(f"港股监控: {', '.join(HK_SYMBOLS)}")
    if args.market in ['a', 'all']:
        symbols_to_monitor.extend(A_SYMBOLS)
        print(f"A股监控: {', '.join(A_SYMBOLS)}")
    
    # 解析扫描间隔
    interval_min = 5
    if 'min' in args.interval:
        interval_min = int(args.interval.replace('min', ''))
    
    print(f"扫描间隔: {interval_min}分钟")
    print("="*60)
    
    # 主循环
    last_scan_time = None
    
    try:
        while True:
            market_status, market_name = get_market_status()
            
            if market_status == "closed":
                print(f"\n⏰ {datetime.now().strftime('%H:%M')} 市场休市，等待开盘...")
                time.sleep(60)
                continue
            
            # 检查是否需要扫描
            now = datetime.now()
            if last_scan_time is None or (now - last_scan_time).seconds >= interval_min * 60:
                signals = scan_signals(client, symbols_to_monitor, market_name)
                
                if signals:
                    print(f"\n🚨 发现 {len(signals)} 个买点信号！")
                    for sig in signals:
                        print(f"   - {sig['symbol']}: {sig['signal']['type']} @ {sig['price']:.2f}")
                else:
                    print(f"\n✓ 扫描完成，暂无买点信号")
                
                last_scan_time = now
                print(f"\n⏳ 下次扫描: {(now.timestamp() + interval_min * 60):.0f}")
            
            time.sleep(30)  # 每30秒检查一次时间
            
    except KeyboardInterrupt:
        print("\n\n👋 监控已停止")


if __name__ == "__main__":
    main()
