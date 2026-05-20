#!/usr/bin/env python3
"""
Finance Perception Skill - Quick Start Script
快速验证脚本，用于测试金融数据感知模块是否正常工作

Usage:
    python quick_start.py

Requirements:
    - finance_fetcher.py 在 ../global-info-fetcher/ 目录
    - SECRET.md 在项目根目录
"""

import sys
import json
from datetime import datetime

# 添加模块路径
sys.path.insert(0, '../global-info-fetcher')

try:
    from finance_fetcher import FinanceFetcher, FinanceSignalType
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保 finance_fetcher.py 在 ../global-info-fetcher/ 目录")
    sys.exit(1)


def print_separator(title: str = ""):
    """打印分隔符"""
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


def main():
    """主函数"""
    print_separator("Finance Perception Quick Start")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 初始化
    print("\n📦 初始化 FinanceFetcher...")
    try:
        fetcher = FinanceFetcher()
        print("✅ 初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)
    
    # 1. 健康检查
    print_separator("1. 健康检查")
    print("检查数据源状态...")
    try:
        health = fetcher.health_check()
        print("\n数据源状态:")
        for source, status in health.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {source}: {'正常' if status else '不可用'}")
    except Exception as e:
        print(f"⚠️ 健康检查失败: {e}")
        health = {}
    
    # 2. 获取报价
    print_separator("2. 行情查询")
    
    test_cases = [
        ("AAPL", "US", "Apple Inc."),
        ("TSLA", "US", "Tesla"),
        ("00700", "HK", "腾讯控股"),
        ("BTCUSDT", "CC", "Bitcoin"),
        ("ETHUSDT", "CC", "Ethereum"),
    ]
    
    for symbol, market, name in test_cases:
        try:
            quote = fetcher.get_quote(symbol, market)
            if quote:
                trend = "📈" if quote.change_pct > 0 else "📉" if quote.change_pct < 0 else "➡️"
                print(f"\n{trend} {name} ({symbol})")
                print(f"   价格: ${quote.price:.4f}" if market == "CC" else f"   价格: ${quote.price:.2f}")
                print(f"   涨跌: {quote.change_pct:+.2f}%")
                print(f"   来源: {quote.source}")
            else:
                print(f"\n⚠️ {name} ({symbol}): 无数据")
        except Exception as e:
            print(f"\n❌ {name} ({symbol}): {e}")
    
    # 3. K线数据
    print_separator("3. K线数据")
    try:
        klines = fetcher.get_kline("AAPL", "US", "101", limit=5)
        if klines:
            print(f"\nAAPL 日K线 (最近{len(klines)}条):")
            print("-" * 50)
            for bar in klines[-5:]:
                print(f"  {bar.timestamp[:10]}: O={bar.open:.2f} H={bar.high:.2f} "
                      f"L={bar.low:.2f} C={bar.close:.2f} V={bar.volume:,}")
        else:
            print("⚠️ 无K线数据")
    except Exception as e:
        print(f"❌ K线获取失败: {e}")
    
    # 4. 信号扫描
    print_separator("4. 信号扫描")
    watchlist = {
        "US": ["AAPL", "TSLA", "NVDA"],
        "CC": ["BTCUSDT", "ETHUSDT"],
    }
    
    print(f"\n监控列表: {json.dumps(watchlist, ensure_ascii=False)}")
    
    try:
        signals = fetcher.scan_signals(watchlist)
        print(f"\n检测到 {len(signals)} 个信号:")
        
        if signals:
            for sig in signals[:10]:  # 最多显示10个
                severity_icon = {
                    "critical": "🚨",
                    "high": "⚠️",
                    "medium": "⚡",
                    "low": "📝",
                    "info": "ℹ️"
                }.get(sig.severity, "•")
                
                print(f"\n{severity_icon} [{sig.severity.upper()}] {sig.title}")
                print(f"   标的: {sig.symbol}")
                print(f"   类型: {sig.signal_type}")
                if sig.summary:
                    print(f"   摘要: {sig.summary}")
        else:
            print("  未检测到异常信号")
    except Exception as e:
        print(f"❌ 信号扫描失败: {e}")
    
    # 5. 状态报告
    print_separator("5. 状态报告")
    try:
        report = fetcher.get_status_report()
        print(report)
    except Exception as e:
        print(f"❌ 获取状态报告失败: {e}")
    
    # 总结
    print_separator("完成")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n💡 提示:")
    print("   - 查看 health_daemon.py 进行定期健康检查")
    print("   - 查看 integration_guide.md 学习集成方式")
    print("   - 查看 provider_registry.md 了解数据源详情")


if __name__ == "__main__":
    main()
