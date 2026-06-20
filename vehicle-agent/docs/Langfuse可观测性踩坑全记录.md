# Langfuse 可观测性集成 — 完整踩坑记录

> 时间线：2026-06-19 ~ 2026-06-20
> 项目：AutoMind 智能车机助手（vehicle-agent）
> 目标：用 Langfuse V3 自部署 + V4 SDK 实现全链路可观测性

---

## 一、起因：发现 Agent 未被调用

用户在 UI 中输入"空调调低点"，期望 supervisor 路由到 `vehicle_agent` 并调用 `set_climate` 工具，但 LLM 直接输出文本回复，没有走工具调用链。

**无法看到**：
- supervisor 为什么没调用 transfer 工具？
- 模型是否生成了 tool call 但被忽略了？
- 每次 LLM 调用的 prompt / completion / token 消耗是什么？

**核心需求**：需要一个可观测性平台，能追踪 LLM → Agent 路由 → 工具调用的完整链路。

---

## 二、方案选择：为什么选 Langfuse

| 方案 | 优点 | 缺点 |
|------|------|------|
| Langfuse（自部署） | 开源免费，LangChain 原生集成，支持 trace 树状图 | 需自部署 Docker 容器 |
| LangSmith | LangChain 官方，功能最全 | 收费，数据在国外 |
| LangGraph Studio | 本地开发调试，无需服务器 | 仅限本地，不能追踪生产环境 |

**最终选择**：Langfuse V3 自部署。理由：
1. 开源免费，数据自主可控
2. 与 LangChain/LangGraph 原生集成
3. 项目已预集成 Langfuse 配置，只需填 Key 即可

---

## 三、版本升级全链条（为什么从 V2 升级到 V3）

这是整个踩坑过程中最复杂的部分，涉及 **服务端版本** 和 **SDK 版本** 两条线的冲突与最终统一。

### 3.1 两个独立的版本体系

很多人容易混淆，Langfuse 有**两个独立的版本**：

| | Langfuse **服务端**（Docker 容器） | Langfuse **Python SDK**（pip 包） |
|---|---|---|
| 版本线 | V2 → V3 | V2 → V3 → V4 |
| 作用 | 运行 Langfuse Web 平台，接收和存储 traces | 在 AutoMind 后端代码里发送 traces |
| 安装方式 | `docker pull langfuse/langfuse` | `pip install langfuse` |

### 3.2 第一阶段：服务端 V2（最初方案）

最初用 `langfuse/langfuse:latest` 部署，发现 `latest` 已经是 V3，需要 ClickHouse，启动失败。当时给了**两个方案**：

- **方案A：使用 Langfuse V2 镜像**（`langfuse/langfuse:2`，不需要 ClickHouse，更简单）
- **方案B：加上 ClickHouse 容器**（V3 架构完整，但更重）

当时选了方案A，用 `langfuse/langfuse:2` 快速跑起来了。

### 3.3 第二阶段：SDK 版本冲突爆发

`pip install langfuse` 默认装了 `langfuse==4.9.1`（V4 SDK），但 V4 SDK 的 API 和 V2/V3 SDK 完全不同：

| 操作 | V2/V3 SDK | V4 SDK |
|------|-----------|--------|
| CallbackHandler 导入 | `from langfuse.callback import CallbackHandler` | ❌ 模块不存在 |
| LangChain 集成 | CallbackHandler 自动追踪 | `@observe` 装饰器 或 `from langfuse.langchain import CallbackHandler` |
| 数据传输协议 | REST API | OpenTelemetry (OTLP) |

**尝试 1：降级 SDK 到 V2** → 失败。V2 SDK 的 CallbackHandler 依赖旧版 `langchain.callbacks.base`，而项目用的 LangChain 1.3+ 已把 callbacks 移到 `langchain_core.callbacks`，模块路径不兼容。

**尝试 2：用 V4 SDK 的 `@observe` 装饰器** → 失败。装饰器放错位置（放在了 `build_supervisor_graph` 上，这个函数只在启动时调用一次），实际用户请求路径（`POST /agent` → AG-UI → graph → LLM）上没有任何 `@observe`，不产生 trace。

**尝试 3：V4 SDK + V2 服务端** → 失败。V4 SDK 内部用 OTLP 协议发送数据，V2 服务端不支持 OTLP，导出报 `401 Unauthorized`。

