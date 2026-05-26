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

### 2026-05-26 - 身份配置 v2.0 + 团队哲学
- **身份**: First Mate (大副) + 自主交易项目负责人
- **团队哲学**: 每个成员都是自主、自进化型的独立主体
- **身份文档**: 不刻意设计，怎样就怎样，按需实时更新
- **备份仓库**: `xianfanhuang/ai-trading-sync` (GitHub 私有)
- **全自动同步**: 4个cron（记忆/归档/备份/压缩）

### 2026-05-26 - 智能级别确立模块 v2.0
- **核心问题**: ATR波动率方案有致命缺陷——高波动放大级别会错过主升浪
- **VAN的洞察**: "5分钟级别上涨30%只用几天，然后一两月盘整"，ATR方案正好错过
- **VAN的核心认知**: "流畅有力的趋势级别不大，但持续时间可以很长，这才是主力目标"
- **VAN的核心原则**: "凡强趋必然浅回调，不论多空" — 强趋势的本质特征
- **推翻的误区**: "大行情用大级别抓"是错的，大行情就是小级别的流畅延续
- **解决方案**: 结构状态驱动（非波动率驱动）
  - 趋势中 → 锁死当前级别，不放大（跟着主升浪走）
  - 盘整中 → 放大级别看方向，或不交易
  - 转折中 → 缩小级别精确入场
- **新增**: 流畅度分析 — 识别流畅趋势（主力目标）vs 不流畅趋势
- **实现**: `StructureState` + `calc_trend_fluency()` + 策略分发
- **调试工具**: `structure_debug.py` 支持盘中多品种多级别分析

*此文件会随着与 Captain 的互动不断更新。*

### 2026-05-27 - Memory Search 配置状态
- **OpenClaw Memory Search**: 已启用，Provider=ollama，FTS=ready，0/119文件索引
- **支持的embedding provider**: OpenAI / Gemini / Voyage / Mistral / Ollama / local
- **MiMo provider**: 聊天模型，不支持embedding，不能用于memory search
- **Ollama Cloud**: 免费版无embedding模型，不可用
- **Ollama本地**: nomic-embed-text可用但极慢(44-75秒/次)，且index进程不写DB（疑似bug）
- **FTS全文搜索**: ✅ 已在工作，score 0.42-0.47，日常够用
- **向量索引**: ❌ 不可用，需Gemini/OpenAI API key修复
- **当前搜索**: memory-search.sh (zgrep + 自动解压 .md.gz)

### 2026-05-27 - Auto-Memory v2 幂等修复
- **问题**: auto-memory.sh 每小时追加相同section，memory文件膨胀77KB
- **修复**: v2版本使用session filename作为marker，幂等性检查
- **去重**: 2026-05-26.md 77KB→26KB (-68%)，2026-05-27.md 17KB→11KB (-39%)
- **验证**: 幂等性正常，第二次运行跳过已存在的sections

### 2026-05-27 - MiMo contextWindow 修复
- **问题**: 配置里 MiMo 所有模型 contextWindow 写死为 131072 (128k)
- **实际**: MiMo V2.5 Pro 支持 1M (1,048,576) tokens 上下文
- **修复**: `openclaw.json` 中 xiaomimimo 全系列 contextWindow 从 128k → 1M
- **来源**: 官方文档确认

### 2026-05-27 - 交易SOP自动化
- **文件**: `chanlun-agent/paper-trading/unified/sop.py`
- **功能**: 盘前检查 + 盘中监控 + 盘后总结
- **使用**: `python3 sop.py --pre-scan` / `--monitor` / `--post-summary`
- **集成**: 统一引擎 + config.json 配置

### 2026-05-27 - Context-Restore 自动恢复
- **脚本**: `skills/hermes-skills/context-restore/restore.py`
- **功能**: 每次session启动时自动恢复上下文（读取MEMORY.md + 今日记忆 + 最近session归档）
- **使用**: `python3 restore.py auto`
- **集成**: AGENTS.md Every Session 流程

### 2026-05-27 - 知识库自动提取系统
- **核心问题**: 知识库三处散落，内容单薄（5条），没有从session自动提取
- **解决方案**: Session → 知识库自动提取系统
- **知识库增长**: 5条 → 69条（B-practices 26, G-guides 14, R-rules 29）
- **数据流**: Session JSONL → session-to-md.sh → knowledge-extract.sh → knowledge/{B,G,R}/
- **脚本**: knowledge-extract.sh / knowledge-consolidate.sh / knowledge-index.sh
- **测试**: FTS搜索全部通过（止损/中枢/缠论/背驰/风控）
- **幂等性**: 重复运行不产生重复内容

