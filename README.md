# Mahongwei Studio

全栈 Web 应用平台，集技术博客、AI 智能对话和 RAG 知识库于一体。

## 功能特性

- **技术博客** — Markdown 文章发布与阅读
- **AI 对话** — 多模型智能对话（DeepSeek、通义千问等 OpenAI 兼容接口）
- **RAG 知识库** — 上传文档（PDF/DOCX/TXT/MD/CSV/HTML）构建知识库，AI 自动检索相关内容进行问答
- **Langfuse 可观测性** — LLM 调用追踪与分析

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + Vite 6 + TypeScript + Tailwind CSS 4 |
| 后端 | Python FastAPI + OpenAI SDK |
| 向量数据库 | Qdrant |
| 文本嵌入 | SiliconFlow API (BAAI/bge-m3) |
| 部署 | Docker Compose + Nginx + Let's Encrypt |

## 项目结构

```
├── web/            # React 前端
├── ai-server/      # Python AI 后端（FastAPI + RAG）
├── vehicle-agent/  # 独立副项目：车载智能助手
├── deploy/         # Docker 部署配置
└── docs/           # 项目文档
```

## 快速开始

### Docker 部署（生产环境）

```bash
cd deploy
cp .env.example .env
nano .env  # 填入所有 API Key 和密码
docker compose up -d --build
```

访问 https://mahongwei.com.cn

### 本地开发

```bash
# 1. 启动 Qdrant（向量数据库）
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant

# 2. 启动 AI 后端
cd ai-server
python -m venv .venv && .venv/Scripts/Activate.ps1
pip install -r requirements.txt
cp .env.example .env  # 编辑填入 API Key
uvicorn app.main:app --reload --port 8000

# 3. 启动前端
cd web
npm install
npm run dev
```

访问 http://localhost:5173

---

## Docker 运维命令速查

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

# 强制重新构建（忽略缓存，依赖变更后用）
docker compose build --no-cache web
docker compose up -d web
```

### 重启（不重新构建，只重启容器）

```bash
# 重启某个服务
docker compose restart web
docker compose restart ai-server
docker compose restart vehicle-backend
docker compose restart vehicle-frontend
docker compose restart vehicle-runtime
docker compose restart nginx

# 重启全部服务
docker compose restart
```

### 停止

```bash
# 停止全部服务（不删除数据）
docker compose down

# 停止全部 + 删除数据卷（慎用，会清空知识库数据）
docker compose down -v
```

### 查看日志

```bash
# 查看所有服务日志（实时）
docker compose logs -f

# 查看单个服务日志
docker compose logs -f web
docker compose logs -f ai-server
docker compose logs -f vehicle-backend
docker compose logs -f nginx

# 查看最近 100 行日志
docker compose logs --tail 100 ai-server
```

### 调试 & 状态

```bash
# 查看所有容器状态
docker compose ps

# 进入容器内部
docker compose exec ai-server bash
docker compose exec vehicle-backend bash
docker compose exec nginx sh
docker compose exec redis redis-cli -a redis123

# Langfuse 可观测性（默认随 docker compose up -d 启动）
docker compose logs -f langfuse-app           # Langfuse 日志
docker compose logs -f langfuse-worker        # Langfuse Worker 日志
```

### Docker 环境配置备份与还原

> 国内服务器拉取镜像经常失败，配置好镜像源后记得备份，方便以后还原。

```bash
# ===== 备份 Docker 配置 =====

# 备份 daemon.json（镜像源配置）
cp /etc/docker/daemon.json ~/docker-daemon.json.bak

# 备份 Docker 代理配置（如果有）
cp /etc/systemd/system/docker.service.d/proxy.conf ~/docker-proxy.conf.bak 2>/dev/null || true

# 备份 docker-compose 的 .env
cp deploy/.env ~/deploy-env.bak

# 备份 frp 配置
cp /etc/frp/frpc.toml ~/frpc.toml.bak 2>/dev/null || true

# 备份 ECS nginx 配置（在 ECS 上执行）
cp /etc/nginx/conf.d/mahongwei.conf ~/ecs-nginx.conf.bak 2>/dev/null || true


# ===== 还原 Docker 配置 =====

# 还原 daemon.json（镜像源）
cp ~/docker-daemon.json.bak /etc/docker/daemon.json
sudo systemctl daemon-reload
sudo systemctl restart docker

# 还原 Docker 代理（如果有）
sudo mkdir -p /etc/systemd/system/docker.service.d
cp ~/docker-proxy.conf.bak /etc/systemd/system/docker.service.d/proxy.conf 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl restart docker

# 还原 .env
cp ~/deploy-env.bak deploy/.env

# 还原 frp 配置
cp ~/frpc.toml.bak /etc/frp/frpc.toml 2>/dev/null || true
sudo systemctl restart frpc


# ===== 快速切换镜像源（镜像拉取失败时）=====

# 方案 1：国内镜像源（不用代理）
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "registry-mirrors": [
        "https://docker.1ms.run",
        "https://docker.xuanyuan.me",
        "https://docker.rainbond.cc"
    ],
    "log-driver": "json-file",
    "log-opts": { "max-size": "10m", "max-file": "3" }
}
EOF
sudo systemctl restart docker

# 方案 2：通过代理直连（代理能访问外网时）
# 注意：代理会绕过国内镜像源，可能访问国内服务反而变慢
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/proxy.conf > /dev/null << 'EOF'
[Service]
Environment="HTTP_PROXY=http://192.168.31.xxx:10809"
Environment="HTTPS_PROXY=http://192.168.31.xxx:10809"
Environment="NO_PROXY=localhost,127.0.0.1"
EOF
# 同时去掉 daemon.json 中的 registry-mirrors，避免冲突
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "log-driver": "json-file",
    "log-opts": { "max-size": "10m", "max-file": "3" }
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker

# 方案 3：关掉代理，只用国内镜像源
sudo rm -f /etc/systemd/system/docker.service.d/proxy.conf
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "registry-mirrors": [
        "https://docker.1ms.run",
        "https://docker.xuanyuan.me",
        "https://docker.rainbond.cc"
    ],
    "log-driver": "json-file",
    "log-opts": { "max-size": "10m", "max-file": "3" }
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker


# ===== 查看当前配置 =====
cat /etc/docker/daemon.json
ls -la /etc/systemd/system/docker.service.d/ 2>/dev/null
```

---

## 文档

- [使用说明](docs/usage.md)
- [本地开发指南](docs/local-dev.md)
- [Docker 部署（含内网穿透）](docs/deployment.md)
- [故障排除](docs/troubleshooting.md)

## 许可证

[Apache-2.0](LICENSE)
