#!/usr/bin/env python3
"""
CRCL 缠论实时模拟交易监控

使用方式:
    python3 crcl_monitor.py --once     # 单次扫描
    python3 crcl_monitor.py --loop     # 持续监控（每5分钟）
"""

import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'skills' / 'tiger-broker'))
from chanlun_perception import ChanlunPerception
from tiger_client import place_order_limit, place_order_market

# Finnhub API Key
FINNHUB_KEY = "d85kn4hr01qitd92g090d85kn4hr01qitd92g09g"

def get_realtime_quote(symbol: str) -> dict:
    """从Finnhub获取实时行情"""
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'price': data.get('c', 0),
                'change': data.get('d', 0),
                'change_pct': data.get('dp', 0),
                'high': data.get('h', 0),
                'low': data.get('l', 0),
                'open': data.get('o', 0),
                'prev_close': data.get('pc', 0),
            }
    except Exception as e:
        print(f"Finnhub行情获取失败: {e}")
    return {'price': 0, 'change': 0, 'change_pct': 0}

PORTFOLIO_PATH = Path(__file__).parent / "crcl_portfolio.json"

def load_portfolio():
    with open(PORTFOLIO_PATH, 'r') as f:
        return json.load(f)

def save_portfolio(portfolio):
    with open(PORTFOLIO_PATH, 'w') as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)

def analyze_crcl(perception):
    """分析 CRCL 缠论结构"""
    quote = get_realtime_quote('CRCL')
    structures = perception.analyze_symbol('CRCL', 'US', ['日线', '30分钟', '5分钟'])
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'quote': quote,
        'structures': {}
    }
    
    for freq, structure in structures.items():
        result['structures'][freq] = {
            'trend': structure.trend,
            'bi_count': structure.bi_count,
            'zs_count': structure.zs_count,
            'zs_range': structure.last_zs_range,
            'last_bi': structure.last_bi_direction,
            'divergence': structure.divergence
        }
    
    return result

def generate_signal(analysis, portfolio):
    """基于缠论分析生成交易信号"""
    signals = []
    
    daily = analysis['structures'].get('日线', {})
    min30 = analysis['structures'].get('30分钟', {})
    min5 = analysis['structures'].get('5分钟', {})
    
    price = analysis['quote'].get('price', 0) if analysis['quote'] else 0
    has_position = len(portfolio['positions']) > 0
    
    # 信号1: 日线上升趋势 + 5分钟回调结束（底分型确认）
    if daily.get('trend') == 'up' and min5.get('last_bi') == '向上' and not has_position:
        if min5.get('divergence'):
            signals.append({
                'type': 'BUY',
                'strength': 'STRONG',
                'reason': '日线上升趋势 + 5分钟底背驰确认',
                'entry': price,
                'stop_loss': price * 0.97,
                'target': price * 1.06,
                'confidence': 80
            })
        elif daily.get('zs_range'):
            zs_high = daily['zs_range'][1]
            if price > zs_high:
                signals.append({
                    'type': 'BUY',
                    'strength': 'MEDIUM',
                    'reason': f'日线突破中枢上沿 {zs_high:.2f}',
                    'entry': price,
                    'stop_loss': zs_high * 0.98,
                    'target': price * 1.08,
                    'confidence': 65
                })
    
    # 信号2: 日线下跌趋势 + 反弹至中枢上沿（做空/观望）
    if daily.get('trend') == 'down' and not has_position:
        if daily.get('zs_range'):
            zs_high = daily['zs_range'][1]
            if price >= zs_high * 0.98:
                signals.append({
                    'type': 'WAIT',
                    'strength': 'MEDIUM',
                    'reason': f'日线下跌趋势，价格接近中枢上沿 {zs_high:.2f}，等待确认',
                    'note': '若突破中枢上沿并站稳，则趋势可能反转'
                })
    
    # 信号3: 持仓止盈/止损检查
    if has_position:
        pos = portfolio['positions'][0]
        entry_price = pos.get('entry_price', 0)
        stop_loss = pos.get('stop_loss', 0)
        target = pos.get('target', 0)
        
        if price <= stop_loss:
            signals.append({
                'type': 'SELL',
                'strength': 'STRONG',
                'reason': f'触发止损 {stop_loss:.2f}',
                'pnl_pct': ((price - entry_price) / entry_price) * 100
            })
        elif price >= target:
            signals.append({
                'type': 'SELL',
                'strength': 'STRONG',
                'reason': f'达到目标位 {target:.2f}',
                'pnl_pct': ((price - entry_price) / entry_price) * 100
            })
        elif min5.get('divergence') and min5.get('last_bi') == '向下':
            signals.append({
                'type': 'SELL',
                'strength': 'MEDIUM',
                'reason': '5分钟顶背驰，考虑部分止盈',
                'pnl_pct': ((price - entry_price) / entry_price) * 100
            })
    
    # 默认：无信号
    if not signals:
        signals.append({
            'type': 'HOLD',
            'strength': 'NONE',
            'reason': '无明确信号，继续观察'
        })
    
    return signals

