# 集成指南 (Integration Guide)

> 面向其他 OpenClaw 智能体的开发者指南

## 目录

- [最小集成（3行代码）](#最小集成3行代码)
- [自定义 Watchlist](#自定义-watchlist)
- [信号订阅](#信号订阅)
- [与 Agent 感知层对接](#与-agent-感知层对接)
- [常见问题](#常见问题)

---

## 最小集成（3行代码）

将以下代码复制到你的智能体中即可快速接入金融数据能力：

```python
import sys
sys.path.insert(0, '../global-info-fetcher')
from finance_fetcher import FinanceFetcher

# 初始化
fetcher = FinanceFetcher()

# 获取报价
quote = fetcher.get_quote("AAPL", "US")
print(f"AAPL: ${quote.price:.2f}")
```

### 完整示例

```python
#!/usr/bin/env python3
"""Finance Perception - 最小集成示例"""
import sys
sys.path.insert(0, '../global-info-fetcher')
from finance_fetcher import FinanceFetcher

def main():
    # 1. 初始化
    fetcher = FinanceFetcher()
    
    # 2. 健康检查
    health = fetcher.health_check()
    print("数据源状态:", health)
    
    # 3. 获取报价
    quote = fetcher.get_quote("AAPL", "US")
    if quote:
        print(f"AAPL: ${quote.price:.2f} ({quote.change_pct:+.2f}%)")
    
    # 4. 获取K线
    klines = fetcher.get_kline("AAPL", "US", "101", limit=10)
    print(f"K线数量: {len(klines)}")
    
    # 5. 扫描信号
    signals = fetcher.scan_signals({"US": ["AAPL"]})
    for sig in signals:
        print(f"[{sig.severity}] {sig.title}")

if __name__ == "__main__":
    main()
```

---

## 自定义 Watchlist

### 基本用法

```python
# 定义你的监控列表
my_watchlist = {
    "US": ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"],
    "HK": ["00700", "09988", "09888"],
    "CC": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "GB": ["USDJPY", "EURUSD", "GBPUSD"]
}

# 扫描所有标的
all_signals = fetcher.scan_signals(my_watchlist)
```

### 按行业分组

```python
watchlist_by_sector = {
    "tech": {
        "US": ["AAPL", "MSFT", "GOOGL", "META", "NVDA"],
        "HK": ["00700"]
    },
    "finance": {
        "US": ["JPM", "BAC", "GS", "MS"],
        "HK": ["0939", "3988"]
    },
    "crypto": {
        "CC": ["BTCUSDT", "ETHUSDT"]
    }
}

# 分别处理不同行业的信号
for sector, watchlist in watchlist_by_sector.items():
    signals = fetcher.scan_signals(watchlist)
    print(f"\n=== {sector.upper()} 信号 ({len(signals)}个) ===")
    for sig in signals:
        print(f"  [{sig.severity}] {sig.symbol}: {sig.title}")
```

### 动态 Watchlist

```python
import json

def load_watchlist_from_file(path: str) -> dict:
    """从文件加载监控列表"""
    with open(path, 'r') as f:
        return json.load(f)

def save_watchlist_to_file(path: str, watchlist: dict):
    """保存监控列表到文件"""
    with open(path, 'w') as f:
        json.dump(watchlist, f, indent=2)

# 使用
watchlist = load_watchlist_from_file('./my_watchlist.json')
signals = fetcher.scan_signals(watchlist)
```

---

## 信号订阅

### 实时信号监控

```python
import threading
import time

class SignalMonitor:
    """信号监控器"""
    
    def __init__(self, fetcher, watchlist, interval=300):
        self.fetcher = fetcher
        self.watchlist = watchlist
        self.interval = interval  # 检查间隔（秒）
        self.running = False
        self.callbacks = []
    
    def add_callback(self, callback):
        """添加信号回调"""
        self.callbacks.append(callback)
    
    def start(self):
        """启动监控"""
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        print(f"信号监控已启动，间隔 {self.interval} 秒")
    
    def stop(self):
        """停止监控"""
        self.running = False
        print("信号监控已停止")
    
    def _run(self):
        while self.running:
            try:
                signals = self.fetcher.scan_signals(self.watchlist)
                
                # 按严重程度筛选
                critical = [s for s in signals if s.severity == "critical"]
                high = [s for s in signals if s.severity == "high"]
                
                # 触发回调
                for callback in self.callbacks:
                    callback(signals)
                
                # 打印摘要
                if signals:
                    print(f"检测到 {len(signals)} 个信号 "
                          f"(critical: {len(critical)}, high: {len(high)})")
            
            except Exception as e:
                print(f"监控错误: {e}")
            
            time.sleep(self.interval)

# 使用示例
def handle_signals(signals):
    """处理信号的回调函数"""
    for sig in signals:
        if sig.severity in ["critical", "high"]:
            print(f"🚨 [{sig.severity.upper()}] {sig.symbol}: {sig.title}")

monitor = SignalMonitor(fetcher, watchlist, interval=300)
monitor.add_callback(handle_signals)
monitor.start()

# 5分钟后停止
time.sleep(300)
monitor.stop()
```

### 过滤特定信号类型

```python
def filter_signals(signals, 
                  severity: list = None,
                  signal_types: list = None,
                  symbols: list = None) -> list:
    """过滤信号"""
    result = signals
    
    if severity:
        result = [s for s in result if s.severity in severity]
    
    if signal_types:
        result = [s for s in result if s.signal_type in signal_types]
    
    if symbols:
        result = [s for s in result if s.symbol in symbols]
    
    return result

# 使用
all_signals = fetcher.scan_signals(watchlist)

# 只看价格突破信号
breakout_signals = filter_signals(
    all_signals,
    signal_types=["price_breakout"]
)

# 只看高严重程度的信号
urgent_signals = filter_signals(
    all_signals,
    severity=["critical", "high"]
)
```

---

## 与 Agent 感知层对接

### 方案一：合并到 GlobalInfoAggregator

```python
import sys
sys.path.insert(0, '../global-info-fetcher')
from global_info_fetcher import GlobalInfoAggregator
from finance_fetcher import FinanceFetcher, FinanceSignalType

class UnifiedPerception:
    """统一感知层 - 合并金融数据和其他感知信号"""
    
    def __init__(self):
        self.global_fetcher = GlobalInfoAggregator()
        self.finance_fetcher = FinanceFetcher()
    
    async def fetch_all(self):
        """获取所有感知信号"""
        # 1. 获取传统感知信号
        global_results = await self.global_fetcher.fetch_all()
        global_signals = self.global_fetcher.get_perception_signals(global_results)
        
        # 2. 获取金融信号
        finance_signals = self.finance_fetcher.scan_signals(watchlist)
        
        # 3. 合并
        return {
            "global_signals": global_signals,
            "finance_signals": finance_signals,
            "all_signals": global_signals + finance_signals
        }
    
    def get_action_required(self):
        """获取需要行动的信号"""
        all_signals = self.fetch_all()["all_signals"]
        
        # 高严重程度的金融信号
        urgent_finance = [
            s for s in all_signals 
            if isinstance(s, FinancePerceptionSignal) 
            and s.severity in ["critical", "high"]
        ]
        
        # 其他行动信号
        other_action = self.global_fetcher.get_action_required_signals(
            self.global_fetcher.fetch_all()
        )
        
        return urgent_finance + other_action
```

### 方案二：独立金融感知模块

```python
class FinancePerceptionModule:
    """
    独立金融感知模块
    
    可被任何智能体继承使用
    """
    
    def __init__(self, watchlist: dict, config: dict = None):
        self.fetcher = FinanceFetcher()
        self.watchlist = watchlist
        self.config = config or {}
    
    async def perceive(self) -> dict:
        """
        执行一次感知
        
        Returns:
            {
                "quotes": [...],
                "signals": [...],
                "summary": "..."
            }
        """
        quotes = self._fetch_quotes()
        signals = self.fetcher.scan_signals(self.watchlist)
        
        return {
            "quotes": quotes,
            "signals": signals,
            "summary": self._generate_summary(signals)
        }
    
    def _fetch_quotes(self) -> list:
        """获取所有报价"""
        quotes = []
        for market, symbols in self.watchlist.items():
            for symbol in symbols:
                quote = self.fetcher.get_quote(symbol, market)
                if quote:
                    quotes.append(quote)
        return quotes
    
    def _generate_summary(self, signals: list) -> str:
        """生成摘要"""
        if not signals:
            return "无异常信号"
        
        by_severity = {}
        for sig in signals:
            by_severity.setdefault(sig.severity, []).append(sig.symbol)
        
        parts = []
        for sev in ["critical", "high", "medium"]:
            if sev in by_severity:
                parts.append(f"{sev.upper()}: {', '.join(by_severity[sev])}")
        
        return "; ".join(parts)
```

### 方案三：定期报告

```python
async def daily_finance_report():
    """生成每日金融报告"""
    report = ["# 📊 每日金融报告\n"]
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    # 市场概览
    report.append("## 市场概览\n")
    report.append("| 标的 | 价格 | 涨跌幅 | 来源 |\n")
    report.append("|------|------|--------|------|\n")
    
    for market, symbols in watchlist.items():
        for symbol in symbols[:3]:  # 每类最多3个
            quote = fetcher.get_quote(symbol, market)
            if quote:
                report.append(
                    f"| {symbol} | ${quote.price:.2f} | "
                    f"{quote.change_pct:+.2f}% | {quote.source} |\n"
                )
    
    # 信号摘要
    signals = fetcher.scan_signals(watchlist)
    if signals:
        report.append("\n## 🚨 信号摘要\n")
        for sig in signals[:5]:
            report.append(f"- **[{sig.severity.upper()}]** {sig.title}\n")
    
    return "".join(report)
```

---

## 常见问题

### Q1: 如何处理 API Key 缺失？

```python
fetcher = FinanceFetcher()

# 检查哪些源可用
health = fetcher.health_check()
available = [k for k, v in health.items() if v]
print(f"可用数据源: {available}")

# 强制使用可用源
if "binance" in available:
    fetcher.force_source("binance")
```

### Q2: 如何获取历史数据？

```python
# 获取历史K线
klines = fetcher.get_kline("AAPL", "US", "101", limit=500)  # 约2年日K

# 计算技术指标
closes = [k.close for k in klines]
ma_20 = sum(closes[-20:]) / 20
ma_60 = sum(closes[-60:]) / 60
```

### Q3: 如何处理限流？

```python
from time import sleep

def get_with_retry(fetcher, symbol, market, max_retries=3):
    """带重试的获取"""
    for i in range(max_retries):
        try:
            return fetcher.get_quote(symbol, market)
        except RateLimitExceeded:
            wait_time = 60 * (i + 1)
            print(f"限流，等待 {wait_time} 秒...")
            sleep(wait_time)
    return None
```

### Q4: 如何存储历史数据？

```python
import json
from datetime import datetime

def save_to_history(symbol: str, quote: Quote, filepath: str = "./history"):
    """保存报价到历史文件"""
    import os
    os.makedirs(filepath, exist_ok=True)
    
    filename = f"{filepath}/{symbol}_{datetime.now().strftime('%Y%m%d')}.json"
    
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
    else:
        data = {"symbol": symbol, "quotes": []}
    
    data["quotes"].append({
        "timestamp": quote.timestamp,
        "price": quote.price,
        "change_pct": quote.change_pct
    })
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
```

### Q5: 如何集成到定时任务？

```bash
# crontab 示例
# 每天9:30执行
30 9 * * * cd /path/to/project && python scripts/quick_start.py >> /var/log/finance.log 2>&1

# 每15分钟检查一次
*/15 * * * * cd /path/to/project && python scripts/health_daemon.py
```

### Q6: 如何调试路由问题？

```python
# 开启调试模式
fetcher.set_log_level("DEBUG")

# 获取路由决策
quote = fetcher.get_quote("AAPL", "US", debug=True)
# 输出:
# DEBUG: Requesting AAPL from US
# DEBUG: Trying iTick (priority=1)... FAILED (RateLimitExceeded)
# DEBUG: Trying Polygon (priority=2)... SUCCESS
# DEBUG: Using Polygon data
```

---

## 进一步资源

- [SKILL.md](../SKILL.md) - 完整 API 文档
- [provider_registry.md](./provider_registry.md) - 数据源详情
- [routing_protocol.md](./routing_protocol.md) - 路由机制
- [quick_start.py](../scripts/quick_start.py) - 快速启动脚本
- [health_daemon.py](../scripts/health_daemon.py) - 健康检查脚本
