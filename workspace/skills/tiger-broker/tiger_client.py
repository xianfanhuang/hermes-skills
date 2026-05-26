import os
from tigeropen.common.consts import Language
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient

# ===================== 环境变量 =====================
TIGER_ID = os.getenv("TIGER_ID", "20159412")
TIGER_PRIVATE_KEY = os.getenv("TIGER_PRIVATE_KEY")
TIGER_MODE = os.getenv("TIGER_MODE", "simulation")
TIGER_SIM_ACCOUNT = os.getenv("TIGER_SIMULATION_ACCOUNT", "21409378833585169")
TIGER_LIVE_ACCOUNT = os.getenv("TIGER_LIVE_ACCOUNT", "1406653")

# ===================== 域名配置 =====================
# 生产: openapi.tigerfintech.com (默认)
# 模拟: openapi-sandbox.tigerfintech.com (默认)
# ⚠️ openapi-sgp.itigerup.com / openapi-sg.tigerbrokers.com 均不存在

# ===================== 行情端：生产域名拿行情 =====================
quote_config = TigerOpenClientConfig(sandbox_debug=False)
quote_config.tiger_id = TIGER_ID
quote_config.private_key = TIGER_PRIVATE_KEY
quote_config.language = Language.zh_CN

# ===================== 交易端：模拟盘 =====================
trade_config = TigerOpenClientConfig(sandbox_debug=False)
trade_config.tiger_id = TIGER_ID
trade_config.account = TIGER_SIM_ACCOUNT
trade_config.private_key = TIGER_PRIVATE_KEY
trade_config.language = Language.zh_CN

# 初始化客户端
quote_client = QuoteClient(quote_config)
trade_client = TradeClient(trade_config)

print("✅ 行情端【生产】+ 交易端【模拟盘】初始化完成")

# ===================== 行情函数（港股/A股可用，美股需开通权限） =====================
def get_stock_brief(symbol: str):
    """
    获取股票行情摘要
    :param symbol: 股票代码 (如 AAPL / 00700 / 600519)
    """
    try:
        res = quote_client.get_briefs([symbol])
        if not res:
            return f"【失败】未获取到 {symbol} 行情数据"
        d = res[0]
        price = d.latest_price
        prev = d.prev_close
        change = price - prev if price and prev else 0
        pct = (change / prev * 100) if prev and prev > 0 else 0
        return (
            f"【{symbol} 实时行情】\n"
            f"名称：{d.name}\n"
            f"最新价：{price}\n"
            f"涨跌：{change:+.2f} ({pct:+.2f}%)\n"
            f"开盘价：{d.open_price}\n"
            f"最高价：{d.high_price}\n"
            f"最低价：{d.low_price}\n"
            f"昨收：{prev}"
        )
    except Exception as e:
        return f"【错误】{str(e)}"

def get_stock_quote(symbol: str):
    """
    获取股票详细报价
    :param symbol: 股票代码
    """
    try:
        res = quote_client.get_stock_quote([symbol])
        if not res:
            return f"【失败】未获取到 {symbol} 行情数据"
        d = res[0]
        return (
            f"【{symbol} 详细报价】\n"
            f"最新价：{d.latest_price}\n"
            f"涨跌：{d.change}\n"
            f"涨跌幅：{d.change_percent:.2f}%\n"
            f"开盘价：{d.open}\n"
            f"最高价：{d.high}\n"
            f"最低价：{d.low}\n"
            f"成交量：{d.volume}\n"
            f"成交额：{d.amount}"
        )
    except Exception as e:
        return f"【错误】{str(e)}"

# ===================== 交易函数（模拟盘） =====================
def get_account_info():
    """获取模拟账户信息"""
    try:
        assets = trade_client.get_assets()
        if not assets:
            return "【失败】未获取到账户信息"
        s = assets[0].summary
        return (
            f"【模拟盘账户信息】\n"
            f"总资产(净值)：${s.net_liquidation:,.2f}\n"
            f"可用资金：${s.cash:,.2f}\n"
            f"购买力：${s.buying_power:,.2f}\n"
            f"持仓市值：${s.gross_position_value:,.2f}\n"
            f"已实现盈亏：${s.realized_pnl:,.2f}\n"
            f"未实现盈亏：${s.unrealized_pnl:,.2f}"
        )
    except Exception as e:
        return f"【错误】{str(e)}"

def get_positions():
    """查询模拟盘持仓"""
    try:
        pos_list = trade_client.get_positions()
        if not pos_list:
            return "模拟盘暂无持仓"
        text = "【模拟盘持仓】\n"
        for p in pos_list:
            text += f"{p.symbol} | 数量：{p.quantity} | 成本价：{p.cost_price} | 盈亏：{p.unrealized_pnl}\n"
        return text
    except Exception as e:
        return f"【错误】{str(e)}"

