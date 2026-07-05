# AutoMind - 智能车机助手

## 本地开发 (Windows)

```bash
# 1. 后端
cd vehicle-agent/backend
python -m venv .venv && 
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env  # 填入 API Key
python -m uvicorn app.main:app --port 8001 --reload

# 2. Runtime
cd vehicle-agent/runtime
npm install
npm run dev  # port 4000

# 3. 前端
cd vehicle-agent/frontend
npm install
npm run dev  # http://localhost:5174
```

## 内网 Docker 部署

```bash
cd deploy
cp .env.example .env  # 填入真实配置
docker compose up -d --build
```

更新单个服务：
```bash
docker compose up -d --force-recreate --build vehicle-backend
docker compose restart nginx
```
