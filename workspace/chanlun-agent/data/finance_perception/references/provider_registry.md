# 数据源注册表 (Provider Registry)

> 详细说明各数据源的能力、限制和配置方式

## 概览

| Provider | 市场 | 免费额度 | 限流 | 优先级 |
|----------|------|----------|------|--------|
| iTick | US/HK/SH/SZ/GB | 有限 | 5次/分钟 | 高 |
| Binance | CC | 完全免费 | 1200权重/分钟 | 高 |
| Polygon.io | US/GB/CC | 5次/分钟 | 5次/分钟 | 中 |
| AKShare | SH/SZ | 完全免费 | 无明确限制 | 低 |
| FRED | MACRO | 完全免费 | 无明确限制 | 中 |

---

## 1. iTick

**Base URL**: `https://api0.itick.org`

### 能力矩阵

| 市场 | 报价 | K线 | 实时 | 历史 |
|------|------|-----|------|------|
| 美股 (US) | ✅ | ✅ | ✅ | ✅ |
| 港股 (HK) | ✅ | ✅ | ✅ | ✅ |
| A股沪市 (SH) | ✅ | ✅ | ✅ | ✅ |
| A股深市 (SZ) | ✅ | ✅ | ✅ | ✅ |
| 外汇 (GB) | ✅ | ✅ | ✅ | ✅ |
| 加密货币 | ❌ | ❌ | ❌ | ❌ |

### 限制说明

- **REST API**: 5次/分钟（免费版）
- **每次K线请求**: 最多500条
- **缓存建议**: 实时行情60秒，K线60秒（日线24小时）
- **Key过期**: 注意检查 `key_expires` 日期

### 成本

| 项目 | 免费版 | 付费版 |
|------|--------|--------|
| API调用 | 5次/分钟 | 更高配额 |
| 数据延迟 | 无（实时） | 无（实时） |
| 加密货币 | ❌ | ✅ |

### 获取 Key

