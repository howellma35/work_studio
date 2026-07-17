# LangFuse + RAGFlow 外网访问配置指南

> 目标：通过子域名让 LangFuse 和 RAGFlow 可以从外网访问
> - `langfuse.mahongwei.com.cn` → LangFuse 可观测性平台
> - `ragflow.mahongwei.com.cn` → RAGFlow 知识库平台

## 当前架构

```
外网用户 → ECS nginx(443 SSL) → 127.0.0.1:6003 (frps) → frp隧道 → 家里nginx:80 → Docker服务
                                    ↕
                            目前只有一条隧道(6003)
                            只代理 mahongwei.com.cn
```

## 目标架构

```
外网用户 → ECS nginx(443 SSL)
           ├─ mahongwei.com.cn         → 127.0.0.1:6003 (frps) → 家里nginx → 主站+车载助手
           ├─ langfuse.mahongwei.com.cn → 127.0.0.1:6004 (frps) → 家里nginx → langfuse-app:3000
           └─ ragflow.mahongwei.com.cn  → 127.0.0.1:6005 (frps) → 家里nginx → ragflow容器:80
```

---

## 操作步骤（共 5 步）

### 第 1 步：DNS 添加子域名解析

在阿里云 DNS 控制台添加两条 A 记录：

| 主机记录 | 记录类型 | 记录值 | TTL |
|---------|---------|--------|-----|
| `langfuse` | A | `106.14.24.38`（ECS IP） | 10分钟 |
| `ragflow` | A | `106.14.24.38`（ECS IP） | 10分钟 |

> 阿里云 DNS 控制台：https://dns.console.aliyun.com
> 找到 `mahongwei.com.cn` 域名 → 解析设置 → 添加记录

---

### 第 2 步：ECS 上申请 SSL 证书

在 ECS 服务器上执行（用 certbot 为两个子域名申请证书）：

```bash
# 先停掉 ECS nginx（certbot standalone 模式需要占用 80 端口）
sudo systemctl stop nginx

# 申请 langfuse 子域名证书
sudo certbot certonly --standalone -d langfuse.mahongwei.com.cn

# 申请 ragflow 子域名证书
sudo certbot certonly --standalone -d ragflow.mahongwei.com.cn

# 证书会保存在：
# /etc/letsencrypt/live/langfuse.mahongwei.com.cn/fullchain.pem
# /etc/letsencrypt/live/ragflow.mahongwei.com.cn/fullchain.pem

# 重启 nginx
sudo systemctl start nginx
```

> certbot 会自动续期，不用管。如果 certbot 未安装：`sudo apt install certbot`

---

### 第 3 步：ECS nginx 添加两个 server block

在 ECS 上编辑 `/etc/nginx/conf.d/mahongwei.conf`，在**现有内容之后**追加以下两个 server block：

```nginx
# =============================================================
# LangFuse — SSL 终结 + 反向代理到 frp 隧道
# =============================================================

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name langfuse.mahongwei.com.cn;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS — SSL 终结后转发到 frp 隧道（6004）
server {
    listen 443 ssl;
    http2 on;
    server_name langfuse.mahongwei.com.cn;

    ssl_certificate     /etc/letsencrypt/live/langfuse.mahongwei.com.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/langfuse.mahongwei.com.cn/privkey.pem;

    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://127.0.0.1:6004;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 120;
        proxy_buffering off;  # LangFuse 有 SSE 流，需要关闭缓冲
    }
}

# =============================================================
# RAGFlow — SSL 终结 + 反向代理到 frp 隧道
# =============================================================

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name ragflow.mahongwei.com.cn;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS — SSL 终结后转发到 frp 隧道（6005）
server {
    listen 443 ssl;
    http2 on;
    server_name ragflow.mahongwei.com.cn;

    ssl_certificate     /etc/letsencrypt/live/ragflow.mahongwei.com.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ragflow.mahongwei.com.cn/privkey.pem;

    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://127.0.0.1:6005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 120;
        proxy_buffering off;
        client_max_body_size 100m;  # RAGFlow 上传大文件需要
    }
}
```

然后测试并重载：

```bash
sudo nginx -t          # 测试配置语法
sudo systemctl reload nginx  # 重载配置
```

---

### 第 4 步：家里 frpc 添加两条穿透规则

编辑 `/etc/frp/frpc.toml`，在**文件末尾**追加：

```toml

# ----- 规则 6：穿透 LangFuse -----
# 外网访问 https://langfuse.mahongwei.com.cn → ECS:6004 → frp隧道 → 家里nginx → langfuse-app:3000
[[proxies]]
name = "langfuse-http"
type = "tcp"
localIP = "127.0.0.1"
localPort = 80          # 经过家里 nginx 再代理到 langfuse-app:3000
remotePort = 6004       # ECS frps 监听端口

# ----- 规则 7：穿透 RAGFlow -----
# 外网访问 https://ragflow.mahongwei.com.cn → ECS:6005 → frp隧道 → 家里nginx → ragflow容器:80
[[proxies]]
name = "ragflow-http"
type = "tcp"
localIP = "127.0.0.1"
localPort = 80          # 经过家里 nginx 再代理到 ragflow 容器
remotePort = 6005       # ECS frps 监听端口
```

然后重启 frpc：

```bash
sudo systemctl restart frpc
```

> **为什么都走 localPort=80？** 因为家里 Docker nginx 已经在 80 端口监听，它会根据 `Host` 头区分不同服务，统一代理。这样不用为每个服务开单独端口，更简洁。

---

### 第 5 步：家里 Docker nginx 添加反向代理规则

