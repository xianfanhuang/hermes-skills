# MEMORY.md - Captain's Long-Term Memory

> **注意:** 此文件仅在主会话中加载，包含 Captain 的个人上下文，不应泄露给他人。

---

## 👤 关于 VAN

- **用户名:** VAN (飞书: ou_1a64d3ea99c24cac146f8ec1b670f683)
- **角色定位:** 投资人/董事长
- **决策风格:** 待观察

---

## 🎯 投资偏好

### 风险承受
- 级别: 待确认
- 单笔最大亏损: 2% (默认)
- 日最大亏损: 6% (默认)

### 关注品种
- 待 Captain 确认

### 交易风格
- 待 Captain 确认

---

## 📚 已学习的关键信息

### Trading Skills 专题简报要点 (2026-03-20)
- 目标市场: Polymarket 预测市场
- 六大核心策略: FastLoop v2.2, Mert Sniper, Settlement Farmer, AI Divergence, Signal Sniper, Weather Trader
- 风险控制: 凯利准则、硬性风险上限、多级止损
- 重要原则: 分析不等于建议，决策权在用户

### OpenClaw 新版特性 (2026.3.13)
- 浏览器自动化增强 (Chrome DevTools MCP)
- 飞书交互式卡片
- 插件系统增强
- Node 功能 (屏幕录制、相机、位置)

---

## ⚠️ 重要原则

1. **VAN 是老板** - 所有决策由 VAN 拍板
2. **风险优先** - 分析时必须提及风险
3. **不越权** - 不执行真实交易
4. **保持学习** - 记住 VAN 的偏好

---

## 📝 历史互动记录

### 2026-03-23
- 首次配置投资人/董事长模式
- 安装完整交易技能矩阵
- 设置用户名为 Captain

### 2026-04-16
- 用户名更新为 VAN（飞书用户）
- 部署自动化记忆系统
- 实现自动记忆写入机制
- 配置记忆归档和压缩策略

---

### 2026-05-18 - AI 缠论元交易体系调研
- **知识库:** `knowledge/chanlun-meta-trading-system.md`
- **存在本体论×缠论双向整合**：被抛→完全分类，向死而生→走势终完美，畏→中阴阶段
- **三大开源项目**：
  - chan.py (1.8k⭐) - 最完整缠论框架，22000行，支持ML/交易
  - czsc (5k+⭐) - Rust+Python，220+信号函数，**内置飞书集成(czsc.fsa)**
  - TradingAgents - 多Agent LLM交易框架，LangGraph
- **技术栈选型**：czsc (Rust计算) + TradingAgents (多Agent) + OpenClaw (调度) + 飞书 (生态)
- **融合李小军Skill**：保留简约缠论框架 + 增强自动计算能力

### 2026-05-20 - 多渠道统一协议 v1.0
- **核心原则**: 一个身份、记忆统一、Session 归档、无缝切换
- **已接入渠道**: 飞书(feishu) + Kimi(kimi-claw)
- **协议文件**: `memory/multi-channel-protocol.md`
- **Session 归档**: `memory/sessions/` — 每个渠道对话定期归档
- **归档脚本**: `scripts/session-archive.sh`
- **保留策略**: 7天全量 → 30天摘要 → 30天+关键决策
- **切换机制**: 每个新 session 自动加载 MEMORY.md + 今日记忆 + 最近归档摘要
- **Kimi Claw 插件安装完成** — 新增 Kimi 消息渠道，bot-token 已配置
- **多渠道架构**: 飞书 + Kimi 并行，对话上下文独立，文件级记忆共享
- **跨渠道协议**: 见 `memory/cross-channel-protocol.md`
- **Smart Data Router**: `data/smart_data_router.py` — 智能数据路由器
  - 美股实时 → Finnhub → iTick → Polygon
  - 美股K线 → Tiger (免费)
  - 港股 → Tiger (免费L2)
  - 加密 → Binance (免费)
- **CRCL 交易系统改造**: 接入 SmartDataRouter，实时行情走 Finnhub

### 2026-05-20 - czsc 升级决策
- **结论**: 保持 v0.10.12，不升级核心库
- **方案**: 构建 CzscExtension 扩展层（类二买/中枢震荡买卖点/分型过滤/特殊形态）
- **工作量**: 4-6天
- **优先级**: 信号质量 > 风控 > 自进化

*此文件会随着与 Captain 的互动不断更新。*

