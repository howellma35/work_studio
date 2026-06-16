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
  ├── /                → Web 前端 (React SPA，内部 Nginx 提供 try_files 回退)
  ├── /api/ai/*        → AI 后端 (FastAPI，大模型对话)
  ├── /api/pdf/*       → AI 后端 (FastAPI，PDF 解析)
  ├── /api/game/*      → 游戏后端 (FastAPI，词库 API)
  └── /socket.io/*     → 游戏后端 (Socket.IO WebSocket)
```

---

## 服务列表

| 服务 | 容器名 | 端口 | 技术栈 | 说明 |
|------|--------|------|--------|------|
| nginx | raggame-nginx | 80, 443 | Nginx Alpine | 反向代理 + SSL 终结 |
| web | raggame-web | 80 (内部) | Nginx + React SPA | 前端静态资源 + SPA 路由回退 |
| ai-server | raggame-ai-server | 8000 | Python FastAPI | AI 聊天 + PDF 解析 |
| game-server | raggame-game-server | 3001 | Python FastAPI + Socket.IO | 猜词游戏 WebSocket |

> 注意：Redis 已不再需要，游戏后端使用内存排行榜。

---

## 部署步骤

### 1. 准备环境变量

```bash
# AI 后端
cd ai-server
cp .env.example .env
vim .env
# 必须填入: LLM_API_KEY, LLM_API_BASE

# 游戏后端
cd game-server
cp .env.example .env
vim .env
# 可选填入: EMBEDDING_API_KEY（不填则使用字符串匹配模式）
```

### 2. 准备 SSL 证书

将证书放到服务器 `/etc/letsencrypt/live/你的域名/` 目录，或修改 `deploy/nginx.conf` 中的证书路径。

如果使用 Let's Encrypt：
```bash
# 安装 certbot
apt install certbot

# 获取证书（先停 nginx 或用 webroot 模式）
certbot certonly --standalone -d 你的域名
```

### 3. 修改域名

编辑 `deploy/nginx.conf`，将所有 `mahongwei.com.cn` 替换为你的域名。

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
curl https://你的域名/api/health        # AI 后端
curl https://你的域名/api/game/words    # 游戏后端词库

# 浏览器访问
# https://你的域名
```

---

## 常用运维命令

```bash
# 查看单个服务日志
docker compose logs -f ai-server
docker compose logs -f game-server

# 重启单个服务
docker compose restart ai-server
docker compose restart game-server

# 重新构建某个服务（代码更新后）
docker compose up -d --build ai-server

# 进入容器调试
docker compose exec ai-server bash
docker compose exec game-server bash

# 停止所有服务
docker compose down

# 停止并清除数据卷（慎用）
docker compose down -v

# 清理构建缓存
docker compose build --no-cache
```

---

## 数据持久化

| Volume | 挂载路径 | 说明 |
|--------|---------|------|
| game-data | /app/data | 游戏词库和猜测记录 |
| game-logs | /app/logs | 游戏后端日志 |
| ai-logs | /app/logs | AI 后端日志 |

---

## Dockerfile 说明

### ai-server/Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p logs
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### game-server/Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p logs data
EXPOSE 3001
CMD ["uvicorn", "app.main:combined_app", "--host", "0.0.0.0", "--port", "3001"]
```

### web/Dockerfile

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

---

## 注意事项

1. **SSL 证书更新**：Let's Encrypt 证书每 90 天需更新，更新后 `docker compose restart nginx`
2. **日志查看**：容器内日志文件位于 `/app/logs/` 目录
3. **端口冲突**：确保宿主机 80/443/3001/8000 端口未被占用
4. **环境变量**：`.env` 文件不要提交到 Git（已在 .gitignore 中排除）
5. **词库更新**：修改 `game-server/data/words.json` 后重启 game-server 生效
