# Docker 容器化部署方案（Ubuntu 24.04）

## 前置要求

| 工具 | 最低版本 | 说明 |
|------|---------|------|
| Docker | 24+ | 容器运行时 |
| Docker Compose | 2+ | 多服务编排 |
| Ubuntu | 24.04 LTS | 服务器操作系统 |
| SSL 证书 | — | Let's Encrypt 或商业证书 |

---

## 部署架构

```
用户请求 → ECS Nginx (443 SSL终结) → frp 隧道 (6003) → 家里 Docker Nginx (80)
  ├── /                       → Web 前端 (React SPA)
  ├── /api/ai/*               → AI 后端 (FastAPI，大模型对话 + RAG)
  ├── /api/knowledge/*        → AI 后端 (FastAPI，知识库管理)
  ├── /vehicle/*              → 车载助手前端 (React + CopilotKit)
  ├── /api/vehicle/*          → 车载助手后端 (FastAPI + LangGraph)
  └── /api/copilotkit         → CopilotKit Runtime (WebSocket)
```

---

## 服务列表

| 服务 | 容器名 | 端口 | 技术栈 | 说明 |
|------|--------|------|--------|------|
| nginx | nginx | 80 | Nginx Alpine | HTTP 反向代理（SSL由ECS nginx处理） |
| web | web | 80 (内部) | Nginx + React SPA | 主站前端 |
| ai-server | ai-server | 8000 | Python FastAPI | AI 聊天 + RAG 知识库 |
| vehicle-backend | vehicle-backend | 8001 | Python FastAPI + LangGraph | 车载助手后端 |
| vehicle-runtime | vehicle-runtime | 4000 | Express + CopilotKit | CopilotKit Runtime |
| vehicle-frontend | vehicle-frontend | 80 (内部) | React + CopilotKit | 车载助手前端 |
| qdrant | qdrant | 6333 | Qdrant | 向量数据库 |
| chromadb | chromadb | 8002 | ChromaDB | 长期记忆向量库 |
| redis | redis | 6379 | Redis 7 Alpine | 共享缓存/队列 |
| langfuse | langfuse-app | 3000 | Langfuse V3 | LLM 可观测性（可选） |

---

## 第一部分：服务器基础环境配置

### 1. 切换阿里云镜像源

```bash
sudo cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak 2>/dev/null || true

sudo tee /etc/apt/sources.list.d/ubuntu.sources > /dev/null << 'EOF'
Types: deb
URIs: https://mirrors.aliyun.com/ubuntu
Suites: noble noble-updates noble-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb-src
URIs: https://mirrors.aliyun.com/ubuntu
Suites: noble noble-updates noble-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF

sudo apt update && sudo apt upgrade -y
```

### 2. 安装基础工具

```bash
sudo apt install -y curl wget git nano htop unzip jq lsof \
    software-properties-common apt-transport-https ca-certificates gnupg
```

### 3. 安装 Docker（阿里云源）

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker-aliyun.gpg
sudo chmod a+r /etc/apt/keyrings/docker-aliyun.gpg
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker-aliyun.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu noble stable" | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
# 重新登录 SSH 使 docker 组生效
```

### 4. 配置 Docker 镜像加速

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "registry-mirrors": [
        "https://docker.1ms.run",
        "https://docker.xuanyuan.me"
    ],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 5. 安装 Node.js 22 LTS

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
sudo apt install -y nodejs
npm config set registry https://registry.npmmirror.com
```

### 6. 配置防火墙 (UFW)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh          # 22
sudo ufw allow 80/tcp       # HTTP
sudo ufw allow 443/tcp      # HTTPS
sudo ufw --force enable
sudo ufw status verbose
```

### 7. 时区与 Swap

```bash
sudo timedatectl set-timezone Asia/Shanghai
sudo timedatectl set-ntp true

# 如果 Swap 不足 1GB，创建 4GB Swap
CURRENT_SWAP=$(free -m | awk '/^Swap:/ {print $2}')
if [ -z "$CURRENT_SWAP" ] || [ "$CURRENT_SWAP" -lt 1024 ]; then
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
    sudo sysctl -p
fi
```

### 8. 申请 SSL 证书（ECS 上操作）

> **架构说明**：SSL 终结在 ECS 上完成。ECS nginx 监听 443（HTTPS），解密后转发 HTTP 明文到 frp 隧道（127.0.0.1:6003），再通过 frp 到达家里 Docker nginx。
> 这样证书申请、续期都在 ECS 上，不需要走 frp 随道验证，更简单可靠。

#### 8.1 安装 certbot

**方式 1：snap 安装（推荐，Ubuntu 24.04+）**

```bash
sudo apt install -y snapd
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
```

**方式 2：apt 安装（旧版本 Ubuntu）**

```bash
sudo apt install -y certbot
```

#### 8.2 申请证书

```bash
# 在 ECS 上执行（certbot standalone 直接在 ECS 监听 80）
# 如果 frps 正在监听 80 端口，需要先停止 frps 释放 80
sudo systemctl stop frps

# 申请证书
sudo certbot certonly --standalone -d mahongwei.com.cn

# 证书存放在: /etc/letsencrypt/live/mahongwei.com.cn/
ls -la /etc/letsencrypt/live/mahongwei.com.cn/
# 应看到 fullchain.pem 和 privkey.pem

# 重新启动 frps
sudo systemctl start frps
```

#### 8.3 安装 ECS nginx

```bash
# 在 ECS 上安装 nginx
sudo apt install -y nginx

# 复制配置文件（从项目 deploy/ecs-nginx/mahongwei.conf）
sudo cp deploy/ecs-nginx/mahongwei.conf /etc/nginx/conf.d/mahongwei.conf

# 删除默认站点（避免冲突）
sudo rm -f /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t
# 应看到: test is successful

# 启动 nginx
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl status nginx
```

#### 8.4 验证 SSL 是否正常

```bash
# ① 检查证书文件是否存在
ls -la /etc/letsencrypt/live/mahongwei.com.cn/
# 应看到: fullchain.pem, privkey.pem

# ② 检查 ECS nginx 是否监听 443
sudo ss -tlnp | grep -E ":80|:443"
# 应看到 nginx 监听 80 和 443

# ③ 检查 ECS nginx 配置语法
sudo nginx -t

# ④ 测试 HTTPS 连接（在 ECS 本机测试）
curl -v https://mahongwei.com.cn
# 应看到 SSL handshake 成功 + 返回 HTML 内容
# 如果返回 Empty reply，说明 frp 随道还没打通

# ⑤ 测试 SSL 证书信息
openssl s_client -connect mahongwei.com.cn:443 -servername mahongwei.com.cn </dev/null 2>/dev/null | openssl x509 -noout -subject -dates
# 应看到: subject=CN = mahongwei.com.cn
#          notBefore=... notAfter=...（有效期 90 天）

# ⑥ 从外网测试 HTTPS
# 在任意外网机器上
curl -I https://mahongwei.com.cn
# 应看到: HTTP/2 200 或 301
```

#### 8.5 SSL 常见问题排查

| 问题 | 症状 | 排查命令 | 解决方法 |
|------|------|----------|----------|
| 证书未申请 | nginx 启动失败 | `ls /etc/letsencrypt/live/mahongwei.com.cn/` | 先执行 8.2 申请证书 |
| frps 占了 80 端口 | certbot standalone 失败 | `sudo ss -tlnp | grep :80` | 先停 frps 再申请证书 |
| nginx 配置语法错误 | `nginx -t` 报错 | `sudo nginx -t` | 检查配置文件语法 |
| HTTPS 返回 Empty reply | `curl https://域名` 无响应 | 检查 frp 穿透是否生效 | 确保 frpc 连接成功 + nginx-http 穿透规则注册 |
| SSL handshake 失败 | `curl: (35) SSL connect error` | `openssl s_client -connect 域名:443` | 检查证书路径是否正确 |
| 证书过期 | 浏览器提示不安全 | `openssl x509 -noout -dates` | 执行 `sudo certbot renew` |

#### 8.6 设置自动续期

```bash
# 在 ECS 上设置 crontab
sudo certbot renew --dry-run   # 先测试续期是否正常
echo "0 3 */7 * * certbot renew --quiet --deploy-hook 'systemctl reload nginx'" | sudo tee -a /var/spool/cron/crontabs/root
```

---

## 第二部分：部署项目

### 1. 准备环境变量

```bash
cd /path/to/project/deploy
cp .env.example .env
nano .env
```

**必须填入的变量：**

```ini
# LLM 大模型 API Key（阿里云 DashScope）
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx

# Embedding 向量 API Key（SiliconFlow）
EMBEDDING_API_KEY=sk-xxxxxxxxxxxxxxxx

# 服务器公网 IP
SERVER_IP=106.14.24.38
```

### 2. 构建并启动

```bash
cd deploy

# 构建所有镜像并后台启动
docker compose up -d --build

# 查看所有服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 3. 验证部署

```bash
# 健康检查
curl https://mahongwei.com.cn/api/health

# 车载助手
curl https://mahongwei.com.cn/vehicle/

