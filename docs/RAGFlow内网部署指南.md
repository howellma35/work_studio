# 2026-07-05 RAGFlow 内网服务器部署指南

> 适用环境：Ubuntu 服务器 / 32GB RAM / 内网部署 / 国内网络
> 版本：RAGFlow v0.26.3（2026年7月）
> 官方文档：https://ragflow.io/docs/dev/

---

## 一、RAGFlow 简介

RAGFlow 是由 InfiniFlow 开源的**企业级 RAG（检索增强生成）引擎**，核心能力：

- **深度文档理解**：自动解析 PDF、Word、Excel、PPT、图片等复杂格式文档
- **低幻觉问答**：基于精准文本切片，答案自带引用来源，可追溯
- **可配置 LLM**：支持 OpenAI、通义千问、DeepSeek、Ollama 等几乎所有主流大模型
- **Agent 能力**：融合智能体模板，支持自动化 RAG 工作流
- **Docker 一键部署**：无需复杂环境配置

---

## 二、硬件与环境要求

| 项目 | 最低要求 | 推荐 | 你的服务器 |
|------|---------|------|-----------|
| CPU | 4 核心 | 8 核心+ | ✅ 请确认 |
| 内存 | 16 GB | 32 GB+ | ✅ 32 GB |
| 硬盘 | 50 GB | 100 GB+ | ✅ 请确认 |
| Docker | ≥ 24.0.0 | 最新版 | ✅ 已安装 |
| Docker Compose | ≥ v2.26.1 | 最新版 | ✅ 已安装 |

**检查命令**：

```bash
# 检查 Docker 版本
docker --version

# 检查 Docker Compose 版本
docker compose version

# 检查内存
free -h

# 检查磁盘空间
df -h /
```

---

## 三、核心组件与端口规划

RAGFlow 的 Docker Compose 会启动以下服务：

| 服务 | 镜像 | 默认端口 | 作用 |
|------|------|---------|------|
| ragflow-server | infiniflow/ragflow:v0.26.3 | 80 (Web), 9380 (API) | 主服务 |
| mysql | mysql:8.0.39 | 3306 | 元数据/关系数据库 |
| elasticsearch | elasticsearch:8.11.3 | 1200 (HTTP), 9200 (内部) | 向量+全文检索 |
| minio | minio | 9000 (API), 9001 (Console) | 对象存储 |
| redis/valkey | valkey:8 | 6379 | 缓存/任务队列 |
| tei (可选) | text-embeddings-inference | 6380 | 嵌入模型服务 |

### ⚠️ 端口冲突处理

你的服务器已经运行了以下服务，**存在端口冲突**：

| 冲突端口 | 已占用服务 | RAGFlow 需要的 | 解决方案 |
|---------|-----------|----------------|---------|
| 80 | nginx（主站） | RAGFlow Web | **改 RAGFlow Web 端口为 9380**，或通过现有 nginx 代理 |
| 6379 | redis（已有） | RAGFlow Redis | **复用现有 Redis**，或改 RAGFlow Redis 端口为 6380 |
| 3306 | 无冲突 | MySQL | 保持默认即可 |

**推荐方案**：让 RAGFlow 使用独立端口，通过你现有的 Nginx 反向代理统一入口。

---

## 四、部署步骤

### 步骤 1：配置系统参数（vm.max_map_count）

Elasticsearch 要求 `vm.max_map_count ≥ 262144`，**不设置会导致 ES 启动失败**。

```bash
# 检查当前值
sysctl vm.max_map_count

# 如果值小于 262144，临时修改
sudo sysctl -w vm.max_map_count=262144

# 永久生效（重启后也不会丢失）
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

验证：
```bash
sysctl vm.max_map_count
# 输出应为：vm.max_map_count = 262144
```

---

### 步骤 2：克隆 RAGFlow 仓库

```bash
# 选择安装目录（建议放 /opt 下）
cd /opt

# 克隆仓库
git clone https://github.com/infiniflow/ragflow.git

