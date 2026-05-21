#!/usr/bin/env python3
"""
港A标的交易价值分析 - 找出最具交易价值的标的
"""

import sys
import logging
sys.path.insert(0, '/workspace/projects/workspace/chanlun-agent')
sys.path.insert(0, '/workspace/projects/workspace/chanlun-agent/paper-trading')

from czsc import CZSC, Freq, format_standard_kline
from czsc_extension import CzscExtension
import pandas as pd
from datetime import datetime
from pathlib import Path

# Tiger SDK
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import Language

# 密钥配置
TIGER_ID = "20159412"
TIGER_PRIVATE_KEY = """MIICXAIBAAKBgQCQsk07H1czwJy5Gfm9GH2iahHEX3Hhej6y8FW7Hvd9X9jTqxoxFi45aMPFXU7nAx9Ki/gYQlYeXjpCu5RMUHboaz29iBlXmq0gFd6/CdB1LEPbua5V5/kUP53ETbKo0RFjm+fWHxYE6QMpMyW6amP2ASyygSs23aAxYnLZboq5vwIDAQABAoGAXr0/r/w/PlVYyCFn0RXd/J9ybp8Hk1hVARg3KcOGzAIbl8up5IXfUht0Qx9q7/qtXEP09v1IIa4Ue2kSGj18/IhEDla3+EMs24pQ9xnRPgwnzsQkfwNTerGwnxvrM+iHl/IH0AKL0kBPs56JsIIP5VZMd3xNK4xiVTzZIRcRVRECQQDGdrrM6qkomFPw8YRjIO7DuM1IG7ec2PVHX/zYMgCkfYBCsz+DjsopKLjEGms3IqHlSwzB5GLq/z1iHBf8IM/tAkEAuqUn91dmOgSsUJIbuAVN/FtoGcIKe0SYybX3BDsPE6295XR70XMhnrTjx0wIsiANzgC1JZC8PdxB1pxUyx0C2wJBALeao9prxa8OramcZlOm5f0f/JoXOljaxqAPh0UjjUCf8obCeaHl+dT2HWke382UNp6APf8qoPCyzUD0qKPSX0kCQE7WJ/V/wzxKcQZvUKoAA5rOeUA4B/ldVjQNWlM9Jvcm8gkTlKE5wj+pJHUwFpQ2md4jymAdrIVsnZqq2d4ZWPUCQFesxYFPfPv2xnonihe7zqsFAz0pD3E5Ks/F3sdUZk4s/A9Zf1rzxS2XsQtqHgl08L0u340m+YbtTlz/Lyq0mLI=="""
SIM_ACCOUNT = "21409378833585169"

class TigerClient:
    """Tiger API 客户端"""
    
    def __init__(self, account: str = SIM_ACCOUNT):
        self.account = account
        self.config = TigerOpenClientConfig(sandbox_debug=False)
        self.config.tiger_id = TIGER_ID
        self.config.private_key = TIGER_PRIVATE_KEY
        self.config.language = Language.zh_CN
        self.config.account = account
        
        self.quote_client = QuoteClient(self.config)
        print(f"✅ Tiger客户端初始化成功")
    
    def get_daily_bars(self, symbol: str, limit: int = 30):
        """获取日线数据"""
        try:
            bars = self.quote_client.get_bars([symbol], period="day", limit=limit)
            if bars is not None and not bars.empty:
                return bars
            return None
        except Exception as e:
            print(f"获取日线失败: {e}")
            return None


