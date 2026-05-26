#!/usr/bin/env python3
"""
智能级别确立 — 盘中调试工具

Usage:
    python3 structure_debug.py --symbol CRCL
    python3 structure_debug.py --symbol CRCL --timeframe daily
    python3 structure_debug.py --symbol 01810 --market HK
    python3 structure_debug.py --symbol CRCL --full

输出：
    - 各级别结构状态（趋势/盘整/转折）
    - 买卖点检测
    - 策略建议（跟趋势/等突破/捕反转）
    - 共振状态
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

try:
    import czsc
    from czsc import CZSC, Freq, format_standard_kline, RawBar
    HAS_CZSC = True
except ImportError:
    HAS_CZSC = False

from czsc_extension import CzscExtension, StructureState


def get_bars(symbol: str, market: str, timeframe: str, limit: int = 200):
    """获取K线数据"""
    try:
        from chanlun_perception import ChanlunPerception
        p = ChanlunPerception()

        tf_map = {'daily': '1d', '30min': '30m', '5min': '5m', '1min': '1m'}
        tf_code = tf_map.get(timeframe, '1d')

        klines = p.get_kline_data(symbol, market, tf_code, limit=limit)
        if not klines:
            return None

        import pandas as pd
        df = pd.DataFrame(klines)
        df['dt'] = pd.to_datetime(df['timestamp'])
        df['symbol'] = symbol
        df['amount'] = df['vol'] * df['close']
        df = df[['dt', 'symbol', 'open', 'high', 'low', 'close', 'vol', 'amount']].copy()

        freq_map = {'daily': Freq.D, '30min': Freq.F30, '5min': Freq.F5, '1min': Freq.F1}
        bars = format_standard_kline(df, freq=freq_map.get(timeframe, Freq.D))
        return bars
    except Exception as e:
        print(f"⚠️ 获取数据失败: {e}")
        return None


def analyze_structure(symbol: str, market: str, timeframes: list, full: bool = False):
    """分析多级别结构"""

    results = {}
    all_states = {}

    for tf in timeframes:
        print(f"\n{'─'*50}")
        print(f"📊 {symbol} {tf} 分析")
        print(f"{'─'*50}")

        bars = get_bars(symbol, market, tf)
        if not bars:
            print(f"  ❌ 数据不足")
            continue

        ka = CZSC(bars)
        ext = CzscExtension(ka, symbol=symbol, timeframe=tf)
        analysis = ext.full_analysis()

        results[tf] = analysis
        all_states[tf] = analysis.get('structure_state', 'unknown')

        # 输出核心信息
        state_emoji = {'trending': '📈', 'ranging': '↔️', 'turning': '🔄', 'unknown': '❓'}
        print(f"  {state_emoji.get(analysis['structure_state'], '?')} 结构: {analysis['structure_state']}")
        print(f"  📍 方向: {analysis['trend_direction'] or '无'}")
        print(f"  💪 强度: {analysis['trend_strength']:.1%}")
        print(f"  🔢 中枢运动: {analysis['zs_movement']}")
        print(f"  📝 {analysis['detail']}")

        # 流畅度（VAN核心洞察）
        fluency = analysis.get('trend_fluency', {})
        if fluency:
            smooth_emoji = '🌊' if fluency.get('is_smooth') else '🌊⚠️'
            print(f"  {smooth_emoji} 流畅度: {fluency.get('fluency', 0):.1%} | {fluency.get('detail', '')}")
            if fluency.get('is_smooth'):
                print(f"     → 流畅趋势，锁定{tf}级别，这是主力目标！")
                print(f"     → 中枢重叠{fluency.get('zs_overlap_ratio', 0):.0%} | 回调深度{fluency.get('pullback_depth', 0):.0%} | 方向一致{fluency.get('direction_consistency', 0):.0%}")

        # 中枢信息
        if analysis['last_zs']:
            zs = analysis['last_zs']
            print(f"  📦 最后中枢: [{zs['zd']:.2f}, {zs['zg']:.2f}]")

        # 背驰
        div = analysis['divergence']
        if div.get('detected'):
            print(f"  ⚡ 背驰: {div.get('detail', '')}")

        # 买卖点
        if analysis['buy_sell_points']:
            for bsp in analysis['buy_sell_points']:
                print(f"  📍 {bsp['type']}: ${bsp['price']:.2f} [{bsp['direction']}] 置信度{bsp['confidence']:.0%}")

        # 建议
        print(f"  🎯 建议: 跟趋势={analysis['should_follow_trend']} | 等突破={analysis['should_wait_breakout']} | 捕反转={analysis['should_catch_reversal']}")

        if full:
            print(f"\n  笔数: {analysis['bi_count']} | 中枢数: {analysis['zs_count']}")
            if analysis['last_bi']:
                bi = analysis['last_bi']
                print(f"  最后一笔: {bi['direction']} [{bi['low']:.2f}, {bi['high']:.2f}]")

    # ===== 综合判断 =====
    print(f"\n{'='*50}")
    print(f"🧠 智能级别确立 — 综合判断")
    print(f"{'='*50}")

    daily_s = all_states.get('daily', 'unknown')
    m30_s = all_states.get('30min', 'unknown')
    m5_s = all_states.get('5min', 'unknown')

    print(f"  日线: {daily_s} | 30分钟: {m30_s} | 5分钟: {m5_s}")

    # 策略判断
    if daily_s == 'trending':
        daily_dir = results.get('daily', {}).get('trend_direction')
        strength = results.get('daily', {}).get('trend_strength', 0)
        fluency = results.get('daily', {}).get('trend_fluency', {})
        is_smooth = fluency.get('is_smooth', False)

        print(f"\n  ✅ 策略: 趋势跟随")
        print(f"     日线{daily_dir}趋势，强度{strength:.0%}")

        if is_smooth:
            print(f"     🌊 流畅趋势! 这是主力目标")
            print(f"     → 锁定最小级别（5分钟），不放大")
            print(f"     → 流畅趋势=小级别长时间延续")
            print(f"     → 持续{fluency.get('continuation_bars', '?')}根K线")
        else:
            print(f"     ⚠️ 趋势不流畅，笔笔混乱")
            print(f"     → 谨慎跟随，可能需要放大级别确认")

        print(f"     → 止损设在5分钟中枢外沿")

        if m5_s == 'trending':
            m5_dir = results.get('5min', {}).get('trend_direction')
            if m5_dir == daily_dir:
                print(f"     → ✅ 5分钟同向确认，高置信度")
            else:
                print(f"     → ⚠️ 5分钟方向{m5_dir}，需谨慎")

    elif daily_s == 'turning':
        div = results.get('daily', {}).get('divergence', {})
        print(f"\n  ✅ 策略: 反转捕捉")
        print(f"     {div.get('detail', '背驰出现')}")
        print(f"     → 缩小到30分钟精确入场")
        print(f"     → 止损设在背驰极值")

    elif daily_s == 'ranging':
        if m30_s == 'trending':
            m30_dir = results.get('30min', {}).get('trend_direction')
            print(f"\n  ✅ 策略: 盘整突破")
            print(f"     日线盘整，30分钟{m30_dir}")
            print(f"     → 用30分钟方向做短线")
            print(f"     → 止损设在中枢内沿（紧止损）")
        elif m5_s == 'trending':
            m5_dir = results.get('5min', {}).get('trend_direction')
            print(f"\n  ✅ 策略: 盘整内短线")
            print(f"     日线盘整，5分钟{m5_dir}")
            print(f"     → 用5分钟做超短线")
        else:
            print(f"\n  ⏸️ 策略: 等待")
            print(f"     各级别均盘整，无明确方向")
            print(f"     → 不交易，等突破")

    else:
        print(f"\n  ❓ 数据不足，无法判断")

    return results


def main():
    parser = argparse.ArgumentParser(description="智能级别确立调试工具")
    parser.add_argument("--symbol", "-s", default="CRCL", help="品种代码")
    parser.add_argument("--market", "-m", default="US", choices=["US", "HK", "CN"], help="市场")
    parser.add_argument("--timeframe", "-t", help="单个时间级别 (daily/30min/5min)")
    parser.add_argument("--full", "-f", action="store_true", help="完整分析")
    parser.add_argument("--json", "-j", action="store_true", help="JSON输出")

    args = parser.parse_args()

    if not HAS_CZSC:
        print("❌ 需要安装 czsc: pip install czsc")
        sys.exit(1)

    if args.timeframe:
        timeframes = [args.timeframe]
    else:
        timeframes = ['daily', '30min', '5min']

    print(f"🦞 智能级别确立调试")
    print(f"   品种: {args.symbol} ({args.market})")
    print(f"   级别: {', '.join(timeframes)}")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = analyze_structure(args.symbol, args.market, timeframes, full=args.full)

    if args.json:
        # 过滤不可序列化的字段
        clean = {}
        for tf, r in results.items():
            clean[tf] = {k: v for k, v in r.items() if k not in ('bars',)}
        print(f"\n{json.dumps(clean, indent=2, ensure_ascii=False, default=str)}")


if __name__ == "__main__":
    main()
