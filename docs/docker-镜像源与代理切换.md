# 2026-07-04 Docker 镜像源与代理切换手册

> 国内服务器拉取 Docker 镜像经常失败，本文档整理了三种网络方案的切换命令，方便快速切换。

## 当前可用的国内镜像源

| 镜像源 | 地址 | 稳定性 |
|--------|------|--------|
| docker.1ms.run | https://docker.1ms.run | 较好，免费公共源 |
| docker.xuanyuan.me | https://docker.xuanyuan.me | 较好，免费公共源 |
| docker.rainbond.cc | https://docker.rainbond.cc | 一般，偶尔缓存不全 |

> 免费镜像源会不定期失效，如果某个源突然不可用，换另一个即可。

---

## 方案一：国内镜像源（默认，不用代理）

**适用场景**：正常开发，不需要翻墙，直连国内镜像源。

**检查当前是否为此方案**：
```bash
cat /etc/docker/daemon.json
# 应看到 registry-mirrors 字段
```

**切换到方案一**：

```bash
# 1. 删掉可能残留的代理配置
sudo rm -f /etc/systemd/system/docker.service.d/proxy.conf
sudo rm -rf /etc/systemd/system/docker.service.d

# 2. 写入国内镜像源配置
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

# 3. 重启 Docker
sudo systemctl daemon-reload
sudo systemctl restart docker

# 4. 验证
cat /etc/docker/daemon.json
```

---

## 方案二：通过代理直连 Docker Hub

**适用场景**：镜像源全挂，或需要拉取镜像源缓存不到的冷门镜像。

**前提**：局域网内有机器运行 v2rayN / Clash 等代理软件，并开启了局域网连接。

**切换到方案二**：

```bash
# 1. 先确认代理可用（把 192.168.31.100 换成你的代理机器 IP）
curl -x http://192.168.31.100:10809 https://www.google.com
# 能返回 HTML 说明代理通

# 2. 清掉 daemon.json 中的镜像源（代理走外网，国内镜像源反而不通）
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF

# 3. 配置 Docker 使用代理
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/proxy.conf > /dev/null << 'EOF'
[Service]
Environment="HTTP_PROXY=http://192.168.31.100:10809"
Environment="HTTPS_PROXY=http://192.168.31.100:10809"
Environment="NO_PROXY=localhost,127.0.0.1"
EOF

# 4. 重启 Docker
sudo systemctl daemon-reload
sudo systemctl restart docker

# 5. 验证（拉一个测试镜像）
docker pull hello-world
```

> **注意**：`NO_PROXY` 中不要包含国内服务地址，否则访问国内 API 也会走代理变慢。

---

## 方案三：无镜像源、无代理（裸连 docker.io）

**适用场景**：服务器能直接访问外网（比如阿里云 ECS），不需要镜像源。

```bash
# 1. 清掉所有配置
sudo rm -f /etc/systemd/system/docker.service.d/proxy.conf
sudo rm -rf /etc/systemd/system/docker.service.d

# 2. 只保留日志配置
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF

# 3. 重启 Docker
sudo systemctl daemon-reload
sudo systemctl restart docker
```

---

## 快速切换速查表

| 从 → 到 | 执行步骤 |
|---------|---------|
| 方案一 → 方案二 | 删 `registry-mirrors`，加 `proxy.conf`，`daemon-reload` + `restart docker` |
| 方案二 → 方案一 | 删 `proxy.conf`，加 `registry-mirrors`，`daemon-reload` + `restart docker` |
| 任意 → 方案三 | 删 `proxy.conf`，`daemon.json` 只留日志配置，`daemon-reload` + `restart docker` |

---

## 常见问题

### Q: 怎么知道当前是哪种方案？

```bash
# 看镜像源
cat /etc/docker/daemon.json | grep -A3 registry-mirrors

# 看代理
cat /etc/systemd/system/docker.service.d/proxy.conf 2>/dev/null || echo "无代理配置"
```

- 有 `registry-mirrors` 无 `proxy.conf` → **方案一**（国内镜像源）
- 无 `registry-mirrors` 有 `proxy.conf` → **方案二**（代理直连）
- 都没有 → **方案三**（裸连）

### Q: 切换方案后需要重新 build 吗？

不需要。切换 Docker 网络配置后，已 build 的镜像缓存仍然有效。只有下次 build 时拉取新镜像或新基础镜像层才会用到新方案。

### Q: docker compose build 失败但 docker pull 成功？

这是因为 `docker pull` 走 `registry-mirrors`，但 `docker build`（buildx/buildkit）可能走不同的镜像解析路径。解决：
- 方案一下 build 失败：换镜像源试试
- 方案二下 build 失败：确认 `proxy.conf` 已生效，`systemctl show docker | grep proxy` 应能看到代理地址

### Q: 镜像源全挂了怎么办？

按以下顺序尝试：
1. 换另一个国内镜像源
2. 切到方案二（代理直连）
3. 如果代理也挂，等镜像源恢复后再切回方案一

### Q: 构建时 apt/npm/pip 下载慢？

这和镜像源无关，是 Dockerfile **内部**的下载源问题。各项目 Dockerfile 已经配了国内源：
- apt → `mirrors.aliyun.com`
- npm → `registry.npmmirror.com`
- pip → `pypi.tuna.tsinghua.edu.cn`

如果构建内部下载还是慢，检查 Dockerfile 中是否遗漏了换源步骤。

---

## 配置备份（首次配置成功后执行）

```bash
# 备份镜像源配置
cp /etc/docker/daemon.json ~/docker-daemon.json.bak

# 备份代理配置（如果有）
cp /etc/systemd/system/docker.service.d/proxy.conf ~/docker-proxy.conf.bak 2>/dev/null || true
```

**还原**：
```bash
cp ~/docker-daemon.json.bak /etc/docker/daemon.json
cp ~/docker-proxy.conf.bak /etc/systemd/system/docker.service.d/proxy.conf 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl restart docker
```
