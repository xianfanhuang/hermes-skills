#!/usr/bin/env python3
"""
SQLite 持久化存储
ChanlunAgent MVP - 核心基础设施

功能：
1. Token/配置持久化（飞书Token、API Key等）
2. 交易记录存储
3. 信号日志
4. 反思记录

Author: Trading Assistant
Version: 1.0.0
"""

import sqlite3
import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger("TokenStore")


@dataclass
class TradeRecord:
    """交易记录"""
    trade_id: str
    symbol: str
    direction: str  # long/short
    entry_price: float
    exit_price: Optional[float] = None
    quantity: int = 0
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    signal_type: str = ""
    czsc_structure: str = ""
    reflection: str = ""
    status: str = "open"  # open/closed/cancelled


@dataclass
class SignalLog:
    """信号日志"""
    signal_id: str
    symbol: str
    market: str
    freq: str
    signal_type: str
    direction: str
    price: float
    confidence: float = 0.0
    description: str = ""
    created_at: Optional[str] = None


class TokenStore:
    """SQLite 持久化存储"""

    def __init__(self, db_path: str = "./data/chanlun.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._cache: Dict[str, str] = {}
        self._init_db()
        logger.info(f"TokenStore initialized: {db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            # Token/配置表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 交易记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity INTEGER DEFAULT 0,
                    pnl REAL,
                    pnl_pct REAL,
                    entry_time TIMESTAMP,
                    exit_time TIMESTAMP,
                    signal_type TEXT DEFAULT '',
                    czsc_structure TEXT DEFAULT '',
                    reflection TEXT DEFAULT '',
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 信号日志表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT UNIQUE,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    freq TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    price REAL NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 反思记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT,
                    reflection_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metrics TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (trade_id) REFERENCES trades(trade_id)
                )
            """)

            # 索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at)")

            conn.commit()
            logger.info("Database tables initialized")

    # ============ Token 操作 ============

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取Token/配置值"""
        if key in self._cache:
            return self._cache[key]
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT value FROM tokens WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                self._cache[key] = row['value']
                return row['value']
        return default

    def set(self, key: str, value: str):
        """设置Token/配置值"""
        self._cache[key] = value
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tokens (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, datetime.now().isoformat())
            )
            conn.commit()

    def delete(self, key: str):
        """删除Token/配置值"""
        self._cache.pop(key, None)
        with self._get_conn() as conn:
            conn.execute("DELETE FROM tokens WHERE key = ?", (key,))
            conn.commit()

    def keys(self, prefix: str = "") -> List[str]:
        """列出所有键（可选前缀过滤）"""
        with self._get_conn() as conn:
            if prefix:
                cursor = conn.execute("SELECT key FROM tokens WHERE key LIKE ?", (f"{prefix}%",))
            else:
                cursor = conn.execute("SELECT key FROM tokens")
            return [row['key'] for row in cursor.fetchall()]

    # ============ 交易记录操作 ============

    def log_trade(self, trade: TradeRecord) -> bool:
        """记录交易"""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO trades 
                    (trade_id, symbol, direction, entry_price, exit_price, quantity,
                     pnl, pnl_pct, entry_time, exit_time, signal_type, czsc_structure,
                     reflection, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade.trade_id, trade.symbol, trade.direction,
                    trade.entry_price, trade.exit_price, trade.quantity,
                    trade.pnl, trade.pnl_pct, trade.entry_time, trade.exit_time,
                    trade.signal_type, trade.czsc_structure, trade.reflection,
                    trade.status, datetime.now().isoformat()
                ))
                conn.commit()
                logger.info(f"Trade logged: {trade.trade_id} {trade.symbol} {trade.direction}")
                return True
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
            return False

    def update_trade(self, trade_id: str, **kwargs) -> bool:
        """更新交易记录"""
        try:
            allowed = {'exit_price', 'pnl', 'pnl_pct', 'exit_time', 'reflection', 'status'}
            updates = {k: v for k, v in kwargs.items() if k in allowed}
            if not updates:
                return False
            updates['updated_at'] = datetime.now().isoformat()
            
            set_clause = ', '.join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [trade_id]
            
            with self._get_conn() as conn:
                conn.execute(
                    f"UPDATE trades SET {set_clause} WHERE trade_id = ?",
                    values
                )
                conn.commit()
                logger.info(f"Trade updated: {trade_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update trade: {e}")
            return False

    def get_trades(self, symbol: Optional[str] = None, status: Optional[str] = None,
                   limit: int = 50) -> List[Dict]:
        """查询交易记录"""
        conditions = []
        params = []
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        with self._get_conn() as conn:
            cursor = conn.execute(
                f"SELECT * FROM trades {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit]
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_open_trades(self, symbol: Optional[str] = None) -> List[Dict]:
        """获取未平仓交易"""
        return self.get_trades(symbol=symbol, status='open')

    def get_trade_stats(self, symbol: Optional[str] = None) -> Dict:
        """获取交易统计"""
        conditions = ["status = 'closed'"]
        params = []
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        
        where = f"WHERE {' AND '.join(conditions)}"
        
        with self._get_conn() as conn:
            cursor = conn.execute(f"""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl_pct) as avg_pnl_pct,
                    MAX(pnl) as best_trade,
                    MIN(pnl) as worst_trade,
                    SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as gross_profit,
                    SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END) as gross_loss
                FROM trades {where}
            """, params)
            row = cursor.fetchone()
            if row:
                stats = dict(row)
                total = stats['total_trades'] or 0
                wins = stats['winning_trades'] or 0
                stats['win_rate'] = (wins / total * 100) if total > 0 else 0
                gross_profit = stats['gross_profit'] or 0
                gross_loss = stats['gross_loss'] or 1
                stats['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else 0
                return stats
            return {}

    # ============ 信号日志操作 ============

    def log_signal(self, signal: SignalLog) -> bool:
        """记录信号"""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO signals 
                    (signal_id, symbol, market, freq, signal_type, direction,
                     price, confidence, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    signal.signal_id, signal.symbol, signal.market, signal.freq,
                    signal.signal_type, signal.direction, signal.price,
                    signal.confidence, signal.description,
                    signal.created_at or datetime.now().isoformat()
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to log signal: {e}")
            return False

    def get_signals(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """查询信号日志"""
        conditions = []
        params = []
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        with self._get_conn() as conn:
            cursor = conn.execute(
                f"SELECT * FROM signals {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit]
            )
            return [dict(row) for row in cursor.fetchall()]

    # ============ 反思记录操作 ============

    def log_reflection(self, trade_id: str, reflection_type: str, 
                       content: str, metrics: Dict = None) -> bool:
        """记录反思"""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO reflections (trade_id, reflection_type, content, metrics)
                    VALUES (?, ?, ?, ?)
                """, (trade_id, reflection_type, content, json.dumps(metrics or {})))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to log reflection: {e}")
            return False

    def get_reflections(self, trade_id: Optional[str] = None, 
                        limit: int = 50) -> List[Dict]:
        """查询反思记录"""
        conditions = []
        params = []
        if trade_id:
            conditions.append("trade_id = ?")
            params.append(trade_id)
        
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        with self._get_conn() as conn:
            cursor = conn.execute(
                f"SELECT * FROM reflections {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit]
            )
            return [dict(row) for row in cursor.fetchall()]

    # ============ 工具方法 ============

    def get_db_stats(self) -> Dict:
        """获取数据库统计"""
        with self._get_conn() as conn:
            stats = {}
            for table in ['tokens', 'trades', 'signals', 'reflections']:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            return stats

    def vacuum(self):
        """压缩数据库"""
        with self._get_conn() as conn:
            conn.execute("VACUUM")
            logger.info("Database vacuumed")


# ============ 测试 ============

if __name__ == "__main__":
    import tempfile
    
    # 使用临时数据库测试
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db = f.name
    
    store = TokenStore(test_db)
    
    # 测试 Token 操作
    store.set("test_key", "test_value")
    assert store.get("test_key") == "test_value"
    print("✅ Token get/set OK")
    
    # 测试交易记录
    trade = TradeRecord(
        trade_id="T001",
        symbol="CRCL",
        direction="long",
        entry_price=110.0,
        quantity=100,
        entry_time=datetime.now().isoformat(),
        signal_type="bi_buy"
    )
    store.log_trade(trade)
    trades = store.get_trades(symbol="CRCL")
    assert len(trades) == 1
    assert trades[0]['symbol'] == "CRCL"
    print("✅ Trade logging OK")
    
    # 测试更新交易
    store.update_trade("T001", exit_price=115.0, pnl=500, pnl_pct=4.55, status="closed")
    stats = store.get_trade_stats()
    assert stats['total_trades'] == 1
    assert stats['winning_trades'] == 1
    print("✅ Trade update & stats OK")
    
    # 测试信号日志
    signal = SignalLog(
        signal_id="S001",
        symbol="CRCL",
        market="US",
        freq="日线",
        signal_type="divergence_bottom",
        direction="up",
        price=110.0,
        confidence=0.75
    )
    store.log_signal(signal)
    signals = store.get_signals(symbol="CRCL")
    assert len(signals) == 1
    print("✅ Signal logging OK")
    
    # 测试反思记录
    store.log_reflection("T001", "post_trade", "测试反思内容", {"accuracy": 0.8})
    reflections = store.get_reflections(trade_id="T001")
    assert len(reflections) == 1
    print("✅ Reflection logging OK")
    
    # 统计
    db_stats = store.get_db_stats()
    print(f"✅ DB stats: {db_stats}")
    
    # 清理
    os.unlink(test_db)
    print("\n🎉 All tests passed!")
