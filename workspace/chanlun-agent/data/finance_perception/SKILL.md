---
name: finance-perception
description: 金融数据感知技能 - 跨市场行情获取、K线分析、信号扫描、智能路由。支持美股/港股/A股/外汇/加密货币/宏观经济。供 OpenClaw 智能体按需接入金融数据能力。
version: 2.0.0
license: MIT
tags: [金融数据, 市场行情, 信号扫描, 智能路由, OpenClaw]
author: Top Sailor
---

# Finance Perception v2.0

> 🚀 金融数据感知基础设施 - Agent的金融市场之眼

## 核心功能

| 功能 | 说明 |
|------|------|
| 跨市场行情 | 美股、港股、A股、外汇、加密货币、期货 |
| K线数据 | 多周期技术图表（1m/5m/15m/30m/1h/1d/1w/1M） |
| 信号扫描 | 价格突破、成交量突增、异常波动检测 |
| 宏观经济 | 利率、CPI、GDP等关键指标 |
| 智能路由 | 自动选择最优数据源，降级链路保障 |
| 感知信号 | 结构化市场信号输出，对接 Agent 决策 |

## 快速开始（3步接入）

### Step 1: 配置密钥

在项目根目录的 `SECRET.md` 中添加所需 API Key：

```markdown
## 金融数据 API Keys
ITICK_API_KEY=your_itick_key
POLYGON_API_KEY_V1=your_polygon_key_v1
POLYGON_API_KEY_V2=your_polygon_key_v2
```

### Step 2: 初始化模块

```python
import sys
sys.path.insert(0, '../global-info-fetcher')
from finance_fetcher import FinanceFetcher

# 初始化（自动从 SECRET.md 读取密钥）
fetcher = FinanceFetcher()
```

### Step 3: 获取数据

```python
# 获取报价
quote = fetcher.get_quote("AAPL", "US")

# 获取K线
klines = fetcher.get_kline("AAPL", "US", "101", limit=100)

# 扫描信号
signals = fetcher.scan_signals({"US": ["AAPL", "TSLA"], "CC": ["BTCUSDT"]})
```

## 支持的市场和数据源

### 市场覆盖

| 市场 | 代码 | 示例标的 | 主要数据源 |
|------|------|----------|------------|
| 美股 | US | AAPL, TSLA, NVDA | iTick, Polygon.io |
| 港股 | HK | 00700, 09988 | iTick |
| A股 | SH/SZ | 600000, 000001 | iTick, AKShare |
| 外汇 | GB | USDJPY, EURUSD | iTick, Polygon.io |
| 加密货币 | CC | BTCUSDT, ETHUSDT | Binance, Polygon.io |
| 宏观经济 | MACRO | GDP, CPI, FED | FRED |

### 数据源详情

| 数据源 | 市场 | 免费额度 | 限流 | 特点 |
|--------|------|----------|------|------|
| iTick | US/HK/SH/SZ/GB | 有限 | 5次/分钟 | 覆盖全面，A股/港股首选 |
| Binance | CC | 完全免费 | 1200权重/分钟 | 加密货币最佳源 |
| Polygon.io | US/GB/CC | 5次/分钟 | 5次/分钟(免费) | 专业级美股数据 |
| AKShare | SH/SZ | 完全免费 | 无明确限制 | A股数据补充 |
| FRED | MACRO | 完全免费 | 无明确限制 | 宏观经济权威源 |

详细说明见 [references/provider_registry.md](references/provider_registry.md)

## API 参考

### FinanceFetcher 主类

