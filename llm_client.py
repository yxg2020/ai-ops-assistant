"""
AI 运维助手 - LLM 接口层
支持三种后端：OpenRouter, Ollama, Demo（内置示例数据）
"""
import os
import json
import random
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

BACKEND = os.getenv("LLM_BACKEND", "demo")


class LLMClient:
    """统一的 LLM 调用接口"""

    def __init__(self):
        self.backend = BACKEND
        self._client = None
        self._init_client()

    def _init_client(self):
        if self.backend == "openrouter":
            from openai import OpenAI
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key or api_key == "your_key_here":
                print("[WARN] OpenRouter API key not configured, falling back to demo")
                self.backend = "demo"
                return
            self._client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
            )
            self._model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
        elif self.backend == "ollama":
            from openai import OpenAI
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            self._client = OpenAI(
                api_key="ollama",
                base_url=f"{base_url}/v1",
            )
            self._model = os.getenv("OLLAMA_MODEL", "llama3.2")
        elif self.backend == "demo":
            pass  # 使用内置示例数据

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """发送对话并返回回复"""
        if self.backend == "demo":
            return self._demo_response(system_prompt, user_prompt)

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[错误] API 调用失败: {str(e)}"

    def _match_keyword(self, query: str, *keywords) -> bool:
        """增强关键词匹配：支持同义词和中英文混合"""
        q = query.lower()
        for kw in keywords:
            if kw.lower() in q:
                return True
        return False

    def _demo_response(self, system_prompt: str, user_prompt: str) -> str:
        """
        演示模式：基于规则返回示例回复
        使用扩展关键词匹配，确保多种表述方式都能命中
        """
        query = user_prompt.lower()

        # --- 脚本生成 ---
        if self._match_keyword(query, "磁盘", "disk", "存储", "硬盘", "存储空间", "空间", "df"):
            return self._demo_script("disk_monitor")

        elif self._match_keyword(query, "cpu", "负载", "处理器", "性能"):
            return self._demo_script("cpu_monitor")

        elif self._match_keyword(query, "内存", "mem", "memory", "ram"):
            return self._demo_script("memory_monitor")

        elif self._match_keyword(query, "备份", "backup", "存档", "归档"):
            return self._demo_script("backup")

        elif self._match_keyword(query, "nginx", "njinx", "web服务", "网站"):
            return self._demo_script("nginx_check")

        elif self._match_keyword(query, "docker", "容器"):
            return self._demo_script("docker_cleanup")

        elif self._match_keyword(query, "日志", "log", "排查", "分析", "问题"):
            return self._demo_script("log_analyzer")

        # --- 日志分析（根据日志内容自动判断） ---
        if self._match_keyword(query, "error", "failed to connect", "timed out", "dbconnectionpool"):
            return self._demo_log("error_analysis")
        elif self._match_keyword(query, "ssh", "failed password", "brute force"):
            return self._demo_log("ssh_fail")
        elif self._match_keyword(query, "oom", "killed", "out of memory"):
            return self._demo_log("oom_analysis")
        elif self._match_keyword(query, "403", "权限", "forbidden"):
            return self._demo_log("permission_403")

        # --- 如果同时有脚本类关键词和日志类关键词，优先按系统提示判断 ---
        if "系统提示" in user_prompt or "log_system" in system_prompt.lower():
            return self._demo_log("error_analysis")

        # 通用回复
        return self._demo_script("general")

    # ============ 预置脚本数据 ============

    def _demo_script(self, script_type: str) -> str:
        scripts = {
            "disk_monitor": """#!/bin/bash
# 磁盘使用率监控脚本 - 超过阈值时发告警
# 用法: ./disk_monitor.sh [阈值%] [邮箱]

THRESHOLD=${1:-80}
EMAIL=${2:-admin@example.com}
HOSTNAME=$(hostname)
DATE=$(date '+%Y-%m-%d %H:%M:%S')

df -h | grep -vE '^Filesystem|tmpfs|devtmpfs' | awk '{print $5 " " $1 " " $6}' | while read output; do
    USAGE=$(echo $output | awk '{print $1}' | sed 's/%//g')
    PARTITION=$(echo $output | awk '{print $3}')
    FILESYSTEM=$(echo $output | awk '{print $2}')

    if [ $USAGE -ge $THRESHOLD ]; then
        echo "[$DATE] 警告: 分区 $PARTITION ($FILESYSTEM) 使用率已达 ${USAGE}%"
        echo "磁盘使用率告警 - $HOSTNAME - $PARTITION 使用率 ${USAGE}%" | mail -s "磁盘告警" $EMAIL

        echo "  建议操作:"
        echo "  - 查找大文件: find $PARTITION -xdev -type f -size +100M 2>/dev/null"
        echo "  - 清理日志: journalctl --vacuum-time=7d"
        echo "  - 清理Docker: docker system prune -f"
    fi
done

echo "=== 磁盘使用率概览 ==="
df -h | grep -vE '^Filesystem|tmpfs|devtmpfs' | awk '{printf "%-20s %-10s %s\\n", $1, $5, $6}'
""",
            "cpu_monitor": """#!/bin/bash
# CPU 负载监控脚本

THRESHOLD=${1:-2.0}
INTERVAL=${2:-5}

echo "监控CPU负载 (阈值: $THRESHOLD)..."

while true; do
    LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | tr -d ' ')
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4}')

    echo "$(date '+%H:%M:%S') | 负载: $LOAD | CPU使用: ${CPU_USAGE}%"

    if (( $(echo "$LOAD > $THRESHOLD" | bc -l) )); then
        echo " CPU负载过高！检查占用进程:"
        ps aux --sort=-%cpu | head -10
    fi

    sleep $INTERVAL
done
""",
            "memory_monitor": """#!/bin/bash
# 内存使用监控脚本

echo "=== 内存使用情况 ==="
free -h | grep -v Swap

echo ""
echo "=== 按内存占用排序的前10个进程 ==="
ps aux --sort=-%mem | head -11 | awk '{printf "%-8s %-8s %-6s %-6s %s\\n", $1, $2, $4, $3, $11}'

echo ""
TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
USED_MEM=$(free -m | awk '/^Mem:/{print $3}')
USAGE_PERCENT=$(echo "scale=2; $USED_MEM * 100 / $TOTAL_MEM" | bc)

if (( $(echo "$USAGE_PERCENT > 90" | bc -l) )); then
    echo " 内存使用率高达 ${USAGE_PERCENT}%！建议:"
    echo "  1. 检查内存泄漏: ps aux --sort=-%rss | head -5"
    echo "  2. 清理缓存: sync && echo 3 > /proc/sys/vm/drop_caches"
fi
""",
            "backup": """#!/bin/bash
# 目录增量备份脚本 - 使用 rsync
# 用法: ./backup.sh /源目录 /目标目录

SRC=${1:-/data}
DST=${2:-/backup}
DATE=$(date '+%Y%m%d_%H%M%S')
LOG="/var/log/backup_${DATE}.log"

if [ ! -d "$SRC" ]; then
    echo "错误: 源目录 $SRC 不存在"
    exit 1
fi

mkdir -p "$DST"

echo "[$(date)] 开始备份 $SRC -> $DST" | tee -a "$LOG"

rsync -avz --delete --progress \\
    --exclude='*.tmp' \\
    --exclude='.cache/' \\
    --exclude='node_modules/' \\
    "$SRC/" "$DST/" | tee -a "$LOG"

echo ""
echo "=== 备份校验 ==="
echo "源目录大小: $(du -sh $SRC | cut -f1)"
echo "备份大小: $(du -sh $DST | cut -f1)"
""",
            "nginx_check": """#!/bin/bash
# Nginx 状态检查脚本

NGINX_BIN=$(which nginx 2>/dev/null || echo "/usr/sbin/nginx")

echo "=== Nginx 运行状态 ==="
if systemctl is-active nginx &>/dev/null; then
    echo " nginx.service: $(systemctl is-active nginx)"
else
    echo " nginx 服务未运行！"
    echo "尝试启动: systemctl start nginx"
    exit 1
fi

echo ""
echo "=== 配置语法检查 ==="
$NGINX_BIN -t 2>&1

echo ""
echo "=== 监听端口 ==="
ss -tlnp | grep -E 'nginx|:80 |:443 '

echo ""
echo "=== 反向代理测试 ==="
for upstream in $(grep -r 'proxy_pass' /etc/nginx/conf.d/ 2>/dev/null | awk '{print $2}' | tr -d ';' | sort -u); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$upstream" 2>/dev/null)
    echo "  $upstream -> HTTP $HTTP_CODE"
done
""",
            "docker_cleanup": """#!/bin/bash
# Docker 资源清理脚本

echo "=== Docker 系统状态 ==="
docker system df

echo ""
echo "=== 正在清理 ==="

STOPPED=$(docker ps -aq -f status=exited 2>/dev/null | wc -l)
if [ "$STOPPED" -gt 0 ]; then
    docker rm $(docker ps -aq -f status=exited) 2>/dev/null
    echo " 清理了 $STOPPED 个已停止的容器"
fi

DANGLING=$(docker images -f dangling=true -q 2>/dev/null | wc -l)
if [ "$DANGLING" -gt 0 ]; then
    docker rmi $(docker images -f dangling=true -q) 2>/dev/null
    echo " 清理了 $DANGLING 个悬空镜像"
fi

docker volume prune -f 2>/dev/null
echo " 清理了无用卷"

docker system prune -af 2>/dev/null
docker system df
""",
            "log_analyzer": """#!/bin/bash
# 日志文件快速分析脚本
# 用法: ./log_analyzer.sh /var/log/syslog

LOG_FILE=${1:-/var/log/syslog}
LINES=${2:-1000}

if [ ! -f "$LOG_FILE" ]; then
    echo "错误: 日志文件 $LOG_FILE 不存在"
    exit 1
fi

echo "=== 日志分析报告: $LOG_FILE ==="
echo "分析时间: $(date)"
echo ""

echo "--- 错误级别分布 ---"
echo "  ERROR 总数: $(grep -c -i 'error' "$LOG_FILE" 2>/dev/null)"
echo "  WARN 总数: $(grep -c -i 'warn' "$LOG_FILE" 2>/dev/null)"
echo "  FAIL 总数: $(grep -c -i 'fail' "$LOG_FILE" 2>/dev/null)"

echo ""
echo "--- 时间分布 (最近24小时) ---"
awk -v date="$(date -d '24 hours ago' '+%b %d')" '$0 ~ date' "$LOG_FILE" | awk '{print $1,$2,$3}' | sort | uniq -c | tail -10

echo ""
echo "--- 最频繁的错误消息 (Top 10) ---"
grep -i -E 'error|fail|critical' "$LOG_FILE" 2>/dev/null | sort | uniq -c | sort -rn | head -10

echo ""
echo "--- IP 访问统计 ---"
grep -oE '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}' "$LOG_FILE" 2>/dev/null | sort | uniq -c | sort -rn | head -10
""",
            "general": """## 通用运维助手

请告诉我您需要什么帮助，我可以：

1. **生成运维脚本**
   - 磁盘/CPU/内存监控脚本
   - 自动化备份脚本
   - 服务状态检查脚本
   - Docker/容器管理脚本

2. **分析日志**
   - 系统日志错误分析
   - 访问日志统计
   - 故障排查建议

3. **方案咨询**
   - 架构建议
   - 安全加固方案
   - 性能优化建议

例如：`帮我写一个监控磁盘使用率的脚本` 或 `分析这段日志中的错误`
""",
        }
        return scripts.get(script_type, scripts["general"])

    # ============ 预置日志分析数据 ============

    def _demo_log(self, log_type: str) -> str:
        logs = {
            "error_analysis": """## 日志分析结果

### 发现的主要问题

#### 1. 数据库连接超时 [关键]
```
[ERROR] DBConnectionPool: Connection timed out after 30s
[ERROR] DBConnectionPool: Failed to connect to 192.168.1.100:3306
[ERROR] DBConnectionPool: Max pool size reached (50/50)
```

**影响**: 数据库连接池耗尽，新请求被阻塞

**根因分析**:
- 连接未正常释放（可能缺少 close() 调用）
- 短时间内并发请求突增
- 数据库服务器负载过高

**修复建议**:
```bash
# 1. 检查数据库连接数
mysqladmin -u root -p status | grep Threads

# 2. 临时增加连接池
# my.cnf: max_connections = 200

# 3. 检查慢查询
mysqladmin -u root -p processlist
```

#### 2. 磁盘空间警告 [警告]
```
[WARN] Disk '/var/lib/docker' is 87% full (174G/200G)
```

**建议**: 执行清理 `docker system prune -f`

---

**综合风险评级: 高**
建议优先处理数据库连接问题，预计修复时间 30 分钟。
""",
            "ssh_fail": """## SSH 登录失败分析

### 日志片段
```
Apr 24 03:15:22 server sshd[12345]: Failed password for root from 61.177.172.140
Apr 24 03:15:24 server sshd[12346]: Failed password for root from 61.177.172.140
Apr 24 03:15:26 server sshd[12347]: Failed password for root from 61.177.172.140
```

### 分析结论
**类型**: 暴力破解攻击 (Brute Force Attack)

**特征**:
- 来源 IP: 61.177.172.140（国外IP）
- 3秒内3次尝试，每次不同端口
- 目标用户: root（默认高权限账户）

### 防御方案

**立即执行**:
```bash
# 1. 封禁攻击IP
iptables -A INPUT -s 61.177.172.140 -j DROP
iptables-save > /etc/iptables/rules.v4

# 2. 检查是否已被入侵
lastb | head -20
last | head -20
```

**长期加固**:
```bash
# 1. 禁止root直接SSH登录
sed -i 's/^PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# 2. 更换SSH端口
sed -i 's/^#Port 22/Port 2222/' /etc/ssh/sshd_config

# 3. 安装Fail2ban
apt install fail2ban -y
systemctl enable --now fail2ban

# 4. 使用密钥认证
systemctl restart sshd
```
""",
            "oom_analysis": """## OOM (Out of Memory) 分析

### 日志片段
```
Apr 24 08:30:01 server kernel: java invoked oom-killer
Apr 24 08:30:01 server kernel: oom-kill: process=java, pid=15432
Apr 24 08:30:01 server kernel: Memory cgroup out of memory: Killed process 15432
```

### 分析结论
Java 进程 (PID 15432) 因内存耗尽被 OOM Killer 杀死
- 总虚拟内存: 8.2 GB
- 实际物理内存: 3.5 GB

### 根因排查
```bash
# 1. 检查系统总内存
free -m

# 2. 查看 Java 堆配置
ps aux | grep java
# 检查 -Xmx 参数（最大堆内存）

# 3. 检查内存泄漏
jstat -gcutil <pid> 1000 10
jmap -heap <pid>
```

### 解决方案

**短期**:
```bash
systemctl restart your-service

# 增加swap空间（临时）
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
```

**长期**: 配置内存限制（docker-compose 设置 memory limit）
""",
            "permission_403": """## HTTP 403 权限错误分析

### 问题现象
访问 Web 服务时返回 403 Forbidden

### 排查步骤

```bash
# 1. 检查文件权限
ls -la /var/www/html/

chown -R www-data:www-data /var/www/html/
find /var/www/html/ -type f -exec chmod 644 {} \\;
find /var/www/html/ -type d -exec chmod 755 {} \\;

# 2. 检查 Nginx 配置
nginx -t 2>&1
grep -r 'deny all' /etc/nginx/

# 3. 检查 SELinux
getenforce
restorecon -Rv /var/www/html/

# 4. 检查 .htaccess (Apache)
find /var/www/ -name '.htaccess'
```

### 快速修复
```bash
chmod -R 755 /var/www/html/
chown -R www-data:www-data /var/www/html/
systemctl reload nginx
```
""",
        }
        return logs.get(log_type, "日志分析完成，未发现明显异常。")