### 3.4 第三阶段：用户拒绝临时方案

用户明确说：**"我不需要你给临时简单方案，我要你调研业界最主流的方案，不可能都用各种补丁、临时方案来解决，我要一个完美能找工作的项目"**

### 3.5 第四阶段：调研官方文档，确定最终方案

调研 Langfuse 官方文档后发现：

- V4 SDK 有 `from langfuse.langchain import CallbackHandler`（官方标准 LangChain/LangGraph 集成方式）
- 这个 CallbackHandler 通过 **OTLP 协议** 发送数据，需要 **V3 服务端** 才能正确处理
- V3 服务端的数据摄入管道：API → Redis 队列 → Worker → ClickHouse

**结论**：必须服务端升级到 V3 + SDK 使用 V4 的 CallbackHandler，两者配合才能工作。

### 3.6 备用方案：Langfuse Cloud

在调研过程中，考虑到 2GB 服务器跑 V3 全栈太重，给了一个**明确的备用方案**：

> **用 Langfuse Cloud（免费，每月 5M events）**
>
> - 代码端只需改 `LANGFUSE_BASE_URL` 指向 Cloud
> - CallbackHandler 等代码完全不变
> - 服务器上删掉 Langfuse 相关的 6 个容器，内存压力立刻解除
> - 业界主流做法：很多 demo 项目都用 Cloud 而非自部署

这个备用方案最终没有被采用（因为用户升级了服务器内存到 3.4GB），但如果服务器资源不足，这是最合理的退路。

### 3.7 版本冲突总结图

```
时间线：

V2 服务端 ──→ V4 SDK 装了 ──→ import 失败 ──→ 降级 SDK ──→ LangChain 不兼容
     │              │                │               │               │
     │              │                │               │          换 @observe
     │              │                │               │               │
     │              │                │               │          放错位置
     │              │                │               │               │
     │              │                │               │          V4+V2 OTLP 401
     │              │                │               │               │
     │              │                │               │          用户拒绝临时方案
     │              │                │               │               │
     │              │                │               │     调研官方文档
     │              │                │               │               │
     └──────────────┴────────────────┴───────────────┴───── V3 服务端 + V4 SDK CallbackHandler ✅
```

---

## 四、踩坑全过程（按时间线）

### 坑 0：`langgraph dev` 命令找不到 — 本地部署失败

**现象**：
```powershell
PS E:\githubcode\rag_game\vehicle-agent\backend> langgraph dev
langgraph : 无法将"langgraph"项识别为 cmdlet、函数、脚本文件或可运行程序的名称。
```

**原因**：`langgraph-cli` 没有安装，或者安装了但不在 PATH 中。Windows 下 Python 全局包和虚拟环境包的 bin 目录行为不一致，`langgraph` 命令无法直接识别。

**影响**：本地 LangGraph Studio（可视化调试工具）无法启动，**被迫转向服务器部署**。这直接导致了后续一系列 Docker 部署的问题。

**经验**：
- LangGraph Studio 目前对 Windows 支持不友好，更适合 Linux/macOS 开发环境
- 如果要在 Windows 本地用，需要确认 `pip install langgraph-cli[inmem]` 后 Scripts 目录在 PATH 中
- 服务器部署才是生产级方案，本地 Studio 仅用于开发调试

---

### 坑 1：LangGraph Studio 启动失败 — blockbuster 阻塞检测

**现象**：`langgraph dev` 启动后报 `Failed to preview graph`。

**原因**：`langgraph-cli[inmem]` 自带的 `blockbuster` 库检测到 `jsonschema` 包 import 时的同步阻塞调用（`ScandirIterator`），拦截后导致图构建失败。

**解决**：加 `--allow-blocking` 标志启动。

```bash
$env:PYTHONUTF8=1; langgraph dev --allow-blocking
```

**额外发现**：Windows 下 Python 默认用 GBK 编码，需要设置 `PYTHONUTF8=1` 强制 UTF-8 模式。

---

### 坑 1.5：阿里云安全组 3001 端口未开放

**现象**：Docker 容器全部正常启动，`docker compose ps` 显示 Up，但浏览器访问 `http://115.29.236.248:3001` 无法打开页面，连接超时。

**原因**：阿里云 ECS 默认只开放了少数端口（22、80、443 等），**3001 端口没有在安全组入方向规则中放行**。Docker 容器虽然在监听 3001，但云服务器的防火墙把外部请求拦截了。

