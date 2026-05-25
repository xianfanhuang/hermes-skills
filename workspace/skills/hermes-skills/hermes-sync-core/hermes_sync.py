#!/usr/bin/env python3
"""
Hermes Sync Client v2 - 高级同步客户端
支持 GitHub Token 和 GitHub App Token
"""
import os
import sys
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime

class HermesSyncV2:
    def __init__(self, token=None, owner="xianfanhuang", repo="hermes-sync"):
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
        self.owner = owner
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        
        # 检测 Token 类型
        if self.token and self.token.startswith("github_pat_"):
            self.auth_header = f"Bearer {self.token}"  # GitHub App Token
        else:
            self.auth_header = f"token {self.token}"   # Classic Token
    
    def _api(self, method, endpoint, data=None):
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith("http") else endpoint
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode() if data else None,
            headers={
                "Authorization": self.auth_header,
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "HermesSync/2.0"
            },
            method=method
        )
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            return {"error": str(e), "code": e.code, "details": error_body}
        except Exception as e:
            return {"error": str(e)}
    
    def verify(self):
        """验证 Token 和仓库访问"""
        print("🔑 验证连接...")
        user = self._api("GET", "https://api.github.com/user")
        if "login" in user:
            print(f"✅ Token 有效: {user['login']}")
        else:
            print(f"❌ Token 无效: {user.get('error')}")
            return False
        
        repo = self._api("GET", "")
        if "full_name" in repo:
            print(f"✅ 仓库访问: {repo['full_name']}")
            return True
        else:
            print(f"⚠️  仓库访问受限: {repo.get('error')}")
            return False
    
    def pull_all(self):
        """拉取所有核心文件"""
        print("\n📥 拉取核心文件...")
        files = ["SOUL.md", "IDENTITY.md", "USER.md"]
        for file in files:
            r = self._api("GET", f"contents/core/{file}")
            if "content" in r:
                content = base64.b64decode(r["content"]).decode()
                os.makedirs("core", exist_ok=True)
                with open(f"core/{file}", "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  ✅ core/{file}")
            else:
                print(f"  ❌ core/{file}: {r.get('error', 'Unknown')}")
        
        print("\n📥 拉取 MEMORY...")
        r = self._api("GET", "contents/memory/MEMORY.md")
        if "content" in r:
            with open("MEMORY.md", "w", encoding="utf-8") as f:
                f.write(base64.b64decode(r["content"]).decode())
            print("  ✅ MEMORY.md")
        
        print("\n📥 拉取同步状态...")
        r = self._api("GET", "contents/memory/sync.json")
        if "content" in r:
            status = json.loads(base64.b64decode(r["content"]).decode())
            print(f"  📊 最后同步: {status.get('last_sync')}")
            print(f"  📍 平台: {status.get('platform')}")
    
    def push_memory(self, message=None):
        """推送 MEMORY"""
        print("\n📤 推送 MEMORY...")
        
        if not os.path.exists("MEMORY.md"):
            print("  ❌ MEMORY.md 不存在")
            return False
        
        # 获取当前 SHA
        r = self._api("GET", "contents/memory/MEMORY.md")
        sha = r.get("sha")
        
        # 读取并编码
        with open("MEMORY.md", "r", encoding="utf-8") as f:
            content = f.read()
        
        b64 = base64.b64encode(content.encode()).decode()
        msg = message or f"Update from {os.getenv('PLATFORM', 'unknown')} at {datetime.now().isoformat()}"
        
        data = {
            "message": msg,
            "content": b64
        }
        if sha:
            data["sha"] = sha
        
        r = self._api("PUT", "contents/memory/MEMORY.md", data)
        if "content" in r:
            print("  ✅ 推送成功")
            self._update_sync_status()
            return True
        else:
            print(f"  ❌ 推送失败: {r.get('error')}")
            return False
    
    def _update_sync_status(self):
        """更新同步状态"""
        status = {
            "last_sync": datetime.now().isoformat(),
            "platform": os.getenv("PLATFORM", "unknown"),
            "version": "2.0"
        }
        
        r = self._api("GET", "contents/memory/sync.json")
        sha = r.get("sha")
        
        b64 = base64.b64encode(json.dumps(status, indent=2).encode()).decode()
        data = {
            "message": f"Sync status update from {status['platform']}",
            "content": b64
        }
        if sha:
            data["sha"] = sha
        
        self._api("PUT", "contents/memory/sync.json", data)
    
    def quick_backup(self, filename, content):
        """快速备份内容到 updates/"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = f"memory/updates/{timestamp}-{filename}.md"
        
        b64 = base64.b64encode(content.encode()).decode()
        data = {
            "message": f"Quick backup: {filename}",
            "content": b64
        }
        
        r = self._api("PUT", f"contents/{path}", data)
        if "content" in r:
            print(f"  ✅ 备份: {path}")
            return True
        return False

def main():
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
    if not token and len(sys.argv) > 1:
        token = sys.argv[1]
    
    if not token:
        print("请设置 GITHUB_TOKEN 或 GITHUB_PAT 环境变量")
        sys.exit(1)
    
    sync = HermesSyncV2(token)
    
    if "--verify" in sys.argv:
        sync.verify()
    elif "--pull" in sys.argv:
        sync.pull_all()
    elif "--push" in sys.argv:
        sync.push_memory()
    elif "--sync" in sys.argv:
        sync.pull_all()
        sync.push_memory()
    else:
        print("Hermes Sync Client v2")
        print("用法:")
        print("  python3 hermes_sync.py --verify   # 验证连接")
        print("  python3 hermes_sync.py --pull     # 拉取所有")
        print("  python3 hermes_sync.py --push     # 推送 MEMORY")
        print("  python3 hermes_sync.py --sync     # 双向同步")

if __name__ == "__main__":
    main()
