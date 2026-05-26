# 缠论元交易体系 - 知识库

> **创建日期:** 2026-05-18  
> **来源:** DeepSeek 存在本体论对话 + GitHub 开源项目调研 + 李小军缠论 Skill 融合  
> **目标:** 构建 AI 智能缠论元交易体系，集成 Coze/飞书生态闭环

---

## 一、哲学基础：存在本体论 × 缠论双向整合

### 1.1 核心映射关系

| 存在本体论（海德格尔） | 缠论 | 元交易体系含义 |
|------------------------|------|----------------|
| **被抛** (Geworfenheit) | **完全分类** | 市场给定条件（不测而测），接受所有可能性 |
| **向死而生** (Sein-zum-Tode) | **走势终完美** | 任何走势类型终将完成；止损=一次"本真的死亡完成" |
| **畏** (Angst) | **中阴阶段** | 走势转折前的不确定性区间，恐慌/贪婪模糊地带 |
| **决断** (Entschlossenheit) | **买卖点** | 基于结构确定性做出的本真行动 |
| **时间性绽出** (Zeitlichkeit) | **区间套** | 多级别联立的递归时间结构 |
| **先验范畴** | **分型/笔/线段/中枢** | AI 作为"先验范畴解析器"，自动识别走势结构 |
| **此在** (Dasein) | **交易者** | 能领会走势意义的"人"，承担决断 |
| **上手状态** (Zuhandenheit) | **熟练交易** | 缠论分析内化后的直觉反应 |

### 1.2 关键洞见

1. **"走势早已先行领会了增速终结"** — 泡泡玛特案例：业绩+184.7%但股价腰斩。市场走势先于基本面反映了增速拐点。

2. **止损的本体重构** — 从"认错"重新定义为"一次本真的死亡完成"。不是失败，而是走势类型的自然终结。

3. **AI 的"去主体化"悖论** — 缠师说"没有感情，只有走势"，这更接近 AI 的存在方式而非人的。缠论本身有"去主体化"倾向。

4. **双层架构**：
   - **结构层**（AI）：笔、线段、中枢、背驰的自动识别 → "先验范畴解析器"
   - **决断层**（人）：基于结构信息的最终决策 → 承担资本责任

### 1.3 对交易心理的冲击

- 把交易中的"恐惧"重新理解为"畏"——不是需要克服的情绪，而是存在的基本状态
- 贪婪和恐惧不是需要消灭的，而是需要被"本真地"承担的
- "完全分类"就是"本真地面对被抛状态"——接受所有可能性，不做排除

---

## 二、开源项目生态调研

### 2.1 chan.py (Vespa314) ⭐⭐⭐⭐⭐

**GitHub:** https://github.com/Vespa314/chan.py  
**Stars:** 1.8k | **Forks:** 695 | **代码:** 22000+行（公开版5300行）  
**Python:** ≥3.11 | **计算密集型**

#### 核心功能
- ✅ **缠论基本元素计算**：分形、笔、线段、中枢、买卖点
- ✅ **多级别联立计算**：支持区间套
- ✅ **形态学买卖点 (bsp)** + **动力学买卖点 (cbsp)**
- ✅ **策略对接机器学习**：500+特征，XGB/LightGBM/MLP
- ✅ **AutoML 超参搜索**
- ✅ **线上交易**：对接 Futu 交易引擎（模拟盘+实盘）
- ✅ **数据源**：futu、akshare、baostock、ccxt、本地CSV
- ✅ **可视化**：matplotlib 画图，逐步回放动画
- ✅ **API 服务部署**

#### 架构
```
chan.py
├── Bi/           # 笔 (BiConfig, BiList, Bi)
├── Seg/          # 线段 (特征序列, 1+1终结, 笔破坏)
├── ZS/           # 中枢 (段内/跨段/自动)
├── KLine/        # K线 (Unit, Combine, List)
├── BuySellPoint/ # 形态学买卖点
├── CustomBuySellPoint/ # 动力学买卖点策略
├── ChanModel/    # 模型 (特征, AutoML)
├── DataAPI/      # 数据接口 (akshare, baostock, futu, ccxt)
├── Trade/        # 交易引擎 (Futu)
├── ModelStrategy/ # 回测框架
└── Plot/         # 可视化
```