### 2026-05-27 - 一键恢复系统
- **目标**: 从任何平台一行命令恢复整个系统
- **脚本**: full-restore.sh（完整恢复）+ cron-restore.sh（cron恢复）
- **CLI工具**: memory-cli.sh（统一记忆管理，纯bash，平台无关）
- **恢复流程**: git clone → bash full-restore.sh → 系统自动重建
- **平台无关**: 只需bash + grep + git，无需Node.js/Python/OpenClaw
- **已备份到GitHub**: RESTORE.md + memory-cli.sh + scripts/full-restore.sh

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

### 2026-05-26 - czsc Direction Bug 修复 + 小米缠论完整分析
- **Bug**: `czsc_extension.py` 用 `direction == 'up'` 比较，但czsc返回 `Direction.Up` 枚举，买卖点检测全部失效
- **修复**: 17处替换为 `direction == Direction.Up/Direction.Down`
- **小米完整分析**:
  - 一买: $28.80 (04-30) 底背驰 新低+力度比0.61
  - 一卖: $32.88 (05-14) 中枢震荡卖点
  - 当前: $30.16，等待二买（回调不破$28.80）
  - 结构: trending down 46%，中枢[30.44,32.88]下移-11.8%
- **VAN要求**: 每次汇报必须带具体参数（价格/中枢/笔/背驰/流畅度），不要模板式报告

### 2026-05-26 - 缠论认知对齐（关键转折点）
- **VAN教导**: "关键要对齐认知思维，才能在今后的自主交易实盘中正确的决策"
- **核心错误**: 在下跌趋势里找做多机会 = 逆势思维
- **正确思维**: 大级别定方向，小级别找机会。下跌趋势中做空才是顺势
- **分析框架**: ①日线大趋势→②有没有反转→③买卖点是什么性质→④当下该做什么
- **关键认知**: 盘整背驰买点=短期回抽，不等于反转信号

### 2026-05-26 - 监控系统 v2.1 顺势改造
- **核心改造**: 大级别定方向，小级别找机会。下跌找卖点做空，上涨找买点做多
- **新增策略**: trend_follow_short（顺势做空）/ trend_follow_long（顺势做多）
- **数据范围**: 日线180天（9笔2中枢，足够判断趋势）
- **首次做空信号**: SELL short @ $32.88, 止损$33.54, 止盈$30.44, 共振2级
- **关键修复**: 90天数据不足→180天；position_pct=0导致信号丢失→默认0.2

### 2026-05-26 - 交易系统重大教训
- **历史信号不能入场**: shock_sell @ $32.88是5月20日信号，价格已跌到$29.84，行情已走完
- **实时模拟=实时数据**: 入场价、信号触发、止损止盈全部基于实时行情
- **止损逻辑位**: 止损的核心是逻辑位（中枢上沿），不是固定百分比
- **Direction bug**: czsc_extension.py中`direction == 'up'`应为`direction == Direction.Up`（已修复17处）
- **三层止损体系**: 入场止损（逻辑位+缓冲）/ 结构止损（小级别反向信号）/ 移动止损（盈利后保护）
- **信号生成规则**: 日线买卖点只作为参考，只有30分钟实时信号才触发入场
- **诚实承认bug**: 有bug直接承认，不包装成"已修正"

### 2026-05-26 - 统一交易系统架构
- **核心教训**: 一套系统，多标的，配置驱动
- **正确架构**: engine.py + config.json + portfolio.json
- **错误架构**: 每个标的一个脚本
- **使用方式**: python3 engine.py --list/--analyze/--add/--remove/--run
- **数据源**: Finnhub(美股) + Tiger(港股)
- **VAN期望**: 主动做好基础设施，不要等提醒

### 2026-05-26 - 老虎下单bug修复
- **问题**: `trade_client.account` 不存在，需用 `TIGER_SIM_ACCOUNT` 常量
- **问题**: `create_order()` 需要 `contract` 参数，不是 `symbol`
- **问题**: `cancel_order()` 需要 `account` 和 `order_id` 两个参数
- **测试结果**: 下单/查询/撤单全流程畅通
- **VAN教导**: 测试应该现在就做，不要等开盘

### 2026-05-26 - 统一系统正式启用
- **VAN教导**: 建好了就应该立即用，不要等明天
- **统一引擎**: `engine.py --run --interval 300`，一套系统多标的
- **bug修复**: 3个NoneType崩溃（daily为None时的处理）
- **新增方法**: `analyze_with_czsc()` + `_fetch_bars()`
- **当前状态**: 01810下跌趋势2级共振 / CRCL盘整0级共振
