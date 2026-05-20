#!/usr/bin/env python3
"""
缠论元交易系统 - 主入口
Phase 3: 多Agent框架 + 金融数据感知层

使用方式:
1. 无网络环境（测试）: python3 main.py --mock
2. 有网络环境（实盘）: python3 main.py --scan
3. 分析指定品种: python3 main.py --symbol AAPL --market US

Author: VAN's Trading Assistant
Version: 1.0.0
"""

import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from chanlun_perception import ChanlunPerception

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ChanlunAgent")

def run_mock_mode():
    """测试模式（无网络）"""
    print("=" * 60)
    print("🧠 缠论元交易系统 v1.0 [Mock Mode]")
    print("=" * 60)
    print()
    
    perception = ChanlunPerception()
    perception.fetcher = None  # 使用 mock 数据
    
    # 测试品种
    test_symbols = [
        {"symbol": "TEST_A50", "market": "FUTURES"},
        {"symbol": "TEST_BTC", "market": "CC"},
        {"symbol": "TEST_NVDA", "market": "US"},
    ]
    
    print("📊 使用模拟数据测试...\n")
    
    all_signals = []
    for item in test_symbols:
        symbol = item["symbol"]
        market = item["market"]
        
        print(f"🔍 分析 {symbol} ({market})...")
        structures = perception.analyze_symbol(symbol, market, ["日线", "30分钟", "5分钟"])
        
        for freq, structure in structures.items():
            print(f"  【{freq}】")
            print(f"    趋势: {structure.trend}")
            print(f"    笔: {structure.bi_count} | 中枢: {structure.zs_count}")
            print(f"    最后一笔: {structure.last_bi_direction}")
            if structure.last_zs_range:
                print(f"    中枢区间: [{structure.last_zs_range[0]:.2f}, {structure.last_zs_range[1]:.2f}]")
            print(f"    背驰: {'是 ⚠️' if structure.divergence else '否'}")
            
            # 生成信号
            signals = perception._generate_signals(symbol, market, {freq: structure})
            all_signals.extend(signals)
        
        print()
    
    # 生成报告
    report = perception.generate_report(all_signals)
    print(report)
    
    # 保存报告
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"{datetime.now().strftime('%Y%m%d_%H%M')}_mock.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Mock 测试完成，报告已保存: {report_path}")
    
    # 输出信号统计
    if all_signals:
        print(f"\n📡 检测到 {len(all_signals)} 个信号：")
        for sig in all_signals:
            emoji = {"divergence_top": "🔴", "divergence_bottom": "🟢", "zs_range": "🟡"}.get(sig.signal_type, "⚡")
            print(f"  {emoji} [{sig.signal_type}] {sig.symbol} ({sig.freq}): {sig.description}")

def run_scan_mode():
    """实盘扫描模式"""
    print("=" * 60)
    print("🧠 缠论元交易系统 v1.0 [Live Scan]")
    print("=" * 60)
    print()
    
    perception = ChanlunPerception()
    
    print("📊 扫描关注品种...\n")
    
    signals = perception.scan_signals()
    report = perception.generate_report(signals)
    print(report)
    
    # 保存报告
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ 报告已保存: {report_path}")

def run_symbol_analysis(symbol: str, market: str):
    """分析指定品种"""
    print(f"📊 分析 {symbol} ({market})...")
    print()
    
    perception = ChanlunPerception()
    structures = perception.analyze_symbol(symbol, market, ["日线", "30分钟", "5分钟"])
    
    for freq, structure in structures.items():
        print(f"【{freq}】")
        print(f"  趋势: {structure.trend}")
        print(f"  笔: {structure.bi_count} | 中枢: {structure.zs_count}")
        print(f"  最后一笔: {structure.last_bi_direction}")
        if structure.last_zs_range:
            print(f"  中枢区间: [{structure.last_zs_range[0]:.2f}, {structure.last_zs_range[1]:.2f}]")
        print(f"  背驰: {'是 ⚠️' if structure.divergence else '否'}")
        print()

def main():
    parser = argparse.ArgumentParser(description="缠论元交易系统")
    parser.add_argument("--mock", action="store_true", help="测试模式（使用模拟数据）")
    parser.add_argument("--scan", action="store_true", help="扫描所有关注品种")
    parser.add_argument("--symbol", type=str, help="分析指定品种")
    parser.add_argument("--market", type=str, default="US", help="市场 (US/HK/SH/SZ/CC)")
    
    args = parser.parse_args()
    
    if args.mock:
        run_mock_mode()
    elif args.scan:
        run_scan_mode()
    elif args.symbol:
        run_symbol_analysis(args.symbol, args.market)
    else:
        # 默认使用测试模式
        run_mock_mode()

if __name__ == "__main__":
    main()
