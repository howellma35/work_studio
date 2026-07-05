# AutoMind 智能车机助手 - 本地开发与调试指南

> 本文档详细说明如何本地启动、调试、观测 AutoMind 项目，以及如何新增功能。

---

## 一、环境准备

### 1.1 系统要求
- Python >= 3.11
- Node.js >= 18
- Docker & Docker Compose（部署用）

### 1.2 后端依赖安装

```powershell
# 进入后端目录
cd e:\githubcode\rag_game\vehicle-agent\backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 1.3 前端依赖安装

```powershell
# 进入前端目录
cd e:\githubcode\rag_game\vehicle-agent\frontend

# 安装依赖
npm install --registry https://registry.npmmirror.com
```

### 1.4 配置环境变量

```powershell
# 复制示例配置
cd e:\githubcode\rag_game\vehicle-agent\backend
cp .env.example .env
```

编辑 `.env` 文件，**必须填写**以下配置项：

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_API_KEY` | 百炼平台 API Key | `sk-xxxxx` |
| `LLM_MODEL` | 模型名称 | `deepseek-v3` |
| `EMBEDDING_API_KEY` | 嵌入模型 Key（可与 LLM_API_KEY 相同）| `sk-xxxxx` |

可选项（LangFuse 可观测性）：
| 变量 | 说明 |
|------|------|
| `LANGFUSE_HOST` | LangFuse 地址，默认 `http://localhost:3000` |
| `LANGFUSE_PUBLIC_KEY` | 在 LangFuse 控制台创建项目后获取 |
| `LANGFUSE_SECRET_KEY` | 同上 |

---

## 二、本地启动

### 2.1 启动后端

```powershell
cd e:\githubcode\rag_game\vehicle-agent\backend
.\.venv\Scripts\Activate.ps1

# 开发模式（热重载）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

启动成功后可访问：
- 健康检查: http://localhost:8001/api/vehicle/health
- Agent 信息: http://localhost:8001/api/vehicle/agent-info
- API 文档: http://localhost:8001/docs

### 2.2 启动前端

```powershell
cd e:\githubcode\rag_game\vehicle-agent\frontend
npm run dev
```

访问 http://localhost:5174 即可看到车机仪表盘界面。

### 2.3 启动 LangFuse（可选，推荐）

```powershell
cd e:\githubcode\rag_game\vehicle-agent\deploy

# 启动 LangFuse + 数据库
docker compose up -d langfuse langfuse-db
```

访问 http://localhost:3000，首次进入需注册账号，然后：
1. 创建一个新项目
2. 获取 `Public Key` 和 `Secret Key`
3. 填入后端 `.env` 文件的 `LANGFUSE_PUBLIC_KEY` 和 `LANGFUSE_SECRET_KEY`
4. 重启后端服务

---

## 三、调试与观测（核心重点）

AutoMind 提供 **三层观测体系**，帮你逐步调试 Agent 的每个输入输出：

### 3.1 第一层：LangGraph Studio（可视化单步调试）

LangGraph Studio 是 LangChain 官方的桌面调试工具，可以：
- 可视化查看图结构（节点、边、条件路由）
- 单步执行，查看每个节点的输入/输出状态
- 状态时间旅行：回溯到任意一步重新执行
- 实时修改 state 并继续运行

**启动方式：**

```powershell
cd e:\githubcode\rag_game\vehicle-agent\backend
.\.venv\Scripts\Activate.ps1

# 启动 LangGraph 开发服务器（会自动打开 Studio）
langgraph dev
```

> 如果未安装 langgraph-cli：`pip install langgraph-cli`

在 Studio 中你可以：
- 左侧聊天框输入测试消息（如"导航去公司"）
- 右侧实时看到 Supervisor 如何路由到 navigation_agent
- 点击任意节点查看详细 input/output
- 观察工具调用（MCP 工具）的完整参数和返回值

### 3.2 第二层：LangFuse（全链路追踪平台）

LangFuse 记录生产级别的完整 trace，适合分析性能和定位问题。

访问 http://localhost:3000，进入你的项目后可以看到：

- **Traces 页面**：每次对话的完整调用链
  - 每个节点的输入消息、输出消息
  - 每个 LLM 调用的 prompt、completion、token 数、延迟
  - 每个工具调用的参数和返回结果
  - 调用层级树（Supervisor → 子Agent → 工具）

- **Dashboard 页面**：统计概览
  - 总请求数、平均延迟、Token 消耗趋势
  - 按模型/Agent 分组的调用统计

### 3.3 第三层：应用日志（Loguru）

后端日志同时输出到控制台和文件：

```powershell
# 实时查看日志
cd e:\githubcode\rag_game\vehicle-agent\backend
# 日志文件位置
type logs\automind.log
# 或在 PowerShell 中持续监控
Get-Content logs\automind.log -Wait
```

日志包含：
- MCP 工具加载信息
- Agent 图构建过程
- 记忆系统召回的偏好数量
- 每次请求的元数据

---

## 四、新增功能开发指南

### 4.1 新增一个 MCP 工具

以"充电桩查询"为例：

**步骤 1：创建工具文件** `backend/app/mcp/tools/charging_tools.py`

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ChargingTools")

@mcp.tool()
def find_charging_stations(location: str, radius_km: int = 5) -> dict:
    """
    查找附近充电桩

    Args:
        location: 当前位置
        radius_km: 搜索半径（公里）
    """
    # 模拟数据（真实环境对接充电桩 API）
    return {
        "status": "ok",
        "stations": [
            {"name": "特来电(科技园站)", "distance_km": 1.5, "available": 4, "power_kw": 120},
        ],
    }
```

