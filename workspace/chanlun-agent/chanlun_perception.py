#!/usr/bin/env python3
"""
缠论数据感知集成层
将 FinanceFetcher 与 CZSC 连接，实现：
1. 自动获取多市场K线数据
2. CZSC 缠论结构分析
3. 信号生成与推送

Author: VAN's Trading Assistant
Version: 1.0.0
"""

import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / "data" / "finance_fetcher"))
sys.path.insert(0, str(Path(__file__).parent / "data" / "finance_perception" / "scripts"))

# CZSC 导入
import czsc
from czsc import CZSC, Freq, format_standard_kline

# FinanceFetcher 导入
try:
    from finance_fetcher import FinanceFetcher, Market, KlineInterval
    HAS_FINANCE_FETCHER = True
except ImportError:
    HAS_FINANCE_FETCHER = False
    logging.warning("FinanceFetcher not available, using mock data")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ChanlunPerception")

# ============ 数据结构 ============

@dataclass
class ChanlunSignal:
    """缠论信号"""
    symbol: str
    market: str
    freq: str  # 日线/30分钟/5分钟
    signal_type: str  # bi_buy/bi_sell/zs_buy/zs_sell/divergence
    direction: str  # up/down/neutral
    price: float
    timestamp: str
    description: str
    confidence: float  # 0-1
    raw_data: Optional[Dict] = None

@dataclass
class MarketStructure:
    """市场结构分析结果"""
    symbol: str
    market: str
    freq: str
    trend: str  # up/down/range
    bi_count: int
    zs_count: int
    last_bi_direction: str
    last_zs_range: Optional[tuple]  # (low, high)
    divergence: bool
    buy_sell_points: List[Dict]
    analysis_time: str

# ============ 核心集成类 ============

