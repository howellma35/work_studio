# rag_game



```powershell
# 进入后端目录
cd e:\githubcode\rag_game\vehicle-agent\backend



# 激活虚拟环境 (Windows PowerShell)
.\.venv\Scripts\Activate.ps1


python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload





cd e:\githubcode\rag_game\vehicle-agent\frontend
npm run dev