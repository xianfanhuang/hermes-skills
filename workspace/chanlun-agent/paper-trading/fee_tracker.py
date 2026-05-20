#!/usr/bin/env python3
"""
Fee Tracker - 自动费率统计与成本结构分析

功能:
1. 自动计算每笔交易的费率
2. 按品种统计成本结构
3. 随交易增加自动校准费率
4. 提供交易成本预估

Author: Trading Assistant
Version: 1.0.0
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger("FeeTracker")

# 数据文件路径
FEE_DB_PATH = Path(__file__).parent / "fee_database.json"


@dataclass
class TradeRecord:
    """交易记录"""
    symbol: str
    action: str  # BUY/SELL
    quantity: int
    price: float
    notional: float  # 成交金额
    fee_total: float  # 总费用
    fee_breakdown: Dict[str, float]  # 费用明细
    trade_time: str
    order_id: str


@dataclass
class SymbolCostStructure:
    """品种成本结构"""
    symbol: str
    trade_count: int = 0
    total_notional: float = 0.0  # 总成交金额
    total_fees: float = 0.0  # 总费用
    avg_fee_rate: float = 0.0  # 平均费率
    buy_fee_rate: float = 0.0  # 买入费率
    sell_fee_rate: float = 0.0  # 卖出费率
    fee_breakdown_avg: Dict[str, float] = None  # 平均费用结构
    last_updated: str = ""
    
    def __post_init__(self):
        if self.fee_breakdown_avg is None:
            self.fee_breakdown_avg = {}


class FeeTracker:
    """费率追踪器"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or FEE_DB_PATH
        self.trades: List[TradeRecord] = []
        self.cost_structures: Dict[str, SymbolCostStructure] = {}
        self._load_db()
    
    def _load_db(self):
        """加载数据库"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 加载交易记录
                    for t in data.get('trades', []):
                        self.trades.append(TradeRecord(**t))
                    # 加载成本结构
                    for symbol, cs in data.get('cost_structures', {}).items():
                        self.cost_structures[symbol] = SymbolCostStructure(**cs)
                logger.info(f"📊 费率数据库加载: {len(self.trades)}笔交易, {len(self.cost_structures)}个品种")
            except Exception as e:
                logger.error(f"加载费率数据库失败: {e}")
    
    def _save_db(self):
        """保存数据库"""
        try:
            data = {
                'trades': [asdict(t) for t in self.trades],
                'cost_structures': {s: asdict(cs) for s, cs in self.cost_structures.items()},
                'last_updated': datetime.now().isoformat(),
            }
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存费率数据库失败: {e}")
    
    def add_trade(self, symbol: str, action: str, quantity: int, 
                  price: float, fee_total: float, 
                  fee_breakdown: Dict[str, float] = None,
                  trade_time: str = None, order_id: str = None):
        """
        添加交易记录
        
        Args:
            symbol: 品种代码
            action: BUY/SELL
            quantity: 数量
            price: 成交价格
            fee_total: 总费用
            fee_breakdown: 费用明细（老虎收费/佣金/平台费等）
            trade_time: 交易时间
            order_id: 订单ID
        """
        notional = quantity * price
        
        trade = TradeRecord(
            symbol=symbol,
            action=action.upper(),
            quantity=quantity,
            price=price,
            notional=notional,
            fee_total=fee_total,
            fee_breakdown=fee_breakdown or {},
            trade_time=trade_time or datetime.now().isoformat(),
            order_id=order_id or "",
        )
        
        self.trades.append(trade)
        self._update_cost_structure(trade)
        self._save_db()
        
        fee_rate = (fee_total / notional * 100) if notional > 0 else 0
        logger.info(f"💰 交易记录: {symbol} {action} ${notional:,.2f}, 费用: ${fee_total:.2f} ({fee_rate:.3f}%)")
    
    def _update_cost_structure(self, trade: TradeRecord):
        """更新品种成本结构"""
        symbol = trade.symbol
        
        if symbol not in self.cost_structures:
            self.cost_structures[symbol] = SymbolCostStructure(symbol=symbol)
        
        cs = self.cost_structures[symbol]
        cs.trade_count += 1
        cs.total_notional += trade.notional
        cs.total_fees += trade.fee_total
        cs.last_updated = datetime.now().isoformat()
        
        # 计算平均费率
        if cs.total_notional > 0:
            cs.avg_fee_rate = cs.total_fees / cs.total_notional
        
        # 区分买卖费率
        symbol_trades = [t for t in self.trades if t.symbol == symbol]
        buy_trades = [t for t in symbol_trades if t.action == 'BUY']
        sell_trades = [t for t in symbol_trades if t.action == 'SELL']
        
        buy_notional = sum(t.notional for t in buy_trades)
        buy_fees = sum(t.fee_total for t in buy_trades)
        sell_notional = sum(t.notional for t in sell_trades)
        sell_fees = sum(t.fee_total for t in sell_trades)
        
        if buy_notional > 0:
            cs.buy_fee_rate = buy_fees / buy_notional
        if sell_notional > 0:
            cs.sell_fee_rate = sell_fees / sell_notional
        
        # 更新费用结构明细
        if trade.fee_breakdown:
            for fee_type, amount in trade.fee_breakdown.items():
                if fee_type not in cs.fee_breakdown_avg:
                    cs.fee_breakdown_avg[fee_type] = 0.0
                # 加权平均
                cs.fee_breakdown_avg[fee_type] = (
                    (cs.fee_breakdown_avg[fee_type] * (cs.trade_count - 1) + amount) / cs.trade_count
                )
    
    def get_cost_structure(self, symbol: str) -> Optional[SymbolCostStructure]:
        """获取品种成本结构"""
        return self.cost_structures.get(symbol)
    
    def estimate_cost(self, symbol: str, notional: float, action: str = "BUY") -> Dict:
        """
        预估交易成本
        
        Args:
            symbol: 品种代码
            notional: 预估成交金额
            action: BUY/SELL
        
        Returns:
            成本预估详情
        """
        cs = self.cost_structures.get(symbol)
        
        if cs is None or cs.trade_count < 1:
            # 无历史数据，使用默认值
            return {
                'symbol': symbol,
                'notional': notional,
                'action': action,
                'estimated_fee': notional * 0.0014,  # 默认0.14%
                'estimated_fee_rate': 0.0014,
                'confidence': 'low',
                'note': '无历史交易数据，使用默认费率0.14%',
            }
        
        # 使用历史费率
        if action.upper() == 'BUY' and cs.buy_fee_rate > 0:
            rate = cs.buy_fee_rate
        elif action.upper() == 'SELL' and cs.sell_fee_rate > 0:
            rate = cs.sell_fee_rate
        else:
            rate = cs.avg_fee_rate
        
        confidence = 'high' if cs.trade_count >= 10 else 'medium' if cs.trade_count >= 3 else 'low'
        
        return {
            'symbol': symbol,
            'notional': notional,
            'action': action,
            'estimated_fee': notional * rate,
            'estimated_fee_rate': rate,
            'historical_avg_rate': cs.avg_fee_rate,
            'trade_count': cs.trade_count,
            'confidence': confidence,
            'fee_breakdown_avg': cs.fee_breakdown_avg,
        }
    
    def get_report(self) -> str:
        """生成费率统计报告"""
        lines = ["=" * 60, "📊 费率统计报告", "=" * 60, ""]
        
        if not self.cost_structures:
            lines.append("暂无交易数据")
            return '\n'.join(lines)
        
        for symbol, cs in sorted(self.cost_structures.items()):
            lines.append(f"\n【{symbol}】")
            lines.append(f"  交易次数: {cs.trade_count}")
            lines.append(f"  总成交额: ${cs.total_notional:,.2f}")
            lines.append(f"  总费用: ${cs.total_fees:,.2f}")
            lines.append(f"  平均费率: {cs.avg_fee_rate*100:.4f}%")
            
            if cs.buy_fee_rate > 0:
                lines.append(f"  买入费率: {cs.buy_fee_rate*100:.4f}%")
            if cs.sell_fee_rate > 0:
                lines.append(f"  卖出费率: {cs.sell_fee_rate*100:.4f}%")
            
            if cs.fee_breakdown_avg:
                lines.append(f"  费用结构:")
                for fee_type, avg_amount in sorted(cs.fee_breakdown_avg.items(), key=lambda x: -x[1]):
                    lines.append(f"    - {fee_type}: ${avg_amount:.2f}")
            
            lines.append(f"  最后更新: {cs.last_updated[:19]}")
        
        lines.append("\n" + "=" * 60)
        return '\n'.join(lines)


# 全局实例
_fee_tracker: Optional[FeeTracker] = None

def get_fee_tracker() -> FeeTracker:
    """获取全局费率追踪器"""
    global _fee_tracker
    if _fee_tracker is None:
        _fee_tracker = FeeTracker()
    return _fee_tracker


if __name__ == "__main__":
    # 测试：添加 SOXS 交易记录
    ft = get_fee_tracker()
    
    # 买入记录
    ft.add_trade(
        symbol="SOXS",
        action="BUY",
        quantity=34843,
        price=8.59,
        fee_total=413.24,
        fee_breakdown={
            "老虎收费": 275.26,
            "佣金": 135.89,
            "平台费": 139.37,
            "代收费用": 137.98,
            "其他代收": 137.98,
            "证监会费": 2.39,
        },
        trade_time="2026-05-21 03:55:22",
        order_id="4"
    )
    
    # 卖出记录
    ft.add_trade(
        symbol="SOXS",
        action="SELL",
        quantity=34843,
        price=8.57,
        fee_total=415.63,
        fee_breakdown={
            "老虎收费": 275.26,
            "佣金": 135.89,
            "平台费": 139.37,
            "代收费用": 140.37,
            "其他代收": 137.98,
            "证监会费": 2.39,
        },
        trade_time="2026-05-21 04:16:20",
        order_id="7"
    )
    
    # 打印报告
    print(ft.get_report())
    
    # 预估成本
    print("\n" + "=" * 60)
    print("💡 成本预估: SOXS $10,000 买入")
    print("=" * 60)
    estimate = ft.estimate_cost("SOXS", 10000, "BUY")
    print(f"预估费用: ${estimate['estimated_fee']:.2f}")
    print(f"预估费率: {estimate['estimated_fee_rate']*100:.4f}%")
    print(f"置信度: {estimate['confidence']}")
