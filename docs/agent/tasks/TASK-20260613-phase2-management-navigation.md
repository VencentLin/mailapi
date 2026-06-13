# TASK-20260613-phase2-management-navigation

Status: TODO
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

当前控制台只有几个指标卡片，没有管理菜单，用户看不到用户管理、邮箱管理、API Key 和日志入口。

## 目标

实现登录后的管理后台布局和导航，让管理入口可见。

不实现所有管理 API 的真实业务逻辑。

## 修改范围

- `frontend/src/layouts/AppLayout.vue`
- `frontend/src/router/index.ts`
- `frontend/src/views/DashboardView.vue`
- `frontend/src/views/users/UserListView.vue`
- `frontend/src/views/mail/MailAccountListView.vue`
- `frontend/src/views/apiKeys/ApiKeyListView.vue`
- `frontend/src/views/logs/MailFetchLogView.vue`

## 建议方案

按 `docs/superpowers/plans/2026-06-13-mailapi-phase-2-auth-management-db.md` 的 Task 4 执行。

## 测试建议

- `cd frontend && npm run build`
- 登录后手工点击所有菜单

## 验收标准

1. 登录后显示顶部栏和侧边栏。
2. 菜单包含工作台、用户管理、邮箱管理、API Key、取件日志。
3. 每个菜单都有页面和空状态。
4. 退出登录可用。

## 风险与回退

主要是前端结构调整。若路由守卫冲突，优先保证未登录不能进入后台。

## Claude 完成记录

Status:
Summary:
Verification:
Notes:
