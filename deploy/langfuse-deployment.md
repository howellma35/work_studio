# Langfuse 可观测性平台部署指南

> 在 mahongwei.com.cn 服务器上部署 Langfuse，用于追踪 AutoMind 车机助手的完整 LLM 链路

## 一、部署架构

```
用户浏览器
    ↓ HTTP (服务器IP:3000)
Langfuse 容器 (:3000)
    ↓
PostgreSQL 容器 (:5432)
```

Langfuse 通过端口 3000 直接访问，无需 Nginx 代理。
（生产环境可后续加 Nginx + SSL 反向代理）

## 二、前置条件

- 服务器已有 Docker + Docker Compose 环境
- 服务器防火墙开放 3000 端口

## 三、部署步骤

### Step 1: 生成密钥

在服务器上运行以下命令，生成安全密钥：

```bash
# NEXTAUTH_SECRET (认证密钥, 64位hex)
openssl rand -hex 32
# 输出: a1b2c3d4e5f6...64位hex字符串

# LANGFUSE_SECRET_KEY (API密钥, 64位hex)
openssl rand -hex 32
# 输出: f6e5d4c3b2a1...64位hex字符串

# SALT (盐值, 32位hex)
openssl rand -hex 16
# 输出: 1a2b3c4d...32位hex字符串

# 数据库密码 (32位hex)
openssl rand -hex 16
# 输出: dbpass123abc...32位hex字符串
```

### Step 2: 创建 deploy/.env 文件

在 `deploy/` 目录下创建 `.env` 文件（存放敏感密钥，不要提交到 Git）：

```bash
# deploy/.env (不要提交到 Git!)
LANGFUSE_DB_PASSWORD=<Step1生成的数据库密码>
LANGFUSE_NEXTAUTH_SECRET=<Step1生成的NEXTAUTH_SECRET>
LANGFUSE_SECRET_KEY=<Step1生成的LANGFUSE_SECRET_KEY>
LANGFUSE_SALT=<Step1生成的SALT>
SERVER_IP=<你的服务器公网IP>   # 例如: 123.45.67.89
```

确保 `deploy/.gitignore` 包含 `.env`

### Step 3: 启动服务

```bash
cd deploy

# 启动所有服务（包括新增的 Langfuse）
docker compose up -d

# 查看 Langfuse 容器状态
docker compose ps

# 查看 Langfuse 日志
docker compose logs -f langfuse
# 等待日志出现: "Langfuse is running"
```

### Step 4: 注册管理员账号并获取 API Key

浏览器访问 `http://<你的服务器IP>:3000`：

1. 点击 **Sign up** 注册第一个账号（自动成为管理员）
2. 创建一个 **Project**（如 "AutoMind"）
3. 进入 Project Settings → API Keys
4. 复制 **Public Key** 和 **Secret Key**

### Step 5: 配置 AutoMind 连接 Langfuse

将 Step 4 获取的密钥填入 `vehicle-agent/backend/.env`：

```bash
# vehicle-agent/backend/.env
LANGFUSE_HOST=http://<你的服务器IP>:3000
LANGFUSE_PUBLIC_KEY=pk-lf-<你的真实Public Key>
LANGFUSE_SECRET_KEY=sk-lf-<你的真实Secret Key>
```

然后重启 AutoMind 服务。

## 四、验证

### 4.1 检查 Langfuse 状态

```bash
curl http://<服务器IP>:3000/api/health
# 应返回 {"status":"ok"}
```

### 4.2 测试追踪

发送一条消息给 AutoMind（如"空调调低点"），然后在 Langfuse 控制台查看：

- **Trace 树状图** — supervisor → vehicle_agent → tool call 的完整链路
- **每次 LLM 调用** — prompt / completion / token / latency
- **工具调用详情** — set_climate 的参数和返回值

## 五、安全建议

1. **关闭公开注册** — 创建管理员后修改 `LANGFUSE_ENABLE_SIGNUP: "false"`
2. **数据库密码** — 使用 openssl 生成，不要用默认值
3. **deploy/.env** — 不要提交到 Git
4. **后续加固** — 生产环境建议加 Nginx + SSL 反向代理（参考 nginx.conf 中的注释）
5. **定期备份** — `docker compose exec langfuse-db pg_dump -U langfuse langfuse > backup.sql`

## 六、常见问题

| 问题 | 解决方案 |
|------|----------|
| 端口 3000 无法访问 | 检查防火墙是否开放: `firewall-cmd --add-port=3000/tcp` |
| Langfuse 容器启动失败 | `docker compose logs langfuse` 查看，通常是 DB 连接错误 |
| AutoMind 日志显示 "Langfuse 未配置" | 检查 .env 中 PUBLIC_KEY / SECRET_KEY 是否为真实值 |
| Trace 数据未出现 | 确保 observability.py 的 CallbackHandler 正确注入 |

## 七、后续升级: 加 Nginx + SSL 反向代理

当你需要 HTTPS 访问时，步骤如下：

1. DNS: 添加 `langfuse.mahongwei.com.cn` A 记录指向服务器 IP
2. SSL: `certbot certonly --standalone -d langfuse.mahongwei.com.cn`
3. docker-compose.yml: 移除 Langfuse 的 `ports: 3000:3000`，改为内部端口
4. nginx.conf: 添加 Langfuse HTTPS server block（参考注释中的模板）
5. .env: 将 NEXTAUTH_URL 和 NEXT_PUBLIC_SITE_URL 改为 `https://langfuse.mahongwei.com.cn`
6. vehicle-agent .env: 将 LANGFUSE_HOST 改为 `https://langfuse.mahongwei.com.cn`
