# Hermes GitHub 同步方案 - 轻量移动办公版

## 核心理念

**版本 B = 核心灵魂文件 + GitHub API 实时同步**

- 不打包项目文件（太大、变动频繁）
- 启动时从 GitHub API 拉取最新 MEMORY
- 任务完成后推送关键更新回 GitHub

---

## GitHub 仓库结构

```
hermes-sync/                    # 私有仓库
├── core/                       # 核心灵魂（手动维护）
│   ├── SOUL.md
│   ├── IDENTITY.md
│   └── USER.md
├── memory/                     # 动态记忆（API 同步）
│   ├── MEMORY.md              # 主记忆文件
│   ├── updates/               # 每日更新片段
│   │   └── 2026-05-22.md
│   └── sync-marker.txt        # 最后同步时间
├── manifest.json              # 版本信息
└── README.md                  # 同步指南
```

---

## 同步机制

### 1. 启动时拉取（轻量版 Agent 使用）

```python
# 伪代码 - 新平台 Agent 启动时执行
import requests

def pull_hermes_from_github(token):
    headers = {"Authorization": f"token {token}"}
    
    # 拉取核心文件
    for file in ["SOUL.md", "IDENTITY.md", "USER.md", "MEMORY.md"]:
        url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/core/{file}"
        response = requests.get(url, headers=headers)
        content = base64.b64decode(response.json()["content"])
        save_local(file, content)
    
    return "Hermes 轻量版已恢复"
```

### 2. 关键更新推送（任务完成后）

```python
def push_memory_update(token, update_content):
    """将关键记忆更新推送到 GitHub"""
    
    # 创建新的更新文件
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    filename = f"memory/updates/{timestamp}.md"
    
    # 更新主 MEMORY.md
    # 提交到 GitHub
    pass
```

---

## 平台适配策略

| 能力 | Coze OpenClaw | MiMo 平台 | 轻量版处理 |
|------|---------------|-----------|-----------|
| **文件系统** | ✅ 完整 | ⚠️ 云端目录 | 仅核心 md 文件 |
| **联网搜索** | ✅ | ⚠️ 待验证 | 如果有就使用 |
| **GitHub API** | ✅ | ✅ 应该有 | 主要同步方式 |
| **日程系统** | ✅ Calendar | ⚠️ 待验证 | 简化版或手动 |
| **飞书集成** | ✅ | ❌ 不支持 | 无法在 MiMo 使用 |
| **邮件分身** | ✅ | ⚠️ 待验证 | 简化版 |

---

## 使用流程

### 场景：在 MiMo 上快速办公

```
1. 启动 MiMo Agent
   ↓
2. Agent 读取本地 00-INSTRUCTION.md
   ↓
3. 从 GitHub API 拉取最新 SOUL + IDENTITY + USER + MEMORY
   ↓
4. 恢复 Hermes 核心上下文（约 30 秒）
   ↓
5. 接收任务，使用 MiMo-V2.5 模型执行
   ↓
6. 任务完成后，关键更新推送到 GitHub
   ↓
7. 下次 Coze/MiMo 启动时自动同步
```

---

## 关键设计决策

### 1. 为什么不同步整个项目文件夹？

- **太大**：项目文件夹 30MB+，每次拉取慢
- **变动频繁**：代码、日志、临时文件不断变化
- **平台差异**：不同平台的文件路径、权限不同
- **非核心**：真正的"你"是记忆和思维，不是项目文件

### 2. 什么必须同步？

| 文件 | 同步方式 | 原因 |
|------|---------|------|
| SOUL.md | GitHub core/ | 灵魂设定，极少变动 |
| IDENTITY.md | GitHub core/ | 外在呈现，极少变动 |
| USER.md | GitHub core/ | 主人画像，定期更新 |
| MEMORY.md | GitHub memory/ | 工作状态，每日同步 |
| SECRET.md | ❌ 不同步 | 各平台各自维护凭证 |

### 3. 冲突解决

如果两边同时修改了 MEMORY.md：
1. 以时间戳最新的为准
2. 保留历史版本在 updates/ 目录
3. 合并时人工确认关键决策

---

## MiMo 平台具体适配

### 已知信息

- **MiMo API**: https://platform.xiaomimimo.com
- **模型**: MiMo-V2.5, MiMo-V2.5-Pro（性能强、成本低）
- **当前优惠**: 100T Token 免费活动
- **OpenClaw 集成**: 社区已有 MiMo 适配（GitHub 搜 xiaomi-mimo）

### 待验证清单

在 MiMo 上测试以下内容：

- [ ] 是否有文件系统（读取/写入本地文件）
- [ ] 是否有联网搜索工具
- [ ] 是否能调用外部 API（GitHub API）
- [ ] 会话时长限制（1小时？）
- [ ] 是否支持多轮工具调用
- [ ] 是否有日程/定时任务系统

---

## 实施步骤

### Phase 1: 建立 GitHub 仓库（今天）

1. 创建私有仓库 `hermes-sync`
2. 上传核心文件（SOUL.md, IDENTITY.md, USER.md）
3. 创建 GitHub Personal Access Token
4. 测试 API 拉取/推送

### Phase 2: 验证 MiMo 能力（明天）

1. 用 Token Plan 登录 MiMo 平台
2. 测试文件系统、联网搜索、API 调用
3. 记录能力矩阵

### Phase 3: 实现同步脚本（本周）

1. 编写 `sync_from_github.py`（拉取）
2. 编写 `sync_to_github.py`（推送）
3. 集成到 00-INSTRUCTION.md 启动流程

### Phase 4: 双平台并行（持续）

- Coze: 复杂任务、飞书集成、长期运行
- MiMo: 轻量查询、模型测试、成本优化

---

## 核心原则

> **Hermes 在 GitHub，不在任何平台**
> 
> **平台只是 Harness，随时可以换**
> 
> **轻量版让你不死守单一阵地**