**步骤 2：注册到 MCP Server** - 编辑 `backend/app/mcp/server.py`，添加：

```python
from app.mcp.tools import charging_tools  # 新增导入

for tool_module in [navigation_tools, media_tools, vehicle_tools, weather_tools, charging_tools]:
    # ... 合并工具
```

**步骤 3：分配给子Agent** - 编辑 `backend/app/agents/vehicle_agent.py`，在工具筛选中加入关键词：

```python
vehicle_tools = [
    t for t in tools
    if any(kw in t.name for kw in ["window", "climate", "door", "seat", "vehicle_status", "charging"])
]
```

### 4.2 新增一个子Agent

以"充电管理Agent"为例：

**步骤 1：创建 Agent** `backend/app/agents/charging_agent.py`

```python
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent
from app.models.llm import create_llm

CHARGING_PROMPT = """\
你是 AutoMind 的充电管理专家 Agent...
"""

def create_charging_agent(tools: list[BaseTool]):
    charging_tools = [t for t in tools if "charging" in t.name]
    return create_react_agent(
        model=create_llm(),
        tools=charging_tools,
        name="charging_agent",
        prompt=CHARGING_PROMPT,
    )
```

**步骤 2：注册到 Supervisor** - 编辑 `backend/app/graph/supervisor.py`：

```python
from app.agents.charging_agent import create_charging_agent

agents = [
    # ... 已有 agents
    create_charging_agent(tools),  # 新增
]
```

**步骤 3：更新路由描述** - 编辑 `backend/app/graph/routing.py`，在 `ROUTING_DESCRIPTION` 中添加充电 Agent 的描述。

### 4.3 新增前端生成式 UI 卡片

**步骤 1：创建组件** `frontend/src/components/ChargingCard.tsx`

```tsx
export default function ChargingCard() {
  return (
    <div className="glass-card p-6">
      <h3 className="text-lg font-bold text-white">⚡ 充电</h3>
      {/* ... UI 内容 */}
    </div>
  );
}
```

**步骤 2：加入仪表盘** - 编辑 `frontend/src/components/VehicleDashboard.tsx`：

```tsx
import ChargingCard from "./ChargingCard";
// 在 JSX 中添加
<ChargingCard />
```

---

## 五、Docker 全栈部署

### 5.1 一键启动全部服务

```powershell
cd e:\githubcode\rag_game\vehicle-agent\deploy

# 构建并启动所有服务
docker compose up -d --build
```

服务端口映射：

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 5174 | 车机仪表盘 UI |
| 后端 | 8001 | FastAPI + CopilotKit Runtime |
| LangFuse | 3000 | 可观测性平台 |
| ChromaDB | 8002 | 向量数据库 |

### 5.2 部署到服务器

```bash
# 在服务器上克隆代码后
cd vehicle-agent/deploy
docker compose up -d --build

# 配置 Nginx 反向代理（参考主项目 nginx.conf）
```

### 5.3 查看服务状态

```powershell
docker compose ps          # 查看运行状态
docker compose logs -f vehicle-backend   # 查看后端日志
```

---

## 六、常见问题排查

### Q: MCP 工具加载失败？
A: MCP Server 以 stdio 子进程方式运行，确保 `python -m app.mcp.server` 能正常执行。可在 `backend` 目录手动测试：`python -m app.mcp.server`。

### Q: LangFuse 看不到 trace？
A: 检查 `.env` 中 `LANGFUSE_PUBLIC_KEY` 和 `LANGFUSE_SECRET_KEY` 是否正确填写，且 `LANGFUSE_HOST` 能从后端容器访问。

### Q: CopilotKit 连接失败？
A: 确保后端 `/copilotkit` 端点正常。可访问 `http://localhost:8001/docs` 查看 API 文档，或直接 POST 测试。

### Q: 前端组件报错找不到模块？
A: 这是正常的，执行 `npm install` 安装依赖后即会消失。
