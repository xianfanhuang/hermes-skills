# /aigit 模型切换技能

## 当前配置状态

### API Keys
| Key | 用途 | 状态 |
|-----|------|------|
| V3: `4QKfGjVN-WEinGRk_Pz5-HZ8` | 主力 Key | ✅ 生效中 |
| V4: `hArvuFv1tqxS7fnos2uwuDfB` | 备用 Key | ✅ 已测试 |

### 可用模型 (GitCode)
| 模型 | ID | 定位 |
|------|-----|------|
| Qwen3.5-35B | `Qwen/Qwen3.5-35B-A3B` | 轻量快速 |
| **Qwen3.5-122B** | `Qwen/Qwen3.5-122B-A10B` | **主力 (当前)** |
| Qwen3.5-397B | `Qwen/Qwen3.5-397B-A17B` | 旗舰 (自动降级122B) |
| DeepSeek-V3.1 | `deepseek-ai/DeepSeek-V3.1` | 备用稳定 |

---

## 切换命令

### 模型切换
| 命令 | 效果 |
|------|------|
| `/aigit` | 在 Qwen ↔ Coze 之间切换 |
| `/aigit 35b` | 切换到 35B 轻量 |
| `/aigit 122b` | 切换到 122B 主力 |
| `/aigit deepseek` | 切换到 DeepSeek |
| `/aigit coze` | 切回 Coze |

### Key 切换 (手动)
当主力 Key V3 失效时，告诉我"切换到 V4 Key"，我会帮你更新。

---

## Key 轮换策略

OpenClaw 单 provider 只支持一个 apiKey，但我们可以：
1. **V3 主力** — 默认使用
2. **V4 备用** — V3 失效时手动切换

如需自动 failover，可以考虑配置多个 provider：
- `gitcode-v3` → V3 Key
- `gitcode-v4` → V4 Key

---

## API 信息
- Base URL: `https://api.gitcode.com/api/v5`
- 上下文窗口: 32000 tokens
- 最大输出: 7168 tokens
- 参数格式: 驼峰式 (maxTokens, topP 等)