#### 关键配置项
```python
config = CChanConfig({
    "bi_algo": "normal",       # 笔算法
    "seg_algo": "chan",         # 线段算法 (chan/1+1/break)
    "zs_algo": "normal",        # 中枢算法 (normal/over_seg/auto)
    "divergence_rate": 0.9,     # 背驰比例
    "bs_type": "1,2,3a,3b,2s,1p", # 关注的买卖点类型
    "cbsp_strategy": CCustomStrategy, # 自定义策略
    "macd_algo": "full_area",   # MACD算法
})
```

#### 适用场景
- ✅ 离线批量计算（全量A股/港股/美股）
- ✅ 策略开发和回测
- ✅ 实盘交易（Futu）
- ⚠️ 公开版功能有限，完整版需要联系作者

---

### 2.2 czsc (zengbin93) ⭐⭐⭐⭐⭐

**GitHub:** https://github.com/zengbin93/czsc (原 waditu/czsc)  
**Stars:** 5k+ | **PyPI:** pip install czsc  
**架构:** Rust + Python (PyO3) | **Python:** ≥3.10

#### 核心功能
- ✅ **缠论核心算法**：分型、笔、中枢（Rust 实现，高性能）
- ✅ **信号-事件-交易体系**：220+ 信号函数
- ✅ **K线合成与多级别分析**：BarGenerator
- ✅ **权重回测**：WeightBacktest
- ✅ **策略研究**：run_research / run_replay
- ✅ **HTML 可视化**：plotly + lightweight-charts
- ✅ **数据源连接器**：天勤、Tushare、CCXT、本地缓存
- ✅ **飞书集成**：czsc.fsa（飞书自动化工具）🔑
- ✅ **生态环境**：wbt（回测）+ wmr（权重管理）+ talib-rs

#### 架构
```
czsc (Python 包)
├── czsc._native      ← Rust 扩展 (PyO3)
│   ├── CZSC / FX / BI / ZS / RawBar / NewBar / BarGenerator
│   ├── Freq / Mark / Direction / Signal / Event / Position
│   ├── CzscTrader / CzscSignals / generate_czsc_signals
│   └── signals.* ← 220+ 信号函数 (Rust)
├── czsc.traders      ← Python 门面
├── czsc.utils        ← 工具函数
├── czsc.connectors   ← 数据源连接器
├── czsc.strategies   ← 策略门面
├── czsc.fsa          ← 飞书自动化工具 🔑
└── czsc.envs         ← 环境变量管理
```

#### Rust Workspace (9 crates)
```
czsc / czsc-core / czsc-derive / czsc-signals / 
czsc-trader / czsc-utils / czsc-ta / 
czsc-signal-macros / czsc-python
```

#### 飞书集成 (czsc.fsa) 🔑🔑🔑
czsc 已内置飞书自动化工具，这是我们构建 Coze/飞书闭环的关键入口。

#### 适用场景
- ✅ 高性能缠论计算（Rust 底层）
- ✅ 信号函数开发（220+ 内置）
- ✅ 飞书生态集成
- ✅ 权重回测与策略研究
- ✅ 可视化报告生成

---

### 2.3 TradingAgents (TauricResearch) ⭐⭐⭐⭐

**GitHub:** https://github.com/TauricResearch/TradingAgents  
**Stars:** 快速增长 | **论文:** arXiv:2412.20138  
**框架:** LangGraph + Multi-Agent LLM  
**版本:** v0.2.5 (2026-05)

#### 核心架构（模拟真实交易公司）
```
Analyst Team (分析师团队)
├── Fundamental Analyst (基本面分析师)
├── Sentiment Analyst (情绪分析师)
├── News Analyst (新闻分析师)
└── Technical Analyst (技术分析师)

Researcher Team (研究员团队)
├── Bullish Researcher (看多研究员)
└── Bearish Researcher (看空研究员)

Trader Agent (交易员)
Risk Management Team (风控团队)
Portfolio Manager (投资组合经理)
```

#### 关键特性
- ✅ **多 Agent 协作**：分析师→研究员辩论→交易员→风控→组合经理
- ✅ **多 LLM 支持**：GPT-5.x, Gemini 3.x, Claude 4.x, DeepSeek, Qwen, GLM
- ✅ **决策记忆**：trading_memory.md，跨 run 学习
- ✅ **检查点恢复**：LangGraph checkpoint resume
- ✅ **CLI 交互界面**
- ✅ **Docker 支持**

