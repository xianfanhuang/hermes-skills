#!/usr/bin/env python3
"""
Tiger 统一交易客户端 - 修正版

修正内容:
- TigerOpenClientConfig 不支持 host/sandbox_debug 参数（v3.5.8）
- get_stock_quote → get_stock_briefs（返回 DataFrame）
- get_kline_data → get_bars
- place_order → create_order + place_order（两步）
- get_account → get_assets
"""

import os
import requests
from datetime import datetime, timedelta
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import Language, OrderType
from tigeropen.trade.domain.contract import Contract

# ==================== 全局配置 ====================
TIGER_ID = "20159412"
TIGER_PRIVATE_KEY = """MIICXAIBAAKBgQCQsk07H1czwJy5Gfm9GH2iahHEX3Hhej6y8FW7Hvd9X9jTqxoxFi45aMPFXU7nAx9Ki/gYQlYeXjpCu5RMUHboaz29iBlXmq0gFd6/CdB1LEPbua5V5/kUP53ETbKo0RFjm+fWHxYE6QMpMyW6amP2ASyygSs23aAxYnLZboq5vwIDAQABAoGAXr0/r/w/PlVYyCFn0RXd/J9ybp8Hk1hVARg3KcOGzAIbl8up5IXfUht0Qx9q7/qtXEP09v1IIa4Ue2kSGj18/IhEDla3+EMs24pQ9xnRPgwnzsQkfwNTerGwnxvrM+iHl/IH0AKL0kBPs56JsIIP5VZMd3xNK4xiVTzZIRcRVRECQQDGdrrM6qkomFPw8YRjIO7DuM1IG7ec2PVHX/zYMgCkfYBCsz+DjsopKLjEGms3IqHlSwzB5GLq/z1iHBf8IM/tAkEAuqUn91dmOgSsUJIbuAVN/FtoGcIKe0SYybX3BDsPE6295XR70XMhnrTjx0wIsiANzgC1JZC8PdxB1pxUyx0C2wJBALeao9prxa8OramcZlOm5f0f/JoXOljaxqAPh0UjjUCf8obCeaHl+dT2HWke382UNp6APf8qoPCyzUD0qKPSX0kCQE7WJ/V/wzxKcQZvUKoAA5rOeUA4B/ldVjQNWlM9Jvcm8gkTlKE5wj+pJHUwFpQ2md4jymAdrIVsnZqq2d4ZWPUCQFesxYFPfPv2xnonihe7zqsFAz0pD3E5Ks/F3sdUZk4s/A9Zf1rzxS2XsQtqHgl08L0u340m+YbtTlz/Lyq0mLI=="""
SIM_ACCOUNT = "21409378833585169"
LIVE_ACCOUNT = "1406653"

# Finnhub Keys（轮换）
FINNHUB_KEYS = [
    "d85kn4hr01qitd92g090d85kn4hr01qitd92g09g",
    "d85k7kpr01qitd92dhl0d85k7kpr01qitd92dhlg",
    "d85mbo1r01qitd92ng60d85mbo1r01qitd92ng6g",
    "d85mo0hr01qitd92pbcgd85mo0hr01qitd92pbd0",
    "d85mpr9r01qitd92pm1gd85mpr9r01qitd92pm20",
]
_finnhub_idx = 0

# 实盘交易锁：True=模拟盘 False=实盘
TRADE_LOCK = True


# ==================== 初始化客户端 ====================
def _make_config(account, sandbox=False):
    """创建 TigerOpenClientConfig（v3.5.8 兼容）"""
    cfg = TigerOpenClientConfig(sandbox_debug=sandbox)
    cfg.tiger_id = TIGER_ID
    cfg.private_key = TIGER_PRIVATE_KEY
    cfg.language = Language.zh_CN
    cfg.account = account
    return cfg


# 行情端：生产域名（港股/A股免费）
tiger_quote = QuoteClient(_make_config(SIM_ACCOUNT))

# 模拟盘交易端
sim_trade = TradeClient(_make_config(SIM_ACCOUNT))

# 实盘交易端（需解锁后启用）
live_trade = TradeClient(_make_config(LIVE_ACCOUNT))


