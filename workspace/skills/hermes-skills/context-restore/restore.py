#!/usr/bin/env python3
"""
Context Restore Engine
会话归档后的上下文自动恢复

用法:
  python3 restore.py auto                        # 自动恢复上一个会话
  python3 restore.py restore <session_id> [last_n]  # 指定会话恢复
  python3 restore.py list                         # 列出所有会话
  python3 restore.py history                      # 恢复历史
  python3 restore.py config                       # 查看配置
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path

# 配置路径
BASE_DIR = Path(__file__).parent.parent / "hermes-sync-core" / "sessions"
CONFIG_FILE = Path(__file__).parent / "config.json"
HISTORY_FILE = Path(__file__).parent / ".restore_history"

# 默认配置
DEFAULT_CONFIG = {
    "last_n_messages": 30,
    "include_summary": True,
    "include_keywords": True,
    "compress_threshold": 50,
    "compress_strategy": "keep_decisions",
    "storage_backend": "local"
}


def load_config() -> dict:
    """加载配置"""
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config.update(json.load(f))
    return config


def save_config(config: dict):
    """保存配置"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_history() -> list:
    """加载恢复历史"""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_history(history: list):
    """保存恢复历史"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def record_restore(session_id: str, source: str = "auto"):
    """记录恢复操作"""
    history = load_history()
    history.append({
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "source": source
    })
    # 只保留最近100条
    save_history(history[-100:])


def load_index() -> dict:
    """加载会话索引"""
    index_file = BASE_DIR / "index" / "session_index.json"
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"sessions": [], "keywords_index": {}}


def get_session(session_id: str) -> dict:
    """获取会话信息"""
    index = load_index()
    for s in index.get("sessions", []):
        if s["session_id"] == session_id:
            return s
    return None


def get_last_session_id() -> str:
    """读取上一个会话ID"""
    last_id_file = BASE_DIR / ".last_session_id"
    if last_id_file.exists():
        return last_id_file.read_text().strip()
    
    # 回退：从 memory/sessions/ 找最新文件
    memory_sessions = Path("/workspace/projects/workspace/memory/sessions")
    if memory_sessions.exists():
        files = sorted(memory_sessions.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        if files:
            # 从文件名提取 session id
            return files[0].stem
    return ""


def clear_last_session_id():
    """清除标记"""
    last_id_file = BASE_DIR / ".last_session_id"
    if last_id_file.exists():
        last_id_file.unlink()


def load_chunks(session_id: str, last_n: int = 30) -> list:
    """加载会话消息"""
    session = get_session(session_id)
    if not session:
        return []
    
    all_messages = []
    for chunk_id in session.get("chunks", []):
        # 搜索chunk文件
        for chunk_file in BASE_DIR.rglob(f"{chunk_id}.json"):
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk = json.load(f)
            all_messages.extend(chunk.get("messages", []))
            break
    
    # 返回最后N条
    if len(all_messages) > last_n:
        return all_messages[-last_n:]
    return all_messages


def load_summary(session_id: str) -> str:
    """加载会话摘要"""
    for summary_file in BASE_DIR.rglob(f"{session_id}_summary.md"):
        with open(summary_file, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def compress_messages(messages: list, strategy: str = "keep_decisions") -> list:
    """压缩消息（超长会话用）"""
    if strategy == "keep_decisions":
        # 只保留包含决策关键词的消息
        decision_keywords = ["决定", "决策", "策略", "买", "卖", "止损", "止盈", 
                           "开仓", "平仓", "确认", "结论", "TODO", "待办", "重要"]
        compressed = []
        for msg in messages:
            content = msg.get("content", "")
            if any(kw in content for kw in decision_keywords):
                compressed.append(msg)
        return compressed if compressed else messages[-10:]  # 至少保留最后10条
    
    elif strategy == "summary_only":
        return messages[-5:]  # 只保留最后5条
    
    return messages  # keep_all


def restore_auto(config: dict = None) -> dict:
    """自动恢复上一个会话"""
    if config is None:
        config = load_config()
    
    # 优先使用 session_manager
    mgr_path = Path(__file__).parent.parent / "hermes-sync-core" / "session_manager.py"
    if mgr_path.exists():
        import importlib.util, io, contextlib
        spec = importlib.util.spec_from_file_location("session_manager", mgr_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mgr = mod.SessionManager()
        # 抑制 session_manager 的 stdout 输出
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = mgr.resume(config["last_n_messages"])
        if result:
            return result
    
    # 回退：从 memory/sessions/ 读最新归档
    memory_sessions = Path("/workspace/projects/workspace/memory/sessions")
    if memory_sessions.exists():
        files = sorted(memory_sessions.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        if files:
            latest = files[0]
            content = latest.read_text(encoding='utf-8')
            result = {
                "session_id": latest.stem,
                "platform": "feishu",
                "summary": content[:500],
                "messages": [],
                "restored_at": datetime.now().isoformat(),
                "source_file": str(latest)
            }
            print(f"🔄 恢复最近归档: {latest.name}")
            print(f"   路径: {latest}")
            print(f"   大小: {latest.stat().st_size} bytes")
            print()
            for line in content.split('\n')[:10]:
                if line.strip():
                    print(f"   {line.strip()}")
            print()
            print("✅ 恢复完成")
            record_restore(latest.stem, "auto-memory-fallback")
            return result
    
    print("📭 没有上一个会话记录")
    return {}


def restore_session(session_id: str, last_n: int = 30, config: dict = None) -> dict:
    """恢复指定会话"""
    if config is None:
        config = load_config()
    
    session = get_session(session_id)
    if not session:
        print(f"❌ 会话不存在: {session_id}")
        return {}
    
    # 加载消息
    messages = load_chunks(session_id, last_n)
    
    # 压缩（如需要）
    if len(messages) > config["compress_threshold"]:
        messages = compress_messages(messages, config["compress_strategy"])
    
    # 加载摘要
    summary = load_summary(session_id) if config["include_summary"] else ""
    
    # 构建结果
    result = {
        "session_id": session_id,
        "platform": session.get("platform", "unknown"),
        "start_time": session.get("start_time", ""),
        "end_time": session.get("end_time", ""),
        "message_count": session.get("message_count", 0),
        "keywords": session.get("keywords", []) if config["include_keywords"] else [],
        "summary": summary,
        "messages": messages,
        "restored_at": datetime.now().isoformat()
    }
    
    # 输出
    print_restore_result(result)
    
    # 记录恢复
    record_restore(session_id, "auto")
    
    return result


def print_restore_result(result: dict):
    """格式化输出恢复结果"""
    print(f"🔄 恢复会话: {result['session_id']}")
    print(f"   平台: {result['platform']}")
    print(f"   时间: {result['start_time'][:19]} → {result['end_time'][:19] if result['end_time'] else '进行中'}")
    print(f"   消息数: {result['message_count']}")
    
    if result['keywords']:
        print(f"   关键词: {', '.join(result['keywords'])}")
    
    if result['summary']:
        print()
        print("📝 会话摘要:")
        # 只输出摘要的核心部分（跳过元数据行）
        for line in result['summary'].split('\n'):
            if line.strip() and not line.startswith('#') and not line.startswith('-'):
                print(f"   {line.strip()}")
    
    if result['messages']:
        print()
        print(f"📋 最近 {len(result['messages'])} 条消息:")
        for msg in result['messages'][-5:]:  # 只显示最后5条
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:80]
            icon = "👤" if role == 'user' else "🤖"
            print(f"   {icon} {content}{'...' if len(msg.get('content', '')) > 80 else ''}")
    
    print()
    print("✅ 恢复完成")


def cmd_list():
    """列出所有会话"""
    index = load_index()
    sessions = index.get("sessions", [])
    
    if not sessions:
        print("📭 暂无会话记录")
        return
    
    print(f"📋 会话列表 ({len(sessions)} 个)")
    print("-" * 60)
    for s in sessions:
        status_icon = "🟢" if s.get("status") == "complete" else "🟡"
        keywords = ', '.join(s.get('keywords', []))
        print(f"{status_icon} {s['session_id']}")
        print(f"   平台: {s.get('platform','')} | 消息: {s.get('message_count',0)} | 关键词: {keywords}")
        print()


def cmd_history():
    """查看恢复历史"""
    history = load_history()
    if not history:
        print("📭 暂无恢复记录")
        return
    
    print(f"📜 恢复历史 (最近 {len(history)} 条)")
    print("-" * 40)
    for h in history[-10:]:
        print(f"  {h['timestamp'][:19]} | {h['session_id']} | {h['source']}")


def cmd_config():
    """查看当前配置"""
    config = load_config()
    print("⚙️  Context Restore 配置")
    print("-" * 30)
    for k, v in config.items():
        print(f"  {k}: {v}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    cmd = sys.argv[1]
    config = load_config()
    
    if cmd == "auto":
        restore_auto(config)
    
    elif cmd == "restore":
        session_id = sys.argv[2]
        last_n = int(sys.argv[3]) if len(sys.argv) > 3 else config["last_n_messages"]
        restore_session(session_id, last_n, config)
    
    elif cmd == "list":
        cmd_list()
    
    elif cmd == "history":
        cmd_history()
    
    elif cmd == "config":
        cmd_config()
    
    else:
        print(f"❌ 未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
