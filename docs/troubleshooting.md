# 调试技巧与常见问题排查

## 日志查看

### 前端（Vite 开发模式）
- 浏览器控制台：F12 → Console 面板
- 网络请求：F12 → Network 面板（查看 API 请求）
- 终端输出：Vite 构建和 HMR 信息

### AI 后端 (ai-server)
```bash
# 本地开发 — 终端直接输出（分级日志格式）

# Docker 部署
docker compose logs -f ai-server

# 容器内文件日志
docker compose exec ai-server cat /app/logs/app.log
```

**日志格式**：`时间 | 级别 | 模块 | 消息`
```
2025-01-01 12:00:00 | INFO    | app.main | AI Server 启动中...
2025-01-01 12:00:01 | INFO    | app.services.llm_service | LLM call: model=deepseek-v4-flash
```

---

## 常见问题

### 1. 前端页面空白 / 刷新后 404

**原因**：React Router SPA 路由回退未正确配置。

**排查步骤**：
1. 确认 `web/nginx.conf` 中包含 `try_files $uri $uri/ /index.html;`
2. Docker 环境确认 web 容器的 Nginx 使用了自定义配置
3. 检查浏览器控制台是否有 JavaScript 错误

**解决**：`web/nginx.conf` 已预配置 SPA 回退，确保 Dockerfile 正确复制了该配置文件。

---

### 2. AI 聊天返回 500 错误

**排查步骤**：

```bash
# 1. 检查 AI 后端是否正常运行
curl http://localhost:8000/api/health

# 2. 查看 AI 后端日志
docker compose logs ai-server
# 或本地查看终端输出

# 3. 手动测试 API
curl -X POST http://localhost:8000/api/ai/chat \
  -F "message=你好" \
  -F "model=deepseek-v4-flash" \
  -F "history=[]"
```

**常见原因与解决**：

| 错误信息 | 原因 | 解决 |
|---------|------|------|
| `LLM API 调用失败: 401` | API Key 无效 | 检查 `ai-server/.env` 中 `LLM_API_KEY` |
| `LLM API 调用失败: 404` | API Base URL 错误 | 检查 `LLM_API_BASE` 是否正确 |
| `Connection refused` | AI 后端未启动 | 启动 ai-server 服务 |
| `模型不存在` | 模型 ID 不正确 | 使用 `/api/ai/models` 查看可用模型 |

---

### 3. 知识库文件上传失败

**排查步骤**：

```bash
# 手动测试
curl -X POST http://localhost:8000/api/knowledge/test-kb/files \
  -F "file=@test.pdf"

# 检查 Qdrant 是否运行
curl http://localhost:6333/collections
```

**常见原因**：

| 现象 | 原因 | 解决 |
|------|------|------|
| `Qdrant 连接失败` | Qdrant 未启动 | 启动 Qdrant 服务 |
| `Embedding API 调用失败` | API Key 无效 | 检查 `EMBEDDING_API_KEY` |
| 上传超时 | 文件过大 | 确保文件 ≤ 100MB |
| 解析内容为空 | 文件格式不支持或无可提取文本 | 确认文件格式（PDF/DOCX/TXT/MD/CSV/HTML） |

---

### 4. RAG 问答结果不准确

**排查步骤**：

1. 确认知识库中已上传相关文档
2. 检查 Qdrant 面板（`http://localhost:6333/dashboard`）查看向量数据
3. 查看日志中的检索结果，确认检索到了相关文档片段

**优化方向**：

| 问题 | 可能原因 | 调整 |
|------|---------|------|
| 检索不到相关内容 | 分块太大导致语义模糊 | 减小 `CHUNK_SIZE`（默认 500） |
| 检索到但不相关 | top_k 太少 | 增大检索数量 |
| 回答忽略上下文 | 系统 prompt 权重不够 | 调整 prompt 模板 |

---

### 5. Docker 构建失败

**排查步骤**：

```bash
# 清除缓存重新构建
docker compose build --no-cache

# 查看详细构建日志
docker compose build --progress=plain

# 检查端口冲突
docker compose ps
netstat -tlnp  # Linux
```

**常见错误**：

| 错误 | 原因 | 解决 |
|------|------|------|
| `pip install` 超时 | 网络问题 | Dockerfile 中添加 pip 镜像源 |
| `npm ci` 失败 | 依赖版本问题 | 删除 `package-lock.json` 重新 `npm install` |
| 端口冲突 | 端口被占用 | 修改 `docker-compose.yml` 中的端口映射 |

---

### 6. 前端 API 请求 404（本地开发）

**原因**：Vite 代理未生效。

**解决**：
1. 确认后端服务已启动
2. 检查 `web/vite.config.ts` 中 proxy 配置
3. 重启 Vite 开发服务器（`npm run dev`）
4. 确认请求路径前缀匹配代理规则

---

### 7. 修改代码后 Docker 未更新

**原因**：Docker 使用构建缓存。

**解决**：
```bash
# 重新构建指定服务
docker compose up -d --build ai-server
docker compose up -d --build web
```

---

## 开发调试技巧

### 前端调试
```javascript
// 在浏览器控制台中调试
// 查看 localStorage 中的对话数据
JSON.parse(localStorage.getItem('ai_conversations'))

// 查看 Cookie 同意状态
localStorage.getItem('cookie_consent_accepted')
```

### AI 后端调试
```bash
# 使用 Swagger UI 交互式测试
# 访问 http://localhost:8000/docs
```

### Qdrant 调试
```bash
# 查看所有集合
curl http://localhost:6333/collections

# 查看集合详情
curl http://localhost:6333/collections/{collection_name}

# 访问 Web 面板
# http://localhost:6333/dashboard
```