# ==================== 第三方行情 ====================
def get_finnhub_quote(symbol):
    """Finnhub 美股行情（5个Key轮换）"""
    global _finnhub_idx
    for _ in range(len(FINNHUB_KEYS)):
        try:
            key = FINNHUB_KEYS[_finnhub_idx]
            _finnhub_idx = (_finnhub_idx + 1) % len(FINNHUB_KEYS)
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={key}"
            res = requests.get(url, timeout=5).json()
            if res.get("c"):
                return True, res
        except:
            continue
    return False, None


# ==================== 统一行情查询 ====================
def get_all_quote(symbol: str) -> str:
    sym = symbol.upper()

    # 港股
    if sym.endswith(".HK"):
        try:
            code = sym.replace(".HK", "")
            df = tiger_quote.get_stock_briefs([code])
            if df is not None and not df.empty:
                row = df.iloc[0]
                return f"港股{sym}｜现价 {row['latest_price']} 涨跌幅 {row['change_rate']*100:.2f}%"
        except Exception as e:
            return f"港股行情获取失败: {e}"

    # A股
    elif sym.endswith(".SH") or sym.endswith(".SZ"):
        try:
            code = sym.split(".")[0]  # 去掉交易所后缀
            df = tiger_quote.get_stock_briefs([code])
            if df is not None and not df.empty:
                row = df.iloc[0]
                pct = row.get('change_rate', 0) or 0
                return f"A股{sym}｜现价 {row['latest_price']} 涨跌幅 {pct*100:.2f}%"
        except Exception as e:
            return f"A股行情获取失败: {e}"

    # 美股
    else:
        ok, d = get_finnhub_quote(sym)
        if ok:
            return f"美股{sym}｜现价 ${d['c']} 涨跌 {d['d']:+.2f} 涨幅 {d['dp']:+.2f}%"
        return "美股行情获取失败"


# ==================== 历史K线（免费） ====================
def get_history_line(symbol: str, days: int = 30) -> str:
    """获取历史K线数据（全品种免费）"""
    try:
        df = tiger_quote.get_bars([symbol], period="day", limit=days)
        if df is not None and not df.empty:
            return f"{symbol} 近{days}日K线正常，共{len(df)}根数据"
        return "K线数据为空"
    except Exception as e:
        return f"历史K线拉取失败: {e}"


# ==================== 交易函数 ====================
def trade_limit_order(symbol: str, price: float, volume: int, direction: str) -> str:
    """
    限价下单
    direction: BUY / SELL
    """
    client = sim_trade if TRADE_LOCK else live_trade
    mode = "【模拟盘】" if TRADE_LOCK else "【实盘】"

    try:
        contract = Contract(symbol=symbol, currency='USD', exchange='SMART')
        order = client.create_order(
            contract=contract,
            action=direction,
            order_type=OrderType.LMT,
            quantity=volume,
            limit_price=price,
            time_in_force='day',
            outside_rth=True
        )
        result = client.place_order(order)
        if result:
            return f"{mode}{direction}委托成功，订单号：{order.order_id}"
        return f"{mode}委托失败"
    except Exception as e:
        return f"{mode}委托失败: {e}"


def trade_market_order(symbol: str, volume: int, direction: str) -> str:
    """市价下单"""
    client = sim_trade if TRADE_LOCK else live_trade
    mode = "【模拟盘】" if TRADE_LOCK else "【实盘】"

    try:
        contract = Contract(symbol=symbol, currency='USD', exchange='SMART')
        order = client.create_order(
            contract=contract,
            action=direction,
            order_type=OrderType.MKT,
            quantity=volume,
            time_in_force='day',
            outside_rth=True
        )
        result = client.place_order(order)
        if result:
            return f"{mode}{direction}市价单成功，订单号：{order.order_id}"
        return f"{mode}委托失败"
    except Exception as e:
        return f"{mode}委托失败: {e}"


def cancel_order(order_id: str) -> str:
    """撤单"""
    client = sim_trade if TRADE_LOCK else live_trade
    try:
        client.cancel_order(order_id)
        return f"订单{order_id}撤销成功"
    except Exception as e:
        return f"撤单失败: {e}"