# 进入 docker 配置目录
cd ragflow/docker
```

> ⚠️ 国内网络如果 git clone 超时，可以用 gitee 镜像：
> ```bash
> git clone https://gitee.com/mirrors/ragflow.git
> ```

---

### 步骤 3：修改 `.env` 配置文件

```bash
cd /opt/ragflow/docker
cp .env .env.local   # 备份原始配置
vim .env              # 编辑配置
```

**关键修改项**（按行号搜索修改）：

#### 3.1 切换国内镜像源（解决 Docker 拉取超时）

找到 `RAGFLOW_IMAGE` 行，**注释掉默认的，启用国内镜像**：

```env
# 默认配置（国外源，国内可能拉取超时）：
# RAGFLOW_IMAGE=infiniflow/ragflow:v0.26.3

# ✅ 使用华为云镜像（推荐，速度最快）：
RAGFLOW_IMAGE=swr.cn-north-4.myhuaweicloud.com/infiniflow/ragflow:v0.26.3

# 或者使用阿里云镜像：
# RAGFLOW_IMAGE=registry.cn-hangzhou.aliyuncs.com/infiniflow/ragflow:v0.26.3
```

#### 3.2 修改 Web 端口（避免与现有 Nginx 80 端口冲突）

```env
# 将 Web HTTP 端口改为 9380（避免与现有 nginx 的 80 端口冲突）
SVR_WEB_HTTP_PORT=9380

# HTTPS 端口也可以改，内网一般不需要 HTTPS
SVR_WEB_HTTPS_PORT=443

# API 端口保持默认
SVR_HTTP_PORT=9380
```

> ⚠️ 注意：RAGFlow 容器内部 Web 仍然监听 80 端口，`SVR_WEB_HTTP_PORT` 只是宿主机映射端口。
> 映射关系是 `${SVR_WEB_HTTP_PORT}:80`，即宿主机 9380 → 容器内 80。

#### 3.3 修改 Redis 端口（避免与现有 Redis 6379 冲突）

```env
# 将 Redis 对外端口改为 6380（避免与现有 Redis 6379 冲突）
REDIS_PORT=6380
```

> 💡 **也可以复用现有 Redis**：如果你的 Redis 密码一致，可以不启动 RAGFlow 自带的 Redis，
> 修改 `docker-compose-base.yml` 中 ragflow 的 Redis 配置指向宿主机 Redis。
> 但为简化部署，建议让 RAGFlow 用自己的 Redis（端口改 6380）。

#### 3.4 修改 MySQL 端口（可选）

```env
# MySQL 对外端口改为 3307（避免将来与其他 MySQL 冲突）
EXPOSE_MYSQL_PORT=3307
```

#### 3.5 修改 Elasticsearch 内存限制

```env
# ES 内存限制（32GB 服务器，给 ES 限制 8GB）
MEM_LIMIT=8073741824
```

#### 3.6 配置时区

```env
TZ=Asia/Shanghai
```

#### 3.7 配置 HuggingFace 镜像（国内网络必须）

```env
# 取消注释，启用 HF 镜像
HF_ENDPOINT=https://hf-mirror.com
```

#### 3.8 修改密码（⚠️ 安全必做）

```env
# 修改 Elasticsearch 密码
ELASTIC_PASSWORD=你的强密码1

# 修改 MySQL 密码
MYSQL_PASSWORD=你的强密码2

# 修改 MinIO 密码（同时要修改 service_conf.yaml 中的对应配置）
MINIO_PASSWORD=你的强密码3

# 修改 Redis 密码
REDIS_PASSWORD=你的强密码4
```

> 💡 生成随机密码命令：`openssl rand -hex 32`

---

### 步骤 4：修改 `service_conf.yaml.template`

```bash
vim /opt/ragflow/docker/service_conf.yaml.template
```

找到以下配置并修改（与 `.env` 中的密码保持一致）：

```yaml
# MinIO 配置（密码要与 .env 中 MINIO_PASSWORD 一致）
minio:
  host: minio
  port: 9000
  access_key: rag_flow          # 与 .env 中 MINIO_USER 一致
  secret_key: 你的强密码3        # 与 .env 中 MINIO_PASSWORD 一致

# Redis 配置
redis:
  host: redis
  port: 6379                     # 容器内部端口，不是对外端口
  password: 你的强密码4           # 与 .env 中 REDIS_PASSWORD 一致