**排查**：
```bash
# 服务器上本地访问（能通说明容器没问题）
curl http://localhost:3001

# 本地浏览器访问（不通说明是网络/防火墙问题）
# 浏览器打开 http://115.29.236.248:3001 → 超时
```

**解决**：
1. 登录阿里云控制台 → ECS → 安全组
2. 添加入方向规则：
   - 协议类型：TCP
   - 端口范围：3001/3001
   - 授权对象：0.0.0.0/0（或你的 IP）
3. 保存后**立即生效**，无需重启

**经验**：
- 阿里云/腾讯云等云服务器，**每个端口都需要在安全组中手动放行**
- Docker `-p 3001:3001` 只是容器到宿主机的映射，宿主机防火墙是另一层
- 排查思路：先 `curl localhost:端口` 确认容器正常，再检查安全组
- 常见需要放行的端口：3000、3001、5432、6379、8123（ClickHouse）等

---

### 坑 2：Langfuse V2 → V3 架构升级，缺少依赖

**现象**：初始用 `docker run -d -p 3000:3000 langfuse/langfuse` 一行命令部署，启动后日志报 `CLICKHOUSE_URL not configured, skipping migration`。

**原因**：Langfuse V3 相比 V2 架构大改，从单 PostgreSQL 变为需要 **PostgreSQL + ClickHouse + Redis + MinIO** 四个依赖。单容器 `langfuse/langfuse` 只是 V2 用法。

**解决**：重写 `docker-compose.yml`，补全所有依赖容器。

---

### 坑 2.5：NEXTAUTH_URL 用了 localhost — 注册跳转失败

**现象**：Langfuse 页面能打开，但注册账户时跳转到 `http://localhost:3001/`，导致失败。

**原因**：`.env` 中 `SERVER_IP=localhost`，NextAuth 注册回调时用这个值构建重定向 URL，但 `localhost` 是服务器自己，不是用户的浏览器。

**解决**：把 `.env` 中 `SERVER_IP` 改为服务器真实 IP（`115.29.236.248`），`NEXTAUTH_URL` 变为 `http://115.29.236.248:3001`。重启容器（`docker compose up -d --force-recreate langfuse`）使新配置生效。

**经验**：所有需要生成重定向 URL 的服务（NextAuth、OAuth 等），都必须配置为**外部可访问的地址**，不能用 localhost。

---

### 坑 2.6：Redis 密码变量名错误 — REDIS_PASSWORD vs REDIS_AUTH

**现象**：`Redis error WRONGPASS invalid username-password pair or user is disabled.`

**原因**：Langfuse V3 源码中读取 Redis 密码用的是 `REDIS_AUTH` 环境变量（不是 `REDIS_PASSWORD`）。我们之前配的是 `REDIS_PASSWORD`，导致 Langfuse 用空密码去 AUTH Redis。

**源码证据**（`packages/shared/src/server/redis/redis.ts`）：
```typescript
password: String(env.REDIS_AUTH),  // ← 用的是 REDIS_AUTH
```

**解决**：docker-compose.yml 中 Redis 密码变量名改为 `REDIS_AUTH`。

---

### 坑 2.7：缺少 CLICKHOUSE_MIGRATION_URL

**现象**：`Error: CLICKHOUSE_MIGRATION_URL is not configured.`

**原因**：V3 需要两个 ClickHouse 连接 URL：
- `CLICKHOUSE_URL`（HTTP 协议，端口 8123）— 日常查询写入
- `CLICKHOUSE_MIGRATION_URL`（ClickHouse native TCP，端口 9000）— 数据库迁移建表

之前只配了 HTTP 的，没配 TCP 的。

**解决**：添加 `CLICKHOUSE_MIGRATION_URL: clickhouse://langfuse-clickhouse:9000`

---

### 坑 3：端口 3000 被占用

**现象**：`Bind for 0.0.0.0:3000 failed: port is already allocated`

**原因**：服务器上已有其他服务占用 3000 端口。

**解决**：改 `deploy/.env` 中 `LANGFUSE_PORT=3001`，访问地址改为 `http://服务器IP:3001`。

---

### 坑 2.8：缺少 LANGFUSE_S3_EVENT_UPLOAD_BUCKET — MinIO 配置不完整

**现象**：`Error [ZodError]: Invalid input: expected string, received undefined` at `LANGFUSE_S3_EVENT_UPLOAD_BUCKET`

**原因**：Langfuse V3 强制要求 S3 存储（用于事件上传和媒体文件），不配就启动不了。需要加 MinIO（S3 兼容存储）容器，并配置 bucket 名称。

**解决**：
1. 添加 MinIO 容器 + 初始化容器（自动创建 bucket）
2. 配置 `LANGFUSE_S3_EVENT_UPLOAD_BUCKET: langfuse`
3. 配置 `LANGFUSE_S3_MEDIA_UPLOAD_BUCKET: langfuse`
4. 配置 S3 endpoint、access key、secret key 等

---

### 坑 4：ClickHouse 集群模式报错 — ReplicatedMergeTree 需要 Zookeeper

**现象**：`Code: 337. DB::Exception: Cannot create ReplicatedMergeTree, because there is no ZooKeeper`

**原因**：ClickHouse 默认使用 `ReplicatedMergeTree` 引擎（集群模式），需要 Zookeeper。单节点部署不需要集群。

**解决**：添加环境变量 `CLICKHOUSE_CLUSTER_ENABLED: "false"`，使 ClickHouse 使用 `MergeTree` 引擎（单节点模式）。

---

### 坑 5：`@observe` 装饰器阻塞 HTTP 请求

**现象**：使用 V4 SDK 的 `@observe` 装饰器后，每次聊天请求都会阻塞，前端长时间无响应。

**原因**：`@observe` 装饰器在同步上下文中执行 Langfuse 的 HTTP 上报，阻塞了 FastAPI 的异步事件循环。

**解决**：放弃 `@observe` 装饰器，改用 Langfuse V4 SDK 的 **CallbackHandler** 方案。这是官方推荐的 LangChain/LangGraph 标准集成方式。

---

### 坑 6：V4 SDK 导入路径变更

**现象**：`No module named 'langfuse.callback'`

**原因**：V4 SDK 重新组织了模块结构，CallbackHandler 的路径从 V2 的 `langfuse.callback` 变为 `langfuse.langchain`。

**解决**：改为 `from langfuse.langchain import CallbackHandler`。

---

### 坑 7：环境变量命名不一致 — `LANGFUSE_HOST` vs `LANGFUSE_BASE_URL`

**现象**：配置了 `LANGFUSE_HOST` 但 V4 SDK 似乎没读到。

**原因**：V4 SDK 官方环境变量名是 `LANGFUSE_BASE_URL`（非 `LANGFUSE_HOST`）。虽然 `LANGFUSE_HOST` 作为兼容仍有效，但官方推荐使用 `LANGFUSE_BASE_URL`。

**解决**：统一改为 `LANGFUSE_BASE_URL`，config.py 中加 fallback：
```python
LANGFUSE_BASE_URL: str = os.getenv("LANGFUSE_BASE_URL", os.getenv("LANGFUSE_HOST", "http://localhost:3000"))
```

---

### 坑 8：API Key 搞反 — pk/sk 互换

**现象**：V4 SDK 的 OTLP 导出报 `Failed to export span batch code: 401, reason: Unauthorized`。REST API 也报认证异常。

**原因**：用户把 `sk-lf-xxx`（Secret Key）填到了 `LANGFUSE_PUBLIC_KEY`，把 `pk-lf-xxx`（Public Key）填到了 `LANGFUSE_SECRET_KEY`。

**命名规则**：
- `pk-lf-xxx` = **P**ublic **K**ey → `LANGFUSE_PUBLIC_KEY`
- `sk-lf-xxx` = **S**ecret **K**ey → `LANGFUSE_SECRET_KEY`

**解决**：纠正 .env 中的 Key 对应关系。

---

### 坑 9（核心坑）：缺少 langfuse-worker 容器

**现象**：
- POST `/api/public/traces` 返回 200（接受 trace）
- GET `/api/public/traces` 返回 `totalItems=0`（查不到任何数据）
- Langfuse 控制台永远显示 "Waiting for first trace"

**原因**：Langfuse V3 需要 **两个** 应用容器：

| 容器 | 镜像 | 作用 |
|------|------|------|
| `langfuse-web` | `langfuse/langfuse:3` | 前端 UI + REST API |
| `langfuse-worker` | `langfuse/langfuse-worker:3` | 后台处理（Redis → ClickHouse） |

