#!/usr/bin/env python3
"""
Hermes Sync Client v2.0 - 支持Session全量同步

功能：
1. 核心文件同步（core/ + memory/）
2. Session分块归档（sessions/）
3. 上下文恢复

环境变量：
- HERMES_GITHUB_TOKEN: GitHub Personal Access Token
- HERMES_GITHUB_OWNER: GitHub用户名
- HERMES_GITHUB_REPO: 仓库名（默认hermes-sync）
"""

import os
import sys
import json
import base64
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

import requests


class HermesSyncClient:
    """Hermes同步客户端 - v2.0支持Session管理"""
    
    def __init__(self):
        self.token = os.getenv('HERMES_GITHUB_TOKEN')
        self.owner = os.getenv('HERMES_GITHUB_OWNER', 'xianfanhuang')
        self.repo = os.getenv('HERMES_GITHUB_REPO', 'hermes-sync')
        
        if not self.token:
            print("❌ 错误: 请设置HERMES_GITHUB_TOKEN环境变量")
            sys.exit(1)
        
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = f'https://api.github.com/repos/{self.owner}/{self.repo}'
    
    def _github_request(self, method: str, path: str, data: dict = None) -> Optional[dict]:
        """GitHub API请求"""
        url = f'{self.base_url}/contents/{path}'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method == 'PUT':
                response = requests.put(url, headers=self.headers, json=data)
            else:
                return None
            
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ GitHub API错误: {e}")
            return None
    
    def _encode_content(self, content: str) -> str:
        """Base64编码"""
        return base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    def _decode_content(self, content: str) -> str:
        """Base64解码"""
        return base64.b64decode(content).decode('utf-8')
    
    def _calculate_checksum(self, data: dict) -> str:
        """计算数据校验和"""
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    # ==================== 核心文件同步 ====================
    
    def pull_core(self):
        """拉取核心灵魂文件"""
        print("🔄 拉取核心文件...")
        
        core_files = ['SOUL.md', 'IDENTITY.md', 'USER.md', 'MEMORY.md']
        
        for filename in core_files:
            data = self._github_request('GET', f'core/{filename}')
            if data:
                content = self._decode_content(data['content'])
                
                # 保存到本地
                Path('基础设定').mkdir(exist_ok=True)
                if filename == 'MEMORY.md':
                    filepath = Path('MEMORY.md')
                else:
                    filepath = Path('基础设定') / filename
                
                filepath.write_text(content, encoding='utf-8')
                print(f"  ✅ {filename}")
            else:
                print(f"  ⚠️  {filename} 不存在")
        
        print("✅ 核心文件拉取完成")
    
    def push_core(self):
        """推送核心灵魂文件"""
        print("🔄 推送核心文件...")
        
        files_to_push = {
            'core/SOUL.md': Path('基础设定/SOUL.md'),
            'core/IDENTITY.md': Path('基础设定/IDENTITY.md'),
            'core/USER.md': Path('USER.md'),
            'memory/MEMORY.md': Path('MEMORY.md')
        }
        
        for remote_path, local_path in files_to_push.items():
            if not local_path.exists():
                print(f"  ⚠️  本地文件不存在: {local_path}")
                continue
            
            content = local_path.read_text(encoding='utf-8')
            
            # 检查远程是否存在
            existing = self._github_request('GET', remote_path)
            
            data = {
                'message': f'Update {remote_path} via Hermes Sync v2',
                'content': self._encode_content(content)
            }
            if existing:
                data['sha'] = existing['sha']
            
            result = self._github_request('PUT', remote_path, data)
            if result:
                print(f"  ✅ {remote_path}")
            else:
                print(f"  ❌ {remote_path} 推送失败")
        
        print("✅ 核心文件推送完成")
    
    # ==================== Session管理 ====================
    
    def session_start(self, platform: str, context: str = '') -> str:
        """
        开始新会话
        
        Returns:
            session_id: 会话唯一标识
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session_index = {
            'session_id': session_id,
            'platform': platform,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'message_count': 0,
            'chunks': [],
            'status': 'active',
            'context': context
        }
        
        # 保存到GitHub
        path = f'sessions/index/active/{session_id}.json'
        data = {
            'message': f'Start session {session_id}',
            'content': self._encode_content(json.dumps(session_index, indent=2))
        }
        
        result = self._github_request('PUT', path, data)
        if result:
            print(f"✅ Session started: {session_id}")
            return session_id
        else:
            raise Exception("Failed to start session")
    
    def session_store_chunk(self, session_id: str, messages: List[dict], 
                           platform: str, chunk_num: int = 1) -> dict:
        """
        存储会话分块
        
        Args:
            session_id: 会话ID
            messages: 消息列表
            platform: 平台标识
            chunk_num: 块序号
        
        Returns:
            chunk信息
        """
        chunk_id = f"{session_id}_{chunk_num:03d}"
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # 构建chunk数据
        start_msg_id = messages[0].get('id', 1)
        end_msg_id = messages[-1].get('id', len(messages))
        
        chunk_data = {
            'chunk_id': chunk_id,
            'session_id': session_id,
            'platform': platform,
            'message_range': [start_msg_id, end_msg_id],
            'message_count': len(messages),
            'checksum': self._calculate_checksum({'messages': messages}),
            'prev_chunk': f"{session_id}_{chunk_num-1:03d}" if chunk_num > 1 else None,
            'next_chunk': None,
            'status': 'complete',
            'timestamp_start': messages[0].get('timestamp', datetime.now().isoformat()),
            'timestamp_end': messages[-1].get('timestamp', datetime.now().isoformat()),
            'messages': messages
        }
        
        # 保存chunk
        chunk_path = f'sessions/raw/{date_str.replace("-", "/")}/{chunk_id}.json'
        result = self._github_request('PUT', chunk_path, {
            'message': f'Store chunk {chunk_id}',
            'content': self._encode_content(json.dumps(chunk_data, indent=2))
        })
        
        if not result:
            raise Exception(f"Failed to store chunk {chunk_id}")
        
        # 更新session索引
        index_path = f'sessions/index/active/{session_id}.json'
        existing = self._github_request('GET', index_path)
        
        if existing:
            session_index = json.loads(self._decode_content(existing['content']))
            session_index['chunks'].append(f"{chunk_num:03d}")
            session_index['message_count'] = end_msg_id
            session_index['end_time'] = datetime.now().isoformat()
            
            self._github_request('PUT', index_path, {
                'message': f'Update session {session_id}',
                'content': self._encode_content(json.dumps(session_index, indent=2)),
                'sha': existing['sha']
            })
        
        print(f"✅ Chunk stored: {chunk_id} ({len(messages)} messages)")
        
        return {
            'chunk_id': chunk_id,
            'next_chunk_num': chunk_num + 1,
            'next_start_msg': end_msg_id + 1
        }
    
    def session_end(self, session_id: str, summary: str = '', keywords: List[str] = None):
        """
        结束会话
        
        Args:
            session_id: 会话ID
            summary: 会话摘要
            keywords: 关键词列表
        """
        # 获取活跃session
        active_path = f'sessions/index/active/{session_id}.json'
        existing = self._github_request('GET', active_path)
        
        if not existing:
            raise Exception(f"Active session not found: {session_id}")
        
        session_index = json.loads(self._decode_content(existing['content']))
        session_index['status'] = 'complete'
        session_index['end_time'] = datetime.now().isoformat()
        session_index['summary'] = summary
        session_index['keywords'] = keywords or []
        
        # 移动到completed目录
        completed_path = f'sessions/index/completed/{session_id}.json'
        self._github_request('PUT', completed_path, {
            'message': f'Complete session {session_id}',
            'content': self._encode_content(json.dumps(session_index, indent=2))
        })
        
        # 保存摘要
        if summary:
            date_str = session_index['start_time'][:10].replace('-', '/')
            summary_path = f'sessions/summaries/{date_str}/{session_id}_summary.md'
            summary_content = f"""# Session Summary: {session_id}

