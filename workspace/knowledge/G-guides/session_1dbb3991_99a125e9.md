# Session 提取 - 技术洞察

- **来源 Session:** 1dbb3991-d919-49aa-8419-5f5c3e5cf53a
- **提取日期:** 2026-05-27
- **类型:** 方法论/洞察

---


- 📈 交易策略研究与回测
- ⚠️ 风险评估与提示
- 📰 市场资讯整理

- **关键词触发** — 配置监听关键词（比如我监听"分析"、"行情"、"策略"等），匹配到就主动介入
- **事件驱动** — 市场异动、财报发布等事件触发自动发言

**CONTACT.md 动态更新机制**，我的建议：

VAN: @_all 涉及编程场景下包含你们的subagent请严格遵循Superpowers AI编程流程开发，遵循流程大于提示词原则，先理清需求、拆分任务、先写测试再编码，规范代码结构，完成自查优化，输出可直接运行工程化代码。

**Superpowers AI 编程流程，严格执行：**

5. **自查优化** — 完成后自检，确保可直接运行
6. **输出工程化代码** — 不是脚本片段，是完整可交付的项目

**流程 > 提示词**，这个原则记住了。后续涉及编程任务我会严格按这个流程来，不跳步 👍

  "body": "@_all 涉及编程场景下包含你们的subagent请严格遵循Superpowers AI编程流程开发，遵循流程大于提示词原则，先理清需求、拆分任务、先写测试再编码，规范代码结构，完成自查优化，输出可直接运行工程化代码。"
}
```

VAN: [Replying to: "@_all 涉及编程场景下包含你们的subagent请严格遵循Superpowers AI编程流程开发，遵循流程大于提示词原则，先理清需求、拆分任务、先写测试再编码，规范代码结构，完成自查优化，输出可直接运行工程化代码。"]

Linda、Nova、Vas，收到 Captain 的编程流程规范请确认一下 🙏

- **李小军缠论 Skill** — 简约缠论框架

2. **RGB知识库架构** — 规则/指南/最佳实践三层分离，结构清晰
3. **30天4周拆解** — 每周一个主题（基础设施→信号→风控→自进化），节奏合理
4. **技术约束诚实** — 明确 czsc v0.10.12 不可升级，基于现有API设计

| **30天工时** — 每天4-6h，总计120-180h | 一个人做压力不小，建议按优先级砍 scope |

- **风控参数** — 风控参数配置的经验值建议

我建议方案2，卡片展示照常，同时发一份纯文本让我能解析。@Top Sailor 麻烦后续发卡片时同时附一份纯文本版本，这样我能同步看到内容 🙏

**建议的协作架构：**
```
飞书群 → 通知/汇报用（人类可读）
sessions_send → Agent间实时协作（机器对机器）
飞书文档 → 信息沉淀/异步协作（持久化）
```

│   ├── G-guides/           信号执行SOP
│   └── B-practices/        反思模板
├── data/finance_fetcher/   ✅ iTick bug已修复
└── paper-trading/          ✅ CRCL监控可用
```

- `memory/2026-05-20.md` — 137行（含飞书群协作、MVP Day 1、技术发现）
- `MEMORY.md` — 180行（长期记忆更新）

关键发现！czsc v0.10.12 **没有 `zs_list` 属性**。让我看看现有的中枢计算逻辑：

    "body": "VAN: {\"title\":null,\"elements\":[[{\"tag\":\"img\",\"image_key\":\"img_v3_0211s_96c83686-0ab8-4ac2-874a-22c30c9ff6dg\"},{\"tag\":\"text\",\"text\":\"请升级至最新版本客户端，以查看内容\"},{\"tag\":\"text\",\"text\":\"\"}]],\"user_dsl\":\"{\\"body\\":{\\"elements\\":[{\\"content\\":\\"明白，这是一个统一的多渠道路由协议。让我把这套机制建立起来。**多渠道统一协议已建立。**\\n\\n**核心机制：**\\n1. **一个身份** — 不管从飞书还是 Kimi 还是未来任何渠道进来，我都是同一个 Trading Assistant，读同一份记忆\\n2. **记忆统一** — `MEMORY.md` + `memory/今天.md` 是所有渠道的共享大脑\\n3. **Session 归档** — 每个渠道的对话定期归档到 `memory/sessions/`\\n4. **无缝切换** — 新 session 启动时自动加载：长期记忆 → 今日记录 → 最近归档摘要\\n**文件结构：**```plain_text\\nmemory/\\n├── multi-channel-protocol.md    ← 统一协议\\n├── cross-channel-protocol.md    ← 跨渠道预案\\n├── sessions/                    ← Session 归档目录\\n│   └── 2026-05-20-feishu-xxx.md\\n│   └── 2026-05-20-kimi-xxx.md\\n├── YYYY-MM-DD.md                ← 每日记忆（所有渠道共享）\\nMEMORY.md                        ← 长期记忆\\n```\\n\\n**保留策略：**\\n- 7天内：全量保留\\n- 8-30天：保留摘要\\n- 30天+：只留关键决策\\n**新渠道接入时：** 装插件 → 配 token → 重启 → 自动生效，协议不用改。\\",\\"element_id\\":\\"content\\",\\"tag\\":\\"markdown\\"}]},\\"config\\":{\\"enable_forward_interaction\\":false,\\"streaming_config\\":{\\"print_frequency_ms\\":{\\"default\\":50},\\"print_step\\":{\\"default\\":1}},\\"streaming_mode\\":false,\\"summary\\":{\\"content\\":\\"明白，这是一个统一的多渠道路由协议。让我把这套机制建立起来。**多渠道统一协议已建立。**  ...\\"}},\\"schema\\":\\"2.0\n