def execute_signal(signal, analysis, portfolio):
    """执行交易信号（模拟）"""
    price = analysis['quote'].get('price', 0) if analysis['quote'] else 0
    
    if signal['type'] == 'BUY' and signal['strength'] in ['STRONG', 'MEDIUM']:
        # 计算仓位（风险3%）
        risk_pct = 0.03
        stop_loss = signal.get('stop_loss', price * 0.97)
        risk_per_share = price - stop_loss
        max_risk = portfolio['account']['equity'] * risk_pct
        shares = int(max_risk / risk_per_share) if risk_per_share > 0 else 0
        shares = min(shares, int(portfolio['account']['cash_available'] / price))
        
        if shares > 0:
            cost = shares * price
            portfolio['account']['cash_available'] -= cost
            portfolio['account']['equity'] = portfolio['account']['cash_available'] + cost
            
            position = {
                'symbol': 'CRCL',
                'entry_price': price,
                'shares': shares,
                'cost': cost,
                'stop_loss': stop_loss,
                'target': signal.get('target', price * 1.06),
                'entry_time': datetime.now().isoformat(),
                'entry_reason': signal['reason']
            }
            portfolio['positions'].append(position)
            
            portfolio['trade_log'].append({
                'time': datetime.now().isoformat(),
                'action': 'BUY',
                'price': price,
                'shares': shares,
                'reason': signal['reason']
            })
            
            print(f'\n🟢 模拟买入:')
            print(f'  价格: ${price:.2f}')
            print(f'  数量: {shares} 股')
            print(f'  成本: ${cost:.2f}')
            print(f'  止损: ${stop_loss:.2f}')
            print(f'  目标: ${signal.get("target", price * 1.06):.2f}')
    
    elif signal['type'] == 'SELL' and portfolio['positions']:
        pos = portfolio['positions'][0]
        entry_price = pos['entry_price']
        shares = pos['shares']
        proceeds = shares * price
        pnl = proceeds - pos['cost']
        pnl_pct = ((price - entry_price) / entry_price) * 100
        
        portfolio['account']['cash_available'] += proceeds
        portfolio['account']['realized_pnl'] += pnl
        portfolio['account']['equity'] = portfolio['account']['cash_available']
        portfolio['positions'].remove(pos)
        
        portfolio['trade_log'].append({
            'time': datetime.now().isoformat(),
            'action': 'SELL',
            'price': price,
            'shares': shares,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': signal['reason']
        })
        
        print(f'\n🔴 模拟卖出:')
        print(f'  价格: ${price:.2f}')
        print(f'  数量: {shares} 股')
        print(f'  盈亏: ${pnl:.2f} ({pnl_pct:+.2f}%)')
        print(f'  原因: {signal["reason"]}')
    
    portfolio['account']['last_update'] = datetime.now().isoformat()
    save_portfolio(portfolio)

