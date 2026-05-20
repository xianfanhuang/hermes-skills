#!/usr/bin/env python3
"""
Trading Cost Reference - 交易成本参考表

基于 Tiger 费率标准（模拟盘/实盘通用）
用于交易品种性价比参考

Author: Trading Assistant
Version: 1.0.0
"""

from typing import Dict
from dataclasses import dataclass


@dataclass
class CostProfile:
    """成本结构"""
    name: str
    buy_rate: float  # 买入费率
    sell_rate: float  # 卖出费率
    min_fee: float  # 最低收费
    notes: str


# Tiger 交易成本参考 (美股/港股/期货)
# 基于官方费率文档，实际可能有优惠
TIGER_COST_TABLE: Dict[str, CostProfile] = {
    # 美股
    "US_STOCK": CostProfile(
        name="美股",
        buy_rate=0.0008,   # 0.08%
        sell_rate=0.0008,  # 0.08%
        min_fee=0.99,
        notes="平台费+佣金+外部代收，模拟盘显示约0.14%"
    ),
    
    # 美股ETF
    "US_ETF": CostProfile(
        name="美股ETF",
        buy_rate=0.0008,   # 0.08%
        sell_rate=0.0008,  # 0.08%
        min_fee=0.99,
        notes="与美股股票相同费率"
    ),
    
    # 港股
    "HK_STOCK": CostProfile(
        name="港股",
        buy_rate=0.0003,   # 0.03%
        sell_rate=0.0003,  # 0.03%
        min_fee=3.0,
        notes="平台费0.03%，另有印花税0.1%、交收费0.002%、证监会费0.0027%"
    ),
    
    # 港股ETF
    "HK_ETF": CostProfile(
        name="港股ETF",
        buy_rate=0.0003,   # 0.03%
        sell_rate=0.0003,  # 0.03%
        min_fee=3.0,
        notes="与港股股票相同"
    ),
    
    # 美国期货
    "US_FUTURE": CostProfile(
        name="美期",
        buy_rate=0.0005,   # 约0.05% (按保证金估算)
        sell_rate=0.0005,
        min_fee=2.99,
        notes="期货手续费按合约收取，约$2.99-$5.99/手，非比例费率"
    ),
    
    # 港股期货
    "HK_FUTURE": CostProfile(
        name="港期",
        buy_rate=0.0005,
        sell_rate=0.0005,
        min_fee=15.0,  # HKD
        notes="港股期货手续费约HKD15-30/手"
    ),
    
    # 期权
    "US_OPTION": CostProfile(
        name="美股期权",
        buy_rate=0.0000,  # 非比例
        sell_rate=0.0000,
        min_fee=0.95,
        notes="按合约收费 $0.95-$2.95/张，复杂期权可能更高"
    ),
}


def estimate_cost(category: str, notional: float, action: str = "BOTH") -> Dict:
    """
    预估交易成本
    
    Args:
        category: 品类代码 (US_STOCK, HK_STOCK, etc.)
        notional: 交易金额
        action: BUY/SELL/BOTH
    
    Returns:
        成本预估
    """
    profile = TIGER_COST_TABLE.get(category)
    if not profile:
        return {
            "category": category,
            "error": "品类不存在",
            "available": list(TIGER_COST_TABLE.keys())
        }
    
    action = action.upper()
    
    if action == "BUY":
        fee = max(notional * profile.buy_rate, profile.min_fee)
        rate = profile.buy_rate
    elif action == "SELL":
        fee = max(notional * profile.sell_rate, profile.min_fee)
        rate = profile.sell_rate
    else:  # BOTH
        buy_fee = max(notional * profile.buy_rate, profile.min_fee)
        sell_fee = max(notional * profile.sell_rate, profile.min_fee)
        fee = buy_fee + sell_fee
        rate = (profile.buy_rate + profile.sell_rate)
    
    return {
        "category": profile.name,
        "notional": notional,
        "action": action,
        "estimated_fee": round(fee, 2),
        "fee_rate": f"{rate*100:.4f}%",
        "min_fee": profile.min_fee,
        "notes": profile.notes,
    }


def get_cost_comparison(notional: float = 10000) -> str:
    """
    生成各品类成本对比表
    
    Args:
        notional: 交易金额（默认$10,000）
    """
    lines = [
        "=" * 70,
        f"📊 交易成本对比表（交易金额: ${notional:,.0f}）",
        "=" * 70,
        "",
        f"{'品类':<12} {'买入费':<10} {'卖出费':<10} {'双向合计':<12} {'费率':<10} 说明",
        "-" * 70,
    ]
    
    for code, profile in TIGER_COST_TABLE.items():
        buy = estimate_cost(code, notional, "BUY")
        sell = estimate_cost(code, notional, "SELL")
        both = estimate_cost(code, notional, "BOTH")
        
        lines.append(
            f"{profile.name:<10} ${buy['estimated_fee']:<9.2f} ${sell['estimated_fee']:<9.2f} "
            f"${both['estimated_fee']:<10.2f} {both['fee_rate']:<8} {profile.notes[:25]}"
        )
    
    lines.extend([
        "",
        "=" * 70,
        "💡 说明:",
        "- 以上费率为 Tiger 标准费率，实际可能有优惠",
        "- 港股额外有印花税0.1%、交收费等政府代收费用",
        "- 期货/期权非比例收费，按合约收取",
        "- 模拟盘费率可能与实盘略有差异",
        "=" * 70,
    ])
    
    return '\n'.join(lines)


def get_recommendation(notional: float = 10000, trade_frequency: str = "medium") -> str:
    """
    获取品种性价比推荐
    
    Args:
        notional: 交易金额
        trade_frequency: low/medium/high (低频/中频/高频)
    """
    freq_multiplier = {
        "low": 1,
        "medium": 5,
        "high": 20
    }.get(trade_frequency, 5)
    
    lines = [
        "=" * 60,
        f"🎯 交易品种性价比推荐（金额${notional:,.0f}, 频率{trade_frequency}）",
        "=" * 60,
        "",
    ]
    
    # 计算综合成本
    costs = []
    for code, profile in TIGER_COST_TABLE.items():
        both = estimate_cost(code, notional, "BOTH")
        annual_cost = both['estimated_fee'] * freq_multiplier * 12  # 年度预估
        costs.append((profile.name, both['estimated_fee'], annual_cost, both['fee_rate']))
    
    # 按成本排序
    costs.sort(key=lambda x: x[1])
    
    lines.append("按单笔成本排序（低到高）:")
    lines.append("")
    for i, (name, per_trade, annual, rate) in enumerate(costs, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        lines.append(f"{emoji} {name:<10} 单笔${per_trade:<8.2f} 年度~${annual:<10,.0f} ({rate})")
    
    lines.extend([
        "",
        "=" * 60,
        "📌 建议:",
    ])
    
    if trade_frequency == "high":
        lines.append("- 高频交易：优先选择港股（费率最低）")
        lines.append("- 避免频繁交易美股期权（按合约收费）")
    elif trade_frequency == "medium":
        lines.append("- 中频交易：美股ETF流动性好，费率适中")
        lines.append("- 港股适合波段操作")
    else:
        lines.append("- 低频交易：费率影响小，优先看波动性和流动性")
    
    lines.append("=" * 60)
    
    return '\n'.join(lines)


if __name__ == "__main__":
    # 打印成本对比表
    print(get_cost_comparison(10000))
    
    print("\n")
    print(get_recommendation(10000, "medium"))