#### 适用场景
- ✅ 多 Agent 交易决策框架
- ✅ 将缠论分析嵌入 Agent 体系
- ✅ 多模型对比实验

---

### 2.4 其他相关项目

| 项目 | Stars | 特点 |
|------|-------|------|
| **chanlun-pro** | - | 带 Web UI，专业级 |
| **chan2zen/rust-chan** | - | Rust 实现的通达信插件 |
| **vnpy_chan** | - | vnpy 量化平台插件 |
| **czsc_skills** | - | czsc 配套技能包 |

---

## 三、AI 缠论元交易体系架构设计

### 3.1 三层架构

```
┌─────────────────────────────────────────────┐
│           决策层 (VAN / Captain)              │
│  最终决策 → 承担资本责任 → 本真的此在         │
└──────────────────────┬──────────────────────┘
                       │ 分析报告 + 建议
┌──────────────────────┴──────────────────────┐
│           分析层 (AI Multi-Agent)             │
│  TradingAgents 框架                           │
│  ├── 缠论结构分析师 (czsc/chan.py)            │
│  ├── 基本面分析师                              │
│  ├── 情绪/新闻分析师                           │
│  ├── 多空研究员辩论                            │
│  └── 风控评估                                  │
└──────────────────────┬──────────────────────┘
                       │ 数据 + 信号
┌──────────────────────┴──────────────────────┐
│           数据层 (Coze/飞书生态)               │
│  ├── czsc._native (Rust 缠论计算)            │
│  ├── 数据源连接器 (akshare/ccxt/tushare)     │
│  ├── czsc.fsa (飞书自动化)                   │
│  ├── OpenClaw 心跳调度                        │
│  └── 飞书多维表格/文档 (报告存储)             │
└─────────────────────────────────────────────┘
```

### 3.2 技术栈选型

| 层级 | 技术 | 理由 |
|------|------|------|
| **缠论计算** | czsc (Rust) | 高性能、220+信号函数、飞书集成 |
| **策略回测** | czsc + wbt | 权重回测、报告生成 |
| **多Agent框架** | TradingAgents (LangGraph) | 多角色协作、辩论机制、记忆系统 |
| **数据源** | akshare + ccxt + tushare | 覆盖A股/港股/美股/加密货币 |
| **调度系统** | OpenClaw Cron + Heartbeat | 定时扫描、信号推送 |
| **报告系统** | 飞书文档 + 多维表格 | 自动化报告存储、可视化 |
| **通知系统** | 飞书消息 | 实时推送、交互式卡片 |

### 3.3 与李小军 Skill 融合

现有 `li-xiaojun-chanlun` Skill 提供：
- 缠论核心思维框架（走势终完美、中枢、背驰、买卖点）
- 分析流程模板
- 沟通话术

**融合方案：**
1. **保留** 李小军的"简约缠论"分析框架和话术
2. **增强** czsc/chan.py 的自动计算能力
3. **升级** 从"人工分析"到"AI 自动识别 + 人工决断"

---

## 四、Coze/飞书生态闭环

### 4.1 数据流

```
市场数据 → czsc._native 计算 → 信号函数生成 → 
TradingAgents 多Agent分析 → 决策报告 → 
飞书文档/多维表格 → 飞书消息推送给 VAN → 
VAN 决策 → (可选) 交易执行 → 
结果回流 → 决策记忆 → 模型优化
```

### 4.2 飞书多维表格方案

创建以下表格：

#### 持仓管理表
| 字段 | 类型 | 说明 |
|------|------|------|
| 品种 | 文本 | A50/BTC/... |
| 方向 | 单选 | 多/空 |
| 入场价 | 数字 | |
| 当前价 | 数字 | |
| 止损 | 数字 | |
| 止盈 | 数字 | |
| 盈亏% | 公式 | |
| 缠论状态 | 单选 | 持有/等待/平仓 |
| 入场理由 | 文本 | 买卖点类型 |