## Platform
{session_index['platform']}

## Duration
{session_index['start_time']} ~ {session_index['end_time']}

## Messages
{session_index['message_count']} messages

## Summary
{summary}

## Keywords
{chr(10).join(f'- {k}' for k in (keywords or []))}
"""
            self._github_request('PUT', summary_path, {
                'message': f'Add summary for {session_id}',
                'content': self._encode_content(summary_content)
            })
        
        # 更新主索引
        self._update_main_index(session_index)
        
        print(f"✅ Session ended: {session_id}")
    
    def _update_main_index(self, session_index: dict):
        """更新主索引"""
        index_path = 'sessions/index/session_index.json'
        existing = self._github_request('GET', index_path)
        
        if existing:
            main_index = json.loads(self._decode_content(existing['content']))
        else:
            main_index = {
                'version': '1.0.0',
                'sessions': [],
                'keywords_index': {},
                'total_sessions': 0
            }
        
        # 更新或添加session
        sessions = main_index['sessions']
        existing_idx = next((i for i, s in enumerate(sessions) 
                           if s['session_id'] == session_index['session_id']), -1)
        
        index_entry = {
            'session_id': session_index['session_id'],
            'platform': session_index['platform'],
            'start_time': session_index['start_time'],
            'end_time': session_index['end_time'],
            'message_count': session_index['message_count'],
            'status': session_index['status'],
            'keywords': session_index.get('keywords', [])
        }
        
        if existing_idx >= 0:
            sessions[existing_idx] = index_entry
        else:
            sessions.append(index_entry)
        
        # 更新关键词索引
        for keyword in session_index.get('keywords', []):
            if keyword not in main_index['keywords_index']:
                main_index['keywords_index'][keyword] = []
            if session_index['session_id'] not in main_index['keywords_index'][keyword]:
                main_index['keywords_index'][keyword].append(session_index['session_id'])
        
        main_index['last_updated'] = datetime.now().isoformat()
        main_index['total_sessions'] = len(sessions)
        
        data = {
            'message': 'Update main session index',
            'content': self._encode_content(json.dumps(main_index, indent=2))
        }
        if existing:
            data['sha'] = existing['sha']
        
        self._github_request('PUT', index_path, data)
    
    def session_query(self, platform: str = None, date: str = None, 
                     keyword: str = None, limit: int = 50) -> List[dict]:
        """
        查询会话
        
        Args:
            platform: 平台筛选
            date: 日期筛选 (YYYY-MM-DD)
            keyword: 关键词筛选
            limit: 返回数量限制
        """
        index_path = 'sessions/index/session_index.json'
        existing = self._github_request('GET', index_path)
        
        if not existing:
            return []
        
        main_index = json.loads(self._decode_content(existing['content']))
        sessions = main_index.get('sessions', [])
        
        if platform:
            sessions = [s for s in sessions if s['platform'] == platform]
        
        if date:
            sessions = [s for s in sessions if s['start_time'].startswith(date)]
        
        if keyword:
            sessions = [s for s in sessions 
                      if any(keyword.lower() in k.lower() for k in s.get('keywords', []))]
        
        return sessions[:limit]
    
    def session_restore(self, session_id: str, last_n: int = 50) -> dict:
        """
        恢复会话上下文
        
        Args:
            session_id: 会话ID
            last_n: 恢复最近N条消息
        
        Returns:
            会话数据
        """
        # 查找session索引
        for status in ['completed', 'active']:
            path = f'sessions/index/{status}/{session_id}.json'
            existing = self._github_request('GET', path)
            if existing:
                break
        
        if not existing:
            raise Exception(f"Session not found: {session_id}")
        
        session_index = json.loads(self._decode_content(existing['content']))
        date_str = session_index['start_time'][:10].replace('-', '/')
        
        # 计算需要加载的chunks
        chunks_to_load = (last_n + 49) // 50  # 向上取整
        recent_chunks = session_index['chunks'][-chunks_to_load:]
        
        messages = []
        for chunk_num in recent_chunks:
            chunk_path = f'sessions/raw/{date_str}/{session_id}_{chunk_num}.json'
            chunk_data = self._github_request('GET', chunk_path)
            if chunk_data:
                chunk = json.loads(self._decode_content(chunk_data['content']))
                messages.extend(chunk['messages'])
        
        return {
            'session_id': session_id,
            'platform': session_index['platform'],
            'message_count': len(messages),
            'messages': messages[-last_n:]
        }
    
    def verify_continuity(self, session_id: str) -> dict:
        """
        验证会话连续性
        
        Returns:
            验证结果
        """
        # 查找session
        for status in ['completed', 'active']:
            path = f'sessions/index/{status}/{session_id}.json'
            existing = self._github_request('GET', path)
            if existing:
                break
        
        if not existing:
            return {'error': f'Session not found: {session_id}'}
        
        session_index = json.loads(self._decode_content(existing['content']))
        date_str = session_index['start_time'][:10].replace('-', '/')
        
        issues = []
        last_message_id = 0
        
        for chunk_num in session_index['chunks']:
            chunk_path = f'sessions/raw/{date_str}/{session_id}_{chunk_num}.json'
            chunk_data = self._github_request('GET', chunk_path)
            
            if not chunk_data:
                issues.append(f"Missing chunk: {chunk_num}")
                continue
            
            chunk = json.loads(self._decode_content(chunk_data['content']))
            start_id, end_id = chunk['message_range']
            
            if last_message_id != 0 and start_id != last_message_id + 1:
                issues.append(f"Gap before chunk {chunk_num}: expected {last_message_id + 1}, got {start_id}")
            
            last_message_id = end_id
        
        return {
            'session_id': session_id,
            'status': 'healthy' if not issues else 'issues_found',
            'total_chunks': len(session_index['chunks']),
            'issues': issues
        }


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("""
Hermes Sync Client v2.0