**数据流**：
```
SDK → langfuse-web (API) → Redis 队列 → langfuse-worker → ClickHouse 存储
                                         ↑
                                  没有这个！数据进了队列无人处理
```

没有 worker 容器 = trace 数据进入 Redis 队列后无人消费 = 永远不写入 ClickHouse。

**解决**：在 docker-compose.yml 中添加 `langfuse-worker` 容器，对照官方 `docker-compose.yml` 补全配置。

---

### 坑 10（最终根因）：Redis Socket Timeout — 服务器内存不足

**现象**：
```
Redis error Socket timeout. Expecting data, but didn't receive any in 30000ms.
Redis error connect ETIMEDOUT
```
langfuse-web 和 langfuse-worker 持续报 Redis 超时，worker 中所有 BullMQ 队列任务（otel-ingestion-queue、dataset-delete-queue 等）全部失败。

**排查过程**（逐步排除法）：

1. **Redis 本地测试** → `INFO server | grep loading` 无输出 → ❌ 排除 RDB 加载
2. **跨容器 TCP 测试** → `AUTH redis123 + PING` 立即返回 `+OK +PONG` → ❌ 排除 Docker 网络
3. **DNS 解析测试** → `langfuse-redis` 解析到 `172.19.0.2` → ❌ 排除 DNS 问题
4. **环境变量检查** → `REDIS_HOST`、`REDIS_PORT`、`REDIS_AUTH` 均正确传递 → ❌ 排除配置错误

**关键矛盾**：手动 TCP 测试立刻成功，但 ioredis 持续 30 秒超时。问题不在网络层。

**源码分析**（`packages/shared/src/server/redis/redis.ts`）：
```typescript
const defaultRedisOptions = {
  enableReadyCheck: true,
  maxRetriesPerRequest: null,
  socketTimeout: 30000,  // ← Langfuse 硬编码 30 秒
  keepAlive: 10000,
};
```

**根因**：旧服务器内存仅 2GB，Langfuse V3 全栈稳定运行需求约 1.8GB（ClickHouse ~800MB + PostgreSQL ~200MB + langfuse-web ~300MB + langfuse-worker ~300MB + Redis + MinIO）。ClickHouse 迁移期间内存峰值导致系统压力过大，Redis 响应变慢，触发 ioredis 的 30 秒 socketTimeout。

**解决**：升级服务器到 3.4GB RAM + 4GB Swap → **Socket timeout 彻底消失**。

---

## 五、最终架构

### 服务端（Docker Compose）

```
┌─────────────────────────────────────────────────────┐
│  服务器 (115.29.236.248, 3.4GB RAM + 4GB Swap)      │
│                                                     │
│  ┌─────────────┐  ┌─────────────────────────────┐   │
│  │  langfuse-web│  │  langfuse-worker            │   │
│  │  :3001       │  │  (后台处理 Redis → CH)       │   │
│  └──────┬───────┘  └──────────┬──────────────────┘   │
│         │                     │                      │
│  ┌──────┴─────────────────────┴──────┐               │
│  │  Redis (队列 + 缓存)              │               │
│  └───────────────────────────────────┘               │
│  ┌─────────────┐  ┌──────────┐  ┌────────────┐      │
│  │  ClickHouse │  │PostgreSQL│  │   MinIO    │      │
│  │  (分析存储)  │  │(元数据)  │  │  (S3对象)  │      │
│  └─────────────┘  └──────────┘  └────────────┘      │
└─────────────────────────────────────────────────────┘
```

### 客户端（V4 SDK CallbackHandler）

```python
# observability.py — CallbackHandler 单例
from langfuse.langchain import CallbackHandler
_langfuse_handler = CallbackHandler()

# main.py — 注入到 LangGraphAgent
agent = LangGraphAgent(
    name="automind",
    graph=graph,
    config={"callbacks": [langfuse_handler]},
)
```

**追踪覆盖**：LLM 调用 / 工具调用 / Agent 路由 / 节点执行 → 自动生成 trace 树状图。

### 关键配置文件

| 文件 | 用途 |
|------|------|
| `vehicle-agent/deploy/docker-compose.yml` | 服务端全栈部署 |
| `vehicle-agent/deploy/.env` | 服务端环境变量（密钥、端口） |
| `vehicle-agent/backend/.env` | 本地开发环境变量 |
| `vehicle-agent/backend/app/utils/observability.py` | CallbackHandler 初始化 |
| `vehicle-agent/backend/app/main.py` | 注入 handler 到 LangGraphAgent |
| `vehicle-agent/backend/app/config.py` | LANGFUSE_BASE_URL 配置 |