编辑 `deploy/nginx/nginx.conf`，在**现有 `http` block 内、现有 `server` block 之后**追加：

```nginx
    # ============================================================
    #  LangFuse 可观测性平台
    # ============================================================

    upstream langfuse_app {
        server langfuse-app:3000;
    }

    server {
        listen 80;
        server_name langfuse.mahongwei.com.cn;

        location / {
            proxy_pass http://langfuse_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
            proxy_buffering off;  # LangFuse SSE 流需要
        }
    }

    # ============================================================
    #  RAGFlow 知识库平台
    # ============================================================

    upstream ragflow_app {
        server docker-ragflow-cpu-1:80;  # RAGFlow 容器内部端口是 80
    }

    server {
        listen 80;
        server_name ragflow.mahongwei.com.cn;

        location / {
            proxy_pass http://ragflow_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
            client_max_body_size 100m;  # RAGFlow 上传大文件
        }
    }
```

> ⚠️ **注意**：RAGFlow 容器名是 `docker-ragflow-cpu-1`（从 `docker ps` 看到的）。
> 如果 Docker nginx 和 RAGFlow 不在同一个 docker-compose 络络里，
> 需要用宿主机端口代替：`server 127.0.0.1:9380;`（RAGFlow 映射到宿主机的端口）。

然后重启 Docker nginx：

```bash
cd /data/caragent/work_studio/deploy
docker compose restart nginx
```

---

## 第 5 步补充：LangFuse 环境变量更新

LangFuse 的 NEXTAUTH_URL 必须改成外网域名，否则登录回调会失败。

编辑 `deploy/.env`，修改以下两行：

```bash
# 修改前：
NEXTAUTH_URL=http://${SERVER_IP:-localhost}:${LANGFUSE_PORT:-3000}
NEXT_PUBLIC_SITE_URL=http://${SERVER_IP:-localhost}:${LANGFUSE_PORT:-3000}

# 修改后：
NEXTAUTH_URL=https://langfuse.mahongwei.com.cn
NEXT_PUBLIC_SITE_URL=https://langfuse.mahongwei.com.cn
```

然后重启 LangFuse：

```bash
cd /data/caragent/work_studio/deploy
docker compose restart langfuse langfuse-worker
```

---

## 同步更新：后端代码中的 RAGFlow/LangFuse URL

后端代码中引用的 RAGFlow 和 LangFuse URL 也需要更新：

### vehicle-agent/.env

```bash
# 修改前：
RAGFLOW_BASE_URL=http://localhost:9380
LANGFUSE_BASE_URL=http://localhost:3000

# 修改后（如果想让后端走外网）：
RAGFLOW_BASE_URL=https://ragflow.mahongwei.com.cn
LANGFUSE_BASE_URL=https://langfuse.mahongwei.com.cn

# 或者继续走内网（更稳定，推荐）：
RAGFLOW_BASE_URL=http://localhost:9380          # 内网直连，不走外网
LANGFUSE_BASE_URL=http://localhost:3000         # 内网直连，不走外网
```

> **推荐**：后端继续走内网（localhost），不走外网绕一圈。只有**前端浏览器**需要走外网域名。

---

## 验证步骤

按顺序验证，每一步通过后再做下一步：

| 顺序 | 验证内容 | 方法 |
|------|---------|------|
| 1 | DNS 解析生效 | `dig langfuse.mahongwei.com.cn` 和 `dig ragflow.mahongwei.com.cn` 应返回 `106.14.24.38` |
| 2 | SSL 证书有效 | `curl -I https://langfuse.mahongwei.com.cn` 应返回 200 或 302 |
| 3 | frp 隧道连通 | ECS 上 `curl http://127.0.0.1:6004` 应有响应 |
| 4 | 家里 nginx 代理正确 | 家里 `curl -H "Host: langfuse.mahongwei.com.cn" http://127.0.0.1:80` 应返回 LangFuse 页面 |
| 5 | LangFuse 登录正常 | 浏览器访问 `https://langfuse.mahongwei.com.cn` 能正常登录 |
| 6 | RAGFlow 正常 | 浏览器访问 `https://ragflow.mahongwei.com.cn` 能正常打开 |

---

## 常见问题排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 502 Bad Gateway | 家里 nginx 没识别到 Host 头 | 检查 nginx.conf 是否有对应 server_name 的 server block |
| LangFuse 登录后无限回调 | NEXTAUTH_URL 没改成 https 域名 | 改 .env 中的 NEXTAUTH_URL |
| RAGFlow 上传文件失败 | nginx client_max_body_size 太小 | 加 `client_max_body_size 100m;` |
| frp 隧道不通 | frpc 没重启 / remotePort 和 ECS nginx 不一致 | `sudo systemctl restart frpc`，确认 remotePort=6004/6005 |
| SSL 证书错误 | certbot 申请失败或路径不对 | `sudo certbot certificates` 查看已申请的证书 |

---

## 操作顺序汇总

```
1. 阿里云 DNS 添加 A 记录（langfuse / ragflow → 106.14.24.38）
2. ECS 上 certbot 申请 SSL 证书
3. ECS nginx 添加 langfuse/ragflow 的 server block
4. 家里 frpc.toml 添加两条穿透规则（6004/6005）
5. 家里 Docker nginx.conf 添加 langfuse/ragflow 反向代理
6. 修改 .env 中 NEXTAUTH_URL 和 NEXT_PUBLIC_SITE_URL
7. 重启服务：frpc → Docker nginx → langfuse → langfuse-worker
8. 验证访问
```

> **每次只改一个地方，改完验证再改下一个，不要一口气全改。**
