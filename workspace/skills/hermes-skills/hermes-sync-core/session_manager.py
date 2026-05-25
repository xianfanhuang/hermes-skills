#!/usr/bin/env python3
"""
Hermes Session Manager v2.0
完整实现原方案设计：自动分块、异常恢复、Token Budget联动

设计哲学：
- 分块防错乱：≥50条 或 ≥30分钟 自动切块
- 链式校验：prev/next 指针 + SHA256 checksum
- 异常恢复：active/completed 状态分离
- Token Budget联动：超阈值自动归档

用法:
  python3 session_manager.py start <platform> [context]
  python3 session_manager.py push <session_id> <message_json>     # 单条消息，自动分块
  python3 session_manager.py flush <session_id>                    # 手动刷新缓冲区
  python3 session_manager.py end <session_id> [summary] [keywords]
  python3 session_manager.py resume [last_n]                       # 恢复上一个会话
  python3 session_manager.py restore <session_id> [last_n]
  python3 session_manager.py verify <session_id>                   # 验证连续性
  python3 session_manager.py recover                               # 恢复未完成会话
  python3 session_manager.py list [date]
  python3 session_manager.py checkpoint                            # Token Budget检查点
"""

import os
import sys
import json
import hashlib
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

# ========== 配置 ==========
BASE_DIR = Path(__file__).parent / "sessions"
ACTIVE_DIR = BASE_DIR / "index" / "active"
COMPLETED_DIR = BASE_DIR / "index" / "completed"
RAW_DIR = BASE_DIR / "raw"
SUMMARY_DIR = BASE_DIR / "summaries"
LAST_SESSION_FILE = BASE_DIR / ".last_session_id"
BUFFER_FILE = BASE_DIR / ".message_buffer.json"

CHUNK_SIZE = 50           # 每50条消息一个chunk
FLUSH_INTERVAL = 1800     # 30分钟自动刷新（秒）
CHECKSUM_ALGO = "sha256"

# Token Budget 阈值
TOKEN_WARN_ROUNDS = 30    # 黄色预警轮次
TOKEN_STOP_ROUNDS = 50    # 红色熔断轮次


# ========== 工具函数 ==========