```python
class FinanceFetcher:
    """金融数据感知主类"""
    
    def __init__(self, config_path: str = None, secret_path: str = None):
        """
        初始化
        
        Args:
            config_path: 数据源配置文件路径（默认使用内置配置）
            secret_path: 密钥文件路径（默认从项目根目录读取 SECRET.md）
        """
    
    def get_quote(self, code: str, region: str) -> Optional[Quote]:
        """
        获取实时行情
        
        Args:
            code: 标的代码，如 "AAPL", "BTCUSDT"
            region: 市场区域，如 "US", "HK", "CC", "GB"
        
        Returns:
            Quote 对象，失败返回 None
        """
    
    def get_kline(self, code: str, region: str, interval: str = "101", 
                  limit: int = 100) -> List[KlineBar]:
        """
        获取K线数据
        
        Args:
            code: 标的代码
            region: 市场区域
            interval: K线周期 ("1", "5", "15", "30", "60", "101"=日, "102"=周, "103"=月)
            limit: 返回数量（最大500）
        
        Returns:
            List[KlineBar]
        """
    
    def scan_signals(self, watchlist: Dict[str, List[str]]) -> List[FinancePerceptionSignal]:
        """
        扫描市场信号
        
        Args:
            watchlist: 监控列表，格式 {"市场": ["标的1", "标的2"]}
        
        Returns:
            List[FinancePerceptionSignal]，按严重程度排序
        """
    
    def health_check(self) -> Dict[str, bool]:
        """
        健康检查
        
        Returns:
            Dict[str, bool]，各数据源状态
        """
    
    def get_status_report(self) -> str:
        """获取状态报告（Markdown格式）"""
```

### 数据类

#### Quote - 行情数据

```python
@dataclass
class Quote:
    symbol: str           # 股票代码
    market: str           # 市场（US/HK/SH/SZ/GB/CC）
    name: str             # 名称
    price: float          # 最新价
    change: float         # 涨跌额
    change_pct: float     # 涨跌幅（%）
    volume: int           # 成交量
    amount: float         # 成交额
    high: float           # 最高
    low: float            # 最低
    open: float           # 开盘
    prev_close: float     # 昨收
    timestamp: str        # 数据时间
    source: str            # 数据来源
```

#### KlineBar - K线数据

```python
@dataclass
class KlineBar:
    symbol: str
    market: str
    timestamp: str        # K线时间
    open: float
    high: float
    low: float
    close: float
    volume: int
    interval: str         # 周期
    source: str
```

#### FinancePerceptionSignal - 感知信号

```python
@dataclass
class FinancePerceptionSignal:
    signal_type: str      # 信号类型
    source: str           # 数据来源
    title: str            # 信号标题
    symbol: str           # 关联标的
    severity: str         # critical/high/medium/low/info
    summary: Optional[str] = None
    quote_data: Optional[Quote] = None
```

### 枚举类型

```python
class Market(Enum):
    US = "US"           # 美股
    HK = "HK"           # 港股
    SH = "SH"           # 上海
    SZ = "SZ"           # 深圳
    GB = "GB"           # 外汇
    CC = "CC"           # 加密货币
    FUTURES = "FUTURES" # 期货

class KlineInterval(Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    D1 = "1d"
    W1 = "1w"
    MN = "1M"

class FinanceSignalType(Enum):
    MARKET_SIGNAL = "market_signal"         # 市场信号
    FINANCIAL_ANOMALY = "financial_anomaly" # 金融异常
    PRICE_BREAKOUT = "price_breakout"       # 价格突破
    VOLUME_SPIKE = "volume_spike"          # 成交量突增
    MACRO_EVENT = "macro_event"            # 宏观事件
```

## 智能路由

FinanceFetcher 内置智能路由机制：

1. **优先级路由**：按配置的优先级选择数据源
2. **自动降级**：主源失败时自动切换到备源
3. **降级恢复**：自动检测源恢复并切回
4. **负载均衡**：在多个等优先级的源之间轮询

详细路由规则见 [references/routing_protocol.md](references/routing_protocol.md)

## 配置要求

### 必须的密钥（SECRET.md）

| 密钥 | 必需 | 用途 | 获取方式 |
|------|------|------|----------|
| ITICK_API_KEY | 推荐 | 美股/港股/A股/外汇 | iTick官网注册 |
| POLYGON_API_KEY_V1 | 可选 | 美股/外汇/加密货币 | Polygon.io免费注册 |
| POLYGON_API_KEY_V2 | 推荐 | Polygon V2（优先使用） | Polygon.io |
| AKSHARE_TOKEN | 可选 | A股补充数据 | AKShare免费使用 |

### 可选配置

```json
// sources_config.json
{
  "sources": {
    "itick": {
      "status": "active",
      "priority": 1,
      "rate_limit": 5
    },
    "binance": {
      "status": "active", 
      "priority": 1
    }
  }
}
```

