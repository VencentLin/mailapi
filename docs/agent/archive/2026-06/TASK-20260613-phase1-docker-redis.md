# TASK-20260613-phase1-docker-redis

Status: DONE
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

用户要求最终前后端和 Redis 打包到同一个 Docker 镜像里部署，PostgreSQL 使用外部云数据库。

## 目标

完成 `docs/superpowers/plans/2026-06-13-mailapi-phase-1-foundation.md` 中的 Task 3。

不把 PostgreSQL 放进容器，不对外暴露 Redis 端口。

## 修改范围

- `.env.example`
- `Dockerfile`
- `docker/entrypoint.sh`

## 建议方案

按 Phase 1 plan 的 Task 3 执行：

- 添加 `.env.example`。
- Docker 使用 Node 阶段构建前端，再用 Python runtime 运行后端。
- runtime 镜像安装 Redis，entrypoint 先启动 Redis，再按 `RUN_MIGRATIONS` 决定是否执行 Alembic，最后启动 Uvicorn。

## 测试建议

- `python -m compileall backend`
- 如果本机 Docker 可用：`docker build -t mailapi:phase1 .`

## 验收标准

1. Dockerfile 是单镜像最终产物。
2. Redis 在容器内启动，不暴露外部端口。
3. `RUN_MIGRATIONS=true` 时会执行 `alembic upgrade head`。
4. 提交信息为 `feat: add single-container docker runtime` 或同等清晰信息。

## 风险与回退

Docker 构建依赖前端文件，若前端任务未完成，需在完成记录里说明 Docker build 被阻塞的原因。出问题时 revert 本任务 commit。

## Claude 完成记录

Status: DONE
Summary: Created .env.example, multi-stage Dockerfile (Node frontend build + Python runtime with Redis), and entrypoint.sh that starts Redis, optionally runs Alembic, then launches Uvicorn.
Verification: python -m compileall backend → no errors. Docker is NOT available on this Windows machine (not installed), so `docker build` was not run. Commit: 45d5187.
Notes: Docker build blocked by missing Docker daemon. Frontend uses Node 20 base image (matching local Node 20.11.0). Verify `docker build` on a machine with Docker installed.