def print_status(analysis, signals, portfolio):
    """打印当前状态"""
    quote = analysis['quote']
    daily = analysis['structures'].get('日线', {})
    min5 = analysis['structures'].get('5分钟', {})
    
    print(f'\n{"="*60}')
    print(f'📊 CRCL 缠论实时监控')
    print(f'⏰ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"="*60}')
    
    if quote:
        print(f'\n💰 行情:')
        print(f'  价格: ${quote.get("price", "N/A")}')
        print(f'  涨跌: {quote.get("change_pct", "N/A")}%')
    
    print(f'\n📈 日线结构:')
    print(f'  趋势: {daily.get("trend", "N/A")}')
    print(f'  笔: {daily.get("bi_count", "N/A")} | 中枢: {daily.get("zs_count", "N/A")}')
    if daily.get('zs_range'):
        print(f'  中枢区间: [{daily["zs_range"][0]:.2f}, {daily["zs_range"][1]:.2f}]')
    print(f'  最后一笔: {daily.get("last_bi", "N/A")}')
    print(f'  背驰: {"是 ⚠️" if daily.get("divergence") else "否"}')
    
    print(f'\n📉 5分钟结构:')
    print(f'  趋势: {min5.get("trend", "N/A")}')
    print(f'  笔: {min5.get("bi_count", "N/A")} | 中枢: {min5.get("zs_count", "N/A")}')
    
    print(f'\n📡 信号:')
    for sig in signals:
        emoji = {'BUY': '🟢', 'SELL': '🔴', 'WAIT': '🟡', 'HOLD': '⚪'}.get(sig['type'], '⚪')
        print(f'  {emoji} [{sig["type"]}] {sig["reason"]}')
        if 'confidence' in sig:
            print(f'     置信度: {sig["confidence"]}%')
    
    if portfolio['positions']:
        pos = portfolio['positions'][0]
        current_price = quote.get('price', 0) if quote else 0
        pnl = (current_price - pos['entry_price']) * pos['shares']
        pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
        print(f'\n💼 持仓:')
        print(f'  入场价: ${pos["entry_price"]:.2f}')
        print(f'  数量: {pos["shares"]} 股')
        print(f'  当前盈亏: ${pnl:.2f} ({pnl_pct:+.2f}%)')
        print(f'  止损: ${pos["stop_loss"]:.2f}')
        print(f'  目标: ${pos["target"]:.2f}')
    else:
        print(f'\n💼 持仓: 空仓')
    
    print(f'\n💰 账户:')
    print(f'  权益: ${portfolio["account"]["equity"]:.2f}')
    print(f'  可用: ${portfolio["account"]["cash_available"]:.2f}')
    print(f'  已实现盈亏: ${portfolio["account"]["realized_pnl"]:.2f}')

def run_once():
    """单次扫描"""
    perception = ChanlunPerception()
    portfolio = load_portfolio()
    
    analysis = analyze_crcl(perception)
    signals = generate_signal(analysis, portfolio)
    print_status(analysis, signals, portfolio)
    
    # 执行最强信号
    for sig in signals:
        if sig['type'] in ['BUY', 'SELL'] and sig['strength'] in ['STRONG', 'MEDIUM']:
            execute_signal(sig, analysis, portfolio)
            break

def run_loop(interval=300):
    """持续监控"""
    print('🚀 启动 CRCL 实时监控...')
    print(f'   扫描间隔: {interval}秒')
    print('   按 Ctrl+C 停止')
    
    while True:
        try:
            run_once()
            print(f'\n⏳ 下次扫描: {interval}秒后...')
            time.sleep(interval)
        except KeyboardInterrupt:
            print('\n🛑 监控已停止')
            break
        except Exception as e:
            print(f'\n❌ 错误: {e}')
            time.sleep(60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CRCL 缠论实时监控")
    parser.add_argument("--once", action="store_true", help="单次扫描")
    parser.add_argument("--loop", action="store_true", help="持续监控")
    parser.add_argument("--interval", type=int, default=300, help="扫描间隔（秒）")
    
    args = parser.parse_args()
    
    if args.loop:
        run_loop(args.interval)
    else:
        run_once()
