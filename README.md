# MailAPI

MailAPI 是一个面向 Outlook OAuth2 邮箱的验证码取件平台。

## 开发和部署约定

- **本机开发不使用 Docker**：直接启动 FastAPI 后端和 Vite 前端，方便调试。
- **最终部署再打包 Docker**：开发完成后，在服务器或有 Docker 的环境构建镜像；镜像内包含后端、前端静态文件和 Redis。
- **PostgreSQL 使用云端数据库**：本机开发和服务器部署都通过 `DATABASE_URL` 连接外部 PGSQL。

## 本机开发

安装后端依赖：

```bash
pip install -e ".[dev]"
```

准备环境变量：

```bash
copy .env.example .env
```

按实际情况修改 `.env` 里的 `DATABASE_URL`。第一阶段健康检查和基础测试不会连接真实数据库。

## 配置云端 PostgreSQL

不要把真实数据库密码提交到 git。复制 `.env.example` 为 `.env`，然后填写：

```env
DATABASE_URL=postgresql+asyncpg://用户名:密码@主机:5432/数据库名
```

应用运行时使用 `asyncpg`，`DATABASE_URL` 保持 `postgresql+asyncpg://...` 格式。Alembic 迁移会在内部使用项目依赖里的同步 PostgreSQL 驱动执行建表。

验证数据库连接：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000/api/health/db`，正常时返回：

```json
{"status": "ok", "database": "postgresql"}
```

执行迁移：

```bash
alembic upgrade head
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

安装并启动前端：

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

打开：

- 后端健康检查：`http://127.0.0.1:8000/api/health`
- 数据库健康检查：`http://127.0.0.1:8000/api/health/db`
- 前端开发服务：`http://127.0.0.1:5173/`

## 本机验证

后端测试：

```bash
pytest tests/backend -v
ruff check backend tests/backend
```

前端构建：

```bash
cd frontend
npm run build
```

Python 编译检查：

```bash
python -m compileall backend
```

## 服务器 Docker 部署

本机没有 Docker 时可以跳过这一节。等开发完成后，在服务器或有 Docker 的机器上执行：

```bash
docker build -t mailapi:latest .
docker run -d -p 8000:8000 --env-file .env --name mailapi mailapi:latest
```

打开：

- `http://服务器IP:8000/api/health`
- `http://服务器IP:8000/`