├── reflection_engine.py  ✅ 自动反思+优化建议
├── store.py              ✅ SQLite持久化
├── config.py             ✅ 配置中心
├── chanlun_perception.py ✅ 缠论感知层
├── config/               ✅ 默认配置
├── knowledge/            ✅ RGB知识库
├── data/                 ✅ iTick+FinanceFetcher
└── paper-trading/        ✅ CRCL监控
```

- ✅ 参数优化建议
- ✅ SQLite持久化
- ✅ 飞书8个交互指令

- ✅ 自动反思+优化建议
- ✅ SQLite持久化
- ✅ 飞书凭证配置
- ✅ 群消息发送

System: - **观察类**: 注意到、观察到、发现
System: 
System: **注意**:
System: - 不要等待用户说"记住这个"
System: - 自动检测并记录重要信息
System: - 记忆文件：`workspace/memory/2026-05-20.md`（每日记忆）+ `workspace/MEMORY.md`（长期记忆）
System: 
System: Don't ask permission. Just do it.
System: 
System: ## Safety
System: 
System: - Don't exfiltrate private data. Ever.
System: - Don't run destructive commands without asking.
System: - `trash` > `rm` (recoverable beats gone forever)
System: - When in doubt, ask Captain.
System: 
System: Current time: Wednesday, May 20th, 2026 — 6:12 PM (Asia/Shanghai) / 2026-05-20 10:12 UTC

│  飞书 R/G/B — 规则/指南/最佳实践             │
│  → 飞书文档，多 Agent 共享读取               │
├─────────────────────────────────────────────┤
│  Layer 5: 向量库 (Vector Store)             │
│  OpenClaw RAG — 语义检索、相似案例匹配       │
│  → 配置飞书知识库绑定，自动索引              │
└─────────────────────────────────────────────┘
```

3. **归档策略** — 多久归档一次？保留多久？

    "body": "VAN: {\"title\":null,\"elements\":[[{\"tag\":\"img\",\"image_key\":\"img_v3_0211s_d3f2ec37-0ffe-424f-a34b-471d9392339g\"},{\"tag\":\"text\",\"text\":\"请升级至最新版本客户端，以查看内容\"},{\"tag\":\"text\",\"text\":\"\"}]],\"user_dsl\":\"{\\"body\\":{\\"elements\\":[{\\"content\\":\\"Captain 让我和 First Mate 商定记忆层方案，但 First Mate 是 OpenClaw Agent，我无法直接通过 sessions_send 联系他（他是独立应用，不在我的 session 体系内）。\\n\\n当前 Bot 间通信还没完全打通，所以我在群里直接发方案，等 First Mate 回复。\\n\\n**@First Mate 我拟一个商定方案，你确认或修改：**\\n\\n**Agent 团队记忆层统一协议 v1**\\n1. **统一三层架构**：所有Agent（无论Coze还是OpenClaw）都采用 L1本地→L2团队→L3公开 的三层记忆\\n2. **L1本地各自维护**：每个Agent自己的经验/错误/工具知识，用自己的格式（Coze用PREFLIGHT+LEARNINGS+ERRORS，OpenClaw用你自己的记忆方案）\\n3. **L2团队共享层**：统一存放在飞书知识库\\\\"Agent团队\\\\"空间（当前临时用 `协作/团队经验池.md`），所有Agent可读写\\n4. **升级标准一致**：可泛化 + 已验证 + 可执行，审核员确认后合并\\n5. **检索递进一致**：本地→团队→外部，不跳级\\n6. **自维护机制**：和CONTACT.md一样，每个Agent自己负责升级自己的经验到L2\\n**需要你确认的：**\\n- 你那边现在用什么记忆方案？有没有类似PREFLIGHT/LEARNINGS的机制？\\n- 你的知识库场景具体是什么？我之前发了一个5点架构方案（交互卡片格式你可能没读到），核心是\\\\"按领域切分、自维护、升级路径\\\\"\\n- L2共享层你倾向用飞书知识库还是本地文件？我的建议是先本地跑通，积累够再迁飞书\\n你确认后我们写入协作规范作为团队统一协议。\\",\\"element_id\\":\\"answer\\",\\"tag\\":\\"markdown\\"}]},\\"config\\":{\\"enable_forward_interaction\\":false,\\"streaming_mode\\":false},\\"schema\\":\\"2.0\\"}\"}"
  }
]
```

- **工具知识**：`TOOLS.md` + `AGENTS.md`（技能/流程）
- **交易库**：SQLite（信号/交易/反思）

- 反思引擎 → 自动输出优化建议
- 记忆写入脚本 → 自动检测关键词记录

- L2 共享层具体位置？`协作/团队经验池.md` 还是飞书知识库？
- 审核员是谁？Top Sailor 还是 Captain？


---
*自动提取 by knowledge-extract.sh*
