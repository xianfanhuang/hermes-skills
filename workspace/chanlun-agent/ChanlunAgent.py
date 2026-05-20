#!/usr/bin/env python3
"""
ChanlunAgent - 飞书交互缠论交易Agent
ChanlunAgent MVP 核心文件

功能：
1. 飞书消息响应（持仓/分析/信号/帮助）
2. 缠论分析引擎集成
3. 风控引擎集成
4. 自动反思

Author: Trading Assistant
Version: 1.0.0-MVP
"""

import os
import sys
import json
import logging
import requests
import time
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from config import AgentConfig, load_config
from store import TokenStore, TradeRecord, SignalLog
from chanlun_perception import ChanlunPerception
from czsc_extension import CzscExtension
from risk_engine import RiskEngine
from reflection_engine import ReflectionEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ChanlunAgent")


class FeishuClient:
    """飞书API客户端"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: Optional[str] = None
        self._token_expires: float = 0

    def _get_token(self) -> str:
        """获取Tenant Access Token（带缓存）"""
        if self._token and time.time() < self._token_expires:
            return self._token

        resp = requests.post(
            f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret}
        )
        data = resp.json()
        if data.get('code') != 0:
            raise Exception(f"Failed to get token: {data}")

        self._token = data['tenant_access_token']
        self._token_expires = time.time() + data.get('expire', 7200) - 300
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def send_message(self, chat_id: str, content: str, msg_type: str = "text") -> dict:
        """发送消息到群聊"""
        if msg_type == "text":
            body = {"receive_id": chat_id, "msg_type": "text", "content": json.dumps({"text": content})}
        elif msg_type == "post":
            body = {"receive_id": chat_id, "msg_type": "post", "content": content}
        else:
            body = {"receive_id": chat_id, "msg_type": msg_type, "content": content}

        resp = requests.post(
            f"{self.BASE_URL}/im/v1/messages",
            headers=self._headers(),
            params={"receive_id_type": "chat_id"},
            json=body
        )
        return resp.json()

    def reply_message(self, message_id: str, content: str, msg_type: str = "text") -> dict:
        """回复消息"""
        if msg_type == "text":
            body = {"msg_type": "text", "content": json.dumps({"text": content})}
        else:
            body = {"msg_type": msg_type, "content": content}

        resp = requests.post(
            f"{self.BASE_URL}/im/v1/messages/{message_id}/reply",
            headers=self._headers(),
            json=body
        )
        return resp.json()

    def get_chat_messages(self, chat_id: str, page_size: int = 20) -> List[dict]:
        """获取群聊消息"""
        resp = requests.get(
            f"{self.BASE_URL}/im/v1/messages",
            headers=self._headers(),
            params={
                "container_id_type": "chat",
                "container_id": chat_id,
                "page_size": page_size,
                "sort_type": "ByCreateTimeDesc"
            }
        )
        data = resp.json()
        if data.get('code') == 0:
            return data.get('data', {}).get('items', [])
        return []


class ChanlunAgent:
    """缠论交易Agent - 飞书交互版"""

    def __init__(self, config: AgentConfig = None):
        self.config = config or load_config()
        self.store = TokenStore(self.config.db_path)
        self.perception = ChanlunPerception()
        self.risk_engine = RiskEngine(self.store, {
            'technical_stop_pct': self.config.risk.technical_stop_pct,
            'time_stop_bars': self.config.risk.time_stop_bars,
            'time_stop_reduce_pct': self.config.risk.time_stop_reduce_pct,
            'max_loss_per_trade': self.config.risk.max_loss_per_trade,
            'max_daily_loss': self.config.risk.max_daily_loss,
            'consecutive_loss_limit': self.config.risk.consecutive_loss_limit,
            'halt_duration_minutes': self.config.risk.halt_duration_minutes,
        })
        self.reflection_engine = ReflectionEngine(self.store)
        self.feishu: Optional[FeishuClient] = None

        # 初始化飞书客户端
        if self.config.feishu.app_id and self.config.feishu.app_secret:
            self.feishu = FeishuClient(
                self.config.feishu.app_id,
                self.config.feishu.app_secret
            )
            logger.info("Feishu client initialized")
        else:
            logger.warning("Feishu credentials not configured")

    def handle_command(self, command: str, args: str = "", message_id: str = "") -> str:
        """
        处理飞书指令

        Args:
            command: 指令名称（持仓/分析/信号/帮助等）
            args: 指令参数
            message_id: 原始消息ID（用于回复）

        Returns:
            响应文本
        """
        handler_map = {
            "持仓": self._cmd_positions,
            "分析": self._cmd_analyze,
            "信号": self._cmd_signals,
            "平仓": self._cmd_close,
            "反思": self._cmd_reflect,
            "日报": self._cmd_daily_report,
            "状态": self._cmd_status,
            "帮助": self._cmd_help,
        }

        handler = handler_map.get(command)
        if handler:
            try:
                return handler(args)
            except Exception as e:
                logger.error(f"Command '{command}' failed: {e}")
                return f"❌ 执行失败: {str(e)}"
        else:
            return f"❓ 未知指令: {command}\n\n" + self._cmd_help("")

    # ============ 指令实现 ============

    def _cmd_positions(self, args: str) -> str:
        """查询持仓"""
        trades = self.store.get_open_trades()
        if not trades:
            return "💼 当前空仓"

        lines = ["💼 当前持仓:\n"]
        for t in trades:
            emoji = "🟢" if t['direction'] == 'long' else "🔴"
            lines.append(
                f"{emoji} {t['symbol']} | {t['direction']} | "
                f"入场: ${t['entry_price']:.2f} | 数量: {t['quantity']}"
            )
        return "\n".join(lines)

    def _cmd_analyze(self, args: str) -> str:
        """缠论分析（含扩展：类二买/中枢震荡/背驰/风控）"""
        symbol = args.strip() or self.config.symbol.symbol
        market = self.config.symbol.market

        structures = self.perception.analyze_symbol(symbol, market, ["日线", "30分钟", "5分钟"])

        lines = [f"📊 {symbol} 缠论分析:\n"]
        for freq, structure in structures.items():
            trend_emoji = "📈" if structure.trend == "up" else "📉" if structure.trend == "down" else "➡️"
            lines.append(f"【{freq}】{trend_emoji} {structure.trend}")
            lines.append(f"  笔: {structure.bi_count} | 中枢: {structure.zs_count}")
            if structure.last_zs_range:
                lines.append(f"  中枢区间: [{structure.last_zs_range[0]:.2f}, {structure.last_zs_range[1]:.2f}]")
            lines.append(f"  背驰: {'⚠️ 是' if structure.divergence else '否'}")
            if structure.buy_sell_points:
                for bsp in structure.buy_sell_points:
                    lines.append(f"  🔔 买卖点: {bsp}")
            lines.append("")

        # 风控检查
        open_trades = self.store.get_open_trades(symbol=symbol)
        if open_trades:
            quote = self.perception.get_quote(symbol, market)
            if quote:
                current_price = quote.get('price', 0) or quote.get('last_price', 0)
                for t in open_trades:
                    zs_range = structures.get('日线', structures.get(list(structures.keys())[0]))
                    zs = zs_range.last_zs_range if zs_range else None
                    alerts = self.risk_engine.check_all(t, current_price, zs)
                    if alerts:
                        lines.append("⚠️ 风控告警:")
                        for a in alerts:
                            lines.append(f"  [{a.level}] {a.message}")
                        lines.append("")

        return "\n".join(lines)

    def _cmd_signals(self, args: str) -> str:
        """查看信号"""
        signals = self.store.get_signals(limit=10)
        if not signals:
            return "📡 暂无信号记录"

        lines = ["📡 最近信号:\n"]
        for s in signals:
            emoji = {"divergence_top": "🔴", "divergence_bottom": "🟢", "zs_range": "🟡"}.get(s['signal_type'], "⚡")
            lines.append(
                f"{emoji} {s['symbol']} ({s['freq']}) | {s['signal_type']} | "
                f"${s['price']:.2f} | {s['created_at'][:16]}"
            )
        return "\n".join(lines)

    def _cmd_close(self, args: str) -> str:
        """平仓"""
        symbol = args.strip() or self.config.symbol.symbol
        trades = self.store.get_open_trades(symbol=symbol)

        if not trades:
            return f"❌ {symbol} 无未平仓交易"

        results = []
        for t in trades:
            # 获取当前价格
            quote = self.perception.fetcher.get_quote(symbol, self.config.symbol.market) if self.perception.fetcher else None
            current_price = quote.price if quote else t['entry_price']

            pnl = (current_price - t['entry_price']) * t['quantity']
            pnl_pct = (current_price / t['entry_price'] - 1) * 100

            self.store.update_trade(
                t['trade_id'],
                exit_price=current_price,
                pnl=pnl,
                pnl_pct=pnl_pct,
                exit_time=datetime.now().isoformat(),
                status="closed"
            )

            emoji = "✅" if pnl > 0 else "❌"
            results.append(
                f"{emoji} {t['symbol']} 平仓 | 盈亏: ${pnl:.2f} ({pnl_pct:+.2f}%)"
            )

            # 自动反思
            if self.config.auto_reflect:
                self._generate_trade_reflection(t, current_price, pnl, pnl_pct)

        return "\n".join(results)

    def _cmd_reflect(self, args: str) -> str:
        """生成反思（含优化建议）"""
        trades = self.store.get_trades(status='closed', limit=5)
        if not trades:
            return "📝 暂无已平仓交易，无法生成反思"

        # 生成最近交易反思
        latest = trades[0]
        trade_reflection = self.reflection_engine.generate_post_trade_reflection(latest)

        # 获取优化建议
        suggestions = self.reflection_engine.get_optimization_suggestions()

        lines = [trade_reflection, "\n📊 参数优化建议:\n"]
        for category, data in suggestions.items():
            if category == "总体建议":
                lines.append(f"\n💡 总体建议:")
                for tip in data:
                    lines.append(f"  • {tip}")
            elif isinstance(data, dict) and data:
                lines.append(f"  {category}: {data.get('建议', 'N/A')}")

        return "\n".join(lines)

    def _cmd_daily_report(self, args: str) -> str:
        """日报"""
        today = datetime.now().strftime("%Y-%m-%d")
        trades = self.store.get_trades(limit=20)
        stats = self.store.get_trade_stats() or {}

        lines = [
            f"📊 交易日报 {today}\n",
            f"总交易: {stats.get('total_trades') or 0}",
            f"胜率: {stats.get('win_rate') or 0:.1f}%",
            f"总盈亏: ${stats.get('total_pnl') or 0:.2f}",
            ""
        ]

        # 今日信号
        signals = self.store.get_signals(limit=5)
        if signals:
            lines.append("📡 最近信号:")
            for s in signals:
                lines.append(f"  • {s['symbol']} {s['signal_type']}")
            lines.append("")

        return "\n".join(lines)

    def _cmd_status(self, args: str) -> str:
        """系统状态"""
        db_stats = self.store.get_db_stats()
        lines = [
            "🦞 ChanlunAgent 状态:\n",
            f"版本: {self.config.version}",
            f"模式: {self.config.mode}",
            f"数据库: {db_stats}",
            f"飞书: {'✅ 已连接' if self.feishu else '❌ 未配置'}",
            f"czsc: v0.10.12",
        ]
        return "\n".join(lines)

    def _cmd_help(self, args: str) -> str:
        """帮助信息"""
        return """🦞 ChanlunAgent 指令列表:

