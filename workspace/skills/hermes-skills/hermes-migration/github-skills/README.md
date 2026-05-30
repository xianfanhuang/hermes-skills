# Hermes Skills

Hermes 双轨制技能仓库 —— 与核心层分离，按需加载。

## 架构

```
Hermes-Core (轻量迁移包)
    ↓ 加载
skill-manifest.json
    ↓ 按需clone
Hermes-Skills (本仓库)
```

## 使用

### 新环境初始化

```bash
# 1. 加载必需技能
python3 skill_loader.py

# 2. 加载所有技能
python3 skill_loader.py --all

# 3. 加载指定技能
python3 skill_loader.py --skill token-budget-manager
```

### 列出可用技能

```bash
python3 skill_loader.py --list
```

## 技能清单

| 技能 | 版本 | 优先级 | 说明 |
|-----|------|--------|------|
| hermes-migration | 2.0 | 100 | 迁移系统 |
| token-budget-manager | 2.1 | 90 | 轻量预算管理 |

## 版本管理

- 每个skill独立版本
- Git tag格式: `skill-name-vx.x.x`
- manifest自动追踪版本

## 开发规范

1. 每个skill必须有SKILL.md，包含version字段
2. 敏感信息不进仓库（API key等）
3. 更新后及时打tag
