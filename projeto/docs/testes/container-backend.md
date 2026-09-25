# Validação do container backend isolado

- Build: `docker build -t servidores-backend .` (OK)
- Run: `docker run -d -p 8000:8000 --name backend-test servidores-backend`
- `GET /health` → 200 `{"status":"ok"}`
- `GET /api/servidores` → 501 `{"status":"nao implementado"}`
- Logs do Gunicorn: servidor iniciado em `0.0.0.0:8000`, worker `gthread`, 2 workers ativos (pids 7 e 8)
- Container parado e removido após o teste