---

# 六、核心经验总结

### 1. 部署前的环境检查清单

| 检查项 | 说明 | 踩坑案例 |
|--------|------|----------|
| 本地 CLI 工具是否可用 | `langgraph dev` 等命令能否执行 | Windows 下 `langgraph` 命令找不到，被迫转服务器 |
| 云服务器安全组 | 需要的端口是否已放行 | 3001 端口没开，容器正常运行但外部无法访问 |
| 服务器内存 | 是否满足最低要求 | 2GB 服务器跑 V3 全栈 → Redis OOM → Socket timeout |
| 端口冲突 | 目标端口是否被其他服务占用 | 3000 端口被占用，改到 3001 |
| Docker 版本 | docker compose v2 是否可用 | 旧版 `docker-compose` vs 新版 `docker compose` |

### 2. 服务器内存最低要求

Langfuse V3 自部署**最低 3GB RAM**（推荐 4GB+）：

| 容器 | 内存占用 |
|------|---------|
| ClickHouse | 500MB - 2GB（迁移时峰值） |
| langfuse-web (Node.js) | ~300MB |
| langfuse-worker (Node.js) | ~300MB |
| PostgreSQL | ~200MB |
| Redis | ~50MB |
| MinIO | ~100MB |
| **合计** | **~1.5GB - 3GB** |

### 3. 必须对照官方 docker-compose.yml

Langfuse V3 官方 compose 文件：https://github.com/langfuse/langfuse/blob/main/docker-compose.yml

关键差异点：
- **必须包含 `langfuse-worker` 容器**（不是只有 `langfuse`）
- Redis 密码变量名是 `REDIS_AUTH`（不是 `REDIS_PASSWORD`）
- 环境变量名是 `LANGFUSE_BASE_URL`（不是 `LANGFUSE_HOST`）
- MinIO bucket 名称是 `langfuse`（不是自定义名）
- ClickHouse 单节点必须设 `CLICKHOUSE_CLUSTER_ENABLED: "false"`

### 4. V4 SDK 集成标准方案

不要自己拼凑 `@observe` + monkey patch。V4 SDK 官方标准方案：
- LangChain/LangGraph → **CallbackHandler**（`from langfuse.langchain import CallbackHandler`）
- 注入方式 → `config={"callbacks": [handler]}`
- 环境变量 → `LANGFUSE_BASE_URL` + `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY`

### 5. 版本匹配铁律

> **服务端版本和 SDK 版本必须匹配，不能随意组合。**

| 组合 | 结果 |
|------|------|
| V2 服务端 + V2 SDK | ✅ 能工作，但 V2 SDK 与新版 LangChain 不兼容 |
| V2 服务端 + V4 SDK | ❌ OTLP 协议不兼容，报 401 |
| V3 服务端 + V4 SDK CallbackHandler | ✅ **唯一正确的生产组合** |
| V3 服务端 + V2 SDK | ❌ API 路径变更，部分功能不可用 |

**教训**：不要先装 SDK 再想服务端，应该**先确定服务端版本，再选匹配的 SDK 版本和 API**。

### 6. 排查方法论

遇到问题时的排查顺序：
1. **先看日志** — `docker compose logs` 确认具体报错
2. **排除网络** — 跨容器 TCP 测试 + 安全组检查
3. **排除配置** — `docker exec printenv` 检查容器内环境变量
4. **查官方源码** — 直接读 Langfuse 源码中的连接逻辑
5. **对比官方 compose** — 逐行对比官方和自己的 docker-compose.yml
6. **检查资源** — `docker stats`、`free -h`、`dmesg | grep -i oom` 排查内存/CPU 问题

### 7. 不要跳过基础检查

本次踩坑中，如果一开始就检查以下三项，可以节省大量时间：

```bash
# 1. 端口是否对外开放（安全组）
curl http://服务器IP:3001  # 从本地电脑执行

# 2. 内存是否充足
free -h  # 看 available 列

# 3. 容器是否真的在运行
docker compose ps  # 看 Status 列是否全部 Up
```

**教训**：很多问题不是代码问题，是**基础设施配置遗漏**。先确认基础设施正常，再排查代码层面。