class ChanlunPerception:
    """
    缠论数据感知集成层
    连接 FinanceFetcher 和 CZSC
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        
        # 初始化 FinanceFetcher
        if HAS_FINANCE_FETCHER:
            try:
                self.fetcher = FinanceFetcher(
                    config_path=str(Path(__file__).parent / "data" / "finance_fetcher" / "sources_config.json"),
                    secret_path=str(Path(__file__).parent.parent / "SECRET.md")
                )
                logger.info("FinanceFetcher initialized")
                
                # 检查 API Keys
                self._check_api_keys()
            except Exception as e:
                logger.warning(f"FinanceFetcher initialization failed: {e}")
                self.fetcher = None
        else:
            self.fetcher = None
            logger.warning("FinanceFetcher not available")
        
        # 缠论配置
        self.chanlun_config = self.config.get("chanlun", {})
        
        # 关注品种
        self.watchlist = self.config.get("watchlist", {})
        
        logger.info("ChanlunPerception initialized")
    
    def _check_api_keys(self):
        """检查 API Keys 配置状态"""
        import os
        secret_path = Path(__file__).parent.parent / "SECRET.md"
        
        has_keys = False
        if secret_path.exists():
            with open(secret_path, 'r') as f:
                content = f.read()
                # 检查多种格式
                if 'ITICK_API_KEY=' in content or '**API Key**' in content or 'API Key' in content:
                    # 检查是否有实际值
                    for line in content.split('\n'):
                        # 格式1: ITICK_API_KEY=xxx
                        if line.startswith('ITICK_API_KEY=') and len(line.split('=', 1)[1].strip()) > 0:
                            has_keys = True
                            break
                        # 格式2: - **API Key**: xxx
                        if 'API Key' in line and '**' in line:
                            parts = line.split('**')
                            if len(parts) >= 3:
                                key = parts[-1].strip().strip(':').strip()
                                if key and len(key) > 10:
                                    has_keys = True
                                    break
        
        # 也检查环境变量
        if not has_keys:
            for var in ['ITICK_API_KEY', 'POLYGON_API_KEY_V2', 'FRED_API_KEY']:
                if os.environ.get(var):
                    has_keys = True
                    break
        
        if not has_keys:
            logger.warning("⚠️ No API Keys configured. Using mock data for testing.")
            logger.warning("   Configure keys in SECRET.md or set environment variables:")
            logger.warning("   - ITICK_API_KEY (for US/HK/A-share/Forex)")
            logger.warning("   - POLYGON_API_KEY_V2 (for US/Forex/Crypto)")
            logger.warning("   - FRED_API_KEY (for macro data)")
            logger.warning("   Set fetcher to None for mock mode.")
            self.fetcher = None
    
    def _load_config(self, config_path: str = None) -> Dict:
        """加载配置"""
        if config_path is None:
            config_path = str(Path(__file__).parent / "config" / "settings.yaml")
        
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}, using defaults")
            return {}
    
    # ============ 数据获取 ============
    
    def get_kline_data(self, symbol: str, market: str, 
                       interval: str = "1d", limit: int = 200) -> Optional[List[Dict]]:
        """
        获取K线数据
        
        Args:
            symbol: 标的代码
            market: 市场 (US/HK/SH/SZ/CC/GB)
            interval: K线周期 (1m/5m/15m/30m/1h/1d/1w/1M)
            limit: 返回数量
            
        Returns:
            List[Dict] with keys: timestamp, open, high, low, close, volume
        """
        if not self.fetcher:
            logger.warning("FinanceFetcher not available, returning mock data")
            return self._get_mock_kline(symbol, limit)
        
        try:
            klines = self.fetcher.get_kline(symbol, market, interval, limit)
            if klines:
                return [
                    {
                        "timestamp": k.timestamp,
                        "open": k.open,
                        "high": k.high,
                        "low": k.low,
                        "close": k.close,
                        "vol": k.volume
                    }
                    for k in klines
                ]
            return None
        except Exception as e:
            logger.error(f"Failed to get kline for {symbol}: {e}")
            return None
    
    def _get_mock_kline(self, symbol: str, limit: int = 200) -> List[Dict]:
        """模拟K线数据（用于测试，生成有趋势的数据）"""
        import random
        import math
        data = []
        base_price = 100.0
        
        # 生成有趋势的数据（正弦波 + 噪声）
        for i in range(limit):
            # 使用递增的日期
            from datetime import timedelta
            timestamp = (datetime.now() - timedelta(days=limit-i)).strftime("%Y-%m-%d")
            
            # 趋势：正弦波模拟
            trend = math.sin(i / 20.0) * 10
            noise = random.uniform(-2, 2)
            base_price = 100 + trend + noise
            
            open_price = base_price + random.uniform(-1, 1)
            close_price = base_price + random.uniform(-1, 1)
            high_price = max(open_price, close_price) + random.uniform(0.5, 2)
            low_price = min(open_price, close_price) - random.uniform(0.5, 2)
            volume = random.randint(100000, 1000000)
            
            data.append({
                "timestamp": timestamp,
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "vol": volume
            })
        
        return data
    
    def get_quote(self, symbol: str, market: str) -> Optional[Dict]:
        """获取实时行情"""
        if not self.fetcher:
            return None
        
        try:
            quote = self.fetcher.get_quote(symbol, market)
            if quote:
                return {
                    "symbol": quote.symbol,
                    "price": quote.price,
                    "change": quote.change,
                    "change_pct": quote.change_pct,
                    "volume": quote.volume,
                    "high": quote.high,
                    "low": quote.low,
                    "timestamp": quote.timestamp
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None
    
    # ============ CZSC 缠论分析 ============
    
    def analyze_symbol(self, symbol: str, market: str, 
                       freqs: List[str] = None) -> Dict[str, MarketStructure]:
        """
        对单个品种进行多级别缠论分析
        
        Args:
            symbol: 标的代码
            market: 市场
            freqs: 分析频率列表，默认 ["日线", "30分钟", "5分钟"]
            
        Returns:
            Dict[freq, MarketStructure]
        """
        if freqs is None:
            freqs = self.chanlun_config.get("freqs", ["日线", "30分钟", "5分钟"])
        
        results = {}
        
        # 频率映射
        freq_map = {
            "1分钟": ("1m", Freq.F1),
            "5分钟": ("5m", Freq.F5),
            "15分钟": ("15m", Freq.F15),
            "30分钟": ("30m", Freq.F30),
            "60分钟": ("1h", Freq.F60),
            "日线": ("1d", Freq.D),
            "周线": ("1w", Freq.W),
            "月线": ("1M", Freq.M),
        }
        
        for freq_name in freqs:
            if freq_name not in freq_map:
                logger.warning(f"Unknown frequency: {freq_name}")
                continue
            
            interval, czsc_freq = freq_map[freq_name]
            
            try:
                # 获取K线数据
                kline_data = self.get_kline_data(symbol, market, interval, limit=500)
                if not kline_data or len(kline_data) < 30:
                    logger.warning(f"Insufficient kline data for {symbol} {freq_name}")
                    continue
                
                # 转换为 CZSC RawBar 格式
                import pandas as pd
                df = pd.DataFrame(kline_data)
                df['dt'] = pd.to_datetime(df['timestamp'])
                df['symbol'] = symbol
                df['amount'] = df['vol'] * df['close']  # 估算成交额
                
                # 确保列名正确
                df = df[['dt', 'symbol', 'open', 'high', 'low', 'close', 'vol', 'amount']].copy()
                
                bars = format_standard_kline(df, freq=czsc_freq)
                
                # 创建 CZSC 分析对象
                c = CZSC(bars)
                
                # 分析结构
                structure = self._analyze_structure(c, symbol, market, freq_name)
                results[freq_name] = structure
                
                logger.info(f"Analyzed {symbol} {freq_name}: trend={structure.trend}, "
                          f"bi={structure.bi_count}, zs={structure.zs_count}")
                
            except Exception as e:
                logger.error(f"Failed to analyze {symbol} {freq_name}: {e}")
                continue
        
        return results
    
    def _analyze_structure(self, c: CZSC, symbol: str, market: str, 
                          freq: str) -> MarketStructure:
        """从 CZSC 对象提取结构信息"""
        
        # 基础统计
        bi_list = c.bi_list
        fx_list = c.fx_list
        
        bi_count = len(bi_list)
        
        # 最后一笔方向
        last_bi_direction = bi_list[-1].direction.value if bi_list else "unknown"
        
        # 中枢判断（通过笔的重叠计算）
        zs_list = self._calculate_zs_from_bi(bi_list)
        zs_count = len(zs_list)
        
        # 最后一个中枢范围
        last_zs_range = None
        if zs_list:
            last_zs = zs_list[-1]
            last_zs_range = (last_zs['low'], last_zs['high'])
        
        # 趋势判断
        if bi_count >= 3:
            last_3_bi = bi_list[-3:]
            up_count = sum(1 for b in last_3_bi if b.direction.value == "up")
            if up_count >= 2:
                trend = "up"
            elif up_count <= 1:
                trend = "down"
            else:
                trend = "range"
        else:
            trend = "unknown"
        
        # 背驰判断（简化版）
        divergence = False
        if bi_count >= 5:
            # 比较最后两段的力度
            last_bi = bi_list[-1]
            prev_bi = bi_list[-3] if bi_count >= 3 else bi_list[0]
            
            # 使用价格幅度判断
            last_amplitude = abs(last_bi.high - last_bi.low)
            prev_amplitude = abs(prev_bi.high - prev_bi.low)
            
            if last_bi_direction == "up" and last_amplitude < prev_amplitude * 0.8:
                divergence = True  # 顶背驰
            elif last_bi_direction == "down" and last_amplitude < prev_amplitude * 0.8:
                divergence = True  # 底背驰
        
        # 买卖点
        buy_sell_points = []
        
        return MarketStructure(
            symbol=symbol,
            market=market,
            freq=freq,
            trend=trend,
            bi_count=bi_count,
            zs_count=zs_count,
            last_bi_direction=last_bi_direction,
            last_zs_range=last_zs_range,
            divergence=divergence,
            buy_sell_points=buy_sell_points,
            analysis_time=datetime.now().isoformat()
        )
    
    def _calculate_zs_from_bi(self, bi_list) -> List[Dict]:
        """
        从笔列表计算中枢
        中枢定义：连续三笔有重叠区域
        """
        zs_list = []
        
        if len(bi_list) < 3:
            return zs_list
        
        i = 0
        while i < len(bi_list) - 2:
            # 取三笔
            bi1 = bi_list[i]
            bi2 = bi_list[i + 1]
            bi3 = bi_list[i + 2]
            
            # 计算重叠区间
            overlap_high = min(bi1.high, bi2.high, bi3.high)
            overlap_low = max(bi1.low, bi2.low, bi3.low)
            
            if overlap_high > overlap_low:
                # 有重叠，形成中枢
                zs_list.append({
                    'high': overlap_high,
                    'low': overlap_low,
                    'index': i,
                    'bis': [i, i+1, i+2]
                })
                i += 3  # 跳过已计算的笔
            else:
                i += 1
        
        return zs_list
    
    # ============ 信号扫描 ============
    
    def scan_signals(self, symbols: List[Dict] = None) -> List[ChanlunSignal]:
        """
        扫描所有关注品种的缠论信号
        
        Args:
            symbols: 品种列表，格式 [{"symbol": "AAPL", "market": "US"}, ...]
                     如果为 None，使用配置中的 watchlist
        
        Returns:
            List[ChanlunSignal]
        """
        if symbols is None:
            symbols = self._get_watchlist_symbols()
        
        all_signals = []
        
        for item in symbols:
            symbol = item["symbol"]
            market = item["market"]
            
            logger.info(f"Scanning {symbol} ({market})...")
            
            try:
                # 多级别分析
                structures = self.analyze_symbol(symbol, market)
                
                # 生成信号
                signals = self._generate_signals(symbol, market, structures)
                all_signals.extend(signals)
                
            except Exception as e:
                logger.error(f"Failed to scan {symbol}: {e}")
                continue
        
        # 按严重程度排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_signals.sort(key=lambda s: severity_order.get(s.signal_type, 99))
        
        return all_signals
    
    def _get_watchlist_symbols(self) -> List[Dict]:
        """从配置中提取关注品种列表"""
        symbols = []
        
        # 期货
        for item in self.watchlist.get("futures", []):
            symbols.append({"symbol": item["code"], "market": "FUTURES"})
        
        # 加密货币
        for item in self.watchlist.get("crypto", []):
            symbols.append({"symbol": item["symbol"], "market": "CC"})
        
        # A股
        for item in self.watchlist.get("stocks_cn", []):
            symbols.append({"symbol": item["code"], "market": "SH"})
        
        # 美股
        for item in self.watchlist.get("stocks_us", []):
            symbols.append({"symbol": item["code"], "market": "US"})
        
        return symbols
    
    def _generate_signals(self, symbol: str, market: str, 
                         structures: Dict[str, MarketStructure]) -> List[ChanlunSignal]:
        """从结构分析生成信号"""
        signals = []
        
        for freq, structure in structures.items():
            # 背驰信号
            if structure.divergence:
                if structure.last_bi_direction == "up":
                    signal_type = "divergence_top"
                    direction = "down"
                    description = f"{freq}级别顶背驰，上涨力度衰竭"
                else:
                    signal_type = "divergence_bottom"
                    direction = "up"
                    description = f"{freq}级别底背驰，下跌力度衰竭"
                
                signals.append(ChanlunSignal(
                    symbol=symbol,
                    market=market,
                    freq=freq,
                    signal_type=signal_type,
                    direction=direction,
                    price=0,  # 需要从行情获取
                    timestamp=datetime.now().isoformat(),
                    description=description,
                    confidence=0.7,
                    raw_data={"structure": structure}
                ))
            
            # 中枢震荡信号
            if structure.last_zs_range and structure.trend == "range":
                zs_low, zs_high = structure.last_zs_range
                signals.append(ChanlunSignal(
                    symbol=symbol,
                    market=market,
                    freq=freq,
                    signal_type="zs_range",
                    direction="neutral",
                    price=0,
                    timestamp=datetime.now().isoformat(),
                    description=f"{freq}级别中枢震荡，区间 [{zs_low:.2f}, {zs_high:.2f}]",
                    confidence=0.5,
                    raw_data={"zs_range": structure.last_zs_range}
                ))
            
            # 趋势延续信号
            if structure.trend in ["up", "down"] and structure.bi_count >= 5:
                signals.append(ChanlunSignal(
                    symbol=symbol,
                    market=market,
                    freq=freq,
                    signal_type=f"trend_{structure.trend}",
                    direction=structure.trend,
                    price=0,
                    timestamp=datetime.now().isoformat(),
                    description=f"{freq}级别{structure.trend}趋势延续，已完成{structure.bi_count}笔",
                    confidence=0.6,
                    raw_data={"bi_count": structure.bi_count}
                ))
        
        return signals
    
    # ============ 报告生成 ============
    
    def generate_report(self, signals: List[ChanlunSignal] = None) -> str:
        """生成缠论分析报告（Markdown格式）"""
        if signals is None:
            signals = self.scan_signals()
        
        report = []
        report.append(f"# 缠论信号扫描报告")
        report.append(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if not signals:
            report.append("✅ 当前无明显缠论信号")
            return "\n".join(report)
        
        # 按信号类型分组
        signal_groups = {}
        for sig in signals:
            if sig.signal_type not in signal_groups:
                signal_groups[sig.signal_type] = []
            signal_groups[sig.signal_type].append(sig)
        
        # 信号类型映射
        type_emoji = {
            "divergence_top": "🔴",
            "divergence_bottom": "🟢",
            "zs_range": "🟡",
            "trend_up": "📈",
            "trend_down": "📉"
        }
        
        type_name = {
            "divergence_top": "顶背驰",
            "divergence_bottom": "底背驰",
            "zs_range": "中枢震荡",
            "trend_up": "上涨趋势",
            "trend_down": "下跌趋势"
        }
        
        for sig_type, sig_list in signal_groups.items():
            emoji = type_emoji.get(sig_type, "⚡")
            name = type_name.get(sig_type, sig_type)
            
            report.append(f"## {emoji} {name}信号")
            report.append("")
            
            for sig in sig_list:
                report.append(f"- **{sig.symbol}** ({sig.market}) - {sig.freq}")
                report.append(f"  - 方向: {sig.direction}")
                report.append(f"  - 置信度: {sig.confidence:.0%}")
                report.append(f"  - 描述: {sig.description}")
                report.append("")
        
        report.append("---")
        report.append("*以上为缠论技术分析信号，不构成投资建议。决策权在 Captain 手中。*")
        
        return "\n".join(report)


# ============ 命令行入口 ============

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="缠论数据感知系统")
    parser.add_argument("--scan", action="store_true", help="扫描所有关注品种")
    parser.add_argument("--symbol", type=str, help="分析指定品种")
    parser.add_argument("--market", type=str, default="US", help="市场 (US/HK/SH/SZ/CC)")
    parser.add_argument("--report", action="store_true", help="生成报告")
    
    args = parser.parse_args()
    
    # 初始化
    perception = ChanlunPerception()
    
    if args.scan:
        print("🔍 扫描中...")
        signals = perception.scan_signals()
        report = perception.generate_report(signals)
        print(report)
    
    elif args.symbol:
        print(f"📊 分析 {args.symbol} ({args.market})...")
        structures = perception.analyze_symbol(args.symbol, args.market)
        
        for freq, structure in structures.items():
            print(f"\n【{freq}】")
            print(f"  趋势: {structure.trend}")
            print(f"  笔数量: {structure.bi_count}")
            print(f"  中枢数量: {structure.zs_count}")
            print(f"  最后一笔: {structure.last_bi_direction}")
            if structure.last_zs_range:
                print(f"  中枢区间: [{structure.last_zs_range[0]:.2f}, {structure.last_zs_range[1]:.2f}]")
            print(f"  背驰: {'是' if structure.divergence else '否'}")
    
    elif args.report:
        signals = perception.scan_signals()
        report = perception.generate_report(signals)
        
        # 保存报告
        report_path = f"/workspace/projects/workspace/chanlun-agent/reports/{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"报告已保存: {report_path}")
    
    else:
        parser.print_help()
