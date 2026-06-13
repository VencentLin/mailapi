# TASK-20260613-phase2-frontend-login-guard

Status: TODO
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

当前 `/` 直接进入 MailAPI 控制台，`/login` 是静态页面，登录按钮没有真实行为。

## 目标

实现前端登录请求、token 保存、路由守卫和退出登录。

不实现完整管理业务页面。

## 修改范围

- `frontend/src/stores/auth.ts`
- `frontend/src/router/index.ts`
- `frontend/src/views/LoginView.vue`
- `frontend/src/api/http.ts`
- `frontend/src/api/auth.ts`

## 建议方案

按 `docs/superpowers/plans/2026-06-13-mailapi-phase-2-auth-management-db.md` 的 Task 3 执行。

## 测试建议

- `cd frontend && npm run build`
- 手工打开 `/`，未登录应跳转 `/login`
- 登录成功后跳转 `/`
- 退出后回到 `/login`

## 验收标准

1. 未登录不能直接进入控制台。
2. 登录页调用后端 `/auth/login`。
3. token 存入 `localStorage`。
4. 刷新后登录态可恢复。

## 风险与回退

依赖后端 Auth 任务完成。若后端未完成，只能完成前端代码构建，手工登录验证标记 BLOCKED。

## Claude 完成记录

Status:
Summary:
Verification:
Notes:
