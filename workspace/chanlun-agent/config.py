#!/usr/bin/env python3
"""
配置中心
ChanlunAgent MVP - 所有参数外部化

Author: Trading Assistant
Version: 1.0.0
"""

import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger("Config")


@dataclass
class SymbolConfig:
    """品种配置"""
    symbol: str = "CRCL"
    asset_type: str = "stock"  # stock/crypto/futures/forex
    market: str = "US"
    primary_timeframe: str = "30M"
    secondary_timeframes: List[str] = field(default_factory=lambda: ["5M", "1H", "4H"])
    min_volume_ratio: float = 1.0
    enable_second_buy: bool = True
    enable_shock_buy: bool = True
    max_position_pct: float = 0.5
    max_loss_per_trade: float = 0.03
    max_daily_loss: float = 0.08
    time_stop_bars: int = 8
    trend_timeframe: str = "1D"
    structure_timeframe: str = "1H"
    entry_timeframe: str = "5M"


@dataclass
class FeishuConfig:
    """飞书配置"""
    app_id: str = ""
    app_secret: str = ""
    chat_id: str = ""
    kb_root_token: str = ""
    kb_rule_folder_token: str = ""
    kb_guide_folder_token: str = ""
    kb_practice_folder_token: str = ""

    def __post_init__(self):
        if not self.app_id:
            self.app_id = os.getenv("FEISHU_APP_ID", "")
        if not self.app_secret:
            self.app_secret = os.getenv("FEISHU_APP_SECRET", "")
        if not self.chat_id:
            self.chat_id = os.getenv("FEISHU_CHAT_ID", "")


@dataclass
class RiskConfig:
    """风控配置"""
    # 技术止损
    technical_stop_enabled: bool = True
    technical_stop_pct: float = 0.03  # 3%
    
    # 时间止损
    time_stop_enabled: bool = True
    time_stop_bars: int = 8
    time_stop_reduce_pct: float = 0.5  # 减仓50%
    
    # 中枢止损
    zs_stop_enabled: bool = True
    
    # 资金止损
    capital_stop_enabled: bool = True
    max_loss_per_trade: float = 0.03  # 单笔最大亏损3%
    max_daily_loss: float = 0.08  # 日最大亏损8%
    
    # 连续亏损熔断
    consecutive_loss_limit: int = 3
    halt_duration_minutes: int = 60


@dataclass
class AgentConfig:
    """Agent 总配置"""
    version: str = "1.0.0-MVP"
    mode: str = "paper"  # paper/live
    debug: bool = False
    
    # 子配置
    feishu: FeishuConfig = field(default_factory=FeishuConfig)
    symbol: SymbolConfig = field(default_factory=SymbolConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    
    # 路径
    db_path: str = "./data/chanlun.db"
    log_path: str = "./logs/chanlun.log"
    
    # 自进化
    daily_report_hour: int = 2
    daily_report_minute: int = 0
    auto_reflect: bool = True
    auto_optimize: bool = True
    
    # 飞书交互指令映射
    commands: dict = field(default_factory=lambda: {
        "持仓": "show_positions",
        "分析": "analyze_symbol",
        "信号": "show_signals",
        "平仓": "close_position",
        "反思": "generate_reflection",
        "日报": "daily_report",
        "优化": "optimize_params",
        "状态": "show_status",
        "帮助": "show_help",
    })

    @classmethod
    def from_file(cls, filepath: str) -> 'AgentConfig':
        """从JSON文件加载配置"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = cls()
        if 'feishu' in data:
            config.feishu = FeishuConfig(**data['feishu'])
        if 'symbol' in data:
            config.symbol = SymbolConfig(**data['symbol'])
        if 'risk' in data:
            config.risk = RiskConfig(**data['risk'])
        
        for key in ['version', 'mode', 'debug', 'db_path', 'log_path',
                     'daily_report_hour', 'daily_report_minute',
                     'auto_reflect', 'auto_optimize', 'commands']:
            if key in data:
                setattr(config, key, data[key])
        
        return config

    def to_file(self, filepath: str):
        """保存配置到JSON文件"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
        logger.info(f"Config saved to {filepath}")

    def load_secrets(self, secrets_path: str = None):
        """加载密钥配置"""
        if not secrets_path:
            secrets_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "SECRET.md"
            )
        
        if not os.path.exists(secrets_path):
            logger.warning(f"Secrets file not found: {secrets_path}")
            return {}
        
        secrets = {}
        with open(secrets_path, 'r') as f:
            for line in f:
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    key, _, value = line.partition(':')
                    key = key.strip().strip('`').strip('*').strip()
                    value = value.strip().strip('`').strip()
                    if key and value:
                        secrets[key] = value
        
        return secrets


# 默认配置文件路径
DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "config", "agent_config.json"
)


def load_config(filepath: str = None) -> AgentConfig:
    """加载配置（优先从文件，否则使用默认）"""
    filepath = filepath or DEFAULT_CONFIG_PATH
    if os.path.exists(filepath):
        return AgentConfig.from_file(filepath)
    else:
        config = AgentConfig()
        config.to_file(filepath)
        return config


if __name__ == "__main__":
    # 测试
    config = AgentConfig()
    print(f"Version: {config.version}")
    print(f"Mode: {config.mode}")
    print(f"Symbol: {config.symbol.symbol}")
    print(f"Commands: {list(config.commands.keys())}")
    
    # 测试保存/加载
    test_path = "/tmp/test_config.json"
    config.to_file(test_path)
    loaded = AgentConfig.from_file(test_path)
    assert loaded.version == config.version
    assert loaded.symbol.symbol == config.symbol.symbol
    print("✅ Config save/load OK")
    
    os.unlink(test_path)
    print("🎉 Config tests passed!")