# 查看各服务日志
docker compose logs -f ai-server
docker compose logs -f vehicle-backend
```

---

## 第三部分：内网穿透（frp）

### 什么是内网穿透？为什么需要它？

**场景举例**：

你在家里电脑上开发，项目跑在 `localhost:8001`。想让同事或客户用手机浏览器看效果，但你的电脑没有公网 IP（运营商给你的是一个内网地址 `192.168.x.x` 或 `10.x.x.x`），外面的人访问不到。

**内网穿透的作用**：

通过一台有公网 IP 的服务器（阿里云 ECS）做"中转站"，把你本地的服务"映射"到公网上。

**用比喻来说**：
```
你的电脑（家里）        →  快递柜（阿里云服务器）  →  客户（手机访问）
localhost:8001             公网 IP:6001               http://公网IP:6001
```
客户访问 `http://106.14.24.38:6001`，请求会被转发到你家里的 `localhost:8001`。

### 当前网络拓扑

```
┌─────────────────────────────────────────────────────────────────┐
│                         互联网 (公网)                            │
│                                                                 │
│  手机/电脑用户                                                   │
│       │                                                         │
│       │  访问 https://mahongwei.com.cn                          │
│       ▼                                                         │
│  ┌────────────────────────────────────────────┐                 │
│  │  阏里云 ECS (106.14.24.38)                  │                │
│  │  ─────────────────────────                  │                │
│  │  • 公网 IP，24 小时在线                      │                │
│  │  • nginx: SSL 终结 (80/443)                 │                │
│  │  • frps: 内网穿透服务端 (7000)               │                │
│  │  • 开放端口：80, 443, 7000, 6000-6002, 7500 │                │
│  │                                             │                │
│  │  HTTPS 请求处理流程：                        │                │
│  │  443 → nginx SSL终结 → 127.0.0.1:6003 → frps │                │
│  │  80 → nginx 301重定向到HTTPS                │                │
│  └─────────────────┬──────────────────────────┘                 │
│                    │                                            │
│                    │  ← frp 加密隧道 (TCP 长连接) →              │
│                    │                                            │
└────────────────────┼────────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │  家里/公司内网         │
          │  (192.168.31.x)      │
          │                      │
          │  内网机器              │
          │  192.168.31.101       │
          │  ──────────────       │
          │  • frpc (客户端)      │
          │  • Docker 全部服务     │
          │                      │
          │  Docker nginx:80     │  HTTP 反向代理（不做SSL）
          │  ai-server:8000      │  AI 后端
          │  vehicle-backend:8001│  车载助手后端
          │  vehicle-runtime:4000│  CopilotKit Runtime
          └──────────────────────┘
```

### 工作原理（一步步解释）

```
HTTPS 请求的完整流程：

第 1 步：用户访问 https://mahongwei.com.cn
         请求到达 ECS 的 nginx (443端口)

第 2 步：ECS nginx 做 SSL 终结（解密 HTTPS → HTTP）
         nginx 将请求转发到 127.0.0.1:6003

第 3 步：frps 在 ECS 上监听 6003 端口
         收到 HTTP 明文请求

第 4 步：frps 通过 frp 隧道转发给 frpc
         ECS:6003 ──────隧道──────→ 192.168.31.101:80

第 5 步：frpc 转发给本地 Docker nginx:80
         192.168.31.101 ──────→ Docker nginx:80

第 6 步：Docker nginx 反向代理到各后端服务
         ai-server / vehicle-backend / web 等

第 7 步：响应沿原路返回
         后端 → Docker nginx → frpc → 隧道 → frps → ECS nginx(加密) → 用户
```

HTTP 请求的流程：

```
用户访问 http://mahongwei.com.cn
→ ECS nginx (80) 返回 301 重定向到 HTTPS
→ 用户浏览器自动跳转到 https://mahongwei.com.cn
→ 走上面的 HTTPS 流程
```

---

### 1. 阿里云 ECS 安装 frps（服务端）

SSH 登录到阿里云服务器（106.14.24.38）执行：

#### 1.1 下载并安装

```bash
# 下载 frp（选最新版本，以 0.61.0 为例）
cd /tmp
wget https://github.com/fatedier/frp/releases/download/v0.61.0/frp_0.61.0_linux_amd64.tar.gz

# 解压
tar -xzf frp_0.61.0_linux_amd64.tar.gz

# 安装 frps 到系统目录
sudo cp frp_0.61.0_linux_amd64/frps /usr/local/bin/

# 创建配置目录
sudo mkdir -p /etc/frp

# 验证安装
frps --version
# 应输出: frps version 0.61.0
```

#### 1.2 生成通信密钥

```bash
# 生成一个随机 token（客户端和服务端必须一致）
openssl rand -hex 16
# 输出示例: a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5
# 复制这串字符，下面配置要用
```

