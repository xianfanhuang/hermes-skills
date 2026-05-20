# Tiger Broker (老虎证券) Skill - 新加坡区

## 概述
老虎证券 Python SDK，新加坡区专属，支持模拟/实盘自动切换。

## 环境变量 (OpenClaw .env)

| 变量 | 说明 |
|------|------|
| `TIGER_ID` | 老虎开放平台 Tiger ID |
| `TIGER_PRIVATE_KEY` | RSA 私钥 (PKCS#8 DER base64，无PEM头尾) |
| `TIGER_MODE` | `simulation` (模拟) 或 `live` (实盘) |
| `TIGER_SIMULATION_ACCOUNT` | 模拟账户 ID |
| `TIGER_LIVE_ACCOUNT` | 实盘账户 ID |

## 区域配置 (固定)
- Region: `Region.SG` (新加坡)
- 模拟: `Env.SANDBOX_SG`
- 实盘: `Env.PRODUCTION_SG`

## 域名 (已验证)
- 生产: `https://openapi.tigerfintech.com/gateway`
- 模拟: `https://openapi-sandbox.tigerfintech.com/gateway`
- ⚠️ `openapi-sgp.itigerup.com` 域名不存在，不要使用

## API 函数

| 函数 | 说明 |
|------|------|
| `get_stock_brief(symbol)` | 获取股票行情摘要 (简要) |
| `get_stock_quote(symbol)` | 获取股票详细报价 |
| `get_account_info()` | 获取账户总资产/可用资金/购买力/盈亏 |
| `get_positions()` | 查询全部持仓 |
| `place_order_limit(symbol, price, quantity, action)` | 限价单下单 |
| `place_order_market(symbol, quantity, action)` | 市价单下单 |
| `cancel_order(order_id)` | 撤单 |
| `get_today_orders()` | 查询今日所有订单 |
| `get_open_orders()` | 查询未成交订单 |

## 依赖
- `tigeropen` (Python SDK v3.5.8+)
- `pip install tigeropen`

## 配置状态
- [x] Tiger ID: 20159412
- [x] Private Key: PKCS#8 DER 格式
- [x] 模拟账户: 21409378833585169
- [x] 实盘账户: 1406653
- [x] 域名验证: openapi.tigerfintech.com ✅
