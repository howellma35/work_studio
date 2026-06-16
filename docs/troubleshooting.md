# 调试技巧与常见问题排查

## 日志查看

### 前端（Vite 开发模式）
- 浏览器控制台：F12 → Console 面板
- 网络请求：F12 → Network 面板（查看 API 请求和 WebSocket 连接）
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
2025-01-01 12:00:01 | INFO    | app.services.llm_service | LLM call: model=gpt-4o-mini
```

### 游戏后端 (game-server)
```bash
# 本地开发 — 终端直接输出

# Docker 部署
docker compose logs -f game-server

# 容器内文件日志
docker compose exec game-server cat /app/logs/game.log
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
  -F "model=gpt-4o-mini" \
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

### 3. PDF 解析失败

**排查步骤**：

```bash
# 手动测试
curl -X POST http://localhost:8000/api/pdf/parse \
  -F "file=@test.pdf"
```

**常见原因**：

| 现象 | 原因 | 解决 |
|------|------|------|
| `请上传 PDF 格式文件` | 上传的不是 PDF | 确认文件格式 |
| `PDF 解析失败` | 文件是扫描件 | 使用文字型 PDF（非图片扫描） |
| 超时 | 文件过大 | 确保文件 ≤ 50MB |
| 提取内容为空 | PDF 无可提取文本 | 尝试其他 PDF 文件 |

---

### 4. WebSocket 连接失败（猜词游戏）

**排查步骤**：

```bash
# 1. 检查游戏后端是否正常运行
curl http://localhost:3001/api/health

# 2. 检查浏览器 Network → WS 面板
#    确认 Socket.IO 握手请求是否成功

# 3. Docker 环境检查 Nginx 代理
# 确认 /socket.io/ 路径代理到 game_backend
```

**常见原因**：

| 现象 | 原因 | 解决 |
|------|------|------|
| 连接超时 | 游戏后端未启动 | 启动 game-server |
| 连接被拒绝 | 端口未开放 | 检查防火墙和端口监听 |
| 连接后无消息 | Socket.IO 事件不匹配 | 检查浏览器控制台错误 |
| Docker 下连接失败 | Nginx WebSocket 代理缺失 | 检查 nginx.conf 中 `/socket.io/` 配置 |

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

### 6. Embedding API 调用失败（猜词游戏）

**现象**：所有猜测相似度都很低或返回错误。

**排查步骤**：

```bash
# 手动测试 SiliconFlow API
curl -X POST https://api.siliconflow.cn/v1/embeddings \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"BAAI/bge-m3","input":["测试"]}'
```

**解决**：
1. 确认 `game-server/.env` 中 `EMBEDDING_API_KEY` 有效
2. 检查网络是否能访问 API 端点
3. 如不配置 API Key，系统自动回退到编辑距离匹配（精度较低但可用）

---

### 7. 前端 API 请求 404（本地开发）

**原因**：Vite 代理未生效。

**解决**：
1. 确认后端服务已启动
2. 检查 `web/vite.config.ts` 中 proxy 配置
3. 重启 Vite 开发服务器（`npm run dev`）
4. 确认请求路径前缀匹配代理规则

---

### 8. 修改代码后 Docker 未更新

**原因**：Docker 使用构建缓存。

**解决**：
```bash
# 重新构建指定服务
docker compose up -d --build ai-server
docker compose up -d --build game-server
docker compose up -d --build web
```

---

## 性能优化建议

| 方面 | 建议 |
|------|------|
| 前端 | Vite 已自动代码分割和 tree-shaking，无需额外配置 |
| Nginx | 已配置 gzip 压缩和静态资源缓存 |
| AI 后端 | 大模型请求可设置合理的 `max_tokens` 减少输出长度 |
| 游戏后端 | 内存排行榜适合小规模使用，大规模场景可引入 Redis |
| Embedding | 词库 embedding 会缓存到 words.json，避免重复调用 API |

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

### 游戏后端调试
```bash
# 查看词库
curl http://localhost:3001/api/game/words

# 按分类筛选
curl http://localhost:3001/api/game/words?category=fruit

# 按难度筛选
curl http://localhost:3001/api/game/words?difficulty=2
```