📊 持仓 — 查询当前持仓
🔍 分析 <代码> — 缠论分析（默认CRCL）
📡 信号 — 查看最近信号
💰 平仓 <代码> — 平仓指定品种
📝 反思 — 生成交易反思
📋 日报 — 生成交易日报
ℹ️ 状态 — 系统运行状态
❓ 帮助 — 显示此帮助

示例: 分析 AAPL"""

    # ============ 辅助方法 ============

    def _generate_trade_reflection(self, trade: dict, exit_price: float, 
                                     pnl: float, pnl_pct: float):
        """自动生成交易反思"""
        reflection = (
            f"交易 {trade['symbol']} {trade['direction']} | "
            f"入场: ${trade['entry_price']:.2f} → 出场: ${exit_price:.2f} | "
            f"盈亏: {pnl_pct:+.2f}% | "
            f"信号: {trade.get('signal_type', 'N/A')}"
        )
        self.store.log_reflection(
            trade['trade_id'], 
            "auto_post_trade",
            reflection,
            {"pnl": pnl, "pnl_pct": pnl_pct}
        )

    def send_to_feishu(self, content: str, chat_id: str = None):
        """发送消息到飞书"""
        if not self.feishu:
            logger.warning("Feishu not configured")
            return
        chat_id = chat_id or self.config.feishu.chat_id
        return self.feishu.send_message(chat_id, content)


# ============ CLI 入口 ============

def main():
    import argparse

    parser = argparse.ArgumentParser(description="ChanlunAgent - 飞书缠论交易Agent")
    parser.add_argument("--command", "-c", type=str, help="执行指令")
    parser.add_argument("--args", "-a", type=str, default="", help="指令参数")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--demo", action="store_true", help="演示模式")

    args = parser.parse_args()

    config = load_config(args.config) if args.config else load_config()
    agent = ChanlunAgent(config)

    if args.demo:
        print("=" * 60)
        print("🦞 ChanlunAgent MVP Demo")
        print("=" * 60)
        print()

        commands = ["帮助", "状态", "分析", "持仓", "信号", "反思", "日报"]
        for cmd in commands:
            print(f">>> {cmd}")
            print(agent.handle_command(cmd))
            print("-" * 40)
        return

    if args.command:
        result = agent.handle_command(args.command, args.args)
        print(result)
    else:
        print("ChanlunAgent MVP v1.0.0")
        print("Use --demo for demo mode, or --command <cmd> to execute")


if __name__ == "__main__":
    main()