# MySQL 配置
mysql:
  host: mysql
  port: 3306                     # 容器内部端口
  password: 你的强密码2           # 与 .env 中 MYSQL_PASSWORD 一致
  database: rag_flow
```

---

### 步骤 5：配置 Docker 镜像加速器

如果你拉取 RAGFlow 镜像时国内镜像源仍然慢，可以配置 Docker daemon 镜像加速：

```bash
sudo mkdir -p /etc/docker

# 编辑 daemon.json
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1panel.live",
    "https://hub-mirror.c.163.com"
  ]
}
EOF

# 重启 Docker
sudo systemctl daemon-reload
sudo systemctl restart docker
```

---

### 步骤 6：启动 RAGFlow

```bash
cd /opt/ragflow/docker

# CPU 版本（你的服务器无 GPU，用这个）
docker compose -f docker-compose.yml up -d

# GPU 版本（如果有 NVIDIA GPU）
# docker compose -f docker-compose.yml --profile gpu up -d
```

首次启动会拉取约 **10GB+** 的镜像，耐心等待（国内镜像源约 10-30 分钟）。

---

### 步骤 7：验证启动状态

```bash
# 查看所有容器状态
docker compose ps

# 所有容器应显示 "Up" 或 "healthy"
# 正常运行的容器约 5-6 个：
# - ragflow-cpu-1（或 ragflow-server）
# - mysql-1
# - es01-1（Elasticsearch）
# - minio-1
# - redis-1（或 valkey-1）
```

查看 RAGFlow 启动日志：

```bash
docker logs -f ragflow-cpu-1
# 或者
docker compose logs -f ragflow-cpu
```

**看到以下输出说明启动成功**：

```
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:9380
 * Running on http://192.168.31.xxx:9380
 INFO:werkzeug:Press CTRL+C to quit
```

> ⚠️ 如果 ES 连接失败（`Can't connect to ES cluster`），检查 `vm.max_map_count` 是否 ≥ 262144。

---

### 步骤 8：访问 RAGFlow Web 界面

浏览器访问：

```
http://192.168.31.101:9380
```

> 注意：如果 `SVR_WEB_HTTP_PORT` 改为 9380，访问地址带端口号。
> 如果保持默认 80，则直接访问 `http://192.168.31.101`。

**首次访问操作**：

1. **注册管理员账号**：填写用户名、邮箱、密码
2. 登录后，在右上角切换为**中文界面**

---

### 步骤 9：通过 Nginx 反向代理统一入口（可选但推荐）

在你的现有 Nginx 配置中添加 RAGFlow 代理规则：

```bash
vim /opt/rag_game/deploy/nginx/nginx.conf
```

在 `http` block 中添加：

```nginx
# RAGFlow 知识库平台
upstream ragflow {
    server 192.168.31.101:9380;  # RAGFlow Web 端口
}

server {
    listen 80;
    server_name ragflow.mahongwei.com.cn;  # 或用内网 IP

    location / {
        proxy_pass http://ragflow;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持（RAGFlow 对话需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 大文件上传支持
        client_max_body_size 100M;
    }
}
```

然后重启 Nginx：
```bash
docker restart nginx
```

---

## 五、配置 LLM 模型（关键步骤）

RAGFlow 本身不包含 LLM，需要对接外部大模型才能工作。

### 5.1 使用阿里云百炼（推荐，与现有项目一致）

登录 RAGFlow 后：

1. 点击右上角 **头像 → 模型提供商**
2. 找到 **Tongyi-Qianwen（通义千问/百炼）**
3. 点击 **添加模型**

**Chat 模型配置**：

| 配置项 | 值 |
|--------|---|
| 模型类型 | Chat |
| 模型名称 | deepseek-v4-flash（或其他你使用的模型） |
| API Key | 你的百炼 API Key |
| Base URL | https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1 |

**Embedding 模型配置**：

| 配置项 | 值 |
|--------|---|
| 模型类型 | Embedding |
| 模型名称 | text-embedding-v4 |
| API Key | 你的百炼 API Key |
| Base URL | https://cn-beijing.maas.aliyuncs.com/compatible-mode/v1 |

4. 在 **系统模型设置** 中，将刚添加的模型设为默认对话模型和默认嵌入模型

### 5.2 使用 Ollama 本地模型（可选）

