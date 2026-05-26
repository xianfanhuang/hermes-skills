# 🔄 一键恢复

## 从任何平台恢复

```bash
# 一行搞定
curl -sL https://raw.githubusercontent.com/xianfanhuang/ai-trading-sync/main/scripts/full-restore.sh | bash
```

## 或者手动恢复

```bash
# 1. 克隆备份
git clone git@github.com:xianfanhuang/ai-trading-sync.git /workspace/projects/workspace

# 2. 运行恢复脚本
bash /workspace/projects/workspace/scripts/full-restore.sh
```

## 日常使用

```bash
# 搜索记忆和知识库
bash memory-cli.sh search "止损"

# 查看系统状态
bash memory-cli.sh status

# 自动记忆更新
bash memory-cli.sh auto-memory

# 同步到云端
bash memory-cli.sh sync
```

## 平台无关

- ✅ 纯bash实现，无需Node.js/Python
- ✅ 只需bash + grep + git
- ✅ 任何Linux/macOS/WSL都能运行
- ✅ 一行命令搞定一切
