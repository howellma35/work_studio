# Langfuse 可观测性平台部署指南

> 在服务器上部署 Langfuse，用于追踪 AutoMind 车机助手的完整 LLM 链路

## 一、部署架构

```
用户浏览器
    ↓ HTTP (服务器IP:3001)
Langfuse 容器 (:3001)
    ↓
PostgreSQL 容器 (:5432)
```

Langfuse 通过端口 3001 直接访问（3000 端口已被其他服务占用），无需 Nginx 代理。

## 二、前置条件

- 服务器已有 Docker + Docker Compose 环境
- 服务器防火墙开放 3001 端口

## 三、部署步骤

### Step 1: 生成密钥

在服务器上运行：

```bash
# NEXTAUTH_SECRET (认证密钥)
openssl rand -hex 32

# LANGFUSE_APP_SECRET (Langfuse 服务内部密钥)
openssl rand -hex 32

# SALT (盐值)
openssl rand -hex 16

# 数据库密码
openssl rand -hex 16
```

### Step 2: 编辑 deploy/.env 文件

编辑 `vehicle-agent/deploy/.env` 中的关键变量：

```bash
# ===== 必改项 =====
SERVER_IP=<你的服务器公网IP>    # 例如: 123.45.67.89
LLM_API_KEY=<你的百炼平台API Key>

# ===== Langfuse 密钥 (用 Step1 生成的值替换) =====
LANGFUSE_DB_PASSWORD=<数据库密码>
LANGFUSE_NEXTAUTH_SECRET=<认证密钥>
LANGFUSE_APP_SECRET=<服务内部密钥>
LANGFUSE_SALT=<盐值>
```

### Step 3: 启动服务

```bash
cd vehicle-agent/deploy

# 启动全部服务 (后端 + 前端 + Langfuse + ChromaDB)
docker compose up -d

# 查看 Langfuse 日志
docker compose logs -f langfuse
# 等待日志出现: "Langfuse is running"
```

### Step 4: 注册管理员账号并获取 API Key

浏览器访问 `http://<服务器IP>:3001`：

1. 点击 **Sign up** 注册第一个账号（自动成为管理员）
2. 创建一个 **Project**（如 "AutoMind"）
3. 进入 Project Settings → API Keys
4. 复制 **Public Key** 和 **Secret Key**

### Step 5: 配置 AutoMind 连接 Langfuse

将 Step 4 获取的密钥填入 `vehicle-agent/deploy/.env`：

```bash
LANGFUSE_HOST=http://<服务器IP>:3001
LANGFUSE_PUBLIC_KEY=pk-lf-<你的真实Public Key>
LANGFUSE_SECRET_KEY=sk-lf-<你的真实Secret Key>
```

然后重启后端：`docker compose restart vehicle-backend`

## 四、启动方式说明

### 4.1 全量启动 (推荐首次部署)

```bash
# 启动全部 5 个服务
docker compose up -d

# 服务列表:
#   vehicle-backend   - AutoMind 后端 (端口 8001)
#   vehicle-frontend  - AutoMind 前端 (端口 5174)
#   langfuse          - Langfuse Web  (端口 3001)
#   langfuse-db       - Langfuse DB   (内部端口 5432)
#   chromadb          - ChromaDB      (端口 8002)
```

### 4.2 单独启动 Langfuse (先部署调试)

```bash
# 只启动 Langfuse + 数据库
docker compose up -d langfuse langfuse-db

# 查看 Langfuse 日志
docker compose logs -f langfuse

# 等调试好后再启动后端
docker compose up -d vehicle-backend

# 全部启动后，最后启动前端
docker compose up -d vehicle-frontend
```

### 4.3 其他常用操作

```bash
# 只重启后端
docker compose restart vehicle-backend

# 前端代码改了需要重新构建
docker compose up -d --build vehicle-frontend

# 查看 Langfuse 健康状态
curl http://<服务器IP>:3001/api/health

# 停止所有服务
docker compose down

# 只停止 Langfuse
docker compose down langfuse langfuse-db
```

## 五、本地开发连接服务器 Langfuse

本地开发时，前后端在本地跑，但 Langfuse 在服务器上。只需要修改本地 `.env`：

### 5.1 修改本地 backend/.env