如果你服务器上装了 Ollama：

| 配置项 | 值 |
|--------|---|
| 模型类型 | Chat |
| 模型名称 | deepseek-r1（或其他本地模型） |
| Base URL | http://192.168.31.101:11434 |

> ⚠️ Ollama Base URL 填**宿主机 IP**，不是 localhost（因为 RAGFlow 在容器内）

---

## 六、配置嵌入模型服务（v0.22+ 必须）

从 v0.22 版本开始，RAGFlow 镜像不再自带嵌入模型。你有两种选择：

### 方案 A：使用在线 API 嵌入模型（推荐，最简单）

直接在 RAGFlow Web 界面中添加在线 Embedding API（如上面 5.1 节配置的百炼 embedding），无需额外操作。

### 方案 B：使用本地 TEI 服务（离线场景）

如果服务器完全无外网，需要启动本地嵌入服务：

```bash
# 编辑 .env，取消注释以下行
vim /opt/ragflow/docker/.env

# 启用 TEI CPU 版本
COMPOSE_PROFILES=${COMPOSE_PROFILES},tei-cpu

# 选择嵌入模型（BAAI/bge-m3 推荐，需要约 21GB 内存）
TEI_MODEL=BAAI/bge-m3

# 或者用更小的模型（仅需约 1.2GB 内存）
# TEI_MODEL=BAAI/bge-small-en-v1.5

# 国内网络必须配置 HF 镜像
HF_ENDPOINT=https://hf-mirror.com
```

重启服务：
```bash
cd /opt/ragflow/docker
docker compose up -d
```

---

## 七、创建知识库并测试

1. **创建知识库**：
   - 左侧菜单 → 知识库 → 创建知识库
   - 名称：随意（如"测试知识库"）
   - 语言：中文
   - 嵌入模型：选择你配置的模型
   - 解析方法：General（通用，适合大多数文档）
   - 点击保存

2. **上传文档**：
   - 进入知识库 → 上传文件
   - 支持 PDF、Word、Excel、TXT、Markdown 等
   - 上传后点击"开始解析"

3. **创建对话助手**：
   - 左侧菜单 → 助手 → 创建助手
   - 关联你刚创建的知识库
   - 选择对话模型

4. **开始对话**：
   - 在助手对话界面输入问题，测试 RAG 效果
   - 回答会包含引用来源，可点击查看原文

---

## 八、常用运维命令

```bash
# 进入 RAGFlow docker 目录（所有命令都在此目录执行）
cd /opt/ragflow/docker

# 查看容器状态
docker compose ps

# 查看所有日志
docker compose logs

# 查看 RAGFlow 主服务日志
docker compose logs -f ragflow-cpu

# 查看 Elasticsearch 日志
docker compose logs -f es01

# 停止所有服务
docker compose down

# 重启所有服务
docker compose restart

# 重新构建并启动（修改配置后）
docker compose up -d --force-recreate

# 清理旧数据重建（⚠️ 会删除所有数据）
docker compose down -v
docker compose up -d
```

---

## 九、常见问题与排查

### 9.1 Elasticsearch 启动失败

```
Can't connect to ES cluster
```

**排查**：
```bash
# 检查 vm.max_map_count
sysctl vm.max_map_count
# 必须 ≥ 262144

# 检查 ES 日志
docker compose logs es01
```

解决：重新执行步骤 1 设置 `vm.max_map_count`。

### 9.2 Docker 镜像拉取超时/失败

**解决方案**：
1. 确认 `.env` 中 `RAGFLOW_IMAGE` 使用了国内镜像源
2. 配置 Docker daemon 镜像加速器（步骤 5）
3. 如果仍然失败，尝试手动拉取：
```bash
docker pull swr.cn-north-4.myhuaweicloud.com/infiniflow/ragflow:v0.26.3
```

### 9.3 文档解析进度卡住不动

**排查**：
1. 检查嵌入模型是否配置正确
2. 检查嵌入模型 API 是否可达（容器内网络）
3. 减少同时解析的文件数量（≤5 个/批次）

```bash
# 检查 RAGFlow 日志中是否有嵌入错误
docker compose logs ragflow-cpu | grep -i "embedding\|error"
```