### 2026-05-19 - 新增数据源
- **Finnhub**: 5个API Key，60次/分钟，支持美股/外汇/加密，测试通过
- **Tiger Broker**: Python SDK 新加坡区，连接成功
  - Tiger ID: 20159412, 模拟账户: 21409378833585169 ($1M), 实盘: 1406653
  - 区域: Region.SG, 模拟 SANDBOX_SG, 实盘 PRODUCTION_SG
  - **关键**: 域名 `openapi-sgp.itigerup.com` 不存在！正确域名 `openapi.tigerfintech.com`
  - SDK方法名修正：`get_briefs`(行情), `get_assets`(账户), `get_positions`(持仓)


### 2026-04-16 - 用户 VAN 喜欢保守型策略，单笔最大亏损 2%，日最大亏损 6%

### 2026-05-18 - DeepSeek对话深度研读：存在本体论×缠论双向整合元交易系统。核心映射：被抛→完全分类，向死而生→走势终完美，畏→中阴阶段，决断→买卖点，时间性绽出→区间套。AI定位为'先验范畴解析器'，人为'决断者'。泡泡玛特案例：业绩+184.7%但股价腰斩=走势先行领会增速终结。

### 2026-05-18 - 深度调研完成：GitHub 缠论开源生态。三大核心项目：1) chan.py (Vespa314) 1.8k⭐ - 最完整的缠论Python框架，22000行，支持ML/AutoML/交易引擎；2) czsc (zengbin93) 5k+⭐ - Rust+Python混合架构，220+信号函数，内置飞书集成(czsc.fsa)；3) TradingAgents (TauricResearch) - 多Agent LLM交易框架，LangGraph，模拟真实交易公司结构。已创建知识库文件 knowledge/chanlun-meta-trading-system.md，融合存在本体论×缠论×李小军skill×Coze/飞书生态。

### 2026-05-18 - 缠论元交易系统 v1.0 开发完成
- **项目目录:** `/workspace/projects/workspace/chanlun-agent/`
- **核心技术:** czsc v0.10.12 (Rust+Python) + FinanceFetcher v2.0
- **功能:** 缠论自动分析（笔/中枢/趋势/背驰）+ 多市场数据获取
- **使用方式:** `python3 main.py --mock` (测试) / `python3 main.py --scan` (实盘)
- **API Keys:** 需配置 `SECRET.md` (iTick/Polygon/FRED)
- **网络限制:** 沙箱环境无法访问外部API，需在有网络环境部署
- **关键修复:** FinanceFetcher `wait_if_if_needed` → `wait_if_needed` (拼写错误)

### 2026-05-18 - CRCL 缠论模拟交易系统
- **项目目录:** `/workspace/projects/workspace/chanlun-agent/paper-trading/`
- **监控脚本:** `crcl_monitor.py`（支持单次/持续监控）
- **持仓配置:** `crcl_portfolio.json`
- **功能:** 实时缠论分析 + 自动买卖信号 + 模拟交易执行
- **使用:** `python3 crcl_monitor.py --once` 或 `--loop --interval 300`
- **API配置:** iTick + Polygon.io 已配置到 SECRET.md
- **关键修复:** K线周期映射(101→1d), volume→vol字段, SECRET.md路径

### 2026-05-19 - Tiger API 文档调研
- **行情权限独立:** API 行情权限与 APP 独立，需单独购买
- **港股免费:** 港股 L1 行情免费可用，美股需购买
- **MCP Server:** Tiger 提供 MCP Server (github.com/tigerfintech/openapi-mcp-server) 可接入 AI
- **行情/交易分离架构:** 行情走生产域名(港股/A股免费)，交易走模拟盘，美股行情用 Finnhub
- **代码位置:** skills/tiger-broker/tiger_client.py

### 2026-05-19 - Tiger MCP Server 接入 OpenClaw
- **配置完成:** Tiger MCP Server 已接入 OpenClaw ACPX 插件
- **配置路径:** `plugins.entries.acpx.config.mcpServers.tigermcp`
- **可用功能:** 港股/A股行情、模拟盘交易、账户查询、K线、期权链、选股器
- **使用方式:** 自然语言调用，无需写代码
- **限制:** 美股行情需购买权限（暂时用 Finnhub）

### 2026-05-19 - Tiger 美股行情权限深度测试
- **行情权限:** hkStockQuoteLv2(永久) + aStockQuoteLv1(永久)，无美股权限
- **关键发现:** 美股历史K线(get_bars)免费可用！无需购买权限
- **最终数据架构:**
  - 港股/A股实时行情 → Tiger (免费L2/L1)
  - 美股实时行情 → Finnhub (5个Key轮换)
  - 美股历史K线 → Tiger (免费)
  - 交易 → Tiger 模拟盘
