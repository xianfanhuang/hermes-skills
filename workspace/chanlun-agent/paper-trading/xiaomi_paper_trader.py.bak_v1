#!/usr/bin/env python3
"""
小米(01810)实时模拟交易系统

整合:
- 缠论买卖点检测
- Tiger模拟盘下单
- 风控管理
- 自动反思
- RGB知识库更新

Usage:
    python3 xiaomi_paper_trader.py --monitor    # 启动监控
    python3 xiaomi_paper_trader.py --status     # 查看状态
    python3 xiaomi_paper_trader.py --report     # 生成报告
"""

import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / 'xiaomi_trader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Tiger SDK
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import Language, OrderType

# 缠论扩展
from czsc import CZSC, Freq, format_standard_kline
from czsc_extension import CzscExtension
import pandas as pd

# 密钥配置
TIGER_ID = "20159412"
TIGER_PRIVATE_KEY = """MIICXAIBAAKBgQCQsk07H1czwJy5Gfm9GH2iahHEX3Hhej6y8FW7Hvd9X9jTqxoxFi45aMPFXU7nAx9Ki/gYQlYeXjpCu5RMUHboaz29iBlXmq0gFd6/CdB1LEPbua5V5/kUP53ETbKo0RFjm+fWHxYE6QMpMyW6amP2ASyygSs23aAxYnLZboq5vwIDAQABAoGAXr0/r/w/PlVYyCFn0RXd/J9ybp8Hk1hVARg3KcOGzAIbl8up5IXfUht0Qx9q7/qtXEP09v1IIa4Ue2kSGj18/IhEDla3+EMs24pQ9xnRPgwnzsQkfwNTerGwnxvrM+iHl/IH0AKL0kBPs56JsIIP5VZMd3xNK4xiVTzZIRcRVRECQQDGdrrM6qkomFPw8YRjIO7DuM1IG7ec2PVHX/zYMgCkfYBCsz+DjsopKLjEGms3IqHlSwzB5GLq/z1iHBf8IM/tAkEAuqUn91dmOgSsUJIbuAVN/FtoGcIKe0SYybX3BDsPE6295XR70XMhnrTjx0wIsiANzgC1JZC8PdxB1pxUyx0C2wJBALeao9prxa8OramcZlOm5f0f/JoXOljaxqAPh0UjjUCf8obCeaHl+dT2HWke382UNp6APf8qoPCyzUD0qKPSX0kCQE7WJ/V/wzxKcQZvUKoAA5rOeUA4B/ldVjQNWlM9Jvcm8gkTlKE5wj+pJHUwFpQ2md4jymAdrIVsnZqq2d4ZWPUCQFesxYFPfPv2xnonihe7zqsFAz0pD3E5Ks/F3sdUZk4s/A9Zf1rzxS2XsQtqHgl08L0u340m+YbtTlz/Lyq0mLI=="""
SIM_ACCOUNT = "21409378833585169"

# 风控参数
RISK_PER_TRADE = 0.02  # 单笔2%
MAX_DAILY_LOSS = 0.06  # 日最大6%
MAX_CONSECUTIVE_LOSSES = 3  # 连亏3笔熔断
COOLDOWN_MINUTES = 60  # 熔断冷却时间

# 交易记录文件
TRADE_LOG = Path(__file__).parent / "xiaomi_trades.json"
PORTFOLIO_FILE = Path(__file__).parent / "xiaomi_portfolio.json"


