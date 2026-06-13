# TASK-20260613-phase1-frontend-shell

Status: DONE
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

前端需要重新整理为 Vue 管理后台。第一阶段只建立可构建的后台壳，不实现真实登录、邮箱管理或 API Key 页面。

## 目标

完成 `docs/superpowers/plans/2026-06-13-mailapi-phase-1-foundation.md` 中的 Task 4。

不实现真实鉴权请求，不接入后端业务 API。

## 修改范围

- `frontend/**`

## 建议方案

按 Phase 1 plan 的 Task 4 执行：

- 创建 Vite + Vue + Element Plus 项目结构。
- 添加登录页和工作台基础页面。
- 使用 Pinia 保留未来认证状态入口。
- 确保 `npm run build` 成功生成 `frontend/dist`。

## 测试建议

- `cd frontend && npm install`
- `cd frontend && npm run build`

## 验收标准

1. `frontend/dist/index.html` 可以生成。
2. 页面包括登录页和工作台。
3. UI 是管理后台风格，不是营销落地页。
4. 提交信息为 `feat: add vue admin shell` 或同等清晰信息。

## 风险与回退

风险较低。若依赖安装失败，需要记录 npm 和 Node 版本。出问题时 revert 本任务 commit。

## Claude 完成记录

Status: DONE
Summary: Created Vite + Vue 3 + Element Plus admin shell with login page and dashboard. Downgraded Vite 7→5 and Vue plugin versions for Node.js 20.11.0 compatibility. Build generates frontend/dist/ with index.html.
Verification: npm install → success (no engine warnings). npm run build → success, dist/index.html generated, 3 output files (index.html, CSS, JS). Commit: 383cb69.
Notes: Node.js 20.11.0 is below Vite 7's requirement (^20.19.0). Used Vite 5.4 + @vitejs/plugin-vue 5.2 instead. Removed @tsconfig/node22 and @vue/tsconfig dependencies since they require newer Node; wrote tsconfig manually.
