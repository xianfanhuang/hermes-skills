#!/usr/bin/env python3
"""
港A实时模拟交易监控器 - 支持多空双向

Usage:
    python3 hk_a_monitor.py --market hk --interval 5min --now
    python3 hk_a_monitor.py --market all --interval 5min
"""

import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Tiger SDK 配置
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import Language

TIGER_ID = "20159412"
TIGER_PRIVATE_KEY = """MIICXAIBAAKBgQCQsk07H1czwJy5Gfm9GH2iahHEX3Hhej6y8FW7Hvd9X9jTqxoxFi45aMPFXU7nAx9Ki/gYQlYeXjpCu5RMUHboaz29iBlXmq0gFd6/CdB1LEPbua5V5/kUP53ETbKo0RFjm+fWHxYE6QMpMyW6amP2ASyygSs23aAxYnLZboq5vwIDAQABAoGAXr0/r/w/PlVYyCFn0RXd/J9ybp8Hk1hVARg3KcOGzAIbl8up5IXfUht0Qx9q7/qtXEP09v1IIa4Ue2kSGj18/IhEDla3+EMs24pQ9xnRPgwnzsQkfwNTerGwnxvrM+iHl/IH0AKL0kBPs56JsIIP5VZMd3xNK4xiVTzZIRcRVRECQQDGdrrM6qkomFPw8YRjIO7DuM1IG7ec2PVHX/zYMgCkfYBCsz+DjsopKLjEGms3IqHlSwzB5GLq/z1iHBf8IM/tAkEAuqUn91dmOgSsUJIbuAVN/FtoGcIKe0SYybX3BDsPE6295XR70XMhnrTjx0wIsiANzgC1JZC8PdxB1pxUyx0C2wJBALeao9prxa8OramcZlOm5f0f/JoXOljaxqAPh0UjjUCf8obCeaHl+dT2HWke382UNp6APf8qoPCyzUD0qKPSX0kCQE7WJ/V/wzxKcQZvUKoAA5rOeUA4B/ldVjQNWlM9Jvcm8gkTlKE5wj+pJHUwFpQ2md4jymAdrIVsnZqq2d4ZWPUCQFesxYFPfPv2xnonihe7zqsFAz0pD3E5Ks/F3sdUZk4s/A9Zf1rzxS2XsQtqHgl08L0u340m+YbtTlz/Lyq0mLI=="""
SIM_ACCOUNT = "21409378833585169"


class TigerClient:
    """Tiger API 客户端"""
    
    def __init__(self, account: str = SIM_ACCOUNT):
        self.account = account
        self.config = TigerOpenClientConfig(sandbox_debug=False)
        self.config.tiger_id = TIGER_ID
        self.config.private_key = TIGER_PRIVATE_KEY
        self.config.language = Language.zh_CN
        self.config.account = account
        
        self.quote_client = QuoteClient(self.config)
        self.trade_client = TradeClient(self.config)
        print(f"🐯 Tiger 客户端初始化成功 - 账户: {account}")
    
    def get_daily_bars(self, symbol: str, limit: int = 30):
        """获取日线数据"""
        try:
            bars = self.quote_client.get_bars([symbol], period="day", limit=limit)
            if bars is not None and not bars.empty:
                return bars
            return None
        except Exception as e:
            print(f"获取日线失败: {e}")
            return None

# 监控品种 - 港A最多一支，当前最具交易价值标的
# 根据analyze_best_pick.py分析结果动态选择
# 2026-05-21: 小米(01810)评分最高(3.4分)，但所有标的趋势向下，暂无买点
HK_SYMBOLS = ['01810']  # 小米 - 当前最具交易价值
A_SYMBOLS = []  # A股ETF为T+1品种，暂不监控


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
        return "closed", "市场休市"