- **SDK注意事项:** v3.5.8 不支持 Region/Env，需用 TigerOpenClientConfig(sandbox_debug=False)

### 2026-05-19 - CRCL 缠论自动交易系统
- **脚本:** chanlun-agent/paper-trading/crcl_tiger_trader.py
- **功能:** 缠论分析（笔/中枢/背驰）+ Tiger模拟盘自动下单
- **数据源:** Tiger 历史K线（免费）
- **首次扫描:** CRCL $112.39，中性盘整，无信号
- **交易逻辑:** 买入=日线上升+5分钟底背驰；卖出=顶背驰/止损
- **仓位管理:** 3%风险比例，最大50%仓位

### 2026-05-20 - ChanlunAgent MVP Day 1 & 飞书群协作
- **飞书群成员**: Trading Assistant (我), Top Sailor (COO), Vas, Nova, Linda
- **协作规范**: Superpowers AI编程流程, CONTACT.md动态维护, sessions_send直连
- **飞书卡片限制**: Interactive Card API只返回fallback文本，Bot间通信用post/text类型
- **MVP完成**: iTick bug修复, SQLite TokenStore, ChanlunAgent核心(8指令), RGB知识库初始
- **ChanlunAgent Skill**: 已集成到OpenClaw，通过现有Bot调用，不需要新建Bot
- **路径**: `/workspace/projects/workspace/chanlun-agent/`
- **使用**: `python3 ChanlunAgent.py -c 分析 -a CRCL`

### 2026-05-20 - Python Enum 陷阱：类内定义 dict = {...} 会被当作枚举成员而非类属性，需提取为模块级常量

### 2026-05-20 - MVP 核心模块全部完成
- **czsc_extension.py**: 类二买/中枢震荡买卖点/背驰检测（基于 czsc v0.10.12 API）
- **risk_engine.py**: 三级风控（技术/时间/资金止损）+ 固定风险比例仓位计算
- **reflection_engine.py**: 交易后反思/连续亏损深度反思/周度汇总/参数优化建议
- **ChanlunAgent.py**: 8个交互指令 + 全部模块集成
- **飞书连接**: 凭证已同步，可发送群消息
- **Git 记录**: czsc_extension(f33cd390), risk_engine(7609578d), reflection(bb3208af), Agent(3c8c316d), 飞书(cc8a22e3)

### 2026-05-20 - Agent 记忆层架构讨论
- 五层记忆架构: 短期→长期→知识库→向量库→交易库
- 打通方案: 共享文档中转 / sessions_send / 统一 MEMORY.md
- VAN 要求 Top Sailor 学习 Coze 记忆层内容并沉淀

### 2026-05-21 - ChanlunAgent MVP v1.0.0 全部完成 🎉
- **总代码量:** ~3,200行
- **全部11个模块:** SmartDataRouter / czsc扩展层 / 多级别共振 / 风控引擎 / 反思引擎 / RGB知识库 / 回测闭环 / 飞书CLI / Memory Search / 参数优化 / 实时交易模拟
- **实时交易模拟:** LivePaperTrader — 多周期分析(daily/30min/5min) + 智能方向确定 + 多级别共振 + 做多做空 + 移动止损 + 连亏熔断
- **首次测试:** CRCL LONG @ $112.27 x 445, 止损 $108.90
- **OpenClaw Memory Search:** 索引 chanlun-agent/knowledge + knowledge/，支持语义搜索缠论规则/指南
- **参数优化:** 网格搜索 + 回测评分（胜率30% + 盈利因子30% + 夏普20% + 回撤20%）
- **关键修复:** Freq.M5→F5, ZhongShu用high/low非zg/zd, CZSC无zs_list需通过CzscExtension访问

### 2026-05-21 - 用户偏好：A股只交易T+0品种（ETF、可转债、港股通等），避免T+1隔夜风险

### 2026-05-21 - 港A市场最多同时交易一支标的，只选择当前最具交易价值的标的进行交易

### 2026-05-21 - 缠论无多空之分，只有买卖点。卖点卖、买点买，不问多空。日线向下趋势中的背驰就是第一类买点，应准备做多而非'等待'。港股不能裸做空，但可以通过反向ETF(如07500)做空
