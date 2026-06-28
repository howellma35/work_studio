# Docker 容器化部署方案

## 前置要求

| 工具 | 最低版本 | 说明 |
|------|---------|------|
| Docker | 24+ | 容器运行时 |
| Docker Compose | 2+ | 多服务编排 |
| SSL 证书 | — | Let's Encrypt 或商业证书 |

---

## 部署架构

```
用户请求 → Nginx (80/443)
  ├── /                   → Web 前端 (React SPA)
  ├── /api/ai/*           → AI 后端 (FastAPI，大模型对话 + RAG)
  └── /api/knowledge/*    → AI 后端 (FastAPI，知识库管理)
```

---

## 服务列表

| 服务 | 容器名 | 端口 | 技术栈 | 说明 |
|------|--------|------|--------|------|
| nginx | raggame-nginx | 80, 443 | Nginx Alpine | 反向代理 + SSL 终结 |
| web | raggame-web | 80 (内部) | Nginx + React SPA | 前端静态资源 |
| ai-server | raggame-ai-server | 8000 | Python FastAPI | AI 聊天 + RAG 知识库 |
| qdrant | qdrant | 6333, 6334 | Qdrant | 向量数据库 |
| langfuse | langfuse-app | 3000 | Langfuse V3 | LLM 可观测性平台 |

---

## 部署步骤

### 1. 准备环境变量

```bash
cd deploy
cp .env.example .env
vim .env
# 必须填入: LLM_API_KEY, LLM_API_BASE, EMBEDDING_API_KEY
# 可选修改: Langfuse 密码、数据库密码等
```

### 2. 准备 SSL 证书

将证书放到服务器 `/etc/letsencrypt/live/你的域名/` 目录，或修改 `deploy/nginx/nginx.conf` 中的证书路径。

如果使用 Let's Encrypt：
```bash
# 安装 certbot
apt install certbot

# 获取证书（先停 nginx 或用 webroot 模式）
certbot certonly --standalone -d 你的域名
```

### 3. 修改域名

编辑 `deploy/nginx/nginx.conf`，将所有 `mahongwei.com.cn` 替换为你的域名。

### 4. 构建并启动

```bash
cd deploy

# 构建所有镜像并后台启动
docker compose up -d --build

# 查看所有服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 5. 验证

```bash
# 健康检查
curl https://你的域名/api/health

# 浏览器访问
# https://你的域名
```

---

## 常用运维命令

```bash
# 查看单个服务日志
docker compose logs -f ai-server
docker compose logs -f qdrant

# 重启单个服务
docker compose restart ai-server

# 重新构建某个服务（代码更新后）
docker compose up -d --build ai-server

# 进入容器调试
docker compose exec ai-server bash

# 停止所有服务
docker compose down

# 停止并清除数据卷（慎用，会删除所有知识库数据）
docker compose down -v

# 清理构建缓存
docker compose build --no-cache
```

---

## 数据持久化

| Volume | 挂载路径 | 说明 |
|--------|---------|------|
| ai-logs | /app/logs | AI 后端日志 |
| qdrant-data | /qdrant/storage | 向量数据库持久化存储 |
| langfuse-db-data | /var/lib/postgresql/data | Langfuse PostgreSQL |
| langfuse-clickhouse-data | /var/lib/clickhouse | Langfuse ClickHouse |
| langfuse-redis-data | /data | Langfuse Redis |
| langfuse-minio-data | /data | Langfuse MinIO |

---

## 注意事项

1. **SSL 证书更新**：Let's Encrypt 证书每 90 天需更新，更新后 `docker compose restart nginx`
2. **日志查看**：容器内日志文件位于 `/app/logs/` 目录
3. **端口冲突**：确保宿主机 80/443/6333/8000/3000 端口未被占用
4. **环境变量**：`.env` 文件不要提交到 Git（已在 .gitignore 中排除）
5. **知识库数据**：Qdrant 数据持久化在 `qdrant-data` 卷中，删除卷将丢失所有知识库数据