# ==================== 账户查询 ====================
def get_account_info() -> str:
    """获取账户信息"""
    client = sim_trade if TRADE_LOCK else live_trade
    mode = "模拟账户" if TRADE_LOCK else "实盘账户"

    try:
        assets = client.get_assets()
        if assets and len(assets) > 0:
            a = assets[0]
            seg = a.segments.get('S')
            if seg:
                return f"{mode}｜净值: ${seg.net_liquidation:,.2f} 可用: ${seg.available_funds:,.2f} 现金: ${seg.cash:,.2f}"
        return f"{mode}｜查询失败"
    except Exception as e:
        return f"{mode}｜查询失败: {e}"


def get_hold_pos() -> str:
    """获取持仓"""
    client = sim_trade if TRADE_LOCK else live_trade
    try:
        positions = client.get_positions()
        if not positions:
            return "暂无持仓"
        res = ""
        for p in positions:
            sym = p.contract.symbol if hasattr(p, 'contract') else p.get('symbol', 'N/A')
            qty = p.quantity if hasattr(p, 'quantity') else p.get('quantity', 0)
            pnl = p.unrealized_pnl if hasattr(p, 'unrealized_pnl') else p.get('unrealized_pnl', 0)
            res += f"{sym} 持仓{qty} 未实现盈亏 ${pnl:+.2f}\n"
        return res.strip()
    except Exception as e:
        return f"持仓查询失败: {e}"


def get_orders() -> str:
    """获取今日订单"""
    client = sim_trade if TRADE_LOCK else live_trade
    try:
        orders = client.get_orders()
        if not orders:
            return "今日无订单"
        res = ""
        for o in orders:
            sym = o.contract.symbol if hasattr(o, 'contract') else 'N/A'
            action = o.action if hasattr(o, 'action') else 'N/A'
            qty = o.quantity if hasattr(o, 'quantity') else 0
            status = o.status if hasattr(o, 'status') else 'N/A'
            filled = o.filled if hasattr(o, 'filled') else 0
            res += f"{sym} {action} {qty}股 已成交{filled} 状态{status}\n"
        return res.strip()
    except Exception as e:
        return f"订单查询失败: {e}"


# ==================== 虚实盘切换 ====================
def check_current_mode() -> str:
    if TRADE_LOCK:
        return "🔒 当前模式：模拟盘交易（实盘已锁定）"
    return "🔓 当前模式：实盘正式交易"


def open_real_trade() -> str:
    """申请开启实盘"""
    if not TRADE_LOCK:
        return "已处于实盘模式"
    return "⚠️ 确认开启实盘交易请回复：确认启用实盘"


def confirm_open_real() -> str:
    """二次确认解锁"""
    global TRADE_LOCK
    TRADE_LOCK = False
    return "✅ 已切换为实盘交易模式，所有下单动用真实资金"


def close_real_trade() -> str:
    """一键切回模拟"""
    global TRADE_LOCK
    TRADE_LOCK = True
    return "✅ 已锁定实盘，切回模拟盘练习模式"


# ==================== 测试入口 ====================
if __name__ == "__main__":
    print("="*60)
    print("🐯 Tiger 统一交易客户端 - 测试")
    print("="*60)

    print("\n[1] 模式检查:")
    print(f"  {check_current_mode()}")

    print("\n[2] 账户信息:")
    print(f"  {get_account_info()}")

    print("\n[3] 持仓查询:")
    print(f"  {get_hold_pos()}")

    print("\n[4] 港股行情:")
    print(f"  {get_all_quote('00700.HK')}")

    print("\n[5] A股行情:")
    print(f"  {get_all_quote('600519.SH')}")

    print("\n[6] 美股行情:")
    print(f"  {get_all_quote('AAPL')}")
    print(f"  {get_all_quote('CRCL')}")

    print("\n[7] 历史K线:")
    print(f"  {get_history_line('CRCL', 10)}")

    print("\n[8] 订单查询:")
    print(f"  {get_orders()}")

    print("\n" + "="*60)
