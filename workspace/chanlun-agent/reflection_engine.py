#!/usr/bin/env python3
"""
自动反思引擎
ChanlunAgent MVP - Day 22+ 自进化闭环

功能：
1. 交易后自动反思（平仓后5分钟内）
2. 连续亏损深度反思（连亏3笔触发）
3. 周度反思汇总（每周日）
4. 参数优化建议

Author: Trading Assistant
Version: 1.0.0
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from store import TokenStore

logger = logging.getLogger("ReflectionEngine")


class ReflectionEngine:
    """自动反思引擎"""

    def __init__(self, store: TokenStore):
        self.store = store

    def generate_post_trade_reflection(self, trade: Dict) -> str:
        """
        交易后自动反思
        平仓后自动生成结构化反思
        """
        symbol = trade.get('symbol', 'N/A')
        direction = trade.get('direction', 'N/A')
        entry_price = trade.get('entry_price', 0)
        exit_price = trade.get('exit_price', 0)
        pnl = trade.get('pnl', 0) or 0
        pnl_pct = trade.get('pnl_pct', 0) or 0
        signal_type = trade.get('signal_type', 'N/A')

        # 结构化反思
        reflection = f"""## {datetime.now().strftime('%Y-%m-%d')} {symbol} {direction} {'✅盈利' if pnl > 0 else '❌亏损'} {pnl_pct:+.2f}%

### 结构分析
- 入场价: ${entry_price:.2f} | 出场价: ${exit_price:.2f}
- 信号类型: {signal_type}
- 盈亏: ${pnl:.2f} ({pnl_pct:+.2f}%)

### 决策回顾
- 入场理由: {signal_type} 信号触发
- 出场理由: {'止盈' if pnl > 0 else '止损/信号反转'}

### 归因分析
- {'盈利主要来自缠论结构判断准确' if pnl > 0 else '亏损原因需要进一步分析市场环境和信号质量'}

### 改进措施
- {'保持当前策略参数' if pnl > 0 else '检查止损设置是否合理，信号过滤是否需要加强'}
"""

        # 存储反思
        self.store.log_reflection(
            trade.get('trade_id', ''),
            "post_trade",
            reflection,
            {"pnl": pnl, "pnl_pct": pnl_pct, "symbol": symbol}
        )

        return reflection

    def generate_consecutive_loss_reflection(self) -> str:
        """
        连续亏损深度反思
        连亏3笔时触发
        """
        trades = self.store.get_trades(status='closed', limit=5)
        stats = self.store.get_trade_stats() or {}

        # 分析亏损模式
        loss_trades = [t for t in trades if (t.get('pnl') or 0) < 0]
        
        reflection = f"""## ⚠️ 连续亏损深度反思 - {datetime.now().strftime('%Y-%m-%d %H:%M')}

### 亏损统计
- 连续亏损: {len(loss_trades)} 笔
- 总交易: {stats.get('total_trades', 0)}
- 胜率: {stats.get('win_rate', 0):.1f}%
- 盈亏比: {stats.get('profit_factor', 0):.2f}

### 亏损交易分析
"""
        for t in loss_trades[:3]:
            reflection += f"- {t.get('symbol', 'N/A')} {t.get('direction', 'N/A')} | "
            reflection += f"信号: {t.get('signal_type', 'N/A')} | "
            reflection += f"亏损: {t.get('pnl_pct', 0):+.2f}%\n"

        reflection += """
### 可能原因
1. 市场环境变化（趋势转震荡或反之）
2. 信号过滤不够严格（低质量信号入场）
3. 止损设置过紧（频繁被扫损）
4. 仓位过大（单笔风险过高）

### 建议措施
1. 暂停交易60分钟，冷静分析
2. 降低仓位至原来的50%
3. 提高信号级别要求（只做L3+信号）
4. 检查是否需要调整止损参数

### 参数调整建议
- 当前止损: 3% → 建议: 保持或放宽至4%
- 当前信号级别: L2+ → 建议: 提高至L3+
- 当前仓位: 50%最大 → 建议: 降至30%
"""

        self.store.log_reflection(
            "",
            "consecutive_loss",
            reflection,
            {"loss_count": len(loss_trades), "win_rate": stats.get('win_rate', 0)}
        )

        return reflection

    def generate_weekly_reflection(self) -> str:
        """
        周度反思汇总
        每周日生成
        """
        # 获取本周交易
        week_ago = datetime.now() - timedelta(days=7)
        all_trades = self.store.get_trades(limit=100)
        week_trades = [
            t for t in all_trades 
            if t.get('exit_time') and t['exit_time'] > week_ago.isoformat()
        ]

        stats = self.store.get_trade_stats() or {}

        winning = [t for t in week_trades if (t.get('pnl') or 0) > 0]
        losing = [t for t in week_trades if (t.get('pnl') or 0) < 0]

        total_pnl = sum(t.get('pnl', 0) or 0 for t in week_trades)
        avg_win = sum(t.get('pnl', 0) or 0 for t in winning) / len(winning) if winning else 0
        avg_loss = sum(t.get('pnl', 0) or 0 for t in losing) / len(losing) if losing else 0

        reflection = f"""## 📊 周度反思汇总 - {datetime.now().strftime('%Y-%m-%d')}

