"""
AI 运维助手 - Gradio Web 界面
两个核心功能：
1. 运维命令/脚本生成器
2. 日志智能分析
"""
import os
import gradio as gr
from llm_client import LLMClient

client = LLMClient()

# ===== 系统提示模板 =====

SCRIPT_SYSTEM_PROMPT = """你是一个专业的Linux运维工程师。你的任务是将用户的中文自然语言请求转化为准确、可用的Shell脚本或命令。

规则：
1. 输出必须是完整的、可直接运行的脚本
2. 包含必要的注释和错误处理
3. 重要参数使用变量，方便用户修改
4. 包含使用说明（用法、依赖）
5. 对危险操作（rm -rf、dd等）必须有警告
6. 输出格式：代码块 + 说明

如果用户请求不明确，先问清楚再写脚本。"""

LOG_SYSTEM_PROMPT = """你是一个日志分析专家。分析用户提供的日志内容，给出：
1. 发现的问题（分级：🔴关键 / 🟡警告 / 🔵信息）
2. 根因分析
3. 具体的修复命令或操作步骤

注意：不要泛泛而谈，要根据日志中的具体信息做分析。"""


# ===== 功能函数 =====

def generate_script(query: str, history: list) -> tuple:
    """生成运维脚本"""
    if not query.strip():
        return history, ""
    response = client.chat(SCRIPT_SYSTEM_PROMPT, query)
    history = history or []
    history.append((query, response))
    return history, ""


def analyze_log(log_input: str, history: list) -> tuple:
    """分析日志"""
    if not log_input.strip():
        return history, ""
    response = client.chat(LOG_SYSTEM_PROMPT, log_input)
    history = history or []
    history.append((log_input[:50] + ("..." if len(log_input) > 50 else ""), response))
    return history, ""


def clear_history() -> tuple:
    """清空对话历史"""
    return [], []


# ===== 预设示例 =====

SCRIPT_EXAMPLES = [
    "帮我写一个监控磁盘使用率的脚本，超过80%发告警",
    "写一个每天自动备份 /var/www 目录到 /backup 的脚本",
    "写一个检查 Nginx 状态的脚本",
    "写一个清理 Docker 无用资源的脚本",
    "监控CPU负载并找出高占用的进程",
    "写一个日志轮转（logrotate）配置",
]

LOG_EXAMPLES = """[ERROR] 2025-04-24 10:23:15 - DBConnectionPool: Connection timed out after 30s
[ERROR] 2025-04-24 10:23:46 - DBConnectionPool: Failed to connect to 192.168.1.100:3306
[WARN] 2025-04-24 10:20:01 - Disk usage on /var/lib/docker: 87%
[INFO] 2025-04-24 10:22:00 - Service healthcheck passed for api-gateway
[ERROR] 2025-04-24 10:25:01 - DBConnectionPool: Max pool size reached (50/50)"""

SSH_LOG_EXAMPLE = """Apr 24 03:15:22 server sshd[12345]: Failed password for root from 61.177.172.140 port 52341 ssh2
Apr 24 03:15:24 server sshd[12346]: Failed password for root from 61.177.172.140 port 52342 ssh2
Apr 24 03:15:26 server sshd[12347]: Failed password for root from 61.177.172.140 port 52343 ssh2"""

OOM_LOG_EXAMPLE = """Apr 24 08:30:01 server kernel: java invoked oom-killer: gfp_mask=0x100cca, order=1
Apr 24 08:30:01 server kernel: oom-kill: process=java, pid=15432, total_vm=5242880
Apr 24 08:30:01 server kernel: Memory cgroup out of memory: Killed process 15432"""

# ===== 构建界面 =====

CSS = ".gradio-container { height: 100vh; overflow-y: auto !important; }"

with gr.Blocks(title="AI 运维助手", css=CSS) as demo:
    gr.Markdown("""
    # 🖥️ AI 运维助手

    面向 Linux 运维工程师的 AI 工具，支持：
    - **命令/脚本生成**：自然语言描述 → 可运行的 Shell 脚本
    - **日志智能分析**：粘贴日志 → 根因分析 + 修复方案

    > 当前模式：**演示模式**（内置示例数据）
    > 配置 .env 中的 LLM_BACKEND 可切换为真实模型
    """)

    with gr.Tabs():
        # ===== Tab 1: 脚本生成 =====
        with gr.TabItem("📜 脚本生成器"):
            with gr.Row():
                with gr.Column(scale=2):
                    chatbot_script = gr.Chatbot(
                        label="对话记录",
                        height=400,
                    )
                    query_input = gr.Textbox(
                        label="输入你的需求",
                        placeholder="例如：帮我写一个监控磁盘使用率的脚本...",
                        lines=2,
                    )
                    with gr.Row():
                        submit_btn = gr.Button("🚀 生成脚本", variant="primary")
                        clear_btn = gr.Button("🗑️ 清空对话")

            # 绑定事件
            submit_btn.click(
                generate_script,
                inputs=[query_input, chatbot_script],
                outputs=[chatbot_script, query_input],
            )
            query_input.submit(
                generate_script,
                inputs=[query_input, chatbot_script],
                outputs=[chatbot_script, query_input],
            )
            clear_btn.click(
                clear_history,
                outputs=[chatbot_script, query_input],
            )

        # ===== Tab 2: 日志分析 =====
        with gr.TabItem("🔍 日志分析器"):
            with gr.Row():
                with gr.Column(scale=2):
                    chatbot_log = gr.Chatbot(
                        label="分析记录",
                        height=400,
                    )
                    log_input = gr.Textbox(
                        label="粘贴日志内容",
                        placeholder="粘贴系统日志、应用日志或访问日志...",
                        lines=8,
                    )
                    with gr.Row():
                        analyze_btn = gr.Button("🔎 分析日志", variant="primary")
                        clear_log_btn = gr.Button("🗑️ 清空记录")

                with gr.Column(scale=1):
                    gr.Markdown("### 示例日志")
                    gr.Examples(
                        examples=[
                            [LOG_EXAMPLES],
                            [SSH_LOG_EXAMPLE],
                            [OOM_LOG_EXAMPLE],
                        ],
                        inputs=[log_input],
                        label="点击加载示例",
                    )

            analyze_btn.click(
                analyze_log,
                inputs=[log_input, chatbot_log],
                outputs=[chatbot_log, log_input],
            )
            log_input.submit(
                analyze_log,
                inputs=[log_input, chatbot_log],
                outputs=[chatbot_log, log_input],
            )
            clear_log_btn.click(
                clear_history,
                outputs=[chatbot_log, log_input],
            )

    gr.Markdown("""
    ---
    ### 💡 使用提示
    - **演示模式**：当前使用内置示例数据，功能可正常展示
    - **切换真实模型**：复制 `.env.example` 为 `.env`，设置 `LLM_BACKEND=openrouter` 并填入 API Key
    - **资源**：项目源码在 `~/projects/ai-ops-assistant/`
    """)


if __name__ == "__main__":
    PORT = int(os.getenv("APP_PORT", "7860"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    demo.launch(server_port=PORT, debug=DEBUG, server_name="0.0.0.0", css=CSS)
