# TASK-20260613-phase2-frontend-login-guard

Status: DONE
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

Status: DONE
Summary:
- `frontend/src/api/http.ts`：基于 fetch 的 HTTP 客户端，自动附加 `Authorization: Bearer <token>`，统一错误处理（ApiError 类）。
- `frontend/src/api/auth.ts`：`login()` 和 `fetchMe()` API 函数，类型定义（LoginRequest、TokenResponse、UserPublic）。
- `frontend/src/stores/auth.ts`：新增 `login`、`logout`、`loadMe`、`setUser` actions；token 持久化到 localStorage；启动时从 localStorage 恢复 token。
- `frontend/src/router/index.ts`：新增 `beforeEach` 路由守卫——未登录访问受保护页跳转 `/login`，已登录访问 `/login` 跳转 `/`。
- `frontend/src/views/LoginView.vue`：添加 `<script setup>`，v-model 绑定用户名/密码，loading 状态，错误提示，调用 auth store login。
- `frontend/src/views/DashboardView.vue`：退出按钮接入 auth store logout + router 跳转。

Verification:
- `cd frontend && npm run build` → vue-tsc 类型检查通过，vite build 成功。
- 手工验证被标记为 BLOCKED（需要后端运行 + 真实 admin 账号才能测试完整登录流程），但代码和构建完全通过。

Notes:
- 完整端到端登录验证需要：1) 后端运行 2) 通过 CLI 创建 admin 用户 3) 前端 dev server 代理到后端。当前可验证构建通过。
