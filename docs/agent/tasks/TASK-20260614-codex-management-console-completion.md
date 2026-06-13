# TASK-20260614-codex-management-console-completion

Status: DONE
Owner: Codex
Created by: Codex
Created at: 2026-06-14

## 背景

Claude 执行不稳定，用户要求 Codex 直接接手后续任务并完成后台管理闭环。

## 完成内容

- API Key 创建、列表、禁用、哈希存储、过期/禁用校验。
- 兼容取件 API 支持 Bearer API Key 和 body `user_token`，并按 Key 所属用户自动托管邮箱。
- 邮箱管理 API：列表筛选、创建、认领、禁用、测试取件、清空、管理员查看/修改凭据。
- 管理员查看/修改 refresh token 写入 `audit_logs`。
- 取件日志 API：管理员看全部，普通用户看自己的日志。
- 验证码 API：按发件人、主题、正文关键词、时间窗口和正则提取验证码。
- 工作台统计 API。
- 前端接入真实接口：工作台、邮箱管理、API Key、验证码取件测试、取件日志。
- README 增加后台功能、API Key、验证码 API 说明。

## 验证结果

- `.venv\Scripts\python.exe -m pytest tests/backend -v`：78 passed。
- `.venv\Scripts\ruff.exe check backend tests/backend`：All checks passed。
- `.venv\Scripts\python.exe -m compileall backend`：通过。
- `.venv\Scripts\python.exe -m alembic current`：`20260613_0001 (head)`。
- 云端数据库健康检查：`{'status': 'ok', 'database': 'postgresql'}`。
- `cd frontend && npm run build`：构建成功；保留 Vite 对依赖 PURE 注释和大 chunk 的 warning。

## 遗留事项

- 本机没有 Docker，未执行 Docker 镜像构建。
- 真实 Outlook OAuth2 联调仍等待真实 `email + client_id + refresh_token`，不能标记为已完成。