用法:
  python3 sync_client_v2.py pull          # 拉取核心文件
  python3 sync_client_v2.py push          # 推送核心文件
  python3 sync_client_v2.py verify        # 验证配置
  
Session管理:
  python3 sync_client_v2.py session-start <platform> [context]
  python3 sync_client_v2.py session-store <session_id> <chunk_num> <messages_json>
  python3 sync_client_v2.py session-end <session_id> [summary] [keywords_json]
  python3 sync_client_v2.py session-query [platform] [date] [keyword]
  python3 sync_client_v2.py session-restore <session_id> [last_n]
  python3 sync_client_v2.py verify-session <session_id>
        """)
        sys.exit(0)
    
    client = HermesSyncClient()
    cmd = sys.argv[1]
    
    if cmd == 'pull':
        client.pull_core()
    elif cmd == 'push':
        client.push_core()
    elif cmd == 'verify':
        print(f"✅ 配置验证通过")
        print(f"   Owner: {client.owner}")
        print(f"   Repo: {client.repo}")
    elif cmd == 'session-start':
        platform = sys.argv[2] if len(sys.argv) > 2 else 'unknown'
        context = sys.argv[3] if len(sys.argv) > 3 else ''
        session_id = client.session_start(platform, context)
        print(f"Session ID: {session_id}")
    elif cmd == 'session-store':
        session_id = sys.argv[2]
        chunk_num = int(sys.argv[3])
        messages = json.loads(sys.argv[4])
        platform = sys.argv[5] if len(sys.argv) > 5 else 'unknown'
        result = client.session_store_chunk(session_id, messages, platform, chunk_num)
        print(json.dumps(result, indent=2))
    elif cmd == 'session-end':
        session_id = sys.argv[2]
        summary = sys.argv[3] if len(sys.argv) > 3 else ''
        keywords = json.loads(sys.argv[4]) if len(sys.argv) > 4 else []
        client.session_end(session_id, summary, keywords)
    elif cmd == 'session-query':
        platform = sys.argv[2] if len(sys.argv) > 2 else None
        date = sys.argv[3] if len(sys.argv) > 3 else None
        keyword = sys.argv[4] if len(sys.argv) > 4 else None
        results = client.session_query(platform, date, keyword)
        print(json.dumps(results, indent=2))
    elif cmd == 'session-restore':
        session_id = sys.argv[2]
        last_n = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        result = client.session_restore(session_id, last_n)
        print(json.dumps(result, indent=2))
    elif cmd == 'verify-session':
        session_id = sys.argv[2]
        result = client.verify_continuity(session_id)
        print(json.dumps(result, indent=2))
    else:
        print(f"❌ 未知命令: {cmd}")
        sys.exit(1)


if __name__ == '__main__':
    main()


    def session_resume(self, last_n: int = 30) -> dict:
        """恢复上一个会话（读取 .last_session_id）"""
        last_id_path = 'sessions/.last_session_id'
        existing = self._github_request('GET', last_id_path)
        
        if not existing:
            print("📭 没有上一个会话记录")
            return {}
        
        session_id = self._decode_content(existing['content']).strip()
        if not session_id:
            print("📭 .last_session_id 为空")
            return {}
        
        # 清除标记
        self._github_request('DELETE', last_id_path, {
            'message': 'Clear last session id',
            'sha': existing['sha']
        })
        
        print(f"🔄 恢复上一个会话: {session_id}")
        return self.session_restore(session_id, last_n)