### 9.4 端口冲突导致服务无法启动

**排查**：
```bash
# 查看哪些端口被占用
sudo netstat -tlnp | grep -E "80|6379|3306|9000|9380"

# 或用 ss
sudo ss -tlnp | grep -E "80|6379|3306|9000|9380"
```

解决：修改 `.env` 中对应端口为未被占用的端口。

### 9.5 Redis 端口冲突（6379 已被占用）

如果 RAGFlow 的 Redis 无法启动，修改 `.env`：

```env
REDIS_PORT=6380    # 改为 6380
```

然后重启：
```bash
docker compose up -d --force-recreate
```

### 9.6 内存不足（OOM）

32GB 服务器运行 RAGFlow + 其他服务，需注意内存分配：

```bash
# 查看内存使用
free -h

# 查看 Docker 容器内存使用
docker stats --no-stream
```

优化建议：
- 减少 ES 内存限制（`.env` 中 `MEM_LIMIT`）
- 减少 Redis 内存限制
- 文件分批解析（≤5 个/批次）
- 不启动 TEI 本地嵌入服务（用在线 API）

---

## 十、数据备份与持久化

RAGFlow 的数据存储在 Docker volumes 中，确认以下数据目录：

| 数据 | Volume | 内容 |
|------|--------|------|
| MySQL 数据 | mysql_data | 元数据、对话记录 |
| Elasticsearch | es_data | 向量索引、全文索引 |
| MinIO | minio_data | 上传的原始文档 |
| Redis | redis_data | 缓存、任务队列 |

**备份方法**：

```bash
# 备份 MySQL
docker exec mysql-1 mysqldump -u root -p你的密码 rag_flow > ragflow_backup.sql

# 备份所有 volumes（完整备份）
docker run --rm -v /opt/ragflow_backup:/backup \
  -v ragflow_mysql_data:/data:ro \
  alpine tar czf /backup/mysql_data.tar.gz -C /data .
```

---

## 十一、与现有项目集成

RAGFlow 可以通过 API 与你现有的项目（ai-server、vehicle-agent）集成。

### API 调用示例

```bash
# 创建对话
curl -X POST http://192.168.31.101:9380/api/v1/conversation \
  -H "Authorization: Bearer 你的RAGFlow API Key" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "你的助手ID",
    "question": "你好"
  }'
```

> 在 RAGFlow Web 界面 → 右上角 → API Key 管理 中获取 API Key。

---

## 十二、完整配置文件参考

### 最终 `.env` 配置清单（关键项）

```env
# ===== 核心配置 =====
DOC_ENGINE=elasticsearch
DEVICE=cpu
COMPOSE_PROFILES=elasticsearch,cpu
TZ=Asia/Shanghai

# ===== 镜像源 =====
RAGFLOW_IMAGE=swr.cn-north-4.myhuaweicloud.com/infiniflow/ragflow:v0.26.3
HF_ENDPOINT=https://hf-mirror.com

# ===== 端口（避免冲突） =====
SVR_WEB_HTTP_PORT=9380
SVR_HTTP_PORT=9380
SVR_WEB_HTTPS_PORT=443
ADMIN_SVR_HTTP_PORT=9381
REDIS_PORT=6380
EXPOSE_MYSQL_PORT=3307
ES_PORT=1200
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001

# ===== Elasticsearch =====
STACK_VERSION=8.11.3
ES_HOST=es01
ELASTIC_PASSWORD=你的强密码1
MEM_LIMIT=8073741824

# ===== MySQL =====
MYSQL_PASSWORD=你的强密码2
MYSQL_HOST=mysql
MYSQL_DBNAME=rag_flow
MYSQL_PORT=3306

# ===== MinIO =====
MINIO_HOST=minio
MINIO_USER=rag_flow
MINIO_PASSWORD=你的强密码3

# ===== Redis =====
REDIS_HOST=redis
REDIS_PASSWORD=你的强密码4

# ===== 其他 =====
REGISTER_ENABLED=1
```

---

> 📌 **部署完成后**，建议将本文件放在 `/opt/ragflow/docs/` 目录下，方便后续运维查阅。
> 📌 **所有密码**请使用 `openssl rand -hex 32` 生成，不要使用默认值！
