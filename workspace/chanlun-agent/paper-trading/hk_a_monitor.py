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
    if 900 <= time_val < 930:
        return "hk_pre", "港股开市前"
    elif 930 <= time_val <= 1200:
        return "hk_morning", "港股早市"
    elif 1200 < time_val < 1300:
        return "hk_noon", "港股午间休市"
    elif 1300 <= time_val <= 1600:
        return "hk_afternoon", "港股午市"
    # A股时段
    elif 915 <= time_val < 930:
        return "a_pre", "A股集合竞价"
    elif 930 <= time_val <= 1130:
        return "a_morning", "A股早市"
    elif 1130 < time_val < 1300:
        return "a_noon", "A股午间休市"
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
    
    # 导入czsc扩展
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from czsc_extension import CzscExtension, analyze_multi_level
        from czsc import CZSC, Freq, format_standard_kline
        import pandas as pd
        CZSC_AVAILABLE = True
    except ImportError as e:
        print(f"⚠️ czsc扩展不可用: {e}")
        CZSC_AVAILABLE = False
    
    for symbol in symbols:
        try:
            # 获取实时行情 - 直接使用Tiger的分钟数据
            print(f"  📡 获取 {symbol} 数据...")
            
            # 获取日线数据（包含最新价格）
            df_daily = client.get_daily_bars(symbol, limit=5)
            if df_daily is None or len(df_daily) < 2:
                print(f"⏳ {symbol}: 无法获取日线数据")
                continue
            
            current_price = float(df_daily.iloc[-1]['close'])
            if current_price <= 0:
                print(f"⏳ {symbol}: 无效价格")
                continue
            
            if not CZSC_AVAILABLE:
                print(f"⏳ {symbol}: 现价 {current_price:.2f} (缠论分析不可用)")
                continue
            
            # 获取日线数据
            df_daily = client.get_daily_bars(symbol, limit=100)
            if df_daily is None or len(df_daily) < 50:
                print(f"⏳ {symbol}: 日线数据不足")
                continue
            
            # 转换为czsc格式
            df_daily = df_daily.rename(columns={
                'time': 'dt',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'vol'
            })
            df_daily['dt'] = pd.to_datetime(df_daily['dt'])
            df_daily = df_daily.sort_values('dt')
            df_daily['symbol'] = symbol
            df_daily['amount'] = df_daily['vol'] * df_daily['close']
            
            # 使用format_standard_kline转换为RawBar列表
            bars_daily = format_standard_kline(df_daily, Freq.D)
            
            # 创建czsc对象
            ka_daily = CZSC(bars_daily, max_bi_num=1000)
            ext_daily = CzscExtension(ka_daily)
            
            # 判断日线方向
            daily_bi_list = ext_daily.bi_list
            daily_direction = "up" if len(daily_bi_list) >= 2 and daily_bi_list[-1].direction == 'up' else "down"
            
            # 使用analyze_multi_level进行多级别分析
            analysis = analyze_multi_level(symbol, client.quote_client)
            
            if not analysis or 'error' in analysis:
                print(f"⏳ {symbol}: 分析失败 - {analysis.get('error', '未知错误')}")
                continue
            
            # 获取买点信息
            buy_points = []
            if '30min' in analysis and 'buy_signals' in analysis['30min']:
                for sig in analysis['30min']['buy_signals']:
                    buy_points.append({
                        'type': sig.get('type', 'unknown'),
                        'confidence': sig.get('strength', 0),
                        'price': sig.get('price', current_price)
                    })
            
            # 输出结果
            direction_emoji = "📈" if daily_direction == 'up' else "📉"
            
            if buy_points:
                # 找到最佳买点
                best_point = max(buy_points, key=lambda x: x['confidence'])
                if best_point['confidence'] >= 0.5:
                    print(f"\n🎯 {symbol} | 现价: {current_price:.2f}")
                    print(f"   日线方向: {direction_emoji} {daily_direction}")
                    print(f"   买点类型: {best_point['type']} | 置信度: {best_point['confidence']:.2f}")
                    print(f"   买点价格: {best_point['price']:.2f}")
                    signals_found.append({
                        'symbol': symbol,
                        'price': current_price,
                        'signal': {
                            'type': best_point['type'],
                            'strength': best_point['confidence'],
                            'suggested_stop': best_point['price'] * 0.97
                        },
                        'daily': {'direction': daily_direction}
                    })
                else:
                    print(f"⏳ {symbol}: 有买点但置信度不足 ({best_point['confidence']:.2f} < 0.5) | 日线: {daily_direction}")
            else:
                print(f"⏳ {symbol}: 现价 {current_price:.2f} | 日线: {daily_direction} | 暂无买点")
                
        except Exception as e:
            print(f"❌ {symbol}: 分析失败 - {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return signals_found


def main():
    parser = argparse.ArgumentParser(description='港A实时模拟交易监控')
    parser.add_argument('--market', choices=['hk', 'a', 'all'], default='all', help='市场选择')
    parser.add_argument('--interval', default='5min', help='扫描间隔')
    parser.add_argument('--now', action='store_true', help='立即执行一次扫描（不等待开盘）')
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
    
    # 如果指定--now，立即执行一次扫描
    if args.now:
        print("\n⚡ 立即执行首次扫描...")
        signals = scan_signals(client, symbols_to_monitor, "实时扫描")
        if signals:
            print(f"\n🚨 发现 {len(signals)} 个买点信号！")
        return
    
    # 主循环
    last_scan_time = None
    
    try:
        while True:
            market_status, market_name = get_market_status()
            
            if market_status in ['closed']:
                print(f"\n⏰ {datetime.now().strftime('%H:%M')} 市场休市，等待开盘...")
                time.sleep(60)
                continue
            elif market_status in ['hk_pre', 'a_pre']:
                print(f"\n⏰ {datetime.now().strftime('%H:%M')} {market_name}，准备中...")
                # 开盘前也进行一次扫描
                if last_scan_time is None:
                    signals = scan_signals(client, symbols_to_monitor, "开盘前分析")
                    last_scan_time = datetime.now()
                time.sleep(30)
                continue
            elif market_status in ['hk_noon', 'a_noon']:
                print(f"\n⏰ {datetime.now().strftime('%H:%M')} {market_name}")
                time.sleep(60)
                continue
            
            # 交易时段 - 检查是否需要扫描
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
