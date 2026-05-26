# Session 提取 - 交易实践

- **来源 Session:** 1dbb3991-d919-49aa-8419-5f5c3e5cf53a
- **提取日期:** 2026-05-27
- **类型:** 实战记录

---


我是 Trading Assistant，船上的交易分析员。主要职责：
- 📊 市场数据分析与技术分析
- 📈 交易策略研究与回测
- ⚠️ 风险评估与提示
- 📰 市场资讯整理

2. **实现 SQLite TokenStore** — 交易记录+Token持久化
3. **基础飞书消息响应** — @Agent 持仓/分析/帮助

- 交易记录 CRUD + 统计分析
- 信号日志记录
- 反思记录管理
- 自动建表 + 索引

**可用指令：** 持仓 / 分析 / 信号 / 平仓 / 反思 / 日报 / 状态 / 帮助

- ✅ 三级风控（技术止损/时间止损/资金止损/熔断）
- ✅ 固定风险比例仓位计算（3%风险，50%最大仓位）
- ✅ SQLite持久化（交易/信号/反思）
- ✅ 飞书8个交互指令
- ✅ 集成到OpenClaw Skill

System: - **决策类**: 决定、决策、策略、交易计划、平仓、开仓
System: - **知识类**: 学习、学到、理解、明白了
System: - **错误类**: 错误、失败、不要、避免、注意、警告
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


---
*自动提取 by knowledge-extract.sh*