def scan_signals(client, symbols, market_name):
    """扫描缠论买卖点信号（支持多空双向）"""
    print(f"\n{'='*60}")
    print(f"🔍 {market_name} 缠论买卖点扫描 - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    buy_signals = []
    sell_signals = []
    
    # 导入czsc扩展
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from czsc_extension import CzscExtension, BuySellPoint, ZS
        from czsc import CZSC, Freq, format_standard_kline
        import pandas as pd
        CZSC_AVAILABLE = True
    except ImportError as e:
        print(f"⚠️ czsc扩展不可用: {e}")
        CZSC_AVAILABLE = False
    
    for symbol in symbols:
        try:
            print(f"  📡 获取 {symbol} 数据...")
            
            # 获取日线数据
            df_daily = client.get_daily_bars(symbol, limit=100)
            if df_daily is None or len(df_daily) < 50:
                print(f"⏳ {symbol}: 日线数据不足")
                continue
            
            current_price = float(df_daily.iloc[-1]['close'])
            if current_price <= 0:
                print(f"⏳ {symbol}: 无效价格")
                continue
            
            if not CZSC_AVAILABLE:
                print(f"⏳ {symbol}: 现价 {current_price:.2f} (缠论分析不可用)")
                continue
            
            # 转换为czsc格式
            df_daily = df_daily.rename(columns={
                'time': 'dt', 'open': 'open', 'high': 'high',
                'low': 'low', 'close': 'close', 'volume': 'vol'
            })
            df_daily['dt'] = pd.to_datetime(df_daily['dt'])
            df_daily['symbol'] = symbol
            df_daily['amount'] = df_daily['vol'] * df_daily['close']
            df_daily = df_daily.sort_values('dt')
            
            bars_daily = format_standard_kline(df_daily, Freq.D)
            ka_daily = CZSC(bars_daily, max_bi_num=1000)
            ext_daily = CzscExtension(ka_daily)
            
            # 获取缠论分析结果
            bi_list = ext_daily.bi_list
            zs_list = ext_daily.calc_zs_list()
            divergence = ext_daily.detect_divergence()
            all_points = ext_daily.detect_buy_sell_points()
            
            # 提取买卖信号
            buys = [p for p in all_points if 'buy' in p.type]
            sells = [p for p in all_points if 'sell' in p.type]
            
            # 一买/一卖（背驰）
            if divergence.get('divergence'):
                if divergence['type'] == 'bottom':
                    buys.append(type('obj', (object,), {
                        'type': 'buy1', 'price': bi_list[-1].low if bi_list else current_price,
                        'confidence': 0.8, 'direction': 'up'
                    })())
                elif divergence['type'] == 'top':
                    sells.append(type('obj', (object,), {
                        'type': 'sell1', 'price': bi_list[-1].high if bi_list else current_price,
                        'confidence': 0.8, 'direction': 'down'
                    })())
            
            # 输出当前状态
            bi_count = len(bi_list)
            zs_count = len(zs_list)
            has_divergence = "✓" if divergence.get('divergence') else "✗"
            
            print(f"     价格: {current_price:.2f} | 笔: {bi_count} | 中枢: {zs_count} | 背驰: {has_divergence}")
            
            # 处理买点
            if buys:
                best_buy = max(buys, key=lambda x: x.confidence)
                if best_buy.confidence >= 0.5:
                    print(f"     🟢 买点: {best_buy.type} @ {best_buy.price:.2f} (置信度: {best_buy.confidence:.2f})")
                    buy_signals.append({
                        'symbol': symbol,
                        'price': current_price,
                        'signal_type': best_buy.type,
                        'signal_price': best_buy.price,
                        'confidence': best_buy.confidence,
                        'action': 'BUY'
                    })
            
            # 处理卖点
            if sells:
                best_sell = max(sells, key=lambda x: x.confidence)
                if best_sell.confidence >= 0.5:
                    print(f"     🔴 卖点: {best_sell.type} @ {best_sell.price:.2f} (置信度: {best_sell.confidence:.2f})")
                    sell_signals.append({
                        'symbol': symbol,
                        'price': current_price,
                        'signal_type': best_sell.type,
                        'signal_price': best_sell.price,
                        'confidence': best_sell.confidence,
                        'action': 'SELL_SHORT'
                    })
            
            if not buys and not sells:
                print(f"     ⏳ 暂无买卖信号")
                
        except Exception as e:
            print(f"❌ {symbol}: 分析失败 - {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 汇总结果
    all_signals = buy_signals + sell_signals
    
    print(f"\n{'='*60}")
    print(f"📊 扫描结果汇总")
    print(f"{'='*60}")
    print(f"做多信号: {len(buy_signals)} 个")
    print(f"做空信号: {len(sell_signals)} 个")
    
    if all_signals:
        for sig in all_signals:
            emoji = "🟢 BUY" if sig['action'] == 'BUY' else "🔴 SHORT"
            print(f"   {emoji} {sig['symbol']}: {sig['signal_type']} @ {sig['signal_price']:.2f}")
    
    return all_signals


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
            print(f"\n🚨 发现 {len(signals)} 个交易信号！")
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
                    print(f"\n🚨 发现 {len(signals)} 个交易信号！")
                    for sig in signals:
                        emoji = "🟢" if sig['action'] == 'BUY' else "🔴"
                        print(f"   {emoji} {sig['symbol']}: {sig['signal_type']} @ {sig['signal_price']:.2f}")
                else:
                    print(f"\n✓ 扫描完成，暂无买卖信号")
                
                last_scan_time = now
                print(f"\n⏳ 下次扫描: {(now.timestamp() + interval_min * 60):.0f}")
            
            time.sleep(30)  # 每30秒检查一次时间
            
    except KeyboardInterrupt:
        print("\n\n👋 监控已停止")


if __name__ == "__main__":
    main()