---

## 附录：完整踩坑时间线

```
Day 1: 发现问题 → 想本地调试
├─ 输入"空调调低点"，Agent 没被调用
├─ 想打开 LangGraph Studio 看链路
├─ ❌ 坑0: `langgraph dev` 命令找不到
├─ 安装 langgraph-cli，解决编码问题
├─ ❌ 坑1: blockbuster 阻塞检测 → 加 --allow-blocking
├─ 本地 Studio 能用但不够直观
└─ 决定：服务器部署 Langfuse

Day 1: 服务器部署 Langfuse
├─ docker run langfuse/langfuse:latest
├─ ❌ 坑2: V3 需要 ClickHouse → 降级到 V2 镜像
├─ ❌ 坑2.5: NEXTAUTH_URL 用了 localhost → 注册跳转失败
├─ ❌ 坑1.5: 阿里云安全组 3001 端口没开 → 外部无法访问
├─ ❌ 坑3: 端口 3000 被占用 → 改到 3001
└─ ✅ V2 服务端跑起来了！

Day 1-2: SDK 版本冲突
├─ pip install langfuse → 装了 V4 SDK (4.9.1)
├─ ❌ 坑6: `from langfuse.callback import CallbackHandler` → 模块不存在
├─ 尝试降级 SDK 到 V2 → ❌ LangChain 1.3+ 不兼容
├─ 改用 V4 @observe 装饰器 → ❌ 放错位置，无 trace
├─ ❌ V4 SDK + V2 服务端 → OTLP 401 Unauthorized
├─ 用户拒绝临时方案
├─ 调研官方文档 → 发现 `from langfuse.langchain import CallbackHandler`
└─ 决定：升级到 V3 服务端 + V4 SDK CallbackHandler

Day 2: 升级到 V3 服务端
├─ 加 ClickHouse 容器
├─ ❌ 坑2.7: 缺少 CLICKHOUSE_MIGRATION_URL
├─ ❌ 坑4: ClickHouse ReplicatedMergeTree 需要 Zookeeper → 加 CLICKHOUSE_CLUSTER_ENABLED=false
├─ ❌ 坑2.8: 缺少 LANGFUSE_S3_EVENT_UPLOAD_BUCKET → 加 MinIO 容器
├─ ❌ 坑2.6: Redis 密码变量名 REDIS_PASSWORD 应该是 REDIS_AUTH
├─ ❌ 坑9: 缺少 langfuse-worker 容器 → 数据进了 Redis 队列无人处理
├─ ❌ 坑8: API Key pk/sk 搞反了
└─ 配置对照官方 docker-compose.yml 全部修正

Day 2: Redis Socket Timeout 排查
├─ ❌ 坑10: Redis error Socket timeout 30000ms
├─ 排查：Redis 本地 ✅、TCP 跨容器 ✅、DNS ✅、环境变量 ✅
├─ 矛盾：手动 TCP 立刻成功，ioredis 持续 30s 超时
├─ 源码分析：socketTimeout: 30000 是 Langfuse 硬编码
├─ 用户提到：服务器内存只有 2GB
├─ 分析：V3 全栈需要 ~1.8GB，ClickHouse 迁移峰值超出 → OOM
└─ 用户升级服务器到 3.4GB + 4GB Swap

Day 2: 最终解决
├─ 升级内存后重启所有容器
├─ 清除所有旧 volume 彻底重建
├─ Socket timeout 彻底消失 ✅
├─ 重新注册账户，生成新 API Key
├─ 更新本地 .env 配置
└─ ✅ Langfuse V3 + V4 SDK CallbackHandler 完全正常工作
```

**总计踩坑数：13 个**（坑0 ~ 坑10，其中坑2 包含 2.5/2.6/2.7/2.8 四个子坑）

**耗时：约 2 天**

**根本原因分类**：
| 类型 | 数量 | 案例 |
|------|------|------|
| 基础设施配置 | 4 | 安全组端口、内存不足、端口占用、localhost |
| 版本不兼容 | 4 | V2+V4 OTLP、V2 SDK+LangChain 1.3、V4 模块路径、@observe 位置 |
| 缺少依赖组件 | 3 | worker容器、ClickHouse、MinIO |
| 配置变量错误 | 2 | REDIS_AUTH 变量名、CLICKHOUSE_MIGRATION_URL |