#### 1.3 配置 frps（服务端）

```bash
sudo nano /etc/frp/frps.toml
```

写入以下内容：

```bash
# ===== frps 服务端配置 =====

# 监听端口，frpc 客户端会连接这个端口
bindPort = 7000

# 通信认证（客户端必须用同样的 token 才能连接）
auth.method = "token"
auth.token = "a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5"   # ← 换成你生成的 token

# Dashboard 管理面板（可选，方便查看连接状态）
webServer.addr = "0.0.0.0"
webServer.port = 7500
webServer.user = "admin"
webServer.password = "StrongP@ssw0rd123"   # ← 改成强密码

# 日志配置
log.to = "/var/log/frps.log"
log.level = "info"
log.maxDays = 7
```

#### 1.4 创建 systemd 服务（开机自启）

```bash
sudo tee /etc/systemd/system/frps.service > /dev/null << 'EOF'
[Unit]
Description=frp Server (内网穿透服务端)
After=network.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/frps -c /etc/frp/frps.toml
Restart=on-failure
RestartSec=5
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF

# 重载 systemd 配置
sudo systemctl daemon-reload

# 设置开机自启
sudo systemctl enable frps

# 立即启动
sudo systemctl start frps

# 查看状态
sudo systemctl status frps
```

看到 `active (running)` 就成功了。

#### 1.5 配置防火墙（两层都要开）

**第一层：UFW 系统防火墙**

```bash
# 放行 frp 通信端口
sudo ufw allow 7000/tcp    # frpc 连接 frps 用的

# 放行 ECS nginx（SSL 终结 + HTTP 重定向）
sudo ufw allow 80/tcp      # HTTP（ECS nginx 监听）
sudo ufw allow 443/tcp     # HTTPS（ECS nginx SSL 终结）

# 放行 frpc 穿透的端口（frpc 配了 remotePort，ECS 这里就要放行）
# 6003 不需要放行！ECS nginx proxy_pass 到 127.0.0.1:6003 是本机内部通信，UFW 不管
sudo ufw allow 6000/tcp    # AI 后端（开发调试）
sudo ufw allow 6001/tcp    # 车载助手后端（开发调试）
sudo ufw allow 6002/tcp    # CopilotKit Runtime（开发调试）

# 放行 Dashboard（可选）
sudo ufw allow 7500/tcp

# 查看状态
sudo ufw status verbose
```

**第二层：阿里云安全组**