## 使用示例

### 基础行情查询

```python
from finance_fetcher import FinanceFetcher

fetcher = FinanceFetcher()

# 美股报价
apple = fetcher.get_quote("AAPL", "US")
print(f"AAPL: ${apple.price:.2f} ({apple.change_pct:+.2f}%)")

# 港股报价
tencent = fetcher.get_quote("00700", "HK")
print(f"腾讯: HK${tencent.price:.2f}")

# 加密货币
btc = fetcher.get_quote("BTCUSDT", "CC")
print(f"BTC: ${btc.price:.2f}")
```

### K线技术分析

```python
# 获取日K线
daily_klines = fetcher.get_kline("AAPL", "US", "101", limit=100)

# 计算均线（示例）
closes = [k.close for k in daily_klines]
ma5 = sum(closes[-5:]) / 5
ma20 = sum(closes[-20:]) / 20

# 检测金叉/死叉
if ma5 > ma20 and closes[-2] <= (sum(closes[-7:-2]) / 5):
    print("📈 金叉信号：MA5 上穿 MA20")
```

### 多市场监控

```python
# 构建监控列表
watchlist = {
    "US": ["AAPL", "TSLA", "NVDA", "MSFT"],
    "HK": ["00700", "09988", "09888"],
    "CC": ["BTCUSDT", "ETHUSDT"],
    "GB": ["USDJPY", "EURUSD"]
}

# 扫描信号
signals = fetcher.scan_signals(watchlist)

# 按严重程度处理
for sig in signals:
    emoji = {"critical": "🚨", "high": "⚠️", "medium": "⚡"}.get(sig.severity, "ℹ️")
    print(f"{emoji} [{sig.severity.upper()}] {sig.title}")
```

### 生成市场报告

```python
def generate_market_report(fetcher, watchlist):
    report = ["# 市场行情报告\n"]
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    signals = fetcher.scan_signals(watchlist)
    if signals:
        report.append("## 🚨 市场信号\n")
        for sig in signals:
            report.append(sig.to_markdown())
            report.append("")
    
    return "\n".join(report)
```

## 与其他 Skill 的关系

### 依赖 global-info-fetcher

本 Skill 依赖 `global-info-fetcher` 的信号基础设施：

- 使用相同的 `SignalType` 枚举（`FinanceSignalType` 扩展）
- 信号输出格式兼容 `FinancePerceptionSignal`
- 可与 global-info-fetcher 的其他信号合并处理

```python
# 示例：合并金融信号和其他感知信号
from global_info_fetcher import GlobalInfoAggregator, SignalType

aggregator = GlobalInfoAggregator()
finance_fetcher = FinanceFetcher()

# 获取金融信号
finance_signals = finance_fetcher.scan_signals(watchlist)

# 获取其他感知信号
other_results = await aggregator.fetch_all()
other_signals = aggregator.get_perception_signals(other_results)

# 合并处理
all_signals = finance_signals + other_signals
```

### 与 agent-browser 配合

可用于：
- 定时监控市场行情，触发交易决策
- 扫描交易机会，主动推送信号
- 宏观经济数据更新提醒

## 常见问题

### Q: 获取数据失败怎么办？

```python
# 检查健康状态
health = fetcher.health_check()
print(health)

# 手动指定数据源
fetcher = FinanceFetcher()
fetcher.force_source("binance")  # 强制使用 Binance
```

### Q: 如何扩展新的数据源？

参考 [references/integration_guide.md](references/integration_guide.md)

### Q: API 调用被限流了？

系统自动处理降级和等待。如需调整限流参数，修改 `sources_config.json`。

## 版本历史

- **v2.0**: 智能路由 v2、重构 Provider 架构、信号系统增强
- **v1.0**: 基础行情和K线数据获取

## 参考文档

- [provider_registry.md](references/provider_registry.md) - 数据源注册表
- [routing_protocol.md](references/routing_protocol.md) - 路由协议
- [integration_guide.md](references/integration_guide.md) - 集成指南

---

**维护者**: Top Sailor  
**问题反馈**: 通过 OpenClaw Issue 追踪
