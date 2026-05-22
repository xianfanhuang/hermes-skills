#!/usr/bin/env python3
"""
Hermes Session 本地归档工具
不依赖 GitHub API，直接存本地文件

用法:
  python3 session_local.py start <platform> [context]
  python3 session_local.py store <session_id> <messages_json>
  python3 session_local.py end <session_id> [summary] [keywords_json]
  python3 session_local.py list [date]
  python3 session_local.py resume [last_n]         # 恢复上一个会话
  python3 session_local.py restore <session_id> [last_n]
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent / "sessions"
RAW_DIR = BASE_DIR / "raw"
SUMMARY_DIR = BASE_DIR / "summaries"
INDEX_FILE = BASE_DIR / "index" / "session_index.json"

CHUNK_SIZE = 50  # 每50条消息一个chunk


def ensure_dirs():
    """确保目录存在"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "index").mkdir(parents=True, exist_ok=True)


def load_index() -> dict:
    """加载索引"""
    ensure_dirs()
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "version": "1.0.0",
        "last_updated": datetime.now().isoformat(),
        "total_sessions": 0,
        "sessions": [],
        "keywords_index": {}
    }


def save_index(index: dict):
    """保存索引"""
    ensure_dirs()
    index["last_updated"] = datetime.now().isoformat()
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def calc_checksum(data: dict) -> str:
    """计算校验和"""
    content = json.dumps(data, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def session_start(platform: str, context: str = '') -> str:
    """开始新会话"""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    session_id = f"session_{ts}"
    
    index = load_index()
    session_entry = {
        "session_id": session_id,
        "platform": platform,
        "context": context,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "message_count": 0,
        "chunks": [],
        "status": "active",
        "summary": None,
        "keywords": []
    }
    index["sessions"].append(session_entry)
    index["total_sessions"] += 1
    save_index(index)
    
    print(f"✅ 会话已创建: {session_id}")
    print(f"   平台: {platform}")
    print(f"   上下文: {context or '(无)'}")
    return session_id


def session_store(session_id: str, messages: list) -> dict:
    """存储消息（自动分块）"""
    ensure_dirs()
    index = load_index()
    
    # 查找会话
    session = None
    for s in index["sessions"]:
        if s["session_id"] == session_id:
            session = s
            break
    
    if not session:
        print(f"❌ 会话不存在: {session_id}")
        return {}
    
    # 计算chunk编号
    existing_chunks = session["chunks"]
    chunk_num = len(existing_chunks) + 1
    chunk_id = f"{session_id}_{chunk_num:03d}"
    
    # 构建chunk
    date_str = datetime.now().strftime('%Y-%m-%d')
    chunk_data = {
        "chunk_id": chunk_id,
        "session_id": session_id,
        "platform": session["platform"],
        "message_range": [1, len(messages)],
        "message_count": len(messages),
        "checksum": calc_checksum({"messages": messages}),
        "prev_chunk": existing_chunks[-1] if existing_chunks else None,
        "next_chunk": None,
        "status": "complete",
        "timestamp_start": messages[0].get("timestamp", datetime.now().isoformat()) if messages else "",
        "timestamp_end": messages[-1].get("timestamp", datetime.now().isoformat()) if messages else "",
        "messages": messages
    }
    
    # 更新前一个chunk的next指针
    if existing_chunks:
        prev_chunk_path = RAW_DIR / date_str.replace("-", "/") / f"{existing_chunks[-1]}.json"
        if prev_chunk_path.exists():
            with open(prev_chunk_path, 'r', encoding='utf-8') as f:
                prev_chunk = json.load(f)
            prev_chunk["next_chunk"] = chunk_id
            with open(prev_chunk_path, 'w', encoding='utf-8') as f:
                json.dump(prev_chunk, f, indent=2, ensure_ascii=False)
    
    # 保存chunk
    chunk_dir = RAW_DIR / date_str.replace("-", "/")
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_path = chunk_dir / f"{chunk_id}.json"
    
    with open(chunk_path, 'w', encoding='utf-8') as f:
        json.dump(chunk_data, f, indent=2, ensure_ascii=False)
    
    # 更新索引
    session["chunks"].append(chunk_id)
    session["message_count"] += len(messages)
    save_index(index)
    
    print(f"✅ Chunk 已存储: {chunk_id}")
    print(f"   消息数: {len(messages)}")
    print(f"   路径: {chunk_path}")
    return chunk_data


def session_end(session_id: str, summary: str = '', keywords: list = None):
    """结束会话"""
    index = load_index()
    
    for s in index["sessions"]:
        if s["session_id"] == session_id:
            s["status"] = "complete"
            s["end_time"] = datetime.now().isoformat()
            s["summary"] = summary
            s["keywords"] = keywords or []
            
            # 保存摘要
            if summary:
                date_str = datetime.now().strftime('%Y-%m-%d')
                summary_dir = SUMMARY_DIR / date_str.replace("-", "/")
                summary_dir.mkdir(parents=True, exist_ok=True)
                summary_path = summary_dir / f"{session_id}_summary.md"
                
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Session Summary: {session_id}\n\n")
                    f.write(f"- 平台: {s['platform']}\n")
                    f.write(f"- 时间: {s['start_time']} → {s['end_time']}\n")
                    f.write(f"- 消息数: {s['message_count']}\n")
                    f.write(f"- 关键词: {', '.join(keywords or [])}\n\n")
                    f.write(summary)
            
            save_index(index)
            
            # 写入 .last_session_id（上下文恢复用）
            last_id_path = BASE_DIR / ".last_session_id"
            with open(last_id_path, 'w', encoding='utf-8') as f:
                f.write(session_id)
            
            print(f"✅ 会话已结束: {session_id}")
            print(f"   消息数: {s['message_count']}")
            print(f"   摘要: {summary[:50] + '...' if len(summary) > 50 else summary or '(无)'}")
            print(f"   .last_session_id 已写入")
            return
    
    print(f"❌ 会话不存在: {session_id}")


def session_list(date_filter: str = None):
    """列出会话"""
    index = load_index()
    sessions = index["sessions"]
    
    if date_filter:
        sessions = [s for s in sessions if s["start_time"][:10] == date_filter]
    
    if not sessions:
        print("📭 暂无会话记录")
        return
    
    print(f"📋 会话列表 ({len(sessions)} 个)")
    print("-" * 60)
    for s in sessions:
        status_icon = "🟢" if s["status"] == "complete" else "🟡"
        print(f"{status_icon} {s['session_id']}")
        print(f"   平台: {s['platform']} | 消息: {s['message_count']} | 状态: {s['status']}")
        if s.get("summary"):
            print(f"   摘要: {s['summary'][:50]}...")
        print()


def session_resume(last_n: int = 30):
    """恢复上一个会话的上下文（读取 .last_session_id）"""
    last_id_path = BASE_DIR / ".last_session_id"
    
    if not last_id_path.exists():
        print("📭 没有上一个会话记录")
        return None
    
    session_id = last_id_path.read_text().strip()
    if not session_id:
        print("📭 .last_session_id 为空")
        return None
    
    # 清除标记（避免重复恢复）
    last_id_path.unlink()
    
    print(f"🔄 恢复上一个会话: {session_id}")
    return session_restore(session_id, last_n)


def session_restore(session_id: str, last_n: int = 50):
    """恢复会话上下文"""
    index = load_index()
    
    session = None
    for s in index["sessions"]:
        if s["session_id"] == session_id:
            session = s
            break
    
    if not session:
        print(f"❌ 会话不存在: {session_id}")
        return
    
    print(f"🔄 恢复会话: {session_id}")
    print(f"   平台: {session['platform']}")
    print(f"   总消息: {session['message_count']}")
    
    all_messages = []
    for chunk_id in session["chunks"]:
        # 找到chunk文件
        for date_dir in RAW_DIR.rglob("*"):
            chunk_file = date_dir / f"{chunk_id}.json"
            if chunk_file.exists():
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk = json.load(f)
                all_messages.extend(chunk.get("messages", []))
                break
    
    # 返回最后N条
    recent = all_messages[-last_n:] if len(all_messages) > last_n else all_messages
    print(f"   返回: {len(recent)} 条消息")
    
    return {
        "session_id": session_id,
        "platform": session["platform"],
        "total_messages": len(all_messages),
        "returned_messages": len(recent),
        "messages": recent
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "start":
        platform = sys.argv[2] if len(sys.argv) > 2 else "unknown"
        context = sys.argv[3] if len(sys.argv) > 3 else ""
        session_start(platform, context)
    
    elif cmd == "store":
        session_id = sys.argv[2]
        messages = json.loads(sys.argv[3])
        session_store(session_id, messages)
    
    elif cmd == "end":
        session_id = sys.argv[2]
        summary = sys.argv[3] if len(sys.argv) > 3 else ""
        keywords = json.loads(sys.argv[4]) if len(sys.argv) > 4 else []
        session_end(session_id, summary, keywords)
    
    elif cmd == "list":
        date_filter = sys.argv[2] if len(sys.argv) > 2 else None
        session_list(date_filter)
    
    elif cmd == "resume":
        last_n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        session_resume(last_n)
    
    elif cmd == "restore":
        session_id = sys.argv[2]
        last_n = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        session_restore(session_id, last_n)
    
    else:
        print(f"❌ 未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