1. 登录 [阿里云控制台](https://ecs.console.aliyun.com)
2. 找到你的 ECS 实例 → **安全组** → **配置规则**
3. **入方向** → **手动添加**：

| 授权策略 | 协议类型 | 端口范围 | 授权对象 | 说明 |
|---------|---------|---------|---------|------|
| 允许 | TCP | 7000/7000 | 0.0.0.0/0 | frp 通信端口 |
| 允许 | TCP | 80/80 | 0.0.0.0/0 | HTTP（ECS nginx 监听） |
| 允许 | TCP | 443/443 | 0.0.0.0/0 | HTTPS（ECS nginx SSL 终结） |
| 允许 | TCP | 6003/6003 | 不需要 | ECS nginx 转发到 127.0.0.1:6003 是本机内部通信，安全组不管 |
| 允许 | TCP | 6000/6000 | 0.0.0.0/0 | AI 后端穿透（开发调试） |
| 允许 | TCP | 6001/6001 | 0.0.0.0/0 | 车载助手后端穿透（开发调试） |
| 允许 | TCP | 6002/6002 | 0.0.0.0/0 | CopilotKit Runtime 穿透（开发调试） |
| 允许 | TCP | 7500/7500 | 你的 IP/32 | frp Dashboard（建议限制 IP） |

#### 1.6 验证服务端是否正常工作

```bash
# 查看 frps 日志
sudo journalctl -u frps -f --no-pager

# 或者查看日志文件
tail -f /var/log/frps.log

# 检查端口是否在监听（80/443 需要等 frpc 注册穿透规则后才会出现）
sudo ss -tlnp | grep frps
# frpc 连接成功后应看到:
# LISTEN  *:6003  (nginx-http 穿透规则，ECS nginx 占了80所以用6003)
# LISTEN  *:443   (ECS nginx SSL终结，不是frps监听的)
# LISTEN  *:7000  (frps 通信端口)
# LISTEN  *:7500  (Dashboard)
# LISTEN  *:6000  (AI 后端穿透)
# LISTEN  *:6001  (车载助手后端穿透)
# LISTEN  *:6002  (CopilotKit Runtime 穿透)
#
# 如果只看到 7000/7500 没有 80/443/6000/6001/6002，说明 frpc 没连接成功
# 请检查 frpc 日志：sudo journalctl -u frpc -n 30
```

---

### 2. 内网机器安装 frpc（客户端）

在 **192.168.31.101** 这台机器上操作。

#### 2.1 下载安装

**Windows 系统（你的开发机）：**

```powershell
# 1. 下载 Windows 版本
# 浏览器打开: https://github.com/fatedier/frp/releases/download/v0.61.0/frp_0.61.0_windows_amd64.zip

# 2. 解压到 C:\frp（或你喜欢的位置）
# 解压后得到: frpc.exe 和 frpc.toml

# 3. 创建配置文件 C:\frp\frpc.toml（见下一步）
```

**Linux 系统：**

```bash
cd /tmp
wget https://github.com/fatedier/frp/releases/download/v0.61.0/frp_0.61.0_linux_amd64.tar.gz
tar -xzf frp_0.61.0_linux_amd64.tar.gz
sudo cp frp_0.61.0_linux_amd64/frpc /usr/local/bin/
sudo mkdir -p /etc/frp
frpc --version
```

#### 2.2 配置 frpc（客户端）

**Windows 路径**：`C:\frp\frpc.toml`  
**Linux 路径**：`/etc/frp/frpc.toml`

```bash
nano /etc/frp/frpc.toml   # Linux
# 或用记事本编辑 C:\frp\frpc.toml   # Windows
```

写入以下内容：

```toml
# ===== frpc 客户端配置 =====

# 连接阿里云 ECS 的 frps 服务端
serverAddr = "106.14.24.38"
serverPort = 7000

# 通信认证（必须和 frps 的 token 完全一致）
auth.method = "token"
auth.token = "a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5"   # ← 和 frps 一样

# 日志配置
# Linux 路径
log.to = "/var/log/frpc.log"
log.level = "info"
log.maxDays = 7
# Windows 路径请改为: log.to = "C:\frp\frpc.log"

# ================================================================
# 穿透规则配置
# 每增加一个 [[proxies]] 就是增加一条穿透规则
# ================================================================

# ----- 规则 1：穿透家里 Nginx HTTP (80) -----
# ECS nginx 占了 80 端口做 HTTPS 重定向，所以 frps 用 6003 端口
# 请求流程：ECS nginx:443(SSL终结) → proxy_pass 127.0.0.1:6003 → frps → frp隧道 → 家里:80
[[proxies]]
name = "nginx-http"
type = "tcp"
localIP = "127.0.0.1"
localPort = 80
remotePort = 6003                   # 不能用80，ECS nginx 已经占了80

# ----- 规则 2：穿透 Vite 前端开发服务器 -----
# 用 HTTP 类型，支持域名访问（需要 DNS 解析）
[[proxies]]
name = "web-dev"
type = "http"
localIP = "127.0.0.1"
localPort = 5173                    # 本地 Vite 端口
customDomains = ["dev.mahongwei.com.cn"]   # 访问域名

# ----- 规则 4：穿透车载助手后端 -----
[[proxies]]
name = "vehicle-backend"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8001                    # 本地后端端口
remotePort = 6001                   # 公网访问端口

# ----- 规则 5：穿透 AI 后端 -----
[[proxies]]
name = "ai-server"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8000
remotePort = 6000

# ----- 规则 6：穿透 CopilotKit Runtime -----
[[proxies]]
name = "vehicle-runtime"
type = "tcp"
localIP = "127.0.0.1"
localPort = 4000
remotePort = 6002
```

#### 2.3 配置 DNS（如果使用域名访问）

如果你想用 `dev.mahongwei.com.cn` 访问内网穿透的前端：

1. 登录 [阿里云 DNS 控制台](https://dns.console.aliyun.com)
2. 找到 `mahongwei.com.cn` → **解析设置**
3. **添加记录**：

| 记录类型 | 主机记录 | 记录值 | TTL |
|---------|---------|--------|-----|
| A | dev | 106.14.24.38 | 10 分钟 |

等待几分钟后生效。

#### 2.4 启动 frpc

**Linux（systemd 服务）：**

```bash
# 创建 systemd 服务文件
sudo tee /etc/systemd/system/frpc.service > /dev/null << 'EOF'
[Unit]
Description=frp Client (内网穿透客户端)
After=network.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/frpc -c /etc/frp/frpc.toml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable frpc
sudo systemctl start frpc
sudo systemctl status frpc
```

**Windows（手动运行或注册服务）：**

```powershell
# 方式 1：手动运行（测试用）
cd C:\frp
.\frpc.exe -c .\frpc.toml
# 看到 "login to server success" 就表示连接成功
# 按 Ctrl+C 停止

# 方式 2：注册为 Windows 服务（开机自启）
# 先安装 nssm
winget install nssm

# 注册服务（注意路径要改成你实际的位置）
nssm install frpc "C:\frp\frpc.exe" "-c" "C:\frp\frpc.toml"
nssm set frpc AppDirectory "C:\frp"
nssm start frpc

# 查看服务状态
nssm status frpc
```

#### 2.5 验证连接是否成功

**在 frpc 端查看日志：**

```bash
# Linux
sudo journalctl -u frpc -f --no-pager

# Windows（命令行窗口会直接输出）
# 看到类似以下内容表示成功：
# [I] login to server success
# [I] [nginx-http] start proxy success
# [I] [vehicle-backend] start proxy success
# [I] [ai-server] start proxy success
# [I] [vehicle-runtime] start proxy success
#
# 如果看到 "login to the server failed: token in login doesn't match"
# 说明 frpc 和 frps 的 auth.token 不一致，请检查两边配置
```

**在阿里云 ECS 上查看 Dashboard：**

浏览器打开 `http://106.14.24.38:7500`，输入 admin 和密码，可以看到：
- 当前连接的客户端数量
- 每条穿透规则的状态
- 流量统计

---

### 3. 访问验证

#### 3.1 测试清单

| 测试项 | 命令/操作 | 预期结果 |
|-------|--------|---------|
| frps 运行状态 | `sudo systemctl status frps` | active (running) |
| frpc 连接状态 | `sudo journalctl -u frpc -n 20` 看到 "login success" | 连接成功 |
| ECS 端口监听 | `sudo ss -tlnp | grep -E "frps|nginx"` | 6003/6000/6001/6002/7000/7500(frps) + 80/443(nginx) |
| Dashboard 可访问 | 浏览器打开 `http://106.14.24.38:7500` | 看到管理面板 |
| HTTP 域名访问 | `curl http://mahongwei.com.cn` | 返回前端页面 |
| HTTPS 域名访问 | `curl https://mahongwei.com.cn` | 返回前端页面（需 SSL 证书） |
| AI 后端穿透 | `curl http://106.14.24.38:6000/api/health` | 返回健康检查 |
| 车载助手穿透 | `curl http://106.14.24.38:6001/api/vehicle/health` | 返回健康检查 |
| 前端域名访问 | 浏览器打开 `http://dev.mahongwei.com.cn` | 看到前端页面 |

#### 3.2 从外网测试

```bash
# 在任意外网机器上测试
curl -v http://106.14.24.38:6001/api/vehicle/health

# 如果返回超时或连接拒绝，按下面的"故障排查"步骤检查
```

---

### 4. 故障排查

#### 问题 1：frpc 无法连接 frps

**症状**：`login to server failed`

**排查步骤**：
```bash
# 1. 检查 frps 是否在运行
# 在阿里云 ECS 上
sudo systemctl status frps
sudo ss -tlnp | grep 7000

# 2. 检查阿里云安全组是否开放 7000 端口
# 登录阿里云控制台查看

# 3. 检查 UFW 是否开放 7000
sudo ufw status | grep 7000

# 4. 检查 token 是否一致
# frps 和 frpc 的 auth.token 必须完全相同

# 5. 检查网络连通性
# 在内网机器上
telnet 106.14.24.38 7000
# 或
nc -zv 106.14.24.38 7000
```

#### 问题 2：外网无法访问穿透端口

**症状**：`curl http://106.14.24.38:6001` 超时

**排查步骤**：
```bash
# 1. 在阿里云 ECS 上检查端口是否被监听
sudo ss -tlnp | grep 6001
# 应该看到 frps 在监听

# 2. 检查 UFW 和阿里云安全组是否都开放了该端口

# 3. 检查本地服务是否在运行
# 在内网机器上
curl http://localhost:8001/api/vehicle/health

# 4. 查看 frpc 日志，看代理是否启动成功
sudo journalctl -u frpc -n 50
```

#### 问题 3：域名无法访问

**症状**：`http://dev.mahongwei.com.cn` 打不开

**排查步骤**：
```bash
# 1. 检查 DNS 是否解析到阿里云服务器
ping dev.mahongwei.com.cn
# 应返回 106.14.24.38

# 2. 等待 DNS 生效（新添加的 A 记录可能需要 10 分钟）

# 3. 检查 frpc 配置中 customDomains 是否和访问域名一致
```

---

### 5. 常用运维命令

```bash
# ==================== 阿里云 ECS (frps) ====================

# 查看服务状态
sudo systemctl status frps

# 重启服务
sudo systemctl restart frps

# 查看实时日志
sudo journalctl -u frps -f

# 查看最近 100 行日志
sudo journalctl -u frps -n 100

# 停止服务
sudo systemctl stop frps

# 查看端口监听情况
sudo ss -tlnp | grep frps


# ==================== 内网机器 (frpc) ====================

# 查看服务状态
sudo systemctl status frpc

# 重启服务（修改配置后）
sudo systemctl restart frpc

# 查看实时日志
sudo journalctl -u frpc -f

# 查看最近 100 行日志
sudo journalctl -u frpc -n 100

# 停止服务
sudo systemctl stop frpc

# Windows 上查看服务状态
nssm status frpc
```

---

### 6. 添加/删除穿透规则

**添加新规则**：

编辑 frpc 配置文件，在末尾添加：
```toml
# 新规则：穿透某个新服务
[[proxies]]
name = "new-service"
type = "tcp"
localIP = "127.0.0.1"
localPort = 9000        # 新服务的本地端口
remotePort = 6003       # 公网访问端口（确保没被占用）
```

然后重启 frpc：
```bash
sudo systemctl restart frpc
```

**同时记得**：在阿里云安全组和 UFW 中开放 `6003` 端口。

**删除规则**：直接删除对应的 `[[proxies]]` 段落，然后重启 frpc。

---

### 7. 安全建议

| 建议 | 说明 |
|------|------|
| **使用强 token** | 不要用 `123456` 或 `password`，用 `openssl rand -hex 16` 生成 |
| **限制 Dashboard 访问** | 7500 端口在安全组中只允许你的 IP 访问，不要开放给 `0.0.0.0/0` |
| **定期更换 token** | 每季度换一次，同时更新 frps 和 frpc 的配置 |
| **不要穿透敏感服务** | 不要把数据库端口、SSH 端口穿透到公网 |
| **用完就关** | 调试演示结束后，`sudo systemctl stop frpc` 关闭穿透 |

---

### 8. 完整配置对照表

| 配置项 | frps (服务端) | frpc (客户端) |
|--------|--------------|--------------|
| 位置 | 阿里云 ECS (106.14.24.38) | 内网机器 (192.168.31.101) |
| 程序 | `/usr/local/bin/frps` | `/usr/local/bin/frpc` 或 `C:\frp\frpc.exe` |
| 配置文件 | `/etc/frp/frps.toml` | `/etc/frp/frpc.toml` 或 `C:\frp\frpc.toml` |
| 服务管理 | `systemctl start/stop/restart frps` | `systemctl start/stop/restart frpc` 或 `nssm` |
| 日志位置 | `/var/log/frps.log` 或 `journalctl -u frps` | `/var/log/frpc.log` 或 `journalctl -u frpc` |
| Dashboard | `http://106.14.24.38:7500` | — |

---

## 第四部分：常用运维命令

> 以下命令均在 `deploy/` 目录下执行

### 构建 & 启动

```bash
# 构建并启动全部服务
docker compose up -d --build

# 只重新构建某个服务（改了代码后用）
docker compose up -d --build web              # 主站前端
docker compose up -d --build ai-server        # AI 后端
docker compose up -d --build vehicle-backend  # 车载助手后端
docker compose up -d --build vehicle-frontend # 车载助手前端
docker compose up -d --build vehicle-runtime  # CopilotKit Runtime
docker compose up -d --build nginx            # Nginx 反向代理

# 强制重新构建（忽略缓存，改了 package.json / requirements.txt 后用）
docker compose build --no-cache web
docker compose up -d web
```

### 重启（不重新构建，只重启容器）

```bash
docker compose restart web              # 主站前端
docker compose restart ai-server        # AI 后端
docker compose restart vehicle-backend  # 车载助手后端
docker compose restart vehicle-frontend # 车载助手前端
docker compose restart vehicle-runtime  # CopilotKit Runtime
docker compose restart nginx            # Nginx
docker compose restart                  # 全部重启
```

### 停止

```bash
docker compose down         # 停止全部服务（不删除数据）
docker compose down -v      # 停止 + 删除数据卷（慎用，清空知识库数据）
```

### 查看日志

```bash
docker compose logs -f                      # 全部服务实时日志
docker compose logs -f web                  # 主站前端
docker compose logs -f ai-server            # AI 后端
docker compose logs -f vehicle-backend      # 车载助手后端
docker compose logs -f vehicle-frontend     # 车载助手前端
docker compose logs -f vehicle-runtime      # CopilotKit Runtime
docker compose logs -f nginx                # Nginx
docker compose logs --tail 100 ai-server    # 最近 100 行日志
```

### 调试 & 状态

```bash
docker compose ps                           # 查看所有容器状态
docker compose exec ai-server bash          # 进入 AI 后端容器
docker compose exec vehicle-backend bash    # 进入车载助手容器
docker compose exec nginx sh                # 进入 Nginx 容器
docker compose exec redis sh                # 进入 Redis 容器
```

### Redis 管理（共享基础设施）

Redis 已配置内存上限（默认 256MB），超限时自动淘汰最久未使用的数据（LRU）。

```bash
# 进入 Redis CLI
docker compose exec redis redis-cli -a $REDIS_PASSWORD

# 查看内存使用情况
redis> info memory
# used_memory_human: 当前使用量（如 50MB）
# used_memory_peak_human: 历史最高值
# maxmemory_human: 内存上限（如 256MB）
# maxmemory_policy: 淘汰策略（allkeys-lru）

# 查看 Key 数量
redis> dbsize

# 查看所有 Key（慎用，生产环境可能很多）
redis> keys *

# 退出
redis> quit
```

**多服务共用 Redis（用不同数据库编号隔离）：**

| 数据库 | 服务 | 连接方式 |
|--------|------|----------|
| db 0 | Langfuse | `SELECT 0` |
| db 1 | RAGFlow（未来） | `SELECT 1` |
| db 2 | 其他服务 | `SELECT 2` |

**检查 Redis 是否被 OOM Killer 杀死：**

```bash
# 查看系统日志，看是否有 OOM（Out Of Memory）记录
sudo dmesg | grep -i "oom\|killed\|redis" | tail -10
```

### Langfuse 可观测性

> 家里服务器 32GB 内存，Langfuse 随默认启动，无需额外参数。

```bash
docker compose up -d --build   # Langfuse 默认启动
docker compose down             # 停止全部
```

---

## 数据持久化

| Volume | 挂载路径 | 说明 |
|--------|---------|------|
| ai-logs | /app/logs | AI 后端日志 |
| qdrant-data | /qdrant/storage | 向量数据库持久化存储 |
| chromadb-data | /chroma/chroma | 车载助手长期记忆 |
| vehicle-data | /app/data | 车载助手数据（SQLite） |
| vehicle-logs | /app/logs | 车载助手日志 |
| langfuse-db-data | /var/lib/postgresql/data | Langfuse PostgreSQL |
| langfuse-clickhouse-data | /var/lib/clickhouse | Langfuse ClickHouse |
| redis-data | /data | Redis 共享数据（缓存/队列） |
| langfuse-minio-data | /data | Langfuse MinIO |

---

## 注意事项

1. **SSL 证书**：Let's Encrypt 证书每 90 天需更新，ECS 上已配置 crontab 自动续期（`sudo certbot renew` + `systemctl reload nginx`）。证书存放在 ECS `/etc/letsencrypt/live/mahongwei.com.cn/`
2. **SSL 终结架构**：HTTPS 在 ECS nginx 上终结，解密后通过 frp 随道转发 HTTP 明文到家里 Docker nginx。家里 nginx 只配 HTTP（80端口），不需要 SSL 证书
3. **日志查看**：容器内日志文件位于 `/app/logs/` 目录
4. **端口冲突**：家里宿主机只需确保 80/6333/8000/8001/8002/4000 端口未被占用（443 不再需要）；ECS 确保 80/443/6003/7000/7500 未被占用（ECS nginx 占80/443，frps 占6003/7000/6000-6002/7500）
5. **环境变量**：`.env` 文件不要提交到 Git（已在 .gitignore 中排除），所有密钥、密码必须在 `.env` 中配置
6. **知识库数据**：Qdrant 数据持久化在 `qdrant-data` 卷中，删除卷将丢失所有知识库数据
7. **内网穿透安全**：frp token 务必设置强密码，不要暴露到公网 7500 端口（Dashboard）
8. **Redis 配置**：Redis 是共享基础设施，需在宿主机执行 `sudo sysctl vm.overcommit_memory=1`
9. **多服务共用 Redis**：各服务使用不同的数据库编号（`SELECT 0`、`SELECT 1`）隔离数据，避免 key 冲突
10. **Redis 内存上限**：默认 256MB（`REDIS_MAXMEMORY`），超限自动淘汰旧数据（LRU），3.4GB 服务器建议不超过 512MB
11. **扩展 RAGFlow**：未来如需添加 RAGFlow，它也会共用同一个 Redis（配置 `REDIS_URL=redis://redis:6379/1` 用 db=1 隔离）
12. **ECS nginx 与 frps 端口不冲突**：frpc 穿透规则的 remotePort=6003（不是80），ECS nginx 占 80/443，frps 监听 6003/7000/6000/6001/6002/7500，互不冲突。申请 SSL 证书时需临时停 frps 释放 80 端口给 certbot