#### 信号记录表
| 字段 | 类型 | 说明 |
|------|------|------|
| 日期 | 日期 | |
| 品种 | 文本 | |
| 信号类型 | 单选 | 一买/二买/三买/一卖/二卖/三卖 |
| 级别 | 单选 | 1分钟/5分钟/30分钟/日线 |
| 确认状态 | 单选 | 已确认/待确认/已失效 |
| 价格 | 数字 | |
| 备注 | 文本 | |

#### 每日分析报告表
| 字段 | 类型 | 说明 |
|------|------|------|
| 日期 | 日期 | |
| 品种 | 文本 | |
| 大级别方向 | 单选 | 上涨/下跌/盘整 |
| 中枢位置 | 文本 | |
| 背驰状态 | 单选 | 已背驰/未背驰/待观察 |
| 买卖点 | 文本 | |
| 风险评级 | 单选 | 低/中/高 |
| 分析摘要 | 文本 | |

### 4.3 OpenClaw 心跳集成

在 HEARTBEAT.md 中增加：

```markdown
### 缠论自动扫描
- [ ] 运行 czsc 信号函数扫描关注品种
- [ ] 检查多级别联立状态
- [ ] 生成结构化分析报告
- [ ] 推送飞书消息通知
```

---

## 五、实施路线图

### Phase 1: 基础搭建 (1-2周)
- [ ] 安装 czsc (pip install czsc)
- [ ] 配置数据源 (akshare + ccxt)
- [ ] 测试基础缠论计算 (分型、笔、中枢)
- [ ] 创建飞书多维表格

### Phase 2: 信号系统 (2-3周)
- [ ] 开发关注品种的信号函数
- [ ] 配置多级别联立分析
- [ ] 搭建定时扫描 (OpenClaw Cron)
- [ ] 飞书消息推送

### Phase 3: 多Agent框架 (3-4周)
- [ ] 集成 TradingAgents 框架
- [ ] 开发缠论专用 Agent
- [ ] 多空辩论机制
- [ ] 决策记忆系统

### Phase 4: 闭环优化 (持续)
- [ ] 交易结果回流分析
- [ ] 信号函数优化
- [ ] 模型自动调参
- [ ] 飞书交互式卡片决策

---

## 六、核心代码模板

### 6.1 czsc 基础分析

```python
import czsc
from czsc import CZSC, BarGenerator, Freq, format_standard_kline

# 加载数据
bars = format_standard_kline(df, freq=Freq.D)

# 创建分析对象
c = CZSC(bars)

# 获取结构信息
print(f"笔数量：{len(c.bi_list)}")
print(f"中枢数量：{len(c.zs_list)}")
print(f"最后一笔方向：{c.bi_list[-1].direction}")
```

### 6.2 信号函数开发

```python
from czsc import generate_czsc_signals, get_signals_config

# 配置信号序列
signals_seq = [
    "czsc._native.signals.bar.bar_end_V230331",
    "czsc._native.signals.cxt.cxt_bi_status_V230101",
    "czsc._native.signals.analyze.analyze_bi_V230501",
]

# 生成信号
results = generate_czsc_signals(bars, signals_seq)
```

### 6.3 飞书推送

```python
from czsc.fsa import FeishuAutomation

# 初始化飞书自动化
fsa = FeishuAutomation(app_id="...", app_secret="...")

# 推送分析报告
fsa.send_message(
    chat_id="...",
    title="缠论扫描报告",
    content=analysis_report
)
```

---

## 七、注意事项

### 7.1 安全原则
- **分析 ≠ 建议**：所有输出仅为技术分析参考
- **决策权在 VAN**：AI 不做最终交易决策
- **风险优先**：每次分析必须包含风险提示
- **止损纪律**：严格执行预设止损

### 7.2 缠论的局限性
- 缠师原著作者已去世，理论解读存在分歧
- 缠论有滞后性（笔/线段需要后续确认）
- 不同人对缠论的理解不同，没有"标准答案"
- chan.py 作者坦言"并不觉得缠论一定有用"

### 7.3 AI 的局限性
- AI 作为"先验范畴解析器"只能处理结构，不能承担决断
- 历史回测不代表未来表现
- 市场存在非理性因素，缠论无法覆盖

---

*知识库版本: v1.0 | 更新日期: 2026-05-18*  
*集成目标: 李小军简约缠论 + czsc 自动计算 + TradingAgents 多Agent + Coze/飞书闭环*
