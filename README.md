# AI Ops Assistant

**AI 运维助手** — 面向 Linux 运维教学的 AI 辅助工具。

自然语言描述需求 → 自动生成可运行的 Shell 脚本，支持智能日志分析。

## 功能

### 📜 脚本生成器
输入中文描述，自动生成完整的运维脚本：
- 磁盘监控与告警
- 自动备份方案
- Nginx 状态检查
- Docker 资源清理
- CPU 负载分析
- 日志轮转配置

### 🔍 日志分析器
粘贴系统日志，自动分析根因并给出修复方案：
- SSH 暴力破解检测
- 数据库连接故障分析
- OOM Killer 分析
- 应用错误日志诊断

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env
python3 app.py
# http://localhost:7860
```

## 架构

支持三种运行模式，通过环境变量 `LLM_BACKEND` 切换：

| 模式 | 说明 |
|:----|:------|
| `demo` | 演示模式，内置示例数据，无需 GPU/API |
| `ollama` | 本地模型模式，需 Ollama + GPU |
| `openrouter` | 云端模型模式，需 API Key |

## 项目结构

```
ai-ops-assistant/
├── app.py           # Gradio Web 界面
├── llm_client.py    # LLM 客户端抽象层
├── requirements.txt # Python 依赖
├── .env.example     # 配置模板
└── README.md
```

## License

MIT
