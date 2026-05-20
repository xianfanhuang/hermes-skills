#!/usr/bin/env python3
"""
风控引擎
ChanlunAgent MVP - 三级风控体系

风控层级：
1. 技术止损：价格跌回中枢 → 全部平仓
2. 时间止损：N根K线未达预期 → 减仓50%
3. 资金止损：单笔亏损>3% → 全部平仓；当日累计亏损>8% → 停止交易
4. 连续亏损熔断：连亏3笔 → 暂停60分钟

Author: Trading Assistant
Version: 1.0.0
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from store import TokenStore

logger = logging.getLogger("RiskEngine")


@dataclass
class RiskAlert:
    """风控告警"""
    level: str  # warning/critical/halt
    type: str   # technical_stop/time_stop/capital_stop/consecutive_halt
    message: str
    action: str  # close_all/reduce_half/stop_trading/wait
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class RiskEngine:
    """风控引擎"""

    def __init__(self, store: TokenStore, config: Dict = None):
        self.store = store
        self.config = config or {}
        self.alerts: List[RiskAlert] = []

        # 风控参数
        self.technical_stop_pct = self.config.get('technical_stop_pct', 0.03)  # 3%
        self.time_stop_bars = self.config.get('time_stop_bars', 8)
        self.time_stop_reduce_pct = self.config.get('time_stop_reduce_pct', 0.5)
        self.max_loss_per_trade = self.config.get('max_loss_per_trade', 0.03)  # 3%
        self.max_daily_loss = self.config.get('max_daily_loss', 0.08)  # 8%
        self.consecutive_loss_limit = self.config.get('consecutive_loss_limit', 3)
        self.halt_duration_minutes = self.config.get('halt_duration_minutes', 60)

        # 状态
        self._halt_until: Optional[datetime] = None
        self._consecutive_losses = 0

    def check_all(self, trade: Dict, current_price: float, 
                  zs_range: tuple = None, bars_held: int = 0) -> List[RiskAlert]:
        """
        综合风控检查
        
        Args:
            trade: 交易记录
            current_price: 当前价格
            zs_range: 中枢区间 (zd, zg)
            bars_held: 已持有K线数
            
        Returns:
            风控告警列表
        """
        self.alerts = []

        # 检查是否在熔断期
        if self._halt_until and datetime.now() < self._halt_until:
            remaining = (self._halt_until - datetime.now()).seconds // 60
            self.alerts.append(RiskAlert(
                level="critical",
                type="consecutive_halt",
                message=f"连续亏损熔断中，剩余 {remaining} 分钟",
                action="wait"
            ))
            return self.alerts

        # 1. 技术止损
        self._check_technical_stop(trade, current_price, zs_range)

        # 2. 时间止损
        self._check_time_stop(trade, current_price, bars_held)

        # 3. 资金止损
        self._check_capital_stop(trade, current_price)

        # 4. 连续亏损检查
        self._check_consecutive_losses()

        return self.alerts

    def _check_technical_stop(self, trade: Dict, current_price: float, zs_range: tuple):
        """技术止损：价格跌回中枢"""
        if not zs_range:
            return

        zd, zg = zs_range
        entry_price = trade.get('entry_price', 0)
        direction = trade.get('direction', 'long')

        if direction == 'long':
            # 多头：价格跌破中枢下沿
            if current_price < zd:
                loss_pct = (entry_price - current_price) / entry_price
                self.alerts.append(RiskAlert(
                    level="critical",
                    type="technical_stop",
                    message=f"技术止损触发：价格 ${current_price:.2f} 跌破中枢下沿 ${zd:.2f}，"
                            f"亏损 {loss_pct*100:.2f}%",
                    action="close_all"
                ))
        elif direction == 'short':
            # 空头：价格突破中枢上沿
            if current_price > zg:
                loss_pct = (current_price - entry_price) / entry_price
                self.alerts.append(RiskAlert(
                    level="critical",
                    type="technical_stop",
                    message=f"技术止损触发：价格 ${current_price:.2f} 突破中枢上沿 ${zg:.2f}，"
                            f"亏损 {loss_pct*100:.2f}%",
                    action="close_all"
                ))

    def _check_time_stop(self, trade: Dict, current_price: float, bars_held: int):
        """时间止损：N根K线未达预期"""
        if bars_held < self.time_stop_bars:
            return

        entry_price = trade.get('entry_price', 0)
        direction = trade.get('direction', 'long')

        if direction == 'long':
            # 多头：N根K线后价格未上涨
            if current_price <= entry_price:
                self.alerts.append(RiskAlert(
                    level="warning",
                    type="time_stop",
                    message=f"时间止损触发：持有 {bars_held} 根K线，"
                            f"价格 ${current_price:.2f} 未超过入场价 ${entry_price:.2f}",
                    action="reduce_half"
                ))
        elif direction == 'short':
            # 空头：N根K线后价格未下跌
            if current_price >= entry_price:
                self.alerts.append(RiskAlert(
                    level="warning",
                    type="time_stop",
                    message=f"时间止损触发：持有 {bars_held} 根K线，"
                            f"价格 ${current_price:.2f} 未低于入场价 ${entry_price:.2f}",
                    action="reduce_half"
                ))

    def _check_capital_stop(self, trade: Dict, current_price: float):
        """资金止损：单笔亏损>3%，当日累计亏损>8%"""
        entry_price = trade.get('entry_price', 0)
        direction = trade.get('direction', 'long')
        quantity = trade.get('quantity', 0)

        if not entry_price or not quantity:
            return

        # 计算当前盈亏
        if direction == 'long':
            pnl = (current_price - entry_price) * quantity
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl = (entry_price - current_price) * quantity
            pnl_pct = (entry_price - current_price) / entry_price

        # 单笔止损
        if pnl_pct < -self.max_loss_per_trade:
            self.alerts.append(RiskAlert(
                level="critical",
                type="capital_stop",
                message=f"单笔止损触发：亏损 {pnl_pct*100:.2f}% > {self.max_loss_per_trade*100}%",
                action="close_all"
            ))

        # 当日累计止损
        today_stats = self.store.get_trade_stats()
        today_pnl = today_stats.get('total_pnl', 0) or 0
        # 假设初始资金 $100,000
        initial_capital = 100000
        daily_loss_pct = today_pnl / initial_capital if today_pnl < 0 else 0

        if daily_loss_pct < -self.max_daily_loss:
            self.alerts.append(RiskAlert(
                level="critical",
                type="capital_stop",
                message=f"当日止损触发：累计亏损 {daily_loss_pct*100:.2f}% > {self.max_daily_loss*100}%",
                action="stop_trading"
            ))

    def _check_consecutive_losses(self):
        """连续亏损检查"""
        trades = self.store.get_trades(status='closed', limit=self.consecutive_loss_limit)

        if len(trades) < self.consecutive_loss_limit:
            return

        # 检查最近N笔是否全部亏损
        all_loss = all((t.get('pnl') or 0) < 0 for t in trades)
        if all_loss:
            self._consecutive_losses = self.consecutive_loss_limit
            self._halt_until = datetime.now() + timedelta(minutes=self.halt_duration_minutes)

            self.alerts.append(RiskAlert(
                level="critical",
                type="consecutive_halt",
                message=f"连续 {self.consecutive_loss_limit} 笔亏损，"
                        f"熔断 {self.halt_duration_minutes} 分钟",
                action="stop_trading"
            ))

    def get_position_size(self, account_balance: float, entry_price: float, 
                          stop_price: float, direction: str = "long") -> Dict:
        """
        计算仓位大小（固定风险比例法）
        
        Args:
            account_balance: 账户余额
            entry_price: 入场价
            stop_price: 止损价
            direction: 方向
            
        Returns:
            仓位信息
        """
        # 计算每股风险
        if direction == "long":
            risk_per_share = entry_price - stop_price
        else:
            risk_per_share = stop_price - entry_price

        if risk_per_share <= 0:
            return {"error": "止损价设置不合理"}

        # 最大风险金额
        max_risk = account_balance * self.max_loss_per_trade

        # 计算数量
        quantity = int(max_risk / risk_per_share)

        # 总金额
        total_cost = quantity * entry_price

        # 不超过账户50%
        max_cost = account_balance * 0.5
        if total_cost > max_cost:
            quantity = int(max_cost / entry_price)
            total_cost = quantity * entry_price

        return {
            "quantity": quantity,
            "total_cost": total_cost,
            "risk_per_share": risk_per_share,
            "max_risk": max_risk,
            "position_pct": total_cost / account_balance * 100
        }

    def get_risk_summary(self) -> Dict:
        """获取风控状态摘要"""
        return {
            "consecutive_losses": self._consecutive_losses,
            "halt_until": self._halt_until.isoformat() if self._halt_until else None,
            "is_halted": self._halt_until and datetime.now() < self._halt_until,
            "alerts_count": len(self.alerts),
            "config": {
                "technical_stop_pct": self.technical_stop_pct,
                "time_stop_bars": self.time_stop_bars,
                "max_loss_per_trade": self.max_loss_per_trade,
                "max_daily_loss": self.max_daily_loss,
                "consecutive_loss_limit": self.consecutive_loss_limit,
                "halt_duration_minutes": self.halt_duration_minutes,
            }
        }


# ============ 测试 ============

if __name__ == "__main__":
    import tempfile
    import os

    # 创建测试数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db = f.name

    store = TokenStore(test_db)
    engine = RiskEngine(store)

    # 测试技术止损
    trade = {"entry_price": 110.0, "direction": "long", "quantity": 100}
    alerts = engine.check_all(trade, current_price=85.0, zs_range=(90.0, 110.0))
    print("技术止损测试:")
    for a in alerts:
        print(f"  [{a.level}] {a.message} → {a.action}")

    # 测试时间止损
    alerts = engine.check_all(trade, current_price=110.0, bars_held=10)
    print("\n时间止损测试:")
    for a in alerts:
        print(f"  [{a.level}] {a.message} → {a.action}")

    # 测试资金止损
    alerts = engine.check_all(trade, current_price=100.0)
    print("\n资金止损测试:")
    for a in alerts:
        print(f"  [{a.level}] {a.message} → {a.action}")

    # 测试仓位计算
    pos = engine.get_position_size(100000, 110.0, 105.0, "long")
    print(f"\n仓位计算: {pos}")

    # 清理
    os.unlink(test_db)
    print("\n✅ 风控引擎测试完成")