```bash
# vehicle-agent/backend/.env (本地开发用)

# 将 LANGFUSE_HOST 指向服务器 (原来是 localhost)
LANGFUSE_HOST=http://<服务器IP>:3001

# 填入从 Langfuse 控制台获取的真实 API Key
LANGFUSE_PUBLIC_KEY=pk-lf-<你的真实Public Key>
LANGFUSE_SECRET_KEY=sk-lf-<你的真实Secret Key>
```

### 5.2 启动本地前后端

```bash
# 后端 (本地)
cd vehicle-agent/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 前端 (本地)
cd vehicle-agent/frontend
npm run dev
```

### 5.3 验证 Trace 数据流向

1. 在本地浏览器访问 `http://localhost:5174` 使用 AutoMind
2. 打开服务器 Langfuse 控制台 `http://<服务器IP>:3001`
3. 查看 Trace 数据是否出现 — 如果 `LANGFUSE_HOST` 和密钥正确，数据会自动发送到服务器

### 5.4 本地 LangGraph Studio 调试

```powershell
# PowerShell (Windows)
$env:PYTHONUTF8=1
cd vehicle-agent/backend
langgraph dev --allow-blocking
```

LangGraph Studio 和 Langfuse 是互补的：
- **LangGraph Studio** — 看图的执行流程（supervisor 路由、节点状态），本地实时调试
- **Langfuse** — 看完整的 LLM trace（prompt/completion/token/latency），数据持久化，跨环境汇总

两者可以同时启用，互不干扰。

## 六、验证

```bash
curl http://<服务器IP>:3001/api/health
# 应返回 {"status":"ok"}
```

发送一条消息给 AutoMind（如"空调调低点"），然后在 Langfuse 控制台查看：

- **Trace 树状图** — supervisor → vehicle_agent → tool call
- **每次 LLM 调用** — prompt / completion / token / latency
- **工具调用详情** — set_climate 的参数和返回值

## 七、统一 .env 配置说明

所有服务共用 `vehicle-agent/deploy/.env`，关键变量：

| 区块 | 变量 | 说明 |
|------|------|------|
| Server IP | SERVER_IP | 服务器公网IP，Langfuse URL 依赖此值 |
| Backend | BACKEND_PORT, LLM_API_KEY, LLM_MODEL | 后端服务配置 |
| Langfuse 服务 | LANGFUSE_DB_PASSWORD, NEXTAUTH_SECRET, APP_SECRET | Langfuse 自身密钥（必须改！） |
| Langfuse API | LANGFUSE_HOST, PUBLIC_KEY, SECRET_KEY | AutoMind 发送 trace 的连接配置 |
| Frontend | FRONTEND_PORT, VITE_BACKEND_URL | 前端构建配置 |

注意区分两个 SECRET_KEY：
- `LANGFUSE_APP_SECRET` — Langfuse 服务内部密钥（部署时 openssl 生成）
- `LANGFUSE_SECRET_KEY` — AutoMind 连接 Langfuse 的 API Secret Key（从 Langfuse 控制台获取）

## 八、常见问题

| 问题 | 解决方案 |
|------|----------|
| 端口 3001 无法访问 | 检查防火墙: `firewall-cmd --add-port=3001/tcp` |
| Langfuse 容器启动失败 | `docker compose logs langfuse` 查看，通常是 DB 连接错误 |
| Trace 数据未出现 | 确保 LANGFUSE_PUBLIC_KEY / SECRET_KEY 为真实值 |
| 后端报 "Langfuse 未配置" | 检查 .env 中密钥是否填写 |
| 本地开发 trace 不进服务器 | 检查 backend/.env 的 LANGFUSE_HOST 是否指向服务器IP |
| 前端改代码后页面没更新 | 需要 `docker compose up -d --build vehicle-frontend` |

## 九、安全建议

1. **关闭公开注册** — 创建管理员后设置 `LANGFUSE_ENABLE_SIGNUP: "false"`
2. **数据库密码** — 使用 openssl 生成，不要用默认值 changeme123
3. **deploy/.env** — 不要提交到 Git（已在 .gitignore 中排除）
4. **定期备份** — `docker compose exec langfuse-db pg_dump -U langfuse langfuse > backup.sql`
