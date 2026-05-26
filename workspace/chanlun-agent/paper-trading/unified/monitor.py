#!/usr/bin/env python3
"""
统一监控入口

Usage:
    python3 monitor.py --list              # 列出标的
    python3 monitor.py --add 01810 小米 HK  # 添加标的
    python3 monitor.py --remove 01810       # 移除标的
    python3 monitor.py --analyze CRCL       # 分析标的
    python3 monitor.py --run                # 启动监控
"""

from engine import TradingEngine, main

if __name__ == '__main__':
    main()