### 本周概况
- 总交易: {len(week_trades)} 笔
- 盈利: {len(winning)} 笔 | 亏损: {len(losing)} 笔
- 胜率: {len(winning)/len(week_trades)*100:.1f}% (如本周有交易)
- 总盈亏: ${total_pnl:.2f}

### 盈亏分析
- 平均盈利: ${avg_win:.2f}
- 平均亏损: ${avg_loss:.2f}
- 盈亏比: {abs(avg_win/avg_loss):.2f} (如适用)

### 信号类型统计
"""
        # 统计各信号类型
        signal_stats = {}
        for t in week_trades:
            st = t.get('signal_type', 'unknown')
            if st not in signal_stats:
                signal_stats[st] = {"count": 0, "wins": 0, "total_pnl": 0}
            signal_stats[st]["count"] += 1
            if (t.get('pnl') or 0) > 0:
                signal_stats[st]["wins"] += 1
            signal_stats[st]["total_pnl"] += t.get('pnl', 0) or 0

        for st, data in signal_stats.items():
            win_rate = data["wins"] / data["count"] * 100 if data["count"] > 0 else 0
            reflection += f"- {st}: {data['count']}笔, 胜率{win_rate:.0f}%, 盈亏${data['total_pnl']:.2f}\n"

        reflection += """
### 改进方向
1. 分析盈利交易的共同特征，强化信号过滤
2. 分析亏损交易的原因，避免重复错误
3. 评估当前参数是否需要调整
4. 考虑是否需要增加新的信号类型

### 下周计划
- 保持/调整止损参数
- 优化信号过滤规则
- 关注市场环境变化
"""

        self.store.log_reflection(
            "",
            "weekly",
            reflection,
            {"week_trades": len(week_trades), "total_pnl": total_pnl}
        )

        return reflection

    def get_optimization_suggestions(self) -> Dict:
        """
        基于历史数据生成参数优化建议
        """
        stats = self.store.get_trade_stats() or {}
        trades = self.store.get_trades(status='closed', limit=50)

        suggestions = {
            "止损参数": {},
            "信号过滤": {},
            "仓位管理": {},
            "总体建议": []
        }

        win_rate = stats.get('win_rate', 0) or 0
        profit_factor = stats.get('profit_factor', 0) or 0

        # 止损建议
        if win_rate < 40:
            suggestions["止损参数"]["建议"] = "胜率偏低，考虑放宽止损至4%"
            suggestions["止损参数"]["当前"] = "3%"
        elif win_rate > 60:
            suggestions["止损参数"]["建议"] = "胜率良好，可保持当前设置"
            suggestions["止损参数"]["当前"] = "3%"

        # 信号过滤建议
        if profit_factor < 1.0:
            suggestions["信号过滤"]["建议"] = "盈亏比<1，需要提高信号质量，只做L3+信号"
        elif profit_factor > 1.5:
            suggestions["信号过滤"]["建议"] = "盈亏比良好，可保持当前信号级别"

        # 仓位建议
        if win_rate < 45:
            suggestions["仓位管理"]["建议"] = "降低最大仓位至30%"
            suggestions["仓位管理"]["当前"] = "50%"
        else:
            suggestions["仓位管理"]["建议"] = "可保持当前仓位设置"
            suggestions["仓位管理"]["当前"] = "50%"

        # 总体建议
        if win_rate > 50 and profit_factor > 1.2:
            suggestions["总体建议"].append("策略运行良好，保持纪律执行")
        elif win_rate < 40:
            suggestions["总体建议"].append("需要提高信号过滤标准")
            suggestions["总体建议"].append("考虑暂停交易，分析市场环境")
        
        if stats.get('total_trades', 0) > 20:
            suggestions["总体建议"].append("已有足够样本，可考虑参数微调")

        return suggestions


# ============ 测试 ============

if __name__ == "__main__":
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db = f.name

    store = TokenStore(test_db)
    engine = ReflectionEngine(store)

    # 测试交易后反思
    trade = {
        "trade_id": "T001",
        "symbol": "CRCL",
        "direction": "long",
        "entry_price": 110.0,
        "exit_price": 115.0,
        "pnl": 500,
        "pnl_pct": 4.55,
        "signal_type": "bi_buy"
    }
    reflection = engine.generate_post_trade_reflection(trade)
    print("=== 交易后反思 ===")
    print(reflection[:200] + "...")

    # 测试优化建议
    suggestions = engine.get_optimization_suggestions()
    print("\n=== 优化建议 ===")
    print(json.dumps(suggestions, indent=2, ensure_ascii=False))

    os.unlink(test_db)
    print("\n✅ 反思引擎测试完成")