def place_order_limit(symbol: str, price: float, quantity: int, action: str = "BUY"):
    """
    限价单
    :param symbol: 标的代码
    :param price: 限价价格
    :param quantity: 股数
    :param action: BUY / SELL
    """
    try:
        contract = trade_client.get_contract(symbol)
        order = trade_client.create_order(
            account=TIGER_SIM_ACCOUNT,
            contract=contract,
            action=action,
            order_type="LMT",
            quantity=quantity,
            limit_price=price
        )
        trade_client.place_order(order)
        return f"【模拟盘下单成功】订单ID：{order.id} | {action} {symbol} 限价{price} 数量{quantity}股"
    except Exception as e:
        return f"【下单失败】{str(e)}"

def place_order_market(symbol: str, quantity: int, action: str = "BUY"):
    """
    市价单
    :param symbol: 标的代码
    :param quantity: 股数
    :param action: BUY / SELL
    """
    try:
        contract = trade_client.get_contract(symbol)
        order = trade_client.create_order(
            account=TIGER_SIM_ACCOUNT,
            contract=contract,
            action=action,
            order_type="MKT",
            quantity=quantity
        )
        trade_client.place_order(order)
        return f"【模拟盘市价下单成功】订单ID：{order.id} | {action} {symbol} 数量{quantity}股"
    except Exception as e:
        return f"【下单失败】{str(e)}"

def get_open_orders():
    """查询未成交订单"""
    try:
        orders = trade_client.get_open_orders()
        if not orders:
            return "模拟盘无未成交订单"
        text = "【未成交订单】\n"
        for o in orders:
            symbol = o.contract.symbol if o.contract else 'N/A'
            text += f"ID:{o.id} | {o.action} {symbol} | {o.status} | 价格：{o.limit_price} | 数量：{o.quantity}\n"
        return text
    except Exception as e:
        return f"【错误】{str(e)}"

def cancel_order(order_id: str):
    """撤单"""
    try:
        trade_client.cancel_order(TIGER_SIM_ACCOUNT, order_id)
        return f"【模拟盘撤单成功】订单{order_id}已撤销"
    except Exception as e:
        return f"【撤单失败】{str(e)}"

def get_today_orders():
    """查询今日所有订单"""
    try:
        orders = trade_client.get_orders()
        if not orders:
            return "今日无任何委托订单"
        text = "【今日订单】\n"
        for o in orders:
            text += f"ID:{o.id} | {o.action} {o.symbol} | {o.status} | 价格：{o.limit_price} | 数量：{o.quantity}\n"
        return text
    except Exception as e:
        return f"【错误】{str(e)}"

def get_order_records(limit=10):
    """获取订单记录 - 老虎APP格式"""
    try:
        orders = trade_client.get_orders(account=TIGER_SIM_ACCOUNT)
        records = []
        for o in orders[:limit]:
            s = o.contract.symbol if o.contract else '?'
            action = '买入' if o.action == 'BUY' else '卖出'
            price = o.limit_price if o.limit_price else 'MKT'
            # 获取时间
            dt = o.order_time if hasattr(o, 'order_time') and o.order_time else ''
            date_str = ''
            time_str = ''
            if dt:
                from datetime import datetime
                d = datetime.fromtimestamp(dt/1000)
                date_str = d.strftime('%Y-%m-%d')
                time_str = d.strftime('%H:%M:%S')
            # 市场+名称
            market = o.contract.currency if o.contract else '?'
            market_label = 'US' if market == 'USD' else 'HK' if market == 'HKD' else market
            # 股票名称
            name = ''
            if s == 'NIO':
                name = '蔚来'
            elif s == 'CRCL':
                name = 'Circle'
            elif s == '01810':
                name = '小米'
            elif s == '01024':
                name = '快手'
            records.append(f'{s} {action} {o.quantity} {date_str} {market_label} {name} {price} {time_str}')
        return records
    except Exception as e:
        return [f'错误: {e}']

# ===================== 快速测试 =====================
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("🐯 老虎证券 行情/交易 分离架构测试")
    print("=" * 50)

    # 行情测试
    print("\n📈 [1] 港股行情:")
    for sym in ['00700', '09988']:
        print(f"  {get_stock_brief(sym)}")

    print("\n🇨🇳 [2] A股行情:")
    for sym in ['600519', '000858']:
        print(f"  {get_stock_brief(sym)}")

    # 交易测试
    print("\n📊 [3] 模拟账户:")
    print(f"  {get_account_info()}")

    print("\n💼 [4] 持仓:")
    print(f"  {get_positions()}")

    print("\n📋 [5] 订单:")
    print(f"  {get_today_orders()}")

    print("\n" + "=" * 50)
    print("🏁 测试完成")
    print("=" * 50)