1. 访问 [iTick 官网](https://itick.org)
2. 注册账户
3. 在 Dashboard 获取 API Key
4. 将 Key 添加到 `SECRET.md`:

```markdown
ITICK_API_KEY=your_itick_api_key_here
```

### 降级链路

```
iTick 失败 → Polygon.io (美股/外汇) → 跳过该市场
```

---

## 2. Binance

**Base URL**: `https://api.binance.com`

### 能力矩阵

| 市场 | 报价 | K线 | 实时 | 历史 |
|------|------|-----|------|------|
| 加密货币 (CC) | ✅ | ✅ | ✅ | ✅ |

### 限制说明

- **权重限制**: 1200权重/分钟
- **按接口权重计费**:
  - `ticker`: 1权重
  - `klines`: 5权重
  - `depth`: 5权重
  - `24hr`: 1权重
- **缓存建议**: 30秒（ticker），60秒（K线非日线），日线24小时
- **无需 API Key**: 公共接口完全免费

### 成本

| 项目 | 免费版 |
|------|--------|
| 公共接口 | ✅ 完全免费 |
| 签名接口 | 需要 API Key（可选） |

### 获取 Key

公共接口无需 Key。如需交易功能：
1. 登录 [Binance](https://binance.com)
2. 进入 API Management
3. 创建 API Key（仅读取权限推荐）

### 降级链路

```
Binance 失败 → Polygon.io (加密货币) → 返回缓存数据
```

### 常用交易对

```python
# 主流币种
BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT

# 稳定币交易对
USDTBUSD, USDTUSDC, BTCUSDC

# 热门合约
BTCUSD_PERP, ETHUSD_PERP
```

---

## 3. Polygon.io

**Base URL**: `https://api.polygon.io`

### 能力矩阵

| 市场 | 报价 | K线 | 实时 | 历史 |
|------|------|-----|------|------|
| 美股 (US) | ✅ | ✅ | ⚠️ 延迟 | ✅ |
| 外汇 (GB) | ✅ | ✅ | ⚠️ 延迟 | ✅ |
| 加密货币 (CC) | ✅ | ✅ | ⚠️ 延迟 | ✅ |

### 限制说明

- **免费版**: 5次/分钟
- **延迟数据**: 免费版提供上一个交易日的收盘数据
- **支持 Markets**:
  - Stocks (美股)
  - Forex (外汇)
  - Crypto (加密货币)

### 成本

| 项目 | 免费版 | Starter | Developer |
|------|--------|---------|-----------|
| API调用 | 5次/分钟 | 100次/分钟 | 1000次/分钟 |
| 数据延迟 | 延迟15分钟 | 延迟15分钟 | 实时 |
| 历史数据 | 有限 | 完整 | 完整 |

### 获取 Key

1. 访问 [Polygon.io](https://polygon.io)
2. 注册免费账户
3. 获取 API Key
4. 配置两个 Key（V1备用，V2优先）:

```markdown
POLYGON_API_KEY_V1=your_polygon_v1_key
POLYGON_API_KEY_V2=your_polygon_v2_key
```

### 降级链路

```
Polygon V2 → Polygon V1 → iTick (美股) → 缓存数据
```

---

## 4. AKShare

**接口类型**: Python库

### 能力矩阵

| 市场 | 报价 | K线 | 实时 | 历史 |
|------|------|-----|------|------|
| A股沪市 (SH) | ✅ | ✅ | ✅ | ✅ |
| A股深市 (SZ) | ✅ | ✅ | ✅ | ✅ |
| 期货 | ✅ | ✅ | ✅ | ✅ |

### 限制说明

- **无需 API Key**: 完全免费
- **限流**: 无明确限制，建议礼貌使用
- **安装**: `pip install akshare`
- **缓存建议**: 60秒

### 成本

完全免费，无任何限制。

### 安装

```bash
pip install akshare
```

### 降级链路

```
AKShare 失败 → iTick (A股) → 跳过该标的
```

---

## 5. FRED (宏观经济)

**Base URL**: `https://api.stlouisfed.org/fred`

### 能力矩阵

| 数据类型 | 获取 | 说明 |
|----------|------|------|
| 利率 | ✅ | 联邦基金利率、国债收益率 |
| GDP | ✅ | 美国GDP数据 |
| CPI | ✅ | 消费者价格指数 |
| 失业率 | ✅ | 劳动力市场数据 |
| 零售销售 | ✅ | 消费数据 |
| 制造业PMI | ✅ | 采购经理指数 |

### 限制说明

- **完全免费**: 无任何限制
- **需注册**: 需要 FRED API Key
- **数据延迟**: 通常有1-2个月延迟（取决于指标）

### 获取 Key

1. 访问 [FRED API](https://fred.stlouisfed.org/docs/api/fred/)
2. 注册账户（免费）
3. 获取 API Key
4. 添加到 `SECRET.md`:

```markdown
FRED_API_KEY=your_fred_api_key
```

### 常用指标代码

| 代码 | 名称 | 频率 |
|------|------|------|
| DFF | 联邦基金有效利率 | 日 |
| DGS10 | 10年期国债收益率 | 日 |
| GDP | 国内生产总值 | 季度 |
| CPIAUCSL | 消费者价格指数 | 月 |
| UNRATE | 失业率 | 月 |
| PCE | 个人消费支出 | 月 |
| ISM Manufacturing PMI | 制造业PMI | 月 |

### 降级链路

```
FRED 失败 → 跳过宏观数据
```

---

## 市场/能力矩阵汇总

```
                    │ iTick │ Binance │ Polygon │ AKShare │ FRED
────────────────────┼───────┼─────────┼─────────┼─────────┼──────
美股 (US)           │  ✅   │    ❌   │   ✅    │    ❌   │  ❌
港股 (HK)           │  ✅   │    ❌   │    ❌   │    ❌   │  ❌
A股沪市 (SH)        │  ✅   │    ❌   │    ❌   │   ✅    │  ❌
A股深市 (SZ)        │  ✅   │    ❌   │    ❌   │   ✅    │  ❌
外汇 (GB)           │  ✅   │    ❌   │   ✅    │    ❌   │  ❌
加密货币 (CC)       │  ❌   │   ✅    │   ✅    │    ❌   │  ❌
宏观经济 (MACRO)    │  ❌   │    ❌   │    ❌   │    ❌   │  ✅
────────────────────┼───────┼─────────┼─────────┼─────────┼──────
免费程度           │ 有限  │ 完全免费│   有限  │ 完全免费│完全免费
限流               │ 5/分  │1200权重 │  5/分   │   无    │  无
```

---

## 自定义 Provider

如需添加新的数据源，参考以下模板：

```python
class CustomProvider:
    """
    自定义数据源示例
    
    1. 继承基础 Provider 接口
    2. 实现 get_quote() 和 get_kline()
    3. 注册到 FinanceFetcher.provider_registry
    """
    
    BASE_URL = "https://api.example.com"
    
    def __init__(self, api_key: str, rate_limiter: RateLimiter):
        self.api_key = api_key
        self.rate_limiter = rate_limiter
        self.cache = CacheManager()
    
    def get_quote(self, code: str, region: str) -> Optional[Quote]:
        """获取报价"""
        # 实现...
        pass
    
    def get_kline(self, code: str, region: str, 
                  interval: str, limit: int) -> List[KlineBar]:
        """获取K线"""
        # 实现...
        pass
    
    def health_check(self) -> bool:
        """健康检查"""
        # 实现...
        pass
```

详细集成步骤见 [integration_guide.md](integration_guide.md)
