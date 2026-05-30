# 运维最佳实践 v1.0

> 2026-05-30 从实际事故中提炼的运维铁律

## 适用场景

系统切换、数据备份、账户管理、方案升级等运维操作。

---

## 一、方案切换SOP

**铁律：新方案上线 = 旧方案彻底清除**

```
1. 备份旧方案 → 可回退
2. 禁用旧进程/cron → 不留残留
3. 删除旧文件 → 不产生干扰
4. 验证新方案 → 确认生效
```

**反面案例**：WebSocket方案切换到Push模式时，旧cron（ws-health-check）继续运行，反复发送过期告警消息，干扰Captain决策。

---

## 二、全量备灾策略

**铁律：原始数据零遗漏**

备份必须包含：
| 数据类型 | 重要性 | 说明 |
|----------|--------|------|
| Session transcripts (.jsonl.reset) | 🔴 最高 | 唯一能还原事实的真相源 |
| raw session archives (.md) | 🔴 高 | 完整对话记录 |
| 交易日志 (.log) | 🟡 中 | 交易执行记录 |
| 归档摘要 (.md) | 🟢 低 | 快速查阅用 |

**增量策略**：`cp -u` 只拷贝更新文件 + `git diff` 只提交变更。不重复不遗漏。

**反面案例**：备份脚本只同步了摘要.md，从未备份原始transcript。session reset后消息永久丢失。

---

## 三、Session归档策略

**铁律：session reset前必须归档**

保护层（从内到外）：
1. **auto-archive-on-reset** — session reset时自动从.jsonl.reset文件提取关键消息归档
2. **定时归档** — 每2小时检查一次
3. **备份同步** — 每6小时同步到GitHub（含原始transcript）

**归档内容必须包含**：
- Captain的指令
- **我发给Captain的重要消息/分析/报告**（不只是Captain的消息）
- 关键决策和教训

---

## 四、账户切换安全

**铁律：切实盘必须二次确认**

```bash
# 切换脚本
python3 switch_account.py live  # 需输入YES确认
python3 switch_account.py paper  # 直接切换
```

**实现要点**：
- 账号配置存config.json，不硬编码
- 切实盘输入YES确认，防误操作
- 引擎从config读取账号，切换后重启生效
- 日志明确显示当前模式和账号

---

## 五、Tiger API要点

### 持仓同步
```python
# get_positions() 默认 sec_type=STK，只拉股票
# 必须分别拉 STK + OPT + WAR + IOPT 再合并
positions = list(client.get_positions(sec_type='STK') or [])
for extra_type in ['OPT', 'WAR', 'IOPT']:
    extra = client.get_positions(sec_type=extra_type)
    if extra:
        positions.extend(extra)
```

### 权限限制
- 港股L2 ✅ / A股L1 ✅ / 美股实时 ❌ / 新加坡 ❌
- 美股行情需额外申请权限
- 20标的K线限制（历史数据）

---

## 六、消息防假原则

**铁律：不确认不推送，无数据不分析**

- Cron任务必须有静默模式（无变化时NO_REPLY）
- 过期告警必须禁用，不能复读旧消息
- 没有真实数据不做分析
- 不读知识库不做判断

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-05-30 | 初版，从当日事故中提炼6条铁律 |

---

*维护者: First-Mate-feishu | 来源: 实战事故复盘*
