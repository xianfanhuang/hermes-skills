#!/usr/bin/env python3
import os, sys, json, base64
from datetime import datetime

class HermesSync:
    def __init__(self, token, owner, repo="hermes-sync"):
        self.token = token
        self.owner = owner
        self.repo = repo
    
    def _api(self, method, endpoint, data=None):
        import urllib.request
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/{endpoint}"
        req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
            headers={"Authorization": f"token {self.token}", "Accept": "application/vnd.github.v3+json"},
            method=method)
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            return {"error": str(e)}
    
    def pull(self):
        """拉取核心文件和 MEMORY"""
        for file in ["SOUL.md", "IDENTITY.md", "USER.md"]:
            r = self._api("GET", f"contents/core/{file}")
            if "content" in r:
                content = base64.b64decode(r["content"]).decode()
                os.makedirs("core", exist_ok=True)
                with open(f"core/{file}", "w") as f:
                    f.write(content)
                print(f"✅ core/{file}")
        
        r = self._api("GET", "contents/memory/MEMORY.md")
        if "content" in r:
            with open("MEMORY.md", "w") as f:
                f.write(base64.b64decode(r["content"]).decode())
            print("✅ MEMORY.md")
    
    def push(self):
        """推送 MEMORY"""
        r = self._api("GET", "contents/memory/MEMORY.md")
        sha = r.get("sha")
        with open("MEMORY.md", "r") as f:
            content = f.read()
        b64 = base64.b64encode(content.encode()).decode()
        data = {"message": f"Update {datetime.now().isoformat()}", "content": b64}
        if sha:
            data["sha"] = sha
        r = self._api("PUT", "contents/memory/MEMORY.md", data)
        print("✅ 已推送" if "content" in r else f"❌ {r.get('message')}")

if __name__ == "__main__":
    token = os.getenv("GITHUB_TOKEN") or (sys.argv[2] if len(sys.argv) > 2 else None)
    owner = os.getenv("GITHUB_OWNER", "xianfanhuang")
    if not token:
        print("请设置 GITHUB_TOKEN 环境变量")
        sys.exit(1)
    sync = HermesSync(token, owner)
    if "--pull" in sys.argv:
        sync.pull()
    elif "--push" in sys.argv:
        sync.push()
    else:
        print("用法: python3 sync_client.py --pull|--push [TOKEN]")