def analyze_symbol(client, symbol, name):
    """分析单个标的"""
    try:
        # 获取日线数据
        df_daily = client.get_daily_bars(symbol, limit=100)
        if df_daily is None or len(df_daily) < 50:
            return None
        
        current_price = float(df_daily.iloc[-1]['close'])
        
        # 转换为czsc格式
        df_daily = df_daily.rename(columns={
            'time': 'dt', 'open': 'open', 'high': 'high', 
            'low': 'low', 'close': 'close', 'volume': 'vol'
        })
        df_daily['dt'] = pd.to_datetime(df_daily['dt'])
        df_daily['symbol'] = symbol
        df_daily['amount'] = df_daily['vol'] * df_daily['close']
        df_daily = df_daily.sort_values('dt')
        
        bars_daily = format_standard_kline(df_daily, Freq.D)
        ka_daily = CZSC(bars_daily, max_bi_num=1000)
        ext_daily = CzscExtension(ka_daily)
        
        # 获取关键指标
        bi_list = ext_daily.bi_list
        zs_list = ext_daily.calc_zs_list()
        trend = ext_daily.judge_trend()
        divergence = ext_daily.detect_divergence()
        
        # 计算评分要素
        bi_count = len(bi_list)
        zs_count = len(zs_list)
        
        # 趋势评分 (up=3, neutral=1, down=0)
        trend_score = 3 if trend == 'up' else 1 if trend == 'neutral' else 0
        
        # 结构评分
        structure_score = min(bi_count / 10, 3) + min(zs_count * 0.5, 2)
        
        # 背驰评分
        divergence_score = 2 if divergence.get('divergence') else 0
        
        # 位置评分 (越低越好)
        if len(df_daily) > 20:
            high_20 = df_daily['high'].tail(20).max()
            low_20 = df_daily['low'].tail(20).min()
            if high_20 > low_20:
                position_pct = (current_price - low_20) / (high_20 - low_20)
                position_score = (1 - position_pct) * 2
            else:
                position_score = 1
        else:
            position_score = 0
        
        # 总分
        total_score = trend_score + structure_score + divergence_score + position_score
        
        return {
            'symbol': symbol,
            'name': name,
            'price': current_price,
            'trend': trend,
            'bi_count': bi_count,
            'zs_count': zs_count,
            'divergence': divergence.get('divergence', False),
            'trend_score': trend_score,
            'structure_score': structure_score,
            'divergence_score': divergence_score,
            'position_score': position_score,
            'total_score': total_score
        }
        
    except Exception as e:
        print(f"   ❌ 分析失败: {e}")
        return None


def main():
    # 所有监控标的
    symbols = {
        '00700': '腾讯控股',
        '03690': '美团',
        '01810': '小米',
        '09999': '网易',
    }
    
    # A股ETF暂不分析(因T+1限制)
    a_etf = {
        '510050': '上证50ETF',
        '510300': '沪深300ETF', 
        '159915': '创业板ETF'
    }
    
    print("="*70)
    print("🎯 港A标的交易价值分析")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("⚠️  注意: A股ETF为T+1品种，暂不参与评选")
    print()
    
    client = TigerClient()
    results = []
    
    print("📊 分析港股标的...")
    for symbol, name in symbols.items():
        print(f"\n  {symbol} ({name})...")
        result = analyze_symbol(client, symbol, name)
        if result:
            results.append(result)
            div_status = "✓有背驰" if result['divergence'] else "✗无背驰"
            print(f"     价格: {result['price']:.2f} | 趋势: {result['trend']} | 评分: {result['total_score']:.1f}")
            print(f"     笔/中枢: {result['bi_count']}/{result['zs_count']} | 背驰: {div_status}")
    
    # 排序并输出结果
    print("\n" + "="*70)
    print("📈 交易价值排名")
    print("="*70)
    
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    for i, r in enumerate(results, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"{emoji} #{i} {r['symbol']} ({r['name']})")
        print(f"      价格: {r['price']:.2f} | 趋势: {r['trend']} | 综合评分: {r['total_score']:.1f}/10")
        print(f"      评分明细: 趋势{r['trend_score']:.0f} + 结构{r['structure_score']:.1f} + 背驰{r['divergence_score']:.0f} + 位置{r['position_score']:.1f}")
        print()
    
    if results:
        best = results[0]
        print("="*70)
        print(f"🏆 当前最具交易价值标的: {best['symbol']} ({best['name']})")
        print(f"   现价: {best['price']:.2f}")
        print(f"   趋势: {best['trend']}")
        print(f"   缠论结构: {best['bi_count']}笔 {best['zs_count']}中枢")
        print(f"   背驰状态: {'有背驰信号' if best['divergence'] else '暂无背驰'}")
        print(f"   综合评分: {best['total_score']:.1f}/10")
        print("="*70)
        print()
        print("💡 建议:")
        if best['trend'] == 'down':
            print("   该标的日线趋势向下，建议等待一买或二买信号出现后再介入")
        elif best['trend'] == 'neutral':
            print("   该标的处于盘整状态，建议等待方向明朗")
        else:
            print("   该标的日线趋势向上，可关注回调买点机会")
    
    return results


if __name__ == "__main__":
    main()
