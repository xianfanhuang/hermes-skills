# Session 提取 - 交易实践

- **来源 Session:** e2012024-f55a-4a5b-90e2-6882e31c1760
- **提取日期:** 2026-05-27
- **类型:** 实战记录

---


• 权益: $10,036.50 | 未实现盈亏: +$136.50 (+1.43%)
• 可用现金: $7,350

1. A50继续持有，建议止损上移至102保护利润
2. 若触及108-109可减仓1/3，剩余追踪
3. 美股/BTC/黄金均处于观望状态，暂不操作

        text += f"{p.symbol} | 持仓数量：{p.quantity} | 成本价：{p.cost_price} | 盈亏：{p.unrealized_pnl}
"
    return text

        txt += f"{p.symbol} 持仓{p.quantity} 盈亏{p.unrealized_pnl}
"
    return txt

- 附加单 (Attached) - 止盈止损
- 算法单 (TWAP/VWAP) - 大单拆分

| 逐笔数据 | Tick-by-tick 交易记录 |
| 深度行情 | 10档/40档买卖盘 |
| 期权链 | 行权价、到期日、希腊字母 |
| 期货 | 合约列表、交易时间 |
| 选股器 | 市值/PE/ROE 等多条件筛选 |
| 资金流 | 个股资金流向、资金分布 |
| 基本面 | 财务报表、股息、财报日历 |

# 手动买入/卖出
python3 crcl_tiger_trader.py --buy 10
python3 crcl_tiger_trader.py --sell 10 --price 115.00
```

2. 卖出信号：5分钟顶背驰确认 / 跌破止损位
3. 仓位管理：3%风险比例，最大50%仓位

# 手动买入/卖出
python3 crcl_tiger_trader.py --buy 10
python3 crcl_tiger_trader.py --sell 10 --price 115.00
```

2. 卖出信号：5分钟顶背驰确认 / 跌破止损位
3. 仓位管理：3%风险比例，最大50%仓位


---
*自动提取 by knowledge-extract.sh*