def ensure_dirs():
    """确保所有目录存在"""
    for d in [ACTIVE_DIR, COMPLETED_DIR, RAW_DIR, SUMMARY_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def calc_checksum(data: dict) -> str:
    """计算数据校验和"""
    content = json.dumps(data, sort_keys=True)
    return f"{CHECKSUM_ALGO}:{hashlib.sha256(content.encode()).hexdigest()[:16]}"


def now_iso() -> str:
    return datetime.now().isoformat()


def today_path() -> str:
    return datetime.now().strftime('%Y/%m/%d')


# ========== 缓冲区管理 ==========

class MessageBuffer:
    """
    消息缓冲区 - 实现自动分块
    
    原方案核心思想：
    - 消息先进缓冲区
    - 满足条件（≥50条 或 ≥30分钟）自动写入chunk
    - 支持手动flush
    """
    
    def __init__(self, session_id: str, platform: str):
        self.session_id = session_id
        self.platform = platform
        self.messages = []
        self.last_flush_time = time.time()
        self.chunk_num = self._load_chunk_num()
        self._timer = None
        self._start_auto_flush()
    
    def _buffer_path(self) -> Path:
        return BASE_DIR / f".buffer_{self.session_id}.json"
    
    def _load_chunk_num(self) -> int:
        """从已有的chunk中恢复chunk_num"""
        session = self._load_session()
        if session:
            return len(session.get("chunks", []))
        return 0
    
    def _load_session(self) -> dict:
        """加载活跃会话"""
        for status_dir in [ACTIVE_DIR, COMPLETED_DIR]:
            path = status_dir / f"{self.session_id}.json"
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        return None
    
    def _start_auto_flush(self):
        """启动定时自动刷新"""
        def _auto_flush():
            while True:
                time.sleep(FLUSH_INTERVAL)
                if self.messages:
                    elapsed = time.time() - self.last_flush_time
                    if elapsed >= FLUSH_INTERVAL:
                        self.flush("auto_timeout")
        
        self._timer = threading.Thread(target=_auto_flush, daemon=True)
        self._timer.start()
    
    def push(self, message: dict) -> dict:
        """
        推入一条消息
        
        Returns:
            {"buffered": True, "flushed": True/False, "chunk_id": ...}
        """
        self.messages.append(message)
        
        # 检查是否需要刷新
        if len(self.messages) >= CHUNK_SIZE:
            return self.flush("auto_size")
        
        # 保存缓冲区到磁盘（防崩溃）
        self._save_buffer()
        
        return {"buffered": True, "flushed": False, "buffer_size": len(self.messages)}
    
    def flush(self, reason: str = "manual") -> dict:
        """刷新缓冲区，写入chunk"""
        if not self.messages:
            return {"flushed": False, "reason": "empty"}
        
        self.chunk_num += 1
        chunk_id = f"{self.session_id}_{self.chunk_num:03d}"
        
        # 构建chunk
        chunk_data = {
            "chunk_id": chunk_id,
            "session_id": self.session_id,
            "platform": self.platform,
            "message_range": [self.messages[0].get("id", 1), self.messages[-1].get("id", len(self.messages))],
            "message_count": len(self.messages),
            "checksum": calc_checksum({"messages": self.messages}),
            "prev_chunk": f"{self.session_id}_{self.chunk_num-1:03d}" if self.chunk_num > 1 else None,
            "next_chunk": None,
            "status": "complete",
            "flush_reason": reason,
            "timestamp_start": self.messages[0].get("timestamp", now_iso()),
            "timestamp_end": self.messages[-1].get("timestamp", now_iso()),
            "messages": self.messages.copy()
        }
        
        # 更新前一个chunk的next指针
        self._update_prev_chunk_next(chunk_id)
        
        # 写入chunk文件
        chunk_dir = RAW_DIR / today_path()
        chunk_dir.mkdir(parents=True, exist_ok=True)
        chunk_path = chunk_dir / f"{chunk_id}.json"
        
        with open(chunk_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, indent=2, ensure_ascii=False)
        
        # 更新会话索引
        self._update_session_index(chunk_id, len(self.messages))
        
        # 清空缓冲区
        self.messages.clear()
        self.last_flush_time = time.time()
        self._clear_buffer()
        
        return {
            "flushed": True,
            "chunk_id": chunk_id,
            "message_count": chunk_data["message_count"],
            "reason": reason
        }
    
    def _update_prev_chunk_next(self, next_chunk_id: str):
        """更新前一个chunk的next指针"""
        if self.chunk_num <= 1:
            return
        
        prev_chunk_id = f"{self.session_id}_{self.chunk_num-1:03d}"
        for chunk_file in RAW_DIR.rglob(f"{prev_chunk_id}.json"):
            with open(chunk_file, 'r', encoding='utf-8') as f:
                prev_chunk = json.load(f)
            prev_chunk["next_chunk"] = next_chunk_id
            with open(chunk_file, 'w', encoding='utf-8') as f:
                json.dump(prev_chunk, f, indent=2, ensure_ascii=False)
            break
    
    def _update_session_index(self, chunk_id: str, msg_count: int):
        """更新活跃会话索引"""
        session_path = ACTIVE_DIR / f"{self.session_id}.json"
        if not session_path.exists():
            return
        
        with open(session_path, 'r', encoding='utf-8') as f:
            session = json.load(f)
        
        session["chunks"].append(chunk_id)
        session["message_count"] = session.get("message_count", 0) + msg_count
        session["end_time"] = now_iso()
        session["last_chunk_time"] = now_iso()
        
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
    
    def _save_buffer(self):
        """保存缓冲区到磁盘（崩溃恢复用）"""
        data = {
            "session_id": self.session_id,
            "messages": self.messages,
            "chunk_num": self.chunk_num,
            "last_flush_time": self.last_flush_time
        }
        with open(self._buffer_path(), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _clear_buffer(self):
        """清除磁盘缓冲区"""
        path = self._buffer_path()
        if path.exists():
            path.unlink()


# ========== 会话管理 ==========

class SessionManager:
    """会话管理器 - 完整实现原方案"""
    
    def __init__(self):
        ensure_dirs()
        self._buffers = {}  # session_id -> MessageBuffer
    
    def start(self, platform: str, context: str = '') -> str:
        """
        开始新会话
        
        原方案：创建 active/ 索引，不创建 completed/
        """
        import uuid
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        uid = uuid.uuid4().hex[:6]
        session_id = f"session_{ts}_{uid}"
        
        session_data = {
            "session_id": session_id,
            "platform": platform,
            "start_time": now_iso(),
            "end_time": None,
            "message_count": 0,
            "chunks": [],
            "status": "active",
            "context": context,
            "last_chunk_time": None
        }
        
        # 写入 active/
        path = ACTIVE_DIR / f"{session_id}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        # 创建缓冲区
        self._buffers[session_id] = MessageBuffer(session_id, platform)
        
        print(f"✅ 会话已创建: {session_id}")
        print(f"   平台: {platform}")
        print(f"   分块阈值: {CHUNK_SIZE}条 / {FLUSH_INTERVAL//60}分钟")
        return session_id
    
    def push(self, session_id: str, message: dict) -> dict:
        """
        推入单条消息（自动分块）
        
        原方案核心：消息先入缓冲区，满条件自动切块
        """
        buffer = self._get_buffer(session_id)
        if not buffer:
            print(f"❌ 会话不存在或已结束: {session_id}")
            return {}
        
        result = buffer.push(message)
        
        if result.get("flushed"):
            print(f"📦 自动分块: {result['chunk_id']} ({result['message_count']}条, 原因: {result['reason']})")
        
        return result
    
    def flush(self, session_id: str) -> dict:
        """手动刷新缓冲区"""
        buffer = self._get_buffer(session_id)
        if not buffer:
            print(f"❌ 会话不存在: {session_id}")
            return {}
        
        result = buffer.flush("manual")
        if result.get("flushed"):
            print(f"📦 手动刷新: {result['chunk_id']} ({result['message_count']}条)")
        else:
            print("📭 缓冲区为空")
        return result
    
    def end(self, session_id: str, summary: str = '', keywords: list = None) -> dict:
        """
        结束会话
        
        原方案设计：
        1. 刷新缓冲区
        2. active/ → completed/
        3. 写入摘要
        4. 更新主索引
        5. 写入 .last_session_id
        """
        # 1. 刷新缓冲区（检查是否已被 checkpoint 子进程刷新）
        buffer = self._buffers.get(session_id)
        if buffer and buffer.messages:
            # 检查磁盘缓冲区文件是否还存在
            # 如果不存在，说明已被 checkpoint 子进程 flush 过
            disk_buffer_path = BASE_DIR / f".buffer_{session_id}.json"
            if disk_buffer_path.exists():
                buffer.flush("session_end")
            else:
                # 缓冲区已被外部 flush，清空内存中的消息
                buffer.messages.clear()
        
        # 2. 读取 active 索引
        active_path = ACTIVE_DIR / f"{session_id}.json"
        if not active_path.exists():
            print(f"❌ 活跃会话不存在: {session_id}")
            return {}
        
        with open(active_path, 'r', encoding='utf-8') as f:
            session = json.load(f)
        
        # 3. 更新状态
        session["status"] = "complete"
        session["end_time"] = now_iso()
        session["summary"] = summary
        session["keywords"] = keywords or []
        
        # 4. active/ → completed/
        completed_path = COMPLETED_DIR / f"{session_id}.json"
        with open(completed_path, 'w', encoding='utf-8') as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
        
        # 5. 删除 active/
        active_path.unlink()
        
        # 6. 写入摘要
        if summary:
            summary_dir = SUMMARY_DIR / today_path()
            summary_dir.mkdir(parents=True, exist_ok=True)
            summary_path = summary_dir / f"{session_id}_summary.md"
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"# Session Summary: {session_id}\n\n")
                f.write(f"- 平台: {session['platform']}\n")
                f.write(f"- 时间: {session['start_time']} → {session['end_time']}\n")
                f.write(f"- 消息数: {session['message_count']}\n")
                f.write(f"- 分块数: {len(session['chunks'])}\n")
                f.write(f"- 关键词: {', '.join(keywords or [])}\n\n")
                f.write(summary)
        
        # 7. 更新主索引
        self._update_main_index(session)
        
        # 8. 写入 .last_session_id
        LAST_SESSION_FILE.write_text(session_id)
        
        # 清理缓冲区引用
        self._buffers.pop(session_id, None)
        
        print(f"✅ 会话已结束: {session_id}")
        print(f"   消息数: {session['message_count']}")
        print(f"   分块数: {len(session['chunks'])}")
        print(f"   .last_session_id 已写入")
        
        return session
    
    def resume(self, last_n: int = 30) -> dict:
        """恢复上一个会话"""
        if not LAST_SESSION_FILE.exists():
            print("📭 没有上一个会话记录")
            return {}
        
        session_id = LAST_SESSION_FILE.read_text().strip()
        if not session_id:
            print("📭 .last_session_id 为空")
            return {}
        
        # 清除标记
        LAST_SESSION_FILE.unlink()
        
        print(f"🔄 恢复上一个会话: {session_id}")
        return self.restore(session_id, last_n)
    
    def restore(self, session_id: str, last_n: int = 30) -> dict:
        """
        恢复指定会话
        
        原方案完整恢复链路：
        1. 读取 MEMORY.md（长期记忆）
        2. 读取 memory/YYYY-MM-DD.md（今日记忆）
        3. 读取会话摘要 + 消息 + 关键词
        4. 输出完整上下文
        """
        # 0. 查找会话
        session = None
        for status_dir in [COMPLETED_DIR, ACTIVE_DIR]:
            path = status_dir / f"{session_id}.json"
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    session = json.load(f)
                break
        
        if not session:
            print(f"❌ 会话不存在: {session_id}")
            return {}
        
        # 1. 加载 MEMORY.md
        memory_content = ""
        # 从 session_manager.py 向上找 workspace: hermes-skills/hermes-sync-core/ → skills/ → workspace/
        workspace = Path(__file__).parent.parent.parent / "workspace"
        memory_path = workspace / "MEMORY.md"
        if not memory_path.exists():
            # 回退: 直接在 workspace 下找
            workspace = Path("/workspace/projects/workspace")
            memory_path = workspace / "MEMORY.md"
        if memory_path.exists():
            with open(memory_path, 'r', encoding='utf-8') as f:
                memory_content = f.read()
        
        # 2. 加载今日记忆
        today_memory = ""
        today_file = workspace / "memory" / f"{datetime.now().strftime('%Y-%m-%d')}.md"
        if today_file.exists():
            with open(today_file, 'r', encoding='utf-8') as f:
                today_memory = f.read()
        
        # 3. 加载会话消息
        all_messages = []
        for chunk_id in session.get("chunks", []):
            for chunk_file in RAW_DIR.rglob(f"{chunk_id}.json"):
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk = json.load(f)
                all_messages.extend(chunk.get("messages", []))
                break
        
        recent = all_messages[-last_n:] if len(all_messages) > last_n else all_messages
        
        # 4. 加载摘要
        summary = ""
        for summary_file in SUMMARY_DIR.rglob(f"{session_id}_summary.md"):
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = f.read()
            break
        
        result = {
            "session_id": session_id,
            "platform": session.get("platform", ""),
            "start_time": session.get("start_time", ""),
            "end_time": session.get("end_time", ""),
            "message_count": session.get("message_count", 0),
            "chunk_count": len(session.get("chunks", [])),
            "keywords": session.get("keywords", []),
            "summary": summary,
            "messages": recent,
            "memory_md": memory_content,
            "today_memory": today_memory,
            "restored_at": now_iso()
        }
        
        # 5. 输出
        print(f"🔄 恢复会话: {session_id}")
        print(f"   平台: {result['platform']}")
        print(f"   时间: {result['start_time'][:19]} → {result['end_time'][:19] if result['end_time'] else '进行中'}")
        print(f"   消息: {result['message_count']}条 / {result['chunk_count']}块")
        
        if result['keywords']:
            print(f"   关键词: {', '.join(result['keywords'])}")
        
        # 显示记忆摘要
        if memory_content:
            print()
            print("🧠 长期记忆 (MEMORY.md):")
            for line in memory_content.split('\n'):
                if line.strip() and not line.startswith('#') and not line.startswith('>') and not line.startswith('---'):
                    print(f"   {line.strip()}")
                    if len(line.strip()) > 100:
                        break  # 只显示前几行
        
        if today_memory:
            print()
            print(f"📅 今日记忆 ({datetime.now().strftime('%Y-%m-%d')}):")
            for line in today_memory.split('\n')[:10]:
                if line.strip() and not line.startswith('#'):
                    print(f"   {line.strip()}")
        
        if summary:
            print()
            print("📝 会话摘要:")
            for line in summary.split('\n'):
                if line.strip() and not line.startswith('#') and not line.startswith('-'):
                    print(f"   {line.strip()}")
        
        if recent:
            print()
            print(f"📋 最近 {len(recent)} 条消息:")
            for msg in recent[-5:]:
                role = msg.get('role', '?')
                content = msg.get('content', '')[:80]
                icon = "👤" if role == 'user' else "🤖"
                print(f"   {icon} {content}{'...' if len(msg.get('content','')) > 80 else ''}")
        
        print()
        print("✅ 恢复完成")
        
        return result
    
    def verify(self, session_id: str) -> dict:
        """
        验证会话连续性
        
        原方案：检查chunk链式指针 + message_range 间隙
        """
        session = None
        for status_dir in [ACTIVE_DIR, COMPLETED_DIR]:
            path = status_dir / f"{session_id}.json"
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    session = json.load(f)
                break
        
        if not session:
            return {"error": f"会话不存在: {session_id}"}
        
        issues = []
        last_end_id = 0
        total_messages = 0
        checksum_ok = 0
        checksum_fail = 0
        
        for chunk_id in session.get("chunks", []):
            chunk_file = None
            for f in RAW_DIR.rglob(f"{chunk_id}.json"):
                chunk_file = f
                break
            
            if not chunk_file:
                issues.append(f"缺失chunk: {chunk_id}")
                continue
            
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk = json.load(f)
            
            # 检查message_range连续性
            start_id, end_id = chunk["message_range"]
            if last_end_id > 0 and start_id != last_end_id + 1:
                issues.append(f"chunk {chunk_id} 间隙: 期望 {last_end_id+1}, 实际 {start_id}")
            
            # 检查checksum
            expected_checksum = calc_checksum({"messages": chunk["messages"]})
            if chunk["checksum"] == expected_checksum:
                checksum_ok += 1
            else:
                checksum_fail += 1
                issues.append(f"chunk {chunk_id} checksum 不匹配")
            
            # 检查prev/next指针
            expected_prev = f"{session_id}_{int(chunk_id.split('_')[-1])-1:03d}" if chunk_id != session["chunks"][0] else None
            if chunk.get("prev_chunk") != expected_prev:
                issues.append(f"chunk {chunk_id} prev_chunk 指针错误")
            
            last_end_id = end_id
            total_messages += chunk["message_count"]
        
        # 检查缓冲区是否有未刷新消息
        buffer_file = BASE_DIR / f".buffer_{session_id}.json"
        buffered = 0
        if buffer_file.exists():
            with open(buffer_file, 'r', encoding='utf-8') as f:
                buf = json.load(f)
            buffered = len(buf.get("messages", []))
            if buffered > 0:
                issues.append(f"缓冲区有 {buffered} 条未刷新消息")
        
        result = {
            "session_id": session_id,
            "status": session.get("status", "unknown"),
            "total_chunks": len(session.get("chunks", [])),
            "total_messages": total_messages,
            "buffered_messages": buffered,
            "checksum_ok": checksum_ok,
            "checksum_fail": checksum_fail,
            "issues": issues,
            "healthy": len(issues) == 0
        }
        
        print(f"🔍 会话验证: {session_id}")
        print(f"   状态: {result['status']}")
        print(f"   分块: {result['total_chunks']}")
        print(f"   消息: {result['total_messages']} (缓冲区: {result['buffered_messages']})")
        print(f"   校验: ✅{result['checksum_ok']} ❌{result['checksum_fail']}")
        
        if issues:
            print(f"   ⚠️ 问题:")
            for issue in issues:
                print(f"      - {issue}")
        else:
            print(f"   ✅ 健康")
        
        return result
    
    def recover(self) -> list:
        """
        恢复所有未完成的会话
        
        原方案设计：active/ 中的会话 = 异常中断，需要恢复
        """
        recovered = []
        
        for active_file in ACTIVE_DIR.glob("session_*.json"):
            session_id = active_file.stem
            
            with open(active_file, 'r', encoding='utf-8') as f:
                session = json.load(f)
            
            # 检查缓冲区
            buffer_file = BASE_DIR / f".buffer_{session_id}.json"
            buffered_messages = []
            if buffer_file.exists():
                with open(buffer_file, 'r', encoding='utf-8') as f:
                    buf = json.load(f)
                buffered_messages = buf.get("messages", [])
            
            if buffered_messages:
                # 有未刷新消息，写入最后一个chunk
                chunk_num = len(session.get("chunks", [])) + 1
                chunk_id = f"{session_id}_{chunk_num:03d}"
                
                chunk_data = {
                    "chunk_id": chunk_id,
                    "session_id": session_id,
                    "platform": session.get("platform", ""),
                    "message_range": [buffered_messages[0].get("id", 1), buffered_messages[-1].get("id", len(buffered_messages))],
                    "message_count": len(buffered_messages),
                    "checksum": calc_checksum({"messages": buffered_messages}),
                    "prev_chunk": session["chunks"][-1] if session.get("chunks") else None,
                    "next_chunk": None,
                    "status": "recovered",
                    "flush_reason": "crash_recovery",
                    "timestamp_start": buffered_messages[0].get("timestamp", now_iso()),
                    "timestamp_end": buffered_messages[-1].get("timestamp", now_iso()),
                    "messages": buffered_messages
                }
                
                # 写入chunk
                chunk_dir = RAW_DIR / today_path()
                chunk_dir.mkdir(parents=True, exist_ok=True)
                with open(chunk_dir / f"{chunk_id}.json", 'w', encoding='utf-8') as f:
                    json.dump(chunk_data, f, indent=2, ensure_ascii=False)
                
                # 更新session
                session["chunks"].append(chunk_id)
                session["message_count"] = session.get("message_count", 0) + len(buffered_messages)
                session["end_time"] = now_iso()
                
                with open(active_file, 'w', encoding='utf-8') as f:
                    json.dump(session, f, indent=2, ensure_ascii=False)
                
                # 清除缓冲区
                buffer_file.unlink()
                
                recovered.append({
                    "session_id": session_id,
                    "recovered_messages": len(buffered_messages),
                    "chunk_id": chunk_id
                })
                
                print(f"🔧 恢复会话: {session_id}")
                print(f"   恢复消息: {len(buffered_messages)}条")
                print(f"   写入chunk: {chunk_id}")
        
        if not recovered:
            print("✅ 没有需要恢复的会话")
        
        return recovered
    
    def checkpoint(self, rounds: int = 0) -> dict:
        """
        Token Budget 检查点
        
        原方案设计：轮次/时间/output 阈值检查，触发归档
        
        注意：此函数可能被外部进程调用（如 token_budget_patrol.py），
        此时内存中的 buffers 为空，需要从磁盘恢复缓冲区。
        """
        result = {
            "timestamp": now_iso(),
            "rounds": rounds,
            "action": "none",
            "sessions_flushed": []
        }
        
        # 从磁盘恢复缓冲区（外部进程调用时必要）
        self._restore_buffers_from_disk()
        
        if rounds >= TOKEN_STOP_ROUNDS:
            # 红色熔断：强制刷新所有活跃会话
            result["action"] = "force_flush"
            print(f"🔴 红色熔断: 轮次 {rounds} ≥ {TOKEN_STOP_ROUNDS}")
            
            for sid, buffer in list(self._buffers.items()):
                if buffer.messages:
                    flush_result = buffer.flush("token_budget_red")
                    result["sessions_flushed"].append(flush_result)
                    # flush 后清空消息，保留缓冲区对象（end() 需要检查但不会重复flush）
                    buffer.messages.clear()
                    buffer._clear_buffer()
            
            if not result["sessions_flushed"]:
                print("   没有需要刷新的缓冲区")
            else:
                print(f"   已刷新 {len(result['sessions_flushed'])} 个会话，请执行 /new")
        
        elif rounds >= TOKEN_WARN_ROUNDS:
            # 黄色预警：提醒归档
            result["action"] = "warn"
            print(f"🟡 黄色预警: 轮次 {rounds} ≥ {TOKEN_WARN_ROUNDS}")
            print("   建议执行归档: python3 session_manager.py end <session_id>")
        
        else:
            result["action"] = "ok"
        
        return result
    
    def _restore_buffers_from_disk(self):
        """从磁盘恢复缓冲区（用于外部进程调用 checkpoint）"""
        for buffer_file in BASE_DIR.glob(".buffer_session_*.json"):
            try:
                with open(buffer_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                session_id = data.get("session_id", "")
                if not session_id:
                    continue
                
                # 检查会话是否还活跃
                active_path = ACTIVE_DIR / f"{session_id}.json"
                if not active_path.exists():
                    buffer_file.unlink()
                    continue
                
                # 如果已有缓冲区（内存中的），同步磁盘数据到现有缓冲区
                if session_id in self._buffers:
                    existing = self._buffers[session_id]
                    # 磁盘消息可能比内存新（崩溃场景），取较新的
                    disk_messages = data.get("messages", [])
                    if len(disk_messages) > len(existing.messages):
                        existing.messages = disk_messages
                        existing.chunk_num = data.get("chunk_num", existing.chunk_num)
                    continue
                
                # 恢复新缓冲区
                buffer = MessageBuffer.__new__(MessageBuffer)
                buffer.session_id = session_id
                buffer.platform = data.get("platform", "")
                buffer.messages = data.get("messages", [])
                buffer.last_flush_time = data.get("last_flush_time", time.time())
                buffer.chunk_num = data.get("chunk_num", 0)
                buffer._timer = None
                
                if buffer.messages:
                    self._buffers[session_id] = buffer
            except Exception:
                pass
    
    def list_sessions(self, date_filter: str = None):
        """列出所有会话"""
        sessions = []
        
        for status_dir, status_label in [(ACTIVE_DIR, "🟡 活跃"), (COMPLETED_DIR, "🟢 完成")]:
            for session_file in status_dir.glob("session_*.json"):
                with open(session_file, 'r', encoding='utf-8') as f:
                    s = json.load(f)
                
                if date_filter and not s.get("start_time", "").startswith(date_filter):
                    continue
                
                sessions.append({
                    **s,
                    "status_label": status_label
                })
        
        if not sessions:
            print("📭 暂无会话记录")
            return
        
        print(f"📋 会话列表 ({len(sessions)} 个)")
        print("-" * 60)
        for s in sessions:
            keywords = ', '.join(s.get('keywords', []))
            print(f"{s['status_label']} {s['session_id']}")
            print(f"   平台: {s.get('platform','')} | 消息: {s.get('message_count',0)} | 关键词: {keywords}")
            print()
    
    # ========== 内部方法 ==========
    
    def _get_buffer(self, session_id: str) -> MessageBuffer:
        """获取或创建缓冲区"""
        if session_id not in self._buffers:
            # 检查会话是否存在
            path = ACTIVE_DIR / f"{session_id}.json"
            if not path.exists():
                return None
            with open(path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            self._buffers[session_id] = MessageBuffer(session_id, session.get("platform", ""))
        return self._buffers[session_id]
    
    def _update_main_index(self, session: dict):
        """更新主索引"""
        index_path = BASE_DIR / "index" / "session_index.json"
        
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {"version": "2.0.0", "sessions": [], "keywords_index": {}}
        
        # 更新或添加
        existing_idx = next((i for i, s in enumerate(index["sessions"]) 
                           if s["session_id"] == session["session_id"]), -1)
        
        entry = {
            "session_id": session["session_id"],
            "platform": session.get("platform", ""),
            "start_time": session.get("start_time", ""),
            "end_time": session.get("end_time", ""),
            "message_count": session.get("message_count", 0),
            "chunk_count": len(session.get("chunks", [])),
            "status": session.get("status", ""),
            "keywords": session.get("keywords", [])
        }
        
        if existing_idx >= 0:
            index["sessions"][existing_idx] = entry
        else:
            index["sessions"].append(entry)
        
        # 更新关键词索引
        for keyword in session.get("keywords", []):
            if keyword not in index["keywords_index"]:
                index["keywords_index"][keyword] = []
            if session["session_id"] not in index["keywords_index"][keyword]:
                index["keywords_index"][keyword].append(session["session_id"])
        
        index["last_updated"] = now_iso()
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)


# ========== CLI ==========

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    cmd = sys.argv[1]
    mgr = SessionManager()
    
    if cmd == "start":
        platform = sys.argv[2] if len(sys.argv) > 2 else "unknown"
        context = sys.argv[3] if len(sys.argv) > 3 else ""
        mgr.start(platform, context)
    
    elif cmd == "push":
        session_id = sys.argv[2]
        message = json.loads(sys.argv[3])
        mgr.push(session_id, message)
    
    elif cmd == "flush":
        session_id = sys.argv[2]
        mgr.flush(session_id)
    
    elif cmd == "end":
        session_id = sys.argv[2]
        summary = sys.argv[3] if len(sys.argv) > 3 else ""
        keywords = json.loads(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].startswith('[') else [sys.argv[4]] if len(sys.argv) > 4 else []
        mgr.end(session_id, summary, keywords)
    
    elif cmd == "resume":
        last_n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        mgr.resume(last_n)
    
    elif cmd == "restore":
        session_id = sys.argv[2]
        last_n = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        mgr.restore(session_id, last_n)
    
    elif cmd == "verify":
        session_id = sys.argv[2]
        mgr.verify(session_id)
    
    elif cmd == "recover":
        mgr.recover()
    
    elif cmd == "list":
        date_filter = sys.argv[2] if len(sys.argv) > 2 else None
        mgr.list_sessions(date_filter)
    
    elif cmd == "checkpoint":
        rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        mgr.checkpoint(rounds)
    
    else:
        print(f"❌ 未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