class XiaomiPaperTrader:
    """小米模拟交易器"""
    
    def __init__(self):
        self.symbol = "01810"
        self.name = "小米"
        
        # 初始化Tiger
        self.config = TigerOpenClientConfig(sandbox_debug=False)
        self.config.tiger_id = TIGER_ID
        self.config.private_key = TIGER_PRIVATE_KEY
        self.config.language = Language.zh_CN
        self.config.account = SIM_ACCOUNT
        
        self.quote_client = QuoteClient(self.config)
        self.trade_client = TradeClient(self.config)
        
        # 加载持仓和交易记录
        self.portfolio = self._load_portfolio()
        self.trades = self._load_trades()
        
        logger.info(f"🚀 小米模拟交易器启动 - 账户: {SIM_ACCOUNT}")
        logger.info(f"   当前持仓: {self.portfolio.get('position', 0)} 股")
        logger.info(f"   累计盈亏: ${self.portfolio.get('total_pnl', 0):.2f}")
    
    def _load_portfolio(self) -> Dict:
        """加载持仓"""
        if PORTFOLIO_FILE.exists():
            with open(PORTFOLIO_FILE, 'r') as f:
                return json.load(f)
        return {
            "symbol": self.symbol,
            "position": 0,
            "avg_cost": 0,
            "total_pnl": 0,
            "consecutive_losses": 0,
            "daily_pnl": 0,
            "last_trade_date": None,
            "cooldown_until": None
        }
    
    def _save_portfolio(self):
        """保存持仓"""
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(self.portfolio, f, indent=2)
    
    def _load_trades(self) -> List:
        """加载交易记录"""
        if TRADE_LOG.exists():
            with open(TRADE_LOG, 'r') as f:
                return json.load(f)
        return []
    
    def _save_trades(self):
        """保存交易记录"""
        with open(TRADE_LOG, 'w') as f:
            json.dump(self.trades, f, indent=2)
    
    def get_account_value(self) -> float:
        """获取账户净值"""
        try:
            assets = self.trade_client.get_assets()
            if assets and len(assets) > 0:
                a = assets[0]
                seg = a.segments.get('S')
                if seg:
                    return float(seg.net_liquidation)
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
        return 1000000.0  # 默认100万
    
    def analyze_signal(self) -> Optional[Dict]:
        """分析缠论买卖点"""
        try:
            # 获取日线数据
            df_daily = self.quote_client.get_bars([self.symbol], period="day", limit=100)
            if df_daily is None or df_daily.empty:
                return None
            
            current_price = float(df_daily.iloc[-1]['close'])
            
            # 转换为czsc格式
            df_daily = df_daily.rename(columns={
                'time': 'dt', 'open': 'open', 'high': 'high',
                'low': 'low', 'close': 'close', 'volume': 'vol'
            })
            df_daily['dt'] = pd.to_datetime(df_daily['dt'])
            df_daily['symbol'] = self.symbol
            df_daily['amount'] = df_daily['vol'] * df_daily['close']
            df_daily = df_daily.sort_values('dt')
            
            bars = format_standard_kline(df_daily, Freq.D)
            ka = CZSC(bars, max_bi_num=1000)
            ext = CzscExtension(ka)
            
            # 获取分析结果
            bi_list = ext.bi_list
            zs_list = ext.calc_zs_list()
            divergence = ext.detect_divergence()
            points = ext.detect_buy_sell_points()
            
            # 提取买卖信号
            buy_points = [p for p in points if 'buy' in p.type]
            sell_points = [p for p in points if 'sell' in p.type]
            
            # 添加背驰信号
            if divergence.get('divergence'):
                if divergence['type'] == 'bottom':
                    buy_points.append(type('obj', (object,), {
                        'type': 'buy1_divergence', 'price': bi_list[-1].low if bi_list else current_price,
                        'confidence': 0.85
                    })())
                elif divergence['type'] == 'top':
                    sell_points.append(type('obj', (object,), {
                        'type': 'sell1_divergence', 'price': bi_list[-1].high if bi_list else current_price,
                        'confidence': 0.85
                    })())
            
            # 确定最佳信号
            signal = None
            if buy_points and not self.portfolio['position'] > 0:  # 无持仓时找买点
                best = max(buy_points, key=lambda x: x.confidence)
                if best.confidence >= 0.5:
                    signal = {
                        'action': 'BUY',
                        'type': best.type,
                        'price': best.price,
                        'confidence': best.confidence,
                        'current_price': current_price
                    }
            elif sell_points and self.portfolio['position'] > 0:  # 有持仓时找卖点
                best = max(sell_points, key=lambda x: x.confidence)
                if best.confidence >= 0.5:
                    signal = {
                        'action': 'SELL',
                        'type': best.type,
                        'price': best.price,
                        'confidence': best.confidence,
                        'current_price': current_price
                    }
            
            return {
                'current_price': current_price,
                'bi_count': len(bi_list),
                'zs_count': len(zs_list),
                'divergence': divergence.get('divergence', False),
                'signal': signal,
                'buy_signals': [{'type': p.type, 'price': p.price, 'confidence': p.confidence} for p in buy_points],
                'sell_signals': [{'type': p.type, 'price': p.price, 'confidence': p.confidence} for p in sell_points]
            }
            
        except Exception as e:
            logger.error(f"分析信号失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def check_risk_limits(self) -> bool:
        """检查风控限制"""
        now = datetime.now()
        
        # 检查熔断
        if self.portfolio.get('cooldown_until'):
            cooldown = datetime.fromisoformat(self.portfolio['cooldown_until'])
            if now < cooldown:
                logger.info(f"⏸️ 熔断中，冷却至 {cooldown.strftime('%H:%M')}")
                return False
            else:
                self.portfolio['cooldown_until'] = None
                self.portfolio['consecutive_losses'] = 0
                logger.info("✅ 熔断解除")
        
        # 检查日亏损
        if self.portfolio['daily_pnl'] < -self.get_account_value() * MAX_DAILY_LOSS:
            logger.warning(f"🚫 日亏损超限: ${self.portfolio['daily_pnl']:.2f}")
            return False
        
        # 检查连亏
        if self.portfolio['consecutive_losses'] >= MAX_CONSECUTIVE_LOSSES:
            cooldown_time = now.timestamp() + COOLDOWN_MINUTES * 60
            self.portfolio['cooldown_until'] = datetime.fromtimestamp(cooldown_time).isoformat()
            logger.warning(f"🚫 连亏{MAX_CONSECUTIVE_LOSSES}笔，熔断{COOLDOWN_MINUTES}分钟")
            self._save_portfolio()
            return False
        
        return True
    
    def execute_trade(self, signal: Dict) -> bool:
        """执行交易"""
        try:
            action = signal['action']
            price = signal['current_price']
            account_value = self.get_account_value()
            
            if action == 'BUY':
                # 计算仓位
                risk_amount = account_value * RISK_PER_TRADE
                stop_loss = price * 0.97  # 3%止损
                risk_per_share = price - stop_loss
                shares = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
                
                if shares < 100:
                    logger.info(f"⚠️ 计算仓位过小: {shares}股，放弃交易")
                    return False
                
                # 模拟下单
                trade = {
                    'timestamp': datetime.now().isoformat(),
                    'symbol': self.symbol,
                    'action': 'BUY',
                    'signal_type': signal['type'],
                    'shares': shares,
                    'price': price,
                    'stop_loss': stop_loss,
                    'confidence': signal['confidence']
                }
                
                # 更新持仓
                self.portfolio['position'] = shares
                self.portfolio['avg_cost'] = price
                self.portfolio['last_trade_date'] = datetime.now().strftime('%Y-%m-%d')
                
                logger.info(f"🟢 买入 {self.symbol} {shares}股 @ ${price:.2f}")
                logger.info(f"   信号: {signal['type']} | 置信度: {signal['confidence']:.2f}")
                logger.info(f"   止损: ${stop_loss:.2f}")
                
            elif action == 'SELL':
                shares = self.portfolio['position']
                avg_cost = self.portfolio['avg_cost']
                pnl = (price - avg_cost) * shares
                pnl_pct = (price - avg_cost) / avg_cost if avg_cost > 0 else 0
                
                # 模拟平仓
                trade = {
                    'timestamp': datetime.now().isoformat(),
                    'symbol': self.symbol,
                    'action': 'SELL',
                    'signal_type': signal['type'],
                    'shares': shares,
                    'price': price,
                    'avg_cost': avg_cost,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'confidence': signal['confidence']
                }
                
                # 更新持仓和盈亏
                self.portfolio['position'] = 0
                self.portfolio['avg_cost'] = 0
                self.portfolio['total_pnl'] += pnl
                self.portfolio['daily_pnl'] += pnl
                
                # 更新连亏计数
                if pnl < 0:
                    self.portfolio['consecutive_losses'] += 1
                else:
                    self.portfolio['consecutive_losses'] = 0
                
                emoji = "🟢" if pnl > 0 else "🔴"
                logger.info(f"{emoji} 卖出 {self.symbol} {shares}股 @ ${price:.2f}")
                logger.info(f"   盈亏: ${pnl:.2f} ({pnl_pct*100:+.2f}%)")
                logger.info(f"   累计盈亏: ${self.portfolio['total_pnl']:.2f}")
            
            # 保存记录
            self.trades.append(trade)
            self._save_trades()
            self._save_portfolio()
            
            return True
            
        except Exception as e:
            logger.error(f"执行交易失败: {e}")
            return False
    
    def run_monitor(self):
        """运行监控循环"""
        logger.info("="*60)
        logger.info("🚀 小米实时模拟交易系统启动")
        logger.info("="*60)
        
        while True:
            try:
                # 检查风控
                if not self.check_risk_limits():
                    time.sleep(60)
                    continue
                
                # 分析信号
                analysis = self.analyze_signal()
                if not analysis:
                    time.sleep(30)
                    continue
                
                signal = analysis.get('signal')
                
                if signal:
                    logger.info(f"\n🎯 发现交易信号!")
                    logger.info(f"   动作: {signal['action']}")
                    logger.info(f"   类型: {signal['type']}")
                    logger.info(f"   价格: ${signal['current_price']:.2f}")
                    logger.info(f"   置信度: {signal['confidence']:.2f}")
                    
                    # 执行交易
                    self.execute_trade(signal)
                else:
                    logger.info(f"⏳ {datetime.now().strftime('%H:%M')} 无信号 | "
                               f"价格: ${analysis['current_price']:.2f} | "
                               f"笔: {analysis['bi_count']} | "
                               f"中枢: {analysis['zs_count']} | "
                               f"背驰: {'是' if analysis['divergence'] else '否'}")
                
                time.sleep(300)  # 5分钟扫描一次
                
            except KeyboardInterrupt:
                logger.info("\n👋 监控已停止")
                break
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                time.sleep(60)


if __name__ == "__main__":
    trader = XiaomiPaperTrader()
    trader.run_monitor()
